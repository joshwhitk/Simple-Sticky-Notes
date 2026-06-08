from __future__ import annotations

import argparse
import json
from typing import Any

from .models import NoteRecord
from .obsidian_integration import current_obsidian_vault_path
from .settings import load_settings
from .single_instance import is_instance_running, send_payload
from .storage import StickyStorage, note_title
from .windows_integration import edit_in_obsidian, show_folder


PREVIEW_LIMIT = 160


def get_storage() -> StickyStorage:
    return StickyStorage(load_settings())


def note_to_dict(note: NoteRecord) -> dict[str, Any]:
    note_path = get_storage().note_path(note.metadata.note_id)
    preview = note.body.strip().replace("\r\n", "\n").replace("\n", " ")
    return {
        "note_id": note.metadata.note_id,
        "title": note.metadata.title,
        "body": note.body,
        "preview": preview[:PREVIEW_LIMIT],
        "path": str(note_path),
        "x": note.metadata.x,
        "y": note.metadata.y,
        "width": note.metadata.width,
        "height": note.metadata.height,
        "is_open": note.metadata.is_open,
        "bg_color": note.metadata.bg_color,
        "created_at": note.metadata.created_at,
        "updated_at": note.metadata.updated_at,
    }


def list_notes(*, open_only: bool = False) -> dict[str, Any]:
    storage = get_storage()
    notes = storage.list_open_notes() if open_only else storage.list_notes()
    ordered = sorted(notes, key=lambda note: note.metadata.updated_at, reverse=True)
    return {
        "storage_root": str(storage.root),
        "count": len(ordered),
        "notes": [note_to_dict(note) for note in ordered],
    }


def get_note(note_id: str) -> dict[str, Any]:
    storage = get_storage()
    return note_to_dict(storage.load_note(note_id))


def get_status() -> dict[str, Any]:
    storage = get_storage()
    vault = current_obsidian_vault_path()
    notes = storage.list_notes()
    return {
        "storage_root": str(storage.root),
        "obsidian_vault": str(vault) if vault else None,
        "note_count": len(notes),
        "open_note_count": sum(1 for note in notes if note.metadata.is_open),
        "instance_running": is_instance_running(),
    }


def search_notes(query: str, *, limit: int = 20) -> dict[str, Any]:
    storage = get_storage()
    tokens = [token.casefold() for token in query.split() if token.strip()]
    matches: list[tuple[int, NoteRecord]] = []
    for note in storage.list_notes():
        haystack = " ".join(
            [
                note.metadata.title,
                note.body,
                str(storage.note_path(note.metadata.note_id).name),
            ]
        ).casefold()
        score = sum(1 for token in tokens if token in haystack)
        if score > 0 or not tokens:
            matches.append((score, note))

    matches.sort(key=lambda item: (item[0], item[1].metadata.updated_at), reverse=True)
    selected = matches[: max(1, limit)]
    return {
        "query": query,
        "count": len(selected),
        "notes": [note_to_dict(note) for _, note in selected],
    }


def notes_changed_since(since: str, *, limit: int = 20) -> dict[str, Any]:
    storage = get_storage()
    changed = [
        note
        for note in storage.list_notes()
        if note.metadata.updated_at >= since
    ]
    ordered = sorted(changed, key=lambda note: note.metadata.updated_at, reverse=True)
    selected = ordered[: max(1, limit)]
    return {
        "since": since,
        "count": len(selected),
        "notes": [note_to_dict(note) for note in selected],
    }


def create_note(
    *,
    body: str,
    title: str | None = None,
    bg_color: str = "#ffd54f",
    is_open: bool = False,
    x: int = 80,
    y: int = 80,
    width: int | None = None,
    height: int | None = None,
) -> dict[str, Any]:
    storage = get_storage()
    note = storage.create_note(
        title=title or note_title(body),
        body=body,
        x=x,
        y=y,
        width=width,
        height=height,
        bg_color=bg_color,
    )
    if not is_open:
        storage.hide_note(note.metadata.note_id)
        note = storage.load_note(note.metadata.note_id)
    return note_to_dict(note)


def create_visible_note(
    *,
    body: str,
    title: str | None = None,
    bg_color: str = "#ffd54f",
    x: int = 80,
    y: int = 80,
) -> dict[str, Any]:
    created = create_note(
        body=body,
        title=title,
        bg_color=bg_color,
        is_open=True,
        x=x,
        y=y,
    )
    sent = send_payload(
        {
            "command": "show-note",
            "note_id": created["note_id"],
        }
    )
    created["instance_running"] = sent
    return created


def edit_note(
    note_id: str,
    *,
    body: str | None = None,
    append_text: str | None = None,
    prepend_text: str | None = None,
    bg_color: str | None = None,
    is_open: bool | None = None,
) -> dict[str, Any]:
    storage = get_storage()
    note = storage.load_note(note_id)
    if body is not None:
        note.body = body
    if prepend_text:
        note.body = f"{prepend_text}{note.body}"
    if append_text:
        note.body = f"{note.body}{append_text}"
    if bg_color is not None:
        note.metadata.bg_color = bg_color
    if is_open is not None:
        note.metadata.is_open = is_open
    storage.save_note(note)
    return note_to_dict(storage.load_note(note_id))


