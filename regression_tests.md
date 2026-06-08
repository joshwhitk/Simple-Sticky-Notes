# Regression Tests

## Planned

- Add durable regression coverage when a bug repeats or a manual finding reveals a realistic failure mode that should stay fixed.

## Run Before Shipping

- `python -m unittest -v`
- `powershell -NoProfile -ExecutionPolicy Bypass -File installer\build.ps1`

## Results

- On `2026-06-02`, `python -m unittest -v` passed `58` tests after reviewing the Obsidian frontmatter feature (auto `title` from the first non-blank line + `stickynote` tag) and fixing three defects plus adding user-frontmatter preservation:
  - external-sync no longer doubles the frontmatter block or rewrites the title to `---` (`app.py` `_current_disk_body` now strips frontmatter like `load_note`);
  - YAML `title` is double-quoted so first lines containing `:` `"` `[` `{` `#` or leading `---` stay valid YAML for Obsidian's properties parser;
  - `strip_frontmatter` uses line-exact `---` delimiters, so a note body containing a markdown rule line round-trips unchanged.
  - On save, the app now *merges* into any existing on-disk frontmatter (`merge_frontmatter`) instead of replacing it: a sticky note the user also edited in Obsidian keeps its custom properties (`aliases`, `cssclass`, etc.) and extra tags, while the app still owns `title` and guarantees the `stickynote` tag. Handles block-list, inline-flow, scalar, missing, and already-present tag representations; idempotent across re-saves. App-created notes (no prior YAML) are unaffected.
  - New durable coverage: `tests/test_app.py::test_external_sync_does_not_double_frontmatter_or_corrupt_title` and seven `tests/test_storage.py` frontmatter tests (YAML validity, exact-inverse round-trip, single-block save, user-property preservation, tag-representation merge). The YAML-parsing tests skip cleanly if PyYAML is absent, since it is a test-only convenience and not a runtime dependency.
- On `2026-04-27`, `python -m unittest -v` passed `50` tests after the dropped-file import path and docs cleanup landed.
- On `2026-04-27`, `python -m unittest tests.test_cli tests.test_app tests.test_drop_import -v` passed `15` focused tests covering dropped-path forwarding, initial note creation from dropped content, and importing `.url`, text, and binary files.
- On `2026-04-27`, `powershell -NoProfile -ExecutionPolicy Bypass -File installer\build.ps1` succeeded after the dropped-file import changes and produced a fresh installer at `dist\installer\Simple-Sticky-Notes-Setup.exe`.
- On `2026-04-27`, the first retry of `installer\build.ps1` failed before PyInstaller ran because `dist\Simple Sticky Notes` was locked by an external handle. Renaming that stale directory out of the way confirmed the lock was environmental rather than a code/build-graph failure, and the immediate rerun succeeded.
- On `2026-04-27`, the docs were cleaned up to match the Whitkin MCP project standards: `STATUS.MD` now begins with a one-line status, `README.md` calls out the canonical tracker files plus the local MCP server, and `docs/DEVELOPMENT.md` documents the registry/MCP conventions. No separate automated test was needed beyond the code/build runs in the same turn.
- On `2026-04-27`, `python -m unittest -v` passed `45` tests after the live-command MCP additions landed.
- On `2026-04-27`, `python -m unittest tests.test_cli tests.test_app tests.test_service_api -v` passed `16` focused tests covering JSON remote commands, visible-note creation, changed-since queries, and existing-instance forwarding.
- On `2026-04-27`, `python -m unittest tests.test_service_api -v` passed `6` targeted tests covering server-side creation, visible-note creation, search, append-editing, changed-since filtering, and live-status reporting.
- On `2026-04-27`, a live stdio MCP smoke test connected to `mcp-server/index.js`, listed `16` exposed tools, and successfully called `get_sticky_notes_status` against the active vault-backed storage root.
- On `2026-04-27`, `powershell -NoProfile -ExecutionPolicy Bypass -File installer\build.ps1` succeeded after the MCP/live-command additions and produced a fresh installer at `dist\installer\Simple-Sticky-Notes-Setup.exe`.
- On `2026-04-27`, `python -m unittest -v` passed `39` tests after the sticky-note MCP service bridge and stdio server landed.
- On `2026-04-27`, `python -m unittest tests.test_service_api -v` passed `3` targeted tests covering server-side note creation, search, and edit behavior.
- On `2026-04-27`, a live stdio MCP smoke test connected to `mcp-server/index.js`, listed `8` exposed tools, and successfully called `list_sticky_notes` against the active vault-backed storage root.
- On `2026-04-27`, `node C:/Users/Josh/Dropbox/code/whitkin-apps/bin/whitkin-apps.js validate` passed after the shared registry entry for `simple-sticky-notes` was corrected to a proper `mcp` transport.
- On `2026-04-27`, `python -m unittest -v` passed `36` tests after the single-instance tray fix landed.
- On `2026-04-27`, a focused CLI/app regression run for the duplicate-tray fix passed `7` tests:
  - `python -m unittest tests.test_cli tests.test_app -v`
