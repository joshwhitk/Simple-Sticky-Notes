from __future__ import annotations

import ctypes
import tkinter as tk
from pathlib import Path
from tkinter import filedialog
from tkinter import font as tkfont
from tkinter import messagebox
from typing import Callable

from .models import NoteRecord
from .runtime_state import mark_app_launch, mark_clean_shutdown
from .settings import copy_storage_contents, load_settings, save_settings
from .storage import StickyStorage
from .tray import TrayController
from .windows_integration import edit_in_notepad, edit_in_obsidian, show_folder


DEFAULT_NOTE_BG = "#ffd54f"
NOTE_TEXT = "#1f2933"
CORNER_RADIUS = 4
EXTERNAL_SYNC_POLL_MS = 1000
MIN_WIDTH = 180
MIN_HEIGHT = 120
DRAG_ZONE_HEIGHT = 28
RESIZE_HOTSPOT_SIZE = 16
CLOSE_BUTTON_SIZE = 24
CLOSE_BUTTON_MARGIN = 6
TEXT_RIGHT_MARGIN = CLOSE_BUTTON_SIZE + (CLOSE_BUTTON_MARGIN * 2)

NOTE_COLORS: dict[str, str] = {
    "Yellow": "#ffd54f",
    "Cream": "#fff3bf",
    "Green": "#c8e6c9",
    "Blue": "#bbdefb",
    "Pink": "#f8bbd0",
    "Orange": "#ffcc80",
}

FONT_SIZE_OPTIONS = [11, 12, 14, 16, 18, 20, 24, 28]
COMMON_FONT_FAMILIES = [
    "Segoe UI",
    "Aptos",
    "Calibri",
    "Arial",
    "Bahnschrift",
    "Cambria",
    "Consolas",
    "Georgia",
    "Tahoma",
    "Times New Roman",
    "Trebuchet MS",
    "Verdana",
]


