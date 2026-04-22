# MRD

## Product Name

`Simple Sticky Notes`

## Product Goal

Build a Windows desktop sticky-note companion app that keeps notes visible as standalone desktop objects while storing note bodies as markdown files in a normal Windows folder that Obsidian can also read.

## Primary User Requirements

- Notes are frameless and feel like desktop sticky notes.
- Notes are resizable.
- Notes have a custom close `X`.
- Closing a note hides it from the desktop without deleting it.
- A desktop shortcut can create a new note quickly.
- Open notes restore automatically after reboot/login.
- Notes remember position and size.
- Font family and font size are adjustable via settings.
- Note bodies are stored in markdown files.
- Runtime state is stored in sidecar metadata rather than an opaque database.
- The app works independently of Obsidian at runtime.

## Non-Goals For V1

- Rich markdown rendering inside note windows
- Full Joplin or Evernote read/write integration
- Obsidian as the sticky-note runtime
- Advanced in-app settings UI
- Sync conflict resolution UI

## Storage Requirements

- Base folder:
  - `%USERPROFILE%\Documents\Simple Sticky Notes\`
- Note body format:
  - `.md`
- Metadata format:
  - `.json`

## V1 Success Criteria

- A new note can be created from a desktop shortcut.
- A note can be moved, resized, edited, and hidden.
- The note body persists to markdown.
- Geometry and open/closed state persist to sidecar metadata.
- Startup integration restores previously open notes after login.
- Obsidian can open and read the note markdown files directly.
