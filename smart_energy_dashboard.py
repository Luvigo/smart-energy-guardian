#!/usr/bin/env python3
"""Smart Energy Guardian — panel local de control."""

import csv
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import font as tkfont
from tkinter import ttk
from typing import Callable, Optional

from serial import SerialException

from arduino_serial import ArduinoSerialConnection, list_serial_ports

# Paleta y dimensiones
WINDOW_WIDTH = 1120
WINDOW_HEIGHT = 720
MIN_WIDTH = 960
MIN_HEIGHT = 650
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
BORDER = "#263652"
GRAY_OFF = TEXT_MUTED
GRAY_BG = "#1B2940"
SERIAL_POLL_MS = 200


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
        self.title("Smart Energy Guardian")
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.minsize(MIN_WIDTH, MIN_HEIGHT)
        self.configure(bg=BG)
        self.resizable(True, True)

        self._charge_state = "APAGADA"
        self._arduino = ArduinoSerialConnection()
        self._port_var = tk.StringVar(value="")
        self._sensor_display = "Pendiente de conexión"
        self._session_events: list[tuple[datetime, str]] = []
        self._project_dir = Path(__file__).resolve().parent
        self._connection_error = False
        self._pir_detection_count = 0
        self._charge_activation_count = 0
        self._last_pir_detection_at: Optional[datetime] = None
        self._last_action = "—"

        self._build_ui()
        self._refresh_charge_display()
        self._refresh_serial_ports()
        self._update_arduino_status()
        self._update_system_chrome()
        self._log_event("Sistema iniciado. Carga en estado APAGADA.")

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._schedule_serial_poll()
        self._schedule_activity_tick()
        self.bind("<Configure>", self._on_window_resize)

    def _on_window_resize(self, event: tk.Event) -> None:
        if event.widget is not self:
            return
        wrap = max(160, (event.width - 140) // 4 - 20)
        for label in (
            self._charge_context_label,
            self._sensor_label,
            self._arduino_status_label,
            self._conn_port_label,
            self._control_mode_label,
            self._activity_note_label,
        ):
            label.configure(wraplength=wrap)
        self._activity_note_label.configure(wraplength=max(280, event.width - 120))

    def _build_ui(self) -> None:
        self._title_font = tkfont.Font(family="Helvetica", size=22, weight="bold")
        self._subtitle_font = tkfont.Font(family="Helvetica", size=11)
        self._section_font = tkfont.Font(family="Helvetica", size=13, weight="bold")
        self._label_font = tkfont.Font(family="Helvetica", size=11)
        self._status_font = tkfont.Font(family="Helvetica", size=18, weight="bold")
        self._small_font = tkfont.Font(family="Helvetica", size=10)
        self._btn_font = tkfont.Font(family="Helvetica", size=12, weight="bold")
        self._small_btn_font = tkfont.Font(family="Helvetica", size=10, weight="bold")
        self._mono_font = tkfont.Font(family="Menlo", size=10)
        self._metric_num_font = tkfont.Font(family="Helvetica", size=28, weight="bold")

        root = tk.Frame(self, bg=BG)
        root.pack(fill=tk.BOTH, expand=True, padx=22, pady=18)

        # —— Encabezado ——
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
            text="⚡",
            font=tkfont.Font(size=18),
            fg=TEXT,
            bg=BLUE,
        ).pack()

        titles = tk.Frame(brand_row, bg=BG)
        titles.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Label(
            titles,
            text="SMART ENERGY GUARDIAN",
            font=self._title_font,
            fg=TEXT,
            bg=BG,
            anchor=tk.W,
        ).pack(anchor=tk.W)
        tk.Label(
            titles,
            text="Panel de control y monitoreo de la maqueta",
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

        # —— Tarjetas de estado (fila 1) ——
        metrics = tk.Frame(root, bg=BG)
        metrics.pack(fill=tk.X, pady=(0, 12))
        for col in range(4):
            metrics.columnconfigure(col, weight=1, uniform="metrics")

        charge_outer, charge_inner = _card(metrics, CARD_ALT)
        charge_outer.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        self._build_metric_charge_card(charge_inner)

        sensor_outer, sensor_inner = _card(metrics, CARD_ALT)
        sensor_outer.grid(row=0, column=1, sticky="nsew", padx=6)
        self._build_metric_sensor_card(sensor_inner)

        pir_count_outer, pir_count_inner = _card(metrics, CARD_ALT)
        pir_count_outer.grid(row=0, column=2, sticky="nsew", padx=6)
        self._build_metric_pir_count_card(pir_count_inner)

        activation_outer, activation_inner = _card(metrics, CARD_ALT)
        activation_outer.grid(row=0, column=3, sticky="nsew", padx=(6, 0))
        self._build_metric_activation_count_card(activation_inner)

        activity_outer, activity_inner = _card(root, CARD)
        activity_outer.pack(fill=tk.X, pady=(0, 12))
        self._build_activity_card(activity_inner)

        # —— Fila central (2 columnas) ——
        middle = tk.Frame(root, bg=BG)
        middle.pack(fill=tk.BOTH, expand=True, pady=(0, 16))
        middle.columnconfigure(0, weight=1, uniform="middle")
        middle.columnconfigure(1, weight=1, uniform="middle")
        middle.rowconfigure(0, weight=1)

        control_outer, control_inner = _card(middle, CARD)
        control_outer.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self._build_control_card(control_inner)

        arduino_outer, arduino_inner = _card(middle, CARD)
        arduino_outer.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        self._build_arduino_card(arduino_inner)

        # —— Registro de eventos ——
        log_outer, log_inner = _card(root, CARD)
        log_outer.pack(fill=tk.BOTH, expand=True, pady=(0, 12))

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
            height=8,
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

        # —— Pie de página ——
        footer = tk.Frame(root, bg=BG)
        footer.pack(fill=tk.X)

        tk.Label(
            footer,
            text="Smart Energy Guardian · Proyecto académico",
            font=self._small_font,
            fg=TEXT_MUTED,
            bg=BG,
        ).pack(side=tk.LEFT)

        self._footer_comm_label = tk.Label(
            footer,
            text="Estado de comunicación: en espera",
            font=self._small_font,
            fg=TEXT_MUTED,
            bg=BG,
        )
        self._footer_comm_label.pack(side=tk.RIGHT)

    def _build_metric_charge_card(self, parent: tk.Frame) -> None:
        tk.Label(
            parent,
            text="Estado de carga",
            font=self._label_font,
            fg=TEXT_MUTED,
            bg=parent["bg"],
        ).pack(anchor=tk.W)

        row = tk.Frame(parent, bg=parent["bg"])
        row.pack(anchor=tk.W, pady=(10, 4))

        self._charge_dot = tk.Label(row, text="●", font=self._status_font, fg=GRAY_OFF, bg=parent["bg"])
        self._charge_dot.pack(side=tk.LEFT, padx=(0, 8))

        self._charge_label = tk.Label(
            row,
            text="APAGADA",
            font=self._status_font,
            fg=GRAY_OFF,
            bg=parent["bg"],
        )
        self._charge_label.pack(side=tk.LEFT)

        self._charge_context_label = tk.Label(
            parent,
            text="La carga está detenida.",
            font=self._small_font,
            fg=TEXT_MUTED,
            bg=parent["bg"],
            wraplength=280,
            justify=tk.LEFT,
        )
        self._charge_context_label.pack(anchor=tk.W, pady=(6, 0))

    def _build_metric_sensor_card(self, parent: tk.Frame) -> None:
        tk.Label(
            parent,
            text="Sensor PIR",
            font=self._label_font,
            fg=TEXT_MUTED,
            bg=parent["bg"],
        ).pack(anchor=tk.W)

        row = tk.Frame(parent, bg=parent["bg"])
        row.pack(anchor=tk.W, pady=(10, 4))

        self._sensor_dot = tk.Label(row, text="●", font=self._status_font, fg=TEXT_MUTED, bg=parent["bg"])
        self._sensor_dot.pack(side=tk.LEFT, padx=(0, 8))

        self._sensor_label = tk.Label(
            row,
            text="Pendiente de conexión",
            font=tkfont.Font(family="Helvetica", size=14, weight="bold"),
            fg=TEXT_MUTED,
            bg=parent["bg"],
            wraplength=280,
            justify=tk.LEFT,
        )
        self._sensor_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        tk.Label(
            parent,
            text="Lectura en vivo al conectar el Arduino.",
            font=self._small_font,
            fg=TEXT_MUTED,
            bg=parent["bg"],
            wraplength=280,
            justify=tk.LEFT,
        ).pack(anchor=tk.W, pady=(6, 0))

    def _build_metric_pir_count_card(self, parent: tk.Frame) -> None:
        tk.Label(
            parent,
            text="Detecciones PIR",
            font=self._label_font,
            fg=TEXT_MUTED,
            bg=parent["bg"],
        ).pack(anchor=tk.W)
        self._pir_count_label = tk.Label(
            parent,
            text="0",
            font=self._metric_num_font,
            fg=BLUE,
            bg=parent["bg"],
        )
        self._pir_count_label.pack(anchor=tk.W, pady=(8, 2))
        tk.Label(
            parent,
            text="Solo eventos reales del sensor.",
            font=self._small_font,
            fg=TEXT_MUTED,
            bg=parent["bg"],
            wraplength=200,
            justify=tk.LEFT,
        ).pack(anchor=tk.W, pady=(4, 0))

    def _build_metric_activation_count_card(self, parent: tk.Frame) -> None:
        tk.Label(
            parent,
            text="Activaciones de carga",
            font=self._label_font,
            fg=TEXT_MUTED,
            bg=parent["bg"],
        ).pack(anchor=tk.W)
        self._activation_count_label = tk.Label(
            parent,
            text="0",
            font=self._metric_num_font,
            fg=GREEN,
            bg=parent["bg"],
        )
        self._activation_count_label.pack(anchor=tk.W, pady=(8, 2))
        tk.Label(
            parent,
            text="Cada encendido APAGADA → ACTIVA.",
            font=self._small_font,
            fg=TEXT_MUTED,
            bg=parent["bg"],
            wraplength=200,
            justify=tk.LEFT,
        ).pack(anchor=tk.W, pady=(4, 0))

    def _build_activity_card(self, parent: tk.Frame) -> None:
        tk.Label(
            parent,
            text="Actividad reciente",
            font=self._section_font,
            fg=TEXT,
            bg=parent["bg"],
        ).pack(anchor=tk.W, pady=(0, 10))

        self._activity_frame = tk.Frame(parent, bg=parent["bg"])
        self._activity_frame.pack(fill=tk.X)

        left = tk.Frame(self._activity_frame, bg=parent["bg"])
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 16))

        tk.Label(
            left,
            text="Última detección",
            font=self._label_font,
            fg=TEXT_MUTED,
            bg=parent["bg"],
        ).pack(anchor=tk.W)
        self._last_detection_time_label = tk.Label(
            left,
            text="--:--:--",
            font=tkfont.Font(family="Menlo", size=20, weight="bold"),
            fg=TEXT,
            bg=parent["bg"],
        )
        self._last_detection_time_label.pack(anchor=tk.W, pady=(4, 0))
        self._last_detection_ago_label = tk.Label(
            left,
            text="Sin detecciones en esta sesión",
            font=self._small_font,
            fg=TEXT_MUTED,
            bg=parent["bg"],
        )
        self._last_detection_ago_label.pack(anchor=tk.W, pady=(2, 0))

        center = tk.Frame(self._activity_frame, bg=parent["bg"])
        center.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=16)

        tk.Label(
            center,
            text="Última acción",
            font=self._label_font,
            fg=TEXT_MUTED,
            bg=parent["bg"],
        ).pack(anchor=tk.W)
        self._last_action_label = tk.Label(
            center,
            text="—",
            font=tkfont.Font(family="Helvetica", size=18, weight="bold"),
            fg=TEXT,
            bg=parent["bg"],
        )
        self._last_action_label.pack(anchor=tk.W, pady=(4, 0))

        right = tk.Frame(self._activity_frame, bg=parent["bg"])
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(16, 0))

        tk.Label(
            right,
            text="Salidas de control",
            font=self._label_font,
            fg=TEXT_MUTED,
            bg=parent["bg"],
        ).pack(anchor=tk.W)
        self._activity_note_label = tk.Label(
            right,
            text="Estado comandado (no medición eléctrica).",
            font=self._small_font,
            fg=TEXT_MUTED,
            bg=parent["bg"],
            wraplength=280,
            justify=tk.LEFT,
        )
        self._activity_note_label.pack(anchor=tk.W, pady=(0, 6))

        relays_row = tk.Frame(right, bg=parent["bg"])
        relays_row.pack(anchor=tk.W)

        self._relay1_pill = self._make_relay_pill(relays_row, "Relé 1")
        self._relay1_pill.pack(side=tk.LEFT, padx=(0, 8))
        self._relay2_pill = self._make_relay_pill(relays_row, "Relé 2")
        self._relay2_pill.pack(side=tk.LEFT)

    def _make_relay_pill(self, parent: tk.Frame, name: str) -> tk.Frame:
        pill = tk.Frame(parent, bg=CARD_ALT, padx=10, pady=6, highlightthickness=1, highlightbackground=BORDER)
        tk.Label(pill, text=name, font=self._small_font, fg=TEXT_MUTED, bg=CARD_ALT).pack(anchor=tk.W)
        state_label = tk.Label(
            pill,
            text="EN ESPERA",
            font=self._small_btn_font,
            fg=TEXT_MUTED,
            bg=CARD_ALT,
        )
        state_label.pack(anchor=tk.W)
        pill._state_label = state_label  # type: ignore[attr-defined]
        return pill

    def _build_control_card(self, parent: tk.Frame) -> None:
        tk.Label(
            parent,
            text="Control de carga",
            font=self._section_font,
            fg=TEXT,
            bg=parent["bg"],
        ).pack(anchor=tk.W)

        tk.Label(
            parent,
            text="Control manual disponible desde el panel.",
            font=self._small_font,
            fg=TEXT_MUTED,
            bg=parent["bg"],
            wraplength=420,
            justify=tk.LEFT,
        ).pack(anchor=tk.W, pady=(8, 16))

        self._btn_on = FlatButton(
            parent,
            text="Activar carga",
            command=self._activate_charge,
            bg=GREEN,
            hover_bg=GREEN_DIM,
            font=self._btn_font,
            pady=14,
        )
        self._btn_on.pack(fill=tk.X, pady=(0, 10))

        self._btn_off = FlatButton(
            parent,
            text="Apagar carga",
            command=self._deactivate_charge,
            bg=RED_DIM,
            hover_bg=RED,
            font=self._btn_font,
            pady=14,
        )
        self._btn_off.pack(fill=tk.X)

        self._control_mode_label = tk.Label(
            parent,
            text="Modo demostración: cambios locales",
            font=self._small_font,
            fg=TEXT_MUTED,
            bg=parent["bg"],
            wraplength=420,
            justify=tk.LEFT,
        )
        self._control_mode_label.pack(anchor=tk.W, pady=(16, 0))

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
            wraplength=420,
            justify=tk.LEFT,
        ).pack(anchor=tk.W, pady=(8, 12))

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
            wraplength=420,
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
        conn_summary.pack(fill=tk.X, pady=(14, 0))

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
            wraplength=420,
            justify=tk.LEFT,
        )
        self._conn_port_label.pack(anchor=tk.W, pady=(4, 0))

    def _schedule_activity_tick(self) -> None:
        self._update_last_detection_ago()
        self.after(1000, self._schedule_activity_tick)

    def _update_last_detection_ago(self) -> None:
        if self._last_pir_detection_at is None:
            return
        elapsed = int((datetime.now() - self._last_pir_detection_at).total_seconds())
        self._last_detection_ago_label.configure(text=f"hace {elapsed} s")

    def _set_last_action(self, action: str) -> None:
        self._last_action = action
        self._last_action_label.configure(text=action)

    def _record_serial_pir_presence(self) -> None:
        if self._sensor_display == "PRESENCIA DETECTADA":
            return
        self._pir_detection_count += 1
        self._pir_count_label.configure(text=str(self._pir_detection_count))
        self._last_pir_detection_at = datetime.now()
        self._last_detection_time_label.configure(
            text=self._last_pir_detection_at.strftime("%H:%M:%S")
        )
        self._last_detection_ago_label.configure(text="hace 0 s")
        self._set_last_action("PIR")

    def _increment_charge_activation(self) -> None:
        self._charge_activation_count += 1
        self._activation_count_label.configure(text=str(self._charge_activation_count))

    def _transition_charge_to(self, state: str) -> bool:
        if self._charge_state == state:
            return False
        previous = self._charge_state
        self._charge_state = state
        if previous == "APAGADA" and state == "ACTIVA":
            self._increment_charge_activation()
        self._refresh_charge_display()
        return True

    def _update_relay_indicators(self) -> None:
        active = self._charge_state == "ACTIVA"
        state_text = "ACTIVADO" if active else "EN ESPERA"
        state_color = GREEN if active else TEXT_MUTED
        for pill in (self._relay1_pill, self._relay2_pill):
            pill._state_label.configure(text=state_text, fg=state_color)  # type: ignore[attr-defined]

    def _update_system_chrome(self) -> None:
        if self._connection_error:
            self._badge_frame.configure(bg="#3F1D1D")
            self._badge_label.configure(
                text="Error de conexión",
                fg=RED,
                bg="#3F1D1D",
            )
        elif self._arduino.is_connected:
            self._badge_frame.configure(bg="#14301F")
            self._badge_label.configure(
                text="Sistema conectado",
                fg=GREEN,
                bg="#14301F",
            )
        else:
            self._badge_frame.configure(bg=GRAY_BG)
            self._badge_label.configure(
                text="Modo demostración",
                fg=TEXT_MUTED,
                bg=GRAY_BG,
            )

        if self._arduino.is_connected:
            self._footer_comm_label.configure(
                text="Estado de comunicación: activa",
                fg=GREEN,
            )
            self._control_mode_label.configure(
                text="Arduino conectado: comandos en tiempo real",
                fg=GREEN,
            )
        else:
            self._footer_comm_label.configure(
                text="Estado de comunicación: en espera",
                fg=TEXT_MUTED,
            )
            self._control_mode_label.configure(
                text="Modo demostración: cambios locales",
                fg=TEXT_MUTED,
            )

        if self._arduino.is_connected:
            port = self._arduino.port_name or "?"
            self._conn_port_label.configure(text=f"Puerto: {port}")
        else:
            selected = self._port_var.get().strip()
            if selected:
                self._conn_port_label.configure(text=f"Puerto: {selected}")
            else:
                self._conn_port_label.configure(text="Puerto: no seleccionado")

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
            port = self._arduino.port_name or "?"
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
            self._log_event("Error: no se pudo enviar el comando STATUS a Arduino.")

    def _disconnect_arduino(self) -> None:
        if not self._arduino.is_connected:
            self._log_event("Arduino no estaba conectado.")
            self._update_arduino_connection_controls()
            return
        port = self._arduino.port_name
        self._arduino.disconnect()
        self._connection_error = False
        self._reset_sensor_pending()
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

    def _handle_serial_line(self, line: str) -> None:
        if line == "READY":
            self._log_event("Arduino listo para operar.")
            return
        if line == "PIR:PRESENCIA":
            self._record_serial_pir_presence()
            self._update_sensor_display(
                "PRESENCIA DETECTADA",
                GREEN,
                "Sensor PIR: presencia detectada.",
            )
            return
        if line == "PIR:AUSENCIA":
            self._update_sensor_display(
                "SIN PRESENCIA",
                GRAY_OFF,
                "Sensor PIR: sin presencia.",
            )
            return
        if line == "CARGA:ACTIVA":
            self._update_charge_from_arduino("ACTIVA", "Carga activada (reporte Arduino).")
            return
        if line == "CARGA:APAGADA":
            self._update_charge_from_arduino("APAGADA", "Carga apagada (reporte Arduino).")
            return

    def _update_sensor_display(self, text: str, color: str, log_message: str) -> None:
        if self._sensor_display == text:
            return
        self._sensor_display = text
        self._sensor_label.configure(text=text, fg=color)
        self._sensor_dot.configure(fg=color)
        self._log_event(log_message)

    def _reset_sensor_pending(self) -> None:
        self._sensor_display = "Pendiente de conexión"
        self._sensor_label.configure(text="Pendiente de conexión", fg=TEXT_MUTED)
        self._sensor_dot.configure(fg=TEXT_MUTED)

    def _update_charge_from_arduino(self, state: str, log_message: str) -> None:
        if not self._transition_charge_to(state):
            return
        self._log_event(log_message)

    def _on_close(self) -> None:
        if self._arduino.is_connected:
            self._arduino.disconnect()
        self.destroy()

    def _refresh_charge_display(self) -> None:
        if self._charge_state == "ACTIVA":
            self._charge_label.configure(text="ACTIVA", fg=GREEN)
            self._charge_dot.configure(fg=GREEN)
            self._charge_context_label.configure(text="La carga está en funcionamiento.")
            self._btn_on.configure(bg=GREEN_DIM)
            self._btn_off.configure(bg=RED)
        else:
            self._charge_label.configure(text="APAGADA", fg=GRAY_OFF)
            self._charge_dot.configure(fg=GRAY_OFF)
            self._charge_context_label.configure(text="La carga está detenida.")
            self._btn_on.configure(bg=GREEN)
            self._btn_off.configure(bg=RED_DIM)
        self._update_relay_indicators()

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

    def _activate_charge(self) -> None:
        if self._charge_state == "ACTIVA":
            self._log_event("Control manual: la carga ya estaba activa.")
            return
        self._transition_charge_to("ACTIVA")
        self._set_last_action("Control manual")
        if self._arduino.is_connected:
            if self._arduino.send_command("ON"):
                self._log_event("Comando enviado a Arduino: ON.")
            else:
                self._log_event("Error: no se pudo enviar el comando ON a Arduino.")
        else:
            self._log_event(
                "Modo demostración: carga activada localmente; Arduino no conectado."
            )

    def _deactivate_charge(self) -> None:
        if self._charge_state == "APAGADA":
            self._log_event("Control manual: la carga ya estaba apagada.")
            return
        self._transition_charge_to("APAGADA")
        self._set_last_action("Control manual")
        if self._arduino.is_connected:
            if self._arduino.send_command("OFF"):
                self._log_event("Comando enviado a Arduino: OFF.")
            else:
                self._log_event("Error: no se pudo enviar el comando OFF a Arduino.")
        else:
            self._log_event(
                "Modo demostración: carga apagada localmente; Arduino no conectado."
            )


def main() -> None:
    app = SmartEnergyDashboard()
    app.mainloop()


if __name__ == "__main__":
    main()
