package com.whitkin.stickynotes

/**
 * Kotlin port of the format contract in the Windows app's
 * `simple_sticky_notes/storage.py`. Keep these byte-compatible with the
 * desktop app so notes round-trip cleanly through the shared Obsidian vault.
 *
 * Parity is guaranteed by FrontmatterTest, which mirrors the Python test cases.
 */
object Frontmatter {

    const val MAX_FILE_STEM_LENGTH = 80
    const val MAX_TITLE_WORDS = 10
    const val STICKYNOTE_TAG = "stickynote"

    private val TOP_LEVEL_KEY_RE = Regex("^([^\\s:#][^:]*):(.*)$")
    private val LIST_ITEM_RE = Regex("^(\\s*)-\\s*(.*)$")
    private val INVALID_FILENAME_RE = Regex("[<>:\"/\\\\|?*\\x00-\\x1f]")
    private val WS_RE = Regex("\\s+")

    // ----- title / filename --------------------------------------------------

    fun firstNonblankLine(text: String): String? {
        for (line in text.split(Regex("\r?\n"))) {
            val stripped = line.trim()
            if (stripped.isNotEmpty()) return stripped.trimStart('#').trim()
        }
        return null
    }

    private fun collapsedNoteText(text: String): String {
        val flattened = text.split(Regex("\r?\n"))
            .map { it.trim() }
            .filter { it.isNotEmpty() }
            .joinToString(" ") { it.trimStart('#').trim() }
        return flattened.ifEmpty { "Untitled note" }
    }

    fun noteTitle(body: String): String {
        val words = collapsedNoteText(body).split(WS_RE).filter { it.isNotEmpty() }
        if (words.isEmpty()) return "Untitled note"
        return words.take(MAX_TITLE_WORDS).joinToString(" ")
    }

    fun suggestedFileStem(title: String): String {
        val source = noteTitle(title)
        var cleaned = INVALID_FILENAME_RE.replace(source, " ")
        cleaned = WS_RE.replace(cleaned, " ").trim(' ', '.')
        if (cleaned.isEmpty()) cleaned = "Untitled note"
        return cleaned.take(MAX_FILE_STEM_LENGTH).trimEnd(' ', '.')
    }

    /** Unique stem (case-insensitive) given the stems already used by other notes. */
    fun makeUniqueFileStem(title: String, usedStemsLower: Set<String>): String {
        val base = suggestedFileStem(title)
        var candidate = base
        var counter = 1
        while (candidate.lowercase() in usedStemsLower) {
            val suffix = "-$counter"
            candidate = base.take(MAX_FILE_STEM_LENGTH - suffix.length) + suffix
            counter++
        }
        return candidate
    }

    // ----- yaml quoting ------------------------------------------------------

    fun yamlDoubleQuote(value: String): String {
        val escaped = value.replace("\\", "\\\\").replace("\"", "\\\"")
        return "\"$escaped\""
    }

    // ----- frontmatter split / strip ----------------------------------------

    /** Returns Pair(frontmatterBlockOrNull, body). Only lines that are exactly
     *  "---" delimit the block, so interior "---" rules in the body survive. */
    fun splitFrontmatter(content: String): Pair<String?, String> {
        val lines = splitLinesKeepEnds(content)
        if (lines.isEmpty() || lines[0].trim() != "---") return Pair(null, content)
        for (i in 1 until lines.size) {
            if (lines[i].trim() == "---") {
                val block = lines.subList(1, i).joinToString("")
                val body = lines.subList(i + 1, lines.size).joinToString("")
                return Pair(block, body)
            }
        }
        return Pair(null, content)
    }

    fun stripFrontmatter(content: String): String = splitFrontmatter(content).second

    private fun splitLinesKeepEnds(s: String): List<String> {
        val out = ArrayList<String>()
        var start = 0
        var i = 0
        while (i < s.length) {
            val c = s[i]
            if (c == '\n') {
                out.add(s.substring(start, i + 1)); start = i + 1
            } else if (c == '\r') {
                if (i + 1 < s.length && s[i + 1] == '\n') {
                    out.add(s.substring(start, i + 2)); i++; start = i + 1
                } else {
                    out.add(s.substring(start, i + 1)); start = i + 1
                }
            }
            i++
        }
        if (start < s.length) out.add(s.substring(start))
        return out
    }

    // ----- merge -------------------------------------------------------------

    private data class Entry(var key: String?, val lines: MutableList<String>)

    private fun normTag(v: String): String = v.trim().trim('\'', '"').trim()

    private fun parseTopLevelEntries(block: String): MutableList<Entry> {
        val entries = ArrayList<Entry>()
        var current: Entry? = null
        for (line in block.split(Regex("\r?\n"))) {
            val m = TOP_LEVEL_KEY_RE.find(line)
            val isTop = m != null && line.isNotEmpty() && !line[0].isWhitespace()
            if (isTop) {
                current = Entry(m!!.groupValues[1].trim(), mutableListOf(line))
                entries.add(current)
            } else if (current == null) {
                current = Entry(null, mutableListOf(line))
                entries.add(current)
            } else {
                current.lines.add(line)
            }
        }
        return entries
    }

