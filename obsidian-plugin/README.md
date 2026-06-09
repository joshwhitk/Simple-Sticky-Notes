# Simple Sticky Notes Helper — Obsidian plugin

Two conveniences for the Simple Sticky Notes workflow:

1. **Open as sticky note** — a command, right-click (file-menu) item, and ribbon
   button that opens the current note as a real desktop sticky in the **Simple Sticky
   Notes** app.
2. **Auto-title new notes** — when an `Untitled` note gets a first line, the plugin
   renames the file to that line (first 10 words, sanitized to match the desktop app's
   filename rules). Toggle in the plugin's settings tab. Only ever touches notes still
   named `Untitled`/`Untitled N`, so it never renames notes you've already named.

## How it works
The desktop app listens on a localhost TCP socket (`127.0.0.1:38473`, see
`simple_sticky_notes/single_instance.py`). The plugin sends
`{"command": "open-as-sticky", "path": "<absolute .md path>"}`. The app resolves the
path to a managed sticky — adopting a vault-root note (creating its sidecar and adding
the `stickynote` tag, merge-safe) if it isn't one yet — and pops the sticky window.

Desktop-only (`isDesktopOnly: true`) — it uses Node's `net` to reach the app. Notes
must live in the **vault root** (where the desktop app stores stickies). The desktop
app must be running.

## Build
```
cd obsidian-plugin
npm install
npm run build        # -> main.js
```

## Install
Copy `main.js` + `manifest.json` into
`<vault>/.obsidian/plugins/open-as-sticky-note/`, then enable it in
**Settings → Community plugins** (Restricted Mode off).
