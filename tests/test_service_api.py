from __future__ import annotations

import tempfile
import unittest
from unittest import mock

from simple_sticky_notes.models import AppSettings
from simple_sticky_notes import service_api


class ServiceApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.load_settings_patch = mock.patch.object(
            service_api,
            "load_settings",
            return_value=AppSettings(storage_root=self.tempdir.name),
        )
        self.send_payload_patch = mock.patch.object(service_api, "send_payload", return_value=True)
        self.is_instance_running_patch = mock.patch.object(service_api, "is_instance_running", return_value=True)
        self.load_settings_patch.start()
        self.send_payload_patch.start()
        self.is_instance_running_patch.start()

    def tearDown(self) -> None:
        self.is_instance_running_patch.stop()
        self.send_payload_patch.stop()
        self.load_settings_patch.stop()
        self.tempdir.cleanup()

    def test_create_note_defaults_to_hidden(self) -> None:
        note = service_api.create_note(body="server-created note")

        self.assertEqual(note["title"], "server-created note")
        self.assertFalse(note["is_open"])

    def test_search_notes_matches_body_text(self) -> None:
        created = service_api.create_note(body="call the dentist about friday", is_open=True)

        result = service_api.search_notes("dentist")

        self.assertEqual(result["count"], 1)
        self.assertEqual(result["notes"][0]["note_id"], created["note_id"])

    def test_edit_note_can_append_text(self) -> None:
        created = service_api.create_note(body="hello")

        updated = service_api.edit_note(created["note_id"], append_text=" world")

        self.assertEqual(updated["body"], "hello world")

    def test_create_visible_note_reports_instance_delivery(self) -> None:
        created = service_api.create_visible_note(body="visible now")

        self.assertTrue(created["instance_running"])

    def test_notes_changed_since_filters_older_notes(self) -> None:
        first = service_api.create_note(body="first")
        second = service_api.create_note(body="second")

        result = service_api.notes_changed_since(first["updated_at"])

        returned_ids = {note["note_id"] for note in result["notes"]}
        self.assertIn(second["note_id"], returned_ids)
        self.assertGreaterEqual(result["count"], 1)

    def test_get_status_reports_running_instance(self) -> None:
        service_api.create_note(body="status check", is_open=True)

        status = service_api.get_status()

        self.assertEqual(status["note_count"], 1)
        self.assertEqual(status["open_note_count"], 1)
        self.assertTrue(status["instance_running"])


if __name__ == "__main__":
    unittest.main()
