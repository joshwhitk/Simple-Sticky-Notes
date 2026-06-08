active: Standalone sticky notes work reliably; desktop polish and packaging remain.

# Status

## In Progress

### Pri1

- Manually verify desktop-shortcut and taskbar drag-drop on this PC with real Explorer drops now that the packaged app accepts dropped files and shortcuts.
- Move a selected note to the right of the current note when chosen from the right-click note list, clamped on-screen.
- Add `Tidy Onto Main Screen` to the right-click menu so all open notes are moved and resized back onto the primary display.
- Apply a native Windows drop shadow to frameless note windows if the OS window manager will honor it.
- Validate autosave, startup restore, and hidden-note restore behavior in the packaged app on this PC.
- Validate the packaged installer end-to-end on this PC, including the detected-vault storage prompt and installed shortcut behavior.
- Verify the updated stable-filename Obsidian flow manually on this PC so editing in Obsidian no longer steals focus into another note.
- Keep the repo and docs aligned with the app as implementation and validation land.

## Planned

### Pri2

- Improve test coverage for desktop topology changes such as adding, removing, and restoring a second monitor.
- Improve test coverage for sleep, restart, and other real-world power transitions.
- Stress-test Obsidian two-way sync under overlapping edits so conflict behavior is well understood before more sync scope is added.
- Measure idle CPU and memory usage and verify the app and tray process do not keep the PC awake unnecessarily.

### Pri3

- If an unrecoverable sync conflict ever occurs, preserve both edits in the note instead of silently discarding one side.
- Decide whether interoperability with other note apps should exist at all, and if it does, whether it should be import-only, one-way sync, or full read-write.
- Design a settings view for managing the companion app instead of relying only on context menus and config files.
- Support sketching over sticky-note text with Windows touch or pen input as a deferred enhancement once the core text-note workflow is stable.

## Completed

### Pri0

- Revised `STATUS.MD` to keep active work grouped by status and priority, with the duplicate tray-icon bug tracked as an urgent item until the fix landed.
- Enforced a single tray-backed app instance so launching `Simple Sticky Notes` or `--new-note` reuses the running process instead of creating duplicate tray icons.
- Reorganized the repo docs so Microsoft Store material is clearly marked as deferred, and moved Store work into a `Pri4` deferred bucket instead of leaving it in active priorities.

### Pri1

