package com.whitkin.stickynotes

import android.content.Context
import java.io.File

/** App preferences: storage backend, the vault folder path, Joplin API settings, and per-widget note bindings. */
object Settings {
    private const val PREFS = "ssn_prefs"
    private const val KEY_VAULT = "vault_path"
    private const val KEY_BACKEND = "backend"
    private const val KEY_JOPLIN_URL = "joplin_api_url"
    private const val KEY_JOPLIN_TOKEN = "joplin_api_token"

    /** Same default as the desktop app's settings: the Joplin server on Josh's tailnet. */
    const val DEFAULT_JOPLIN_URL = "http://100.121.209.20:41185"

    private fun prefs(ctx: Context) = ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE)

    fun vaultPath(ctx: Context): String? = prefs(ctx).getString(KEY_VAULT, null)
    fun setVaultPath(ctx: Context, path: String) = prefs(ctx).edit().putString(KEY_VAULT, path).apply()
    fun vaultDir(ctx: Context): File? = vaultPath(ctx)?.let { File(it) }

    /** "files" (default) or "joplin". Absent or unrecognized values fall back to "files". */
    fun backend(ctx: Context): String = Stores.normalizeBackend(prefs(ctx).getString(KEY_BACKEND, null))
    fun setBackend(ctx: Context, backend: String) =
        prefs(ctx).edit().putString(KEY_BACKEND, Stores.normalizeBackend(backend)).apply()

    fun joplinApiUrl(ctx: Context): String =
        prefs(ctx).getString(KEY_JOPLIN_URL, null)?.takeIf { it.isNotBlank() } ?: DEFAULT_JOPLIN_URL
    fun setJoplinApiUrl(ctx: Context, url: String) =
        prefs(ctx).edit().putString(KEY_JOPLIN_URL, url.trim()).apply()

    fun joplinApiToken(ctx: Context): String = prefs(ctx).getString(KEY_JOPLIN_TOKEN, null) ?: ""
    fun setJoplinApiToken(ctx: Context, token: String) =
        prefs(ctx).edit().putString(KEY_JOPLIN_TOKEN, token.trim()).apply()

    fun setWidgetNote(ctx: Context, appWidgetId: Int, path: String) =
        prefs(ctx).edit().putString("widget_$appWidgetId", path).apply()
    fun widgetNote(ctx: Context, appWidgetId: Int): String? =
        prefs(ctx).getString("widget_$appWidgetId", null)
    fun removeWidget(ctx: Context, appWidgetId: Int) =
        prefs(ctx).edit().remove("widget_$appWidgetId").apply()
}
