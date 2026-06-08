from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest import mock

from simple_sticky_notes import cli


class CliTests(unittest.TestCase):
    def test_existing_instance_receives_new_note_command(self) -> None:
        fake_app = mock.Mock()
        fake_server = mock.Mock()
        fake_server.start.return_value = False

        with mock.patch.object(cli, "StickyNotesApp", return_value=fake_app), mock.patch.object(
            cli, "InstanceServer", return_value=fake_server
        ), mock.patch.object(cli, "send_payload", return_value=True) as send_payload:
            result = cli.main(["--new-note"])

        self.assertEqual(result, 0)
        send_payload.assert_called_once_with({"command": "new-note"})
        fake_app.run.assert_not_called()

    def test_existing_instance_receives_dropped_note_bodies(self) -> None:
        fake_app = mock.Mock()
        fake_server = mock.Mock()
        fake_server.start.return_value = False
        dropped_items = [SimpleNamespace(body="first body"), SimpleNamespace(body="second body")]

        with mock.patch.object(cli, "StickyNotesApp", return_value=fake_app), mock.patch.object(
            cli, "InstanceServer", return_value=fake_server
        ), mock.patch.object(cli, "import_dropped_paths", return_value=dropped_items), mock.patch.object(
            cli, "send_payload", return_value=True
        ) as send_payload:
            result = cli.main(["C:/tmp/one.txt", "C:/tmp/two.txt"])

        self.assertEqual(result, 0)
        self.assertEqual(
            send_payload.call_args_list,
            [
                mock.call({"command": "new-note", "body": "first body"}),
                mock.call({"command": "new-note", "body": "second body"}),
            ],
        )
        fake_app.run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
