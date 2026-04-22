from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from simple_sticky_notes.models import AppSettings
from simple_sticky_notes.app import editor_body_for_display, persisted_body_from_editor
from simple_sticky_notes.storage import StickyStorage


class StickyStorageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        settings = AppSettings(storage_root=self.tempdir.name)
        self.storage = StickyStorage(settings)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_create_note_persists_markdown_and_metadata(self) -> None:
        note = self.storage.create_note("Test note")
        self.assertTrue((Path(self.tempdir.name) / "notes" / f"{note.metadata.note_id}.md").exists())
        self.assertTrue((Path(self.tempdir.name) / "meta" / f"{note.metadata.note_id}.json").exists())
        self.assertEqual(note.metadata.title, "Test note")
        self.assertTrue(note.metadata.is_open)

    def test_hide_note_keeps_note_but_marks_it_closed(self) -> None:
        note = self.storage.create_note("Closable")
        self.storage.hide_note(note.metadata.note_id)
        reloaded = self.storage.load_note(note.metadata.note_id)
        self.assertFalse(reloaded.metadata.is_open)
        self.assertTrue((Path(self.tempdir.name) / "notes" / f"{note.metadata.note_id}.md").exists())

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


if __name__ == "__main__":
    unittest.main()