- Added a stdio MCP server plus a Python service bridge so other apps and agents can list, search, create, fetch, edit, hide, reopen, and delete sticky notes against the live Obsidian-backed storage root.
- Registered `simple-sticky-notes` in the shared `whitkin-apps` registry with an `mcp` transport and validated the registry after fixing the CLI path-truncation issue caused by spaces in the Dropbox checkout path.
- Expanded the sticky-note MCP surface so other apps and agents can also query live app status, list recently changed notes, create visible notes, show/focus notes, move/resize notes, tidy open notes onto the main screen, open notes in Obsidian, and reveal note folders in Explorer.
- Fixed the first `notes_changed_since` pass so second-granularity timestamps do not silently miss notes updated within the same second.
- Rebuilt the normal packaged app and installer after the MCP/live-command changes, producing a fresh `dist\installer\Simple-Sticky-Notes-Setup.exe`.
- Implemented dropped-file import on the app launch path so dropping `.url` shortcuts or text files onto the desktop/taskbar launcher creates sticky notes from their contents, while non-text drops are copied into `Attachments\` under the Obsidian-backed storage root and linked from the new sticky note.
- Aligned the repo docs with the current Whitkin MCP project standards by making `STATUS.MD` start with a one-line status, surfacing the canonical tracker files in `README.md`, and documenting the MCP server/registry conventions in `docs/DEVELOPMENT.md`.
- Initialized the original local project workspace as a git repository.
- Connected the project repo to `https://github.com/joshwhitk/Simple-Sticky-Notes.git`.
- Created and pushed the initial local git history to GitHub.
- Added a GitHub-friendly repo shape with `README.md`, `docs/`, `CONTRIBUTING.md`, issue templates, runtime requirements, and installer scripts.
- Installed Obsidian `1.12.7` on this PC.
- Removed the local `lokus` checkout from this workspace.
- Determined that the Obsidian plugin route is not the right product basis because notes must survive independently of Obsidian at runtime.
- Removed the abandoned Obsidian `sticky-notes` plugin path and related local source checkout.
- Implemented the standalone Python/Tkinter app with markdown body storage, JSON sidecar metadata, frameless note windows, and a custom close button.
- Removed the visible note title and visible resize-grip icon so the note reads as a literal sticky note.
- Added rounded window corners and an invisible resize zone in place of the default corner-grab UI.
- Flattened the remaining note chrome into the sticky body so the window no longer uses a visible top header strip.
- Corrected the Win32 rounded-corner implementation to deliver an actual 4px visual corner radius.
- Separated the close-button area from the editable text region so the custom `X` stays fully visible.
- Changed focus behavior so clicking the note background returns the caret to an append-style blank line instead of the end of the last content line.
- Removed the default blue trailing selection look from the text widget and clear selection state after resize and focus transitions.
- Fixed drag behavior by moving window-drag interaction to a dedicated invisible drag zone so dragging the sticky does not select note text.
- Fixed inconsistent right-click menu behavior by rebuilding menus from current state and releasing the Tk popup grab cleanly every time.
- Added a system tray icon with note access, new-note creation, and a clean app exit path.
- Changed app lifecycle behavior so closing the last note leaves the app alive in the tray instead of forcing shutdown.
- Changed startup behavior so the app no longer creates a blank note when no notes are marked open.
- Improved note lifecycle semantics so hidden notes stay hidden while open notes restore cleanly after login.
- Improved note state handling after abnormal shutdowns or forced termination by adding an explicit runtime-state marker and startup reconciliation pass.
- Implemented Windows shortcut installation for a desktop `New Simple Sticky Note` launcher and a startup shortcut for restoring notes after login.
- Built a Windows install package and build script that detect an existing Obsidian vault during install and prefill storage accordingly.
- Smoke-tested the tray-backed app launch path and verified note files and metadata are created under the configured storage root.
- Audited the repo for workspace-path assumptions and confirmed the app code resolves its own project paths dynamically, so the project folder itself is safe to move.
- Validated the moved Dropbox workspace: `python -m unittest -v` passes, timed tray smoke runs succeed, the packaged build succeeds, and rerunning `python main.py --install-windows-integration` repairs Windows shortcuts that still point at the previous folder.
- Restored the existing git history into the Dropbox workspace by copying the original checkout's `.git` directory, verified `git status` works from the moved repo path, and prepared the workspace for normal commits again.
- Flattened the storage layout so note markdown files now live directly under `Simple Sticky Notes`, while note metadata migrates into a hidden `.simple-sticky-notes\meta` sidecar folder.
- Added startup migration for the old `notes\` and visible `meta\` folders so existing installs move forward automatically without losing notes or note state.
- Added README comparison notes explaining why Microsoft Sticky Notes is adjacent but not a substitute for this project's local markdown and Obsidian-compatible storage model.
- Removed the hand-installed app footprint before installer testing by stopping the live `main.py` tray processes, deleting the Python-created desktop and startup shortcuts, and clearing `%APPDATA%\SimpleStickyNotes` while leaving note content files untouched.
- Pushed the current local commits to GitHub and prepared the first GitHub release flow with the current Windows installer artifact.
- Diagnosed the installer launch failure as a packaged-shortcut bug: the post-install Windows integration step was generating shortcuts that passed `_internal\main.py` to the frozen EXE instead of launching the installed EXE directly.
- Fixed packaged shortcut generation so installer-created desktop and startup shortcuts now target the installed EXE with only supported CLI flags, while source checkouts still use `pythonw.exe main.py`.
- Disabled Smart App Control on this developer machine so local installer validation is no longer blocked by reputation-based prompts.
- Published the corrected installer to GitHub as `v1.0.1` and confirmed the public release asset path is ready for a Microsoft Store `EXE` submission.
- Prepared Microsoft Store submission content for the current release: Partner Center field values, listing copy, screenshot/box-art checklist, and a privacy-policy draft.
- Diagnosed the Obsidian focus-jump bug as filename churn during external sync: saving after an Obsidian edit recalculated the markdown filename from the live note body, so the file path could change underneath Obsidian while typing.
- Changed note titles to the first 10 words of the note and kept markdown filenames stable after creation so Obsidian editing no longer triggers live file renames.
- Added regression coverage for the first-10-words title rule and for external Obsidian edits reloading the sticky body without renaming the markdown file.
- Created the Microsoft Partner Center product and submitted the first Store listing for review under Partner Center ID `78b96f9d-3b84-447d-93c2-50fe1a3e52a6`.
- Confirmed the Store submission was accepted with a directly hosted installer URL and is now in the review queue with an estimated review time of about three days.
- Captured the current Microsoft guidance for switching the Store listing to paid pricing: pricing is changed from the `Pricing and availability` page through a submission update, and package uploads are not required when only metadata such as price changes.
- Confirmed the first Microsoft Store `EXE` submission path is blocked by signing requirements, and the next Store submission should pivot to `MSIX`, which Microsoft documents as the recommended format with free Microsoft code signing and CDN hosting.
- Updated the public README so Microsoft Store availability is described as `coming soon` instead of implying the app is already purchasable there.
- Added the full Microsoft Store screenshot and box-art set to the repo under `docs/screenshots/` and embedded all of them in the README so the GitHub project page shows the app visually.
- Diagnosed the desktop shortcut `failed to import encoding module` error as a stale installed shortcut definition still passing `_internal\\main.py` to the packaged EXE; repaired the existing desktop and startup `.lnk` files in place so they now launch the installed EXE directly with supported arguments only.
- Diagnosed the wrong desktop shortcut icon as a packaged-path bug: installed shortcuts were pointing at a non-existent `_internal\\assets\\icons\\simple-sticky-notes.ico` file. Fix applied in source: packaged shortcuts now use the installed EXE itself as the icon source.
- Built the `1.0.2` packaged app and installer from clean staging output after the stock `installer\\build.ps1` path was blocked by a live lock on the Dropbox `dist\\` directory; the staged packaged EXE passed a 2-second liveness smoke check.
- Published `v1.0.2` to GitHub, including the patched installer asset, and mirrored the same installer to the direct download URL used for Store-friendly hosting.
- Added local Dropbox ignore rules at the Dropbox root so future `build`, `dist`, `build_stage_*`, and `dist_stage_*` folders under this repo do not sync by default on this machine.
- Refined the local Dropbox ignore rules so this repo keeps syncing source plus final shipped binaries, while excluding local build scratch folders, `for-ms-store`, `obsidian-test-vault`, and the separate `Muesli\\muesli\\.tmp` temp area shown in Dropbox warnings.
- Re-verified the repaired desktop shortcut by launching the `.lnk` itself and confirming it starts another `Simple Sticky Notes.exe` process with the packaged `--new-note` path.
- Diagnosed the remaining desktop launch failure as a corrupted installed app payload, not a shortcut problem: the installed `_internal` folder was missing `base_library.zip`, which prevented the packaged interpreter from importing `encodings`. Reinstalling `v1.0.2` restored the runtime files, and the desktop `.lnk` now launches successfully.
- Diagnosed the next installed desktop-launch failure as a packaged resource-path bug: the tray/icon loader still looked for `assets\\icons\\simple-sticky-notes-64.png` beside the installed EXE, but packaged assets live under PyInstaller's `_internal` resource root. Fix applied: packaged resource lookup now uses `sys._MEIPASS` via `resource_root()` for tray/icon assets.
- Added regression coverage for frozen-mode resource lookup and tray icon loading from the packaged resource root.
- Rebuilt the installer as `1.0.3`, reinstalled it silently over the local install, and verified the actual desktop `New Simple Sticky Note.lnk` now launches the installed EXE successfully with `--new-note`.
- Diagnosed the tray-icon interaction bug on Windows: the `pystray` menu handle was present, but left click was a no-op because no default tray action was registered, which made the tray icon feel dead. Fix applied: the custom Win32 tray icon now opens the popup menu on left click as well as right click.
- Added regression coverage for the Win32 tray icon opening its popup menu on left click.
- Updated the machine's Obsidian vault path to `C:\Users\Josh\Dropbox\joshs-stuff` and aligned the app's live `settings.json` storage root with `C:\Users\Josh\Dropbox\joshs-stuff\Simple Sticky Notes`.
- Added an Obsidian-vault-move migration so when the active Obsidian vault changes, the app can move its `Simple Sticky Notes` storage root to the new vault automatically.
- Added regression coverage for migrating sticky-note storage from one Obsidian vault root to another.
- Re-ran the full regression checks after the vault-path update: `python -m unittest -v` passed `34` tests and `installer\build.ps1` succeeded.
- Added a localhost single-instance guard and command-forwarding path so duplicate launches no longer create duplicate tray icons, and re-ran the regression suite at `36` passing tests.
- Verified the single-instance change packages through a clean staged PyInstaller build; the stock `installer\build.ps1` path is still intermittently blocked by the existing `dist\` workspace lock on this machine.

### Pri2

- Confirmed Obsidian-based sticky-note popouts are tied to Obsidian and therefore do not meet the requirement that notes remain on the desktop when Obsidian is not running.
- Built the Obsidian `sticky-notes` plugin locally when its documented release ZIP path returned `404`, then later removed that route entirely.
- Searched GitHub for Windows sticky-note apps and sticky-note integrations with Obsidian, Joplin, Evernote, and plaintext storage.
- Determined there is no strong off-the-shelf GitHub project that already satisfies both the required desktop-window behavior and file-backed note interoperability.
- Identified `Textylic` as the strongest source-available UI and runtime baseline found early in the search.
- Searched Dropbox for likely Evernote and Joplin backup names and found no clear `.enex`, `.jex`, or Joplin profile backup under obvious names.
- Generated Windows icon assets for `Simple Sticky Notes` from the provided transparent PNG source.
- Diagnosed and fixed local unittest discovery so the repo test command works from the project root.
- Added a right-click note context menu with a flyout list of sticky notes that shows open or hidden state and can reopen a selected note with focus.
- Added right-click controls for note color, font size, and font family using the installed fonts visible to the app.
- Added right-click actions for `Show Folder`, `Set Storage Folder`, `Edit in Notepad`, and `Edit in Obsidian`.
- Added `Split to New Sticky` when text is selected in the note editor.
- Extended note metadata persistence to store per-note background color.
- Switched the default storage location to a standard Windows Documents folder, then aligned storage with the active Obsidian vault and migrated existing notes there.
- Changed note body files from opaque ID-based names to long content-based filenames with `-1` style uniqueness suffixes when needed.
- Implemented basic 2-way Obsidian sync by detecting external edits to shared markdown files and reloading them into open sticky windows.
- Improved `Edit in Obsidian` so note launches use vault-relative Obsidian URIs when possible.
- Fixed note-list refresh so deleting a source `.md` file removes the note from menus and closes any open sticky for that deleted file.
- Added regression coverage for deleted-note refresh, repeated context-menu popup safety, tray-only startup without forced blank notes, vault-relative Obsidian URIs, and runtime shutdown markers.
- Verified after a full PC restart that sticky notes loaded again, which is a positive signal for startup restore behavior.

## Deferred

### Pri3

- Resume any `lokus` build or evaluation work only if it becomes relevant again.
- Use Obsidian plugins as a primary sticky-note runtime only if the product requirements are relaxed.
- Add an optional Obsidian-side control panel only as a companion surface, not as the sticky-note runtime.

### Pri4

- Revisit Microsoft Store distribution only after the desktop app behavior is stable enough to justify another packaging pass.
- Recover a working Store submission path after the rejected `EXE` attempt and failed local `MSIX` attempt.
- Revisit Store pricing around USD `$10` only after the packaging and signing path is working again.
- Keep the Store listing/public messaging in a deferred `coming soon` state until the packaging path is actually usable.

## Open Questions For Josh

- None currently.

## Testing Status

- Last full regression run: `2026-04-27` `python -m unittest -v` passed `50` tests.
- Sticky-note service regression run: `2026-04-27` `python -m unittest tests.test_service_api -v` passed `6` tests.
- Drag-drop regression run: `2026-04-27` `python -m unittest tests.test_cli tests.test_app tests.test_drop_import -v` passed `15` tests.
- Shared app registry validation: `2026-04-27` `node C:/Users/Josh/Dropbox/code/whitkin-apps/bin/whitkin-apps.js validate` passed.
- MCP smoke test: `2026-04-27` live stdio client connected and listed `16` tools, including `get_sticky_notes_status`.
- Installer build status: `2026-04-27` `powershell -NoProfile -ExecutionPolicy Bypass -File installer\build.ps1` succeeded after a transient lock on the previous `dist\Simple Sticky Notes` folder was cleared by renaming that stale directory and rerunning the build.
- Current bug snapshot: no open in-app bugs are tracked; one external `whitkin-apps` CLI path-with-spaces bug is documented with a manual registry workaround.

## Resolved Decisions

- Store note bodies as `.md`.
- Optimize the first version for Obsidian-folder compatibility only.
- Closed notes stay hidden across reboot unless explicitly reopened.
- Keep the current menu-based font and color controls instead of switching to native Windows chooser dialogs for now.
- Continue with the current clean implementation rather than adapting an external baseline further.
- Existing Windows desktop and startup shortcuts must be rebuilt after a repo-folder move because `.lnk` targets embed the old project path.
- Obsidian-facing storage should keep note markdown files directly in the `Simple Sticky Notes` root and move sidecar metadata into a hidden app-managed folder.
- The first Microsoft Store submission should use the current `EXE/MSI` flow because the app already has a working offline installer, a public versioned download URL, and silent-install support; revisit `MSIX` later only if Store-managed packaging becomes worth the migration cost.
- GitHub release asset URLs are not valid Partner Center package URLs for the `EXE/MSI` flow because they redirect; the Store submission needs a direct HTTPS installer URL plus CA-trusted code signing.
- For Microsoft Store `EXE/MSI` submissions, use a direct hosted installer URL you control rather than a GitHub release asset URL.
- Microsoft Store work is no longer an active delivery priority; treat it as deferred distribution work until the core desktop app priorities are done.
