package com.whitkin.stickynotes

import android.app.PendingIntent
import android.appwidget.AppWidgetManager
import android.appwidget.AppWidgetProvider
import android.content.Context
import android.content.Intent
import android.widget.RemoteViews
import java.io.File

/** A home-screen widget bound to a single sticky note. Displays it; tap opens the editor. */
class NoteWidgetProvider : AppWidgetProvider() {

    override fun onUpdate(context: Context, mgr: AppWidgetManager, appWidgetIds: IntArray) {
        for (id in appWidgetIds) render(context, mgr, id)
    }

    override fun onDeleted(context: Context, appWidgetIds: IntArray) {
        for (id in appWidgetIds) Settings.removeWidget(context, id)
    }

    companion object {
        fun render(ctx: Context, mgr: AppWidgetManager, id: Int) {
            val views = RemoteViews(ctx.packageName, R.layout.widget_note)
            val path = Settings.widgetNote(ctx, id)
            val vault = Settings.vaultDir(ctx)

            if (path == null) {
                views.setTextViewText(R.id.w_title, ctx.getString(R.string.widget_pick_prompt))
                views.setTextViewText(R.id.w_body, "")
                val cfg = Intent(ctx, NoteWidgetConfigActivity::class.java)
                    .putExtra(AppWidgetManager.EXTRA_APPWIDGET_ID, id)
                    .setFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP)
                views.setOnClickPendingIntent(R.id.w_root, activityPi(ctx, id, cfg))
            } else {
                val f = File(path)
                var title = f.nameWithoutExtension
                var body = "(note not found)"
                if (vault != null && f.exists()) {
                    val content = try { f.readText() } catch (e: Exception) { "" }
                    val (block, raw) = Frontmatter.splitFrontmatter(content)
                    title = Frontmatter.frontmatterTitle(block)
                        ?: Frontmatter.firstNonblankLine(raw) ?: f.nameWithoutExtension
                    body = Frontmatter.bodyWithoutTitleLine(raw, title)
                }
                views.setTextViewText(R.id.w_title, title)
                views.setTextViewText(R.id.w_body, body)
                val edit = Intent(ctx, EditorActivity::class.java)
                    .putExtra(EXTRA_NOTE_PATH, path)
                    .setFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP)
                views.setOnClickPendingIntent(R.id.w_root, activityPi(ctx, id, edit))
            }
            mgr.updateAppWidget(id, views)
        }

        private fun activityPi(ctx: Context, requestCode: Int, intent: Intent): PendingIntent =
            PendingIntent.getActivity(
                ctx, requestCode, intent,
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
            )
    }
}
