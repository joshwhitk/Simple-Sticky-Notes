# Simple Sticky Notes

Simple Sticky Notes is a Windows desktop sticky-note companion app that stores note bodies as markdown files in a Dropbox-backed, Obsidian-readable folder.

The app is intentionally **not** built on top of Obsidian as the runtime. Obsidian remains a useful companion for editing, searching, and browsing the same markdown files, but the sticky-note windows themselves are owned by a standalone Windows app so they can remain visible and restorable independent of Obsidian.

## Goals

- Frameless desktop sticky-note windows
- Custom close button without a normal Windows title bar
- Resizable note windows
- Reliable autosave
- Markdown note storage plus sidecar metadata
- Restore open notes and positions after reboot/login
- Fast desktop shortcut for creating a new note
- Obsidian-compatible file storage

## Current Status

This repo is in active prototyping. The first implementation slice includes:

- Python/Tkinter app scaffold
- Markdown file storage in Dropbox
- Sidecar metadata for note geometry and open/closed state
- Frameless note window shell with custom close button
- Windows desktop/startup shortcut installer
- Initial storage tests
- Windows icon assets for the app

## Project Docs

- [MRD](docs/MRD.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Development](docs/DEVELOPMENT.md)
- [Roadmap](docs/ROADMAP.md)
- [Contributing](CONTRIBUTING.md)

## Quick Start

### Run the app

```powershell
python main.py
```

### Create a new note directly

```powershell
python main.py --new-note
```

### Install desktop and startup shortcuts

```powershell
python main.py --install-windows-integration
```

### Run tests

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
```

## Storage Layout

By default note data is stored under:

`C:\Users\Josh\Dropbox\backups\josh-obsidian\simple-sticky-notes\`

The storage layout is:

- `notes/<note-id>.md` for note bodies
- `meta/<note-id>.json` for window state and session metadata

This allows Obsidian to read the note bodies directly while the desktop app manages position, size, and runtime state separately.

## Repo Layout

```text
.
|-- assets/
|   `-- icons/
|-- docs/
|-- simple_sticky_notes/
|-- tests/
|-- main.py
|-- STATUS.MD
|-- bugs.md
`-- regression_tests.md
```

## Design Direction

- The desktop app is the runtime owner of notes.
- Obsidian is a secondary tool that reads the same markdown files.
- A future Obsidian control panel plugin is acceptable, but it should not become the sticky-note runtime.

## Why Not Obsidian Pop-Outs?

Obsidian pop-out windows are tied to Obsidian itself. That fails a key requirement for this project: sticky notes must remain restorable and desktop-native even when Obsidian is not running.

## Roadmap Summary

- Finish the standalone note runtime
- Harden session restore and startup behavior
- Improve Windows integration and packaging
- Add an optional Obsidian-side control panel

See [docs/ROADMAP.md](docs/ROADMAP.md) for more detail.
