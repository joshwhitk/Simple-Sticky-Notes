import {
  App,
  FileSystemAdapter,
  Menu,
  Notice,
  Plugin,
  PluginSettingTab,
  Setting,
  TAbstractFile,
  TFile,
} from "obsidian";
import * as net from "net";
import * as path from "path";

// Matches simple_sticky_notes/single_instance.py (HOST, PORT).
const HOST = "127.0.0.1";
const PORT = 38473;
const TIMEOUT_MS = 1500;

const MAX_TITLE_WORDS = 10;
const MAX_FILE_STEM_LENGTH = 80;
const AUTO_TITLE_DEBOUNCE_MS = 800;
// Obsidian's default new-note names: "Untitled", "Untitled 1", ...
const UNTITLED_RE = /^Untitled(?: \d+)?$/;

interface SSNSettings {
  autoTitle: boolean;
}
const DEFAULT_SETTINGS: SSNSettings = { autoTitle: true };

// ---- Title/filename rules (ported from simple_sticky_notes/storage.py) ----

function stripFrontmatter(content: string): string {
  const lines = content.split(/\r?\n/);
  if (lines.length && lines[0].trim() === "---") {
    for (let i = 1; i < lines.length; i++) {
      if (lines[i].trim() === "---") return lines.slice(i + 1).join("\n");
    }
  }
  return content;
}

