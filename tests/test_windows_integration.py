from __future__ import annotations

import unittest
from pathlib import Path
from unittest import mock

from simple_sticky_notes import windows_integration


class WindowsIntegrationTests(unittest.TestCase):
    def test_shortcut_icon_path_uses_repo_icon_in_source_mode(self) -> None:
        with mock.patch.object(windows_integration, "running_frozen", return_value=False), mock.patch.object(
            windows_integration, "resource_root", return_value=Path(r"C:\repo\SimpleStickyNotes")
        ):
            icon = windows_integration.shortcut_icon_path()

        self.assertEqual(icon, Path(r"C:\repo\SimpleStickyNotes\assets\icons\simple-sticky-notes.ico"))

    def test_shortcut_launch_spec_uses_python_entrypoint_in_source_mode(self) -> None:
        with mock.patch.object(windows_integration, "running_frozen", return_value=False), mock.patch.object(
            windows_integration, "resource_root", return_value=Path(r"C:\repo\SimpleStickyNotes")
        ), mock.patch.object(
            windows_integration, "pythonw_path", return_value=Path(r"C:\Python314\pythonw.exe")
        ):
            spec = windows_integration.shortcut_launch_spec(create_new_note=True)

        self.assertEqual(spec.target, Path(r"C:\Python314\pythonw.exe"))
        self.assertEqual(spec.arguments, r'"C:\repo\SimpleStickyNotes\main.py" --new-note')
        self.assertEqual(spec.working_directory, Path(r"C:\repo\SimpleStickyNotes"))

    def test_shortcut_launch_spec_targets_installed_exe_in_frozen_mode(self) -> None:
        with mock.patch.object(windows_integration, "running_frozen", return_value=True), mock.patch.object(
            windows_integration.sys, "executable", r"C:\Users\Josh\AppData\Local\Programs\Simple Sticky Notes\Simple Sticky Notes.exe"
        ):
            spec = windows_integration.shortcut_launch_spec(create_new_note=False)
            new_note_spec = windows_integration.shortcut_launch_spec(create_new_note=True)

        expected_target = Path(r"C:\Users\Josh\AppData\Local\Programs\Simple Sticky Notes\Simple Sticky Notes.exe")
        self.assertEqual(spec.target, expected_target)
        self.assertEqual(spec.arguments, "")
        self.assertEqual(spec.working_directory, expected_target.parent)
        self.assertEqual(new_note_spec.arguments, "--new-note")

    def test_shortcut_icon_path_uses_installed_exe_in_frozen_mode(self) -> None:
        with mock.patch.object(windows_integration, "running_frozen", return_value=True), mock.patch.object(
            windows_integration.sys, "executable", r"C:\Users\Josh\AppData\Local\Programs\Simple Sticky Notes\Simple Sticky Notes.exe"
        ):
            icon = windows_integration.shortcut_icon_path()

        self.assertEqual(
            icon,
            Path(r"C:\Users\Josh\AppData\Local\Programs\Simple Sticky Notes\Simple Sticky Notes.exe"),
        )


if __name__ == "__main__":
    unittest.main()
