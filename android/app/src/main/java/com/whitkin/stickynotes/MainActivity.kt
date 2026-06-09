package com.whitkin.stickynotes

import android.Manifest
import android.app.Activity
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.Environment
import android.provider.DocumentsContract
import android.provider.Settings as AndroidSettings
import android.text.format.DateFormat
import android.view.View
import android.view.ViewGroup
import android.widget.BaseAdapter
import android.widget.Button
import android.widget.EditText
import android.widget.ListView
import android.widget.TextView
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import java.io.File
import java.util.Date

class MainActivity : AppCompatActivity() {

    private lateinit var status: TextView
    private lateinit var list: ListView
    private lateinit var pathField: EditText
    private var notes: List<StickyNote> = emptyList()

    private val pickFolder = registerForActivityResult(ActivityResultContracts.StartActivityForResult()) { res ->
        if (res.resultCode == Activity.RESULT_OK) {
            res.data?.data?.let { uri ->
                treeUriToPath(uri)?.let {
                    Settings.setVaultPath(this, it)
                    Toast.makeText(this, "Vault: $it", Toast.LENGTH_LONG).show()
                    refresh()
                } ?: Toast.makeText(this, "Couldn't resolve that folder to a path — type it manually.", Toast.LENGTH_LONG).show()
            }
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)
        status = findViewById(R.id.tv_status)
        list = findViewById(R.id.list)
        pathField = findViewById(R.id.et_path)

        findViewById<Button>(R.id.btn_permission).setOnClickListener { requestAllFiles() }
        findViewById<Button>(R.id.btn_pick).setOnClickListener {
            pickFolder.launch(Intent(Intent.ACTION_OPEN_DOCUMENT_TREE))
        }
        findViewById<Button>(R.id.btn_save_path).setOnClickListener {
            val p = pathField.text.toString().trim()
            if (p.isNotEmpty() && File(p).isDirectory) { Settings.setVaultPath(this, p); refresh() }
            else Toast.makeText(this, "Not a folder: $p", Toast.LENGTH_LONG).show()
        }
        findViewById<Button>(R.id.btn_new).setOnClickListener {
            startActivity(Intent(this, EditorActivity::class.java))
        }

        list.setOnItemClickListener { _, _, pos, _ ->
            startActivity(Intent(this, EditorActivity::class.java)
                .putExtra(EXTRA_NOTE_PATH, notes[pos].file.absolutePath))
        }
    }

    override fun onResume() { super.onResume(); refresh() }

    private fun hasStorage(): Boolean =
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) Environment.isExternalStorageManager()
        else ActivityCompat.checkSelfPermission(this, Manifest.permission.READ_EXTERNAL_STORAGE) == PackageManager.PERMISSION_GRANTED

    private fun requestAllFiles() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            startActivity(Intent(AndroidSettings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION,
                Uri.parse("package:$packageName")))
        } else {
            ActivityCompat.requestPermissions(this,
                arrayOf(Manifest.permission.READ_EXTERNAL_STORAGE, Manifest.permission.WRITE_EXTERNAL_STORAGE), 1)
        }
    }

    private fun refresh() {
        val vault = Settings.vaultDir(this)
        val storageOk = hasStorage()
        val vaultOk = vault != null && vault.isDirectory
        val base = buildString {
            append(if (storageOk) "✓ Storage access granted\n" else "✗ Tap 'Grant storage access'\n")
            append(if (vaultOk) "✓ Vault: ${vault?.absolutePath}" else "✗ Pick your vault folder")
        }
        if (!(storageOk && vaultOk)) {
            status.text = base
            notes = emptyList(); list.adapter = NotesAdapter(); return
        }
        status.text = "$base\n… loading notes"
        // Scan off the main thread — the vault can hold thousands of files.
        Thread {
            val scanned = try { VaultStore(vault!!).listNotes() } catch (e: Exception) { emptyList() }
            try { PhoneHome.sync(this@MainActivity) } catch (_: Exception) {}
            runOnUiThread {
                if (isFinishing || isDestroyed) return@runOnUiThread
                notes = scanned
                list.adapter = NotesAdapter()
                status.text = "$base  (${scanned.size} notes)"
            }
        }.start()
    }

    private inner class NotesAdapter : BaseAdapter() {
        override fun getCount() = notes.size
        override fun getItem(p: Int) = notes[p]
        override fun getItemId(p: Int) = p.toLong()
        override fun getView(p: Int, convertView: View?, parent: ViewGroup?): View {
            val v = convertView ?: layoutInflater.inflate(R.layout.row_note, parent, false)
            val note = notes[p]
            v.findViewById<TextView>(R.id.row_title).text = note.title
            v.findViewById<TextView>(R.id.row_date).text =
                DateFormat.format("MMM d, yyyy", Date(note.modified))
            v.findViewById<Button>(R.id.row_pin).setOnClickListener {
                WidgetPins.requestPin(this@MainActivity, note.file.absolutePath)
            }
            return v
        }
    }

    /** Best-effort conversion of a SAF tree URI to a filesystem path (works with All-files access). */
    private fun treeUriToPath(uri: Uri): String? {
        return try {
            val docId = DocumentsContract.getTreeDocumentId(uri)
            val parts = docId.split(":", limit = 2)
            val type = parts[0]
            val rel = parts.getOrElse(1) { "" }
            if (type.equals("primary", true)) {
                val base = Environment.getExternalStorageDirectory().absolutePath
                if (rel.isEmpty()) base else "$base/$rel"
            } else {
                "/storage/$type" + if (rel.isEmpty()) "" else "/$rel"
            }
        } catch (e: Exception) { null }
    }
}
