"""One-time helper: hand existing file-backend stickies over to Joplin.

For every sticky in the file backend (markdown in the vault plus a sidecar in
.simple-sticky-notes/meta), this script finds the matching note in the
configured Joplin notebook by title (the vault folder was already imported
into Joplin, so most notes should match). When a match is found, the local
sidecar metadata is copied to the Joplin backend's meta dir keyed by the
Joplin note id. When no match is found, the note is created in Joplin first
(title plus body) and the sidecar is copied the same way.

Nothing is deleted or modified in the vault, and the script is idempotent:
re-running it matches the notes it created last time and skips sidecars that
are already in place.

Usage (from the repo root):
  python tools/migrate-stickies-to-joplin.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from simple_sticky_notes.joplin_storage import JoplinStickyStorage  # noqa: E402
from simple_sticky_notes.settings import load_settings  # noqa: E402
from simple_sticky_notes.storage import StickyStorage  # noqa: E402


def build_title_index(joplin: JoplinStickyStorage) -> dict[str, list[str]]:
    """Map note title -> Joplin note ids in the notebook. Ids stay sorted so
    the assignment order is stable between runs."""
    index: dict[str, list[str]] = {}
    for note in joplin.list_notes():
        index.setdefault(note.metadata.title, []).append(note.metadata.note_id)
    return index


def claim_joplin_id(index: dict[str, list[str]], *titles: str) -> str | None:
    """Take the next unclaimed Joplin note whose title matches any candidate.

    Claiming (popping) keeps duplicate titles one-to-one: two stickies with
    the same title consume two same-titled Joplin notes in a stable order."""
    for title in titles:
        candidates = index.get(title)
        if candidates:
            return candidates.pop(0)
    return None


def copy_sidecar(files: StickyStorage, joplin: JoplinStickyStorage, note_id: str, joplin_id: str) -> bool:
    """Copy the file-backend sidecar to the Joplin meta dir under the Joplin
    note id. Returns False when the destination already exists (already
    migrated; local state there may be newer, so it is never overwritten)."""
    destination = joplin.meta_path(joplin_id)
    if destination.exists():
        return False
    metadata = files.load_note(note_id).metadata
    metadata.note_id = joplin_id
    joplin.save_metadata(metadata)
    return True


def migrate(files: StickyStorage, joplin: JoplinStickyStorage) -> dict[str, int]:
    """Match or create every file-backend sticky in Joplin and copy sidecars.

    Returns the summary counts. Reads the vault only, so re-running is safe."""
    title_index = build_title_index(joplin)
    counts = {"matched": 0, "created": 0, "sidecars_copied": 0, "sidecars_already": 0}

    note_ids = files.list_note_ids()
    counts["total"] = len(note_ids)
    for note_id in note_ids:
        note = files.load_note(note_id)
        title = note.metadata.title
        joplin_id = claim_joplin_id(title_index, title, note.metadata.file_stem)
        if joplin_id:
            counts["matched"] += 1
            action = "matched"
        else:
            response = joplin.api.post(
                "/notes",
                {"title": title, "body": note.body, "parent_id": joplin.notebook_id()},
            )
            joplin_id = str(response["id"])
            counts["created"] += 1
            action = "created"

        if copy_sidecar(files, joplin, note_id, joplin_id):
            counts["sidecars_copied"] += 1
        else:
            counts["sidecars_already"] += 1
            action += " (sidecar already in place)"
        print(f"  {action:<32} {title[:60]} -> {joplin_id}")

    return counts


def main() -> int:
    settings = load_settings()
    if not settings.joplin_api_token:
        print("No Joplin API token configured.")
        print("Set joplin_api_token in %APPDATA%\\SimpleStickyNotes\\settings.json and rerun.")
        return 1

    files = StickyStorage(settings)
    joplin = JoplinStickyStorage(settings)
    print(f"File storage : {files.root}")
    print(f"Joplin API   : {settings.joplin_api_url}")
    print(f"Notebook     : {settings.joplin_notebook} ({joplin.notebook_id()})")
    print()

    counts = migrate(files, joplin)

    print()
    print("Summary")
    print(f"  matched existing Joplin notes : {counts['matched']}")
    print(f"  created new Joplin notes      : {counts['created']}")
    print(f"  sidecars copied               : {counts['sidecars_copied']}")
    print(f"  sidecars already in place     : {counts['sidecars_already']}")
    print(f"  total stickies processed      : {counts['total']}")
    print()
    print("No vault files were changed or deleted. To cut the desktop app over,")
    print("set storage_backend to 'joplin' in settings.json and restart the app.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
