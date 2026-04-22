from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from .obsidian_integration import obsidian_open_uri

def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def pythonw_path() -> Path:
    executable = Path(sys.executable)
    if executable.name.lower() == "python.exe":
        sibling = executable.with_name("pythonw.exe")
        if sibling.exists():
            return sibling
    return executable


def create_shortcut(shortcut_path: Path, target: Path, arguments: str, icon_path: Path) -> None:
    shortcut_path.parent.mkdir(parents=True, exist_ok=True)
    escaped_shortcut = str(shortcut_path).replace("'", "''")
    escaped_target = str(target).replace("'", "''")
    escaped_args = arguments.replace("'", "''")
    escaped_icon = str(icon_path).replace("'", "''")
    script = f"""
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut('{escaped_shortcut}')
$shortcut.TargetPath = '{escaped_target}'
$shortcut.Arguments = '{escaped_args}'
$shortcut.IconLocation = '{escaped_icon}'
$shortcut.WorkingDirectory = '{project_root()}'
$shortcut.Save()
"""
    subprocess.run(["powershell", "-NoProfile", "-Command", script], check=True)


def install_windows_shortcuts() -> dict[str, str]:
    root = project_root()
    icon = root / "assets" / "icons" / "simple-sticky-notes.ico"
    entry = root / "main.py"
    target = pythonw_path()
    desktop = Path.home() / "Desktop"
    startup = Path.home() / "AppData" / "Roaming" / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"

    shortcuts = {
        "desktop_new": desktop / "New Simple Sticky Note.lnk",
        "startup_app": startup / "Simple Sticky Notes.lnk",
    }
    create_shortcut(shortcuts["desktop_new"], target, f'"{entry}" --new-note', icon)
    create_shortcut(shortcuts["startup_app"], target, f'"{entry}"', icon)
    return {name: str(path) for name, path in shortcuts.items()}


def show_folder(path: Path) -> None:
    subprocess.Popen(["explorer.exe", str(path)])


def edit_in_notepad(path: Path) -> None:
    subprocess.Popen(["notepad.exe", str(path)])


def edit_in_obsidian(path: Path) -> None:
    os.startfile(obsidian_open_uri(path))