def show_note_window(note_id: str) -> dict[str, Any]:
    storage = get_storage()
    note = storage.reopen_note(note_id)
    sent = send_payload({"command": "show-note", "note_id": note_id})
    result = note_to_dict(note)
    result["instance_running"] = sent
    return result


def move_resize_note(
    note_id: str,
    *,
    x: int,
    y: int,
    width: int,
    height: int,
    focus: bool = False,
) -> dict[str, Any]:
    storage = get_storage()
    storage.update_geometry(note_id, x=x, y=y, width=width, height=height)
    sent = send_payload(
        {
            "command": "move-resize-note",
            "note_id": note_id,
            "x": x,
            "y": y,
            "width": width,
            "height": height,
            "focus": focus,
        }
    )
    result = note_to_dict(storage.load_note(note_id))
    result["instance_running"] = sent
    return result


def tidy_notes() -> dict[str, Any]:
    sent = send_payload({"command": "tidy-notes"})
    return {"ok": sent, "instance_running": sent}


def hide_note(note_id: str) -> dict[str, Any]:
    storage = get_storage()
    storage.hide_note(note_id)
    return note_to_dict(storage.load_note(note_id))


def reopen_note(note_id: str) -> dict[str, Any]:
    storage = get_storage()
    return note_to_dict(storage.reopen_note(note_id))


def delete_note(note_id: str) -> dict[str, Any]:
    storage = get_storage()
    storage.delete_note(note_id)
    return {"deleted": True, "note_id": note_id}


def open_note_in_obsidian(note_id: str) -> dict[str, Any]:
    storage = get_storage()
    note_path = storage.note_path(note_id)
    edit_in_obsidian(note_path)
    return {"opened": True, "note_id": note_id, "path": str(note_path)}


def reveal_note_in_explorer(note_id: str) -> dict[str, Any]:
    storage = get_storage()
    note_path = storage.note_path(note_id)
    show_folder(note_path.parent)
    return {"revealed": True, "note_id": note_id, "path": str(note_path.parent)}


def dispatch(command: str, payload: dict[str, Any]) -> dict[str, Any]:
    if command == "get-status":
        return get_status()
    if command == "list-notes":
        return list_notes(open_only=bool(payload.get("open_only", False)))
    if command == "get-note":
        return get_note(str(payload["note_id"]))
    if command == "search-notes":
        return search_notes(str(payload.get("query", "")), limit=int(payload.get("limit", 20)))
    if command == "notes-changed-since":
        return notes_changed_since(str(payload.get("since", "")), limit=int(payload.get("limit", 20)))
    if command == "create-note":
        return create_note(
            body=str(payload.get("body", "")),
            title=payload.get("title"),
            bg_color=str(payload.get("bg_color", "#ffd54f")),
            is_open=bool(payload.get("is_open", False)),
            x=int(payload.get("x", 80)),
            y=int(payload.get("y", 80)),
            width=int(payload["width"]) if payload.get("width") is not None else None,
            height=int(payload["height"]) if payload.get("height") is not None else None,
        )
    if command == "create-visible-note":
        return create_visible_note(
            body=str(payload.get("body", "")),
            title=payload.get("title"),
            bg_color=str(payload.get("bg_color", "#ffd54f")),
            x=int(payload.get("x", 80)),
            y=int(payload.get("y", 80)),
        )
    if command == "edit-note":
        return edit_note(
            str(payload["note_id"]),
            body=payload.get("body"),
            append_text=payload.get("append_text"),
            prepend_text=payload.get("prepend_text"),
            bg_color=payload.get("bg_color"),
            is_open=payload.get("is_open"),
        )
    if command == "show-note-window":
        return show_note_window(str(payload["note_id"]))
    if command == "move-resize-note":
        return move_resize_note(
            str(payload["note_id"]),
            x=int(payload["x"]),
            y=int(payload["y"]),
            width=int(payload["width"]),
            height=int(payload["height"]),
            focus=bool(payload.get("focus", False)),
        )
    if command == "tidy-notes":
        return tidy_notes()
    if command == "hide-note":
        return hide_note(str(payload["note_id"]))
    if command == "reopen-note":
        return reopen_note(str(payload["note_id"]))
    if command == "delete-note":
        return delete_note(str(payload["note_id"]))
    if command == "open-note-in-obsidian":
        return open_note_in_obsidian(str(payload["note_id"]))
    if command == "reveal-note-in-explorer":
        return reveal_note_in_explorer(str(payload["note_id"]))
    raise ValueError(f"unknown command: {command}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Simple Sticky Notes service API")
    parser.add_argument("command")
    parser.add_argument("payload", nargs="?", default="{}")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = json.loads(args.payload)
    result = dispatch(args.command, payload)
    print(json.dumps(result, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
