package com.whitkin.stickynotes

import android.appwidget.AppWidgetManager
import android.content.ComponentName
import android.content.Context
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.time.OffsetDateTime
import java.time.ZoneOffset
import java.time.format.DateTimeFormatter

/**
 * Publishes the set of notes currently on the home screen (one per placed Spawn
 * widget) to `<vault>/.simple-sticky-notes/phone-home.json`. Syncthing carries it
 * to the PC, where the desktop app's "Show phone sticky notes" opens them.
 */
object PhoneHome {
    fun sync(ctx: Context) {
        val vault = Settings.vaultDir(ctx) ?: return
        val mgr = AppWidgetManager.getInstance(ctx)
        val ids = mgr.getAppWidgetIds(ComponentName(ctx, NoteWidgetProvider::class.java))
        val stems = LinkedHashSet<String>()
        for (id in ids) {
            val path = Settings.widgetNote(ctx, id) ?: continue
            val f = File(path)
            if (f.exists()) stems.add(f.nameWithoutExtension)
        }
        val dir = File(vault, ".simple-sticky-notes")
        if (!dir.exists()) dir.mkdirs()
        val arr = JSONArray()
        for (s in stems) arr.put(s)
        val obj = JSONObject()
        obj.put(
            "updated_at",
            OffsetDateTime.now(ZoneOffset.UTC).withNano(0)
                .format(DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ssxxx"))
        )
        obj.put("file_stems", arr)
        try {
            File(dir, "phone-home.json").writeText(obj.toString(2))
        } catch (_: Exception) {
            /* vault not writable yet — best effort */
        }
    }
}
