package com.whitkin.stickynotes

import org.json.JSONObject
import java.io.File
import java.time.OffsetDateTime
import java.time.ZoneOffset
import java.time.format.DateTimeFormatter
import java.util.UUID

data class StickyNote(val file: File, val title: String, val modified: Long)

/**
 * Reads/writes sticky notes in the shared Obsidian vault, byte-compatible with
 * the Windows app: a .md with merged frontmatter (stickynote tag) in the vault
 * root, plus a .simple-sticky-notes/meta/<note_id>.json sidecar so the desktop
 * app lists phone-created notes too.
 */
class VaultStore(private val vaultDir: File) {

    private val metaDir = File(vaultDir, ".simple-sticky-notes/meta")

    private fun mdFiles(): Array<File> =
        vaultDir.listFiles { f -> f.isFile && f.name.endsWith(".md", ignoreCase = true) } ?: emptyArray()

    /**
     * Lists sticky notes (by the stickynote tag). Reads only the head of each
     * file (frontmatter lives at the top) — the body isn't needed for the list,
     * which keeps this fast even on a multi-thousand-note vault. Call OFF the
     * main thread (it still opens every .md once).
     */
    fun listNotes(): List<StickyNote> {
        val notes = ArrayList<StickyNote>()
        for (f in mdFiles()) {
            val head = readHead(f)
            if (head.isEmpty() || !Frontmatter.hasStickynoteTag(head)) continue
            val (block, bodyHead) = Frontmatter.splitFrontmatter(head)
            val title = Frontmatter.frontmatterTitle(block)
                ?: Frontmatter.firstNonblankLine(bodyHead) ?: f.nameWithoutExtension
            notes.add(StickyNote(f, title, f.lastModified()))
        }
        notes.sortByDescending { it.modified }
        return notes
    }

    /** Reads up to [maxBytes] from the file (enough to cover any frontmatter). */
    private fun readHead(f: File, maxBytes: Int = 4096): String = try {
        f.inputStream().use { ins ->
            val buf = ByteArray(maxBytes)
            val n = ins.read(buf)
            if (n <= 0) "" else String(buf, 0, n, Charsets.UTF_8)
        }
    } catch (e: Exception) { "" }

    fun readBody(file: File): String = Frontmatter.stripFrontmatter(file.readText())

    private fun usedStemsLower(exclude: File?): Set<String> =
        mdFiles().filter { it != exclude }.map { it.nameWithoutExtension.lowercase() }.toSet()

    /** Create or update a note. Returns the file, or null if a NEW note had a blank body (discarded). */
    fun saveNote(existing: File?, body: String): File? {
        if (existing == null && body.isBlank()) return null
        val file: File = existing ?: run {
            val stem = Frontmatter.makeUniqueFileStem(Frontmatter.noteTitle(body), usedStemsLower(null))
            File(vaultDir, "$stem.md")
        }
        val existingFm = if (file.exists()) Frontmatter.splitFrontmatter(file.readText()).first else null
        file.parentFile?.mkdirs()
        file.writeText(Frontmatter.formatNoteWithFrontmatter(body, existingFm))
        writeSidecar(file, body)
        return file
    }

    /**
     * Saves pasted image bytes into the vault's _attachments folder and returns the
     * bare filename to embed as an Obsidian wikilink (`![[name]]`). Matches the
     * desktop app: "Pasted image <timestamp>.<ext>", de-duplicated with a -N suffix.
     */
    fun saveAttachment(ext: String, bytes: ByteArray): String {
        val dir = File(vaultDir, "_attachments")
        dir.mkdirs()
        val stamp = OffsetDateTime.now().format(DateTimeFormatter.ofPattern("yyyyMMddHHmmss"))
        var name = "Pasted image $stamp.$ext"
        var dest = File(dir, name)
        var i = 1
        while (dest.exists()) {
            name = "Pasted image $stamp-$i.$ext"
            dest = File(dir, name)
            i++
        }
        dest.writeBytes(bytes)
        return name
    }

    fun deleteNote(file: File) {
        sidecarForStem(file.nameWithoutExtension)?.delete()
        file.delete()
    }

    private fun sidecarForStem(stem: String): File? {
        val metas = metaDir.listFiles { f -> f.name.endsWith(".json") } ?: return null
        for (m in metas) {
            try {
                if (JSONObject(m.readText()).optString("file_stem").equals(stem, ignoreCase = true)) return m
            } catch (_: Exception) { /* skip unreadable */ }
        }
        return null
    }

    private fun writeSidecar(file: File, body: String) {
        metaDir.mkdirs()
        val stem = file.nameWithoutExtension
        val now = utcNowIso()
        val existing = sidecarForStem(stem)
        val j = if (existing != null) {
            try { JSONObject(existing.readText()) } catch (_: Exception) { JSONObject() }
        } else JSONObject()

        val noteId = j.optString("note_id").ifEmpty { newNoteId() }
        // Preserve desktop window state if present; fill defaults otherwise.
        val obj = JSONObject()
        obj.put("note_id", noteId)
        obj.put("title", Frontmatter.noteTitle(body))
        obj.put("x", j.optInt("x", 80))
        obj.put("y", j.optInt("y", 80))
        obj.put("width", j.optInt("width", 360))
        obj.put("height", j.optInt("height", 260))
        obj.put("is_open", j.optBoolean("is_open", true))
        obj.put("created_at", j.optString("created_at").ifEmpty { now })
        obj.put("updated_at", now)
        obj.put("bg_color", j.optString("bg_color").ifEmpty { "#ffd54f" })
        obj.put("file_stem", stem)

        (existing ?: File(metaDir, "$noteId.json")).writeText(obj.toString(2))
    }

    private fun newNoteId(): String = UUID.randomUUID().toString().replace("-", "").substring(0, 12)

    private fun utcNowIso(): String =
        OffsetDateTime.now(ZoneOffset.UTC).withNano(0)
            .format(DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ssxxx"))
}
