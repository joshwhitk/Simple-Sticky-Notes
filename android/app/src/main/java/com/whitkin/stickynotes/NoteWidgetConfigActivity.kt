package com.whitkin.stickynotes

import android.app.Activity
import android.appwidget.AppWidgetManager
import android.content.Intent
import android.os.Bundle
import android.text.format.DateFormat
import android.view.View
import android.view.ViewGroup
import android.widget.BaseAdapter
import android.widget.ListView
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import java.util.Date

/**
 * Runs when a sticky-note widget is added from the launcher's widget tray, and asks the
 * one question that matters: which note?
 *
 * It used to skip the question and always create a new note, so there was no way at all
 * to put an EXISTING sticky on the home screen from the place you would naturally look
 * for it. The notes you already have are the list now, with "write a new one" at the top.
 */
class NoteWidgetConfigActivity : AppCompatActivity() {

    private var appWidgetId = AppWidgetManager.INVALID_APPWIDGET_ID
    private var notes: List<NoteItem> = emptyList()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        appWidgetId = intent.getIntExtra(
            AppWidgetManager.EXTRA_APPWIDGET_ID, AppWidgetManager.INVALID_APPWIDGET_ID
        )
        setResult(Activity.RESULT_CANCELED)  // backing out = widget not placed

        val store = Stores.forContext(this)
        if (store == null) {
            Toast.makeText(this, "Open the app and pick your vault folder first.", Toast.LENGTH_LONG).show()
            finish(); return
        }

        setContentView(R.layout.activity_widget_config)
        val list = findViewById<ListView>(R.id.config_list)
        val status = findViewById<TextView>(R.id.config_status)
        status.text = "Loading your notes…"

        // Vault scans and Joplin API calls alike are not the main thread's job.
        Thread {
            var error: String? = null
            val found = try { store.listNotes() }
                        catch (e: JoplinApiError) { error = e.message; emptyList() }
                        catch (e: Exception) { emptyList<NoteItem>() }
            val scanned = found.sortedByDescending { it.modified }
            runOnUiThread {
                if (isFinishing || isDestroyed) return@runOnUiThread
                notes = scanned
                status.text = if (error != null) {
                    "$error Only 'write a new note' will work right now."
                } else {
                    "Which note should this widget show?"
                }
                list.adapter = Choices()
                list.setOnItemClickListener { _, _, position, _ ->
                    if (position == 0) newNote() else bind(notes[position - 1].key)
                }
            }
        }.start()
    }

    private fun newNote() {
        @Suppress("DEPRECATION")
        startActivityForResult(Intent(this, EditorActivity::class.java), REQ_NEW_NOTE)
    }

    private fun bind(key: String) {
        Settings.setWidgetNote(this, appWidgetId, key)
        NoteWidgetProvider.render(this, AppWidgetManager.getInstance(this), appWidgetId)
        PhoneHome.sync(this)
        setResult(Activity.RESULT_OK, Intent().putExtra(AppWidgetManager.EXTRA_APPWIDGET_ID, appWidgetId))
        finish()
    }

    @Deprecated("startActivityForResult is fine for this one-shot config handoff")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode != REQ_NEW_NOTE) return
        val path = data?.getStringExtra(EXTRA_NOTE_PATH)
        // Nothing written means no note was created, so there is nothing to show and the
        // placement is cancelled rather than leaving an empty square on the home screen.
        if (resultCode == Activity.RESULT_OK && path != null) bind(path)
        else { setResult(Activity.RESULT_CANCELED); finish() }
    }

    /** "Write a new one", then every note you already have, most recent first. */
    private inner class Choices : BaseAdapter() {
        override fun getCount() = notes.size + 1
        override fun getItem(p: Int): Any = if (p == 0) "new" else notes[p - 1]
        override fun getItemId(p: Int) = p.toLong()

        override fun getView(p: Int, convertView: View?, parent: ViewGroup?): View {
            val v = convertView ?: layoutInflater.inflate(R.layout.row_note, parent, false)
            val title = v.findViewById<TextView>(R.id.row_title)
            val date = v.findViewById<TextView>(R.id.row_date)
            // The row's button belongs to the app's own list, where it puts a note on the
            // home screen. Here the whole row already IS that choice.
            v.findViewById<View>(R.id.row_pin).visibility = View.GONE

            if (p == 0) {
                title.text = "＋  Write a new note"
                date.text = "opens the editor, then shows it here"
            } else {
                val note = notes[p - 1]
                title.text = note.title
                date.text = DateFormat.format("MMM d, yyyy", Date(note.modified))
            }
            return v
        }
    }

    companion object { private const val REQ_NEW_NOTE = 1 }
}
