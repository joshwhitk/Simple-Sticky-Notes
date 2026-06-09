package com.whitkin.stickynotes

import android.app.PendingIntent
import android.appwidget.AppWidgetManager
import android.appwidget.AppWidgetProvider
import android.content.Context
import android.content.Intent
import android.widget.RemoteViews

/**
 * A persistent "Spawn" button widget: tapping it creates a new sticky note (opens
 * the editor) and then offers to place a Sticky Note widget for it on the home
 * screen — so a new home-screen sticky is one tap away, no widget-picker needed.
 */
class SpawnWidgetProvider : AppWidgetProvider() {
    override fun onUpdate(context: Context, mgr: AppWidgetManager, appWidgetIds: IntArray) {
        for (id in appWidgetIds) {
            val views = RemoteViews(context.packageName, R.layout.widget_spawn)
            val intent = Intent(context, EditorActivity::class.java)
                .putExtra(EXTRA_PIN_ON_SAVE, true)
                .setFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP)
            val pi = PendingIntent.getActivity(
                context, id, intent,
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
            )
            views.setOnClickPendingIntent(R.id.spawn_root, pi)
            mgr.updateAppWidget(id, views)
        }
    }
}
