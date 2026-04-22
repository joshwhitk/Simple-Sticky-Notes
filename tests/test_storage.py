from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from simple_sticky_notes.models import AppSettings
from simple_sticky_notes.app import editor_body_for_display, note_menu_label, persisted_body_from_editor, selection_bg_for
from simple_sticky_notes.storage import StickyStorage, suggested_file_stem


class StickyStorageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        settings = AppSettings(storage_root=self.tempdir.name)
        self.storage = StickyStorage(settings)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_create_note_persists_markdown_and_metadata(self) -> None:
        note = self.storage.create_note("Test note")
        self.assertTrue((Path(self.tempdir.name) / "notes" / f"{note.metadata.file_stem}.md").exists())
        self.assertTrue((Path(self.tempdir.name) / "meta" / f"{note.metadata.note_id}.json").exists())
        self.assertEqual(note.metadata.title, "Test note")
        self.assertTrue(note.metadata.is_open)
        self.assertEqual(note.metadata.file_stem, "Test note")

    def test_create_note_accepts_body_position_and_color(self) -> None:
        note = self.storage.create_note(
            "Colored note",
            body="Body text",
            x=120,
            y=160,
            width=420,
            height=280,
            bg_color="#bbdefb",
        )
        reloaded = self.storage.load_note(note.metadata.note_id)
        self.assertEqual(reloaded.body, "Body text")
        self.assertEqual(reloaded.metadata.x, 120)
        self.assertEqual(reloaded.metadata.y, 160)
        self.assertEqual(reloaded.metadata.width, 420)
        self.assertEqual(reloaded.metadata.height, 280)
        self.assertEqual(reloaded.metadata.bg_color, "#bbdefb")
        self.assertEqual(reloaded.metadata.file_stem, "Body text")

    def test_hide_note_keeps_note_but_marks_it_closed(self) -> None:
        note = self.storage.create_note("Closable")
        self.storage.hide_note(note.metadata.note_id)
        reloaded = self.storage.load_note(note.metadata.note_id)
        self.assertFalse(reloaded.metadata.is_open)
        self.assertTrue((Path(self.tempdir.name) / "notes" / f"{reloaded.metadata.file_stem}.md").exists())

    def test_list_open_notes_filters_hidden_notes(self) -> None:
        note1 = self.storage.create_note("One")
        note2 = self.storage.create_note("Two")
        self.storage.hide_note(note1.metadata.note_id)
        open_ids = {note.metadata.note_id for note in self.storage.list_open_notes()}
        self.assertNotIn(note1.metadata.note_id, open_ids)
        self.assertIn(note2.metadata.note_id, open_ids)

    def test_editor_body_adds_blank_append_line_without_changing_saved_body(self) -> None:
        stored = "wow this looks good!"
        displayed = editor_body_for_display(stored)
        self.assertEqual(displayed, "wow this looks good!\n")
        self.assertEqual(persisted_body_from_editor(displayed), stored)

    def test_editor_body_preserves_one_intentional_trailing_blank_line(self) -> None:
        stored = "line one\n\n"
        displayed = editor_body_for_display(stored)
        self.assertEqual(persisted_body_from_editor(displayed), stored)

    def test_note_menu_label_reflects_visibility(self) -> None:
        note = self.storage.create_note("Menu title")
        self.assertEqual(note_menu_label(note), "[open] Menu title")
        self.storage.hide_note(note.metadata.note_id)
        hidden_note = self.storage.load_note(note.metadata.note_id)
        self.assertEqual(note_menu_label(hidden_note), "[hidden] Menu title")

    def test_selection_bg_for_darken_color(self) -> None:
        self.assertEqual(selection_bg_for("#ffd54f"), "#e0bb45")

    def test_content_based_filenames_use_incrementing_suffixes(self) -> None:
        first = self.storage.create_note(body="Same title")
        second = self.storage.create_note(body="Same title")
        self.assertEqual(first.metadata.file_stem, "Same title")
        self.assertEqual(second.metadata.file_stem, "Same title-1")

    def test_saving_note_renames_markdown_file_from_updated_content(self) -> None:
        note = self.storage.create_note(body="Old title")
        old_path = Path(self.tempdir.name) / "notes" / "Old title.md"
        self.assertTrue(old_path.exists())
        note.body = "New title"
        note.metadata.title = "New title"
        self.storage.save_note(note)
        self.assertFalse(old_path.exists())
        self.assertTrue((Path(self.tempdir.name) / "notes" / "New title.md").exists())

    def test_suggested_file_stem_sanitizes_invalid_filename_characters(self) -> None:
        self.assertEqual(suggested_file_stem("Plan: finish / ship? *today*", "fallback"), "Plan finish ship today")


if __name__ == "__main__":
    unittest.main()
