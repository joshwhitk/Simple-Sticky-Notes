"use strict";
var __create = Object.create;
var __defProp = Object.defineProperty;
var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
var __getOwnPropNames = Object.getOwnPropertyNames;
var __getProtoOf = Object.getPrototypeOf;
var __hasOwnProp = Object.prototype.hasOwnProperty;
var __export = (target, all) => {
  for (var name in all)
    __defProp(target, name, { get: all[name], enumerable: true });
};
var __copyProps = (to, from, except, desc) => {
  if (from && typeof from === "object" || typeof from === "function") {
    for (let key of __getOwnPropNames(from))
      if (!__hasOwnProp.call(to, key) && key !== except)
        __defProp(to, key, { get: () => from[key], enumerable: !(desc = __getOwnPropDesc(from, key)) || desc.enumerable });
  }
  return to;
};
var __toESM = (mod, isNodeMode, target) => (target = mod != null ? __create(__getProtoOf(mod)) : {}, __copyProps(
  // If the importer is in node compatibility mode or this is not an ESM
  // file that has been converted to a CommonJS file using a Babel-
  // compatible transform (i.e. "__esModule" has not been set), then set
  // "default" to the CommonJS "module.exports" for node compatibility.
  isNodeMode || !mod || !mod.__esModule ? __defProp(target, "default", { value: mod, enumerable: true }) : target,
  mod
));
var __toCommonJS = (mod) => __copyProps(__defProp({}, "__esModule", { value: true }), mod);

// main.ts
var main_exports = {};
__export(main_exports, {
  default: () => SimpleStickyNotesPlugin,
  fileStemFromFirstLine: () => fileStemFromFirstLine
});
module.exports = __toCommonJS(main_exports);
var import_obsidian = require("obsidian");
var net = __toESM(require("net"));
var path = __toESM(require("path"));
var HOST = "127.0.0.1";
var PORT = 38473;
var TIMEOUT_MS = 1500;
var MAX_TITLE_WORDS = 10;
var MAX_FILE_STEM_LENGTH = 80;
var AUTO_TITLE_DEBOUNCE_MS = 800;
var UNTITLED_RE = /^Untitled(?: \d+)?$/;
var DEFAULT_SETTINGS = { autoTitle: true };
function stripFrontmatter(content) {
  const lines = content.split(/\r?\n/);
  if (lines.length && lines[0].trim() === "---") {
    for (let i = 1; i < lines.length; i++) {
      if (lines[i].trim() === "---") return lines.slice(i + 1).join("\n");
    }
  }
  return content;
}
function firstNonblankLine(text) {
  for (const line of text.split(/\r?\n/)) {
    const s = line.trim();
    if (s) return s.replace(/^#+/, "").trim();
  }
  return "";
}
function fileStemFromFirstLine(body) {
  const words = firstNonblankLine(stripFrontmatter(body)).split(/\s+/).filter(Boolean).slice(0, MAX_TITLE_WORDS).join(" ");
  if (!words) return "";
  const cleaned = words.replace(/[<>:"/\\|?*-]/g, " ").replace(/\s+/g, " ").replace(/^[ .]+|[ .]+$/g, "");
  if (!cleaned) return "";
  return cleaned.slice(0, MAX_FILE_STEM_LENGTH).replace(/[ .]+$/g, "");
}
var SimpleStickyNotesPlugin = class extends import_obsidian.Plugin {
  constructor() {
    super(...arguments);
    this.settings = DEFAULT_SETTINGS;
    this.titleTimers = /* @__PURE__ */ new Map();
  }
  async onload() {
    await this.loadSettings();
    this.addCommand({
      id: "open-as-sticky-note",
      name: "Open as sticky note",
      checkCallback: (checking) => {
        const file = this.app.workspace.getActiveFile();
        if (!file || file.extension !== "md") return false;
        if (!checking) void this.openAsSticky(file);
        return true;
      }
    });
    this.registerEvent(
      this.app.workspace.on("file-menu", (menu, file) => {
        if (file instanceof import_obsidian.TFile && file.extension === "md") {
          menu.addItem(
            (item) => item.setTitle("Open as sticky note").setIcon("sticky-note").onClick(() => void this.openAsSticky(file))
          );
        }
      })
    );
    this.addRibbonIcon("sticky-note", "Open as sticky note", () => {
      const file = this.app.workspace.getActiveFile();
      if (file && file.extension === "md") void this.openAsSticky(file);
      else new import_obsidian.Notice("Open a markdown note first.");
    });
    this.registerEvent(
      this.app.vault.on("modify", (f) => {
        if (f instanceof import_obsidian.TFile) this.scheduleAutoTitle(f);
      })
    );
    this.registerEvent(
      this.app.vault.on("create", (f) => {
        if (f instanceof import_obsidian.TFile) this.scheduleAutoTitle(f);
      })
    );
    this.addSettingTab(new SSNSettingTab(this.app, this));
  }
  onunload() {
    for (const t of this.titleTimers.values()) window.clearTimeout(t);
    this.titleTimers.clear();
  }
  async loadSettings() {
    this.settings = Object.assign({}, DEFAULT_SETTINGS, await this.loadData());
  }
  async saveSettings() {
    await this.saveData(this.settings);
  }
  // ---- Open as sticky ----
  async openAsSticky(file) {
    const adapter = this.app.vault.adapter;
    if (!(adapter instanceof import_obsidian.FileSystemAdapter)) {
      new import_obsidian.Notice("Sticky notes need a local (desktop) vault.");
      return;
    }
    const fullPath = path.join(adapter.getBasePath(), file.path);
    try {
      await this.send({ command: "open-as-sticky", path: fullPath });
      new import_obsidian.Notice("Opened as sticky note");
    } catch (err) {
      new import_obsidian.Notice("Simple Sticky Notes isn't running \u2014 start the desktop app and try again.");
    }
  }
  send(payload) {
    return new Promise((resolve, reject) => {
      const socket = net.createConnection({ host: HOST, port: PORT });
      socket.setTimeout(TIMEOUT_MS);
      let settled = false;
      const done = (err) => {
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
      socket.on("error", (e) => done(e));
    });
  }
  // ---- Auto-title ----
  scheduleAutoTitle(file) {
    if (!this.settings.autoTitle || file.extension !== "md") return;
    if (!UNTITLED_RE.test(file.basename)) return;
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
  async autoTitle(file) {
    if (!UNTITLED_RE.test(file.basename)) return;
    let content;
    try {
      content = await this.app.vault.cachedRead(file);
    } catch (e) {
      return;
    }
    const stem = fileStemFromFirstLine(content);
    if (!stem || UNTITLED_RE.test(stem)) return;
    const target = this.uniquePath(file.parent ? file.parent.path : "", stem, file);
    if (target === file.path) return;
    try {
      await this.app.fileManager.renameFile(file, target);
    } catch (e) {
    }
  }
  uniquePath(folder, stem, current) {
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
};
var SSNSettingTab = class extends import_obsidian.PluginSettingTab {
  constructor(app, plugin) {
    super(app, plugin);
    this.plugin = plugin;
  }
  display() {
    const { containerEl } = this;
    containerEl.empty();
    new import_obsidian.Setting(containerEl).setName("Auto-title new notes").setDesc("When an 'Untitled' note gets a first line, rename it to that line (first 10 words).").addToggle(
      (t) => t.setValue(this.plugin.settings.autoTitle).onChange(async (v) => {
        this.plugin.settings.autoTitle = v;
        await this.plugin.saveSettings();
      })
    );
  }
};
// Annotate the CommonJS export names for ESM import in node:
0 && (module.exports = {
  fileStemFromFirstLine
});
