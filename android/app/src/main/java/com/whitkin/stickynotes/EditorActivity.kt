package com.whitkin.stickynotes

import android.app.Activity
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.text.Editable
import android.text.TextWatcher
import android.widget.EditText
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.core.view.OnReceiveContentListener
import androidx.core.view.ViewCompat
import java.io.File

/**
 * A sticky-note editor that AUTOSAVES as you type — no Save button, no Delete.
 * Writes are debounced while typing and flushed on pause (back/home) and on
 * finish, so a note can never be lost by forgetting to save. On finish it reports
 * the resulting note path via setResult, which the widget-config flow uses to bind
 * a freshly created note to its widget (other callers simply ignore the result).
 */
class EditorActivity : AppCompatActivity() {

    private var file: File? = null
    private lateinit var editor: EditText
    private lateinit var vault: File

    private val autosave = Handler(Looper.getMainLooper())
    private val autosaveRunnable = Runnable { persist() }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_editor)
        editor = findViewById(R.id.editor_text)

        val v = Settings.vaultDir(this)
        if (v == null) {
            Toast.makeText(this, "Pick your vault folder first.", Toast.LENGTH_LONG).show()
            finish(); return
        }
        vault = v

        intent.getStringExtra(EXTRA_NOTE_PATH)?.let { path ->
            val f = File(path)
            if (f.exists()) {
                file = f
                editor.setText(VaultStore(vault).readBody(f))
                editor.setSelection(editor.text.length)
            }
        }

        editor.addTextChangedListener(object : TextWatcher {
            override fun beforeTextChanged(s: CharSequence?, a: Int, b: Int, c: Int) {}
            override fun onTextChanged(s: CharSequence?, a: Int, b: Int, c: Int) {}
            override fun afterTextChanged(s: Editable?) {
                autosave.removeCallbacks(autosaveRunnable)
                autosave.postDelayed(autosaveRunnable, AUTOSAVE_DELAY_MS)
            }
        })

        // Accept pasted images (long-press → Paste, or keyboard clipboard): save them
        // to the vault's _attachments folder and insert an Obsidian ![[name]] embed.
        ViewCompat.setOnReceiveContentListener(editor, arrayOf("image/*"), imageReceiver)
    }

    private val imageReceiver = OnReceiveContentListener { _, payload ->
        // partition() returns an androidx.core.util.Pair (first = items with a URI).
        val split = payload.partition { item -> item.uri != null }
        val withUris = split.first
        if (withUris != null) {
            val clip = withUris.clip
            for (i in 0 until clip.itemCount) {
                clip.getItemAt(i).uri?.let { uri -> insertImageFromUri(uri) }
            }
        }
        split.second  // hand any non-image (text) content back for normal pasting
    }

    /** Copy an image content-URI into the vault and embed it; returns false if not an image. */
    private fun insertImageFromUri(uri: Uri): Boolean {
        val type = contentResolver.getType(uri) ?: ""
        if (!type.startsWith("image/")) return false
        val ext = when (type) {
            "image/jpeg" -> "jpg"
            "image/gif" -> "gif"
            "image/webp" -> "webp"
            else -> "png"
        }
        return try {
            val bytes = contentResolver.openInputStream(uri)?.use { it.readBytes() } ?: return false
            val name = VaultStore(vault).saveAttachment(ext, bytes)
            val pos = editor.selectionStart.coerceIn(0, editor.text.length)
            editor.text.insert(pos, "![[$name]]\n")
            persist()
            true
        } catch (e: Exception) {
            Toast.makeText(this, "Couldn't paste image: ${e.message}", Toast.LENGTH_LONG).show()
            false
        }
    }

    /** Create-or-update the note from the current text. Silent and safe to call often. */
    private fun persist() {
        autosave.removeCallbacks(autosaveRunnable)
        val body = editor.text.toString()
        if (file == null && body.isBlank()) return  // don't create an empty note
        val saved = try {
            VaultStore(vault).saveNote(file, body)
        } catch (e: Exception) {
            Toast.makeText(this, "Save failed: ${e.message}", Toast.LENGTH_LONG).show()
            null
        } ?: return
        file = saved
        WidgetUpdater.updateAll(this)
    }

    override fun onPause() {
        super.onPause()
        persist()
    }

    override fun finish() {
        persist()  // ensure the latest text is on disk and `file` is resolved first
        val data = Intent()
        file?.let { data.putExtra(EXTRA_NOTE_PATH, it.absolutePath) }
        setResult(if (file != null) Activity.RESULT_OK else Activity.RESULT_CANCELED, data)
        super.finish()
    }

    override fun onDestroy() {
        autosave.removeCallbacks(autosaveRunnable)
        super.onDestroy()
    }

    companion object {
        private const val AUTOSAVE_DELAY_MS = 500L
    }
}
