package com.whitkin.stickynotes

import android.app.Activity
import android.appwidget.AppWidgetManager
import android.content.Intent
import android.os.Bundle
import android.widget.ArrayAdapter
import android.widget.ListView
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity

/** Lets the user bind an (unbound, tray-added) note widget to an existing sticky note. */
class NoteWidgetConfigActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val appWidgetId = intent.getIntExtra(
            AppWidgetManager.EXTRA_APPWIDGET_ID, AppWidgetManager.INVALID_APPWIDGET_ID
        )
        setResult(Activity.RESULT_CANCELED)

        val vault = Settings.vaultDir(this)
        if (vault == null) {
            Toast.makeText(this, "Open the app and pick your vault folder first.", Toast.LENGTH_LONG).show()
            finish(); return
        }
        setContentView(R.layout.activity_config)
        findViewById<TextView>(R.id.cfg_title).text = getString(R.string.config_pick)
        val listView = findViewById<ListView>(R.id.cfg_list)

        // Scan off the main thread — the vault can hold thousands of files.
        Thread {
            val notes = try { VaultStore(vault).listNotes() } catch (e: Exception) { emptyList() }
            runOnUiThread {
                if (isFinishing || isDestroyed) return@runOnUiThread
                listView.adapter = ArrayAdapter(this, android.R.layout.simple_list_item_1, notes.map { it.title })
                listView.setOnItemClickListener { _, _, pos, _ ->
                    Settings.setWidgetNote(this, appWidgetId, notes[pos].file.absolutePath)
                    NoteWidgetProvider.render(this, AppWidgetManager.getInstance(this), appWidgetId)
                    setResult(Activity.RESULT_OK, Intent().putExtra(AppWidgetManager.EXTRA_APPWIDGET_ID, appWidgetId))
                    finish()
                }
            }
        }.start()
    }
}