- On `2026-04-27`, the docs were reorganized to move Microsoft Store work into a deferred track and mark the Store planning files as deferred drafts. No automated tests were run for that docs-only reclassification.
- On `2026-04-27`, `STATUS.MD` was simplified so feature inventory stays in `docs/MRD.md` and only active/deferred work remains in the status tracker. No automated tests were run for that docs-only cleanup.
- On `2026-04-27`, `installer\build.ps1` could not be re-run for the duplicate-tray change because `dist\Simple Sticky Notes\_internal` was locked by another process in this workspace before PyInstaller started. This was the same environment-style `dist\` lock issue seen previously, not a Python test failure.
- On `2026-04-27`, a clean staged PyInstaller build succeeded for the single-instance change using `--distpath dist_stage_single_instance --workpath build_stage_single_instance`, confirming the new `single_instance.py` module is included in the packaged app.
- On `2026-04-27`, `powershell -NoProfile -ExecutionPolicy Bypass -File installer\build.ps1` succeeded after the Obsidian vault-path update and produced a fresh installer at `dist\installer\Simple-Sticky-Notes-Setup.exe`.
- On `2026-04-27`, the live Obsidian config and app settings on this PC were verified to agree on the new Dropbox-root vault:
  ```powershell
  @'
  from simple_sticky_notes.obsidian_integration import current_obsidian_vault_path, recommended_storage_root
  from simple_sticky_notes.settings import load_settings
  print(f"vault={current_obsidian_vault_path()}")
  print(f"recommended={recommended_storage_root()}")
  print(f"settings={load_settings().storage_root}")
  '@ | python -
  ```
  Expected results:
  - `vault=C:\Users\Josh\Dropbox\joshs-stuff`
  - `recommended=C:\Users\Josh\Dropbox\joshs-stuff\Simple Sticky Notes`
  - `settings=C:\Users\Josh\Dropbox\joshs-stuff\Simple Sticky Notes`
- On `2026-04-24`, a direct runtime harness confirmed the tray controller still builds a live Win32 menu handle while using the custom tray icon class:
  ```powershell
  @'
  from simple_sticky_notes.app import StickyNotesApp

  app = StickyNotesApp()
  app.tray.start()
  app.root.update()
  print(f"menu_handle_exists={bool(getattr(app.tray.icon, '_menu_handle', None))}")
  print(f"tray_icon_class={app.tray.icon.__class__.__name__}")
  app.shutdown()
  '@ | python -
  ```
  Expected results:
  - `menu_handle_exists=True`
  - `tray_icon_class=StickyNotesTrayIcon`
- On `2026-04-23`, `powershell -NoProfile -ExecutionPolicy Bypass -File installer\build.ps1` succeeded from the normal repo workspace after Dropbox was quit, producing a fresh `1.0.3` installer at `dist\installer\Simple-Sticky-Notes-Setup.exe`.
- On `2026-04-23`, the locally installed app under `%LOCALAPPDATA%\Programs\Simple Sticky Notes` was inspected after the `assets\icons\simple-sticky-notes-64.png` crash, silently reinstalled from the freshly built `1.0.3` installer, and then re-verified by launching `New Simple Sticky Note.lnk`. The installed `Simple Sticky Notes.exe --new-note` process stayed alive, confirming the packaged resource-path fix works in practice on this PC.
- On `2026-04-23`, a staged `1.0.2` packaged EXE smoke check passed with `packaged_exe_alive_after_2s=True`.
- On `2026-04-23`, `installer\build.ps1` was blocked by a lock on the Dropbox `dist\` directory, so the same PyInstaller and Inno Setup steps were rerun successfully against clean staging paths to produce the `1.0.2` installer artifact. This was an environment workaround, not a code fix.
- On `2026-04-23`, `v1.0.2` was published to GitHub and mirrored to `https://app.whitkin.com/downloads/Simple-Sticky-Notes-Setup.exe`. No additional automated tests were run for that release-management step.
- On `2026-04-23`, local Dropbox ignore rules were added at the Dropbox root to stop future build-output folders for this repo from syncing. No automated tests were run for that machine-specific sync configuration change.
- On `2026-04-23`, the local Dropbox ignore rules were refined so this repo keeps syncing source plus final binaries while excluding local scratch folders, and the desktop `.lnk` was re-launched successfully to confirm the shortcut itself now works. No automated tests were run for that machine-specific sync/shortcut verification step.
- On `2026-04-23`, the installed `%LOCALAPPDATA%\\Programs\\Simple Sticky Notes` payload was inspected after the desktop launch still failed and was found to be missing `base_library.zip` in `_internal`. Reinstalling `v1.0.2` restored the runtime files, and relaunching the desktop `.lnk` produced a live `Simple Sticky Notes.exe --new-note` process. No automated tests were run for that machine-specific install repair.
- On `2026-04-23`, Microsoft Store pricing guidance for switching the listing to a paid tier was documented from current Microsoft docs. No automated tests were run for that release-management guidance.
- On `2026-04-23`, the README wording for Microsoft Store availability was corrected to `coming soon` after the first MSIX packaging attempt failed locally. No automated tests were run for that docs-only change.
- On `2026-04-23`, the full Microsoft Store screenshot set was copied into `docs/screenshots/` and embedded in the README for GitHub display. No automated tests were run for that docs-and-assets change.
- On `2026-04-23`, the first Microsoft Store submission was created in Partner Center and entered review under ID `78b96f9d-3b84-447d-93c2-50fe1a3e52a6`. No automated tests were run for that release-management update.
- On `2026-04-23`, the installed desktop and startup shortcuts on this PC were manually inspected after a `failed to import encoding module` launch error. The diagnosis confirmed stale packaged shortcut arguments pointing at `_internal\main.py`, and the live `.lnk` files were recreated to launch the installed EXE directly. No automated tests were run for that machine-specific shortcut repair.
- On `2026-04-23`, `python -m unittest tests.test_storage tests.test_app -v` passed `18` targeted tests while diagnosing and fixing the Obsidian title/focus regression.
- Coverage now includes:
  - dropped `.url` internet shortcuts importing as markdown links in new sticky notes
  - dropped text files importing directly into new sticky notes
  - unsupported dropped files copying into `Attachments/` under the storage root and linking back from the created sticky note
  - startup creation of notes from dropped launch arguments without requiring a second app instance
  - frozen-mode packaged resource lookup through PyInstaller's runtime resource root
  - tray icon loading from the packaged `assets\icons\simple-sticky-notes-64.png` path
  - Win32 tray popup-menu handling on left click
  - CLI forwarding of `--new-note` to an already-running instance
  - remote-command handling that creates a new note without starting a second tray-backed app instance
  - migration from one Obsidian vault root to a new active Obsidian vault root
  - packaged shortcut icon selection using the repo `.ico` in source mode and the installed EXE in frozen mode
