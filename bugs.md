# Bugs

## 2026-04-22

- External plugin repo bug: `Abdo-reda/obsidian-sticky-notes-plugin` README points to a `releases/latest/download/sticky-notes.zip` URL that currently returns `404 Not Found`. Workaround used: build from source and copy `main.js`, `manifest.json`, and `styles.css` into the vault plugin folder.
- Product fit bug / blocker: Obsidian pop-out windows are associated with the vault window. Per Obsidian's official help, if the vault window closes, all pop-out windows close as well. This means an Obsidian plugin cannot satisfy the requirement that sticky notes remain on the desktop after reboot when Obsidian itself is not running.
