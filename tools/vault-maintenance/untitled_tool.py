"""Helper for retitling 'Untitled' notes in the Obsidian vault.

Subcommands:
  dedupe <manifest...>            trash exact-duplicate notes, keep one per group
  read   <manifest> <start> <n>  print a batch of notes (base64 stripped/truncated)
  apply  <mapping.json>          rename/delete per mapping, preserving timestamps

Mapping JSON format:
  {
    "renames": [["<abs old path>", "<new title>"], ...],
    "deletes": ["<abs old path>", ...]   # blank notes -> moved to vault .trash
  }

Renames are filesystem renames only (content untouched) and the original
access/modify timestamps are restored afterwards, so note dates are preserved.
Deletes/duplicates are moved to the vault's .trash folder (recoverable).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sys
from pathlib import Path

VAULT = Path(r"C:\Users\Josh\Dropbox\joshs-stuff")
TRASH = VAULT / ".trash"
LOG = Path(__file__).resolve().parent / "untitled_rename_log.jsonl"
MAX_STEM = 100
_DATA_URI_RE = re.compile(r"data:[^)\s]+")
_EMPTY_IMG_RE = re.compile(r"!\[\]\(\[img\]\)")
_BLANKS_RE = re.compile(r"\n{3,}")


def _log(record: dict) -> None:
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def _normalize(content: str) -> str:
    return content.replace("\r\n", "\n").replace("\r", "\n").strip("\n")


def sanitize(title: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', " ", title)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .")
    if not cleaned:
        cleaned = "Note"
    return cleaned[:MAX_STEM].rstrip(" .") or "Note"


def unique_target(directory: Path, stem: str, old: Path) -> Path:
    candidate = directory / f"{stem}.md"
    if not candidate.exists() or candidate == old:
        return candidate
    n = 1
    while True:
        candidate = directory / f"{stem} {n}.md"
        if not candidate.exists() or candidate == old:
            return candidate
        n += 1


def _move_to_trash(old: Path) -> Path:
    TRASH.mkdir(parents=True, exist_ok=True)
    dest = TRASH / old.name
    n = 1
    while dest.exists():
        dest = TRASH / f"{old.stem} {n}{old.suffix}"
        n += 1
    shutil.move(str(old), str(dest))
    return dest


def _read_manifest(path: Path) -> list[str]:
    return [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]


def cmd_dedupe(manifests: list[Path]) -> None:
    # Process manifests in the order given so the first-listed copy is kept
    # (root manifest before imported -> the active-vault copy survives).
    order: list[str] = []
    for m in manifests:
        order.extend(_read_manifest(m))

    seen: dict[str, str] = {}
    trashed: set[str] = set()
    groups = 0
    for p in order:
        path = Path(p)
        if not path.exists():
            continue
        try:
            digest = hashlib.sha1(_normalize(path.read_text(encoding="utf-8", errors="replace")).encode("utf-8")).hexdigest()
        except Exception as exc:  # noqa: BLE001
            print(f"SKIP (read error {exc}): {p}")
            continue
        if digest in seen:
            dest = _move_to_trash(path)
            _log({"action": "dedupe-trash", "old": str(path), "new": str(dest), "duplicate_of": seen[digest]})
            trashed.add(p)
            print(f"  [dup] {path.name}  ==  {Path(seen[digest]).name}")
        else:
            seen[digest] = p

    # Rewrite each manifest to drop trashed files.
    for m in manifests:
        kept = [ln for ln in _read_manifest(m) if ln not in trashed and Path(ln).exists()]
        m.write_text("\n".join(kept) + ("\n" if kept else ""), encoding="utf-8")

    print(f"<<<DEDUPE unique={len(seen)} trashed={len(trashed)}>>>")


def _body_key(content: str) -> str:
    """Normalized body (frontmatter stripped, inline data-URIs removed,
    whitespace collapsed) used to detect notes that are the same note."""
    norm = content.replace("\r\n", "\n").replace("\r", "\n")
    lines = norm.split("\n")
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                norm = "\n".join(lines[i + 1:])
                break
    norm = _DATA_URI_RE.sub("", norm)
    return re.sub(r"\s+", " ", norm).strip()


def _created(content: str):
    """Parse the earliest creation timestamp from frontmatter, or None."""
    import datetime as _dt

    for raw in content.replace("\r\n", "\n").split("\n")[:20]:
        m = re.match(r"\s*(created(?:_time)?|date)\s*:\s*(.+?)\s*$", raw, re.IGNORECASE)
        if not m:
            continue
        val = m.group(2).strip().strip("\"'")
        for fmt in ("%Y%m%dT%H%M%SZ", "%Y%m%dT%H%M%S"):
            try:
                return _dt.datetime.strptime(val, fmt)
            except ValueError:
                pass
        try:
            parsed = _dt.datetime.fromisoformat(val.replace("Z", "+00:00").replace(".000", ""))
            return parsed.replace(tzinfo=None)  # normalize to naive UTC for comparison
        except ValueError:
            continue
    return None


def cmd_clean(manifests: list[Path]) -> None:
    import datetime as _dt

    order: list[str] = []
    for m in manifests:
        order.extend(_read_manifest(m))

    contents: dict[str, str] = {}
    for p in order:
        path = Path(p)
        if path.exists():
            contents[p] = path.read_text(encoding="utf-8", errors="replace")

    trashed: set[str] = set()

    # 1) Trash blank notes (empty body).
    blanks = 0
    for p, c in contents.items():
        if _body_key(c) == "":
            dest = _move_to_trash(Path(p))
            _log({"action": "blank-trash", "old": p, "new": str(dest)})
            trashed.add(p)
            blanks += 1

    # 2) Group remaining by body; keep the earliest-created copy.
    groups: dict[str, list[str]] = {}
    for p, c in contents.items():
        if p in trashed:
            continue
        groups.setdefault(_body_key(c), []).append(p)

    dups = 0
    far_future = _dt.datetime.max
    for key, members in groups.items():
        if len(members) < 2:
            continue
        # earliest created first; unparseable dates sort last; manifest order breaks ties
        ranked = sorted(
            enumerate(members),
            key=lambda im: (_created(contents[im[1]]) or far_future, im[0]),
        )
        keep = ranked[0][1]
        for _, p in ranked[1:]:
            dest = _move_to_trash(Path(p))
            _log({"action": "dedupe-trash", "old": p, "new": str(dest), "duplicate_of": keep})
            trashed.add(p)
            dups += 1
        print(f"  keep {Path(keep).name}  (trashed {len(members) - 1} dup)")

    for m in manifests:
        kept = [ln for ln in _read_manifest(m) if ln not in trashed and Path(ln).exists()]
        m.write_text("\n".join(kept) + ("\n" if kept else ""), encoding="utf-8")

    survivors = len(contents) - len(trashed)
    print(f"<<<CLEAN blanks={blanks} dups={dups} survivors={survivors}>>>")


_IMG_WIKILINK_RE = re.compile(r"!\[\[([^]|#]+)")
_IMG_HTML_RE = re.compile(r'<img[^>]*src=["\']([^"\']+)["\']')


def _fuzzy_text(content: str) -> str:
    body = _body_key_raw_strip_fm(content).lower()
    body = _IMG_WIKILINK_RE.sub("", body)
    body = re.sub(r"<img[^>]*>", "", body)
    body = _DATA_URI_RE.sub("", body)
    body = re.sub(r"_resources/\S+", "", body)
    body = re.sub(r"[^a-z0-9]+", " ", body)
    return re.sub(r"\s+", " ", body).strip()


def _body_key_raw_strip_fm(content: str) -> str:
    norm = content.replace("\r\n", "\n").replace("\r", "\n")
    lines = norm.split("\n")
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                return "\n".join(lines[i + 1:])
    return norm


def _image_ids(content: str) -> frozenset:
    names = _IMG_WIKILINK_RE.findall(content) + _IMG_HTML_RE.findall(content)
    ids = set()
    for n in names:
        stem = Path(n.strip()).name.rsplit(".", 1)[0].lower()
        stem = re.sub(r"^[0-9a-f]{8}-", "", stem)  # drop Obsidian hash prefix
        digits = re.sub(r"\D", "", stem)
        if len(digits) >= 8:  # an image timestamp, not a stray number
            ids.add(digits)
    return frozenset(ids)


def cmd_dedupe_against_root(manifest: Path) -> None:
    root_texts: set[str] = set()
    root_imgsets: list[frozenset] = []
    for p in VAULT.glob("*.md"):
        c = p.read_text(encoding="utf-8", errors="replace")
        t = _fuzzy_text(c)
        if t:
            root_texts.add(t)
        ids = _image_ids(c)
        if ids:
            root_imgsets.append(ids)

    kept: list[str] = []
    trashed = 0
    for line in _read_manifest(manifest):
        path = Path(line)
        if not path.exists():
            continue
        c = path.read_text(encoding="utf-8", errors="replace")
        t = _fuzzy_text(c)
        ids = _image_ids(c)
        is_dup = False
        reason = ""
        if t and t in root_texts:
            is_dup, reason = True, "text"
        elif not t and ids and any(ids <= r for r in root_imgsets):
            is_dup, reason = True, "image"
        if is_dup:
            dest = _move_to_trash(path)
            _log({"action": "dedupe-root-trash", "old": str(path), "new": str(dest), "match": reason})
            trashed += 1
        else:
            kept.append(line)

    manifest.write_text("\n".join(kept) + ("\n" if kept else ""), encoding="utf-8")
    print(f"<<<DEDUPE-ROOT trashed={trashed} kept={len(kept)}>>>")
    for k in kept:
        print(f"  KEEP {Path(k).name}")


def cmd_read(manifest: Path, start: int, count: int) -> None:
    paths = _read_manifest(manifest)
    batch = paths[start : start + count]
    for i, p in enumerate(batch, start=start):
        path = Path(p)
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except Exception as exc:  # noqa: BLE001
            content = f"<<read error: {exc}>>"
        content = _DATA_URI_RE.sub("[img]", content)
        content = _EMPTY_IMG_RE.sub("[img]", content)
        content = _BLANKS_RE.sub("\n\n", content).strip()
        if len(content) > 1400:
            content = content[:1400] + "\n…[truncated]"
        print(f"<<<NOTE {i}>>> {p}")
        print(content)
        print("<<<END>>>")
    print(f"<<<BATCH start={start} shown={len(batch)} total={len(paths)}>>>")


def cmd_apply(mapping_path: Path) -> None:
    data = json.loads(mapping_path.read_text(encoding="utf-8"))
    renames = data.get("renames", [])
    deletes = data.get("deletes", [])

    renamed = 0
    for old_str, title in renames:
        old = Path(old_str)
        if not old.exists():
            print(f"SKIP (missing): {old}")
            continue
        stem = sanitize(title)
        target = unique_target(old.parent, stem, old)
        if target == old:
            print(f"KEEP (same): {old.name}")
            continue
        st = old.stat()
        old.rename(target)
        os.utime(target, (st.st_atime, st.st_mtime))  # preserve original dates
        _log({"action": "rename", "old": str(old), "new": str(target)})
        renamed += 1
        print(f"  {old.name}  ->  {target.name}")

    deleted = 0
    for old_str in deletes:
        old = Path(old_str)
        if not old.exists():
            continue
        dest = _move_to_trash(old)
        _log({"action": "trash", "old": str(old), "new": str(dest)})
        deleted += 1
        print(f"  [trash] {old.name}")

    print(f"<<<APPLIED renamed={renamed} trashed={deleted}>>>")


def main() -> None:
    cmd = sys.argv[1]
    if cmd == "dedupe":
        cmd_dedupe([Path(p) for p in sys.argv[2:]])
    elif cmd == "clean":
        cmd_clean([Path(p) for p in sys.argv[2:]])
    elif cmd == "dedupe-against-root":
        cmd_dedupe_against_root(Path(sys.argv[2]))
    elif cmd == "read":
        cmd_read(Path(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]))
    elif cmd == "apply":
        cmd_apply(Path(sys.argv[2]))
    else:
        raise SystemExit(f"unknown command: {cmd}")


if __name__ == "__main__":
    main()
