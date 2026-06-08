from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from simple_sticky_notes.drop_import import import_dropped_path
from simple_sticky_notes.models import AppSettings
from simple_sticky_notes.storage import StickyStorage


class DropImportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.storage = StickyStorage(AppSettings(storage_root=self.tempdir.name))
        self.source_dir = Path(self.tempdir.name) / "source"
        self.source_dir.mkdir()

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_imports_internet_shortcut_as_markdown_link(self) -> None:
        shortcut = self.source_dir / "OpenAI.url"
        shortcut.write_text("[InternetShortcut]\nURL=https://openai.com/\n", encoding="utf-8")

        imported = import_dropped_path(shortcut, self.storage)

        self.assertEqual(imported.body, "[OpenAI](https://openai.com/)")
        self.assertFalse(imported.imported_to_obsidian)

    def test_imports_text_file_contents_directly(self) -> None:
        text_file = self.source_dir / "note.txt"
        text_file.write_text("Dropped text content", encoding="utf-8")

        imported = import_dropped_path(text_file, self.storage)

        self.assertEqual(imported.body, "Dropped text content")
        self.assertFalse(imported.imported_to_obsidian)

    def test_imports_binary_file_as_obsidian_attachment_link(self) -> None:
        binary_file = self.source_dir / "diagram.pdf"
        binary_file.write_bytes(b"%PDF-\x00binary")

        imported = import_dropped_path(binary_file, self.storage)

        self.assertTrue(imported.imported_to_obsidian)
        self.assertIn("[diagram.pdf](Attachments/diagram.pdf)", imported.body)
        self.assertTrue((Path(self.tempdir.name) / "Attachments" / "diagram.pdf").exists())


if __name__ == "__main__":
    unittest.main()
