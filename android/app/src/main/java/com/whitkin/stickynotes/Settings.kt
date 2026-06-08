package com.whitkin.stickynotes

import android.content.Context
import java.io.File

/** App preferences: the vault folder path and per-widget note bindings. */
object Settings {
    private const val PREFS = "ssn_prefs"
    private const val KEY_VAULT = "vault_path"

    private fun prefs(ctx: Context) = ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE)

    fun vaultPath(ctx: Context): String? = prefs(ctx).getString(KEY_VAULT, null)
    fun setVaultPath(ctx: Context, path: String) = prefs(ctx).edit().putString(KEY_VAULT, path).apply()
    fun vaultDir(ctx: Context): File? = vaultPath(ctx)?.let { File(it) }

    fun setWidgetNote(ctx: Context, appWidgetId: Int, path: String) =
        prefs(ctx).edit().putString("widget_$appWidgetId", path).apply()
    fun widgetNote(ctx: Context, appWidgetId: Int): String? =
        prefs(ctx).getString("widget_$appWidgetId", null)
    fun removeWidget(ctx: Context, appWidgetId: Int) =
        prefs(ctx).edit().remove("widget_$appWidgetId").apply()
}
