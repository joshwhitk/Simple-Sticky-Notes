from __future__ import annotations

import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from urllib.error import HTTPError, URLError

from simple_sticky_notes.models import AppSettings
from simple_sticky_notes import joplin_storage, service_api
from simple_sticky_notes.joplin_storage import (
    JoplinApi,
    JoplinApiError,
    JoplinStickyStorage,
    iso_from_joplin_ms,
)
from simple_sticky_notes.storage import StickyStorage, create_storage


class FakeJoplinApi:
    """In-memory stand-in for the Joplin Data API.

    Serves the same paged shapes as the real API, with a tiny page size so
    pagination is exercised by ordinary tests."""

    PAGE_SIZE = 2

    def __init__(self) -> None:
        self.folders: dict[str, dict] = {}
        self.notes: dict[str, dict] = {}
        self.put_calls = 0
        self._counter = 0

    def add_folder(self, title: str) -> str:
        folder_id = self._new_id()
        self.folders[folder_id] = {"id": folder_id, "title": title}
        return folder_id

    def add_note(self, parent_id: str, title: str, body: str) -> str:
        note_id = self._new_id()
        self.notes[note_id] = {
            "id": note_id,
            "title": title,
            "body": body,
            "parent_id": parent_id,
            "user_created_time": 1755400000000,
            "user_updated_time": 1755400000000,
        }
        return note_id

    def get(self, path: str, **query: object) -> dict:
        page = int(str(query.get("page", 1)))
        if path == "/folders":
            folders = sorted(self.folders.values(), key=lambda folder: folder["id"])
            return self._paged([{"id": f["id"], "title": f["title"]} for f in folders], page)
        if path.startswith("/folders/") and path.endswith("/notes"):
            folder_id = path.split("/")[2]
            notes = sorted(self.notes.values(), key=lambda note: note["id"])
            return self._paged([dict(n) for n in notes if n["parent_id"] == folder_id], page)
        if path.startswith("/notes/"):
            note_id = path.split("/")[2]
            if note_id not in self.notes:
                raise JoplinApiError("note not found", status=404)
            return dict(self.notes[note_id])
        raise AssertionError(f"unexpected GET {path}")

    def post(self, path: str, payload: dict) -> dict:
        if path == "/folders":
            return {"id": self.add_folder(payload["title"])}
        if path == "/notes":
            return {"id": self.add_note(payload["parent_id"], payload["title"], payload["body"])}
        raise AssertionError(f"unexpected POST {path}")

    def put(self, path: str, payload: dict) -> dict:
        self.put_calls += 1
        note_id = path.split("/")[2]
        if note_id not in self.notes:
            raise JoplinApiError("note not found", status=404)
        self.notes[note_id].update({key: payload[key] for key in ("title", "body") if key in payload})
        return dict(self.notes[note_id])

    def delete(self, path: str) -> dict:
        note_id = path.split("/")[2]
        if note_id not in self.notes:
            raise JoplinApiError("note not found", status=404)
        del self.notes[note_id]
        return {}

    def _new_id(self) -> str:
        self._counter += 1
        return f"{self._counter:032x}"

    def _paged(self, items: list[dict], page: int) -> dict:
        start = (page - 1) * self.PAGE_SIZE
        return {
            "items": items[start:start + self.PAGE_SIZE],
            "has_more": start + self.PAGE_SIZE < len(items),
        }


class UnreachableFakeApi:
    def get(self, path: str, **query: object) -> dict:
        raise JoplinApiError("Joplin is unreachable at http://example.invalid.")


class JoplinStickyStorageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.meta_dir = Path(self.tempdir.name) / "joplin-meta"
        self.settings = AppSettings(
            storage_root=str(Path(self.tempdir.name) / "vault"),
            storage_backend="joplin",
        )
        self.api = FakeJoplinApi()
        self.storage = JoplinStickyStorage(self.settings, api=self.api, meta_dir=self.meta_dir)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_create_note_stores_body_in_joplin_and_meta_locally(self) -> None:
        note = self.storage.create_note("Test note", body="Test note\nmore")
        remote = self.api.notes[note.metadata.note_id]
        self.assertEqual(remote["title"], "Test note")
        self.assertEqual(remote["body"], "Test note\nmore")
        self.assertEqual(remote["parent_id"], self.storage.notebook_id())
        self.assertTrue((self.meta_dir / f"{note.metadata.note_id}.json").exists())
        self.assertTrue(note.metadata.is_open)
        self.assertEqual(len(note.metadata.note_id), 32)

    def test_notebook_is_found_across_pages_without_duplicating_it(self) -> None:
        self.api.add_folder("Other 1")
        self.api.add_folder("Other 2")
        wanted = self.api.add_folder("Simple Sticky Notes")  # lands on page 2
        self.assertEqual(self.storage.notebook_id(), wanted)
        self.assertEqual(len(self.api.folders), 3)

    def test_notebook_is_created_when_missing(self) -> None:
        notebook_id = self.storage.notebook_id()
        self.assertEqual(self.api.folders[notebook_id]["title"], "Simple Sticky Notes")

    def test_load_note_without_sidecar_gets_closed_defaults(self) -> None:
        notebook_id = self.storage.notebook_id()
        note_id = self.api.add_note(notebook_id, "Imported note", "Imported note body")
        note = self.storage.load_note(note_id)
        self.assertFalse(note.metadata.is_open)
        self.assertEqual(note.metadata.width, self.settings.default_width)
        self.assertEqual(note.metadata.height, self.settings.default_height)
        self.assertEqual(note.metadata.x, joplin_storage.CASCADE_BASE_X)
        self.assertEqual(note.metadata.created_at, iso_from_joplin_ms(1755400000000))
        self.assertEqual(note.body, "Imported note body")

    def test_load_note_keeps_local_geometry_and_refreshes_title(self) -> None:
        note = self.storage.create_note("Original title", body="Original title")
        self.storage.update_geometry(note.metadata.note_id, x=10, y=20, width=300, height=200)
        self.api.notes[note.metadata.note_id]["title"] = "Renamed in Joplin"
        reloaded = self.storage.load_note(note.metadata.note_id)
        self.assertEqual(reloaded.metadata.title, "Renamed in Joplin")
        self.assertEqual((reloaded.metadata.x, reloaded.metadata.y), (10, 20))
        self.assertEqual((reloaded.metadata.width, reloaded.metadata.height), (300, 200))

    def test_load_note_raises_file_not_found_for_unknown_id(self) -> None:
        with self.assertRaises(FileNotFoundError):
            self.storage.load_note("f" * 32)

    def test_save_note_puts_body_but_never_sends_geometry(self) -> None:
        note = self.storage.create_note("Body note", body="first")
        note.body = "second"
        note.metadata.x = 555
        self.storage.save_note(note)
        remote = self.api.notes[note.metadata.note_id]
        self.assertEqual(remote["body"], "second")
        self.assertNotIn("x", remote)
        sidecar = json.loads((self.meta_dir / f"{note.metadata.note_id}.json").read_text(encoding="utf-8"))
        self.assertEqual(sidecar["x"], 555)

    def test_update_geometry_touches_only_the_sidecar(self) -> None:
        note = self.storage.create_note("Geometry note")
        before = self.api.put_calls
        self.storage.update_geometry(note.metadata.note_id, x=1, y=2, width=333, height=222)
        self.assertEqual(self.api.put_calls, before)
        reloaded = self.storage.load_note(note.metadata.note_id)
        self.assertEqual((reloaded.metadata.width, reloaded.metadata.height), (333, 222))

    def test_hide_and_reopen_note_toggle_local_open_state(self) -> None:
        note = self.storage.create_note("Toggle note", body="Toggle note")
        self.storage.hide_note(note.metadata.note_id)
        self.assertFalse(self.storage.load_note(note.metadata.note_id).metadata.is_open)
        reopened = self.storage.reopen_note(note.metadata.note_id)
        self.assertTrue(reopened.metadata.is_open)
        self.assertEqual(reopened.body, "Toggle note")

    def test_list_notes_pages_through_all_results(self) -> None:
        for index in range(5):
            self.storage.create_note(f"Note {index}", body=f"Note {index}")
        notes = self.storage.list_notes()
        self.assertEqual(len(notes), 5)
        self.assertEqual(len(self.storage.list_note_ids()), 5)
        self.assertEqual(len(self.storage.list_open_notes()), 5)

    def test_delete_note_removes_remote_note_and_sidecar(self) -> None:
        note = self.storage.create_note("Doomed note")
        self.storage.delete_note(note.metadata.note_id)
        self.assertNotIn(note.metadata.note_id, self.api.notes)
        self.assertFalse((self.meta_dir / f"{note.metadata.note_id}.json").exists())
        # Deleting again (already gone in Joplin) must not raise.
        self.storage.delete_note(note.metadata.note_id)

    def test_delete_note_without_body_keeps_remote_note(self) -> None:
        note = self.storage.create_note("Kept note")
        self.storage.delete_note(note.metadata.note_id, delete_body=False)
        self.assertIn(note.metadata.note_id, self.api.notes)
        self.assertFalse((self.meta_dir / f"{note.metadata.note_id}.json").exists())

    def test_prune_missing_note_files_drops_orphan_sidecars(self) -> None:
        kept = self.storage.create_note("Kept")
        orphan = self.storage.create_note("Orphan")
        del self.api.notes[orphan.metadata.note_id]
        protected = self.storage.create_note("Protected")
        del self.api.notes[protected.metadata.note_id]

        removed = self.storage.prune_missing_note_files(
            protected_note_ids={protected.metadata.note_id}
        )

        self.assertEqual(removed, [orphan.metadata.note_id])
        self.assertTrue((self.meta_dir / f"{kept.metadata.note_id}.json").exists())
        self.assertTrue((self.meta_dir / f"{protected.metadata.note_id}.json").exists())

    def test_prune_is_a_quiet_no_op_when_joplin_is_unreachable(self) -> None:
        storage = JoplinStickyStorage(self.settings, api=UnreachableFakeApi(), meta_dir=self.meta_dir)
        self.assertEqual(storage.prune_missing_note_files(), [])

    def test_note_path_is_a_pseudo_path_that_never_exists(self) -> None:
        path = self.storage.note_path("a" * 32)
        self.assertEqual(str(path), "joplin:" + "a" * 32)
        self.assertFalse(path.exists())

    def test_vault_files_are_never_adopted(self) -> None:
        md = Path(self.tempdir.name) / "vault" / "Some note.md"
        md.parent.mkdir(parents=True, exist_ok=True)
        md.write_text("Some note\n", encoding="utf-8")
        self.assertIsNone(self.storage.find_note_id_for_path(md))
        self.assertIsNone(self.storage.note_id_for_sticky(md))

    def test_phone_home_stems_still_read_from_the_vault(self) -> None:
        self.storage.phone_home_path().parent.mkdir(parents=True, exist_ok=True)
        self.storage.phone_home_path().write_text(
            json.dumps({"file_stems": ["Grocery list"]}), encoding="utf-8"
        )
        self.assertEqual(self.storage.phone_home_stems(), ["Grocery list"])


