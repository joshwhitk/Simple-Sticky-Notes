from __future__ import annotations

import argparse
import json

from .app import StickyNotesApp
from .drop_import import import_dropped_paths
from .single_instance import InstanceServer, send_payload
from .windows_integration import install_windows_shortcuts


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Simple Sticky Notes")
    parser.add_argument("--new-note", action="store_true", help="Create and open a new note immediately.")
    parser.add_argument("--show-phone-notes", action="store_true", help="Open the phone's home-screen sticky notes.")
    parser.add_argument("--show-note", metavar="NOTE_ID", help="Open the note with this id.")
    parser.add_argument("--exit", action="store_true", help="Tell the running app to exit.")
    parser.add_argument(
        "--install-windows-integration",
        action="store_true",
        help="Create the desktop shortcut and startup shortcut.",
    )
    parser.add_argument("dropped_paths", nargs="*")
    return parser


def _command_from_args(args: argparse.Namespace) -> dict[str, object] | None:
    """The single Jump-List / CLI action requested, as a remote-command payload."""
    if args.new_note:
        return {"command": "new-note"}
    if args.show_phone_notes:
        return {"command": "show-phone-notes"}
    if args.show_note:
        return {"command": "show-note", "note_id": args.show_note}
    if args.exit:
        return {"command": "exit"}
    return None


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.install_windows_integration:
        shortcuts = install_windows_shortcuts()
        for name, path in shortcuts.items():
            print(f"{name}: {path}")
        return 0

    dropped_note_bodies = [item.body for item in import_dropped_paths(args.dropped_paths)] if args.dropped_paths else []

    app = StickyNotesApp()
    instance_server = InstanceServer(app.enqueue_remote_command)
    if not instance_server.start():
        # Another instance owns the port — forward this action to it and exit.
        if dropped_note_bodies:
            for body in dropped_note_bodies:
                if not send_payload({"command": "new-note", "body": body}):
                    return 1
            return 0
        command = _command_from_args(args)
        if command:
            return 0 if send_payload(command) else 1
        return 0

    app.attach_instance_server(instance_server)

    # Fresh start. --new-note is handled by create_new_note; --exit has nothing to
    # exit; any other action runs once the UI is up via startup_command.
    command = _command_from_args(args)
    startup_command: str | None = None
    if command and command["command"] == "exit":
        instance_server.stop()
        return 0
    if command and command["command"] != "new-note":
        startup_command = json.dumps(command)

    return app.run(
        create_new_note=args.new_note and not dropped_note_bodies,
        initial_note_bodies=dropped_note_bodies,
        startup_command=startup_command,
    )
