package com.whitkin.stickynotes

import org.json.JSONArray
import org.json.JSONObject
import java.io.File

/** A note as last seen from Joplin, kept in the device-local cache for widgets and offline reads. */
data class CachedNote(val id: String, val title: String, val body: String, val modified: Long)

/**
 * The Joplin backend, matching the desktop app's `joplin_storage.py`
 * conventions: note identity is the Joplin note id (32 hex chars, carried
 * around as a "joplin:<id>" key), only title and body round-trip through the
 * Data API, and notes live in the "Simple Sticky Notes" notebook which is
 * found by title or created on demand.
 *
 * Every successful fetch or save also writes the note into [cacheDir]
 * (app-private, one JSON file per note), because home-screen widgets render
 * on the main thread and must never touch the network — they read this cache
 * instead. The cache is also the editor's offline fallback.
 *
 * All methods that hit the API must be called OFF the main thread.
 */
class JoplinStore(
    private val api: JoplinApi,
    private val cacheDir: File,
    private val notebookTitle: String = NOTEBOOK_TITLE,
) : NoteStore {

    private var notebookId: String? = null

    override fun listNotes(): List<NoteItem> {
        val remote = ArrayList<JSONObject>()
        var page = 1
        while (true) {
            val data = api.get(
                "/folders/${notebookId()}/notes",
                mapOf("fields" to NOTE_FIELDS, "page" to page.toString()),
            )
            val items = data.optJSONArray("items") ?: JSONArray()
            for (i in 0 until items.length()) remote.add(items.getJSONObject(i))
            if (!data.optBoolean("has_more")) break
            page++
        }
        val cached = remote.map { writeCache(cachedFromRemote(it)) }
        pruneCache(cached.map { it.id }.toSet())
        return cached
            .map { NoteItem(keyOf(it.id), it.title, it.modified) }
            .sortedByDescending { it.modified }
    }

    override fun readBody(key: String): String {
        val data = api.get("/notes/${idOf(key)}", mapOf("fields" to NOTE_FIELDS))
        return writeCache(cachedFromRemote(data)).body
    }

    override fun saveNote(existingKey: String?, body: String): String? {
        if (existingKey == null && body.isBlank()) return null
        val title = Frontmatter.noteTitle(body)
        val id: String = if (existingKey == null) {
            val payload = JSONObject()
                .put("title", title)
                .put("body", body)
                .put("parent_id", notebookId())
            api.post("/notes", payload).getString("id")
        } else {
            val id = idOf(existingKey)
            api.put("/notes/$id", JSONObject().put("title", title).put("body", body))
            id
        }
        writeCache(CachedNote(id, title, body, System.currentTimeMillis()))
        return keyOf(id)
    }

    override fun deleteNote(key: String) {
        try {
            api.delete("/notes/${idOf(key)}")
        } catch (e: JoplinApiError) {
            if (e.status != 404) throw e
        }
        cacheFile(cacheDir, idOf(key)).delete()
    }

    /** The configured notebook's id, found by title (paged) or created on demand. */
    fun notebookId(): String {
        notebookId?.let { return it }
        var page = 1
        while (true) {
            val data = api.get("/folders", mapOf("fields" to "id,title", "page" to page.toString()))
            val items = data.optJSONArray("items") ?: JSONArray()
            for (i in 0 until items.length()) {
                val folder = items.getJSONObject(i)
                if (folder.optString("title") == notebookTitle) {
                    return folder.getString("id").also { notebookId = it }
                }
            }
            if (!data.optBoolean("has_more")) break
            page++
        }
        val created = api.post("/folders", JSONObject().put("title", notebookTitle))
        return created.getString("id").also { notebookId = it }
    }

    /** The cached copy of a note, or null if it has never been seen online. */
    fun cachedNote(key: String): CachedNote? = readCached(cacheDir, key)

    // ----- cache -------------------------------------------------------------

    private fun cachedFromRemote(remote: JSONObject): CachedNote = CachedNote(
        id = remote.getString("id"),
        title = remote.optString("title").ifEmpty { "Untitled note" },
        body = remote.optString("body"),
        modified = remote.optLong("user_updated_time", System.currentTimeMillis()),
    )

    private fun writeCache(note: CachedNote): CachedNote {
        cacheDir.mkdirs()
        val obj = JSONObject()
            .put("id", note.id)
            .put("title", note.title)
            .put("body", note.body)
            .put("updated", note.modified)
        cacheFile(cacheDir, note.id).writeText(obj.toString(2))
        return note
    }

    /** Drops cache entries whose note is gone from the notebook. Only called after a full listing. */
    private fun pruneCache(keepIds: Set<String>) {
        val files = cacheDir.listFiles { f -> f.name.endsWith(".json") } ?: return
        for (f in files) {
            if (f.nameWithoutExtension !in keepIds) f.delete()
        }
    }

    companion object {
        const val KEY_PREFIX = "joplin:"
        const val NOTEBOOK_TITLE = "Simple Sticky Notes"
        const val NOTE_FIELDS = "id,title,body,user_updated_time"

        fun isJoplinKey(key: String?): Boolean = key?.startsWith(KEY_PREFIX) == true
        fun idOf(key: String): String = key.removePrefix(KEY_PREFIX)
        fun keyOf(id: String): String = KEY_PREFIX + id

        private fun cacheFile(cacheDir: File, id: String): File = File(cacheDir, "$id.json")

        /**
         * Reads one note from the cache without an API client — this is the
         * widgets' render path, safe on the main thread.
         */
        fun readCached(cacheDir: File, key: String): CachedNote? {
            val f = cacheFile(cacheDir, idOf(key))
            if (!f.exists()) return null
            return try {
                val obj = JSONObject(f.readText())
                CachedNote(
                    id = obj.getString("id"),
                    title = obj.optString("title").ifEmpty { "Untitled note" },
                    body = obj.optString("body"),
                    modified = obj.optLong("updated", 0L),
                )
            } catch (e: Exception) {
                null
            }
        }
    }
}
