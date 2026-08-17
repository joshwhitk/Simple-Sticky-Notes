package com.whitkin.stickynotes

import org.json.JSONObject
import java.io.IOException
import java.net.HttpURLConnection
import java.net.URL
import java.net.URLEncoder

/**
 * Minimal client for the Joplin Data API, matching the desktop app's
 * `simple_sticky_notes/joplin_storage.py`: token auth via the `token` query
 * parameter, a timeout on every call, and one retry on 5xx responses and
 * connection errors before raising [JoplinApiError] with a message that is
 * safe to show in the UI.
 *
 * The HTTP layer is behind [JoplinTransport] so unit tests can drive the
 * client with a fake transport and no network.
 */
class JoplinApiError(message: String, val status: Int? = null) : RuntimeException(message)

data class JoplinHttpResponse(val status: Int, val body: String)

fun interface JoplinTransport {
    @Throws(IOException::class)
    fun execute(method: String, url: String, body: String?): JoplinHttpResponse
}

/** Real transport: HttpURLConnection with connect and read timeouts. */
class HttpUrlConnectionTransport(private val timeoutMs: Int) : JoplinTransport {
    override fun execute(method: String, url: String, body: String?): JoplinHttpResponse {
        val conn = URL(url).openConnection() as HttpURLConnection
        try {
            conn.requestMethod = method
            conn.connectTimeout = timeoutMs
            conn.readTimeout = timeoutMs
            if (body != null) {
                conn.doOutput = true
                conn.setRequestProperty("Content-Type", "application/json")
                conn.outputStream.use { it.write(body.toByteArray(Charsets.UTF_8)) }
            }
            val status = conn.responseCode
            val stream = if (status >= 400) conn.errorStream else conn.inputStream
            val text = stream?.bufferedReader(Charsets.UTF_8)?.use { it.readText() } ?: ""
            return JoplinHttpResponse(status, text)
        } finally {
            conn.disconnect()
        }
    }
}

class JoplinApi(
    baseUrl: String,
    private val token: String,
    private val transport: JoplinTransport = HttpUrlConnectionTransport(REQUEST_TIMEOUT_MS),
    private val retryDelayMs: Long = RETRY_DELAY_MS,
) {
    val baseUrl: String = baseUrl.trim().trimEnd('/')

    fun get(path: String, query: Map<String, String> = emptyMap()): JSONObject =
        request("GET", path, query, null)

    fun post(path: String, payload: JSONObject): JSONObject =
        request("POST", path, emptyMap(), payload)

    fun put(path: String, payload: JSONObject): JSONObject =
        request("PUT", path, emptyMap(), payload)

    fun delete(path: String): JSONObject =
        request("DELETE", path, emptyMap(), null)

    private fun request(
        method: String,
        path: String,
        query: Map<String, String>,
        payload: JSONObject?,
    ): JSONObject {
        val params = LinkedHashMap(query)
        params["token"] = token
        val qs = params.entries.joinToString("&") { (k, v) ->
            URLEncoder.encode(k, "UTF-8") + "=" + URLEncoder.encode(v, "UTF-8")
        }
        val url = "$baseUrl$path?$qs"
        val body = payload?.toString()
        for (attempt in 1..REQUEST_ATTEMPTS) {
            val response = try {
                transport.execute(method, url, body)
            } catch (e: IOException) {
                if (attempt < REQUEST_ATTEMPTS) {
                    Thread.sleep(retryDelayMs)
                    continue
                }
                throw JoplinApiError(
                    "Joplin is unreachable at $baseUrl. " +
                        "Check the network (is Tailscale up?) and that Joplin's Web Clipper service is running."
                )
            }
            if (response.status >= 500 && attempt < REQUEST_ATTEMPTS) {
                Thread.sleep(retryDelayMs)
                continue
            }
            if (response.status >= 400) {
                throw JoplinApiError(
                    "Joplin API $method $path failed with HTTP ${response.status}.",
                    status = response.status,
                )
            }
            return if (response.body.isBlank()) JSONObject() else JSONObject(response.body)
        }
        throw JoplinApiError("Joplin API $method $path failed.")
    }

    companion object {
        const val REQUEST_TIMEOUT_MS = 10_000
        const val REQUEST_ATTEMPTS = 2
        const val RETRY_DELAY_MS = 500L
    }
}