function firstNonblankLine(text: string): string {
  for (const line of text.split(/\r?\n/)) {
    const s = line.trim();
    if (s) return s.replace(/^#+/, "").trim();
  }
  return "";
}

/** First line of the body -> a safe filename stem (no extension), deduped by the caller. */
export function fileStemFromFirstLine(body: string): string {
  const words = firstNonblankLine(stripFrontmatter(body))
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, MAX_TITLE_WORDS)
    .join(" ");
  if (!words) return "";
  // Strip the same characters as the desktop app: <>:"/\|?* and control chars.
  const cleaned = words
    .replace(/[<>:"/\\|?*-]/g, " ")
    .replace(/\s+/g, " ")
    .replace(/^[ .]+|[ .]+$/g, "");
  if (!cleaned) return "";
  return cleaned.slice(0, MAX_FILE_STEM_LENGTH).replace(/[ .]+$/g, "");
}

export default class SimpleStickyNotesPlugin extends Plugin {
  settings: SSNSettings = DEFAULT_SETTINGS;
  private titleTimers = new Map<string, number>();

  async onload(): Promise<void> {
    await this.loadSettings();

    // --- "Open as sticky note" ---
    this.addCommand({
      id: "open-as-sticky-note",
      name: "Open as sticky note",
      checkCallback: (checking: boolean): boolean => {
        const file = this.app.workspace.getActiveFile();
        if (!file || file.extension !== "md") return false;
        if (!checking) void this.openAsSticky(file);
        return true;
      },
    });

    this.registerEvent(
      this.app.workspace.on("file-menu", (menu: Menu, file: TAbstractFile) => {
        if (file instanceof TFile && file.extension === "md") {
          menu.addItem((item) =>
            item
              .setTitle("Open as sticky note")
              .setIcon("sticky-note")
              .onClick(() => void this.openAsSticky(file))
          );
        }
      })
    );

    this.addRibbonIcon("sticky-note", "Open as sticky note", () => {
      const file = this.app.workspace.getActiveFile();
      if (file && file.extension === "md") void this.openAsSticky(file);
      else new Notice("Open a markdown note first.");
    });

    // --- Auto-title Untitled notes from their first line ---
    this.registerEvent(
      this.app.vault.on("modify", (f) => {
        if (f instanceof TFile) this.scheduleAutoTitle(f);
      })
    );
    this.registerEvent(
      this.app.vault.on("create", (f) => {
        if (f instanceof TFile) this.scheduleAutoTitle(f);
      })
    );

    this.addSettingTab(new SSNSettingTab(this.app, this));
  }

  onunload(): void {
    for (const t of this.titleTimers.values()) window.clearTimeout(t);
    this.titleTimers.clear();
  }

  async loadSettings(): Promise<void> {
    this.settings = Object.assign({}, DEFAULT_SETTINGS, await this.loadData());
  }
  async saveSettings(): Promise<void> {
    await this.saveData(this.settings);
  }

  // ---- Open as sticky ----

  private async openAsSticky(file: TFile): Promise<void> {
    const adapter = this.app.vault.adapter;
    if (!(adapter instanceof FileSystemAdapter)) {
      new Notice("Sticky notes need a local (desktop) vault.");
      return;
    }
    const fullPath = path.join(adapter.getBasePath(), file.path);
    try {
      await this.send({ command: "open-as-sticky", path: fullPath });
      new Notice("Opened as sticky note");
    } catch (err) {
      new Notice("Simple Sticky Notes isn't running — start the desktop app and try again.");
    }
  }

  private send(payload: Record<string, unknown>): Promise<void> {
    return new Promise<void>((resolve, reject) => {
      const socket = net.createConnection({ host: HOST, port: PORT });
      socket.setTimeout(TIMEOUT_MS);
      let settled = false;
      const done = (err?: Error) => {
        if (settled) return;
        settled = true;
        socket.destroy();
        if (err) reject(err);
        else resolve();
      };
      socket.on("connect", () => {
        socket.write(JSON.stringify(payload), () => {
          socket.end();
          done();
        });
      });
      socket.on("timeout", () => done(new Error("timeout")));
      socket.on("error", (e: Error) => done(e));
    });
  }

  // ---- Auto-title ----

  private scheduleAutoTitle(file: TFile): void {
    if (!this.settings.autoTitle || file.extension !== "md") return;
    if (!UNTITLED_RE.test(file.basename)) return; // only auto-name fresh "Untitled" notes
    const prev = this.titleTimers.get(file.path);
    if (prev) window.clearTimeout(prev);
    this.titleTimers.set(
      file.path,
      window.setTimeout(() => {
        this.titleTimers.delete(file.path);
        void this.autoTitle(file);
      }, AUTO_TITLE_DEBOUNCE_MS)
    );
  }

  private async autoTitle(file: TFile): Promise<void> {
    if (!UNTITLED_RE.test(file.basename)) return; // a rename already happened
    let content: string;
    try {
      content = await this.app.vault.cachedRead(file);
    } catch {
      return;
    }
    const stem = fileStemFromFirstLine(content);
    if (!stem || UNTITLED_RE.test(stem)) return;
    const target = this.uniquePath(file.parent ? file.parent.path : "", stem, file);
    if (target === file.path) return;
    try {
      await this.app.fileManager.renameFile(file, target);
    } catch {
      /* name clash or file locked — leave it as-is */
    }
  }

  private uniquePath(folder: string, stem: string, current: TFile): string {
    const dir = folder && folder !== "/" ? folder + "/" : "";
    let candidate = `${dir}${stem}.md`;
    let n = 1;
    while (true) {
      const existing = this.app.vault.getAbstractFileByPath(candidate);
      if (!existing || existing === current) return candidate;
      const suffix = `-${n}`;
      const trimmed = stem.slice(0, MAX_FILE_STEM_LENGTH - suffix.length);
      candidate = `${dir}${trimmed}${suffix}.md`;
      n++;
    }
  }
}

class SSNSettingTab extends PluginSettingTab {
  constructor(app: App, private plugin: SimpleStickyNotesPlugin) {
    super(app, plugin);
  }
  display(): void {
    const { containerEl } = this;
    containerEl.empty();
    new Setting(containerEl)
      .setName("Auto-title new notes")
      .setDesc("When an 'Untitled' note gets a first line, rename it to that line (first 10 words).")
      .addToggle((t) =>
        t.setValue(this.plugin.settings.autoTitle).onChange(async (v) => {
          this.plugin.settings.autoTitle = v;
          await this.plugin.saveSettings();
        })
      );
  }
}
