package com.whitkin.stickynotes

import java.io.IOException

/**
 * Scripted transport for tests: queue up responses (or IOExceptions) and every
 * request the client makes is recorded for assertions. No sockets involved.
 */
class FakeJoplinTransport : JoplinTransport {

    class Recorded(val method: String, val url: String, val contentType: String?, val bytes: ByteArray?) {
        /** The body decoded as UTF-8 — right for JSON; multipart assertions can use [bytes]. */
        val body: String? get() = bytes?.toString(Charsets.UTF_8)
    }

    val requests = ArrayList<Recorded>()
    private val script = ArrayDeque<Any>()  // JoplinHttpResponse or IOException

    fun enqueue(response: JoplinHttpResponse) = apply { script.addLast(response) }
    fun enqueue(status: Int, body: String) = enqueue(JoplinHttpResponse(status, body))
    fun enqueueFailure(error: IOException = IOException("connection refused")) = apply { script.addLast(error) }

    override fun execute(method: String, url: String, contentType: String?, body: ByteArray?): JoplinHttpResponse {
        requests.add(Recorded(method, url, contentType, body))
        check(script.isNotEmpty()) { "FakeJoplinTransport ran out of scripted responses for $method $url" }
        val next = script.removeFirst()
        if (next is IOException) throw next
        return next as JoplinHttpResponse
    }
}
