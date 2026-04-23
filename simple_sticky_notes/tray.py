from __future__ import annotations

from typing import TYPE_CHECKING

import pystray
from PIL import Image

from .models import NoteRecord
from .windows_integration import resource_root

if TYPE_CHECKING:
    from .app import StickyNotesApp


class TrayController:
    def __init__(self, app: "StickyNotesApp") -> None:
        self.app = app
        self.icon = pystray.Icon(
            "simple-sticky-notes",
            self._load_icon_image(),
            "Simple Sticky Notes",
            menu=pystray.Menu(self._build_menu_items),
        )
        self._started = False

    def start(self) -> None:
        if self._started:
            return
        self.icon.run_detached()
        self._started = True

    def stop(self) -> None:
        if not self._started:
            return
        self.icon.stop()
        self._started = False

    def refresh(self) -> None:
        if not self._started:
            return
        self.icon.update_menu()

    def _load_icon_image(self) -> Image.Image:
        icon_path = resource_root() / "assets" / "icons" / "simple-sticky-notes-64.png"
        with Image.open(icon_path) as image:
            return image.copy()

    def _build_menu_items(self):
        return (
            pystray.MenuItem("New Sticky", self._schedule(self.app.new_note)),
            pystray.MenuItem("Notes", pystray.Menu(self._build_notes_submenu)),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Exit", self._schedule(self.app.shutdown)),
        )

    def _build_notes_submenu(self):
        notes = self.app.list_notes_for_menu()
        if not notes:
            return (pystray.MenuItem("(No notes yet)", lambda: None, enabled=False),)
        return tuple(
            pystray.MenuItem(
                tray_note_menu_label(note),
                self._schedule(lambda note_id=note.metadata.note_id: self.app.show_note(note_id)),
            )
            for note in notes
        )

    def _schedule(self, callback):
        def runner(*_args):
            self.app.root.after(0, callback)

        return runner


def tray_note_menu_label(note: NoteRecord) -> str:
    state = "open" if note.metadata.is_open else "hidden"
    title = note.metadata.title.strip() or f"Note {note.metadata.note_id[:6]}"
    return f"[{state}] {title}"
