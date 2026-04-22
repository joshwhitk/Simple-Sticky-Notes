from __future__ import annotations

import argparse

from .app import StickyNotesApp
from .windows_integration import install_windows_shortcuts


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Simple Sticky Notes")
    parser.add_argument("--new-note", action="store_true", help="Create and open a new note immediately.")
    parser.add_argument(
        "--install-windows-integration",
        action="store_true",
        help="Create the desktop shortcut and startup shortcut.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.install_windows_integration:
        shortcuts = install_windows_shortcuts()
        for name, path in shortcuts.items():
            print(f"{name}: {path}")
        return 0

    app = StickyNotesApp()
    return app.run(create_new_note=args.new_note)
