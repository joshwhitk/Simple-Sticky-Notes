from __future__ import annotations

import ctypes
import tkinter as tk

from .models import NoteRecord
from .settings import load_settings
from .storage import StickyStorage


NOTE_BG = "#ffd54f"
NOTE_TEXT = "#1f2933"
CORNER_RADIUS = 4


class NoteWindow:
    def __init__(self, manager: "StickyNotesApp", note: NoteRecord) -> None:
        self.manager = manager
        self.storage = manager.storage
        self.note = note
        self._autosave_job: str | None = None
        self._drag_origin: tuple[int, int] | None = None
        self._resize_origin: tuple[int, int, int, int] | None = None

        self.window = tk.Toplevel(manager.root)
        self.window.overrideredirect(True)
        self.window.configure(bg=NOTE_BG)
        self.window.geometry(
            f"{note.metadata.width}x{note.metadata.height}+{note.metadata.x}+{note.metadata.y}"
        )

        self.window.bind("<FocusOut>", self._save_geometry)
        self.window.bind("<Configure>", self._on_configure)

        self.container = tk.Frame(self.window, bg=NOTE_BG, highlightthickness=0, bd=0)
        self.container.pack(fill="both", expand=True)

        self.title_bar = tk.Frame(self.container, bg=NOTE_BG, height=24, bd=0, highlightthickness=0)
        self.title_bar.pack(fill="x")
        self.title_bar.bind("<ButtonPress-1>", self._start_drag)
        self.title_bar.bind("<B1-Motion>", self._drag)

        self.drag_spacer = tk.Frame(self.title_bar, bg=NOTE_BG, height=24)
        self.drag_spacer.pack(side="left", fill="x", expand=True)
        self.drag_spacer.bind("<ButtonPress-1>", self._start_drag)
        self.drag_spacer.bind("<B1-Motion>", self._drag)

        self.close_button = tk.Button(
            self.title_bar,
            text="X",
            bg=NOTE_BG,
            fg=NOTE_TEXT,
            bd=0,
            activebackground=NOTE_BG,
            activeforeground=NOTE_TEXT,
            padx=8,
            pady=2,
            command=self.hide_note,
        )
        self.close_button.pack(side="right")

        font_spec = (manager.settings.font_family, manager.settings.font_size)
        self.text = tk.Text(
            self.container,
            wrap="word",
            bd=0,
            relief="flat",
            undo=True,
            bg=NOTE_BG,
            fg=NOTE_TEXT,
            insertbackground=NOTE_TEXT,
            font=font_spec,
            padx=12,
            pady=10,
        )
        self.text.pack(fill="both", expand=True)
        self.text.insert("1.0", note.body)
        self.text.bind("<<Modified>>", self._on_modified)

        self.resize_zone = tk.Frame(self.container, bg=NOTE_BG, width=18, height=18, cursor="size_nw_se")
        self.resize_zone.place(relx=1.0, rely=1.0, anchor="se")
        self.resize_zone.bind("<ButtonPress-1>", self._start_resize)
        self.resize_zone.bind("<B1-Motion>", self._resize)

        self._apply_rounded_corners()

    def show(self) -> None:
        self.window.deiconify()
        self.window.lift()

    def hide_note(self) -> None:
        self.flush_note()
        self.storage.hide_note(self.note.metadata.note_id)
        self.window.destroy()
        self.manager.unregister(self.note.metadata.note_id)

    def flush_note(self) -> None:
        body = self.text.get("1.0", "end-1c")
        self.note.body = body
        self.note.metadata.title = first_line_title(body)
        x, y, width, height = self._geometry()
        self.note.metadata.x = x
        self.note.metadata.y = y
        self.note.metadata.width = width
        self.note.metadata.height = height
        self.note.metadata.is_open = True
        self.storage.save_note(self.note)

    def _on_modified(self, _event: object) -> None:
        self.text.edit_modified(False)
        if self._autosave_job:
            self.window.after_cancel(self._autosave_job)
        self._autosave_job = self.window.after(self.manager.settings.autosave_delay_ms, self.flush_note)

    def _save_geometry(self, _event: object | None = None) -> None:
        self.flush_note()

    def _on_configure(self, _event: object) -> None:
        self.resize_zone.place(relx=1.0, rely=1.0, anchor="se")
        self._apply_rounded_corners()

    def _geometry(self) -> tuple[int, int, int, int]:
        return (
            self.window.winfo_x(),
            self.window.winfo_y(),
            self.window.winfo_width(),
            self.window.winfo_height(),
        )

    def _start_drag(self, event: tk.Event) -> None:
        self._drag_origin = (event.x_root - self.window.winfo_x(), event.y_root - self.window.winfo_y())

    def _drag(self, event: tk.Event) -> None:
        if not self._drag_origin:
            return
        offset_x, offset_y = self._drag_origin
        self.window.geometry(f"+{event.x_root - offset_x}+{event.y_root - offset_y}")

    def _start_resize(self, event: tk.Event) -> None:
        self._resize_origin = (
            event.x_root,
            event.y_root,
            self.window.winfo_width(),
            self.window.winfo_height(),
        )

    def _resize(self, event: tk.Event) -> None:
        if not self._resize_origin:
            return
        start_x, start_y, start_width, start_height = self._resize_origin
        width = max(180, start_width + (event.x_root - start_x))
        height = max(120, start_height + (event.y_root - start_y))
        self.window.geometry(f"{width}x{height}+{self.window.winfo_x()}+{self.window.winfo_y()}")

    def _apply_rounded_corners(self) -> None:
        hwnd = self.window.winfo_id()
        width = max(self.window.winfo_width(), 1)
        height = max(self.window.winfo_height(), 1)
        region = ctypes.windll.gdi32.CreateRoundRectRgn(0, 0, width + 1, height + 1, CORNER_RADIUS, CORNER_RADIUS)
        ctypes.windll.user32.SetWindowRgn(hwnd, region, True)


class StickyNotesApp:
    def __init__(self) -> None:
        self.settings = load_settings()
        self.storage = StickyStorage(self.settings)
        self.windows: dict[str, NoteWindow] = {}
        self.root = tk.Tk()
        self.root.withdraw()
        self.root.protocol("WM_DELETE_WINDOW", self.shutdown)

    def run(self, *, create_new_note: bool = False) -> int:
        if create_new_note:
            self.new_note()
        else:
            open_notes = self.storage.list_open_notes()
            if not open_notes:
                self.new_note()
            else:
                for note in open_notes:
                    self.open_note(note)

        self.root.mainloop()
        return 0

    def new_note(self) -> None:
        self.open_note(self.storage.create_note())

    def open_note(self, note: NoteRecord) -> None:
        note.metadata.is_open = True
        self.storage.save_note(note)
        window = NoteWindow(self, note)
        self.windows[note.metadata.note_id] = window
        window.show()

    def unregister(self, note_id: str) -> None:
        self.windows.pop(note_id, None)
        if not self.windows:
            self.shutdown()

    def shutdown(self) -> None:
        for window in list(self.windows.values()):
            try:
                window.flush_note()
            except tk.TclError:
                pass
        self.root.quit()
        self.root.destroy()


def first_line_title(body: str) -> str:
    for line in body.splitlines():
        stripped = line.strip().lstrip("#").strip()
        if stripped:
            return stripped[:60]
    return "Untitled note"
