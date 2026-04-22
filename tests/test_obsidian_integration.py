from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from simple_sticky_notes import obsidian_integration
from simple_sticky_notes.models import AppSettings
from simple_sticky_notes import settings as settings_module


class ObsidianIntegrationTests(unittest.TestCase):
    def test_current_obsidian_vault_path_prefers_open_vault(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            config_path = Path(tempdir) / "obsidian.json"
            config_path.write_text(
                '{"vaults":{"first":{"path":"C:\\\\vault-a","ts":1,"open":false},"second":{"path":"C:\\\\vault-b","ts":2,"open":true}}}',
                encoding="utf-8",
            )
            with mock.patch.object(obsidian_integration, "OBSIDIAN_CONFIG_PATH", config_path):
                self.assertEqual(obsidian_integration.current_obsidian_vault_path(), Path(r"C:\vault-b"))

    def test_recommended_storage_root_uses_vault_subfolder(self) -> None:
        with mock.patch.object(obsidian_integration, "current_obsidian_vault_path", return_value=Path(r"C:\vault-a")):
            self.assertEqual(
                obsidian_integration.recommended_storage_root(),
                Path(r"C:\vault-a") / obsidian_integration.VAULT_STORAGE_FOLDER,
            )

    def test_obsidian_open_uri_uses_vault_relative_path_when_possible(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            vault_path = Path(tempdir) / "joshs-stuff"
            vault_path.mkdir()
            note_path = vault_path / "Simple Sticky Notes" / "Example Note.md"
            note_path.parent.mkdir(parents=True)
            note_path.write_text("hello", encoding="utf-8")
            config_path = Path(tempdir) / "obsidian.json"
            config_path.write_text(
                json_text_for_vault(vault_path),
                encoding="utf-8",
            )

            with mock.patch.object(obsidian_integration, "OBSIDIAN_CONFIG_PATH", config_path):
                self.assertEqual(
                    obsidian_integration.obsidian_open_uri(note_path),
                    "obsidian://open?vault=joshs-stuff&file=Simple%20Sticky%20Notes/Example%20Note.md",
                )

    def test_migrate_default_documents_storage_to_obsidian(self) -> None:
        with tempfile.TemporaryDirectory() as documents_dir, tempfile.TemporaryDirectory() as vault_dir:
            documents_root = Path(documents_dir)
            vault_root = Path(vault_dir)
            (documents_root / "Seen in Obsidian.md").write_text("hello", encoding="utf-8")
            app_settings = AppSettings(storage_root=str(documents_root))

            with mock.patch.object(settings_module, "DEFAULT_STORAGE_ROOT", vault_root), mock.patch.object(
                settings_module, "save_settings"
            ) as save_mock, mock.patch.object(
                settings_module, "documents_default_storage_root", return_value=documents_root
            ):
                migrated = settings_module.migrate_default_documents_storage_to_obsidian(app_settings)

            self.assertEqual(migrated.storage_root, str(vault_root))
            self.assertTrue((vault_root / "Seen in Obsidian.md").exists())
            save_mock.assert_called_once()


if __name__ == "__main__":
    unittest.main()


def json_text_for_vault(vault_path: Path) -> str:
    escaped = str(vault_path).replace("\\", "\\\\")
    return f'{{"vaults":{{"first":{{"path":"{escaped}","ts":1,"open":true}}}}}}'
