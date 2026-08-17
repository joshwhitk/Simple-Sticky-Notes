package com.whitkin.stickynotes

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/** The backend switch and settings backward compatibility. */
class BackendSelectionTest {

    @Test
    fun missingBackendSettingMeansJoplin() {
        // An install with no "backend" pref is a fresh one, and the notes live in Joplin
        // since 2026-08-17. Defaulting to files would point it at a frozen archive.
        assertEquals(Stores.BACKEND_JOPLIN, Stores.normalizeBackend(null))
    }

    @Test
    fun recognizedValuesRoundTrip() {
        assertEquals(Stores.BACKEND_FILES, Stores.normalizeBackend("files"))
        assertEquals(Stores.BACKEND_JOPLIN, Stores.normalizeBackend("joplin"))
    }

    @Test
    fun onlyAnExplicitFilesKeepsTheArchiveBackend() {
        // Anything unrecognized resolves to the live store rather than the dead one:
        // a typo should not silently send his notes to a folder nothing reads.
        assertEquals(Stores.BACKEND_JOPLIN, Stores.normalizeBackend(""))
        assertEquals(Stores.BACKEND_JOPLIN, Stores.normalizeBackend("Joplin"))
        assertEquals(Stores.BACKEND_JOPLIN, Stores.normalizeBackend("dropbox"))
        assertEquals(Stores.BACKEND_FILES, Stores.normalizeBackend("files"))
    }

    @Test
    fun defaultJoplinUrlMatchesTheDesktopApp() {
        assertEquals("http://100.121.209.20:41185", Settings.DEFAULT_JOPLIN_URL)
    }

    @Test
    fun joplinKeysAreNamespacedAwayFromFilePaths() {
        assertTrue(JoplinStore.isJoplinKey("joplin:0123456789abcdef0123456789abcdef"))
        assertFalse(JoplinStore.isJoplinKey("/storage/emulated/0/vault/Note.md"))
        assertFalse(JoplinStore.isJoplinKey("C:\\vault\\Note.md"))
        assertFalse(JoplinStore.isJoplinKey(null))
        assertEquals("abc", JoplinStore.idOf(JoplinStore.keyOf("abc")))
    }

    @Test
    fun notebookNameMatchesTheDesktopConvention() {
        assertEquals("Simple Sticky Notes", JoplinStore.NOTEBOOK_TITLE)
    }
}
