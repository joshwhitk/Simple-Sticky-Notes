from __future__ import annotations

import json
import re
from dataclasses import asdict
from pathlib import Path
from uuid import uuid4

from .models import AppSettings, NoteMetadata, NoteRecord, utc_now_iso


MAX_FILE_STEM_LENGTH = 80


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
        metadata = self._load_metadata(note_id)
        return self._note_path_for_metadata(metadata)

    def meta_path(self, note_id: str) -> Path:
        return self.meta_dir / f"{note_id}.json"

    def create_note(
        self,
        title: str | None = None,
        *,
        body: str = "",
        x: int = 80,
        y: int = 80,
        width: int | None = None,
        height: int | None = None,
        bg_color: str = "#ffd54f",
    ) -> NoteRecord:
        note_id = uuid4().hex[:12]
        now = utc_now_iso()
        resolved_title = title or "Untitled note"
        metadata = NoteMetadata(
            note_id=note_id,
            title=resolved_title,
            x=x,
            y=y,
            width=width or self.settings.default_width,
            height=height or self.settings.default_height,
            is_open=True,
            created_at=now,
            updated_at=now,
            bg_color=bg_color,
            file_stem=self.make_unique_file_stem(note_id, body, resolved_title),
        )
        note = NoteRecord(metadata=metadata, body=body)
        self.save_note(note)
        return note

    def load_note(self, note_id: str) -> NoteRecord:
        metadata = self._load_metadata(note_id)
        note_path = self._note_path_for_metadata(metadata)
        if not note_path.exists():
            note_path = self._legacy_note_path(note_id)
        body = note_path.read_text(encoding="utf-8") if note_path.exists() else ""
        return NoteRecord(metadata=metadata, body=body)

    def save_note(self, note: NoteRecord) -> None:
        note.metadata.updated_at = utc_now_iso()
        desired_stem = self.make_unique_file_stem(note.metadata.note_id, note.body, note.metadata.title)
        current_path = self._existing_note_path(note.metadata)
        desired_path = self.notes_dir / f"{desired_stem}.md"

        note.metadata.file_stem = desired_stem
        if current_path.exists() and current_path != desired_path and not desired_path.exists():
            current_path.rename(desired_path)

        desired_path.write_text(note.body, encoding="utf-8")
        self.save_metadata(note.metadata)

    def save_metadata(self, metadata: NoteMetadata) -> None:
        self.meta_path(metadata.note_id).write_text(
            json.dumps(asdict(metadata), indent=2),
            encoding="utf-8",
        )

    def list_note_ids(self) -> list[str]:
        return sorted(path.stem for path in self.meta_dir.glob("*.json"))

    def list_notes(self) -> list[NoteRecord]:
        notes: list[NoteRecord] = []
        for note_id in self.list_note_ids():
            try:
                notes.append(self.load_note(note_id))
            except FileNotFoundError:
                continue
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

    def delete_note(self, note_id: str, *, delete_body: bool = True) -> None:
        metadata_path = self.meta_path(note_id)
        if not metadata_path.exists():
            return

        metadata = self._load_metadata(note_id)
        note_path = self._existing_note_path(metadata)
        if delete_body and note_path.exists():
            note_path.unlink()
        metadata_path.unlink(missing_ok=True)

    def prune_missing_note_files(self, *, protected_note_ids: set[str] | None = None) -> list[str]:
        protected = protected_note_ids or set()
        removed: list[str] = []
        for note_id in self.list_note_ids():
            if note_id in protected:
                continue
            try:
                metadata = self._load_metadata(note_id)
            except FileNotFoundError:
                continue
            if self._existing_note_path(metadata).exists():
                continue
            self.meta_path(note_id).unlink(missing_ok=True)
            removed.append(note_id)
        return removed

    def make_unique_file_stem(self, note_id: str, body: str, fallback_title: str) -> str:
        base_stem = suggested_file_stem(body, fallback_title)
        used_stems = {
            self._load_metadata(other_note_id).file_stem.casefold() or self._load_metadata(other_note_id).note_id.casefold()
            for other_note_id in self.list_note_ids()
            if other_note_id != note_id
        }
        candidate = base_stem
        counter = 1
        while candidate.casefold() in used_stems:
            suffix = f"-{counter}"
            candidate = f"{base_stem[: MAX_FILE_STEM_LENGTH - len(suffix)]}{suffix}"
            counter += 1
        return candidate

    def _load_metadata(self, note_id: str) -> NoteMetadata:
        return NoteMetadata(**json.loads(self.meta_path(note_id).read_text(encoding="utf-8")))

    def _note_path_for_metadata(self, metadata: NoteMetadata) -> Path:
        if metadata.file_stem:
            return self.notes_dir / f"{metadata.file_stem}.md"
        return self._legacy_note_path(metadata.note_id)

    def _legacy_note_path(self, note_id: str) -> Path:
        return self.notes_dir / f"{note_id}.md"

    def _existing_note_path(self, metadata: NoteMetadata) -> Path:
        current_path = self._note_path_for_metadata(metadata)
        if current_path.exists():
            return current_path
        legacy_path = self._legacy_note_path(metadata.note_id)
        if legacy_path.exists():
            return legacy_path
        return current_path


def suggested_file_stem(body: str, fallback_title: str) -> str:
    source = collapsed_filename_source(body or fallback_title)
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', " ", source)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .")
    if not cleaned:
        cleaned = "Untitled note"
    return cleaned[:MAX_FILE_STEM_LENGTH].rstrip(" .")


def collapsed_filename_source(text: str) -> str:
    flattened = " ".join(line.strip().lstrip("#").strip() for line in text.splitlines() if line.strip())
    return flattened or "Untitled note"
