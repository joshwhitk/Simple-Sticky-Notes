from __future__ import annotations

import ctypes
import json
import re
from dataclasses import asdict
from pathlib import Path
from uuid import uuid4

from .models import AppSettings, NoteMetadata, NoteRecord, utc_now_iso


MAX_FILE_STEM_LENGTH = 80
MAX_TITLE_WORDS = 10
HIDDEN_APP_DIR_NAME = ".simple-sticky-notes"
METADATA_DIR_NAME = "meta"
LEGACY_NOTES_DIR_NAME = "notes"
LEGACY_META_DIR_NAME = "meta"
ATTACHMENTS_DIR_NAME = "_attachments"
PASTED_IMAGE_PREFIX = "Pasted image"


class StickyStorage:
    def __init__(self, settings: AppSettings) -> None:
        self.root = Path(settings.storage_root)
        self.notes_dir = self.root
        self.internal_dir = self.root / HIDDEN_APP_DIR_NAME
        self.meta_dir = self.internal_dir / METADATA_DIR_NAME
        self.settings = settings
        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        self.internal_dir.mkdir(parents=True, exist_ok=True)
        mark_hidden_on_windows(self.internal_dir)
        self._migrate_legacy_layout()
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
            file_stem=self.make_unique_file_stem(note_id, resolved_title),
        )
        note = NoteRecord(metadata=metadata, body=body)
        self.save_note(note)
        return note

    def load_note(self, note_id: str) -> NoteRecord:
        metadata = self._load_metadata(note_id)
        note_path = self._note_path_for_metadata(metadata)
        if not note_path.exists():
            note_path = self._legacy_note_path(note_id)
        content = note_path.read_text(encoding="utf-8") if note_path.exists() else ""
        body = strip_frontmatter(content)
        return NoteRecord(metadata=metadata, body=body)

    def save_note(self, note: NoteRecord) -> None:
        note.metadata.updated_at = utc_now_iso()
        if not note.metadata.file_stem:
            note.metadata.file_stem = self.make_unique_file_stem(note.metadata.note_id, note.metadata.title)
        note_path = self._existing_note_path(note.metadata)
        existing_frontmatter = None
        if note_path.exists():
            existing_frontmatter, _ = split_frontmatter(note_path.read_text(encoding="utf-8"))
        note_content = format_note_with_frontmatter(note.body, existing_frontmatter)
        note_path.write_text(note_content, encoding="utf-8")
        self.save_metadata(note.metadata)

    def save_metadata(self, metadata: NoteMetadata) -> None:
        self.meta_path(metadata.note_id).write_text(
            json.dumps(asdict(metadata), indent=2),
            encoding="utf-8",
        )

    def attachments_dir(self) -> Path:
        return self.root / ATTACHMENTS_DIR_NAME

    def save_clipboard_image(self, image, *, stamp: str | None = None) -> str:
        """Save a PIL image into the vault's _attachments folder as PNG.

        Returns the bare filename to embed as an Obsidian wikilink ``![[name]]``
        (which resolves by basename anywhere in the vault). Mirrors Obsidian's
        own ``Pasted image YYYYMMDDHHMMSS.png`` naming, de-duplicated with a
        ``-N`` suffix.
        """
        from datetime import datetime

        attach = self.attachments_dir()
        attach.mkdir(parents=True, exist_ok=True)
        stamp = stamp or datetime.now().strftime("%Y%m%d%H%M%S")
        name = f"{PASTED_IMAGE_PREFIX} {stamp}.png"
        dest = attach / name
        counter = 1
        while dest.exists():
            name = f"{PASTED_IMAGE_PREFIX} {stamp}-{counter}.png"
            dest = attach / name
            counter += 1
        image.save(str(dest), "PNG")
        return name

    def import_image_file(self, source: Path | str) -> str:
        """Copy an existing image file into _attachments; return its filename."""
        import shutil

        source = Path(source)
        attach = self.attachments_dir()
        attach.mkdir(parents=True, exist_ok=True)
        name = source.name
        dest = attach / name
        counter = 1
        while dest.exists():
            name = f"{source.stem}-{counter}{source.suffix}"
            dest = attach / name
            counter += 1
        shutil.copy2(str(source), str(dest))
        return name

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

    def make_unique_file_stem(self, note_id: str, title: str) -> str:
        base_stem = suggested_file_stem(title)
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
        return self.notes_dir / f"{metadata.note_id}.md"

    def _legacy_note_path(self, note_id: str) -> Path:
        return self.root / LEGACY_NOTES_DIR_NAME / f"{note_id}.md"

    def _legacy_stemmed_note_path(self, metadata: NoteMetadata) -> Path:
        if metadata.file_stem:
            return self.root / LEGACY_NOTES_DIR_NAME / f"{metadata.file_stem}.md"
        return self._legacy_note_path(metadata.note_id)

    def _existing_note_path(self, metadata: NoteMetadata) -> Path:
        current_path = self._note_path_for_metadata(metadata)
        if current_path.exists():
            return current_path
        legacy_stemmed_path = self._legacy_stemmed_note_path(metadata)
        if legacy_stemmed_path.exists():
            return legacy_stemmed_path
        legacy_path = self._legacy_note_path(metadata.note_id)
        if legacy_path.exists():
            return legacy_path
        return current_path

    def _migrate_legacy_layout(self) -> None:
        legacy_notes_dir = self.root / LEGACY_NOTES_DIR_NAME
        if legacy_notes_dir.exists():
            for note_path in legacy_notes_dir.glob("*.md"):
                destination = self.root / note_path.name
                if not destination.exists():
                    note_path.replace(destination)
            remove_empty_dirs(legacy_notes_dir)

        legacy_meta_dir = self.root / LEGACY_META_DIR_NAME
        if legacy_meta_dir.exists() and legacy_meta_dir != self.meta_dir:
            self.meta_dir.mkdir(parents=True, exist_ok=True)
            for metadata_path in legacy_meta_dir.glob("*.json"):
                destination = self.meta_dir / metadata_path.name
                if not destination.exists():
                    metadata_path.replace(destination)
            remove_empty_dirs(legacy_meta_dir)

