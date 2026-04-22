from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from uuid import uuid4

from .models import AppSettings, NoteMetadata, NoteRecord, utc_now_iso


class StickyStorage:
    def __init__(self, settings: AppSettings) -> None:
        self.root = Path(settings.storage_root)
        self.notes_dir = self.root / "notes"
        self.meta_dir = self.root / "meta"
        self.settings = settings
        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        self.notes_dir.mkdir(parents=True, exist_ok=True)
        self.meta_dir.mkdir(parents=True, exist_ok=True)

    def note_path(self, note_id: str) -> Path:
        return self.notes_dir / f"{note_id}.md"

    def meta_path(self, note_id: str) -> Path:
        return self.meta_dir / f"{note_id}.json"

    def create_note(self, title: str | None = None) -> NoteRecord:
        note_id = uuid4().hex[:12]
        now = utc_now_iso()
        metadata = NoteMetadata(
            note_id=note_id,
            title=title or "Untitled note",
            x=80,
            y=80,
            width=self.settings.default_width,
            height=self.settings.default_height,
            is_open=True,
            created_at=now,
            updated_at=now,
        )
        note = NoteRecord(metadata=metadata, body="")
        self.save_note(note)
        return note

    def load_note(self, note_id: str) -> NoteRecord:
        metadata = NoteMetadata(**json.loads(self.meta_path(note_id).read_text(encoding="utf-8")))
        body = self.note_path(note_id).read_text(encoding="utf-8") if self.note_path(note_id).exists() else ""
        return NoteRecord(metadata=metadata, body=body)

    def save_note(self, note: NoteRecord) -> None:
        note.metadata.updated_at = utc_now_iso()
        self.note_path(note.metadata.note_id).write_text(note.body, encoding="utf-8")
        self.meta_path(note.metadata.note_id).write_text(
            json.dumps(asdict(note.metadata), indent=2),
            encoding="utf-8",
        )

    def list_note_ids(self) -> list[str]:
        return sorted(path.stem for path in self.meta_dir.glob("*.json"))

    def list_notes(self) -> list[NoteRecord]:
        notes: list[NoteRecord] = []
        for note_id in self.list_note_ids():
            notes.append(self.load_note(note_id))
        return notes

    def list_open_notes(self) -> list[NoteRecord]:
        return [note for note in self.list_notes() if note.metadata.is_open]

    def update_geometry(self, note_id: str, *, x: int, y: int, width: int, height: int) -> None:
        note = self.load_note(note_id)
        note.metadata.x = x
        note.metadata.y = y
        note.metadata.width = width
        note.metadata.height = height
        self.save_note(note)

    def hide_note(self, note_id: str) -> None:
        note = self.load_note(note_id)
        note.metadata.is_open = False
        self.save_note(note)

    def reopen_note(self, note_id: str) -> NoteRecord:
        note = self.load_note(note_id)
        note.metadata.is_open = True
        self.save_note(note)
        return note
