package com.whitkin.stickynotes

import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Assert.fail
import org.junit.Test

/** The API client against a fake transport: auth, retries, timeouts-as-errors. */
class JoplinApiTest {

    private fun api(transport: FakeJoplinTransport, token: String = "tok123") =
        JoplinApi("http://joplin.test:41185/", token, transport, retryDelayMs = 0)

    @Test
    fun tokenGoesOnEveryRequestAndTrailingSlashIsTrimmed() {
        val t = FakeJoplinTransport().enqueue(200, """{"items":[],"has_more":false}""")
        api(t).get("/folders", mapOf("fields" to "id,title", "page" to "1"))
        assertEquals(1, t.requests.size)
        val url = t.requests[0].url
        assertTrue(url, url.startsWith("http://joplin.test:41185/folders?"))
        assertTrue(url, url.contains("token=tok123"))
        assertTrue(url, url.contains("fields=id%2Ctitle"))
    }

    @Test
    fun retriesOnceOnServerErrorThenSucceeds() {
        val t = FakeJoplinTransport()
            .enqueue(500, "boom")
            .enqueue(200, """{"id":"abc"}""")
        val result = api(t).get("/notes/abc")
        assertEquals("abc", result.getString("id"))
        assertEquals(2, t.requests.size)
    }

    @Test
    fun retriesOnceOnConnectionErrorThenSucceeds() {
        val t = FakeJoplinTransport()
            .enqueueFailure()
            .enqueue(200, """{"id":"abc"}""")
        assertEquals("abc", api(t).get("/notes/abc").getString("id"))
        assertEquals(2, t.requests.size)
    }

    @Test
    fun unreachableAfterAllAttemptsRaisesUiSafeError() {
        val t = FakeJoplinTransport().enqueueFailure().enqueueFailure()
        try {
            api(t).get("/notes/abc")
            fail("expected JoplinApiError")
        } catch (e: JoplinApiError) {
            assertTrue(e.message!!, e.message!!.contains("unreachable"))
            assertEquals(null, e.status)
        }
        assertEquals(2, t.requests.size)
    }

    @Test
    fun clientErrorsDoNotRetryAndCarryTheStatus() {
        val t = FakeJoplinTransport().enqueue(404, "not found")
        try {
            api(t).get("/notes/missing")
            fail("expected JoplinApiError")
        } catch (e: JoplinApiError) {
            assertEquals(404, e.status)
        }
        assertEquals(1, t.requests.size)
    }

    @Test
    fun postSendsJsonBodyAndParsesResponse() {
        val t = FakeJoplinTransport().enqueue(200, """{"id":"new1","title":"T"}""")
        val created = api(t).post("/notes", JSONObject().put("title", "T").put("body", "B"))
        assertEquals("new1", created.getString("id"))
        val sent = JSONObject(t.requests[0].body!!)
        assertEquals("T", sent.getString("title"))
        assertEquals("B", sent.getString("body"))
        assertEquals("POST", t.requests[0].method)
    }

    @Test
    fun postResourceBuildsAMultipartBodyWithDataAndPropsParts() {
        val t = FakeJoplinTransport().enqueue(200, """{"id":"res1","title":"shot.png"}""")
        val created = api(t).postResource("shot.png", byteArrayOf(0x00, -1) + " raw image".toByteArray())
        assertEquals("res1", created.getString("id"))

        val sent = t.requests[0]
        assertEquals("POST", sent.method)
        assertTrue(sent.url, sent.url.startsWith("http://joplin.test:41185/resources?"))
        assertTrue(sent.url, sent.url.contains("token=tok123"))
        val contentType = sent.contentType!!
        assertTrue(contentType, contentType.startsWith("multipart/form-data; boundary="))

        val boundary = contentType.substringAfter("boundary=")
        val body = sent.body!!
        assertTrue(body, body.startsWith("--$boundary\r\n"))
        assertTrue(body, body.contains("Content-Disposition: form-data; name=\"data\"; filename=\"shot.png\"\r\n"))
        assertTrue(body, body.contains(" raw image"))
        assertTrue(body, body.contains("Content-Disposition: form-data; name=\"props\"\r\n"))
        assertTrue(body, body.contains("{\"title\":\"shot.png\"}"))
        assertTrue(body, body.endsWith("--$boundary--\r\n"))
    }

    @Test
    fun postResourceRetriesOnceLikeEveryOtherCall() {
        val t = FakeJoplinTransport()
            .enqueueFailure()
            .enqueue(200, """{"id":"res2"}""")
        assertEquals("res2", api(t).postResource("x.png", byteArrayOf(1)).getString("id"))
        assertEquals(2, t.requests.size)
    }

    @Test
    fun emptyResponseBodyBecomesEmptyObject() {
        val t = FakeJoplinTransport().enqueue(200, "")
        val result = api(t).delete("/notes/abc")
        assertEquals(0, result.length())
    }
}
