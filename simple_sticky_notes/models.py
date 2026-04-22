from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass(slots=True)
class AppSettings:
    storage_root: str
    font_family: str = "Arial"
    font_size: int = 14
    default_width: int = 360
    default_height: int = 260
    autosave_delay_ms: int = 700


@dataclass(slots=True)
class NoteMetadata:
    note_id: str
    title: str
    x: int
    y: int
    width: int
    height: int
    is_open: bool
    created_at: str
    updated_at: str
    bg_color: str = "#ffd54f"
    file_stem: str = ""


@dataclass(slots=True)
class NoteRecord:
    metadata: NoteMetadata
    body: str
