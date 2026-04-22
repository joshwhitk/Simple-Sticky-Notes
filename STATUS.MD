# Status

## MRD Feature List

- App name: `Simple Sticky Notes`.
- Frameless sticky-note windows for Windows desktop use.
- Notes are resizable.
- Notes have a custom close `X` button without a normal Windows title bar or frame.
- Closing a note removes it from the desktop without deleting the note file.
- Very fast new-note creation from a desktop shortcut or icon.
- Notes reopen automatically and restore position after reboot or login.
- Notes remain usable as desktop objects without Obsidian running.
- Each note remembers position and size.
- Font family and font size are adjustable.
- Notes persist to a normal file-backed store in a standard Windows user location, not an opaque app-only database.
- Storage is Obsidian-readable markdown: `.md` note bodies plus sidecar metadata.
- Multiple notes can stay open simultaneously.
- Autosave should be reliable and low-friction.
- Startup or login behavior should restore previously open notes and leave hidden notes hidden.
- Open notes should reflect edits made from Obsidian against the shared markdown files.
- Optional Obsidian integration may provide a control panel later, but the desktop app remains the runtime owner of sticky notes.

## In Progress

### Pri1

- Change the Microsoft Store listing from free to a paid price around USD `$10`, using the Store pricing workflow that keeps the current review/publish status clear.
- Enforce a single tray-backed app instance so launching `Simple Sticky Notes` or `--new-note` reuses the running process instead of creating duplicate tray icons.
- Move a selected note to the right of the current note when chosen from the right-click note list, clamped on-screen.
- Add `Tidy Onto Main Screen` to the right-click menu so all open notes are moved and resized back onto the primary display.
- Apply a native Windows drop shadow to frameless note windows if the OS window manager will honor it.
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

## Completed

### Pri1

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
- Diagnosed the desktop shortcut `failed to import encoding module` error as a stale installed shortcut definition still passing `_internal\\main.py` to the packaged EXE; repaired the existing desktop and startup `.lnk` files in place so they now launch the installed EXE directly with supported arguments only.
- Diagnosed the wrong desktop shortcut icon as a packaged-path bug: installed shortcuts were pointing at a non-existent `_internal\\assets\\icons\\simple-sticky-notes.ico` file. Fix applied in source: packaged shortcuts now use the installed EXE itself as the icon source.
- Built the `1.0.2` packaged app and installer from clean staging output after the stock `installer\\build.ps1` path was blocked by a live lock on the Dropbox `dist\\` directory; the staged packaged EXE passed a 2-second liveness smoke check.
- Published `v1.0.2` to GitHub, including the patched installer asset, and mirrored the same installer to the direct download URL used for Store-friendly hosting.

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

## Open Questions For Josh

- None currently.

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
