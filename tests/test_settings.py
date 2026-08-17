from __future__ import annotations

import json
import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path
from unittest import mock

from simple_sticky_notes.models import AppSettings
from simple_sticky_notes import settings as settings_module


class SettingsTests(unittest.TestCase):
    def test_storage_backend_settings_default_to_joplin(self) -> None:
        # Joplin has been the live store since 2026-08-17. Defaulting to files would now
        # point at a frozen read-only archive and write notes where nothing reads them.
        settings = AppSettings(storage_root="anywhere")

        self.assertEqual(settings.storage_backend, "joplin")
        self.assertEqual(settings.joplin_api_url, "http://100.121.209.20:41185")
        self.assertEqual(settings.joplin_api_token, "")
        self.assertEqual(settings.joplin_notebook, "Simple Sticky Notes")

    def test_settings_file_without_backend_keys_loads_with_defaults(self) -> None:
        # A settings.json written before the Joplin backend existed has none of the new
        # keys. It must still load, and it now lands on the live store rather than the
        # archive — an old config file is not a decision to keep using the old storage.
        legacy_data = {
            "storage_root": "C:\\somewhere\\Simple Sticky Notes",
            "font_family": "Arial",
            "font_size": 14,
            "default_width": 360,
            "default_height": 260,
            "autosave_delay_ms": 700,
        }

        settings = AppSettings(**json.loads(json.dumps(legacy_data)))

        self.assertEqual(settings.storage_backend, "joplin")
        self.assertEqual(settings.joplin_notebook, "Simple Sticky Notes")

    def test_backend_settings_round_trip_through_json(self) -> None:
        settings = AppSettings(
            storage_root="anywhere",
            storage_backend="joplin",
            joplin_api_token="abc123",
        )

        restored = AppSettings(**json.loads(json.dumps(asdict(settings))))

        self.assertEqual(restored.storage_backend, "joplin")
        self.assertEqual(restored.joplin_api_token, "abc123")
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

    def test_migrate_obsidian_vault_storage_root_switches_to_active_vault(self) -> None:
        with tempfile.TemporaryDirectory() as sandbox_dir, tempfile.TemporaryDirectory() as active_vault_dir:
            legacy_root = Path(sandbox_dir) / "old-vault" / "Simple Sticky Notes"
            active_root = Path(active_vault_dir) / "Simple Sticky Notes"
            (legacy_root / "Moved note.md").parent.mkdir(parents=True, exist_ok=True)
            (legacy_root / "Moved note.md").write_text("moved", encoding="utf-8")
            app_settings = AppSettings(storage_root=str(legacy_root))

            with mock.patch.object(settings_module, "DEFAULT_STORAGE_ROOT", active_root), mock.patch.object(
                settings_module, "save_settings"
            ) as save_mock:
                migrated = settings_module.migrate_obsidian_vault_storage_root(app_settings)

            self.assertEqual(migrated.storage_root, str(active_root))
            self.assertEqual((active_root / "Moved note.md").read_text(encoding="utf-8"), "moved")
            save_mock.assert_called_once()


if __name__ == "__main__":
    unittest.main()
