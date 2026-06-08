package com.whitkin.stickynotes

import android.appwidget.AppWidgetManager
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent

/** Receives the new appWidgetId after a successful pin request and binds it to the note. */
class PinCallbackReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        val notePath = intent.getStringExtra(EXTRA_NOTE_PATH) ?: return
        val appWidgetId = intent.getIntExtra(
            AppWidgetManager.EXTRA_APPWIDGET_ID, AppWidgetManager.INVALID_APPWIDGET_ID
        )
        if (appWidgetId == AppWidgetManager.INVALID_APPWIDGET_ID) return
        Settings.setWidgetNote(context, appWidgetId, notePath)
        NoteWidgetProvider().onUpdate(
            context, AppWidgetManager.getInstance(context), intArrayOf(appWidgetId)
        )
    }
}
