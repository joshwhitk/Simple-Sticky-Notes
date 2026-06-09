# Open as Sticky Note — Obsidian plugin

Adds an **"Open as sticky note"** command, right-click (file-menu) item, and ribbon
button to Obsidian. Triggering it opens the current note as a real desktop sticky in
the **Simple Sticky Notes** app.

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
