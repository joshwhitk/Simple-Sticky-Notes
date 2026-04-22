from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from uuid import uuid4

from .settings import APP_DATA_DIR, ensure_app_data_dir


RUNTIME_STATE_PATH = APP_DATA_DIR / "runtime_state.json"


@dataclass(slots=True)
class RuntimeState:
    active_session_id: str = ""
    last_shutdown_clean: bool = True


def load_runtime_state() -> RuntimeState:
    ensure_app_data_dir()
    if not RUNTIME_STATE_PATH.exists():
        return RuntimeState()
    return RuntimeState(**json.loads(RUNTIME_STATE_PATH.read_text(encoding="utf-8")))


def save_runtime_state(state: RuntimeState) -> None:
    ensure_app_data_dir()
    RUNTIME_STATE_PATH.write_text(json.dumps(asdict(state), indent=2), encoding="utf-8")


def mark_app_launch() -> tuple[str, bool]:
    previous_state = load_runtime_state()
    session_id = uuid4().hex
    save_runtime_state(RuntimeState(active_session_id=session_id, last_shutdown_clean=False))
    return session_id, previous_state.last_shutdown_clean


def mark_clean_shutdown(session_id: str) -> None:
    current_state = load_runtime_state()
    if current_state.active_session_id != session_id:
        return
    save_runtime_state(RuntimeState(active_session_id="", last_shutdown_clean=True))
