# Bugs

## 2026-04-22

- External plugin repo bug: `Abdo-reda/obsidian-sticky-notes-plugin` README pointed to a `releases/latest/download/sticky-notes.zip` URL that returned `404 Not Found`. Workaround used at the time: build from source locally. Final product decision: abandon the Obsidian-plugin runtime route entirely.
- Product fit bug: Obsidian pop-out windows are associated with the vault window, so they cannot satisfy the requirement that sticky notes remain on the desktop when Obsidian is not running. Resolution: move to a standalone desktop runtime.
- UI bug in the early standalone prototype: the note still read like it had a header strip and a visible corner-resize affordance instead of a literal sticky note. Fix applied: remove the dedicated top strip, keep only a custom `X`, and use invisible drag and resize hit zones.
- Rendering bug in the frameless prototype: `CreateRoundRectRgn` was given the configured radius directly even though Win32 expects ellipse dimensions, so the visible corners were tighter than the requested 4px radius. Fix applied: pass the correct diameter to the API.
- Interaction bug in the frameless prototype: the first pass at invisible drag and resize hit testing forced an arrow cursor over the text body, degrading normal text editing. Fix applied: preserve the text cursor in the editable region and reserve custom cursors for the drag and resize zones only.
- UI layering bug in the frameless prototype: the close `X` could be partially overdrawn by the editable text region, making it read like a `V`. Fix applied: reserve a dedicated right-side margin for the button and keep it above the content layer.
- Focus and selection bug in the frameless prototype: refocusing or resizing a note could leave Tk's default blue selection visible in blank trailing space. Fix applied: use sticky-themed selection colors, clear selection during focus and resize transitions, and route background clicks to append-style editing at the blank line.
- Sync bug in the first Obsidian integration pass: the delayed autosave job ID was never cleared after a save, which caused external file polling to think local edits were always pending and block 2-way reload behavior. Fix applied: manual and scheduled saves now cancel and clear the pending autosave token before writing.
- Drag bug: moving a sticky note window could still select text inside the note. Fix applied: drag now happens through a dedicated invisible drag zone above the text body, and drag gestures clear any stale selection before moving.
- Context-menu bug: right-click behavior was inconsistent across notes because the Tk popup grab was not being released reliably. Fix applied: build the menu from current state each time, call `tk_popup`, and always release the popup grab afterward.
- Lifecycle bug: there was no clear app-level exit path once notes were hidden and the process was still running. Fix applied: add a system tray icon with `New Sticky`, note reopening, and `Exit`.
- Notes refresh bug: deleting a source `.md` file did not disappear from the sticky-note list because metadata survived. Fix applied: prune orphaned metadata during menu refresh and close any open sticky whose backing markdown file is deleted.
- Windows integration path bug after moving the workspace: the existing desktop and startup `.lnk` files still targeted the previous folder because Windows shortcuts embed absolute target paths. Verified repair: rerun `python main.py --install-windows-integration` from the moved workspace to rewrite both shortcuts.
- Window placement bug: choosing another note from the right-click note list only focused it at its previous coordinates, which made note switching awkward and left some notes effectively lost off-screen after monitor/layout changes. Planned fix: anchor note switching to the current note, clamp it to the active work area, and add a `Tidy Onto Main Screen` recovery action for all open notes.
- Tray duplication bug: launching the app again while it is already running creates a second process and a second tray icon because each launch path starts a fresh `StickyNotesApp` and `pystray.Icon`. Planned fix: enforce a single running instance and forward `--new-note` commands to that existing process.
- Obsidian layout bug: storing notes under `Simple Sticky Notes\notes\` and metadata under a visible `meta\` folder made the vault view unnecessarily cluttered. Fix applied: note markdown files now live directly under `Simple Sticky Notes`, and metadata migrates into a hidden `.simple-sticky-notes\meta` folder.

## Open Bugs

- None currently tracked.
