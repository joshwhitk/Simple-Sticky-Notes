from __future__ import annotations

import json
from pathlib import Path


OBSIDIAN_CONFIG_PATH = Path.home() / "AppData" / "Roaming" / "Obsidian" / "obsidian.json"
VAULT_STORAGE_FOLDER = "Simple Sticky Notes"


def current_obsidian_vault_path() -> Path | None:
    if not OBSIDIAN_CONFIG_PATH.exists():
        return None

    data = json.loads(OBSIDIAN_CONFIG_PATH.read_text(encoding="utf-8"))
    vaults = data.get("vaults", {})
    open_vaults = [vault for vault in vaults.values() if vault.get("open")]
    if open_vaults:
        return Path(open_vaults[0]["path"])
    if vaults:
        newest = max(vaults.values(), key=lambda vault: vault.get("ts", 0))
        path = newest.get("path")
        if path:
            return Path(path)
    return None


def recommended_storage_root() -> Path:
    vault_path = current_obsidian_vault_path()
    if vault_path:
        return vault_path / VAULT_STORAGE_FOLDER
    return Path.home() / "Documents" / VAULT_STORAGE_FOLDER
