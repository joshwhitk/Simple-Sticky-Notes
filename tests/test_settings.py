from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from simple_sticky_notes.models import AppSettings
from simple_sticky_notes import settings as settings_module


class SettingsTests(unittest.TestCase):
    def test_copy_storage_contents_copies_nested_files(self) -> None:
        with tempfile.TemporaryDirectory() as source_dir, tempfile.TemporaryDirectory() as target_dir:
            source = Path(source_dir)
            target = Path(target_dir)
            nested = source / "notes" / "Example.md"
            nested.parent.mkdir(parents=True, exist_ok=True)
            nested.write_text("example", encoding="utf-8")

            settings_module.copy_storage_contents(source, target)

            self.assertTrue((target / "notes" / "Example.md").exists())
            self.assertEqual((target / "notes" / "Example.md").read_text(encoding="utf-8"), "example")

    def test_migrate_legacy_storage_root_switches_to_documents_default(self) -> None:
        with tempfile.TemporaryDirectory() as sandbox_dir, tempfile.TemporaryDirectory() as default_dir:
            legacy = Path(sandbox_dir) / "Dropbox" / "simple-sticky-notes"
            default = Path(default_dir)
            (legacy / "notes").mkdir(parents=True)
            (legacy / "notes" / "Legacy note.md").write_text("legacy", encoding="utf-8")
            app_settings = AppSettings(storage_root=str(legacy))

            with mock.patch.object(settings_module, "DEFAULT_STORAGE_ROOT", default), mock.patch.object(
                settings_module, "save_settings"
            ) as save_mock:
                migrated = settings_module.migrate_legacy_storage_root(app_settings)

            self.assertEqual(migrated.storage_root, str(default))
            self.assertTrue((default / "notes" / "Legacy note.md").exists())
            save_mock.assert_called_once()


if __name__ == "__main__":
    unittest.main()
