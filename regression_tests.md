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
