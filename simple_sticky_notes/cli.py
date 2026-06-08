from __future__ import annotations

import argparse

from .app import StickyNotesApp
from .drop_import import import_dropped_paths
from .single_instance import InstanceServer, send_payload
from .windows_integration import install_windows_shortcuts


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Simple Sticky Notes")
    parser.add_argument("--new-note", action="store_true", help="Create and open a new note immediately.")
    parser.add_argument(
        "--install-windows-integration",
        action="store_true",
        help="Create the desktop shortcut and startup shortcut.",
    )
    parser.add_argument("dropped_paths", nargs="*")
    return parser


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
        if dropped_note_bodies:
            for body in dropped_note_bodies:
                if not send_payload({"command": "new-note", "body": body}):
                    return 1
            return 0
        if args.new_note:
            return 0 if send_payload({"command": "new-note"}) else 1
        return 0
    app.attach_instance_server(instance_server)
    return app.run(
        create_new_note=args.new_note and not dropped_note_bodies,
        initial_note_bodies=dropped_note_bodies,
    )
