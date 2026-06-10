from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

try:
    import yaml
except ImportError:  # PyYAML is a test-only convenience, not a runtime dependency
    yaml = None

from simple_sticky_notes.models import AppSettings
from simple_sticky_notes.app import (
    editor_body_for_display,
    join_image_runs,
    note_menu_label,
    persisted_body_from_editor,
    recent_notes,
    selection_bg_for,
    split_body_for_images,
    tile_position,
)
from simple_sticky_notes.app import edge_zone, resize_geometry
from simple_sticky_notes.models import NoteMetadata, NoteRecord
from simple_sticky_notes.storage import (
    StickyStorage,
    format_note_with_frontmatter,
    merge_frontmatter,
    note_title,
    split_frontmatter,
    strip_frontmatter,
    suggested_file_stem,
)


class StickyStorageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        settings = AppSettings(storage_root=self.tempdir.name)
        self.storage = StickyStorage(settings)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_save_clipboard_image_writes_png_and_returns_embed_name(self) -> None:
        try:
            from PIL import Image
        except Exception:
            self.skipTest("Pillow not installed")
        img = Image.new("RGB", (4, 4), (255, 213, 79))
        name = self.storage.save_clipboard_image(img, stamp="20260609120000")
        self.assertEqual(name, "Pasted image 20260609120000.png")
        saved = Path(self.tempdir.name) / "_attachments" / name
        self.assertTrue(saved.exists())
        # A second paste with the same stamp must not overwrite — it gets a -1 suffix.
        name2 = self.storage.save_clipboard_image(img, stamp="20260609120000")
        self.assertEqual(name2, "Pasted image 20260609120000-1.png")
        self.assertTrue((Path(self.tempdir.name) / "_attachments" / name2).exists())

    def test_import_image_file_copies_and_dedupes(self) -> None:
        src = Path(self.tempdir.name) / "shot.png"
        src.write_bytes(b"\x89PNG\r\n\x1a\n fake")
        first = self.storage.import_image_file(src)
        self.assertEqual(first, "shot.png")
        second = self.storage.import_image_file(src)
        self.assertEqual(second, "shot-1.png")
        attach = Path(self.tempdir.name) / "_attachments"
        self.assertTrue((attach / "shot.png").exists())
        self.assertTrue((attach / "shot-1.png").exists())

    def test_note_id_for_sticky_adopts_root_note_then_is_idempotent(self) -> None:
        md = Path(self.tempdir.name) / "Grocery list.md"
        md.write_text("Grocery list\n- milk\n", encoding="utf-8")
        note_id = self.storage.note_id_for_sticky(md)
        self.assertIsNotNone(note_id)
        # sidecar now exists and the file gained the stickynote tag
        self.assertTrue((Path(self.tempdir.name) / ".simple-sticky-notes" / "meta" / f"{note_id}.json").exists())
        self.assertIn("stickynote", md.read_text(encoding="utf-8"))
        # second call resolves to the SAME note (no duplicate sidecar)
        self.assertEqual(self.storage.note_id_for_sticky(md), note_id)
        self.assertEqual(self.storage.load_note(note_id).body.splitlines()[0], "Grocery list")

    def test_always_on_top_round_trips_in_sidecar(self) -> None:
        note = self.storage.create_note("Pinned note")
        self.assertFalse(note.metadata.always_on_top)  # default off
        note.metadata.always_on_top = True
        self.storage.save_metadata(note.metadata)
        reloaded = self.storage.load_note(note.metadata.note_id)
        self.assertTrue(reloaded.metadata.always_on_top)

    def test_phone_home_stems_reads_synced_file(self) -> None:
        import json as _json
        self.assertEqual(self.storage.phone_home_stems(), [])  # missing file
        self.storage.phone_home_path().parent.mkdir(parents=True, exist_ok=True)
        self.storage.phone_home_path().write_text(
            _json.dumps({"file_stems": ["Grocery list", "Ideas", "  "]}), encoding="utf-8"
        )
        self.assertEqual(self.storage.phone_home_stems(), ["Grocery list", "Ideas"])

    def test_note_id_for_sticky_rejects_non_markdown(self) -> None:
        self.assertIsNone(self.storage.note_id_for_sticky(Path(self.tempdir.name) / "pic.png"))

    def test_create_note_persists_markdown_and_metadata(self) -> None:
        note = self.storage.create_note("Test note")
        self.assertTrue((Path(self.tempdir.name) / f"{note.metadata.file_stem}.md").exists())
        self.assertTrue((Path(self.tempdir.name) / ".simple-sticky-notes" / "meta" / f"{note.metadata.note_id}.json").exists())
        self.assertEqual(note.metadata.title, "Test note")
        self.assertTrue(note.metadata.is_open)
        self.assertEqual(note.metadata.file_stem, "Test note")

    def test_create_note_accepts_body_position_and_color(self) -> None:
        note = self.storage.create_note(
            "Colored note",
            body="Body text",
            x=120,
            y=160,
            width=420,
            height=280,
            bg_color="#bbdefb",
        )
        reloaded = self.storage.load_note(note.metadata.note_id)
        self.assertEqual(reloaded.body, "Body text")
        self.assertEqual(reloaded.metadata.x, 120)
        self.assertEqual(reloaded.metadata.y, 160)
        self.assertEqual(reloaded.metadata.width, 420)
        self.assertEqual(reloaded.metadata.height, 280)
        self.assertEqual(reloaded.metadata.bg_color, "#bbdefb")
        self.assertEqual(reloaded.metadata.file_stem, "Colored note")

    def test_hide_note_keeps_note_but_marks_it_closed(self) -> None:
        note = self.storage.create_note("Closable")
        self.storage.hide_note(note.metadata.note_id)
        reloaded = self.storage.load_note(note.metadata.note_id)
        self.assertFalse(reloaded.metadata.is_open)
        self.assertTrue((Path(self.tempdir.name) / f"{reloaded.metadata.file_stem}.md").exists())

    def test_list_open_notes_filters_hidden_notes(self) -> None:
        note1 = self.storage.create_note("One")
        note2 = self.storage.create_note("Two")
        self.storage.hide_note(note1.metadata.note_id)
        open_ids = {note.metadata.note_id for note in self.storage.list_open_notes()}
        self.assertNotIn(note1.metadata.note_id, open_ids)
        self.assertIn(note2.metadata.note_id, open_ids)

    def test_editor_body_adds_blank_append_line_without_changing_saved_body(self) -> None:
        stored = "wow this looks good!"
        displayed = editor_body_for_display(stored)
        self.assertEqual(displayed, "wow this looks good!\n")
        self.assertEqual(persisted_body_from_editor(displayed), stored)

    def test_editor_body_preserves_one_intentional_trailing_blank_line(self) -> None:
        stored = "line one\n\n"
        displayed = editor_body_for_display(stored)
        self.assertEqual(persisted_body_from_editor(displayed), stored)

    def test_note_menu_label_reflects_visibility(self) -> None:
        note = self.storage.create_note("Menu title")
        self.assertEqual(note_menu_label(note), "[open] Menu title")
        self.storage.hide_note(note.metadata.note_id)
        hidden_note = self.storage.load_note(note.metadata.note_id)
        self.assertEqual(note_menu_label(hidden_note), "[hidden] Menu title")

    def test_selection_bg_for_darken_color(self) -> None:
        self.assertEqual(selection_bg_for("#ffd54f"), "#e0bb45")

    def test_title_based_filenames_use_incrementing_suffixes(self) -> None:
        first = self.storage.create_note(title="Same title", body="Body one")
        second = self.storage.create_note(title="Same title", body="Body two")
        self.assertEqual(first.metadata.file_stem, "Same title")
        self.assertEqual(second.metadata.file_stem, "Same title-1")

    def test_saving_note_keeps_existing_markdown_filename_stable(self) -> None:
        note = self.storage.create_note(title="Old title", body="Old title")
        old_path = Path(self.tempdir.name) / "Old title.md"
        self.assertTrue(old_path.exists())
        note.body = "New title"
        note.metadata.title = "New title"
        self.storage.save_note(note)
        self.assertTrue(old_path.exists())
        self.assertFalse((Path(self.tempdir.name) / "New title.md").exists())
        # File contains frontmatter, but when loaded the body strips it
        reloaded = self.storage.load_note(note.metadata.note_id)
        self.assertEqual(reloaded.body, "New title")

    def test_storage_migrates_legacy_notes_and_metadata_layout(self) -> None:
        root = Path(self.tempdir.name)
        legacy_notes_dir = root / "notes"
        legacy_meta_dir = root / "meta"
        legacy_notes_dir.mkdir()
        legacy_meta_dir.mkdir()
        # Legacy notes don't have frontmatter
        (legacy_notes_dir / "Migrated Note.md").write_text("hello", encoding="utf-8")
        (legacy_meta_dir / "abc123.json").write_text(
            '{"note_id":"abc123","title":"Migrated Note","x":1,"y":2,"width":300,"height":200,"is_open":true,"created_at":"2026-01-01T00:00:00+00:00","updated_at":"2026-01-01T00:00:00+00:00","bg_color":"#ffd54f","file_stem":"Migrated Note"}',
            encoding="utf-8",
        )

        migrated = StickyStorage(AppSettings(storage_root=self.tempdir.name))

        self.assertTrue((root / "Migrated Note.md").exists())
        self.assertTrue((root / ".simple-sticky-notes" / "meta" / "abc123.json").exists())
        self.assertFalse(legacy_notes_dir.exists())
        self.assertFalse(legacy_meta_dir.exists())
        self.assertEqual(migrated.load_note("abc123").body, "hello")

    def test_suggested_file_stem_sanitizes_invalid_filename_characters(self) -> None:
        self.assertEqual(suggested_file_stem("Plan: finish / ship? *today*"), "Plan finish ship today")

    def test_note_title_uses_first_ten_words(self) -> None:
        self.assertEqual(
            note_title("one two three four five six seven eight nine ten eleven twelve"),
            "one two three four five six seven eight nine ten",
        )

    @unittest.skipUnless(yaml is not None, "PyYAML not installed")
    def test_frontmatter_title_is_first_nonblank_line_with_stickynote_tag(self) -> None:
        wrapped = format_note_with_frontmatter("\n\n# My Heading\nSecond line")
        parsed = yaml.safe_load(wrapped.split("\n---\n", 1)[0])
        self.assertEqual(parsed["title"], "My Heading")
        self.assertEqual(parsed["tags"], ["stickynote"])

    @unittest.skipUnless(yaml is not None, "PyYAML not installed")
    def test_frontmatter_title_is_valid_yaml_for_special_characters(self) -> None:
        # Titles with colons, quotes, leading dashes, brackets must stay valid YAML
        # so Obsidian can parse the properties block.
        for first_line in [
            "foo: bar",
            'has "double" quotes',
            "4.5mm clear acrylic:",
            "--- looks like a rule ---",
            "[wiki] #tag {brace}",
            "back\\slash",
        ]:
            wrapped = format_note_with_frontmatter(first_line)
            parsed = yaml.safe_load(wrapped.split("\n---\n", 1)[0])
            self.assertEqual(parsed["title"], first_line)
            self.assertEqual(parsed["tags"], ["stickynote"])

    def test_strip_frontmatter_is_exact_inverse_including_rule_lines(self) -> None:
        for body in [
            "plain note",
            "first line stays\nsecond line",
            "body with a\n---\nhorizontal rule",
            "--- leading rule line ---\nthen body",
            "---",
            "",
        ]:
            self.assertEqual(strip_frontmatter(format_note_with_frontmatter(body)), body)

    def test_strip_frontmatter_leaves_content_without_frontmatter_untouched(self) -> None:
        legacy = "no frontmatter here\njust text"
        self.assertEqual(strip_frontmatter(legacy), legacy)

    def test_saving_preserves_user_frontmatter_and_adds_stickynote_tag(self) -> None:
        # A sticky note the user also edited in Obsidian to add their own
        # properties and tags must keep them; only title + stickynote are owned.
        note = self.storage.create_note(body="placeholder")
        note_path = self.storage.note_path(note.metadata.note_id)
        note_path.write_text(
            "---\n"
            'title: "stale"\n'
            "aliases:\n"
            "  - nickname\n"
            "tags:\n"
            "  - personal\n"
            "cssclass: wide\n"
            "---\n"
            "New first line\nbody continues",
            encoding="utf-8",
        )

        # Reload (strips frontmatter) then save (re-merges from the on-disk YAML).
        reloaded = self.storage.load_note(note.metadata.note_id)
        self.assertEqual(reloaded.body, "New first line\nbody continues")
        self.storage.save_note(reloaded)

        block, body = split_frontmatter(note_path.read_text(encoding="utf-8"))
        self.assertEqual(body, "New first line\nbody continues")
        self.assertIn('title: "New first line"', block)
        self.assertIn("aliases:", block)
        self.assertIn("- nickname", block)
        self.assertIn("cssclass: wide", block)
        self.assertIn("- personal", block)
        self.assertIn("- stickynote", block)

    @unittest.skipUnless(yaml is not None, "PyYAML not installed")
    def test_merge_frontmatter_handles_tag_representations(self) -> None:
        cases = {
            "tags:\n  - work\n": ["work", "stickynote"],
            "tags: [work, ideas]\n": ["work", "ideas", "stickynote"],
            "tags: work\n": ["work", "stickynote"],
            "aliases:\n  - a\n": ["stickynote"],
            "tags:\n  - stickynote\n  - work\n": ["stickynote", "work"],
        }
        for existing, expected_tags in cases.items():
            block = merge_frontmatter(existing, "Some title")
            parsed = yaml.safe_load(block)
            self.assertCountEqual(parsed["tags"], expected_tags, msg=existing)

    def test_saving_note_writes_single_frontmatter_block_and_loads_clean_body(self) -> None:
        note = self.storage.create_note(body="hello\nworld")
        raw = self.storage.note_path(note.metadata.note_id).read_text(encoding="utf-8")
        self.assertEqual(raw.count("stickynote"), 1)
        # Re-saving (e.g. a geometry update) must not accumulate frontmatter blocks.
        self.storage.save_note(self.storage.load_note(note.metadata.note_id))
        raw = self.storage.note_path(note.metadata.note_id).read_text(encoding="utf-8")
        self.assertEqual(raw.count("stickynote"), 1)
        self.assertEqual(self.storage.load_note(note.metadata.note_id).body, "hello\nworld")


