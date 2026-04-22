from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from simple_sticky_notes.models import AppSettings
from simple_sticky_notes.app import editor_body_for_display, note_menu_label, persisted_body_from_editor, selection_bg_for
from simple_sticky_notes.storage import StickyStorage, note_title, suggested_file_stem


class StickyStorageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        settings = AppSettings(storage_root=self.tempdir.name)
        self.storage = StickyStorage(settings)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_create_note_persists_markdown_and_metadata(self) -> None:
        note = self.storage.create_note("Test note")
        self.assertTrue((Path(self.tempdir.name) / f"{note.metadata.file_stem}.md").exists())
        self.assertTrue((Path(self.tempdir.name) / ".simple-sticky-notes" / "meta" / f"{note.metadata.note_id}.json").exists())
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
        self.assertEqual(reloaded.metadata.file_stem, "Colored note")

    def test_hide_note_keeps_note_but_marks_it_closed(self) -> None:
        note = self.storage.create_note("Closable")
        self.storage.hide_note(note.metadata.note_id)
        reloaded = self.storage.load_note(note.metadata.note_id)
        self.assertFalse(reloaded.metadata.is_open)
        self.assertTrue((Path(self.tempdir.name) / f"{reloaded.metadata.file_stem}.md").exists())

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

    def test_title_based_filenames_use_incrementing_suffixes(self) -> None:
        first = self.storage.create_note(title="Same title", body="Body one")
        second = self.storage.create_note(title="Same title", body="Body two")
        self.assertEqual(first.metadata.file_stem, "Same title")
        self.assertEqual(second.metadata.file_stem, "Same title-1")

    def test_saving_note_keeps_existing_markdown_filename_stable(self) -> None:
        note = self.storage.create_note(title="Old title", body="Old title")
        old_path = Path(self.tempdir.name) / "Old title.md"
        self.assertTrue(old_path.exists())
        note.body = "New title"
        note.metadata.title = "New title"
        self.storage.save_note(note)
        self.assertTrue(old_path.exists())
        self.assertFalse((Path(self.tempdir.name) / "New title.md").exists())
        self.assertEqual(old_path.read_text(encoding="utf-8"), "New title")

    def test_storage_migrates_legacy_notes_and_metadata_layout(self) -> None:
        root = Path(self.tempdir.name)
        legacy_notes_dir = root / "notes"
        legacy_meta_dir = root / "meta"
        legacy_notes_dir.mkdir()
        legacy_meta_dir.mkdir()
        (legacy_notes_dir / "Migrated Note.md").write_text("hello", encoding="utf-8")
        (legacy_meta_dir / "abc123.json").write_text(
            '{"note_id":"abc123","title":"Migrated Note","x":1,"y":2,"width":300,"height":200,"is_open":true,"created_at":"2026-01-01T00:00:00+00:00","updated_at":"2026-01-01T00:00:00+00:00","bg_color":"#ffd54f","file_stem":"Migrated Note"}',
            encoding="utf-8",
        )

        migrated = StickyStorage(AppSettings(storage_root=self.tempdir.name))

        self.assertTrue((root / "Migrated Note.md").exists())
        self.assertTrue((root / ".simple-sticky-notes" / "meta" / "abc123.json").exists())
        self.assertFalse(legacy_notes_dir.exists())
        self.assertFalse(legacy_meta_dir.exists())
        self.assertEqual(migrated.load_note("abc123").body, "hello")

    def test_suggested_file_stem_sanitizes_invalid_filename_characters(self) -> None:
        self.assertEqual(suggested_file_stem("Plan: finish / ship? *today*"), "Plan finish ship today")

    def test_note_title_uses_first_ten_words(self) -> None:
        self.assertEqual(
            note_title("one two three four five six seven eight nine ten eleven twelve"),
            "one two three four five six seven eight nine ten",
        )


if __name__ == "__main__":
    unittest.main()
