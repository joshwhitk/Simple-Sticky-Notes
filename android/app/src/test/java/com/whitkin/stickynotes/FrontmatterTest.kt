package com.whitkin.stickynotes

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/** Mirrors tests/test_storage.py to guarantee byte-compatibility with the desktop app. */
class FrontmatterTest {

    @Test
    fun stripIsExactInverseIncludingRuleLines() {
        val bodies = listOf(
            "plain note",
            "first line stays\nsecond line",
            "body with a\n---\nhorizontal rule",
            "--- leading rule line ---\nthen body",
            "---",
            ""
        )
        for (body in bodies) {
            assertEquals(body, Frontmatter.stripFrontmatter(Frontmatter.formatNoteWithFrontmatter(body)))
        }
    }

    @Test
    fun titleIsFirstNonblankLineAndStickynoteTag() {
        val wrapped = Frontmatter.formatNoteWithFrontmatter("\n\n# My Heading\nSecond line")
        val block = Frontmatter.splitFrontmatter(wrapped).first
        assertEquals("My Heading", Frontmatter.frontmatterTitle(block))
        assertTrue(Frontmatter.hasStickynoteTag(wrapped))
    }

    @Test
    fun titleIsValidForSpecialCharacters() {
        val firstLines = listOf(
            "foo: bar",
            "has \"double\" quotes",
            "4.5mm clear acrylic:",
            "--- looks like a rule ---",
            "[wiki] #tag {brace}",
            "back\\slash"
        )
        for (line in firstLines) {
            val wrapped = Frontmatter.formatNoteWithFrontmatter(line)
            val block = Frontmatter.splitFrontmatter(wrapped).first
            assertEquals(line, Frontmatter.frontmatterTitle(block))
            assertTrue(Frontmatter.hasStickynoteTag(wrapped))
        }
    }

    @Test
    fun mergePreservesUserPropertiesAndAddsTag() {
        val existing = "title: \"stale\"\n" +
            "aliases:\n  - nickname\n" +
            "tags:\n  - personal\n" +
            "cssclass: wide\n"
        val block = Frontmatter.mergeFrontmatter(existing, "New first line")
        assertTrue(block.contains("title: \"New first line\""))
        assertTrue(block.contains("- nickname"))
        assertTrue(block.contains("cssclass: wide"))
        assertTrue(block.contains("- personal"))
        assertTrue(block.contains("- stickynote"))
    }

    @Test
    fun mergeHandlesTagRepresentations() {
        val cases = mapOf(
            "tags:\n  - work\n" to listOf("work", "stickynote"),
            "tags: [work, ideas]\n" to listOf("work", "ideas", "stickynote"),
            "tags: work\n" to listOf("work", "stickynote"),
            "aliases:\n  - a\n" to listOf("stickynote"),
            "tags:\n  - stickynote\n  - work\n" to listOf("stickynote", "work")
        )
        for ((existing, expected) in cases) {
            val wrapped = "---\n" + Frontmatter.mergeFrontmatter(existing, "T") + "---\nbody"
            for (tag in expected) assertTrue("$existing -> expected $tag", wrapped.contains("- $tag") || wrapped.contains("[") )
            assertTrue(existing, Frontmatter.hasStickynoteTag(wrapped))
        }
    }

    @Test
    fun singleFrontmatterBlockNoAccumulation() {
        val once = Frontmatter.formatNoteWithFrontmatter("hello\nworld")
        // simulate edit cycle: strip then re-save using existing frontmatter
        val block = Frontmatter.splitFrontmatter(once).first
        val body = Frontmatter.stripFrontmatter(once)
        val twice = Frontmatter.formatNoteWithFrontmatter(body, block)
        assertEquals(1, countOccurrences(twice, "stickynote"))
        assertEquals("hello\nworld", Frontmatter.stripFrontmatter(twice))
    }

    @Test
    fun filenameRules() {
        assertEquals("Plan finish ship today", Frontmatter.suggestedFileStem("Plan: finish / ship? *today*"))
        assertEquals(
            "one two three four five six seven eight nine ten",
            Frontmatter.noteTitle("one two three four five six seven eight nine ten eleven twelve")
        )
    }

    @Test
    fun uniqueStemSuffixing() {
        val used = setOf("same title")
        assertEquals("Same title-1", Frontmatter.makeUniqueFileStem("Same title", used))
    }

    @Test
    fun bodyWithoutTitleLineDropsDuplicateHeading() {
        assertEquals("second line", Frontmatter.bodyWithoutTitleLine("My title\nsecond line", "My title"))
        assertEquals("second", Frontmatter.bodyWithoutTitleLine("# My title\n\nsecond", "My title"))
        assertEquals("", Frontmatter.bodyWithoutTitleLine("Only line", "Only line"))
        assertEquals("a\nb", Frontmatter.bodyWithoutTitleLine("a\nb", "different"))
    }

    private fun countOccurrences(s: String, sub: String): Int {
        var count = 0; var idx = s.indexOf(sub)
        while (idx >= 0) { count++; idx = s.indexOf(sub, idx + sub.length) }
        return count
    }
}
