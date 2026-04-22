# Regression Tests

## Planned

- Add durable regression coverage when a bug repeats or a manual finding reveals a realistic failure mode that should stay fixed.

## Run Before Shipping

- `python -m unittest -v`
- `powershell -NoProfile -ExecutionPolicy Bypass -File installer\build.ps1`

## Results

- On `2026-04-22`, `python -m unittest -v` passed `24` tests from the moved workspace root.
- Coverage now includes:
  - editor display-buffer handling so append-style blank-line focus does not leak unwanted trailing newlines into saved note files
  - content-based markdown filenames and uniqueness suffixes
  - active-vault detection and default storage migration into an Obsidian vault
  - vault-relative Obsidian URI generation for `Edit in Obsidian`
  - flattened storage layout with markdown files directly under `Simple Sticky Notes`
  - startup migration from legacy `notes\` and visible `meta\` folders into the current hidden sidecar layout
  - deleted markdown pruning from note menus
  - closing an open sticky when its backing markdown file is deleted
  - releasing the Tk popup grab on repeated context-menu use
  - tray-only startup without forcing a new blank note
  - runtime-state markers for unclean-launch and clean-shutdown tracking

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

  - content-based filename diagnostic still produces a long markdown filename from note content:
    ```powershell
    @'
    from simple_sticky_notes.app import StickyNotesApp
    app = StickyNotesApp()
    app.create_and_open_note(body='This note filename should follow the body content')
    window = next(iter(app.windows.values()))
    window.flush_note()
    print(f"note_file={app.storage.note_path(window.note.metadata.note_id).name}")
    app.shutdown()
    '@ | python -
    ```
    Expected result:
    - `note_file=This note filename should follow the body content.md`

  - 2-way sync diagnostic still reloads an external markdown edit and updates the note filename accordingly:
    ```powershell
    @'
    import time
    from simple_sticky_notes.app import StickyNotesApp, persisted_body_from_editor

    app = StickyNotesApp()
    app.create_and_open_note(body='Original body')
    window = next(iter(app.windows.values()))
    window.flush_note()
    note_path_before = app.storage.note_path(window.note.metadata.note_id)
    note_path_before.write_text('Updated from Obsidian', encoding='utf-8')
    time.sleep(0.02)
    window._refresh_from_disk_if_needed()
    app.root.update_idletasks()
    print(f"reloaded_body={persisted_body_from_editor(window.text.get('1.0', 'end-1c'))}")
    print(f"renamed_file={app.storage.note_path(window.note.metadata.note_id).name}")
    app.shutdown()
    '@ | python -
    ```
    Expected results:
    - `reloaded_body=Updated from Obsidian`
    - `renamed_file=Updated from Obsidian.md`

- Verified packaging:
  - `powershell -NoProfile -ExecutionPolicy Bypass -File installer\build.ps1` succeeds from the moved workspace
  - resulting artifacts are created at:
    - `dist\Simple Sticky Notes\`
    - `dist\installer\Simple-Sticky-Notes-Setup.exe`

- Verified move-readiness:
  - audited the repo for hardcoded workspace-path references outside generated caches and build artifacts and found none in active source or docs
  - confirmed project-path-sensitive runtime behavior is isolated to generated Windows shortcuts, which can be repaired by rerunning:
    ```powershell
    python main.py --install-windows-integration
    ```