class BackendSwitchTests(unittest.TestCase):
    def test_create_storage_defaults_to_joplin(self) -> None:
        # The notes live in Joplin since 2026-08-17; the vault is a frozen archive, so
        # the default has to point at the live store rather than the dead one.
        with tempfile.TemporaryDirectory() as tempdir:
            storage = create_storage(AppSettings(storage_root=tempdir))
            self.assertIsInstance(storage, JoplinStickyStorage)

    def test_create_storage_still_builds_the_file_backend_on_request(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            settings = AppSettings(storage_root=tempdir, storage_backend="files")
            self.assertIsInstance(create_storage(settings), StickyStorage)

    def test_create_storage_builds_the_joplin_backend_on_request(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            settings = AppSettings(storage_root=tempdir, storage_backend="joplin")
            storage = create_storage(settings)
            self.assertIsInstance(storage, JoplinStickyStorage)
            self.assertEqual(storage.api.base_url, settings.joplin_api_url)

    def test_service_api_round_trip_against_the_joplin_backend(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            settings = AppSettings(storage_root=tempdir, storage_backend="joplin")
            storage = JoplinStickyStorage(
                settings,
                api=FakeJoplinApi(),
                meta_dir=Path(tempdir) / "joplin-meta",
            )
            with mock.patch.object(service_api, "create_storage", return_value=storage), mock.patch.object(
                service_api, "load_settings", return_value=settings
            ), mock.patch.object(service_api, "send_payload", return_value=True):
                created = service_api.create_note(body="joplin backed note")
                self.assertEqual(created["title"], "joplin backed note")
                self.assertFalse(created["is_open"])
                self.assertTrue(created["path"].startswith("joplin:"))

                edited = service_api.edit_note(created["note_id"], append_text=" plus")
                self.assertEqual(edited["body"], "joplin backed note plus")

                listing = service_api.list_notes()
                self.assertEqual(listing["count"], 1)

                deleted = service_api.delete_note(created["note_id"])
                self.assertTrue(deleted["deleted"])
                self.assertEqual(service_api.list_notes()["count"], 0)


class JoplinApiTransportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.api = JoplinApi("http://example.invalid:41185", "secret-token")

    @staticmethod
    def _response(payload: dict) -> mock.MagicMock:
        response = mock.MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps(payload).encode("utf-8")
        return response

    def test_token_is_sent_as_query_parameter(self) -> None:
        with mock.patch.object(joplin_storage.urllib.request, "urlopen", return_value=self._response({"items": []})) as urlopen:
            self.api.get("/folders", page=1)
        request = urlopen.call_args[0][0]
        self.assertIn("token=secret-token", request.full_url)
        self.assertIn("page=1", request.full_url)

    def test_retries_once_on_connection_error_then_succeeds(self) -> None:
        with mock.patch.object(
            joplin_storage.urllib.request,
            "urlopen",
            side_effect=[URLError("refused"), self._response({"id": "abc"})],
        ) as urlopen, mock.patch.object(joplin_storage.time, "sleep"):
            result = self.api.get("/notes/abc")
        self.assertEqual(result, {"id": "abc"})
        self.assertEqual(urlopen.call_count, 2)

    def test_raises_a_clear_error_when_joplin_stays_unreachable(self) -> None:
        with mock.patch.object(
            joplin_storage.urllib.request,
            "urlopen",
            side_effect=URLError("refused"),
        ) as urlopen, mock.patch.object(joplin_storage.time, "sleep"):
            with self.assertRaises(JoplinApiError) as raised:
                self.api.get("/folders")
        self.assertEqual(urlopen.call_count, 2)
        self.assertIn("unreachable", str(raised.exception))
        self.assertIn("http://example.invalid:41185", str(raised.exception))

    def test_retries_on_server_error_but_not_on_client_error(self) -> None:
        server_error = HTTPError("http://x", 500, "boom", None, io.BytesIO(b""))
        with mock.patch.object(
            joplin_storage.urllib.request,
            "urlopen",
            side_effect=[server_error, self._response({"ok": True})],
        ) as urlopen, mock.patch.object(joplin_storage.time, "sleep"):
            self.assertEqual(self.api.get("/folders"), {"ok": True})
        self.assertEqual(urlopen.call_count, 2)

        not_found = HTTPError("http://x", 404, "missing", None, io.BytesIO(b""))
        with mock.patch.object(
            joplin_storage.urllib.request, "urlopen", side_effect=not_found
        ) as urlopen:
            with self.assertRaises(JoplinApiError) as raised:
                self.api.get("/notes/nope")
        self.assertEqual(urlopen.call_count, 1)
        self.assertEqual(raised.exception.status, 404)

    def test_iso_from_joplin_ms_converts_and_defaults(self) -> None:
        self.assertEqual(iso_from_joplin_ms(1755400000000), "2025-08-17T03:06:40+00:00")
        self.assertTrue(iso_from_joplin_ms(0).endswith("+00:00"))
        self.assertTrue(iso_from_joplin_ms(None).endswith("+00:00"))


if __name__ == "__main__":
    unittest.main()