class InlineImageRunTests(unittest.TestCase):
    """Pure round-trip core for rendering image embeds inline in the editor."""

    @staticmethod
    def _is_image(name: str) -> bool:
        return name.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".webp"))

    def test_only_image_embeds_become_image_runs(self) -> None:
        body = "see ![[Pasted image 1.png]] and link ![[some note]] done"
        runs = split_body_for_images(body, self._is_image)
        self.assertEqual(
            runs,
            [
                ("text", "see "),
                ("image", "Pasted image 1.png"),
                ("text", " and link ![[some note]] done"),
            ],
        )

    def test_join_is_inverse_of_split(self) -> None:
        for body in [
            "plain text only",
            "![[a.png]]",
            "lead\n![[a.png]]\n![[b.jpg]]\ntrail",
            "no images but ![[a wikilink]] stays text",
            "",
        ]:
            self.assertEqual(join_image_runs(split_body_for_images(body, self._is_image)), body)

    def test_image_at_start_and_adjacent_images(self) -> None:
        body = "![[a.png]]![[b.png]]x"
        runs = split_body_for_images(body, self._is_image)
        self.assertEqual(runs, [("image", "a.png"), ("image", "b.png"), ("text", "x")])


class RecentNotesTests(unittest.TestCase):
    @staticmethod
    def _note(note_id: str, created_at: str) -> NoteRecord:
        meta = NoteMetadata(
            note_id=note_id, title=note_id, x=0, y=0, width=10, height=10,
            is_open=True, created_at=created_at, updated_at=created_at,
        )
        return NoteRecord(metadata=meta, body="")

    def test_recent_notes_newest_first_and_capped(self) -> None:
        notes = [self._note(f"n{i}", f"2026-06-{i:02d}T00:00:00+00:00") for i in range(1, 8)]
        notes = notes[3:] + notes[:3]  # de-order the input
        result = recent_notes(notes, limit=3)
        self.assertEqual([n.metadata.note_id for n in result], ["n7", "n6", "n5"])

    def test_recent_notes_handles_fewer_than_limit(self) -> None:
        notes = [self._note("a", "2026-01-01T00:00:00+00:00")]
        self.assertEqual(len(recent_notes(notes, limit=20)), 1)


