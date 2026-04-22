# Regression Tests

## Planned
- Add regression coverage only if this work uncovers a repeated defect or a bug that needs a durable test.

## Run Before Shipping
- No project-specific regression suite identified yet.

## Results
- No local regression suite was applicable for this install/setup task.
- Verification performed:
  - `winget list Obsidian.Obsidian` confirmed Obsidian `1.12.7` is installed.
  - Verified executable exists at `C:\Users\Josh\AppData\Local\Programs\Obsidian\Obsidian.exe`.
  - Built `obsidian-sticky-notes-plugin` from source with `npm install` and `npm run build`.
  - Verified plugin artifacts copied into the test vault and that launching Obsidian against the vault generated normal vault state files including `.obsidian\workspace.json`.
  - Current app tests run with `python -m unittest discover -s tests -p "test_*.py" -v`.
  - Verified `python -m unittest -v` now discovers and runs the same tests from the repo root.
  - Verified `python main.py --install-windows-integration` created:
    - `C:\Users\Josh\Desktop\New Simple Sticky Note.lnk`
    - `C:\Users\Josh\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\Simple Sticky Notes.lnk`
  - Verified launching `python main.py --new-note` creates `.md` and `.json` note files under `C:\Users\Josh\Dropbox\backups\josh-obsidian\simple-sticky-notes\`.
