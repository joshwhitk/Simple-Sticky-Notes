package com.whitkin.stickynotes

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/** The backend switch and settings backward compatibility. */
class BackendSelectionTest {

    @Test
    fun missingBackendSettingMeansFiles() {
        // Installs that predate the setting have no "backend" pref at all.
        assertEquals(Stores.BACKEND_FILES, Stores.normalizeBackend(null))
    }

    @Test
    fun recognizedValuesRoundTrip() {
        assertEquals(Stores.BACKEND_FILES, Stores.normalizeBackend("files"))
        assertEquals(Stores.BACKEND_JOPLIN, Stores.normalizeBackend("joplin"))
    }

    @Test
    fun unrecognizedValuesFallBackToFiles() {
        assertEquals(Stores.BACKEND_FILES, Stores.normalizeBackend(""))
        assertEquals(Stores.BACKEND_FILES, Stores.normalizeBackend("Joplin"))
        assertEquals(Stores.BACKEND_FILES, Stores.normalizeBackend("dropbox"))
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
