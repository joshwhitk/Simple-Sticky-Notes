# Architecture

## Runtime Model

Simple Sticky Notes is a standalone Windows desktop app.

- The app owns sticky-note windows and session restore.
- Note content is stored as markdown files inside the active Obsidian vault when one is available, with a Documents fallback.
- Metadata is stored separately in JSON sidecars.
- Obsidian is a companion reader/editor for the same note files, not the runtime.
- Open sticky windows poll their backing markdown files so external edits can flow back into the desktop UI.

## Current Modules

### `main.py`

Thin entrypoint that dispatches into the package CLI.

### `simple_sticky_notes/cli.py`

Command-line entrypoints:

- normal launch
- create a new note
- install Windows shortcuts

### `simple_sticky_notes/app.py`

Desktop runtime:

- hidden root application
- frameless note windows
- autosave hooks
- session restore

### `simple_sticky_notes/storage.py`

Storage layer:

- create notes
- load/save markdown bodies
- persist metadata
- enumerate open notes

### `simple_sticky_notes/settings.py`

Settings persistence under `%APPDATA%\SimpleStickyNotes`, including storage-root migration into the active Obsidian vault.

### `simple_sticky_notes/obsidian_integration.py`

Obsidian integration helpers:

- detect the active vault from Obsidian config
- choose the preferred storage root inside that vault

### `simple_sticky_notes/windows_integration.py`

Windows-specific shortcut generation using PowerShell and WScript COM.

## Data Layout

```text
simple-sticky-notes/
|-- notes/
|   `-- <content-based note name>.md
`-- meta/
    `-- <note-id>.json
```

## Metadata Fields

Current metadata tracks:

- note id
- title
- content-based file stem for the markdown body
- x/y position
- width/height
- open/closed state
- created timestamp
- updated timestamp

## Planned Extensions

- Optional Obsidian control panel plugin
- Packaging into a Windows executable
- Better note discovery and reopen UI
- More explicit hidden vs archived semantics
