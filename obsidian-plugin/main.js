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
  default: () => OpenAsStickyPlugin
});
module.exports = __toCommonJS(main_exports);
var import_obsidian = require("obsidian");
var net = __toESM(require("net"));
var path = __toESM(require("path"));
var HOST = "127.0.0.1";
var PORT = 38473;
var TIMEOUT_MS = 1500;
var OpenAsStickyPlugin = class extends import_obsidian.Plugin {
  async onload() {
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
  }
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
        err ? reject(err) : resolve();
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
};