class TilePositionTests(unittest.TestCase):
    AREA = (0, 0, 1920, 1080)

    def test_empty_screen_uses_top_left_slot(self) -> None:
        self.assertEqual(tile_position([], 360, 260, self.AREA, padding=24, gap=16), (24, 24))

    def test_next_note_avoids_overlap(self) -> None:
        occupied = [(24, 24, 360, 260)]
        x, y = tile_position(occupied, 360, 260, self.AREA, padding=24, gap=16)
        self.assertEqual((x, y), (400, 24))  # shifted right past the first note
        ox, oy, ow, oh = occupied[0]
        self.assertFalse(x < ox + ow and x + 360 > ox and y < oy + oh and y + 260 > oy)

    def test_cascades_when_area_too_small(self) -> None:
        self.assertEqual(tile_position([], 360, 260, (0, 0, 100, 100)), (24, 24))


class EdgeResizeTests(unittest.TestCase):
    def test_edge_zone_detects_all_regions(self) -> None:
        W = H = 200
        self.assertIsNone(edge_zone(100, 100, W, H, margin=6))
        self.assertEqual(edge_zone(0, 0, W, H, 6), "nw")
        self.assertEqual(edge_zone(199, 0, W, H, 6), "ne")
        self.assertEqual(edge_zone(0, 199, W, H, 6), "sw")
        self.assertEqual(edge_zone(199, 199, W, H, 6), "se")
        self.assertEqual(edge_zone(100, 1, W, H, 6), "n")
        self.assertEqual(edge_zone(100, 198, W, H, 6), "s")
        self.assertEqual(edge_zone(2, 100, W, H, 6), "w")
        self.assertEqual(edge_zone(197, 100, W, H, 6), "e")

    def test_resize_right_and_bottom_keep_origin(self) -> None:
        self.assertEqual(resize_geometry("e", 100, 100, 360, 260, 50, 99, 140, 100), (100, 100, 410, 260))
        self.assertEqual(resize_geometry("s", 100, 100, 360, 260, 99, 40, 140, 100), (100, 100, 360, 300))
        self.assertEqual(resize_geometry("se", 100, 100, 360, 260, 50, 40, 140, 100), (100, 100, 410, 300))

    def test_resize_left_and_top_move_corner(self) -> None:
        # dragging the west edge left by 50 grows width and shifts x left
        self.assertEqual(resize_geometry("w", 100, 100, 360, 260, -50, 0, 140, 100), (50, 100, 410, 260))
        self.assertEqual(resize_geometry("n", 100, 100, 360, 260, 0, -40, 140, 100), (100, 60, 360, 300))
        self.assertEqual(resize_geometry("nw", 100, 100, 360, 260, -50, -40, 140, 100), (50, 60, 410, 300))

    def test_resize_clamps_to_minimum_in_place(self) -> None:
        # shrinking the west edge past the minimum pins width and stops x
        x, y, w, h = resize_geometry("w", 100, 100, 360, 260, 1000, 0, 140, 100)
        self.assertEqual((w, x), (140, 100 + 360 - 140))


if __name__ == "__main__":
    unittest.main()
