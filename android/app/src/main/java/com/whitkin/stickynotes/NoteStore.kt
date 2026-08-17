package com.whitkin.stickynotes

import android.content.Context
import java.io.File

/**
 * One list row, backend-agnostic. [key] identifies the note to the active
 * backend: an absolute .md path for the files backend, or "joplin:<id>" for
 * the Joplin backend. Keys travel through intents and widget bindings exactly
 * like file paths always did, so the widget plumbing needed no rework.
 */
data class NoteItem(val key: String, val title: String, val modified: Long)

/** The storage surface the UI actually calls: list, read, save, delete. */
interface NoteStore {
    fun listNotes(): List<NoteItem>
    fun readBody(key: String): String
    /** Create or update. Returns the note's key, or null if a NEW note had a blank body. */
    fun saveNote(existingKey: String?, body: String): String?
    fun deleteNote(key: String)
}

/**
 * The vault-markdown backend, unchanged: this is a thin adapter over
 * [VaultStore] so the files on disk stay byte-for-byte identical to what the
 * app has always written.
 */
class FileNoteStore(vaultDir: File) : NoteStore {
    private val vault = VaultStore(vaultDir)

    override fun listNotes(): List<NoteItem> =
        vault.listNotes().map { NoteItem(it.file.absolutePath, it.title, it.modified) }

    override fun readBody(key: String): String = vault.readBody(File(key))

    override fun saveNote(existingKey: String?, body: String): String? =
        vault.saveNote(existingKey?.let { File(it) }, body)?.absolutePath

    override fun deleteNote(key: String) = vault.deleteNote(File(key))
}

/** Picks the active backend from settings. Pure decisions live here so tests can cover them. */
object Stores {
    const val BACKEND_FILES = "files"
    const val BACKEND_JOPLIN = "joplin"

    /**
     * Missing or unrecognized values mean the files backend, so installs that
     * predate the setting (and any future typo in it) keep working unchanged.
     */
    fun normalizeBackend(raw: String?): String =
        if (raw == BACKEND_JOPLIN) BACKEND_JOPLIN else BACKEND_FILES

    /** Device-local cache of Joplin note bodies; widgets render from it without network. */
    fun joplinCacheDir(ctx: Context): File = File(ctx.filesDir, "joplin-cache")

    /** The active store, or null when the files backend has no vault folder configured yet. */
    fun forContext(ctx: Context): NoteStore? = when (Settings.backend(ctx)) {
        BACKEND_JOPLIN -> JoplinStore(
            JoplinApi(Settings.joplinApiUrl(ctx), Settings.joplinApiToken(ctx)),
            joplinCacheDir(ctx),
        )
        else -> Settings.vaultDir(ctx)?.let { FileNoteStore(it) }
    }
}