- On `2026-04-22`, the README comparison against Microsoft Sticky Notes was refreshed from current Microsoft Support documentation. No code changes or automated tests were needed for that docs-only update.
- On `2026-04-22`, Microsoft Store submission docs were added for the current `EXE/MSI` Partner Center flow. No automated tests were run for that docs-only planning work.
- On `2026-04-22`, the Store submission docs were corrected after live Partner Center validation showed GitHub release asset URLs are rejected for redirecting and the `EXE/MSI` path requires CA-trusted signing. No automated tests were run for that docs-only correction.
- Coverage now includes:
  - editor display-buffer handling so append-style blank-line focus does not leak unwanted trailing newlines into saved note files
  - stable title-based markdown filenames with uniqueness suffixes
  - note titles derived from the first `10` words of the note
  - active-vault detection and default storage migration into an Obsidian vault
  - vault-relative Obsidian URI generation for `Edit in Obsidian`
  - flattened storage layout with markdown files directly under `Simple Sticky Notes`
  - startup migration from legacy `notes\` and visible `meta\` folders into the current hidden sidecar layout
  - deleted markdown pruning from note menus
  - closing an open sticky when its backing markdown file is deleted
  - external Obsidian edits reloading sticky-note content without renaming the markdown file out from under Obsidian
  - releasing the Tk popup grab on repeated context-menu use
  - tray-only startup without forcing a new blank note
  - runtime-state markers for unclean-launch and clean-shutdown tracking
  - Windows shortcut launch-spec generation for both source checkouts and packaged installer builds

- Verified desktop integration:
  - `python main.py --install-windows-integration` creates:
    - `%USERPROFILE%\Desktop\New Simple Sticky Note.lnk`
    - `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\Simple Sticky Notes.lnk`
  - after the workspace move, inspecting the existing `.lnk` files confirmed they still targeted the previous folder
  - rerunning `python main.py --install-windows-integration` from the moved workspace rewrote both shortcut targets to the current workspace

- Verified runtime diagnostics:
  - timed tray-backed smoke run without forcing a new note exits cleanly:
    ```powershell
    @'
    from simple_sticky_notes.app import StickyNotesApp
    app = StickyNotesApp()
    app.root.after(1200, app.shutdown)
    result = app.run(create_new_note=False)
    print(f"tray_gui_smoke={result}")
    '@ | python -
    ```
    Expected result:
    - `tray_gui_smoke=0`

  - timed tray-backed smoke run with a new note exits cleanly:
    ```powershell
    @'
    from simple_sticky_notes.app import StickyNotesApp
    app = StickyNotesApp()
    app.root.after(1200, app.shutdown)
    result = app.run(create_new_note=True)
    print(f"new_note_tray_smoke={result}")
    '@ | python -
    ```
    Expected result:
    - `new_note_tray_smoke=0`

  - packaged app smoke check confirms the built executable stays alive long enough to launch successfully before forced shutdown for the test harness:
    ```powershell
    $exe = Join-Path (Get-Location) 'dist\Simple Sticky Notes\Simple Sticky Notes.exe'
    $proc = Start-Process -FilePath $exe -PassThru
    Start-Sleep -Seconds 2
    $alive = -not $proc.HasExited
    Write-Output "packaged_exe_alive_after_2s=$alive"
    if ($alive) {
      Stop-Process -Id $proc.Id -Force
      $proc.WaitForExit()
    }
    ```
    Expected result:
    - `packaged_exe_alive_after_2s=True`

  - title-based filename diagnostic still produces a stable markdown filename from the note title chosen at creation time:
    ```powershell
    @'
    from simple_sticky_notes.app import StickyNotesApp
    from simple_sticky_notes.storage import note_title

    app = StickyNotesApp()
    body = 'This note filename should follow the body content even if it keeps going'
    app.create_and_open_note(body=body)
    window = next(iter(app.windows.values()))
    window.flush_note()
    print(f"note_title={note_title(body)}")
    print(f"note_file={app.storage.note_path(window.note.metadata.note_id).name}")
    app.shutdown()
    '@ | python -
    ```
    Expected result:
    - `note_title=This note filename should follow the body content even if`
    - `note_file=This note filename should follow the body content even if.md`

  - 2-way sync diagnostic still reloads an external markdown edit without renaming the markdown file out from under Obsidian:
    ```powershell
    @'
    import time
    from simple_sticky_notes.app import StickyNotesApp, persisted_body_from_editor

    app = StickyNotesApp()
    app.create_and_open_note(body='Original body')
    window = next(iter(app.windows.values()))
    window.flush_note()
    note_path_before = app.storage.note_path(window.note.metadata.note_id)
    note_path_before.write_text('Updated from Obsidian with enough words to change the title', encoding='utf-8')
    time.sleep(0.02)
    window._refresh_from_disk_if_needed()
    app.root.update_idletasks()
    print(f"reloaded_body={persisted_body_from_editor(window.text.get('1.0', 'end-1c'))}")
    print(f"same_file={(app.storage.note_path(window.note.metadata.note_id) == note_path_before)}")
    print(f"note_title={window.note.metadata.title}")
    app.shutdown()
    '@ | python -
    ```
    Expected results:
    - `reloaded_body=Updated from Obsidian with enough words to change the title`
    - `same_file=True`
    - `note_title=Updated from Obsidian with enough words to change the title`

- Verified packaging:
  - `powershell -NoProfile -ExecutionPolicy Bypass -File installer\build.ps1` succeeds from the moved workspace
  - resulting artifacts are created at:
    - `dist\Simple Sticky Notes\`
    - `dist\installer\Simple-Sticky-Notes-Setup.exe`
  - GitHub publish preparation is verified:
    - `main` is pushed to `origin`
    - GitHub CLI authentication is working for the `joshwhitk` account

- Verified move-readiness:
  - audited the repo for hardcoded workspace-path references outside generated caches and build artifacts and found none in active source or docs
  - confirmed project-path-sensitive runtime behavior is isolated to generated Windows shortcuts, which can be repaired by rerunning:
    ```powershell
    python main.py --install-windows-integration
    ```
