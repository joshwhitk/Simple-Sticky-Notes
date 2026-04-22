# Status

## MRD Feature List

- App name: `Simple Sticky Notes`.
- Frameless sticky-note windows for Windows desktop use.
- Notes are resizable.
- Notes have a custom close `X` button without a normal Windows title bar/frame.
- Closing a note removes it from the desktop without deleting the note file.
- Very fast new-note creation from a desktop shortcut/icon.
- Notes reopen automatically and restore position after reboot/login.
- Notes remain usable as desktop objects without Obsidian running.
- Each note remembers position and size.
- Font family and font size are adjustable in a settings file; no dedicated UX is required initially.
- Notes persist to a normal file-backed store in a standard Windows user folder, not an opaque app-only database.
- Storage is Obsidian-readable markdown: `.md` note bodies plus sidecar metadata.
- Multiple notes can stay open simultaneously.
- Autosave should be reliable and low-friction.
- Startup/login behavior should restore previously open notes.
- Open notes should reflect edits made from Obsidian against the shared markdown files.
- Future adapters can target Obsidian folder storage first, then possibly Joplin/Evernote import or sync paths later.
- Optional Obsidian integration may provide a control panel for the companion app, but the desktop app remains the runtime owner of sticky notes.

## In Progress

### Pri1

- Adapt or build a Windows companion sticky-note app as an alternative to using Obsidian as the runtime.
- Define the storage model for `.md` note content and note window metadata.
- Harden the first working app slice: frameless note window behavior, autosave, and session persistence.
- Improve note lifecycle semantics so hidden notes stay hidden while open notes restore cleanly after login.
- Keep the repo presentable in the usual GitHub way as implementation work lands.

## Planned

### Pri2

* Improve note state handling after abnormal shutdowns or forced termination.

### Pri3

* Evaluate whether Joplin/Evernote interoperability should be import-only, one-way sync, or full read/write.
* Evaluate replacing the current menu-based font/color controls with native Windows chooser dialogs if the UX gain is worth the complexity.
* Expand tests beyond storage into more session and integration behaviors.
* Design an optional Obsidian control panel plugin or settings view for managing the companion app.
* Decide whether to adapt any external baseline further or continue with the current clean implementation.

## Completed

### Pri1

* Initialized this workspace as a git repository.
* Connected this workspace to `https://github.com/joshwhitk/Simple-Sticky-Notes.git`.
* Created and pushed the initial local git history to the GitHub repo.
* Added a GitHub-friendly repo shape with `README.md`, `docs/`, `CONTRIBUTING.md`, and issue templates.
* Installed Obsidian `1.12.7` on this PC.
* Removed the local `lokus` checkout from this workspace.
* Created and configured a test Obsidian vault with the `sticky-notes` plugin.
* Determined that the Obsidian plugin route is not the right product basis because notes must survive independently of Obsidian at runtime.
* Searched GitHub for Windows sticky-note apps and sticky-note integrations with Obsidian/Joplin/Evernote/plaintext storage.
* Determined there is no strong off-the-shelf GitHub project that already satisfies both the required desktop-window behavior and file-backed note interoperability.
* Identified `Textylic` as the strongest source-available UI/runtime baseline found so far.
* Searched Dropbox for likely Evernote and Joplin backup names and found no clear `.enex`, `.jex`, or Joplin profile backup under obvious names.
* Generated Windows icon assets for `Simple Sticky Notes` from the provided transparent PNG source.
* Implemented the first standalone app slice in Python/Tkinter with markdown body storage, JSON sidecar metadata, frameless note windows, and a custom close button.
* Removed the visible note title and visible resize-grip icon so the note looks more like a literal sticky note.
* Added rounded window corners and an invisible resize zone in place of the default corner grab UI.
* Flattened the remaining note chrome into the sticky body so the window no longer uses a visible top header strip.
* Corrected the Win32 rounded-corner implementation to deliver an actual 4px visual corner radius instead of a smaller effective curve.
* Separated the close-button area from the editable text region so the custom `X` is fully visible instead of being partially overdrawn by note content.
* Changed focus behavior so clicking the note background returns the caret to an append-style blank line instead of the end of the last content line.
* Removed the default blue selection look from the text widget and clear selection state after resize/focus transitions.
* Added regression coverage for the editor display-buffer rule so append-style blank-line focus does not leak extra trailing newlines into saved note files.
* Implemented Windows shortcut installation for a desktop `New Simple Sticky Note` launcher and a startup shortcut for restoring notes after login.
* Smoke-tested the app launch path and verified note files and metadata are created under the configured storage root.
* Verified the updated frameless note window launches cleanly after the chrome-removal changes.

### Pri2

* Confirmed Obsidian-based sticky-note popouts are tied to Obsidian and therefore do not meet the requirement that notes remain on the desktop when Obsidian is not running.
* Built the Obsidian `sticky-notes` plugin locally because its documented release ZIP path returned `404`.
* Diagnosed and fixed local unittest discovery so the repo test command works from the project root.
* Added a right-click note context menu with a flyout list of sticky notes that shows open/hidden state and can unhide/open a selected note with focus.
* Added right-click controls for note color, font size, and font family using the installed fonts visible to the app.
* Added right-click actions for `Show Folder`, `Edit in Notepad`, and `Edit in Obsidian`.
* Added `Split to New Sticky` when text is selected in the note editor.
* Extended note metadata persistence to store per-note background color.
* Switched the default storage location to a standard Windows Documents folder.
* Added a right-click `Set Storage Folder` action that saves a new storage location for use after restart.
* Changed note body files from opaque ID-based names to long content-based filenames with `-1` style uniqueness suffixes when needed.
* Implemented basic 2-way Obsidian sync by detecting external edits to shared markdown files and reloading them into open sticky windows.

## Deferred

### Pri3

* Resume any `lokus` build or evaluation work only if it becomes relevant again.
* Use Obsidian plugins as a primary sticky-note runtime only if the requirements are relaxed.

## Open Questions For Josh

* None currently.

## Resolved Decisions

* Store note bodies as `.md`.
* Optimize the first version for Obsidian-folder compatibility only.
* Closed notes stay hidden across reboot unless explicitly reopened.
