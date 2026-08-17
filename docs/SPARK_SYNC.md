# Spark sync — sticky notes ↔ the Idea Jar

*Written 2026-08-14. Rewritten 2026-08-17, when the Joplin migration landed and made half
of it wrong.*

## What a spark sticky is

One spark = **one** sticky note. The note's body is the spark text; each of the jar card's
notes is folded in below a `---` rule with its date — never as separate stickies. Linkage
rides in an HTML comment at the end of the body:

```
<!-- spark:6 card:idea-jar -->
```

It survives every round-trip through both sticky apps, renders invisibly, and required
**no changes to this app's code**. It also survived the migration out of Obsidian intact,
which is the reason spark↔note linkage still works.

## Where things live

- **Sparks are canonical in Neon** (`sparks` table) — the Idea Factory and both jars read
  and write it, and jar-api gives it a network face on the tailnet.
- **Sticky notes live in Joplin**, in the notebook **"Simple Sticky Notes"**, reached
  through Joplin's Data API on the cloud VM (`http://100.121.209.20:41185`, tailnet-only).
  Window geometry stays in local per-device sidecars, because where a note sits on *this*
  screen is not a fact about the note.

> **This document used to argue the opposite.** Until 2026-08-17 it recommended keeping
> sticky notes as Obsidian vault markdown and explicitly declined Joplin, on the grounds
> that the byte-compatible markdown contract over Syncthing *was* the sync layer. That was
> a reasonable call for a vault-based world and it is simply obsolete now: the vault at
> `C:/Users/Josh/Dropbox/joshs-stuff/` is a frozen read-only archive, and Joplin Server —
> which the markdown contract was standing in for — does the syncing.

## The bridge

Lives in the desktop jar's main process (`idea-jar/desktop-jar/lib/sticky.js`), and talks
to the same Joplin Data API this app does.

- **Jar → sticky**: the card's footer has "push to stickynote". Creates or updates the one
  note for that spark, in the "Simple Sticky Notes" notebook, then closes the card and asks
  this app's `service_api` to raise the note's window.
- **Sticky → jar**: every 5 minutes the jar scans notes in that notebook carrying the
  marker. If the text above the first `---` rule differs from Neon — compared with
  whitespace flattened, because Neon stores a spark on one line and a note keeps the
  wrapping he typed — Neon is updated and the jar card's spark line is rewritten.

The bridge never holds its own copy of the API token: it reads this app's `settings.json`,
so there is exactly one place on the machine where that token lives.

## Not built yet

- "Push to stickynote" from the **phone** jar app raises a flag on the card that the
  desktop bridge drains; the phone never talks to Joplin itself.
- Tagging an **existing** note as a spark from inside this app.
