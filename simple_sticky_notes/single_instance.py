from __future__ import annotations

import json
import socket
import threading
from collections.abc import Callable
from typing import Any


HOST = "127.0.0.1"
PORT = 38473
BUFFER_SIZE = 16384


class InstanceServer:
    def __init__(self, on_command: Callable[[str], None]) -> None:
        self._on_command = on_command
        self._socket: socket.socket | None = None
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    def start(self) -> bool:
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            listener.bind((HOST, PORT))
            listener.listen()
        except OSError:
            listener.close()
            return False

        self._socket = listener
        self._thread = threading.Thread(target=self._serve, name="sticky-notes-instance-server", daemon=True)
        self._thread.start()
        return True

    def stop(self) -> None:
        self._stop_event.set()
        if self._socket is not None:
            try:
                self._socket.close()
            except OSError:
                pass
            self._socket = None
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=1)
        self._thread = None

    def _serve(self) -> None:
        while not self._stop_event.is_set():
            listener = self._socket
            if listener is None:
                return
            try:
                conn, _addr = listener.accept()
            except OSError:
                return
            with conn:
                try:
                    payload = conn.recv(BUFFER_SIZE).decode("utf-8").strip()
                except OSError:
                    continue
                if payload:
                    self._on_command(payload)


def send_command(command: str) -> bool:
    return send_payload({"command": command})


def send_payload(payload: dict[str, Any]) -> bool:
    try:
        with socket.create_connection((HOST, PORT), timeout=1) as conn:
            conn.sendall(json.dumps(payload, ensure_ascii=True).encode("utf-8"))
        return True
    except OSError:
        return False


def is_instance_running() -> bool:
    try:
        with socket.create_connection((HOST, PORT), timeout=0.5):
            return True
    except OSError:
        return False
