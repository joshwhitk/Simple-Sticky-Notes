from __future__ import annotations

import configparser
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import quote

from .settings import load_settings
from .storage import StickyStorage, create_storage

if TYPE_CHECKING:
    from .joplin_storage import JoplinStickyStorage


ATTACHMENTS_DIR_NAME = "Attachments"
TEXT_EXTENSIONS = {
    ".md",
    ".markdown",
    ".txt",
    ".text",
    ".log",
    ".csv",
    ".json",
    ".py",
    ".js",
    ".ts",
    ".html",
    ".htm",
}


@dataclass(slots=True)
class DroppedNoteContent:
    source: str
    body: str
    imported_to_obsidian: bool


def import_dropped_paths(paths: list[str]) -> list[DroppedNoteContent]:
    storage = create_storage(load_settings())
    return [import_dropped_path(Path(path), storage) for path in paths]


def import_dropped_path(path: Path, storage: "StickyStorage | JoplinStickyStorage") -> DroppedNoteContent:
    resolved = path.expanduser().resolve()
    url_body = try_read_internet_shortcut(resolved)
    if url_body is not None:
        return DroppedNoteContent(source=str(resolved), body=url_body, imported_to_obsidian=False)

    text_body = try_read_text_drop(resolved)
    if text_body is not None:
        return DroppedNoteContent(source=str(resolved), body=text_body, imported_to_obsidian=False)

    body = attachment_drop_body(resolved, storage)
    return DroppedNoteContent(source=str(resolved), body=body, imported_to_obsidian=True)


def attachment_drop_body(path: Path, storage: "StickyStorage | JoplinStickyStorage") -> str:
    """Capture a binary drop under the active backend and return the body line
    that references it. Files backend: copy into the vault's Attachments folder,
    exactly as before. Joplin backend: upload as a resource, because the vault
    is a frozen archive and must never be written."""
    from .joplin_storage import JoplinStickyStorage

    if isinstance(storage, JoplinStickyStorage):
        return storage.import_dropped_file(path)
    attachment_path = copy_drop_into_obsidian(path, storage)
    relative_target = attachment_path.relative_to(storage.root)
    encoded_target = quote(relative_target.as_posix(), safe="/._-()")
    return f"Imported attachment: [{attachment_path.name}]({encoded_target})"


def try_read_internet_shortcut(path: Path) -> str | None:
    if path.suffix.lower() != ".url" or not path.exists():
        return None
    parser = configparser.ConfigParser()
    parser.read(path, encoding="utf-8")
    url = parser.get("InternetShortcut", "URL", fallback="").strip()
    if not url:
        return None
    title = path.stem.strip()
    if title:
        return f"[{title}]({url})"
    return url


def try_read_text_drop(path: Path) -> str | None:
    if not path.exists() or path.is_dir():
        return None
    if path.suffix.lower() in TEXT_EXTENSIONS:
        return path.read_text(encoding="utf-8")

    data = path.read_bytes()
    if b"\x00" in data:
        return None
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return None
    return text


def copy_drop_into_obsidian(path: Path, storage: "StickyStorage | JoplinStickyStorage") -> Path:
    attachments_root = storage.root / ATTACHMENTS_DIR_NAME
    attachments_root.mkdir(parents=True, exist_ok=True)
    destination = unique_attachment_path(attachments_root, path.name)
    if path.is_dir():
        shutil.copytree(path, destination)
    else:
        shutil.copy2(path, destination)
    return destination


def unique_attachment_path(root: Path, name: str) -> Path:
    candidate = root / name
    if not candidate.exists():
        return candidate
    stem = candidate.stem
    suffix = candidate.suffix
    counter = 1
    while True:
        candidate = root / f"{stem}-{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1
