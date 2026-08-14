# Spark sync — sticky notes ↔ the Idea Jar

*2026-08-14. The decision and the contract, so the next session doesn't re-derive it.*

## What a spark sticky is

One spark = **one** sticky note. The note's body is the spark text; each of the jar
card's notes is folded in below a `---` rule with its date — never as separate stickies.
Linkage rides in an HTML comment at the end of the body:

```
<!-- spark:6 card:idea-jar -->
```

It survives every round-trip through both sticky apps, renders invisibly in Obsidian and
on the sticky window, and required **zero changes to this app's code**.

## Where things live (the decision Josh delegated)

- **Sparks are canonical in Neon** (`sparks` table) — the Idea Factory and both jars
  already read and write it, and jar-api gives it a network face on the tailnet.
- **Sticky notes stay as vault markdown + sidecars.** They do NOT migrate into Joplin's
  database. Reasoning: this app's entire cross-device story is the byte-compatible
  markdown contract (`storage.py` ↔ `Frontmatter.kt`, mirrored test suites) over the
  Syncthing-synced vault. Joplin's sqlite is single-app, unreachable from the Android
  sticky app's sandbox, and adopting it would orphan both existing implementations to
  gain nothing the vault doesn't already provide. If Joplin visibility is ever wanted,
  point Joplin at the vault as an external editor the way Obsidian is one today.

## The bridge

Lives in the desktop jar's main process (`idea-jar/desktop-jar/lib/sticky.js`) — on the
machine where the vault lives, which is also the Syncthing hub the phone already syncs
against.

- **Jar → sticky**: the card's work drawer has "push to stickynote". Creates or updates
  the one note for that spark. New notes are written the way the Android app writes them
  from outside the desktop app: frontmatter with `title` + `stickynote` tag, plus a
  `.simple-sticky-notes/meta/<id>.json` sidecar (`is_open: false` — it lists, it does
  not pop a window). Updates replace the **body only**; existing frontmatter is carried
  verbatim, exactly like this app's own save.
- **Sticky → jar**: every 5 minutes the jar scans vault notes carrying the marker. If the
  text above the first `---` rule differs from Neon, Neon is updated and the jar card's
  spark line is rewritten — an edit made on the phone's sticky widget shows up on the
  desktop jar's card.

## Not built yet

- "Push to stickynote" from the **phone** jar app (needs a jar-api endpoint plus a
  pending flag the desktop bridge drains — one nullable column away).
- Tagging an **existing** sticky as a spark from inside this app (planned shape: user
  adds a `spark` tag; the bridge sees tag-without-marker, creates the Neon row, appends
  the marker).
- The VM as a Syncthing peer (its `~/Sync` is empty today) — would let spark stickies
  flow even with the PC off, and is the natural next resilience step.
