package com.whitkin.stickynotes

import android.os.Bundle
import android.widget.Button
import android.widget.EditText
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import java.io.File

/** A lightweight sticky-note editor. Loads an existing note or starts a new one. */
class EditorActivity : AppCompatActivity() {

    private var file: File? = null
    private var pinOnSave = false
    private lateinit var editor: EditText

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_editor)
        editor = findViewById(R.id.editor_text)

        val vault = Settings.vaultDir(this)
        if (vault == null) {
            Toast.makeText(this, "Pick your vault folder first.", Toast.LENGTH_LONG).show()
            finish(); return
        }

        pinOnSave = intent.getBooleanExtra(EXTRA_PIN_ON_SAVE, false)
        intent.getStringExtra(EXTRA_NOTE_PATH)?.let { path ->
            val f = File(path)
            if (f.exists()) {
                file = f
                editor.setText(VaultStore(vault).readBody(f))
                editor.setSelection(editor.text.length)
            }
        }

        findViewById<Button>(R.id.save_button).setOnClickListener { save() }
        findViewById<Button>(R.id.delete_button).setOnClickListener { delete() }
    }

    private fun save() {
        val vault = Settings.vaultDir(this) ?: return
        val body = editor.text.toString()
        val saved = VaultStore(vault).saveNote(file, body)
        if (saved == null) {
            Toast.makeText(this, "Empty note discarded.", Toast.LENGTH_SHORT).show()
            finish(); return
        }
        file = saved
        WidgetUpdater.updateAll(this)
        if (pinOnSave) {
            WidgetPins.requestPin(this, saved.absolutePath)
            pinOnSave = false
        }
        Toast.makeText(this, "Saved.", Toast.LENGTH_SHORT).show()
        finish()
    }

    private fun delete() {
        val vault = Settings.vaultDir(this) ?: return
        file?.let { VaultStore(vault).deleteNote(it) }
        WidgetUpdater.updateAll(this)
        finish()
    }
}
