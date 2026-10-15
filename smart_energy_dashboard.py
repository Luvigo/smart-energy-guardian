#!/usr/bin/env python3
"""SMART ENERGY HOME — panel local de control."""

import csv
import math
import re
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import font as tkfont
from tkinter import ttk
from typing import Callable, Optional

from serial import SerialException

from arduino_serial import ArduinoSerialConnection, list_serial_ports

# Paleta y dimensiones
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 860
MIN_WIDTH = 1120
MIN_HEIGHT = 720
TWIN_MX = 35.0
TWIN_MZ = 25.0
TWIN_MY = 18.0
BG = "#0B1220"
CARD = "#141E30"
CARD_ALT = "#1B2940"
TEXT = "#EAF1FF"
TEXT_MUTED = "#93A4BF"
GREEN = "#22C55E"
GREEN_DIM = "#16A34A"
BLUE = "#3B82F6"
BLUE_DIM = "#2563EB"
RED = "#EF4444"
RED_DIM = "#991B1B"
AMBER = "#F59E0B"
VIOLET = "#8B5CF6"
CYAN = "#22D3EE"
MAP_BG = "#0D1526"
MAP_WALL = "#3D4F6F"
MAP_FLOOR = "#121C2E"
LED_ENTRY_ON = "#FACC15"
LED_LIVING_ON = "#F87171"
LED_BEDROOM_ON = "#4ADE80"
LED_OFF = "#1E2A3D"
DOOR_WOOD = "#92400E"
BORDER = "#263652"
GRAY_OFF = TEXT_MUTED
GRAY_BG = "#1B2940"
SERIAL_POLL_MS = 200

_ENERGY_RE = re.compile(r"^ENERGY:V=([\d.]+),I=([\d.]+),P=([\d.]+)$")


class FlatButton(tk.Frame):
    """Botón visual personalizado sin apariencia nativa de tk.Button."""

    def __init__(
        self,
        parent: tk.Misc,
        text: str,
        command: Callable[[], None],
        bg: str,
        hover_bg: str,
        fg: str = TEXT,
        disabled_bg: str = "#243044",
        font: Optional[tkfont.Font] = None,
        padx: int = 16,
        pady: int = 12,
    ) -> None:
        super().__init__(
            parent,
            bg=bg,
            highlightthickness=1,
            highlightbackground=BORDER,
            highlightcolor=BORDER,
        )
        self._command = command
        self._bg = bg
        self._hover_bg = hover_bg
        self._disabled_bg = disabled_bg
        self._fg = fg
        self._enabled = True
        self._font = font or tkfont.Font(family="Helvetica", size=11, weight="bold")

        self._label = tk.Label(
            self,
            text=text,
            font=self._font,
            bg=bg,
            fg=fg,
            padx=padx,
            pady=pady,
            cursor="hand2",
        )
        self._label.pack(fill=tk.BOTH, expand=True)

        for widget in (self, self._label):
            widget.bind("<Enter>", self._on_enter)
            widget.bind("<Leave>", self._on_leave)
            widget.bind("<Button-1>", self._on_click)

        self._apply_visual()

    def configure(self, cnf: Optional[str] = None, **kwargs) -> None:
        if isinstance(cnf, dict):
            kwargs = {**cnf, **kwargs}
            cnf = None
        if "state" in kwargs:
            self._enabled = kwargs.pop("state") != tk.DISABLED
        if "bg" in kwargs:
            self._bg = kwargs.pop("bg")
        self._apply_visual()
        if cnf is not None or kwargs:
            super().configure(cnf, **kwargs)

    config = configure

    def _apply_visual(self) -> None:
        bg = self._bg if self._enabled else self._disabled_bg
        fg = self._fg if self._enabled else TEXT_MUTED
        cursor = "hand2" if self._enabled else "arrow"
        super().configure(bg=bg)
        self._label.configure(bg=bg, fg=fg, cursor=cursor)

    def _on_enter(self, _event: tk.Event) -> None:
        if self._enabled:
            super().configure(bg=self._hover_bg)
            self._label.configure(bg=self._hover_bg)

    def _on_leave(self, _event: tk.Event) -> None:
        self._apply_visual()

    def _on_click(self, _event: tk.Event) -> None:
        if self._enabled:
            self._command()


def _card(parent: tk.Misc, bg: str = CARD) -> tuple[tk.Frame, tk.Frame]:
    outer = tk.Frame(
        parent,
        bg=BORDER,
        highlightthickness=0,
        padx=1,
        pady=1,
    )
    inner = tk.Frame(outer, bg=bg, padx=18, pady=16)
    inner.pack(fill=tk.BOTH, expand=True)
    return outer, inner


