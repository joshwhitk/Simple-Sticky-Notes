from __future__ import annotations

import json
import shutil
from dataclasses import asdict
from pathlib import Path

from .models import AppSettings


APP_DATA_DIR = Path.home() / "AppData" / "Roaming" / "SimpleStickyNotes"
SETTINGS_PATH = APP_DATA_DIR / "settings.json"
DEFAULT_STORAGE_ROOT = Path.home() / "Documents" / "Simple Sticky Notes"


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
    settings = AppSettings(**data)
    return migrate_legacy_storage_root(settings)


def save_settings(settings: AppSettings) -> None:
    ensure_app_data_dir()
    SETTINGS_PATH.write_text(
        json.dumps(asdict(settings), indent=2),
        encoding="utf-8",
    )


def migrate_legacy_storage_root(settings: AppSettings) -> AppSettings:
    if not looks_like_legacy_dropbox_storage(settings.storage_root):
        return settings

    copy_storage_contents(Path(settings.storage_root), DEFAULT_STORAGE_ROOT)
    settings.storage_root = str(DEFAULT_STORAGE_ROOT)
    save_settings(settings)
    return settings


def copy_storage_contents(source: Path, target: Path) -> None:
    if not source.exists():
        target.mkdir(parents=True, exist_ok=True)
        return

    target.mkdir(parents=True, exist_ok=True)
    for path in source.rglob("*"):
        relative = path.relative_to(source)
        destination = target / relative
        if path.is_dir():
            destination.mkdir(parents=True, exist_ok=True)
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            if not destination.exists():
                shutil.copy2(path, destination)


def normalized_path(path: str | Path) -> str:
    return str(Path(path).expanduser()).lower()


def looks_like_legacy_dropbox_storage(path: str | Path) -> bool:
    candidate = Path(path)
    parts = {part.casefold() for part in candidate.parts}
    return "dropbox" in parts and candidate.name.casefold() == "simple-sticky-notes"
