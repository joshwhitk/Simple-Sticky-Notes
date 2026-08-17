package com.whitkin.stickynotes

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Assert.fail
import org.junit.Rule
import org.junit.Test
import org.junit.rules.TemporaryFolder
import java.io.File

/** The Joplin store against a fake transport: notebook discovery, CRUD, and the widget cache. */
class JoplinStoreTest {

    @get:Rule
    val tmp = TemporaryFolder()

    private fun store(transport: FakeJoplinTransport, cacheDir: File): JoplinStore =
        JoplinStore(JoplinApi("http://joplin.test:41185", "tok", transport, retryDelayMs = 0), cacheDir)

    private fun folderPage(hasMore: Boolean, vararg folders: Pair<String, String>): String {
        val items = folders.joinToString(",") { (id, title) -> """{"id":"$id","title":"$title"}""" }
        return """{"items":[$items],"has_more":$hasMore}"""
    }

    @Test
    fun findsNotebookByTitleAcrossPages() {
        val t = FakeJoplinTransport()
            .enqueue(200, folderPage(true, "f1" to "Other"))
            .enqueue(200, folderPage(false, "f2" to "Simple Sticky Notes"))
        assertEquals("f2", store(t, tmp.newFolder()).notebookId())
        assertEquals(2, t.requests.size)
        assertTrue(t.requests.all { it.method == "GET" && it.url.contains("/folders?") })
    }

    @Test
    fun createsNotebookWhenMissing() {
        val t = FakeJoplinTransport()
            .enqueue(200, folderPage(false, "f1" to "Other"))
            .enqueue(200, """{"id":"created","title":"Simple Sticky Notes"}""")
        assertEquals("created", store(t, tmp.newFolder()).notebookId())
        val post = t.requests[1]
        assertEquals("POST", post.method)
        assertTrue(post.url.contains("/folders?"))
        assertTrue(post.body!!.contains("Simple Sticky Notes"))
    }

    @Test
    fun listNotesPagesSortsNewestFirstAndFillsCache() {
        val cache = tmp.newFolder()
        val t = FakeJoplinTransport()
            .enqueue(200, folderPage(false, "nb" to "Simple Sticky Notes"))
            .enqueue(200, """{"items":[{"id":"a1","title":"Old","body":"old body","user_updated_time":1000}],"has_more":true}""")
            .enqueue(200, """{"items":[{"id":"b2","title":"New","body":"new body","user_updated_time":2000}],"has_more":false}""")
        val notes = store(t, cache).listNotes()
        assertEquals(listOf("joplin:b2", "joplin:a1"), notes.map { it.key })
        assertEquals(listOf("New", "Old"), notes.map { it.title })
        assertEquals(2000L, notes[0].modified)
        assertTrue(t.requests[1].url.contains("/folders/nb/notes?"))
        assertTrue(t.requests[1].url.contains("fields=id%2Ctitle%2Cbody%2Cuser_updated_time"))
        // Cache now serves widgets without network.
        assertEquals("new body", JoplinStore.readCached(cache, "joplin:b2")!!.body)
        assertEquals("old body", JoplinStore.readCached(cache, "joplin:a1")!!.body)
    }

    @Test
    fun listNotesPrunesCacheEntriesGoneFromTheNotebook() {
        val cache = tmp.newFolder()
        File(cache, "stale.json").writeText("""{"id":"stale","title":"T","body":"B","updated":1}""")
        val t = FakeJoplinTransport()
            .enqueue(200, folderPage(false, "nb" to "Simple Sticky Notes"))
            .enqueue(200, """{"items":[{"id":"keep","title":"K","body":"","user_updated_time":1}],"has_more":false}""")
        store(t, cache).listNotes()
        assertNull(JoplinStore.readCached(cache, "joplin:stale"))
        assertEquals("K", JoplinStore.readCached(cache, "joplin:keep")!!.title)
    }

    @Test
    fun saveNewNotePostsIntoTheNotebookAndCaches() {
        val cache = tmp.newFolder()
        val t = FakeJoplinTransport()
            .enqueue(200, folderPage(false, "nb" to "Simple Sticky Notes"))
            .enqueue(200, """{"id":"deadbeef"}""")
        val key = store(t, cache).saveNote(null, "First line\nrest of body")
        assertEquals("joplin:deadbeef", key)
        val post = t.requests[1]
        assertEquals("POST", post.method)
        assertTrue(post.url.contains("/notes?"))
        val sent = post.body!!
        assertTrue(sent.contains("\"parent_id\":\"nb\""))
        assertTrue(sent.contains("\"title\":\"First line rest of body\""))
        assertEquals("First line\nrest of body", JoplinStore.readCached(cache, key!!)!!.body)
    }

