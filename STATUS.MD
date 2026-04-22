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
- Notes persist to a normal file-backed store in `C:\Users\Josh\Dropbox\backups\josh-obsidian\`, not an opaque app-only database.
- Storage is Obsidian-readable markdown: `.md` note bodies plus sidecar metadata.
- Multiple notes can stay open simultaneously.
- Autosave should be reliable and low-friction.
- Startup/login behavior should restore previously open notes.
- Future adapters can target Obsidian folder storage first, then possibly Joplin/Evernote import or sync paths later.
- Optional Obsidian integration may provide a control panel for the companion app, but the desktop app remains the runtime owner of sticky notes.

## In Progress

### Pri1

- Use a GitHub-backed project structure for `Simple Sticky Notes`.
- Adapt or build a Windows companion sticky-note app as an alternative to using Obsidian as the runtime.
* Choose the best baseline implementation to adapt, currently leaning toward `Textylic` because it already has frameless desktop-widget behavior and source is available.
- Define the storage model for `.md` note content and note window metadata.
- Create Windows icon assets for `Simple Sticky Notes` for taskbar, desktop, and executable use.

## Planned

### Pri1

* Create the initial local git history for this workspace and keep the project GitHub-friendly.
* Clone the chosen baseline companion app into this workspace.
* Replace app-specific storage with folder-backed `.md` note files plus sidecar metadata for position, size, font, and restore state.
* Implement startup/session restore so notes reopen after reboot/login.
* Add a fast desktop shortcut path for `New Sticky Note`.
* Verify the app can run independently of Obsidian while still using an Obsidian-readable storage folder.
* Design an optional Obsidian control panel plugin or settings view for managing the companion app.

### Pri2

* Search local machine or other storage locations for clearer Joplin/Evernote exports if Dropbox remains inconclusive.
* Add import or adapter design for older plain-text note sources such as Dropbox `locaytanotes` if useful.
* Evaluate whether Joplin/Evernote interoperability should be import-only, one-way sync, or full read/write.

## Completed

### Pri1

* Initialized this workspace as a git repository.
* Installed Obsidian `1.12.7` on this PC.
* Removed the local `lokus` checkout from this workspace.
* Created and configured a test Obsidian vault with the `sticky-notes` plugin.
* Determined that the Obsidian plugin route is not the right product basis because notes must survive independently of Obsidian at runtime.
* Searched GitHub for Windows sticky-note apps and sticky-note integrations with Obsidian/Joplin/Evernote/plaintext storage.
* Determined there is no strong off-the-shelf GitHub project that already satisfies both the required desktop-window behavior and file-backed note interoperability.
* Identified `Textylic` as the strongest source-available UI/runtime baseline found so far.
* Searched Dropbox for likely Evernote and Joplin backup names and found no clear `.enex`, `.jex`, or Joplin profile backup under obvious names.

### Pri2

* Confirmed Obsidian-based sticky-note popouts are tied to Obsidian and therefore do not meet the requirement that notes remain on the desktop when Obsidian is not running.
* Built the Obsidian `sticky-notes` plugin locally because its documented release ZIP path returned `404`.

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
