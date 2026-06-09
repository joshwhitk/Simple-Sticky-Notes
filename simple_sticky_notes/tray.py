from __future__ import annotations

from typing import TYPE_CHECKING

import pystray
from PIL import Image

from .models import NoteRecord
from .windows_integration import resource_root

if TYPE_CHECKING:
    from .app import StickyNotesApp

try:
    import pystray._win32 as pystray_win32
except ImportError:  # pragma: no cover - Windows is the only supported runtime.
    pystray_win32 = None


class StickyNotesTrayIcon(pystray.Icon):
    def _on_notify(self, wparam, lparam):
        if (
            pystray_win32 is not None
            and self._menu_handle
            and lparam in (pystray_win32.win32.WM_LBUTTONUP, pystray_win32.win32.WM_RBUTTONUP)
        ):
            self._show_popup_menu()
            return
        super()._on_notify(wparam, lparam)

    def _show_popup_menu(self) -> None:
        if pystray_win32 is None or not self._menu_handle:
            return

        pystray_win32.win32.SetForegroundWindow(self._hwnd)

        point = pystray_win32.wintypes.POINT()
        pystray_win32.win32.GetCursorPos(pystray_win32.ctypes.byref(point))

        hmenu, descriptors = self._menu_handle
        index = pystray_win32.win32.TrackPopupMenuEx(
            hmenu,
            pystray_win32.win32.TPM_RIGHTALIGN
            | pystray_win32.win32.TPM_BOTTOMALIGN
            | pystray_win32.win32.TPM_RETURNCMD,
            point.x,
            point.y,
            self._menu_hwnd,
            None,
        )
        if index > 0:
            descriptors[index - 1](self)


class TrayController:
    def __init__(self, app: "StickyNotesApp") -> None:
        self.app = app
        self.icon = StickyNotesTrayIcon(
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
            pystray.MenuItem("View Sticky Note", pystray.Menu(self._build_recent_submenu)),
            pystray.MenuItem("Show phone sticky notes", self._schedule(self.app.show_phone_notes)),
            pystray.MenuItem("Notes", pystray.Menu(self._build_notes_submenu)),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Exit", self._schedule(self.app.shutdown)),
        )

    def _build_recent_submenu(self):
        notes = self.app.list_recent_notes_for_menu(20)
        if not notes:
            return (pystray.MenuItem("(No notes yet)", lambda: None, enabled=False),)
        return tuple(
            pystray.MenuItem(
                tray_note_menu_label(note),
                self._schedule(lambda note_id=note.metadata.note_id: self.app.show_note(note_id)),
            )
            for note in notes
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
