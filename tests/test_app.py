from __future__ import annotations

import json
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

    def test_run_with_initial_note_bodies_creates_notes(self) -> None:
        self.app.root.after(50, self.app.shutdown)

        result = self.app.run(initial_note_bodies=["one", "two"])

        self.assertEqual(result, 0)
        self.assertEqual(len(self.app.storage.list_notes()), 2)

    def test_external_obsidian_edit_reloads_body_without_renaming_markdown_file(self) -> None:
        self.app.create_and_open_note(body="one two three four five six seven eight nine ten eleven")
        window = next(iter(self.app.windows.values()))
        note_id = window.note.metadata.note_id
        note_path = self.app.storage.note_path(note_id)

        note_path.write_text("updated from obsidian with more words than before", encoding="utf-8")

        window._refresh_from_disk_if_needed()

        self.assertEqual(self.app.storage.note_path(note_id), note_path)
        self.assertEqual(window.note.metadata.title, "updated from obsidian with more words than before")
        # After reload and resave, the file now has frontmatter with the title and stickynote tag
        reloaded = self.app.storage.load_note(note_id)
        self.assertEqual(reloaded.body, "updated from obsidian with more words than before")

    def test_external_sync_does_not_double_frontmatter_or_corrupt_title(self) -> None:
        # Regression: an open note whose backing file already carries frontmatter
        # (the normal state after any save) must not gain a second frontmatter block
        # nor have its title rewritten to "---" each time the file is touched.
        self.app.create_and_open_note(body="first line stays the title")
        window = next(iter(self.app.windows.values()))
        note_id = window.note.metadata.note_id
        note_path = self.app.storage.note_path(note_id)

        # The on-disk file has exactly one frontmatter block after creation.
        self.assertEqual(note_path.read_text(encoding="utf-8").count("stickynote"), 1)

        # Simulate an external editor touching the file (rewriting it with frontmatter,
        # as our own saves do) and the open window syncing from disk.
        from simple_sticky_notes.storage import format_note_with_frontmatter

        note_path.write_text(
            format_note_with_frontmatter("edited body keeps a single block"),
            encoding="utf-8",
        )
        window._refresh_from_disk_if_needed()

        raw = note_path.read_text(encoding="utf-8")
        self.assertEqual(raw.count("stickynote"), 1)
        self.assertEqual(window.note.body, "edited body keeps a single block")
        self.assertEqual(window.note.metadata.title, "edited body keeps a single block")
        self.assertNotIn("---", window.note.body)

    def test_remote_new_note_command_creates_note_without_second_instance(self) -> None:
        self.assertEqual(self.app.storage.list_notes(), [])

        self.app.enqueue_remote_command("new-note")
        self.app._poll_remote_commands()

        notes = self.app.storage.list_notes()
        self.assertEqual(len(notes), 1)

    def test_remote_json_new_note_command_supports_body(self) -> None:
        self.app.enqueue_remote_command(json.dumps({"command": "new-note", "body": "from remote"}))

        self.app._poll_remote_commands()

        notes = self.app.storage.list_notes()
        self.assertEqual(len(notes), 1)
        self.assertEqual(notes[0].body, "from remote")

    def test_remote_move_resize_command_updates_open_window_geometry(self) -> None:
        self.app.create_and_open_note(body="Move me")
        window = next(iter(self.app.windows.values()))
        note_id = window.note.metadata.note_id

        self.app.enqueue_remote_command(
            json.dumps(
                {
                    "command": "move-resize-note",
                    "note_id": note_id,
                    "x": 120,
                    "y": 140,
                    "width": 280,
                    "height": 220,
                    "focus": False,
                }
            )
        )

        self.app._poll_remote_commands()

        updated = self.app.storage.load_note(note_id)
        self.assertEqual((updated.metadata.x, updated.metadata.y), (120, 140))
        self.assertEqual((updated.metadata.width, updated.metadata.height), (280, 220))

    def test_parse_remote_command_accepts_json_payload(self) -> None:
        payload = app_module.parse_remote_command('{"command":"show-note","note_id":"abc123"}')

        self.assertEqual(payload["command"], "show-note")
        self.assertEqual(payload["note_id"], "abc123")


if __name__ == "__main__":
    unittest.main()
