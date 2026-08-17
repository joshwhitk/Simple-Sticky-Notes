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
import androidx.activity.OnBackPressedCallback
import androidx.appcompat.app.AppCompatActivity
import androidx.core.view.OnReceiveContentListener
import androidx.core.view.ViewCompat
import java.io.File
import java.util.concurrent.Executors
import java.util.concurrent.atomic.AtomicReference

/**
 * A sticky-note editor that AUTOSAVES as you type — no Save button, no Delete.
 * Writes are debounced while typing and flushed on pause (back/home) and on
 * finish, so a note can never be lost by forgetting to save. On finish it reports
 * the resulting note key via setResult, which the widget-config flow uses to bind
 * a freshly created note to its widget (other callers simply ignore the result).
 *
 * Works against whichever backend is active: vault files exactly as before
 * (synchronous saves, unchanged bytes on disk), or Joplin, whose saves are
 * network calls and therefore run in order on a single background worker.
 */
class EditorActivity : AppCompatActivity() {

    // The note's identity under the active backend: an absolute file path, or
    // "joplin:<id>". Atomic because the Joplin save worker assigns it (from the
    // POST response) while the UI thread reads it for results and pin requests.
    private val noteKey = AtomicReference<String?>(null)
    private var pinOnSave = false   // set by the Spawn widget: pin a Sticky Note widget on leave
    private var pinned = false
    private lateinit var editor: EditText
    private lateinit var store: NoteStore
    private var joplin = false
    private var vault: File? = null          // still used for pasted-image attachments
    private var loadedOk = false             // guards against overwriting a note we failed to load
    private var suppressAutosave = false     // the async load's setText must not trigger a save
    private var saveErrorShown = false       // one toast per offline streak, not one per keystroke
    @Volatile private var lastSavedBody: String? = null