class NoteWindow:
    def __init__(self, manager: "StickyNotesApp", note: NoteRecord) -> None:
        self.manager = manager
        self.storage = manager.storage
        self.note = note
        self._autosave_job: str | None = None
        self._external_sync_job: str | None = None
        self._drag_origin: tuple[int, int] | None = None
        self._resize_origin: tuple[int, int, int, int] | None = None

        self.window = tk.Toplevel(manager.root)
        self.window.overrideredirect(True)
        self.window.geometry(
            f"{note.metadata.width}x{note.metadata.height}+{note.metadata.x}+{note.metadata.y}"
        )

        self.window.bind("<FocusOut>", self._save_geometry)
        self.window.bind("<FocusIn>", self._on_focus_in)
        self.window.bind("<Configure>", self._on_configure)
        self.window.bind("<ButtonRelease-1>", self._clear_pointer_state)
        self.window.bind("<Motion>", self._update_cursor)

        self.container = tk.Frame(self.window, highlightthickness=0, bd=0)
        self.container.pack(fill="both", expand=True)
        self.container.bind("<ButtonPress-1>", self._on_container_pointer_down)
        self.container.bind("<B1-Motion>", self._on_container_pointer_drag)
        self.container.bind("<ButtonRelease-1>", self._clear_pointer_state)

        self.drag_zone = tk.Frame(self.container, bd=0, highlightthickness=0)
        self.drag_zone.place(x=0, y=0, relwidth=1.0, width=-TEXT_RIGHT_MARGIN, height=DRAG_ZONE_HEIGHT)
        self.drag_zone.bind("<ButtonPress-1>", self._on_drag_zone_pointer_down)
        self.drag_zone.bind("<B1-Motion>", self._on_drag_zone_pointer_drag)
        self.drag_zone.bind("<ButtonRelease-1>", self._clear_pointer_state)

        self.body = tk.Frame(self.container, bd=0, highlightthickness=0)
        self.body.place(
            x=0,
            y=DRAG_ZONE_HEIGHT,
            relwidth=1.0,
            relheight=1.0,
            width=-TEXT_RIGHT_MARGIN,
            height=-DRAG_ZONE_HEIGHT,
        )
        self.body.bind("<ButtonPress-1>", self._on_body_pointer_down)
        self.body.bind("<ButtonRelease-1>", self._clear_pointer_state)

        self.close_button = tk.Button(
            self.container,
            text="X",
            fg=NOTE_TEXT,
            bd=0,
            highlightthickness=0,
            relief="flat",
            font=("Arial", 10, "bold"),
            cursor="hand2",
            takefocus=0,
            command=self.hide_note,
        )
        self.close_button.place(width=CLOSE_BUTTON_SIZE, height=CLOSE_BUTTON_SIZE)

        self.text = tk.Text(
            self.body,
            wrap="word",
            bd=0,
            relief="flat",
            undo=True,
            fg=NOTE_TEXT,
            insertbackground=NOTE_TEXT,
            padx=12,
            pady=10,
            exportselection=False,
        )
        self.text.pack(fill="both", expand=True)
        self.text.insert("1.0", editor_body_for_display(note.body))
        self.text.bind("<<Modified>>", self._on_modified)
        self.text.bind("<ButtonPress-1>", self._on_text_pointer_down)
        self.text.bind("<B1-Motion>", self._on_text_pointer_drag)
        self.text.bind("<ButtonRelease-1>", self._clear_pointer_state)
        self.text.bind("<Motion>", self._update_cursor)

        self._bind_context_menu(self.window)
        self._bind_context_menu(self.container)
        self._bind_context_menu(self.drag_zone)
        self._bind_context_menu(self.body)
        self._bind_context_menu(self.text)
        self._bind_context_menu(self.close_button)

        self.apply_visual_style()
        self.apply_font_settings()
        self._apply_rounded_corners()
        self._position_controls()
        self._last_disk_signature = self._current_disk_signature()
        self._schedule_external_sync()

    def show(self) -> None:
        self.window.deiconify()
        self.window.lift()

    def focus_for_edit(self) -> None:
        self.show()
        self.window.focus_force()
        self._focus_editor_for_append()

    def hide_note(self) -> None:
        if self._external_sync_job:
            self.window.after_cancel(self._external_sync_job)
            self._external_sync_job = None
        self.flush_note()
        self.storage.hide_note(self.note.metadata.note_id)
        self.window.destroy()
        self.manager.unregister(self.note.metadata.note_id)

    def flush_note(self) -> None:
        if self._autosave_job:
            try:
                self.window.after_cancel(self._autosave_job)
            except tk.TclError:
                pass
            self._autosave_job = None
        body = persisted_body_from_editor(self.text.get("1.0", "end-1c"))
        self.note.body = body
        self.note.metadata.title = first_line_title(body)
        x, y, width, height = self._geometry()
        self.note.metadata.x = x
        self.note.metadata.y = y
        self.note.metadata.width = width
        self.note.metadata.height = height
        self.note.metadata.is_open = True
        self.storage.save_note(self.note)
        self._last_disk_signature = self._current_disk_signature()

    def apply_visual_style(self) -> None:
        bg_color = self.note.metadata.bg_color or DEFAULT_NOTE_BG
        selection_bg = selection_bg_for(bg_color)
        self.window.configure(bg=bg_color)
        self.container.configure(bg=bg_color)
        self.drag_zone.configure(bg=bg_color)
        self.body.configure(bg=bg_color)
        self.close_button.configure(
            bg=bg_color,
            activebackground=bg_color,
            activeforeground=NOTE_TEXT,
        )
        self.text.configure(
            bg=bg_color,
            selectbackground=selection_bg,
            inactiveselectbackground=selection_bg,
        )

    def apply_font_settings(self) -> None:
        self.text.configure(font=(self.manager.settings.font_family, self.manager.settings.font_size))

    def set_color(self, color_hex: str) -> None:
        self.note.metadata.bg_color = color_hex
        self.apply_visual_style()
        self.flush_note()

    def split_selection_to_new_sticky(self) -> None:
        selected_text = self.selected_text()
        if not selected_text:
            return
        self.text.delete("sel.first", "sel.last")
        self._clear_selection()
        self.flush_note()
        self.manager.create_and_open_note(
            body=selected_text,
            x=self.window.winfo_x() + 32,
            y=self.window.winfo_y() + 32,
            bg_color=self.note.metadata.bg_color,
        )

    def selected_text(self) -> str:
        try:
            return self.text.get("sel.first", "sel.last")
        except tk.TclError:
            return ""

    def open_note_in_notepad(self) -> None:
        self._run_external_action(lambda: edit_in_notepad(self.storage.note_path(self.note.metadata.note_id)))

    def open_note_in_obsidian(self) -> None:
        self._run_external_action(lambda: edit_in_obsidian(self.storage.note_path(self.note.metadata.note_id)))

    def open_note_folder(self) -> None:
        self._run_external_action(lambda: show_folder(self.storage.note_path(self.note.metadata.note_id).parent))

    def _run_external_action(self, action: Callable[[], None]) -> None:
        try:
            self.flush_note()
            action()
        except Exception as exc:
            messagebox.showerror("Simple Sticky Notes", str(exc), parent=self.window)

    def _show_context_menu(self, event: tk.Event) -> str:
        self.manager.reconcile_storage(refresh_tray=False)
        menu = self._build_context_menu()
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()
        return "break"

    def _build_context_menu(self) -> tk.Menu:
        menu = tk.Menu(self.window, tearoff=0)

        notes_menu = tk.Menu(menu, tearoff=0)
        all_notes = self.manager.list_notes_for_menu()
        if all_notes:
            for listed_note in all_notes:
                label = note_menu_label(listed_note)
                notes_menu.add_command(
                    label=label,
                    command=lambda note_id=listed_note.metadata.note_id: self.manager.show_note(note_id),
                )
        else:
            notes_menu.add_command(label="(No notes yet)", state="disabled")
        menu.add_cascade(label="Notes", menu=notes_menu)
        menu.add_command(label="New Sticky", command=self.manager.new_note)
        menu.add_separator()

        color_menu = tk.Menu(menu, tearoff=0)
        for index, (name, color_hex) in enumerate(NOTE_COLORS.items()):
            color_menu.add_command(
                label=name,
                command=lambda color_hex=color_hex: self.set_color(color_hex),
            )
            try:
                color_menu.entryconfigure(index, background=color_hex, activebackground=color_hex)
            except tk.TclError:
                pass
        menu.add_cascade(label="Color", menu=color_menu)

        font_size_menu = tk.Menu(menu, tearoff=0)
        for size in FONT_SIZE_OPTIONS:
            label = f"{size} pt"
            if size == self.manager.settings.font_size:
                label = f"* {label}"
            font_size_menu.add_command(
                label=label,
                command=lambda size=size: self.manager.update_font_settings(font_size=size),
            )
        menu.add_cascade(label="Font Size", menu=font_size_menu)

        font_family_menu = tk.Menu(menu, tearoff=0)
        for family in self.manager.available_font_families():
            label = family
            if family == self.manager.settings.font_family:
                label = f"* {label}"
            font_family_menu.add_command(
                label=label,
                command=lambda family=family: self.manager.update_font_settings(font_family=family),
            )
        menu.add_cascade(label="Font", menu=font_family_menu)

        menu.add_separator()
        menu.add_command(label="Show Folder", command=self.open_note_folder)
        menu.add_command(label="Set Storage Folder", command=lambda: self.manager.choose_storage_folder(self.window))
        menu.add_command(label="Edit in Notepad", command=self.open_note_in_notepad)
        menu.add_command(label="Edit in Obsidian", command=self.open_note_in_obsidian)

        if self.selected_text():
            menu.add_separator()
            menu.add_command(label="Split to New Sticky", command=self.split_selection_to_new_sticky)

        return menu

    def _on_modified(self, _event: object) -> None:
        self.text.edit_modified(False)
        if self._autosave_job:
            self.window.after_cancel(self._autosave_job)
        self._autosave_job = self.window.after(self.manager.settings.autosave_delay_ms, self.flush_note)

    def _save_geometry(self, _event: object | None = None) -> None:
        self.flush_note()

    def _on_configure(self, _event: object) -> None:
        self._position_controls()
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
        width = max(MIN_WIDTH, start_width + (event.x_root - start_x))
        height = max(MIN_HEIGHT, start_height + (event.y_root - start_y))
        self.window.geometry(f"{width}x{height}+{self.window.winfo_x()}+{self.window.winfo_y()}")

    def _apply_rounded_corners(self) -> None:
        hwnd = self.window.winfo_id()
        width = max(self.window.winfo_width(), 1)
        height = max(self.window.winfo_height(), 1)
        diameter = CORNER_RADIUS * 2
        region = ctypes.windll.gdi32.CreateRoundRectRgn(0, 0, width + 1, height + 1, diameter, diameter)
        ctypes.windll.user32.SetWindowRgn(hwnd, region, True)

    def _position_controls(self) -> None:
        self.close_button.place(
            x=max(self.window.winfo_width() - CLOSE_BUTTON_SIZE - CLOSE_BUTTON_MARGIN, 0),
            y=CLOSE_BUTTON_MARGIN,
        )

    def _update_cursor(self, event: tk.Event) -> None:
        local_x, local_y = self._local_pointer(event)
        cursor = self._cursor_for_widget(event.widget, local_x, local_y)
        target = event.widget if isinstance(event.widget, tk.Misc) else self.window
        target.configure(cursor=cursor)

    def _on_container_pointer_down(self, event: tk.Event) -> str | None:
        local_x, local_y = self._local_pointer(event)
        if self._is_resize_hotspot(local_x, local_y):
            self._start_resize(event)
            return "break"
        if self._is_drag_zone(local_x, local_y):
            return "break"
        self._focus_editor_for_append()
        return None

    def _on_container_pointer_drag(self, event: tk.Event) -> str | None:
        if self._resize_origin:
            self._resize(event)
            return "break"
        return None

    def _on_drag_zone_pointer_down(self, event: tk.Event) -> str | None:
        self._clear_selection()
        self._start_drag(event)
        return "break"

    def _on_drag_zone_pointer_drag(self, event: tk.Event) -> str | None:
        if self._drag_origin:
            self._drag(event)
            return "break"
        return None

    def _on_body_pointer_down(self, _event: tk.Event) -> str | None:
        self._focus_editor_for_append()
        return None

    def _on_text_pointer_down(self, event: tk.Event) -> str | None:
        local_x, local_y = self._local_pointer(event)
        if self._is_resize_hotspot(local_x, local_y):
            self._start_resize(event)
            return "break"
        return None

    def _on_text_pointer_drag(self, event: tk.Event) -> str | None:
        if self._resize_origin:
            self._resize(event)
            return "break"
        return None

    def _clear_pointer_state(self, _event: tk.Event | None = None) -> None:
        resized = self._resize_origin is not None
        dragged = self._drag_origin is not None
        self._drag_origin = None
        self._resize_origin = None
        if resized or dragged:
            self._clear_selection()

    def _is_drag_zone(self, x: int, y: int) -> bool:
        return y <= DRAG_ZONE_HEIGHT and x < (self.window.winfo_width() - CLOSE_BUTTON_SIZE - (CLOSE_BUTTON_MARGIN * 2))

    def _is_resize_hotspot(self, x: int, y: int) -> bool:
        return (
            x >= self.window.winfo_width() - RESIZE_HOTSPOT_SIZE
            and y >= self.window.winfo_height() - RESIZE_HOTSPOT_SIZE
        )

    def _local_pointer(self, event: tk.Event) -> tuple[int, int]:
        return (event.x_root - self.window.winfo_x(), event.y_root - self.window.winfo_y())

    def _cursor_for_widget(self, widget: object, x: int, y: int) -> str:
        if self._is_resize_hotspot(x, y):
            return "size_nw_se"
        if widget == self.drag_zone:
            return "fleur"
        if widget == self.text:
            return "xterm"
        return "arrow"

    def _on_focus_in(self, _event: tk.Event) -> None:
        self._clear_selection()
        self._refresh_from_disk_if_needed()

    def _focus_editor_for_append(self) -> None:
        self.text.focus_set()
        self._place_insert_at_append()

    def _clear_selection(self) -> None:
        self.text.tag_remove("sel", "1.0", "end")

    def _place_insert_at_append(self) -> None:
        self._clear_selection()
        self.text.mark_set("insert", "end-1c")
        self.text.see("insert")

    def _schedule_external_sync(self) -> None:
        self._external_sync_job = self.window.after(EXTERNAL_SYNC_POLL_MS, self._poll_external_changes)

    def _poll_external_changes(self) -> None:
        try:
            self._refresh_from_disk_if_needed()
        finally:
            if self.window.winfo_exists():
                self._schedule_external_sync()

    def _refresh_from_disk_if_needed(self) -> None:
        current_signature = self._current_disk_signature()
        if current_signature == self._last_disk_signature:
            return
        if self._autosave_job:
            return
        if current_signature is None:
            self._handle_deleted_from_disk()
            return

        disk_body = self._current_disk_body()
        self._last_disk_signature = current_signature
        if disk_body == self.note.body:
            return

        self.note.body = disk_body
        self.note.metadata.title = first_line_title(disk_body)
        self.storage.save_note(self.note)
        self._last_disk_signature = self._current_disk_signature()
        self.text.delete("1.0", "end")
        self.text.insert("1.0", editor_body_for_display(disk_body))
        self.text.edit_modified(False)
        self._place_insert_at_append()

    def _current_disk_signature(self) -> tuple[str, int, int] | None:
        note_path = self.storage.note_path(self.note.metadata.note_id)
        if not note_path.exists():
            return None
        stat = note_path.stat()
        return (str(note_path), stat.st_mtime_ns, stat.st_size)

    def _current_disk_body(self) -> str:
        note_path = self.storage.note_path(self.note.metadata.note_id)
        if not note_path.exists():
            return ""
        return note_path.read_text(encoding="utf-8")

    def _handle_deleted_from_disk(self) -> None:
        if self._autosave_job:
            try:
                self.window.after_cancel(self._autosave_job)
            except tk.TclError:
                pass
            self._autosave_job = None
        if self._external_sync_job:
            try:
                self.window.after_cancel(self._external_sync_job)
            except tk.TclError:
                pass
            self._external_sync_job = None
        self.storage.delete_note(self.note.metadata.note_id, delete_body=False)
        self.window.destroy()
        self.manager.unregister(self.note.metadata.note_id)

    def _bind_context_menu(self, widget: tk.Misc) -> None:
        widget.bind("<Button-2>", self._show_context_menu)
        widget.bind("<Button-3>", self._show_context_menu)


