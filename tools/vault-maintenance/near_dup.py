"""Find notes that are 'mostly' contained in another (larger) note.

containment(B in A) = |shingles(B) & shingles(A)| / |shingles(B)|
B is a probable-duplicate of A when containment is high, A has strictly more
content, and B is substantial enough that it shouldn't just be deleted.

Usage:
  near_dup.py analyze [threshold]      # report candidates, make no changes
  near_dup.py apply <plan.json>        # move movers -> 'probably duplicates', link original
"""
from __future__ import annotations

import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

VAULT = Path(r"C:\Users\Josh\Dropbox\joshs-stuff")
DUP_DIR = VAULT / "probably duplicates"
LOG = Path(__file__).resolve().parent / "near_dup_log.jsonl"
EXCLUDE = {".trash", ".obsidian", ".stfolder", ".simple-sticky-notes", "_resources", "probably duplicates"}
K = 4            # shingle size (words)
MIN_WORDS = 25   # a 'mover' must be at least this many words (substantial)
BOILERPLATE = 60 # ignore shingles shared by more than this many notes


def iter_md():
    for p in VAULT.rglob("*.md"):
        rel_parts = {x.lower() for x in p.relative_to(VAULT).parts[:-1]}
        if rel_parts & {d.lower() for d in EXCLUDE}:
            continue
        yield p


def strip_fm(c: str) -> str:
    c = c.replace("\r\n", "\n").replace("\r", "\n")
    lines = c.split("\n")
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                return "\n".join(lines[i + 1:])
    return c


def words_of(c: str) -> list[str]:
    b = strip_fm(c).lower()
    b = re.sub(r"!\[\[[^]]*\]\]", " ", b)
    b = re.sub(r"<img[^>]*>", " ", b)
    b = re.sub(r"data:[^)\s]+", " ", b)
    b = re.sub(r"http\S+", " ", b)
    return re.findall(r"[a-z0-9]+", b)


def shingles(words: list[str]) -> frozenset:
    if len(words) < K:
        return frozenset([" ".join(words)]) if words else frozenset()
    return frozenset(" ".join(words[i:i + K]) for i in range(len(words) - K + 1))


def build():
    notes = []
    for p in iter_md():
        try:
            c = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        w = words_of(c)
        notes.append({"path": p, "words": len(w), "sh": shingles(w)})
    return notes


def analyze(threshold: float):
    notes = build()
    index = defaultdict(list)
    for i, n in enumerate(notes):
        for s in n["sh"]:
            index[s].append(i)
    # drop boilerplate shingles
    common = {s for s, lst in index.items() if len(lst) > BOILERPLATE}

    results = []
    for i, n in enumerate(notes):
        if n["words"] < MIN_WORDS or not n["sh"]:
            continue
        shared = defaultdict(int)
        for s in n["sh"]:
            if s in common:
                continue
            for j in index[s]:
                if j != i:
                    shared[j] += 1
        best = None
        denom = len(n["sh"])
        for j, cnt in shared.items():
            other = notes[j]
            # original must have strictly more content
            if other["words"] <= n["words"]:
                continue
            cont = cnt / denom
            if cont >= threshold and (best is None or cont > best[1] or (cont == best[1] and other["words"] > notes[best[0]]["words"])):
                best = (j, cont)
        if best is not None:
            j, cont = best
            results.append({
                "mover": str(n["path"]),
                "mover_words": n["words"],
                "original": str(notes[j]["path"]),
                "original_words": notes[j]["words"],
                "containment": round(cont, 3),
            })
    # avoid moving a note that is itself someone's chosen original
    originals = {r["original"] for r in results}
    results = [r for r in results if r["mover"] not in originals]
    results.sort(key=lambda r: (-r["containment"], -r["mover_words"]))
    return results


def cmd_analyze():
    threshold = float(sys.argv[2]) if len(sys.argv) > 2 else 0.7
    results = analyze(threshold)
    print(f"<<<threshold={threshold} candidates={len(results)}>>>")
    for r in results:
        mv = Path(r["mover"]).name
        og = Path(r["original"]).name
        print(f"  {r['containment']:.2f}  [{r['mover_words']}w -> {r['original_words']}w]  {mv!r}  ⊂  {og!r}")
    # save plan for optional apply
    (Path(__file__).resolve().parent / "near_dup_plan.json").write_text(
        json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")


def _link_target(original_path: Path, stem_counts: dict) -> str:
    # Use a bare wikilink when the basename is unique in the vault; otherwise
    # use the vault-relative path (without extension) to disambiguate.
    if stem_counts.get(original_path.stem, 0) > 1:
        return original_path.relative_to(VAULT).with_suffix("").as_posix()
    return original_path.stem


def cmd_apply(plan_path: Path):
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    DUP_DIR.mkdir(parents=True, exist_ok=True)
    stem_counts: dict = defaultdict(int)
    for p in VAULT.rglob("*.md"):
        stem_counts[p.stem] += 1
    moved = 0
    for r in plan:
        src = Path(r["mover"])
        if not src.exists():
            continue
        original = Path(r["original"])
        st = src.stat()
        content = src.read_text(encoding="utf-8", errors="replace")
        banner = f"> [!warning] Probably a duplicate of [[{_link_target(original, stem_counts)}]] (~{int(r['containment']*100)}% contained)\n\n"
        # insert banner after frontmatter if present
        if content.startswith("---\n"):
            end = content.find("\n---\n", 4)
            if end != -1:
                head = content[: end + 5]
                rest = content[end + 5:]
                new = head + "\n" + banner + rest
            else:
                new = banner + content
        else:
            new = banner + content
        dest = DUP_DIR / src.name
        n = 1
        while dest.exists():
            dest = DUP_DIR / f"{src.stem} {n}{src.suffix}"
            n += 1
        dest.write_text(new, encoding="utf-8")
        os.utime(dest, (st.st_atime, st.st_mtime))  # preserve original date
        src.unlink()
        with LOG.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"moved": str(src), "to": str(dest), "original": str(original),
                                 "containment": r["containment"]}, ensure_ascii=False) + "\n")
        moved += 1
        print(f"  moved {src.name}  ->  probably duplicates/  (dup of {original.stem})")
    print(f"<<<APPLIED moved={moved}>>>")


def main():
    cmd = sys.argv[1]
    if cmd == "analyze":
        cmd_analyze()
    elif cmd == "apply":
        cmd_apply(Path(sys.argv[2]))
    else:
        raise SystemExit(f"unknown command: {cmd}")


if __name__ == "__main__":
    main()
