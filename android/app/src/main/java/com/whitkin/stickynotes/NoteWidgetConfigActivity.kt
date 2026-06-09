package com.whitkin.stickynotes

import android.app.Activity
import android.appwidget.AppWidgetManager
import android.content.Intent
import android.os.Bundle
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity

/**
 * Runs when a sticky-note widget is added from the launcher's widget tray.
 * Adding a widget = creating a NEW sticky note: this immediately opens the editor
 * for a fresh note, then binds the resulting note to the widget so it displays the
 * content. If the user writes nothing, the placement is cancelled (no empty widget).
 */
class NoteWidgetConfigActivity : AppCompatActivity() {

    private var appWidgetId = AppWidgetManager.INVALID_APPWIDGET_ID

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        appWidgetId = intent.getIntExtra(
            AppWidgetManager.EXTRA_APPWIDGET_ID, AppWidgetManager.INVALID_APPWIDGET_ID
        )
        setResult(Activity.RESULT_CANCELED)  // backing out = widget not placed

        if (Settings.vaultDir(this) == null) {
            Toast.makeText(this, "Open the app and pick your vault folder first.", Toast.LENGTH_LONG).show()
            finish(); return
        }
        // Adding the widget creates a brand-new sticky note.
        startActivityForResult(Intent(this, EditorActivity::class.java), REQ_NEW_NOTE)
    }

    @Deprecated("startActivityForResult is fine for this one-shot config handoff")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode != REQ_NEW_NOTE) return
        val path = data?.getStringExtra(EXTRA_NOTE_PATH)
        if (resultCode == Activity.RESULT_OK && path != null) {
            Settings.setWidgetNote(this, appWidgetId, path)
            NoteWidgetProvider.render(this, AppWidgetManager.getInstance(this), appWidgetId)
            PhoneHome.sync(this)
            setResult(Activity.RESULT_OK, Intent().putExtra(AppWidgetManager.EXTRA_APPWIDGET_ID, appWidgetId))
        } else {
            setResult(Activity.RESULT_CANCELED)
        }
        finish()
    }

    companion object { private const val REQ_NEW_NOTE = 1 }
}