class StickyNotesApp:
    def __init__(self) -> None:
        self.settings = load_settings()
        self.storage = StickyStorage(self.settings)
        self.windows: dict[str, NoteWindow] = {}
        self._is_shutting_down = False
        self.session_id = ""
        self.previous_shutdown_clean = True
        self.root = tk.Tk()
        self.root.withdraw()
        self.root.protocol("WM_DELETE_WINDOW", self.shutdown)
        self.tray = TrayController(self)

    def run(self, *, create_new_note: bool = False) -> int:
        self.session_id, self.previous_shutdown_clean = mark_app_launch()
        self.tray.start()
        self.reconcile_storage()
        if create_new_note:
            self.new_note()
        else:
            open_notes = self.storage.list_open_notes()
            for note in open_notes:
                self.open_note(note)

        self.root.mainloop()
        return 0

    def new_note(self) -> None:
        self.create_and_open_note()

    def create_and_open_note(
        self,
        *,
        body: str = "",
        x: int = 80,
        y: int = 80,
        bg_color: str = DEFAULT_NOTE_BG,
    ) -> None:
        title = first_line_title(body)
        note = self.storage.create_note(
            title=title,
            body=body,
            x=x,
            y=y,
            bg_color=bg_color,
        )
        self.open_note(note)

    def open_note(self, note: NoteRecord) -> None:
        existing = self.windows.get(note.metadata.note_id)
        if existing:
            existing.focus_for_edit()
            return

        note.metadata.is_open = True
        self.storage.save_note(note)
        window = NoteWindow(self, note)
        self.windows[note.metadata.note_id] = window
        window.focus_for_edit()
        self.tray.refresh()

    def show_note(self, note_id: str) -> None:
        existing = self.windows.get(note_id)
        if existing:
            existing.focus_for_edit()
            return

        try:
            stored_note = self.storage.load_note(note_id)
        except FileNotFoundError:
            self.reconcile_storage()
            return
        if not stored_note.metadata.is_open:
            stored_note = self.storage.reopen_note(note_id)
        self.open_note(stored_note)

    def update_font_settings(self, *, font_family: str | None = None, font_size: int | None = None) -> None:
        if font_family:
            self.settings.font_family = font_family
        if font_size:
            self.settings.font_size = font_size
        save_settings(self.settings)
        for window in self.windows.values():
            window.apply_font_settings()
            window.flush_note()
        self.tray.refresh()

    def available_font_families(self) -> list[str]:
        installed = set(tkfont.families(self.root))
        chosen: list[str] = []
        for family in [self.settings.font_family, *COMMON_FONT_FAMILIES]:
            if family in installed and family not in chosen:
                chosen.append(family)
        return chosen or [self.settings.font_family]

    def choose_storage_folder(self, parent: tk.Misc | None = None) -> None:
        chosen = filedialog.askdirectory(
            parent=parent,
            title="Choose storage folder",
            initialdir=self.settings.storage_root,
            mustexist=False,
        )
        if not chosen:
            return
        self.prepare_storage_folder_change(Path(chosen), parent=parent)

    def prepare_storage_folder_change(self, new_root: Path, parent: tk.Misc | None = None) -> None:
        old_root = Path(self.settings.storage_root)
        if str(new_root) == str(old_root):
            return

        for window in list(self.windows.values()):
            window.flush_note()

        copy_storage_contents(old_root, new_root)
        self.settings.storage_root = str(new_root)
        save_settings(self.settings)
        messagebox.showinfo(
            "Simple Sticky Notes",
            "Storage folder saved. Restart Simple Sticky Notes to begin using the new location.",
            parent=parent,
        )

    def unregister(self, note_id: str) -> None:
        self.windows.pop(note_id, None)
        self.tray.refresh()

    def list_notes_for_menu(self) -> list[NoteRecord]:
        self.reconcile_storage(refresh_tray=False)
        return self.storage.list_notes()

    def reconcile_storage(self, *, refresh_tray: bool = True) -> None:
        self.storage.prune_missing_note_files(protected_note_ids=set(self.windows))
        if refresh_tray:
            self.tray.refresh()

    def shutdown(self) -> None:
        if self._is_shutting_down:
            return
        self._is_shutting_down = True
        if self.session_id:
            mark_clean_shutdown(self.session_id)
        self.tray.stop()
        for window in list(self.windows.values()):
            try:
                window.flush_note()
            except tk.TclError:
                pass
        self.windows.clear()
        self.root.quit()
        self.root.destroy()


def first_line_title(body: str) -> str:
    for line in body.splitlines():
        stripped = line.strip().lstrip("#").strip()
        if stripped:
            return stripped[:60]
    return "Untitled note"


def editor_body_for_display(body: str) -> str:
    return body + "\n"


def persisted_body_from_editor(body: str) -> str:
    if body.endswith("\n"):
        return body[:-1]
    return body


def selection_bg_for(bg_color: str) -> str:
    red = int(bg_color[1:3], 16)
    green = int(bg_color[3:5], 16)
    blue = int(bg_color[5:7], 16)
    darkened = (
        max(0, int(red * 0.88)),
        max(0, int(green * 0.88)),
        max(0, int(blue * 0.88)),
    )
    return f"#{darkened[0]:02x}{darkened[1]:02x}{darkened[2]:02x}"


def note_menu_label(note: NoteRecord) -> str:
    state = "open" if note.metadata.is_open else "hidden"
    title = note.metadata.title.strip() or f"Note {note.metadata.note_id[:6]}"
    return f"[{state}] {title}"
