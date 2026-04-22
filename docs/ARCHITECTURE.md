# Architecture

## Runtime Model

Simple Sticky Notes is a standalone Windows desktop app.

- The app owns sticky-note windows and session restore.
- Note content is stored as markdown files in a Dropbox-backed folder.
- Metadata is stored separately in JSON sidecars.
- Obsidian is a companion reader/editor for the same note files, not the runtime.

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

Settings persistence under `%APPDATA%\SimpleStickyNotes`.

### `simple_sticky_notes/windows_integration.py`

Windows-specific shortcut generation using PowerShell and WScript COM.

## Data Layout

```text
simple-sticky-notes/
|-- notes/
|   `-- <note-id>.md
`-- meta/
    `-- <note-id>.json
```

## Metadata Fields

Current metadata tracks:

- note id
- title
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