    private val autosave = Handler(Looper.getMainLooper())
    private val autosaveRunnable = Runnable { persist() }
    // Joplin saves stay ordered on this single worker; shutdown() in onDestroy
    // lets anything already queued finish writing.
    private val saveExecutor = Executors.newSingleThreadExecutor()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_editor)
        editor = findViewById(R.id.editor_text)

        joplin = Settings.backend(this) == Stores.BACKEND_JOPLIN
        vault = Settings.vaultDir(this)
        val s = Stores.forContext(this)
        if (s == null) {
            Toast.makeText(this, "Pick your vault folder first.", Toast.LENGTH_LONG).show()
            finish(); return
        }
        store = s

        pinOnSave = intent.getBooleanExtra(EXTRA_PIN_ON_SAVE, false)

        // Back is the deliberate "I'm done" gesture, and it is the last moment this
        // activity is still the foreground one. That matters: Android drops a pin request
        // from an app already in the background, so asking from onPause — which is where
        // the spawn flow used to ask — meant the launcher's "add to home screen" prompt
        // never appeared and the Spawn widget looked like it did nothing at all.
        onBackPressedDispatcher.addCallback(this, object : OnBackPressedCallback(true) {
            override fun handleOnBackPressed() {
                // Wait for the save to settle (a network round-trip on Joplin) while this
                // activity is still foreground — Android drops pin requests from an app
                // already in the background, see the note below about onPause.
                persistThen {
                    if (pinOnSave && !pinned) {
                        val key = noteKey.get()
                        if (key != null) {
                            pinned = true
                            WidgetPins.requestPin(this@EditorActivity, key)
                        } else {
                            // Nothing typed, so nothing was written. Say so, rather than
                            // leaving him to wonder what the button did.
                            Toast.makeText(this@EditorActivity,
                                "Nothing typed, so no note was spawned.", Toast.LENGTH_SHORT).show()
                        }
                    }
                    isEnabled = false
                    finish()
                }
            }
        })
        val startKey = intent.getStringExtra(EXTRA_NOTE_PATH)
        if (startKey != null) loadNote(startKey) else loadedOk = true

        editor.addTextChangedListener(object : TextWatcher {
            override fun beforeTextChanged(s: CharSequence?, a: Int, b: Int, c: Int) {}
            override fun onTextChanged(s: CharSequence?, a: Int, b: Int, c: Int) {}
            override fun afterTextChanged(s: Editable?) {
                if (suppressAutosave) return
                autosave.removeCallbacks(autosaveRunnable)
                autosave.postDelayed(autosaveRunnable, AUTOSAVE_DELAY_MS)
            }
        })

        // Accept pasted images (long-press → Paste, or keyboard clipboard): save them
        // to the vault's _attachments folder and insert an Obsidian ![[name]] embed.
        ViewCompat.setOnReceiveContentListener(editor, arrayOf("image/*"), imageReceiver)
    }

    /** Puts the note's body in the editor. Files: synchronous, exactly as before. Joplin: background fetch with cache fallback. */
    private fun loadNote(key: String) {
        if (!joplin) {
            val f = File(key)
            if (f.exists()) {
                noteKey.set(key)
                editor.setText(store.readBody(key))
                editor.setSelection(editor.text.length)
            }
            loadedOk = true
            return
        }
        noteKey.set(key)
        // Until the body arrives, typing (and therefore saving) is off — a save
        // now would overwrite the remote note with an empty body.
        editor.isEnabled = false
        Thread {
            var fromCache = false
            val body = try {
                store.readBody(key)
            } catch (e: Exception) {
                fromCache = true
                (store as? JoplinStore)?.cachedNote(key)?.body
            }
            runOnUiThread {
                if (isFinishing || isDestroyed) return@runOnUiThread
                if (body == null) {
                    Toast.makeText(this,
                        "Couldn't load the note: Joplin is unreachable and there is no cached copy.",
                        Toast.LENGTH_LONG).show()
                    return@runOnUiThread
                }
                if (fromCache) {
                    Toast.makeText(this, "Joplin unreachable — editing the cached copy.", Toast.LENGTH_LONG).show()
                }
                suppressAutosave = true
                editor.setText(body)
                editor.setSelection(editor.text.length)
                suppressAutosave = false
                lastSavedBody = if (fromCache) null else body
                editor.isEnabled = true
                loadedOk = true
            }
        }.start()
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
        // Attachments live in the vault under either backend (the desktop app does
        // the same on its Joplin backend), so pasting an image needs the vault folder.
        val v = vault
        if (v == null) {
            Toast.makeText(this, "Pasting images needs the vault folder — pick it in the app first.", Toast.LENGTH_LONG).show()
            return false
        }
        return try {
            val bytes = contentResolver.openInputStream(uri)?.use { it.readBytes() } ?: return false
            val name = VaultStore(v).saveAttachment(ext, bytes)
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
    private fun persist() = persistThen(null)

    /**
     * Saves, then runs [after] on the UI thread once the save has settled. File
     * saves are synchronous, exactly the old behavior. Joplin saves run on the
     * background worker because they are network calls; failures show one toast
     * and keep the text in the editor, so nothing is lost while offline.
     */
    private fun persistThen(after: (() -> Unit)?) {
        autosave.removeCallbacks(autosaveRunnable)
        val body = editor.text.toString()
        val existing = noteKey.get()
        if (existing == null && body.isBlank()) { after?.invoke(); return }  // don't create an empty note

        if (!joplin) {
            val saved = try {
                store.saveNote(existing, body)
            } catch (e: Exception) {
                Toast.makeText(this, "Save failed: ${e.message}", Toast.LENGTH_LONG).show()
                null
            }
            if (saved != null) {
                noteKey.set(saved)
                WidgetUpdater.updateAll(this)
            }
            after?.invoke()
            return
        }

        // Joplin: never overwrite a note whose body we failed to load, and skip
        // the round-trip when nothing changed since the last successful save.
        if (existing != null && !loadedOk) { after?.invoke(); return }
        if (existing != null && body == lastSavedBody) { after?.invoke(); return }
        saveExecutor.execute {
            // The worker re-reads the key it last wrote, so a queued pair of saves
            // for a brand-new note becomes one POST then one PUT, never two POSTs.
            val current = noteKey.get()
            val result = try {
                store.saveNote(current, body)
            } catch (e: Exception) {
                runOnUiThread {
                    if (!isDestroyed && !saveErrorShown) {
                        saveErrorShown = true
                        Toast.makeText(applicationContext,
                            "Save failed — ${e.message}", Toast.LENGTH_LONG).show()
                    }
                    after?.invoke()
                }
                return@execute
            }
            if (result != null) {
                noteKey.set(result)
                lastSavedBody = body
            }
            runOnUiThread {
                saveErrorShown = false
                WidgetUpdater.updateAll(applicationContext)
                after?.invoke()
            }
        }
    }

    override fun onPause() {
        super.onPause()
        persist()
        // Fallback for leaving by Home rather than Back. The platform often refuses a
        // pin request from here because we are already backgrounded — the reliable path
        // is the back-press callback in onCreate.
        val key = noteKey.get()
        if (pinOnSave && !pinned && key != null) {
            pinned = true
            WidgetPins.requestPin(this, key)
        }
    }

    override fun finish() {
        persist()  // files: latest text is on disk now; Joplin: best-effort enqueue (the back path already awaited it)
        val key = noteKey.get()
        val data = Intent()
        key?.let { data.putExtra(EXTRA_NOTE_PATH, it) }
        setResult(if (key != null) Activity.RESULT_OK else Activity.RESULT_CANCELED, data)
        super.finish()
    }

    override fun onDestroy() {
        autosave.removeCallbacks(autosaveRunnable)
        saveExecutor.shutdown()  // queued Joplin saves still run to completion
        super.onDestroy()
    }

    companion object {
        private const val AUTOSAVE_DELAY_MS = 500L
    }
}
