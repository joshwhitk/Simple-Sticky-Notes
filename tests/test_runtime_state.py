from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from simple_sticky_notes import runtime_state


class RuntimeStateTests(unittest.TestCase):
    def test_mark_launch_then_clean_shutdown_updates_runtime_marker(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            runtime_path = Path(tempdir) / "runtime_state.json"
            with mock.patch.object(runtime_state, "RUNTIME_STATE_PATH", runtime_path), mock.patch.object(
                runtime_state, "ensure_app_data_dir"
            ):
                session_id, previous_clean = runtime_state.mark_app_launch()
                launched_state = runtime_state.load_runtime_state()
                runtime_state.mark_clean_shutdown(session_id)
                clean_state = runtime_state.load_runtime_state()

        self.assertTrue(previous_clean)
        self.assertEqual(launched_state.active_session_id, session_id)
        self.assertFalse(launched_state.last_shutdown_clean)
        self.assertEqual(clean_state.active_session_id, "")
        self.assertTrue(clean_state.last_shutdown_clean)

    def test_mark_launch_reports_previous_unclean_shutdown(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            runtime_path = Path(tempdir) / "runtime_state.json"
            runtime_path.write_text('{"active_session_id":"stale","last_shutdown_clean":false}', encoding="utf-8")
            with mock.patch.object(runtime_state, "RUNTIME_STATE_PATH", runtime_path), mock.patch.object(
                runtime_state, "ensure_app_data_dir"
            ):
                _session_id, previous_clean = runtime_state.mark_app_launch()

        self.assertFalse(previous_clean)


if __name__ == "__main__":
    unittest.main()
