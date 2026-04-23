from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import NamedTuple

from .obsidian_integration import obsidian_open_uri


class ShortcutLaunchSpec(NamedTuple):
    target: Path
    arguments: str
    working_directory: Path


def shortcut_icon_path() -> Path:
    if running_frozen():
        return Path(sys.executable).resolve()
    return resource_root() / "assets" / "icons" / "simple-sticky-notes.ico"


def resource_root() -> Path:
    if running_frozen():
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass).resolve()
    return Path(__file__).resolve().parent.parent


def pythonw_path() -> Path:
    executable = Path(sys.executable)
    if executable.name.lower() == "python.exe":
        sibling = executable.with_name("pythonw.exe")
        if sibling.exists():
            return sibling
    return executable


def project_root() -> Path:
    if running_frozen():
        return Path(sys.executable).resolve().parent
    return resource_root()


def running_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def shortcut_launch_spec(*, create_new_note: bool) -> ShortcutLaunchSpec:
    if running_frozen():
        arguments = "--new-note" if create_new_note else ""
        target = Path(sys.executable).resolve()
        return ShortcutLaunchSpec(
            target=target,
            arguments=arguments,
            working_directory=target.parent,
        )

    root = resource_root()
    entry = root / "main.py"
    arguments = f'"{entry}"'
    if create_new_note:
        arguments = f'{arguments} --new-note'
    return ShortcutLaunchSpec(
        target=pythonw_path(),
        arguments=arguments,
        working_directory=root,
    )


def create_shortcut(
    shortcut_path: Path,
    target: Path,
    arguments: str,
    icon_path: Path,
    working_directory: Path,
) -> None:
    shortcut_path.parent.mkdir(parents=True, exist_ok=True)
    escaped_shortcut = str(shortcut_path).replace("'", "''")
    escaped_target = str(target).replace("'", "''")
    escaped_args = arguments.replace("'", "''")
    escaped_icon = str(icon_path).replace("'", "''")
    escaped_working_dir = str(working_directory).replace("'", "''")
    script = f"""
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut('{escaped_shortcut}')
$shortcut.TargetPath = '{escaped_target}'
$shortcut.Arguments = '{escaped_args}'
$shortcut.IconLocation = '{escaped_icon}'
$shortcut.WorkingDirectory = '{escaped_working_dir}'
$shortcut.Save()
"""
    subprocess.run(["powershell", "-NoProfile", "-Command", script], check=True)


def install_windows_shortcuts() -> dict[str, str]:
    icon = shortcut_icon_path()
    desktop = Path.home() / "Desktop"
    startup = Path.home() / "AppData" / "Roaming" / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"

    shortcuts = {
        "desktop_new": desktop / "New Simple Sticky Note.lnk",
        "startup_app": startup / "Simple Sticky Notes.lnk",
    }
    desktop_spec = shortcut_launch_spec(create_new_note=True)
    startup_spec = shortcut_launch_spec(create_new_note=False)
    create_shortcut(
        shortcuts["desktop_new"],
        desktop_spec.target,
        desktop_spec.arguments,
        icon,
        desktop_spec.working_directory,
    )
    create_shortcut(
        shortcuts["startup_app"],
        startup_spec.target,
        startup_spec.arguments,
        icon,
        startup_spec.working_directory,
    )
    return {name: str(path) for name, path in shortcuts.items()}


def show_folder(path: Path) -> None:
    subprocess.Popen(["explorer.exe", str(path)])


def edit_in_notepad(path: Path) -> None:
    subprocess.Popen(["notepad.exe", str(path)])


def edit_in_obsidian(path: Path) -> None:
    os.startfile(obsidian_open_uri(path))
