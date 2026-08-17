package com.whitkin.stickynotes

import android.app.PendingIntent
import android.appwidget.AppWidgetManager
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.Bundle
import android.widget.RemoteViews
import java.io.File
import android.widget.Toast

const val EXTRA_NOTE_PATH = "note_path"
const val EXTRA_PIN_ON_SAVE = "pin_on_save"
const val MAX_NOTE_WIDGETS = 40

/** Refreshes all per-note widgets (call after a note is saved/deleted). */
object WidgetUpdater {
    fun updateAll(ctx: Context) {
        val mgr = AppWidgetManager.getInstance(ctx)
        val ids = mgr.getAppWidgetIds(ComponentName(ctx, NoteWidgetProvider::class.java))
        if (ids.isNotEmpty()) NoteWidgetProvider().onUpdate(ctx, mgr, ids)
    }
}

/** Fires a user-confirmed pin request to place a per-note widget bound to [notePath]. */
object WidgetPins {
    fun requestPin(ctx: Context, notePath: String) {
        val mgr = AppWidgetManager.getInstance(ctx)
        val provider = ComponentName(ctx, NoteWidgetProvider::class.java)
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O || !mgr.isRequestPinAppWidgetSupported) {
            Toast.makeText(ctx, "Your launcher can't auto-place widgets — add one from the widget tray.", Toast.LENGTH_LONG).show()
            return
        }
        if (mgr.getAppWidgetIds(provider).size >= MAX_NOTE_WIDGETS) {
            Toast.makeText(ctx, "You already have $MAX_NOTE_WIDGETS sticky-note widgets.", Toast.LENGTH_LONG).show()
            return
        }
        val callback = Intent(ctx, PinCallbackReceiver::class.java).putExtra(EXTRA_NOTE_PATH, notePath)
        var flags = PendingIntent.FLAG_UPDATE_CURRENT
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) flags = flags or PendingIntent.FLAG_MUTABLE
        val pi = PendingIntent.getBroadcast(ctx, notePath.hashCode(), callback, flags)

        // Show the note itself in the "add to home screen?" dialog. Without this the
        // launcher falls back to the provider's preview, which used to be the app icon —
        // so confirming a sticky note meant looking at a picture of the app.
        var extras: Bundle? = null
        if (Build.VERSION.SDK_INT >= 33) {
            runCatching {
                extras = Bundle().apply {
                    putParcelable(AppWidgetManager.EXTRA_APPWIDGET_PREVIEW, previewOf(ctx, notePath))
                }
            }
        }
        mgr.requestPinAppWidget(provider, extras, pi)
    }

    /** The real note, drawn into the widget's own layout, for the confirmation dialog. */
    private fun previewOf(ctx: Context, notePath: String): RemoteViews {
        val views = RemoteViews(ctx.packageName, R.layout.widget_note)
        val f = File(notePath)
        var title = f.nameWithoutExtension
        var body = ""
        runCatching {
            val content = f.readText()
            val (block, raw) = Frontmatter.splitFrontmatter(content)
            title = Frontmatter.frontmatterTitle(block)
                ?: Frontmatter.firstNonblankLine(raw) ?: f.nameWithoutExtension
            body = Frontmatter.bodyWithoutTitleLine(raw, title)
        }
        views.setTextViewText(R.id.w_title, title)
        views.setTextViewText(R.id.w_body, body)
        return views
    }
}