def note_title(body: str) -> str:
    collapsed = collapsed_note_text(body)
    words = collapsed.split()
    if not words:
        return "Untitled note"
    return " ".join(words[:MAX_TITLE_WORDS])


def suggested_file_stem(title: str) -> str:
    source = note_title(title)
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', " ", source)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .")
    if not cleaned:
        cleaned = "Untitled note"
    return cleaned[:MAX_FILE_STEM_LENGTH].rstrip(" .")


def collapsed_note_text(text: str) -> str:
    flattened = " ".join(line.strip().lstrip("#").strip() for line in text.splitlines() if line.strip())
    return flattened or "Untitled note"


def first_nonblank_line(text: str) -> str | None:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped.lstrip("#").strip()
    return None


STICKYNOTE_TAG = "stickynote"
_TOP_LEVEL_KEY_RE = re.compile(r"^([^\s:#][^:]*):(.*)$")
_LIST_ITEM_RE = re.compile(r"^(\s*)-\s*(.*)$")


def _yaml_double_quote(value: str) -> str:
    """Return value as a YAML double-quoted scalar so titles containing
    colons, quotes, leading dashes, etc. produce valid frontmatter."""
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def split_frontmatter(content: str) -> tuple[str | None, str]:
    """Split content into (frontmatter_block, body). frontmatter_block is the
    inner text between the leading '---' delimiter lines (no delimiters), or
    None when there is no frontmatter. Only lines that are exactly '---'
    delimit the block, so a markdown rule inside the body is preserved."""
    lines = content.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return None, content
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return "".join(lines[1:i]), "".join(lines[i + 1:])
    return None, content


def strip_frontmatter(content: str) -> str:
    """Return the note body with any leading YAML frontmatter removed."""
    return split_frontmatter(content)[1]


def _norm_tag(value: str) -> str:
    return value.strip().strip("'\"").strip()


