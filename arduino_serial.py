"""Gestión de puerto serial para Arduino."""

from __future__ import annotations

from typing import Optional

import serial
from serial.tools import list_ports

DEFAULT_BAUD_RATE = 9600


def list_serial_ports() -> list[str]:
    """Devuelve los nombres de puertos seriales detectados en el sistema."""
    return sorted(port.device for port in list_ports.comports())


class ArduinoSerialConnection:
    """Encapsula la conexión serial (envío y lectura no bloqueante)."""

    def __init__(self, baudrate: int = DEFAULT_BAUD_RATE) -> None:
        self._baudrate = baudrate
        self._serial: Optional[serial.Serial] = None
        self._port: Optional[str] = None
        self._line_buffer = ""

    @property
    def is_connected(self) -> bool:
        return self._serial is not None and self._serial.is_open

    @property
    def port_name(self) -> Optional[str]:
        return self._port

    def connect(self, port: str) -> None:
        """Abre el puerto indicado. Lanza serial.SerialException si falla."""
        if self.is_connected:
            self.disconnect()
        self._serial = serial.Serial(port=port, baudrate=self._baudrate, timeout=1)
        self._port = port
        self._line_buffer = ""

    def disconnect(self) -> None:
        """Cierra el puerto si estaba abierto."""
        if self._serial is not None:
            if self._serial.is_open:
                self._serial.close()
            self._serial = None
        self._port = None
        self._line_buffer = ""

    def send_command(self, command: str) -> bool:
        """Envía un comando UTF-8 terminado en nueva línea. Devuelve False si no hay conexión o falla el envío."""
        if not self.is_connected or self._serial is None:
            return False
        try:
            self._serial.write(f"{command}\n".encode("utf-8"))
            return True
        except SerialException:
            return False

    def read_available_lines(self) -> list[str]:
        """Lee y devuelve líneas completas ya disponibles en el puerto (sin bloquear)."""
        if not self.is_connected or self._serial is None:
            return []
        try:
            waiting = self._serial.in_waiting
            if waiting <= 0:
                return []
            chunk = self._serial.read(waiting)
        except SerialException:
            return []

        self._line_buffer += chunk.decode("utf-8", errors="ignore")
        lines: list[str] = []
        while "\n" in self._line_buffer:
            line, self._line_buffer = self._line_buffer.split("\n", 1)
            cleaned = line.strip()
            if cleaned:
                lines.append(cleaned)
        return lines
