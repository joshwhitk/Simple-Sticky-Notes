package com.whitkin.stickynotes

import java.io.IOException

/**
 * Scripted transport for tests: queue up responses (or IOExceptions) and every
 * request the client makes is recorded for assertions. No sockets involved.
 */
class FakeJoplinTransport : JoplinTransport {

    data class Recorded(val method: String, val url: String, val body: String?)

    val requests = ArrayList<Recorded>()
    private val script = ArrayDeque<Any>()  // JoplinHttpResponse or IOException

    fun enqueue(response: JoplinHttpResponse) = apply { script.addLast(response) }
    fun enqueue(status: Int, body: String) = enqueue(JoplinHttpResponse(status, body))
    fun enqueueFailure(error: IOException = IOException("connection refused")) = apply { script.addLast(error) }

    override fun execute(method: String, url: String, body: String?): JoplinHttpResponse {
        requests.add(Recorded(method, url, body))
        check(script.isNotEmpty()) { "FakeJoplinTransport ran out of scripted responses for $method $url" }
        val next = script.removeFirst()
        if (next is IOException) throw next
        return next as JoplinHttpResponse
    }
}