    private fun setTitleEntry(entries: MutableList<Entry>, title: String) {
        val titleLine = "title: ${yamlDoubleQuote(title)}"
        val existing = entries.firstOrNull { it.key == "title" }
        if (existing != null) {
            existing.lines.clear(); existing.lines.add(titleLine)
        } else {
            entries.add(0, Entry("title", mutableListOf(titleLine)))
        }
    }

    private fun ensureStickynoteTag(entries: MutableList<Entry>) {
        val tagsEntry = entries.firstOrNull { it.key == "tags" || it.key == "tag" }
        if (tagsEntry == null) {
            entries.add(Entry("tags", mutableListOf("tags:", "  - $STICKYNOTE_TAG")))
            return
        }
        val firstLine = tagsEntry.lines[0]
        val keyPart = firstLine.substringBefore(":")
        val inlineValue = firstLine.substringAfter(":", "").trim()

        if (inlineValue.startsWith("[")) {
            val inner = inlineValue.trim().removePrefix("[").removeSuffix("]")
            val items = inner.split(",").map { it.trim() }.filter { it.isNotEmpty() }.toMutableList()
            if (items.any { normTag(it) == STICKYNOTE_TAG }) return
            items.add(STICKYNOTE_TAG)
            tagsEntry.lines[0] = "$keyPart: [${items.joinToString(", ")}]"
            return
        }

        if (inlineValue.isNotEmpty() && inlineValue != "~" && inlineValue != "null") {
            if (normTag(inlineValue) == STICKYNOTE_TAG) return
            tagsEntry.lines[0] = "$keyPart: [$inlineValue, $STICKYNOTE_TAG]"
            return
        }

        // Block list (or empty) — inspect indented "- item" children.
        var indent = "  "
        for (child in tagsEntry.lines.drop(1)) {
            val m = LIST_ITEM_RE.find(child) ?: continue
            if (m.groupValues[1].isNotEmpty()) indent = m.groupValues[1]
            if (normTag(m.groupValues[2]) == STICKYNOTE_TAG) return
        }
        tagsEntry.lines.add("$indent- $STICKYNOTE_TAG")
    }

    private fun renderEntries(entries: List<Entry>): String {
        val lines = entries.flatMap { it.lines }
        return lines.joinToString("\n") + "\n"
    }

    fun mergeFrontmatter(existingBlock: String?, title: String): String {
        if (existingBlock.isNullOrBlank()) {
            return "title: ${yamlDoubleQuote(title)}\ntags:\n  - $STICKYNOTE_TAG\n"
        }
        val entries = parseTopLevelEntries(existingBlock)
        setTitleEntry(entries, title)
        ensureStickynoteTag(entries)
        return renderEntries(entries)
    }

    /** Prepend (merged) frontmatter to body. */
    fun formatNoteWithFrontmatter(body: String, existingFrontmatter: String? = null): String {
        val title = firstNonblankLine(body) ?: "Untitled note"
        val block = mergeFrontmatter(existingFrontmatter, title)
        return "---\n$block---\n$body"
    }

    // ----- reading helpers ---------------------------------------------------

    /** True if the frontmatter block declares the stickynote tag (any form). */
    fun hasStickynoteTag(content: String): Boolean {
        val block = splitFrontmatter(content).first ?: return false
        val entries = parseTopLevelEntries(block)
        val tagsEntry = entries.firstOrNull { it.key == "tags" || it.key == "tag" } ?: return false
        val inlineValue = tagsEntry.lines[0].substringAfter(":", "").trim()
        if (inlineValue.startsWith("[")) {
            val inner = inlineValue.removePrefix("[").removeSuffix("]")
            return inner.split(",").any { normTag(it) == STICKYNOTE_TAG }
        }
        if (inlineValue.isNotEmpty() && inlineValue != "~" && inlineValue != "null") {
            return normTag(inlineValue) == STICKYNOTE_TAG
        }
        return tagsEntry.lines.drop(1).any { child ->
            LIST_ITEM_RE.find(child)?.let { normTag(it.groupValues[2]) == STICKYNOTE_TAG } ?: false
        }
    }

    /**
     * Body with its leading title line removed, when that line equals [title]
     * (the common case, since the title is derived from the first non-blank
     * line). Used so a widget doesn't show the title twice.
     */
    fun bodyWithoutTitleLine(body: String, title: String): String {
        if (firstNonblankLine(body) != title) return body
        val lines = body.split(Regex("\r?\n"))
        var i = 0
        while (i < lines.size && lines[i].trim().isEmpty()) i++   // leading blanks
        if (i < lines.size) i++                                   // the title line
        while (i < lines.size && lines[i].trim().isEmpty()) i++   // blanks after it
        return lines.drop(i).joinToString("\n")
    }

    /** The unquoted `title:` value from a frontmatter block, if present. */
    fun frontmatterTitle(block: String?): String? {
        if (block == null) return null
        val entry = parseTopLevelEntries(block).firstOrNull { it.key == "title" } ?: return null
        var v = entry.lines[0].substringAfter(":", "").trim()
        if (v.length >= 2 && v.startsWith("\"") && v.endsWith("\"")) {
            v = v.substring(1, v.length - 1).replace("\\\"", "\"").replace("\\\\", "\\")
        }
        return v
    }
}
