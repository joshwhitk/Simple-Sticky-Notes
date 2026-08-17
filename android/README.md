# Simple Sticky Notes — Android

Home-screen sticky-note widgets for Android with two storage backends, matching
the Windows desktop app:

- **Vault files (default)** — reads/writes the same Obsidian markdown files as
  the desktop app, via the Syncthing-synced vault folder. No sync code.
- **Joplin** — reads/writes notes through the Joplin Data API on the tailnet
  (`http://100.121.209.20:41185`, the phone runs Tailscale), same conventions
  as the desktop app's `simple_sticky_notes/joplin_storage.py`.

## Backends

The backend is a toggle button in the app's main screen ("Backend: vault files /
Joplin — tap to switch"), with fields for the Joplin API URL and token that
appear when Joplin is selected. Everything else (list, editor, both widgets)
works the same on either backend.

**Cutover to Joplin** = tap the backend toggle to Joplin, then paste the API
token and tap Set. The token lives on the VM in `/etc/agent-creds.env` as
`JOPLIN_DATA_API_TOKEN` — read it from there; it is never stored in this repo.
Switching back to vault files is the same toggle; the two backends don't touch
each other's notes.

Joplin-backend notes on the phone:
- Note identity is the Joplin note id, carried as a `joplin:<id>` key wherever
  the files backend used a path (intents, widget bindings). Only title+body
  round-trip; window geometry/color stays device-local, as on the desktop.
- Notes live in the "Simple Sticky Notes" notebook (found by title, created on
  demand).
- Every fetch/save refreshes an app-private cache (`files/joplin-cache/`), which
  is what home-screen widgets render from (widgets can't do network on the main
  thread) and what the editor falls back to offline. Offline, the app shows an
  empty list plus an error status/toast — it never crashes; editor saves retry
  as you keep typing.
- Cleartext HTTP is allowed only for `100.121.209.20`
  (`res/xml/network_security_config.xml`); any other API host would need HTTPS.
- Pasted images still go to the vault's `_attachments/` folder (the desktop
  Joplin backend does the same), so image paste needs the vault folder set.

## Compatibility contract (vault-files backend)
Notes are plain `.md` files in the vault root with merged YAML frontmatter
(`title:` = first non-blank line, `tags:` includes `stickynote`), plus a
`.simple-sticky-notes/meta/<id>.json` sidecar so the desktop app lists
phone-created notes too. The format logic in `Frontmatter.kt` is a faithful port
of the desktop app's `simple_sticky_notes/storage.py`; `FrontmatterTest`
mirrors the Python test suite to guarantee byte-compatible round-trips. The
Joplin backend is additive: the files backend's bytes on disk are unchanged.

## Features
Two widgets (both under the app "A New Stickynote" in the widget picker):
- **Sticky Note** — the per-note widget. Adding it from the picker creates a new
  sticky note (opens the quick editor) and then displays it; tap to edit, drag off
  the home screen to remove. Android widgets can't host inline text fields, so it's
  tap-to-edit.
- **Spawn** — a persistent button. One tap creates a new sticky note and offers to
  place a Sticky Note widget for it on the home screen — so a new home-screen sticky
  is one tap away, no widget-picker browsing needed.
- **In-app list/editor** — browse notes newest-first, create, edit, delete.
- **Paste images** — long-press in the editor → Paste (or paste from the keyboard
  clipboard) saves the image to the vault's `_attachments/` folder and inserts an
  Obsidian `![[image]]` embed, matching the desktop app.

## Build (Windows)
Requires the Android SDK (`C:\Users\Josh\Android\Sdk`, platform 34 + build-tools
34.0.0) and the JDK wired via `gradle.properties: org.gradle.java.home`
(currently `C:\Users\Josh\tools\jdk-21.0.11+10`).

```
cd android
.\gradlew.bat test assembleDebug
```
Output APK: `app/build/outputs/apk/debug/simple-sticky-notes-<version>-<buildType>.apk`
(e.g. `simple-sticky-notes-1.9-debug.apk` — the artifact is renamed in
`app/build.gradle.kts` so it's self-identifying, never the generic `app-debug.apk`).

## Deploy (wireless adb)
Wireless debugging is paired with the Pixel 7 Pro (`cheetah`), so install cable-free.
`adb` lives at `C:\Users\Josh\Android\Sdk\platform-tools\adb.exe` (not on PATH).

```
adb mdns services                       # discover current 192.168.x.x:port
adb connect 192.168.4.60:<port>         # port changes on reboot / WD toggle
adb -s 192.168.4.60:<port> install -r app/build/outputs/apk/debug/simple-sticky-notes-1.0-debug.apk
```
First run on the phone: **Grant storage access** (All files access) → **Pick vault
folder** (the synced `joshs-stuff` folder). Then long-press the home screen →
Widgets → Simple Sticky Notes → add a **Sticky Note** (pick a note) or **New Sticky
Note** widget. (Sideloading by copying the APK into the vault still works as a fallback.)

## Limitations (Android platform)
- No literal typing on the home screen — widgets are tap-to-edit.
- Apps can't silently place widgets or detect free slots; placement is one system
  confirm each (capped at 40 from the app).
- Concurrent edits on phone + desktop before sync can create Syncthing
  `.sync-conflict` files (rare).
