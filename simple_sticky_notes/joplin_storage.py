from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from .models import AppSettings, NoteMetadata, NoteRecord, utc_now_iso
from .settings import APP_DATA_DIR
from .storage import (
    ATTACHMENTS_DIR_NAME,
    HIDDEN_APP_DIR_NAME,
    import_image_into_attachments,
    read_phone_home_stems,
    save_image_to_attachments,
)


JOPLIN_META_DIR = APP_DATA_DIR / "joplin-meta"
JOPLIN_PSEUDO_SCHEME = "joplin:"
NOTE_FIELDS = "id,title,body,user_created_time,user_updated_time"
REQUEST_TIMEOUT_SECONDS = 10
REQUEST_ATTEMPTS = 2
RETRY_DELAY_SECONDS = 0.5
CASCADE_BASE_X = 80
CASCADE_BASE_Y = 80
CASCADE_STEP = 30
CASCADE_SLOTS = 10


class JoplinApiError(RuntimeError):
    """A Joplin Data API call failed. The message is safe to show in the UI."""

    def __init__(self, message: str, *, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


class JoplinApi:
    """Minimal stdlib client for the Joplin Data API (token auth via query param).

    Every call gets a timeout and one retry on 5xx responses and connection
    errors, then raises JoplinApiError with a message the UI can show."""

    def __init__(self, base_url: str, token: str, *, timeout: float = REQUEST_TIMEOUT_SECONDS) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout

    def get(self, path: str, **query: object) -> dict:
        return self._request("GET", path, query=query)

    def post(self, path: str, payload: dict) -> dict:
        return self._request("POST", path, payload=payload)

    def put(self, path: str, payload: dict) -> dict:
        return self._request("PUT", path, payload=payload)

    def delete(self, path: str) -> dict:
        return self._request("DELETE", path)

    def _request(self, method: str, path: str, *, query: dict | None = None, payload: dict | None = None) -> dict:
        params = {str(key): str(value) for key, value in (query or {}).items()}
        params["token"] = self.token
        url = f"{self.base_url}{path}?{urllib.parse.urlencode(params)}"
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        headers = {"Content-Type": "application/json"} if body is not None else {}
        for attempt in range(1, REQUEST_ATTEMPTS + 1):
            request = urllib.request.Request(url, data=body, headers=headers, method=method)
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    raw = response.read()
            except urllib.error.HTTPError as error:
                if error.code >= 500 and attempt < REQUEST_ATTEMPTS:
                    time.sleep(RETRY_DELAY_SECONDS)
                    continue
                raise JoplinApiError(
                    f"Joplin API {method} {path} failed with HTTP {error.code}.",
                    status=error.code,
                ) from error
            except OSError as error:
                if attempt < REQUEST_ATTEMPTS:
                    time.sleep(RETRY_DELAY_SECONDS)
                    continue
                raise JoplinApiError(
                    f"Joplin is unreachable at {self.base_url}. "
                    "Check that Joplin is running with the Web Clipper service enabled."
                ) from error
            if not raw:
                return {}
            return json.loads(raw.decode("utf-8"))
        raise JoplinApiError(f"Joplin API {method} {path} failed.")


class JoplinStickyStorage:
    """Note bodies live in Joplin; window state stays in local sidecars.

    Same public surface as StickyStorage, but note_id is the Joplin note id
    (32 hex chars) and note bodies are read/written through the Joplin Data
    API against the configured notebook. Geometry, color, and open state are
    per-device concerns, so they keep the JSON sidecar mechanism relocated to
    the per-user app data dir and never round-trip through Joplin. The vault
    storage root is still used for pasted-image attachments and the Android
    phone-home file so those flows keep working unchanged."""

    def __init__(
        self,
        settings: AppSettings,
        *,
        api: JoplinApi | None = None,
        meta_dir: Path | None = None,
    ) -> None:
        self.settings = settings
        self.root = Path(settings.storage_root)
        self.notes_dir = self.root
        self.internal_dir = self.root / HIDDEN_APP_DIR_NAME
        self.meta_dir = Path(meta_dir) if meta_dir is not None else JOPLIN_META_DIR
        self.api = api or JoplinApi(settings.joplin_api_url, settings.joplin_api_token)
        self._notebook_id: str | None = None

    def note_path(self, note_id: str) -> Path:
        """A ``joplin:<id>`` pseudo-path. It never exists on disk, so callers
        that probe the file (external-edit polling, Notepad/Obsidian handoff)
        quietly no-op under this backend."""
        return Path(f"{JOPLIN_PSEUDO_SCHEME}{note_id}")

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
        resolved_title = title or "Untitled note"
        created = self.api.post(
            "/notes",
            {"title": resolved_title, "body": body, "parent_id": self.notebook_id()},
        )
        now = utc_now_iso()
        metadata = NoteMetadata(
            note_id=str(created["id"]),
            title=resolved_title,
            x=x,
            y=y,
            width=width or self.settings.default_width,
            height=height or self.settings.default_height,
            is_open=True,
            created_at=now,
            updated_at=now,
            bg_color=bg_color,
        )
        self.save_metadata(metadata)
        return NoteRecord(metadata=metadata, body=body)

    def load_note(self, note_id: str) -> NoteRecord:
        remote = self._fetch_remote_note(note_id)
        metadata = self._metadata_for_remote(remote)
        return NoteRecord(metadata=metadata, body=str(remote.get("body") or ""))

    def save_note(self, note: NoteRecord) -> None:
        note.metadata.updated_at = utc_now_iso()
        self.api.put(
            f"/notes/{note.metadata.note_id}",
            {"title": note.metadata.title, "body": note.body},
        )
        self.save_metadata(note.metadata)

    def save_metadata(self, metadata: NoteMetadata) -> None:
        self.meta_dir.mkdir(parents=True, exist_ok=True)
        self.meta_path(metadata.note_id).write_text(
            json.dumps(asdict(metadata), indent=2),
            encoding="utf-8",
        )

    def notebook_id(self) -> str:
        """The configured notebook's id, found by title or created on demand."""
        if self._notebook_id:
            return self._notebook_id
        wanted = self.settings.joplin_notebook
        page = 1
        while True:
            data = self.api.get("/folders", fields="id,title", page=page)
            for folder in data.get("items", []):
                if folder.get("title") == wanted:
                    self._notebook_id = str(folder["id"])
                    return self._notebook_id
            if not data.get("has_more"):
                break
            page += 1
        created = self.api.post("/folders", {"title": wanted})
        self._notebook_id = str(created["id"])
        return self._notebook_id

    def attachments_dir(self) -> Path:
        return self.root / ATTACHMENTS_DIR_NAME

    def save_clipboard_image(self, image, *, stamp: str | None = None) -> str:
        return save_image_to_attachments(self.attachments_dir(), image, stamp=stamp)

    def import_image_file(self, source: Path | str) -> str:
        return import_image_into_attachments(self.attachments_dir(), source)

    def list_note_ids(self) -> list[str]:
        return sorted(str(item["id"]) for item in self._list_remote_notes())

    def phone_home_path(self) -> Path:
        return self.internal_dir / "phone-home.json"

    def phone_home_stems(self) -> list[str]:
        return read_phone_home_stems(self.phone_home_path())

    def find_note_id_for_path(self, path: Path | str) -> str | None:
        """Vault markdown files do not map to Joplin notes, so never a match."""
        return None

    def note_id_for_sticky(self, path: Path | str) -> str | None:
        """Adopting vault files into stickies is a file-backend feature; the
        Joplin backend cannot own a vault markdown file, so this is always None."""
        return None

    def list_notes(self) -> list[NoteRecord]:
        remote_notes = sorted(self._list_remote_notes(), key=lambda item: str(item["id"]))
        return [
            NoteRecord(metadata=self._metadata_for_remote(remote), body=str(remote.get("body") or ""))
            for remote in remote_notes
        ]

    def list_open_notes(self) -> list[NoteRecord]:
        return [note for note in self.list_notes() if note.metadata.is_open]

    def update_geometry(self, note_id: str, *, x: int, y: int, width: int, height: int) -> None:
        metadata = self._metadata_for_id(note_id)
        metadata.x = x
        metadata.y = y
        metadata.width = width
        metadata.height = height
        metadata.updated_at = utc_now_iso()
        self.save_metadata(metadata)

    def hide_note(self, note_id: str) -> None:
        metadata = self._metadata_for_id(note_id)
        metadata.is_open = False
        metadata.updated_at = utc_now_iso()
        self.save_metadata(metadata)

    def reopen_note(self, note_id: str) -> NoteRecord:
        note = self.load_note(note_id)
        note.metadata.is_open = True
        note.metadata.updated_at = utc_now_iso()
        self.save_metadata(note.metadata)
        return note

    def delete_note(self, note_id: str, *, delete_body: bool = True) -> None:
        if delete_body:
            try:
                self.api.delete(f"/notes/{note_id}")
            except JoplinApiError as error:
                if error.status != 404:
                    raise
        self.meta_path(note_id).unlink(missing_ok=True)

    def prune_missing_note_files(self, *, protected_note_ids: set[str] | None = None) -> list[str]:
        """Drop local sidecars whose note no longer exists in the notebook.

        Quietly does nothing when Joplin is unreachable so tray menus and
        context menus keep working offline."""
        protected = protected_note_ids or set()
        try:
            remote_ids = set(self.list_note_ids())
        except JoplinApiError:
            return []
        removed: list[str] = []
        if not self.meta_dir.exists():
            return removed
        for metadata_path in self.meta_dir.glob("*.json"):
            note_id = metadata_path.stem
            if note_id in protected or note_id in remote_ids:
                continue
            metadata_path.unlink(missing_ok=True)
            removed.append(note_id)
        return removed

    def _fetch_remote_note(self, note_id: str) -> dict:
        try:
            return self.api.get(f"/notes/{note_id}", fields=NOTE_FIELDS)
        except JoplinApiError as error:
            if error.status == 404:
                raise FileNotFoundError(f"Joplin note not found: {note_id}") from error
            raise

    def _list_remote_notes(self) -> list[dict]:
        notes: list[dict] = []
        page = 1
        while True:
            data = self.api.get(f"/folders/{self.notebook_id()}/notes", fields=NOTE_FIELDS, page=page)
            notes.extend(data.get("items", []))
            if not data.get("has_more"):
                break
            page += 1
        return notes

    def _metadata_for_id(self, note_id: str) -> NoteMetadata:
        local = self._load_local_metadata(note_id)
        if local is not None:
            return local
        return self._metadata_for_remote(self._fetch_remote_note(note_id))

    def _metadata_for_remote(self, remote: dict) -> NoteMetadata:
        note_id = str(remote["id"])
        title = str(remote.get("title") or "Untitled note")
        local = self._load_local_metadata(note_id)
        if local is not None:
            local.title = title
            return local
        return self._default_metadata(note_id, title, remote)

    def _load_local_metadata(self, note_id: str) -> NoteMetadata | None:
        metadata_path = self.meta_path(note_id)
        if not metadata_path.exists():
            return None
        return NoteMetadata(**json.loads(metadata_path.read_text(encoding="utf-8")))

    def _default_metadata(self, note_id: str, title: str, remote: dict) -> NoteMetadata:
        """First sighting of a Joplin note on this device: closed, default
        size, and the next cascade position so newly adopted stickies fan out
        instead of stacking."""
        x, y = self._next_cascade_position()
        return NoteMetadata(
            note_id=note_id,
            title=title,
            x=x,
            y=y,
            width=self.settings.default_width,
            height=self.settings.default_height,
            is_open=False,
            created_at=iso_from_joplin_ms(remote.get("user_created_time")),
            updated_at=iso_from_joplin_ms(remote.get("user_updated_time")),
        )

    def _next_cascade_position(self) -> tuple[int, int]:
        known = len(list(self.meta_dir.glob("*.json"))) if self.meta_dir.exists() else 0
        offset = (known % CASCADE_SLOTS) * CASCADE_STEP
        return (CASCADE_BASE_X + offset, CASCADE_BASE_Y + offset)


def iso_from_joplin_ms(value: object) -> str:
    """Joplin reports user_created_time/user_updated_time in ms since epoch;
    convert to the UTC ISO format the sidecars use. Missing/zero means now."""
    try:
        millis = int(value)
    except (TypeError, ValueError):
        millis = 0
    if millis <= 0:
        return utc_now_iso()
    return (
        datetime.fromtimestamp(millis / 1000, timezone.utc)
        .replace(microsecond=0)
        .isoformat()
    )