    @Test
    fun saveExistingNotePutsTitleAndBody() {
        val cache = tmp.newFolder()
        val t = FakeJoplinTransport().enqueue(200, """{"id":"deadbeef"}""")
        val key = store(t, cache).saveNote("joplin:deadbeef", "Updated text")
        assertEquals("joplin:deadbeef", key)
        val put = t.requests[0]
        assertEquals("PUT", put.method)
        assertTrue(put.url.contains("/notes/deadbeef?"))
        assertTrue(put.body!!.contains("\"body\":\"Updated text\""))
        assertEquals("Updated text", JoplinStore.readCached(cache, key!!)!!.body)
    }

    @Test
    fun blankNewNoteIsDiscardedWithoutAnyRequest() {
        val t = FakeJoplinTransport()
        assertNull(store(t, tmp.newFolder()).saveNote(null, "   \n  "))
        assertEquals(0, t.requests.size)
    }

    @Test
    fun deleteRemovesRemoteAndCacheAndToleratesAlreadyGone() {
        val cache = tmp.newFolder()
        File(cache, "abc.json").writeText("""{"id":"abc","title":"T","body":"B","updated":1}""")
        val t = FakeJoplinTransport().enqueue(200, "")
        store(t, cache).deleteNote("joplin:abc")
        assertEquals("DELETE", t.requests[0].method)
        assertNull(JoplinStore.readCached(cache, "joplin:abc"))

        val t404 = FakeJoplinTransport().enqueue(404, "not found")
        store(t404, cache).deleteNote("joplin:abc")  // must not throw

        val t500 = FakeJoplinTransport().enqueue(500, "x").enqueue(500, "x")
        try {
            store(t500, cache).deleteNote("joplin:abc")
            fail("expected JoplinApiError for a real server failure")
        } catch (e: JoplinApiError) {
            assertEquals(500, e.status)
        }
    }

    @Test
    fun readBodyFetchesAndRefreshesTheCache() {
        val cache = tmp.newFolder()
        val t = FakeJoplinTransport()
            .enqueue(200, """{"id":"abc","title":"T","body":"fresh body","user_updated_time":5}""")
        assertEquals("fresh body", store(t, cache).readBody("joplin:abc"))
        assertEquals("fresh body", JoplinStore.readCached(cache, "joplin:abc")!!.body)
    }

    @Test
    fun saveImageResourceUploadsAndReturnsTheEmbed() {
        val t = FakeJoplinTransport().enqueue(200, """{"id":"res1","title":"Pasted image 20260817140000.png"}""")
        val embed = store(t, tmp.newFolder()).saveImageResource("png", byteArrayOf(1, 2, 3), stamp = "20260817140000")
        assertEquals("![Pasted image 20260817140000.png](:/res1)", embed)
        val sent = t.requests[0]
        assertEquals("POST", sent.method)
        assertTrue(sent.url, sent.url.contains("/resources?"))
        val contentType = sent.contentType!!
        assertTrue(contentType, contentType.startsWith("multipart/form-data"))
        val body = sent.body!!
        assertTrue(body, body.contains("filename=\"Pasted image 20260817140000.png\""))
    }

    @Test
    fun saveImageResourceOfflineRaisesTheUnreachableError() {
        val t = FakeJoplinTransport().enqueueFailure().enqueueFailure()
        try {
            store(t, tmp.newFolder()).saveImageResource("png", byteArrayOf(1))
            fail("expected JoplinApiError")
        } catch (e: JoplinApiError) {
            assertTrue(e.message!!.contains("unreachable"))
        }
    }

    @Test
    fun offlineListRaisesTheUnreachableError() {
        val t = FakeJoplinTransport().enqueueFailure().enqueueFailure()
        try {
            store(t, tmp.newFolder()).listNotes()
            fail("expected JoplinApiError")
        } catch (e: JoplinApiError) {
            assertTrue(e.message!!.contains("unreachable"))
        }
    }

    @Test
    fun cachedNoteReadsAreNullSafeOnMissingOrCorruptFiles() {
        val cache = tmp.newFolder()
        assertNull(JoplinStore.readCached(cache, "joplin:nothere"))
        File(cache, "bad.json").writeText("this is not json")
        assertNull(JoplinStore.readCached(cache, "joplin:bad"))
    }
}