class SmartEnergyDashboard(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("SMART ENERGY HOME")
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.minsize(MIN_WIDTH, MIN_HEIGHT)
        self.configure(bg=BG)
        self.resizable(True, True)

        self._arduino = ArduinoSerialConnection()
        self._port_var = tk.StringVar(value="")
        self._session_events: list[tuple[datetime, str]] = []
        self._project_dir = Path(__file__).resolve().parent
        self._connection_error = False

        # Métricas (solo datos reales del Arduino)
        self._distance_cm: Optional[float] = None
        self._proximity_kind: Optional[str] = None  # "NEAR" | "FAR"
        self._energy: Optional[tuple[float, float, float]] = None  # V, I, P

        # Estado comandado (local + sincronizado por serial)
        self._light_entry = False
        self._light_living = False
        self._light_bedroom = False
        self._door_open = False
        self._window_open = False
        self._alarm_active = False
        self._door_state_confirmed = False
        self._window_state_confirmed = False
        self._servos_operational = False
        self._door_pending: Optional[str] = None
        self._window_pending: Optional[str] = None
        self._light_pending: set[str] = set()
        self._alarm_pending = False

        # Actividad
        self._last_distance_cm: Optional[float] = None
        self._near_detection_count = 0
        self._last_near_detection_at: Optional[datetime] = None
        self._last_action = "—"

        # Gemelo digital (vista isométrica 2.5D)
        self._twin_yaw_deg = 32.0
        self._twin_yaw_default = 32.0
        self._camera_zoom = 1.0
        self._twin_drag_anchor_x: Optional[int] = None
        self._twin_anim_phase = 0.0
        self._twin_anim_after_id: Optional[str] = None
        self._current_view = "twin"

        self._build_ui()
        self._refresh_all_displays()
        self._refresh_serial_ports()
        self._update_arduino_status()
        self._update_system_chrome()
        self._log_event("Sistema iniciado (SMART ENERGY HOME).")

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._schedule_serial_poll()
        self._schedule_activity_tick()
        self._schedule_twin_animation()
        self.bind("<Configure>", self._on_window_resize)

    def _on_window_resize(self, event: tk.Event) -> None:
        if event.widget is not self:
            return
        wrap = max(200, (event.width - 120) // 3 - 20)
        card_wrap = max(240, (event.width - 160) // 2)
        if hasattr(self, "_lighting_mode_label"):
            self._lighting_mode_label.configure(wraplength=card_wrap)
        if hasattr(self, "_access_mode_label"):
            self._access_mode_label.configure(wraplength=card_wrap)
        for label in (
            self._distance_context_label,
            self._proximity_context_label,
            self._energy_context_label,
            self._arduino_status_label,
            self._conn_port_label,
            self._lighting_mode_label,
            self._access_mode_label,
            self._servo_status_hint,
        ):
            label.configure(wraplength=wrap)
        if hasattr(self, "_twin_subtitle_label"):
            self._twin_subtitle_label.configure(wraplength=max(280, event.width - 200))
        if hasattr(self, "_log_comm_label"):
            self._log_comm_label.configure(wraplength=max(400, event.width - 80))

    def _build_ui(self) -> None:
        self._title_font = tkfont.Font(family="Helvetica", size=22, weight="bold")
        self._subtitle_font = tkfont.Font(family="Helvetica", size=11)
        self._section_font = tkfont.Font(family="Helvetica", size=13, weight="bold")
        self._label_font = tkfont.Font(family="Helvetica", size=11)
        self._status_font = tkfont.Font(family="Helvetica", size=18, weight="bold")
        self._small_font = tkfont.Font(family="Helvetica", size=10)
        self._btn_font = tkfont.Font(family="Helvetica", size=11, weight="bold")
        self._small_btn_font = tkfont.Font(family="Helvetica", size=10, weight="bold")
        self._mono_font = tkfont.Font(family="Menlo", size=10)
        self._metric_num_font = tkfont.Font(family="Helvetica", size=28, weight="bold")

        root = tk.Frame(self, bg=BG)
        root.pack(fill=tk.BOTH, expand=True, padx=22, pady=18)

        header = tk.Frame(root, bg=BG)
        header.pack(fill=tk.X, pady=(0, 18))

        brand = tk.Frame(header, bg=BG)
        brand.pack(side=tk.LEFT, fill=tk.X, expand=True)

        brand_row = tk.Frame(brand, bg=BG)
        brand_row.pack(anchor=tk.W)

        icon_box = tk.Frame(brand_row, bg=BLUE, padx=10, pady=6)
        icon_box.pack(side=tk.LEFT, padx=(0, 12))
        tk.Label(
            icon_box,
            text="🏠",
            font=tkfont.Font(size=18),
            fg=TEXT,
            bg=BLUE,
        ).pack()

        titles = tk.Frame(brand_row, bg=BG)
        titles.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Label(
            titles,
            text="SMART ENERGY HOME",
            font=self._title_font,
            fg=TEXT,
            bg=BG,
            anchor=tk.W,
        ).pack(anchor=tk.W)
        tk.Label(
            titles,
            text="Dashboard de casa inteligente — sensores, iluminación y accesos",
            font=self._subtitle_font,
            fg=TEXT_MUTED,
            bg=BG,
            anchor=tk.W,
        ).pack(anchor=tk.W, pady=(2, 0))

        self._badge_frame = tk.Frame(header, bg=GRAY_BG, padx=14, pady=8)
        self._badge_frame.pack(side=tk.RIGHT, anchor=tk.NE)
        self._badge_label = tk.Label(
            self._badge_frame,
            text="Modo demostración",
            font=self._small_btn_font,
            fg=TEXT_MUTED,
            bg=GRAY_BG,
        )
        self._badge_label.pack()

        nav = tk.Frame(root, bg=BG)
        nav.pack(fill=tk.X, pady=(0, 12))
        self._nav_buttons: dict[str, FlatButton] = {}
        for key, title in (
            ("twin", "Gemelo digital"),
            ("control", "Control y datos"),
            ("log", "Registro de eventos"),
        ):
            btn = FlatButton(
                nav,
                text=title,
                command=lambda k=key: self._show_view(k),
                bg=CARD_ALT,
                hover_bg=BORDER,
                font=self._small_btn_font,
                padx=14,
                pady=10,
            )
            btn.pack(side=tk.LEFT, padx=(0, 8))
            self._nav_buttons[key] = btn

        self._content_host = tk.Frame(root, bg=BG)
        self._content_host.pack(fill=tk.BOTH, expand=True)

        self._view_twin = tk.Frame(self._content_host, bg=BG)
        self._view_control = tk.Frame(self._content_host, bg=BG)
        self._view_log = tk.Frame(self._content_host, bg=BG)

        twin_outer, twin_inner = _card(self._view_twin, CARD_ALT)
        twin_outer.pack(fill=tk.BOTH, expand=True)
        self._build_maquette_map(twin_inner)

        self._build_control_view(self._view_control)
        self._build_log_view(self._view_log)

        footer = tk.Frame(root, bg=BG)
        footer.pack(fill=tk.X, pady=(10, 0))
        tk.Label(
            footer,
            text="SMART ENERGY HOME · Proyecto académico",
            font=self._small_font,
            fg=TEXT_MUTED,
            bg=BG,
        ).pack(side=tk.LEFT)

        self._show_view("twin")

    def _show_view(self, view: str) -> None:
        self._current_view = view
        for frame in (self._view_twin, self._view_control, self._view_log):
            frame.pack_forget()
        if view == "twin":
            self._view_twin.pack(fill=tk.BOTH, expand=True)
        elif view == "control":
            self._view_control.pack(fill=tk.BOTH, expand=True)
        else:
            self._view_log.pack(fill=tk.BOTH, expand=True)

        for key, btn in self._nav_buttons.items():
            if key == view:
                btn.configure(bg=BLUE)
            else:
                btn.configure(bg=CARD_ALT)

        if view == "twin" and hasattr(self, "_maquette_canvas"):
            self._draw_maquette_map()

    def _build_control_view(self, parent: tk.Frame) -> None:
        shell_outer, shell = _card(parent, CARD_ALT)
        shell_outer.pack(fill=tk.BOTH, expand=True)
        shell.columnconfigure(0, weight=1)
        shell.rowconfigure(1, weight=1)

        tk.Label(
            shell,
            text="Control y datos",
            font=self._section_font,
            fg=TEXT,
            bg=shell["bg"],
        ).grid(row=0, column=0, sticky="w", pady=(0, 10))

        body = tk.Frame(shell, bg=shell["bg"])
        body.grid(row=1, column=0, sticky="nsew")
        body.columnconfigure(0, weight=1)
        body.rowconfigure(2, weight=1)

        metrics = tk.Frame(body, bg=shell["bg"])
        metrics.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        for col in range(3):
            metrics.columnconfigure(col, weight=1, uniform="metrics")

        dist_outer, dist_inner = _card(metrics, CARD)
        dist_outer.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        self._build_metric_distance_card(dist_inner)

        prox_outer, prox_inner = _card(metrics, CARD)
        prox_outer.grid(row=0, column=1, sticky="nsew", padx=6)
        self._build_metric_proximity_card(prox_inner)

        energy_outer, energy_inner = _card(metrics, CARD)
        energy_outer.grid(row=0, column=2, sticky="nsew", padx=(6, 0))
        self._build_metric_energy_card(energy_inner)

        activity_outer, activity_inner = _card(body, CARD)
        activity_outer.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        self._build_activity_card(activity_inner)

        controls = tk.Frame(body, bg=shell["bg"])
        controls.grid(row=2, column=0, sticky="nsew", pady=(0, 10))
        controls.columnconfigure(0, weight=1, uniform="ctrl")
        controls.columnconfigure(1, weight=1, uniform="ctrl")
        controls.rowconfigure(0, weight=1)

        light_outer, light_inner = _card(controls, CARD)
        light_outer.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self._build_lighting_card(light_inner)

        access_outer, access_inner = _card(controls, CARD)
        access_outer.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        self._build_access_card(access_inner)

        arduino_outer, arduino_inner = _card(body, CARD)
        arduino_outer.grid(row=3, column=0, sticky="ew")

        self._build_arduino_card(arduino_inner)

    def _build_log_view(self, parent: tk.Frame) -> None:
        log_outer, log_inner = _card(parent, CARD)
        log_outer.pack(fill=tk.BOTH, expand=True)

        log_header = tk.Frame(log_inner, bg=CARD)
        log_header.pack(fill=tk.X, pady=(0, 10))

        tk.Label(
            log_header,
            text="Registro de eventos",
            font=self._section_font,
            fg=TEXT,
            bg=CARD,
        ).pack(side=tk.LEFT, anchor=tk.W)

        self._btn_export = FlatButton(
            log_header,
            text="Exportar CSV",
            command=self._export_session_log,
            bg=CARD_ALT,
            hover_bg=BORDER,
            fg=TEXT_MUTED,
            font=self._small_btn_font,
            padx=12,
            pady=6,
        )
        self._btn_export.pack(side=tk.RIGHT)

        self._log_comm_label = tk.Label(
            log_inner,
            text="Estado de comunicación: en espera",
            font=self._small_btn_font,
            fg=TEXT_MUTED,
            bg=CARD,
            wraplength=600,
            justify=tk.LEFT,
        )
        self._log_comm_label.pack(anchor=tk.W, pady=(0, 10))

        log_container = tk.Frame(log_inner, bg=BG, highlightthickness=1, highlightbackground=BORDER)
        log_container.pack(fill=tk.BOTH, expand=True)

        self._log_text = tk.Text(
            log_container,
            font=self._mono_font,
            fg=TEXT,
            bg=BG,
            insertbackground=TEXT,
            relief=tk.FLAT,
            wrap=tk.WORD,
            state=tk.DISABLED,
            padx=14,
            pady=12,
            borderwidth=0,
            highlightthickness=0,
        )
        scroll = tk.Scrollbar(
            log_container,
            command=self._log_text.yview,
            bg=CARD,
            troughcolor=BG,
            activebackground=BORDER,
            highlightthickness=0,
            borderwidth=0,
        )
        self._log_text.configure(yscrollcommand=scroll.set)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self._log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    def _build_metric_distance_card(self, parent: tk.Frame) -> None:
        tk.Label(parent, text="Distancia", font=self._label_font, fg=TEXT_MUTED, bg=parent["bg"]).pack(
            anchor=tk.W
        )
        row = tk.Frame(parent, bg=parent["bg"])
        row.pack(anchor=tk.W, pady=(10, 4))
        self._distance_dot = tk.Label(row, text="●", font=self._status_font, fg=TEXT_MUTED, bg=parent["bg"])
        self._distance_dot.pack(side=tk.LEFT, padx=(0, 8))
        self._distance_label = tk.Label(
            row,
            text="Sin lectura",
            font=self._metric_num_font,
            fg=TEXT_MUTED,
            bg=parent["bg"],
        )
        self._distance_label.pack(side=tk.LEFT)
        self._distance_context_label = tk.Label(
            parent,
            text="HC-SR04 (D9/D10). Sin datos simulados.",
            font=self._small_font,
            fg=TEXT_MUTED,
            bg=parent["bg"],
            wraplength=280,
            justify=tk.LEFT,
        )
        self._distance_context_label.pack(anchor=tk.W, pady=(6, 0))

    def _build_metric_proximity_card(self, parent: tk.Frame) -> None:
        tk.Label(parent, text="Proximidad", font=self._label_font, fg=TEXT_MUTED, bg=parent["bg"]).pack(
            anchor=tk.W
        )
        row = tk.Frame(parent, bg=parent["bg"])
        row.pack(anchor=tk.W, pady=(10, 4))
        self._proximity_dot = tk.Label(row, text="●", font=self._status_font, fg=TEXT_MUTED, bg=parent["bg"])
        self._proximity_dot.pack(side=tk.LEFT, padx=(0, 8))
        self._proximity_label = tk.Label(
            row,
            text="Sin lectura",
            font=tkfont.Font(family="Helvetica", size=16, weight="bold"),
            fg=TEXT_MUTED,
            bg=parent["bg"],
            wraplength=260,
            justify=tk.LEFT,
        )
        self._proximity_label.pack(side=tk.LEFT)
        self._proximity_context_label = tk.Label(
            parent,
            text="Basado en el ultrasonido del Arduino.",
            font=self._small_font,
            fg=TEXT_MUTED,
            bg=parent["bg"],
            wraplength=280,
            justify=tk.LEFT,
        )
        self._proximity_context_label.pack(anchor=tk.W, pady=(6, 0))

    def _build_metric_energy_card(self, parent: tk.Frame) -> None:
        tk.Label(parent, text="Energía", font=self._label_font, fg=TEXT_MUTED, bg=parent["bg"]).pack(anchor=tk.W)
        row = tk.Frame(parent, bg=parent["bg"])
        row.pack(anchor=tk.W, pady=(10, 4))
        self._energy_dot = tk.Label(row, text="●", font=self._status_font, fg=TEXT_MUTED, bg=parent["bg"])
        self._energy_dot.pack(side=tk.LEFT, padx=(0, 8))
        self._energy_label = tk.Label(
            row,
            text="Sin lectura INA219",
            font=tkfont.Font(family="Helvetica", size=14, weight="bold"),
            fg=TEXT_MUTED,
            bg=parent["bg"],
            wraplength=280,
            justify=tk.LEFT,
        )
        self._energy_label.pack(side=tk.LEFT)
        self._energy_context_label = tk.Label(
            parent,
            text="INA219 (A4/A5). Sin valores 0.0 simulados.",
            font=self._small_font,
            fg=TEXT_MUTED,
            bg=parent["bg"],
            wraplength=280,
            justify=tk.LEFT,
        )
        self._energy_context_label.pack(anchor=tk.W, pady=(6, 0))

    def _build_activity_card(self, parent: tk.Frame) -> None:
        tk.Label(
            parent,
            text="Actividad reciente",
            font=self._section_font,
            fg=TEXT,
            bg=parent["bg"],
        ).pack(anchor=tk.W, pady=(0, 10))

        frame = tk.Frame(parent, bg=parent["bg"])
        frame.pack(fill=tk.X)

        c1 = tk.Frame(frame, bg=parent["bg"])
        c1.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 12))
        tk.Label(c1, text="Última distancia", font=self._label_font, fg=TEXT_MUTED, bg=parent["bg"]).pack(
            anchor=tk.W
        )
        self._activity_distance_label = tk.Label(
            c1,
            text="—",
            font=tkfont.Font(family="Menlo", size=18, weight="bold"),
            fg=TEXT,
            bg=parent["bg"],
        )
        self._activity_distance_label.pack(anchor=tk.W, pady=(4, 0))

        c2 = tk.Frame(frame, bg=parent["bg"])
        c2.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=12)
        tk.Label(c2, text="Última detección cercana", font=self._label_font, fg=TEXT_MUTED, bg=parent["bg"]).pack(
            anchor=tk.W
        )
        self._last_detection_time_label = tk.Label(
            c2,
            text="--:--:--",
            font=tkfont.Font(family="Menlo", size=18, weight="bold"),
            fg=TEXT,
            bg=parent["bg"],
        )
        self._last_detection_time_label.pack(anchor=tk.W, pady=(4, 0))
        self._last_detection_ago_label = tk.Label(
            c2,
            text="Sin detecciones en esta sesión",
            font=self._small_font,
            fg=TEXT_MUTED,
            bg=parent["bg"],
        )
        self._last_detection_ago_label.pack(anchor=tk.W, pady=(2, 0))

        c3 = tk.Frame(frame, bg=parent["bg"])
        c3.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=12)
        tk.Label(c3, text="Detecciones cercanas (sesión)", font=self._label_font, fg=TEXT_MUTED, bg=parent["bg"]).pack(
            anchor=tk.W
        )
        self._near_count_label = tk.Label(
            c3,
            text="0",
            font=self._metric_num_font,
            fg=BLUE,
            bg=parent["bg"],
        )
        self._near_count_label.pack(anchor=tk.W, pady=(4, 0))

        c4 = tk.Frame(frame, bg=parent["bg"])
        c4.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(12, 0))
        tk.Label(c4, text="Última acción", font=self._label_font, fg=TEXT_MUTED, bg=parent["bg"]).pack(anchor=tk.W)
        self._last_action_label = tk.Label(
            c4,
            text="—",
            font=tkfont.Font(family="Helvetica", size=16, weight="bold"),
            fg=TEXT,
            bg=parent["bg"],
        )
        self._last_action_label.pack(anchor=tk.W, pady=(4, 0))

    def _build_lighting_card(self, parent: tk.Frame) -> None:
        tk.Label(
            parent,
            text="Iluminación de la casa",
            font=self._section_font,
            fg=TEXT,
            bg=parent["bg"],
        ).pack(anchor=tk.W)

        self._lighting_mode_label = tk.Label(
            parent,
            text="Modo demostración: cambios locales en LEDs.",
            font=self._small_font,
            fg=TEXT_MUTED,
            bg=parent["bg"],
            wraplength=420,
            justify=tk.LEFT,
        )
        self._lighting_mode_label.pack(anchor=tk.W, pady=(6, 12))

        self._light_labels: dict[str, tk.Label] = {}
        self._light_dots: dict[str, tk.Label] = {}
        for key, title in (("entry", "Entrada (D2)"), ("living", "Sala (D3)"), ("bedroom", "Habitación (D4)")):
            self._add_light_row(parent, key, title)

    def _add_light_row(self, parent: tk.Frame, key: str, title: str) -> None:
        row = tk.Frame(parent, bg=parent["bg"])
        row.pack(fill=tk.X, pady=(0, 10))

        left = tk.Frame(row, bg=parent["bg"])
        left.pack(side=tk.LEFT, fill=tk.X, expand=True)

        tk.Label(left, text=title, font=self._label_font, fg=TEXT_MUTED, bg=parent["bg"]).pack(anchor=tk.W)
        status_row = tk.Frame(left, bg=parent["bg"])
        status_row.pack(anchor=tk.W, pady=(4, 0))
        dot = tk.Label(status_row, text="●", font=self._status_font, fg=GRAY_OFF, bg=parent["bg"])
        dot.pack(side=tk.LEFT, padx=(0, 6))
        state_lbl = tk.Label(
            status_row,
            text="APAGADA",
            font=self._small_btn_font,
            fg=GRAY_OFF,
            bg=parent["bg"],
        )
        state_lbl.pack(side=tk.LEFT)
        self._light_dots[key] = dot
        self._light_labels[key] = state_lbl

        btn_row = tk.Frame(row, bg=parent["bg"])
        btn_row.pack(side=tk.RIGHT)

        FlatButton(
            btn_row,
            text="Encender",
            command=lambda k=key: self._light_on(k),
            bg=GREEN,
            hover_bg=GREEN_DIM,
            font=self._small_btn_font,
            padx=10,
            pady=8,
        ).pack(side=tk.LEFT, padx=(0, 6))

        FlatButton(
            btn_row,
            text="Apagar",
            command=lambda k=key: self._light_off(k),
            bg=CARD_ALT,
            hover_bg=BORDER,
            font=self._small_btn_font,
            padx=10,
            pady=8,
        ).pack(side=tk.LEFT)

    def _build_access_card(self, parent: tk.Frame) -> None:
        tk.Label(
            parent,
            text="Accesos y alerta",
            font=self._section_font,
            fg=TEXT,
            bg=parent["bg"],
        ).pack(anchor=tk.W)

        self._access_mode_label = tk.Label(
            parent,
            text="Servos D5/D6 y buzzer D7. Demostración local sin Arduino.",
            font=self._small_font,
            fg=TEXT_MUTED,
            bg=parent["bg"],
            wraplength=420,
            justify=tk.LEFT,
        )
        self._access_mode_label.pack(anchor=tk.W, pady=(6, 10))

        self._door_label = self._add_access_status(parent, "Puerta (servo D5)")
        self._window_label = self._add_access_status(parent, "Ventana (servo D6)")
        self._alarm_label = self._add_access_status(parent, "Alarma (buzzer D7)")

        servo_block = tk.Frame(parent, bg=parent["bg"])
        servo_block.pack(fill=tk.X, pady=(10, 10))
        tk.Label(
            servo_block,
            text="Estado de servos",
            font=self._small_font,
            fg=TEXT_MUTED,
            bg=parent["bg"],
        ).pack(anchor=tk.W)
        self._servo_status_label = tk.Label(
            servo_block,
            text="Pendiente de alimentación externa",
            font=self._small_btn_font,
            fg=AMBER,
            bg=parent["bg"],
        )
        self._servo_status_label.pack(anchor=tk.W, pady=(2, 0))
        self._servo_status_hint = tk.Label(
            servo_block,
            text="Requieren 5 V externa y GND común.",
            font=self._small_font,
            fg=TEXT_MUTED,
            bg=parent["bg"],
            wraplength=420,
            justify=tk.LEFT,
        )
        self._servo_status_hint.pack(anchor=tk.W, pady=(2, 0))

        door_btns = tk.Frame(parent, bg=parent["bg"])
        door_btns.pack(fill=tk.X, pady=(4, 8))
        FlatButton(
            door_btns,
            text="Abrir puerta",
            command=self._door_open_cmd,
            bg=BLUE,
            hover_bg=BLUE_DIM,
            font=self._small_btn_font,
            padx=8,
            pady=8,
        ).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 4))
        FlatButton(
            door_btns,
            text="Cerrar puerta",
            command=self._door_close_cmd,
            bg=CARD_ALT,
            hover_bg=BORDER,
            font=self._small_btn_font,
            padx=8,
            pady=8,
        ).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(4, 0))

        win_btns = tk.Frame(parent, bg=parent["bg"])
        win_btns.pack(fill=tk.X, pady=(0, 8))
        FlatButton(
            win_btns,
            text="Abrir ventana",
            command=self._window_open_cmd,
            bg=BLUE,
            hover_bg=BLUE_DIM,
            font=self._small_btn_font,
            padx=8,
            pady=8,
        ).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 4))
        FlatButton(
            win_btns,
            text="Cerrar ventana",
            command=self._window_close_cmd,
            bg=CARD_ALT,
            hover_bg=BORDER,
            font=self._small_btn_font,
            padx=8,
            pady=8,
        ).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(4, 0))

        alarm_btns = tk.Frame(parent, bg=parent["bg"])
        alarm_btns.pack(fill=tk.X)
        FlatButton(
            alarm_btns,
            text="Activar alarma",
            command=self._alarm_on_cmd,
            bg=RED_DIM,
            hover_bg=RED,
            font=self._small_btn_font,
            padx=8,
            pady=8,
        ).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 4))
        FlatButton(
            alarm_btns,
            text="Desactivar alarma",
            command=self._alarm_off_cmd,
            bg=CARD_ALT,
            hover_bg=BORDER,
            font=self._small_btn_font,
            padx=8,
            pady=8,
        ).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(4, 0))

    def _add_access_status(self, parent: tk.Frame, title: str) -> tk.Label:
        block = tk.Frame(parent, bg=parent["bg"])
        block.pack(fill=tk.X, pady=(0, 4))
        tk.Label(block, text=title, font=self._small_font, fg=TEXT_MUTED, bg=parent["bg"]).pack(side=tk.LEFT)
        lbl = tk.Label(block, text="—", font=self._small_btn_font, fg=TEXT, bg=parent["bg"])
        lbl.pack(side=tk.RIGHT)
        return lbl

    def _build_arduino_card(self, parent: tk.Frame) -> None:
        tk.Label(
            parent,
            text="Conexión con Arduino",
            font=self._section_font,
            fg=TEXT,
            bg=parent["bg"],
        ).pack(anchor=tk.W)

        tk.Label(
            parent,
            text="Conecta el Arduino por USB y selecciona su puerto serial.",
            font=self._small_font,
            fg=TEXT_MUTED,
            bg=parent["bg"],
            wraplength=900,
            justify=tk.LEFT,
        ).pack(anchor=tk.W, pady=(6, 10))

        port_row = tk.Frame(parent, bg=parent["bg"])
        port_row.pack(fill=tk.X, pady=(0, 8))

        tk.Label(
            port_row,
            text="Puerto serial",
            font=self._label_font,
            fg=TEXT_MUTED,
            bg=parent["bg"],
        ).pack(anchor=tk.W, pady=(0, 6))

        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Dark.TCombobox",
            fieldbackground=BG,
            background=BG,
            foreground=TEXT,
            arrowcolor=TEXT_MUTED,
            bordercolor=BORDER,
            lightcolor=BORDER,
            darkcolor=BORDER,
        )
        style.map(
            "Dark.TCombobox",
            fieldbackground=[("readonly", BG), ("disabled", CARD_ALT)],
            foreground=[("readonly", TEXT), ("disabled", TEXT_MUTED)],
        )

        self._port_combo = ttk.Combobox(
            port_row,
            textvariable=self._port_var,
            state="readonly",
            font=self._small_font,
            style="Dark.TCombobox",
        )
        self._port_combo.pack(fill=tk.X)

        self._no_ports_label = tk.Label(
            parent,
            text="No hay puertos seriales disponibles. Conecta el Arduino y pulsa «Actualizar puertos».",
            font=self._small_font,
            fg=TEXT_MUTED,
            bg=parent["bg"],
            wraplength=900,
            justify=tk.LEFT,
        )

        self._arduino_btn_row = tk.Frame(parent, bg=parent["bg"])
        self._arduino_btn_row.pack(fill=tk.X, pady=(10, 0))

        self._btn_refresh_ports = FlatButton(
            self._arduino_btn_row,
            text="Actualizar puertos",
            command=self._refresh_serial_ports,
            bg=CARD_ALT,
            hover_bg=BORDER,
            font=self._small_btn_font,
            padx=10,
            pady=10,
        )
        self._btn_refresh_ports.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 6))

        self._btn_connect = FlatButton(
            self._arduino_btn_row,
            text="Conectar Arduino",
            command=self._connect_arduino,
            bg=BLUE,
            hover_bg=BLUE_DIM,
            font=self._small_btn_font,
            padx=10,
            pady=10,
        )
        self._btn_connect.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=6)

        self._btn_disconnect = FlatButton(
            self._arduino_btn_row,
            text="Desconectar",
            command=self._disconnect_arduino,
            bg=CARD_ALT,
            hover_bg=RED_DIM,
            font=self._small_btn_font,
            padx=10,
            pady=10,
        )
        self._btn_disconnect.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(6, 0))

        conn_summary = tk.Frame(parent, bg=parent["bg"])
        conn_summary.pack(fill=tk.X, pady=(12, 0))

        conn_row = tk.Frame(conn_summary, bg=parent["bg"])
        conn_row.pack(anchor=tk.W)

        self._conn_dot = tk.Label(conn_row, text="●", font=self._status_font, fg=GRAY_OFF, bg=parent["bg"])
        self._conn_dot.pack(side=tk.LEFT, padx=(0, 8))

        self._arduino_status_label = tk.Label(
            conn_row,
            text="Sin conectar",
            font=self._small_btn_font,
            fg=GRAY_OFF,
            bg=parent["bg"],
        )
        self._arduino_status_label.pack(side=tk.LEFT)

        self._conn_port_label = tk.Label(
            conn_summary,
            text="Puerto: no seleccionado",
            font=self._small_font,
            fg=TEXT_MUTED,
            bg=parent["bg"],
            wraplength=900,
            justify=tk.LEFT,
        )
        self._conn_port_label.pack(anchor=tk.W, pady=(4, 0))

    def _build_maquette_map(self, parent: tk.Frame) -> None:
        head = tk.Frame(parent, bg=parent["bg"])
        head.pack(fill=tk.X, pady=(0, 8))

        titles = tk.Frame(head, bg=parent["bg"])
        titles.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Label(
            titles,
            text="Gemelo digital en vivo",
            font=self._section_font,
            fg=TEXT,
            bg=parent["bg"],
            anchor=tk.W,
        ).pack(anchor=tk.W)
        self._twin_subtitle_label = tk.Label(
            titles,
            text="Arrastra para girar · Desliza o pellizca para acercar",
            font=self._small_font,
            fg=CYAN,
            bg=parent["bg"],
            anchor=tk.W,
            wraplength=520,
            justify=tk.LEFT,
        )
        self._twin_subtitle_label.pack(anchor=tk.W, pady=(2, 0))

        self._btn_reset_twin_view = FlatButton(
            head,
            text="Restablecer vista",
            command=self._reset_twin_view,
            bg=CARD,
            hover_bg=BORDER,
            font=self._small_btn_font,
            padx=10,
            pady=8,
        )
        self._btn_reset_twin_view.pack(side=tk.RIGHT, anchor=tk.NE, padx=(6, 0))

        self._btn_zoom_in = FlatButton(
            head,
            text="+",
            command=lambda: self._change_camera_zoom(1.12),
            bg=CARD,
            hover_bg=BORDER,
            font=self._small_btn_font,
            padx=12,
            pady=8,
        )
        self._btn_zoom_in.pack(side=tk.RIGHT, anchor=tk.NE, padx=(6, 0))

        self._btn_zoom_out = FlatButton(
            head,
            text="−",
            command=lambda: self._change_camera_zoom(1 / 1.12),
            bg=CARD,
            hover_bg=BORDER,
            font=self._small_btn_font,
            padx=12,
            pady=8,
        )
        self._btn_zoom_out.pack(side=tk.RIGHT, anchor=tk.NE)

        self._maquette_canvas = tk.Canvas(
            parent,
            bg=MAP_BG,
            highlightthickness=1,
            highlightbackground=BORDER,
            height=560,
            bd=0,
            cursor="fleur",
            takefocus=True,
        )
        self._maquette_canvas.pack(fill=tk.BOTH, expand=True)
        self._maquette_canvas.bind("<Configure>", self._on_maquette_resize)
        self._maquette_canvas.bind("<Enter>", self._twin_canvas_focus)
        self._maquette_canvas.bind("<ButtonPress-1>", self._twin_drag_start)
        self._maquette_canvas.bind("<B1-Motion>", self._twin_drag_move)
        self._maquette_canvas.bind("<ButtonRelease-1>", self._twin_drag_end)
        self._maquette_canvas.bind("<Button-4>", self._twin_on_wheel)
        self._maquette_canvas.bind("<Button-5>", self._twin_on_wheel)
        self._maquette_canvas.bind("<Key-plus>", self._twin_key_zoom_in)
        self._maquette_canvas.bind("<Key-equal>", self._twin_key_zoom_in)
        self._maquette_canvas.bind("<Key-minus>", self._twin_key_zoom_out)
        self.bind_all("<MouseWheel>", self._twin_global_mousewheel, add="+")
        try:
            self._maquette_canvas.bind("<Magnify>", self._twin_on_magnify)
        except tk.TclError:
            # Tk 9.1 no registra el tipo de evento Magnify; el scroll sigue en MouseWheel.
            pass

    def _on_maquette_resize(self, event: tk.Event) -> None:
        if event.widget is self._maquette_canvas:
            self._draw_maquette_map()

    def _reset_twin_view(self) -> None:
        self._twin_yaw_deg = self._twin_yaw_default
        self._camera_zoom = 1.0
        self._draw_maquette_map()

    def _twin_canvas_focus(self, _event: tk.Event) -> None:
        self._maquette_canvas.focus_set()

    def _change_camera_zoom(self, factor: float) -> None:
        self._camera_zoom = max(0.8, min(2.8, self._camera_zoom * factor))
        self._draw_maquette_map()

    def _widget_is_twin_canvas(self, widget: Optional[tk.Misc]) -> bool:
        current: Optional[tk.Misc] = widget
        while current is not None:
            if current is self._maquette_canvas:
                return True
            current = getattr(current, "master", None)
        return False

    def _twin_global_mousewheel(self, event: tk.Event) -> Optional[str]:
        try:
            widget_under_pointer = self.winfo_containing(event.x_root, event.y_root)
        except tk.TclError:
            return None
        if not self._widget_is_twin_canvas(widget_under_pointer):
            return None
        delta = getattr(event, "delta", 0) or 0
        if delta > 0:
            self._change_camera_zoom(1.08)
            return "break"
        if delta < 0:
            self._change_camera_zoom(1 / 1.08)
            return "break"
        return None

    def _twin_on_wheel(self, event: tk.Event) -> None:
        num = getattr(event, "num", 0)
        if num == 4:
            self._change_camera_zoom(1.08)
        elif num == 5:
            self._change_camera_zoom(1 / 1.08)

    def _twin_key_zoom_in(self, _event: tk.Event) -> str:
        self._change_camera_zoom(1.12)
        return "break"

    def _twin_key_zoom_out(self, _event: tk.Event) -> str:
        self._change_camera_zoom(1 / 1.12)
        return "break"

    def _twin_on_magnify(self, event: tk.Event) -> None:
        raw = float(getattr(event, "delta", 0) or 0)
        if abs(raw) >= 1.5:
            step = raw / 80.0
        else:
            step = raw * 0.65
        factor = max(0.94, min(1.06, 1.0 + step))
        if factor != 1.0:
            self._change_camera_zoom(factor)

    def _twin_drag_start(self, event: tk.Event) -> None:
        self._maquette_canvas.focus_set()
        self._twin_drag_anchor_x = event.x

    def _twin_drag_move(self, event: tk.Event) -> None:
        if self._twin_drag_anchor_x is None:
            return
        delta = event.x - self._twin_drag_anchor_x
        self._twin_drag_anchor_x = event.x
        self._twin_yaw_deg += delta * 0.35
        lo = self._twin_yaw_default - 55.0
        hi = self._twin_yaw_default + 55.0
        self._twin_yaw_deg = max(lo, min(hi, self._twin_yaw_deg))
        self._draw_maquette_map()

    def _twin_drag_end(self, _event: tk.Event) -> None:
        self._twin_drag_anchor_x = None

    def _twin_project(
        self, mx: float, mz: float, my: float, cx: float, cy: float, scale: float
    ) -> tuple[float, float]:
        cxm, czm = TWIN_MX / 2, TWIN_MZ / 2
        dx = mx - cxm
        dz = mz - czm
        rad = math.radians(self._twin_yaw_deg)
        rx = dx * math.cos(rad) - dz * math.sin(rad)
        rz = dx * math.sin(rad) + dz * math.cos(rad)
        sx = cx + (rx - rz) * scale
        sy = cy + (rx + rz) * scale * 0.42 - my * scale * 0.62
        return sx, sy

    def _twin_poly(
        self,
        canvas: tk.Canvas,
        points: list[tuple[float, float, float]],
        cx: float,
        cy: float,
        scale: float,
        **kwargs,
    ) -> None:
        flat: list[float] = []
        for mx, mz, my in points:
            sx, sy = self._twin_project(mx, mz, my, cx, cy, scale)
            flat.extend((sx, sy))
        canvas.create_polygon(*flat, **kwargs)

    def _twin_line3(
        self,
        canvas: tk.Canvas,
        a: tuple[float, float, float],
        b: tuple[float, float, float],
        cx: float,
        cy: float,
        scale: float,
        **kwargs,
    ) -> None:
        p1 = self._twin_project(a[0], a[1], a[2], cx, cy, scale)
        p2 = self._twin_project(b[0], b[1], b[2], cx, cy, scale)
        canvas.create_line(p1[0], p1[1], p2[0], p2[1], **kwargs)

    def _twin_anim_wants_frames(self) -> bool:
        if self._proximity_kind == "NEAR":
            return True
        if self._map_buzzer_active_visual():
            return True
        if self._light_entry or self._light_living or self._light_bedroom:
            return True
        return False

    def _schedule_twin_animation(self) -> None:
        self._twin_animation_tick()

    def _twin_animation_tick(self) -> None:
        if not self.winfo_exists():
            return
        self._twin_anim_phase = (self._twin_anim_phase + 0.055) % 1.0
        if (
            getattr(self, "_current_view", "twin") == "twin"
            and hasattr(self, "_maquette_canvas")
            and self._twin_anim_wants_frames()
        ):
            self._draw_maquette_map()
        self._twin_anim_after_id = self.after(45, self._twin_animation_tick)

    def _cancel_twin_animation(self) -> None:
        if self._twin_anim_after_id is not None:
            try:
                self.after_cancel(self._twin_anim_after_id)
            except tk.TclError:
                pass
            self._twin_anim_after_id = None

    def _map_door_open_visual(self) -> bool:
        if self._arduino.is_connected and not self._door_state_confirmed:
            return False
        return self._door_open

    def _map_window_open_visual(self) -> bool:
        if self._arduino.is_connected and not self._window_state_confirmed:
            return False
        return self._window_open

    def _map_buzzer_active_visual(self) -> bool:
        if self._alarm_pending:
            return False
        return self._alarm_active

    def _twin_zone_poly(self, xz: list[tuple[float, float]], y: float = 0.0) -> list[tuple[float, float, float]]:
        return [(x, z, y) for x, z in xz]

    def _draw_maquette_map(self) -> None:
        canvas = self._maquette_canvas
        canvas.delete("all")
        w = max(canvas.winfo_width(), 520)
        h = max(canvas.winfo_height(), 400)
        zoom = self._camera_zoom
        exterior = zoom < 1.35
        fading = 1.35 <= zoom < 1.65
        interior = zoom >= 1.65
        base = min((w - 36) / 52.0, (h - 48) / 42.0)
        scale = base * zoom
        cx, cy = w / 2.0, h * 0.58
        wall = 8.0
        peak = 15.5
        ridge_z = 12.5
        phase = self._twin_anim_phase
        holo = "#38BDF8"
        wall_warm = "#4A3B30"
        wall_shade = "#332820"
        eave = 0.7

        def quad(pts, **kwargs) -> None:
            self._twin_poly(canvas, pts, cx, cy, scale, **kwargs)

        def floor(xz, fill: str) -> None:
            quad([(x, z, 0) for x, z in xz], fill=fill, outline="")

        floor([(0, 0), (9, 0), (9, 25), (0, 25)], "#2A2612" if self._light_entry else "#1A140F")
        floor([(9, 0), (30, 0), (30, 8), (9, 8)], "#16120E")
        floor([(9, 8), (22, 8), (22, 25), (9, 25)], "#2A1518" if self._light_living else "#1A140F")
        floor([(22, 8), (30, 8), (30, 25), (22, 25)], "#142A18" if self._light_bedroom else "#1A140F")
        floor([(30, 0), (35, 0), (35, 25), (30, 25)], "#14110E")

        def wall_face(a, b, c, d, fill: str) -> None:
            quad([a, b, c, d], fill=fill, outline=holo, width=1)

        if interior:
            wall_face((0, 25, 0), (35, 25, 0), (35, 25, wall), (0, 25, wall), wall_shade)
            wall_face((0, 0, 0), (0, 25, 0), (0, 25, wall), (0, 0, wall), wall_warm)
            wall_face((35, 0, 0), (35, 25, 0), (35, 25, wall), (35, 0, wall), wall_shade)
            for a, b in (
                ((9, 8, 0), (9, 25, 0)),
                ((22, 8, 0), (22, 25, 0)),
                ((30, 0, 0), (30, 25, 0)),
                ((9, 8, 0), (30, 8, 0)),
            ):
                wall_face(a, b, (b[0], b[1], wall * 0.72), (a[0], a[1], wall * 0.72), "#3D3128")
        else:
            wall_face((0, 0, 0), (35, 0, 0), (35, 0, wall), (0, 0, wall), wall_warm)
            wall_face((35, 0, 0), (35, 25, 0), (35, 25, wall), (35, 0, wall), wall_shade)
            wall_face((0, 25, 0), (35, 25, 0), (35, 25, wall), (0, 25, wall), "#2A211B")
            wall_face((0, 0, 0), (0, 25, 0), (0, 25, wall), (0, 0, wall), "#3F332A")

        door_open = self._map_door_open_visual()
        door = (
            [(3.2, 0, 0.2), (3.2, 0, 5.6), (1.4, 2.2, 5.2), (1.4, 2.2, 0.4)]
            if door_open
            else [(3.2, 0, 0.2), (7.2, 0, 0.2), (7.2, 0, 5.6), (3.2, 0, 5.6)]
        )
        quad(door, fill=DOOR_WOOD if door_open else "#5C3A22", outline="#C4A484", width=1)
        if not self._servos_operational:
            dx, dy = self._twin_project(7.6, 0.3, 5.8, cx, cy, scale)
            canvas.create_oval(dx - 3, dy - 3, dx + 3, dy + 3, fill=AMBER, outline="")

        win_open = self._map_window_open_visual()
        win_pts = (
            [(35, 8, 1.6), (35, 8, 5.2), (33.2, 9.4, 4.8), (33.2, 16.2, 1.8)]
            if win_open
            else [(35, 8, 1.6), (35, 8, 5.2), (35, 17, 5.2), (35, 17, 1.6)]
        )
        quad(win_pts, fill=CYAN if win_open else "#16324A", outline=holo, width=1)
        if not self._servos_operational:
            wx, wy = self._twin_project(34.6, 17.4, 5.4, cx, cy, scale)
            canvas.create_oval(wx - 3, wy - 3, wx + 3, wy + 3, fill=AMBER, outline="")

        lcd = [(9.4, 0, 1.4), (13.6, 0, 1.4), (13.6, 0, 3.4), (9.4, 0, 3.4)]
        quad(lcd, fill="#0B3A5B", outline=holo, width=1)
        lx, ly = self._twin_project(11.5, 0, 2.4, cx, cy, scale)
        if self._distance_cm is not None:
            canvas.create_text(lx, ly, text=f"{self._distance_cm:.1f}", fill="#7DD3FC", font=self._small_font)

        ux, uy = self._twin_project(5.2, 0.4, wall + 0.35, cx, cy, scale)
        if self._proximity_kind == "NEAR":
            for i in range(3):
                r = 7 + ((phase + i / 3) % 1.0) * 16
                canvas.create_oval(ux - r, uy - r, ux + r, uy + r, outline=VIOLET, width=1)
            canvas.create_oval(ux - 5, uy - 5, ux + 5, uy + 5, fill=VIOLET, outline="")
        elif self._proximity_kind == "FAR":
            canvas.create_oval(ux - 5, uy - 5, ux + 5, uy + 5, fill="#334155", outline="#64748B")
        else:
            canvas.create_oval(ux - 5, uy - 5, ux + 5, uy + 5, outline="#64748B", width=1)

        def led(mx: float, mz: float, on: bool, color: str, name: str) -> None:
            px, py = self._twin_project(mx, mz, wall * 0.55, cx, cy, scale)
            if on:
                glow = 8 + phase * 10
                canvas.create_oval(px - glow, py - glow * 0.55, px + glow, py + glow * 0.55, outline=color, width=1)
                canvas.create_oval(px - 6, py - 6, px + 6, py + 6, fill=color, outline="")
            else:
                canvas.create_oval(px - 5, py - 5, px + 5, py + 5, fill="#1C1917", outline="#44403C")
            if interior:
                canvas.create_text(px, py + 14, text=name, fill=TEXT_MUTED, font=self._small_font)

        led(4.5, 14, self._light_entry, LED_ENTRY_ON, "Entrada")
        led(15.5, 16, self._light_living, LED_LIVING_ON, "Sala")
        led(26, 16, self._light_bedroom, LED_BEDROOM_ON, "Hab.")

        if exterior and (self._light_entry or self._light_living or self._light_bedroom):
            gx, gy = self._twin_project(17.5, 0, 3.5, cx, cy, scale)
            canvas.create_oval(gx - 28, gy - 10, gx + 28, gy + 10, outline="#FDE68A", width=1)

        bx, by = self._twin_project(2.2, 3.0, 4.2, cx, cy, scale)
        if self._map_buzzer_active_visual():
            pr = 6 + phase * 9
            canvas.create_oval(bx - pr, by - pr, bx + pr, by + pr, outline=RED, width=2)
            canvas.create_oval(bx - 4, by - 4, bx + 4, by + 4, fill=RED, outline="")
        else:
            canvas.create_rectangle(bx - 3, by - 2, bx + 3, by + 2, outline="#57534E")

        if not interior:
            front_roof = [
                (-eave, -eave, wall),
                (35 + eave, -eave, wall),
                (35 + eave, ridge_z, peak),
                (-eave, ridge_z, peak),
            ]
            back_roof = [
                (-eave, 25 + eave, wall),
                (35 + eave, 25 + eave, wall),
                (35 + eave, ridge_z, peak),
                (-eave, ridge_z, peak),
            ]
            stipple = ""
            if fading:
                t = (zoom - 1.35) / 0.3
                stipple = "gray75" if t < 0.34 else "gray50" if t < 0.67 else "gray25"
            roof_kw = {"fill": "#5C4636", "outline": holo, "width": 1}
            if stipple:
                roof_kw["stipple"] = stipple
            quad(front_roof, **roof_kw)
            quad(back_roof, fill="#3F3128", outline=holo, width=1, **({"stipple": stipple} if stipple else {}))
            gable_l = [(0, 0, wall), (0, 25, wall), (0, ridge_z, peak)]
            gable_r = [(35, 0, wall), (35, 25, wall), (35, ridge_z, peak)]
            quad(gable_l, fill="#6B5344", outline=holo, width=1)
            quad(gable_r, fill="#6B5344", outline=holo, width=1)
            fx, fy = self._twin_project(30, 20, peak - 0.4, cx, cy, scale)
            canvas.create_oval(fx - 8, fy - 8, fx + 8, fy + 8, outline="#78716C", width=1)
            canvas.create_line(fx - 5, fy, fx + 5, fy, fill="#78716C")
            canvas.create_line(fx, fy - 5, fx, fy + 5, fill="#78716C")

        if interior:
            quad([(11, 2, 0.25), (17, 2, 0.25), (17, 5.2, 0.7), (11, 5.2, 0.7)], fill="#1E293B", outline=BLUE_DIM, width=1)
            quad([(18, 2.2, 0.25), (23, 2.2, 0.25), (23, 5, 0.6), (18, 5, 0.6)], fill="#1C1917", outline="#57534E")
            quad([(24, 2.2, 0.25), (29, 2.2, 0.25), (29, 5, 0.6), (24, 5, 0.6)], fill="#1C1917", outline="#57534E")
            fx, fy = self._twin_project(31.5, 22, wall + 0.4, cx, cy, scale)
            canvas.create_oval(fx - 8, fy - 8, fx + 8, fy + 8, outline="#78716C")
            canvas.create_line(fx - 5, fy, fx + 5, fy, fill="#78716C")
            canvas.create_line(fx, fy - 5, fx, fy + 5, fill="#78716C")

        self._draw_twin_hud(canvas, w)

    def _draw_twin_hud(self, canvas: tk.Canvas, width: int) -> None:
        if self._distance_cm is None:
            dist = "—"
        else:
            dist = f"{self._distance_cm:.1f} cm"
        if self._proximity_kind == "NEAR":
            prox = "Cerca"
        elif self._proximity_kind == "FAR":
            prox = "Libre"
        else:
            prox = "—"
        conn = "Serial" if self._arduino.is_connected else "Sin Arduino"
        source = "Confirmado" if self._arduino.is_connected else "Demo"
        lines = (
            f"Distancia  {dist}",
            f"Proximidad  {prox}",
            f"Conexión  {conn}",
            f"Datos  {source}",
        )
        x = max(12, width - 168)
        y = 14
        canvas.create_rectangle(x - 8, 8, width - 10, 8 + 16 * len(lines) + 6, fill="#0B1220", outline="#1E3A5F")
        for i, line in enumerate(lines):
            canvas.create_text(x, y + i * 16, text=line, anchor=tk.NW, fill=TEXT_MUTED, font=self._small_font)

    def _refresh_twin_glance(self) -> None:
        self._refresh_maquette_map()

    def _refresh_maquette_legend(self) -> None:
        self._refresh_maquette_map()

    def _refresh_maquette_map(self) -> None:
        if hasattr(self, "_maquette_canvas"):
            self._draw_maquette_map()

    # —— Visualización ——

    def _refresh_all_displays(self) -> None:
        self._refresh_distance_display()
        self._refresh_proximity_display()
        self._refresh_energy_display()
        self._refresh_lights_display()
        self._refresh_access_display()
        self._refresh_activity_metrics()

    def _refresh_distance_display(self) -> None:
        if self._distance_cm is None:
            self._distance_label.configure(text="Sin lectura", fg=TEXT_MUTED)
            self._distance_dot.configure(fg=TEXT_MUTED)
        else:
            self._distance_label.configure(text=f"{self._distance_cm:.1f} cm", fg=BLUE)
            self._distance_dot.configure(fg=BLUE)
        self._refresh_twin_glance()
        self._refresh_maquette_map()

    def _refresh_proximity_display(self) -> None:
        if self._proximity_kind == "NEAR":
            text, color = "OBJETO CERCANO", AMBER
        elif self._proximity_kind == "FAR":
            text, color = "ÁREA LIBRE", GREEN
        else:
            text, color = "Sin lectura", TEXT_MUTED
        self._proximity_label.configure(text=text, fg=color)
        self._proximity_dot.configure(fg=color)
        self._refresh_twin_glance()
        self._refresh_maquette_map()

    def _refresh_energy_display(self) -> None:
        if self._energy is None:
            self._energy_label.configure(text="Sin lectura INA219", fg=TEXT_MUTED)
            self._energy_dot.configure(fg=TEXT_MUTED)
        else:
            v, i, p = self._energy
            self._energy_label.configure(
                text=f"{v:.2f} V · {i:.2f} A · {p:.2f} W",
                fg=GREEN,
            )
            self._energy_dot.configure(fg=GREEN)

    def _refresh_lights_display(self) -> None:
        states = {
            "entry": self._light_entry,
            "living": self._light_living,
            "bedroom": self._light_bedroom,
        }
        for key, on in states.items():
            lbl = self._light_labels[key]
            dot = self._light_dots[key]
            if key in self._light_pending:
                lbl.configure(text="Pendiente…", fg=AMBER)
                dot.configure(fg=AMBER)
            elif on:
                lbl.configure(text="ENCENDIDA", fg=GREEN)
                dot.configure(fg=GREEN)
            else:
                lbl.configure(text="APAGADA", fg=GRAY_OFF)
                dot.configure(fg=GRAY_OFF)
        self._refresh_maquette_map()

    def _refresh_servo_status_display(self) -> None:
        if self._servos_operational:
            self._servo_status_label.configure(text="Servos operativos", fg=GREEN)
        else:
            self._servo_status_label.configure(
                text="Pendiente de alimentación externa",
                fg=AMBER,
            )

    def _door_status_view(self) -> tuple[str, str]:
        if self._door_pending:
            return self._door_pending, AMBER
        if not self._arduino.is_connected:
            text = "ABIERTA" if self._door_open else "CERRADA"
            return text, AMBER if self._door_open else GREEN
        if not self._door_state_confirmed:
            return "—", TEXT_MUTED
        text = "ABIERTA" if self._door_open else "CERRADA"
        return text, AMBER if self._door_open else GREEN

    def _window_status_view(self) -> tuple[str, str]:
        if self._window_pending:
            return self._window_pending, AMBER
        if not self._arduino.is_connected:
            text = "ABIERTA" if self._window_open else "CERRADA"
            return text, AMBER if self._window_open else GREEN
        if not self._window_state_confirmed:
            return "—", TEXT_MUTED
        text = "ABIERTA" if self._window_open else "CERRADA"
        return text, AMBER if self._window_open else GREEN

    def _refresh_access_display(self) -> None:
        door_text, door_fg = self._door_status_view()
        win_text, win_fg = self._window_status_view()
        self._door_label.configure(text=door_text, fg=door_fg)
        self._window_label.configure(text=win_text, fg=win_fg)

        if self._alarm_pending:
            self._alarm_label.configure(text="Pendiente…", fg=AMBER)
        else:
            self._alarm_label.configure(
                text="ACTIVA" if self._alarm_active else "INACTIVA",
                fg=RED if self._alarm_active else TEXT_MUTED,
            )
        self._refresh_servo_status_display()
        self._refresh_maquette_map()

    def _refresh_activity_metrics(self) -> None:
        if self._last_distance_cm is None:
            self._activity_distance_label.configure(text="—")
        else:
            self._activity_distance_label.configure(text=f"{self._last_distance_cm:.1f} cm")
        self._near_count_label.configure(text=str(self._near_detection_count))
        self._last_action_label.configure(text=self._last_action)

    def _schedule_activity_tick(self) -> None:
        self._update_last_detection_ago()
        self.after(1000, self._schedule_activity_tick)

    def _update_last_detection_ago(self) -> None:
        if self._last_near_detection_at is None:
            self._last_detection_time_label.configure(text="--:--:--")
            self._last_detection_ago_label.configure(text="Sin detecciones en esta sesión")
            return
        self._last_detection_time_label.configure(
            text=self._last_near_detection_at.strftime("%H:%M:%S")
        )
        elapsed = int((datetime.now() - self._last_near_detection_at).total_seconds())
        self._last_detection_ago_label.configure(text=f"hace {elapsed} s")

    def _set_last_action(self, action: str) -> None:
        self._last_action = action
        self._last_action_label.configure(text=action)

    def _record_near_detection(self) -> None:
        self._near_detection_count += 1
        self._last_near_detection_at = datetime.now()
        self._set_last_action("Sensor ultrasónico")
        self._refresh_activity_metrics()
        self._update_last_detection_ago()

    # —— Comandos y demostración ——

    def _command_map_light(self, key: str, on: bool) -> str:
        table = {
            ("entry", True): "ENTRY_ON",
            ("entry", False): "ENTRY_OFF",
            ("living", True): "LIVING_ON",
            ("living", False): "LIVING_OFF",
            ("bedroom", True): "BEDROOM_ON",
            ("bedroom", False): "BEDROOM_OFF",
        }
        return table[(key, on)]

    def _send_arduino_command(self, command: str) -> bool:
        if self._arduino.send_command(command):
            self._log_event(f"Comando enviado a Arduino: {command}.")
            return True
        self._log_event(f"Error: no se pudo enviar {command} a Arduino.")
        return False

    def _apply_light_state(self, key: str, on: bool) -> None:
        if key == "entry":
            self._light_entry = on
        elif key == "living":
            self._light_living = on
        else:
            self._light_bedroom = on
        self._light_pending.discard(key)
        self._refresh_lights_display()

    def _mark_servos_operational(self) -> None:
        self._servos_operational = True
        self._refresh_servo_status_display()

    def _light_on(self, key: str) -> None:
        self._set_last_action("Control manual")
        name = {"entry": "Entrada", "living": "Sala", "bedroom": "Habitación"}[key]
        command = self._command_map_light(key, True)
        if self._arduino.is_connected:
            self._light_pending.add(key)
            self._refresh_lights_display()
            self._send_arduino_command(command)
            return
        self._apply_light_state(key, True)
        self._log_event(f"Modo demostración: LED {name} encendido localmente (Arduino no conectado).")

    def _light_off(self, key: str) -> None:
        self._set_last_action("Control manual")
        name = {"entry": "Entrada", "living": "Sala", "bedroom": "Habitación"}[key]
        command = self._command_map_light(key, False)
        if self._arduino.is_connected:
            self._light_pending.add(key)
            self._refresh_lights_display()
            self._send_arduino_command(command)
            return
        self._apply_light_state(key, False)
        self._log_event(f"Modo demostración: LED {name} apagado localmente (Arduino no conectado).")

    def _door_open_cmd(self) -> None:
        self._set_last_action("Control manual")
        if self._arduino.is_connected:
            self._door_pending = "Orden enviada; esperando confirmación del Arduino..."
            self._refresh_access_display()
            if not self._send_arduino_command("DOOR_OPEN"):
                self._door_pending = None
                self._refresh_access_display()
            return
        self._door_open = True
        self._door_state_confirmed = True
        self._refresh_access_display()
        self._log_event("Modo demostración: puerta abierta localmente (Arduino no conectado).")

    def _door_close_cmd(self) -> None:
        self._set_last_action("Control manual")
        if self._arduino.is_connected:
            self._door_pending = "Orden enviada; esperando confirmación del Arduino..."
            self._refresh_access_display()
            if not self._send_arduino_command("DOOR_CLOSE"):
                self._door_pending = None
                self._refresh_access_display()
            return
        self._door_open = False
        self._door_state_confirmed = True
        self._refresh_access_display()
        self._log_event("Modo demostración: puerta cerrada localmente (Arduino no conectado).")

    def _window_open_cmd(self) -> None:
        self._set_last_action("Control manual")
        if self._arduino.is_connected:
            self._window_pending = "Orden enviada; esperando confirmación del Arduino..."
            self._refresh_access_display()
            if not self._send_arduino_command("WINDOW_OPEN"):
                self._window_pending = None
                self._refresh_access_display()
            return
        self._window_open = True
        self._window_state_confirmed = True
        self._refresh_access_display()
        self._log_event("Modo demostración: ventana abierta localmente (Arduino no conectado).")

    def _window_close_cmd(self) -> None:
        self._set_last_action("Control manual")
        if self._arduino.is_connected:
            self._window_pending = "Orden enviada; esperando confirmación del Arduino..."
            self._refresh_access_display()
            if not self._send_arduino_command("WINDOW_CLOSE"):
                self._window_pending = None
                self._refresh_access_display()
            return
        self._window_open = False
        self._window_state_confirmed = True
        self._refresh_access_display()
        self._log_event("Modo demostración: ventana cerrada localmente (Arduino no conectado).")

    def _alarm_on_cmd(self) -> None:
        self._set_last_action("Control manual")
        if self._arduino.is_connected:
            self._alarm_pending = True
            self._refresh_access_display()
            if not self._send_arduino_command("ALARM_ON"):
                self._alarm_pending = False
                self._refresh_access_display()
            return
        self._alarm_active = True
        self._refresh_access_display()
        self._log_event("Modo demostración: alarma activada localmente (Arduino no conectado).")

    def _alarm_off_cmd(self) -> None:
        self._set_last_action("Control manual")
        if self._arduino.is_connected:
            self._alarm_pending = True
            self._refresh_access_display()
            if not self._send_arduino_command("ALARM_OFF"):
                self._alarm_pending = False
                self._refresh_access_display()
            return
        self._alarm_active = False
        self._refresh_access_display()
        self._log_event("Modo demostración: alarma desactivada localmente (Arduino no conectado).")

    # —— Serial ——

    def _reset_live_metrics(self) -> None:
        self._distance_cm = None
        self._proximity_kind = None
        self._energy = None
        self._door_pending = None
        self._window_pending = None
        self._light_pending.clear()
        self._alarm_pending = False
        self._door_state_confirmed = False
        self._window_state_confirmed = False
        self._servos_operational = False
        self._refresh_distance_display()
        self._refresh_proximity_display()
        self._refresh_energy_display()
        self._refresh_lights_display()
        self._refresh_access_display()

    def _handle_serial_line(self, line: str) -> None:
        if line == "READY":
            self._log_event("Arduino: READY.")
            return

        if line.startswith("DISTANCE:"):
            try:
                value = float(line.split(":", 1)[1])
            except ValueError:
                self._log_event(f"Mensaje serial (distancia inválida): {line}")
                return
            self._distance_cm = value
            self._last_distance_cm = value
            self._refresh_distance_display()
            self._refresh_activity_metrics()
            self._log_event(f"Arduino: distancia {value:.1f} cm.")
            return

        if line == "PROXIMITY:NEAR":
            self._proximity_kind = "NEAR"
            self._record_near_detection()
            self._refresh_proximity_display()
            self._log_event("Arduino: PROXIMITY NEAR.")
            return

        if line == "PROXIMITY:FAR":
            self._proximity_kind = "FAR"
            self._refresh_proximity_display()
            self._log_event("Arduino: PROXIMITY FAR.")
            return

        light_map = {
            "LIGHT:ENTRY:ON": ("entry", True),
            "LIGHT:ENTRY:OFF": ("entry", False),
            "LIGHT:LIVING:ON": ("living", True),
            "LIGHT:LIVING:OFF": ("living", False),
            "LIGHT:BEDROOM:ON": ("bedroom", True),
            "LIGHT:BEDROOM:OFF": ("bedroom", False),
        }
        if line in light_map:
            key, on = light_map[line]
            self._apply_light_state(key, on)
            self._log_event(f"Arduino confirmó: {line}.")
            return

        if line == "SERVO:POWER_REQUIRED":
            self._door_pending = None
            self._window_pending = None
            self._servos_operational = False
            self._refresh_access_display()
            self._log_event(
                "Movimiento no ejecutado: los servos requieren alimentación externa de 5 V."
            )
            return

        if line == "DOOR:OPEN":
            self._door_pending = None
            self._door_open = True
            self._door_state_confirmed = True
            self._mark_servos_operational()
            self._refresh_access_display()
            self._log_event("Arduino confirmó: puerta ABIERTA.")
            return
        if line == "DOOR:CLOSED":
            self._door_pending = None
            self._door_open = False
            self._door_state_confirmed = True
            self._mark_servos_operational()
            self._refresh_access_display()
            self._log_event("Arduino confirmó: puerta CERRADA.")
            return
        if line == "WINDOW:OPEN":
            self._window_pending = None
            self._window_open = True
            self._window_state_confirmed = True
            self._mark_servos_operational()
            self._refresh_access_display()
            self._log_event("Arduino confirmó: ventana ABIERTA.")
            return
        if line == "WINDOW:CLOSED":
            self._window_pending = None
            self._window_open = False
            self._window_state_confirmed = True
            self._mark_servos_operational()
            self._refresh_access_display()
            self._log_event("Arduino confirmó: ventana CERRADA.")
            return
        if line == "BUZZER:ON":
            self._alarm_pending = False
            self._alarm_active = True
            self._refresh_access_display()
            self._log_event("Arduino confirmó: alarma ACTIVA.")
            return
        if line == "BUZZER:OFF":
            self._alarm_pending = False
            self._alarm_active = False
            self._refresh_access_display()
            self._log_event("Arduino confirmó: alarma INACTIVA.")
            return

        if line == "ERROR:UNKNOWN_COMMAND":
            self._log_event("Arduino rechazó un comando desconocido (ERROR:UNKNOWN_COMMAND).")
            return

        match = _ENERGY_RE.match(line)
        if match:
            v, i, p = float(match.group(1)), float(match.group(2)), float(match.group(3))
            self._energy = (v, i, p)
            self._refresh_energy_display()
            self._log_event(f"Arduino: energía V={v:.2f} I={i:.2f} P={p:.2f}.")
            return

        self._log_event(f"Arduino (mensaje): {line}")

    def _update_system_chrome(self) -> None:
        if self._connection_error:
            self._badge_frame.configure(bg="#3F1D1D")
            self._badge_label.configure(text="Error de conexión", fg=RED, bg="#3F1D1D")
        elif self._arduino.is_connected:
            self._badge_frame.configure(bg="#14301F")
            self._badge_label.configure(text="Sistema conectado", fg=GREEN, bg="#14301F")
        else:
            self._badge_frame.configure(bg=GRAY_BG)
            self._badge_label.configure(text="Modo demostración", fg=TEXT_MUTED, bg=GRAY_BG)

        if self._arduino.is_connected:
            if hasattr(self, "_log_comm_label"):
                self._log_comm_label.configure(text="Estado de comunicación: activa", fg=GREEN)
            self._lighting_mode_label.configure(
                text="Arduino conectado: comandos en tiempo real.",
                fg=GREEN,
            )
            self._access_mode_label.configure(
                text="Arduino conectado: servos y buzzer por serial.",
                fg=GREEN,
            )
        else:
            if hasattr(self, "_log_comm_label"):
                self._log_comm_label.configure(text="Estado de comunicación: en espera", fg=TEXT_MUTED)
            self._lighting_mode_label.configure(
                text="Modo demostración: cambios locales en LEDs.",
                fg=TEXT_MUTED,
            )
            self._access_mode_label.configure(
                text="Modo demostración: estado local de puerta, ventana y alarma.",
                fg=TEXT_MUTED,
            )

        if self._arduino.is_connected:
            port = self._arduino.port_name or "?"
            self._conn_port_label.configure(text=f"Puerto: {port}")
        else:
            selected = self._port_var.get().strip()
            self._conn_port_label.configure(
                text=f"Puerto: {selected}" if selected else "Puerto: no seleccionado"
            )
        self._refresh_maquette_legend()
        self._refresh_maquette_map()

    def _refresh_serial_ports(self) -> None:
        ports = list_serial_ports()
        self._port_combo["values"] = ports

        if ports:
            self._no_ports_label.pack_forget()
            if self._port_var.get() not in ports:
                self._port_var.set(ports[0])
            self._port_combo.configure(state="readonly")
            self._log_event(f"Puertos actualizados: {len(ports)} detectado(s).")
        else:
            self._port_var.set("")
            self._port_combo.configure(state="disabled")
            self._no_ports_label.pack(anchor=tk.W, pady=(0, 8), before=self._arduino_btn_row)
            self._log_event("Puertos actualizados: no hay puertos seriales disponibles.")

        self._update_arduino_connection_controls()
        self._update_system_chrome()

    def _update_arduino_status(self) -> None:
        if self._arduino.is_connected:
            self._arduino_status_label.configure(text="Conectado", fg=GREEN)
            self._conn_dot.configure(fg=GREEN)
        else:
            self._arduino_status_label.configure(text="Sin conectar", fg=GRAY_OFF)
            self._conn_dot.configure(fg=GRAY_OFF)
        self._update_system_chrome()

    def _update_arduino_connection_controls(self) -> None:
        connected = self._arduino.is_connected
        has_ports = bool(self._port_combo["values"])

        if connected:
            self._port_combo.configure(state="disabled")
            self._btn_connect.configure(state=tk.DISABLED)
            self._btn_disconnect.configure(state=tk.NORMAL)
        else:
            self._btn_connect.configure(state=tk.NORMAL if has_ports else tk.DISABLED)
            self._btn_disconnect.configure(state=tk.DISABLED)
            if has_ports:
                self._port_combo.configure(state="readonly")

        self._update_system_chrome()

    def _connect_arduino(self) -> None:
        port = self._port_var.get().strip()
        if not port:
            self._log_event("Error de conexión: selecciona un puerto serial.")
            return
        if self._arduino.is_connected:
            self._log_event("Arduino ya estaba conectado.")
            return
        try:
            self._arduino.connect(port)
        except SerialException as exc:
            self._connection_error = True
            self._log_event(f"Error de conexión: {exc}")
            self._update_arduino_status()
            self._update_arduino_connection_controls()
            return

        self._connection_error = False
        self._update_arduino_status()
        self._update_arduino_connection_controls()
        self._log_event(f"Arduino conectado en {port}.")
        if self._arduino.send_command("STATUS"):
            self._log_event("Comando enviado a Arduino: STATUS.")
        else:
            self._log_event("Error: no se pudo enviar STATUS a Arduino.")

    def _disconnect_arduino(self) -> None:
        if not self._arduino.is_connected:
            self._log_event("Arduino no estaba conectado.")
            self._update_arduino_connection_controls()
            return
        port = self._arduino.port_name
        self._arduino.disconnect()
        self._connection_error = False
        self._reset_live_metrics()
        self._update_arduino_status()
        self._update_arduino_connection_controls()
        self._log_event(f"Arduino desconectado ({port}).")

    def _schedule_serial_poll(self) -> None:
        self._poll_serial()
        self.after(SERIAL_POLL_MS, self._schedule_serial_poll)

    def _poll_serial(self) -> None:
        if not self._arduino.is_connected:
            return
        for line in self._arduino.read_available_lines():
            self._handle_serial_line(line)

    def _on_close(self) -> None:
        self._cancel_twin_animation()
        if self._arduino.is_connected:
            self._arduino.disconnect()
        self.destroy()

    def _log_event(self, message: str) -> None:
        now = datetime.now()
        self._session_events.append((now, message))
        stamp = now.strftime("%H:%M:%S")
        line = f"[{stamp}] {message}\n"
        self._log_text.configure(state=tk.NORMAL)
        self._log_text.insert(tk.END, line)
        self._log_text.see(tk.END)
        self._log_text.configure(state=tk.DISABLED)

    def _export_session_log(self) -> None:
        registros_dir = self._project_dir / "registros"
        filename = f"registro_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        filepath = registros_dir / filename
        try:
            registros_dir.mkdir(parents=True, exist_ok=True)
            with filepath.open("w", newline="", encoding="utf-8-sig") as csv_file:
                writer = csv.writer(csv_file)
                writer.writerow(["Fecha y hora", "Evento"])
                for when, event_text in self._session_events:
                    writer.writerow([when.strftime("%Y-%m-%d %H:%M:%S"), event_text])
        except OSError as exc:
            self._log_event(f"Error al exportar registro: {exc}")
            return
        self._log_event(f"Registro exportado: {filename}")


def main() -> None:
    app = SmartEnergyDashboard()
    app.mainloop()


if __name__ == "__main__":
    main()
