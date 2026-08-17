from __future__ import annotations

import importlib.util
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from simple_sticky_notes.joplin_storage import JoplinStickyStorage
from simple_sticky_notes.models import AppSettings
from simple_sticky_notes.storage import StickyStorage

from tests.test_joplin_storage import FakeJoplinApi


def load_migrate_module():
    script = Path(__file__).resolve().parents[1] / "tools" / "migrate-stickies-to-joplin.py"
    spec = importlib.util.spec_from_file_location("migrate_stickies_to_joplin", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class MigrateToolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        root = Path(self.tempdir.name)
        self.settings = AppSettings(storage_root=str(root / "vault"))
        self.files = StickyStorage(self.settings)
        self.api = FakeJoplinApi()
        self.joplin = JoplinStickyStorage(
            self.settings, api=self.api, meta_dir=root / "joplin-meta"
        )
        self.migrate_module = load_migrate_module()

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def run_migrate(self) -> dict[str, int]:
        with redirect_stdout(io.StringIO()):
            return self.migrate_module.migrate(self.files, self.joplin)

    def test_matches_imported_notes_and_creates_the_rest(self) -> None:
        matched_note = self.files.create_note("Grocery list", body="Grocery list\n- milk")
        unmatched_note = self.files.create_note("Only on desktop", body="Only on desktop")
        notebook_id = self.joplin.notebook_id()
        imported_id = self.api.add_note(notebook_id, "Grocery list", "Grocery list\n- milk")

        counts = self.run_migrate()

        self.assertEqual(counts["matched"], 1)
        self.assertEqual(counts["created"], 1)
        self.assertEqual(counts["sidecars_copied"], 2)
        self.assertEqual(counts["total"], 2)
        # The matched sticky's sidecar now lives under the Joplin note id.
        sidecar = json.loads(self.joplin.meta_path(imported_id).read_text(encoding="utf-8"))
        self.assertEqual(sidecar["note_id"], imported_id)
        self.assertEqual(sidecar["title"], "Grocery list")
        # The unmatched sticky was created in Joplin with its body.
        created_titles = {note["title"] for note in self.api.notes.values()}
        self.assertIn("Only on desktop", created_titles)
        # Nothing in the vault was deleted.
        self.assertTrue((Path(self.settings.storage_root) / f"{matched_note.metadata.file_stem}.md").exists())
        self.assertTrue((Path(self.settings.storage_root) / f"{unmatched_note.metadata.file_stem}.md").exists())

    def test_rerunning_is_idempotent(self) -> None:
        self.files.create_note("Grocery list", body="Grocery list\n- milk")
        self.files.create_note("Only on desktop", body="Only on desktop")
        self.api.add_note(self.joplin.notebook_id(), "Grocery list", "Grocery list\n- milk")

        first = self.run_migrate()
        second = self.run_migrate()

        self.assertEqual(first["created"], 1)
        self.assertEqual(second["created"], 0)
        self.assertEqual(second["matched"], 2)
        self.assertEqual(second["sidecars_copied"], 0)
        self.assertEqual(second["sidecars_already"], 2)
        self.assertEqual(len(self.api.notes), 2)

    def test_duplicate_titles_map_one_to_one(self) -> None:
        self.files.create_note("Same title", body="Same title first")
        self.files.create_note("Same title", body="Same title second")
        notebook_id = self.joplin.notebook_id()
        self.api.add_note(notebook_id, "Same title", "Same title first")
        self.api.add_note(notebook_id, "Same title", "Same title second")

        counts = self.run_migrate()

        self.assertEqual(counts["matched"], 2)
        self.assertEqual(counts["created"], 0)
        self.assertEqual(counts["sidecars_copied"], 2)


if __name__ == "__main__":
    unittest.main()
