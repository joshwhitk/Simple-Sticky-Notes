# Regression Tests

## Planned
- Add regression coverage only if this work uncovers a repeated defect or a bug that needs a durable test.

## Run Before Shipping
- No project-specific regression suite identified yet.

## Results
- No local regression suite was applicable for this install/setup task.
- Verification performed:
  - `winget list Obsidian.Obsidian` confirmed Obsidian `1.12.7` is installed.
  - Verified the Obsidian executable exists under the standard per-user install location.
  - Built `obsidian-sticky-notes-plugin` from source with `npm install` and `npm run build`.
  - Verified plugin artifacts copied into the test vault and that launching Obsidian against the vault generated normal vault state files including `.obsidian\workspace.json`.
  - Current app tests run with `python -m unittest discover -s tests -p "test_*.py" -v`.
  - Verified `python -m unittest -v` now discovers and runs the same tests from the repo root.
  - Verified `python main.py --install-windows-integration` created:
    - `%USERPROFILE%\Desktop\New Simple Sticky Note.lnk`
    - `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\Simple Sticky Notes.lnk`
  - Verified launching `python main.py --new-note` creates `.md` and `.json` note files under the configured storage root.
  - Verified `python -m unittest -v` still passes after the frameless note UI changes.
  - Added regression coverage for the editor buffer helpers so the UI can keep a blank append line without persisting an unwanted extra newline into saved note files.
  - Added coverage for richer note creation metadata, note-menu state labels, and sticky-themed selection-color derivation.
  - Added coverage for content-based markdown filenames, `-1` collision suffixes, and legacy-storage migration into the new default Documents location.
  - Verified the append-focus diagnostic lands the caret on the blank line and the text body reserves space for the close button:
    ```powershell
    @'
    from simple_sticky_notes.app import StickyNotesApp, TEXT_RIGHT_MARGIN
    app = StickyNotesApp()
    app.new_note()
    window = next(iter(app.windows.values()))
    window.text.delete('1.0', 'end')
    window.text.insert('1.0', 'wow this looks good!\n')
    app.root.update_idletasks()
    window._focus_editor_for_append()
    app.root.update_idletasks()
    print(f"insert_index={window.text.index('insert')}")
    print(f"body_width={window.body.winfo_width()}")
    print(f"window_width={window.window.winfo_width()}")
    print(f"expected_margin={TEXT_RIGHT_MARGIN}")
    window.hide_note()
    '@ | python -
    ```
    Expected result:
    - `insert_index=2.0`
  - Verified a GUI diagnostic for the new context-menu slice:
    ```powershell
    @'
    from simple_sticky_notes.app import StickyNotesApp
    app = StickyNotesApp()
    app.new_note()
    window = next(iter(app.windows.values()))
    window.text.delete('1.0', 'end')
    window.text.insert('1.0', 'first line\nsecond line\n')
    window.text.tag_add('sel', '1.0', '1.10')
    menu = window._build_context_menu()
    window.set_color('#bbdefb')
    window.split_selection_to_new_sticky()
    app.root.update_idletasks()
    print(f"menu_entries={menu.index('end')}")
    print(f"open_windows={len(app.windows)}")
    print(f"first_note_color={window.note.metadata.bg_color}")
    print(f"saved_color={app.storage.load_note(window.note.metadata.note_id).metadata.bg_color}")
    for open_window in list(app.windows.values()):
        open_window.hide_note()
    '@ | python -
    ```
    Expected results:
    - `open_windows=2`
    - `first_note_color=#bbdefb`
    - `saved_color=#bbdefb`
  - Verified `Edit in Notepad` launches a real note file successfully.
  - Verified a runtime filename diagnostic creates a content-based markdown filename:
    ```powershell
    @'
    from simple_sticky_notes.app import StickyNotesApp
    app = StickyNotesApp()
    app.create_and_open_note(body='This note filename should follow the body content')
    window = next(iter(app.windows.values()))
    window.flush_note()
    print(f"note_file={app.storage.note_path(window.note.metadata.note_id).name}")
    for open_window in list(app.windows.values()):
        open_window.hide_note()
    '@ | python -
    ```
    Expected result:
    - `note_file=This note filename should follow the body content.md`
  - Verified a timed GUI smoke launch completes without Tk errors:
    ```powershell
    @'
    from simple_sticky_notes.app import StickyNotesApp
    app = StickyNotesApp()
    app.root.after(900, app.shutdown)
    result = app.run(create_new_note=True)
    print(f"gui_smoke={result}")
    '@ | python -
    ```
