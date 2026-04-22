from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from simple_sticky_notes import app as app_module
from simple_sticky_notes.models import AppSettings


class FakeTrayController:
    def __init__(self, app: app_module.StickyNotesApp) -> None:
        self.app = app
        self.started = False
        self.refresh_count = 0

    def start(self) -> None:
        self.started = True

    def stop(self) -> None:
        self.started = False

    def refresh(self) -> None:
        self.refresh_count += 1


class AppBehaviorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.load_settings_patch = mock.patch.object(
            app_module,
            "load_settings",
            return_value=AppSettings(storage_root=self.tempdir.name),
        )
        self.save_settings_patch = mock.patch.object(app_module, "save_settings")
        self.copy_storage_patch = mock.patch.object(app_module, "copy_storage_contents")
        self.tray_patch = mock.patch.object(app_module, "TrayController", FakeTrayController)
        self.load_settings_patch.start()
        self.save_settings_patch.start()
        self.copy_storage_patch.start()
        self.tray_patch.start()
        self.app = app_module.StickyNotesApp()

    def tearDown(self) -> None:
        try:
            if self.app.root.winfo_exists():
                self.app.shutdown()
        except Exception:
            pass
        self.tray_patch.stop()
        self.copy_storage_patch.stop()
        self.save_settings_patch.stop()
        self.load_settings_patch.stop()
        self.tempdir.cleanup()

    def test_deleted_markdown_is_pruned_from_note_menus(self) -> None:
        note = self.app.storage.create_note(body="Delete me from disk")
        self.app.storage.note_path(note.metadata.note_id).unlink()

        notes = self.app.list_notes_for_menu()

        self.assertEqual(notes, [])
        self.assertFalse(self.app.storage.meta_path(note.metadata.note_id).exists())

    def test_open_note_closes_if_backing_markdown_is_deleted(self) -> None:
        self.app.create_and_open_note(body="Live note")
        window = next(iter(self.app.windows.values()))
        note_id = window.note.metadata.note_id
        self.app.storage.note_path(note_id).unlink()

        window._refresh_from_disk_if_needed()
        self.app.root.update_idletasks()

        self.assertNotIn(note_id, self.app.windows)
        self.assertFalse(self.app.storage.meta_path(note_id).exists())

    def test_context_menu_releases_popup_grab_every_time(self) -> None:
        self.app.create_and_open_note(body="Menu test")
        window = next(iter(self.app.windows.values()))
        fake_menu = mock.Mock()
        fake_event = SimpleNamespace(x_root=50, y_root=60)

        with mock.patch.object(window, "_build_context_menu", return_value=fake_menu):
            self.assertEqual(window._show_context_menu(fake_event), "break")
            self.assertEqual(window._show_context_menu(fake_event), "break")

        self.assertEqual(fake_menu.tk_popup.call_count, 2)
        self.assertEqual(fake_menu.grab_release.call_count, 2)

    def test_run_without_open_notes_does_not_force_a_new_blank_note(self) -> None:
        self.app.root.after(50, self.app.shutdown)

        result = self.app.run(create_new_note=False)

        self.assertEqual(result, 0)
        self.assertEqual(self.app.storage.list_notes(), [])


if __name__ == "__main__":
    unittest.main()
