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
    # Joplin since the migration on 2026-08-17. This read "files" while the migration was
    # in flight, which was right then and stopped being safe the moment the vault became a
    # frozen read-only archive: a machine with no settings.json would write notes into a
    # dead folder that nothing reads.
    storage_backend: str = "joplin"
    joplin_api_url: str = "http://100.121.209.20:41185"
    joplin_api_token: str = ""
    joplin_notebook: str = "Simple Sticky Notes"


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
    always_on_top: bool = False


@dataclass(slots=True)
class NoteRecord:
    metadata: NoteMetadata
    body: str
