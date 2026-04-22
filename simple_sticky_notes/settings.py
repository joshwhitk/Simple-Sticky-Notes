from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .models import AppSettings


APP_DATA_DIR = Path.home() / "AppData" / "Roaming" / "SimpleStickyNotes"
SETTINGS_PATH = APP_DATA_DIR / "settings.json"
DEFAULT_STORAGE_ROOT = Path.home() / "Dropbox" / "backups" / "josh-obsidian" / "simple-sticky-notes"


def ensure_app_data_dir() -> Path:
    APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
    return APP_DATA_DIR


def default_settings() -> AppSettings:
    return AppSettings(storage_root=str(DEFAULT_STORAGE_ROOT))


def load_settings() -> AppSettings:
    ensure_app_data_dir()
    if not SETTINGS_PATH.exists():
        settings = default_settings()
        save_settings(settings)
        return settings

    data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    return AppSettings(**data)


def save_settings(settings: AppSettings) -> None:
    ensure_app_data_dir()
    SETTINGS_PATH.write_text(
        json.dumps(asdict(settings), indent=2),
        encoding="utf-8",
    )
