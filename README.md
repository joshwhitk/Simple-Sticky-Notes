# Simple Sticky Notes

Simple Sticky Notes is a Windows desktop sticky-note companion app that stores note bodies as markdown files in the active Obsidian vault when one is available, with markdown files that Obsidian can read directly.

The app is intentionally **not** built on top of Obsidian as the runtime. Obsidian remains a useful companion for editing, searching, and browsing the same markdown files, but the sticky-note windows themselves are owned by a standalone Windows app so they can remain visible and restorable independent of Obsidian.

## Goals

- Frameless desktop sticky-note windows
- Custom close button without a normal Windows title bar
- Resizable note windows
- Reliable autosave
- Markdown note storage plus sidecar metadata
- 2-way shared-file sync with Obsidian edits
- Restore open notes and positions after reboot/login
- Fast desktop shortcut for creating a new note
- Obsidian-compatible file storage

## Current Status

This repo is in active prototyping. The current implementation includes:

- Python/Tkinter app scaffold
- Markdown file storage inside the active Obsidian vault when available
- Sidecar metadata for note geometry and open/closed state
- Content-based markdown filenames with uniqueness suffixes when needed
- Frameless note window shell with custom close button
- System tray icon with background-app exit controls
- Windows desktop/startup shortcut installer
- Right-click note menu for note switching, colors, fonts, and storage-folder changes
- External file polling so open stickies can reload markdown edits made from Obsidian
- Built Windows installer flow with detected-vault storage prefill
- Automated tests for storage, menu behavior, runtime recovery, and Obsidian integration
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

### Build the packaged app and installer

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File installer\build.ps1
```

### Move the repo folder

The repo itself is safe to move to another folder. After the move, rebuild the Windows shortcuts so the desktop and startup launchers stop pointing at the old path:

```powershell
python main.py --install-windows-integration
```

### Run tests

```powershell
python -m unittest -v
```

## Storage Layout

By default note data is stored under:

`<active Obsidian vault>\Simple Sticky Notes\`

If no Obsidian vault is available yet, the app falls back to `%USERPROFILE%\Documents\Simple Sticky Notes\`.

The storage layout is:

- `notes/<content-based note name>.md` for note bodies
- `meta/<note-id>.json` for window state and session metadata

This allows Obsidian to read the note bodies directly while the desktop app manages position, size, and runtime state separately. If two notes would produce the same body filename, the app adds `-1`, `-2`, and so on.

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
- The app can stay alive in the tray even when all notes are hidden.
- A future Obsidian control panel plugin is acceptable, but it should not become the sticky-note runtime.

## Why Not Obsidian Pop-Outs?

Obsidian pop-out windows are tied to Obsidian itself. That fails a key requirement for this project: sticky notes must remain restorable and desktop-native even when Obsidian is not running.

## Roadmap Summary

- Finish the standalone note runtime
- Harden session restore and startup behavior
- Improve Windows integration and packaging
- Add an optional Obsidian-side control panel

See [docs/ROADMAP.md](docs/ROADMAP.md) for more detail.