def _parse_top_level_entries(block: str) -> list[dict]:
    """Parse a frontmatter block into ordered top-level entries. Each entry is
    {"key": str|None, "lines": [str, ...]} where indented/blank/comment lines
    attach to the preceding key so arbitrary nested values stay verbatim."""
    entries: list[dict] = []
    current: dict | None = None
    for line in block.splitlines():
        is_top_level_key = bool(_TOP_LEVEL_KEY_RE.match(line)) and not line[:1].isspace()
        if is_top_level_key:
            current = {"key": _TOP_LEVEL_KEY_RE.match(line).group(1).strip(), "lines": [line]}
            entries.append(current)
        elif current is None:
            current = {"key": None, "lines": [line]}
            entries.append(current)
        else:
            current["lines"].append(line)
    return entries


def _set_title_entry(entries: list[dict], title: str) -> None:
    title_line = f"title: {_yaml_double_quote(title)}"
    for entry in entries:
        if entry["key"] == "title":
            entry["lines"] = [title_line]
            return
    entries.insert(0, {"key": "title", "lines": [title_line]})


def _ensure_stickynote_tag(entries: list[dict]) -> None:
    tags_entry = next((e for e in entries if e["key"] in ("tags", "tag")), None)
    if tags_entry is None:
        entries.append({"key": "tags", "lines": ["tags:", f"  - {STICKYNOTE_TAG}"]})
        return

    first_line = tags_entry["lines"][0]
    inline_value = first_line.split(":", 1)[1].strip()

    if inline_value.startswith("["):
        items = [item for item in (i.strip() for i in inline_value[1:-1].split(",")) if item]
        if any(_norm_tag(item) == STICKYNOTE_TAG for item in items):
            return
        items.append(STICKYNOTE_TAG)
        tags_entry["lines"][0] = f"{first_line.split(':', 1)[0]}: [{', '.join(items)}]"
        return

    if inline_value and inline_value not in ("~", "null"):
        # Scalar value like `tags: foo` -> promote to a flow list with our tag.
        if _norm_tag(inline_value) == STICKYNOTE_TAG:
            return
        tags_entry["lines"][0] = f"{first_line.split(':', 1)[0]}: [{inline_value}, {STICKYNOTE_TAG}]"
        return

    # Block list (or empty): inspect indented `- item` children.
    indent = "  "
    for child in tags_entry["lines"][1:]:
        item = _LIST_ITEM_RE.match(child)
        if item:
            indent = item.group(1) or indent
            if _norm_tag(item.group(2)) == STICKYNOTE_TAG:
                return
    tags_entry["lines"].append(f"{indent}- {STICKYNOTE_TAG}")


def _render_entries(entries: list[dict]) -> str:
    lines = [line for entry in entries for line in entry["lines"]]
    return "\n".join(lines) + "\n"


def merge_frontmatter(existing_block: str | None, title: str) -> str:
    """Build a frontmatter block that sets the auto-title and guarantees the
    stickynote tag, preserving every other property/tag from existing_block."""
    if not existing_block or not existing_block.strip():
        return f"title: {_yaml_double_quote(title)}\ntags:\n  - {STICKYNOTE_TAG}\n"
    entries = _parse_top_level_entries(existing_block)
    _set_title_entry(entries, title)
    _ensure_stickynote_tag(entries)
    return _render_entries(entries)


def format_note_with_frontmatter(body: str, existing_frontmatter: str | None = None) -> str:
    """Prepend frontmatter to body. When existing_frontmatter is given (the
    note's current on-disk YAML), its properties are preserved and only the
    title and stickynote tag are updated."""
    title = first_nonblank_line(body) or "Untitled note"
    block = merge_frontmatter(existing_frontmatter, title)
    return f"---\n{block}---\n{body}"


def remove_empty_dirs(path: Path) -> None:
    if not path.exists():
        return
    for child in sorted(path.iterdir(), reverse=True):
        if child.is_dir():
            remove_empty_dirs(child)
    try:
        path.rmdir()
    except OSError:
        pass


def mark_hidden_on_windows(path: Path) -> None:
    try:
        attributes = ctypes.windll.kernel32.GetFileAttributesW(str(path))
        if attributes == -1:
            return
        hidden_flag = 0x2
        if attributes & hidden_flag:
            return
        ctypes.windll.kernel32.SetFileAttributesW(str(path), attributes | hidden_flag)
    except (AttributeError, OSError):
        return
