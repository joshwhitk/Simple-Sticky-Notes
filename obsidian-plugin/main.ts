import { FileSystemAdapter, Menu, Notice, Plugin, TAbstractFile, TFile } from "obsidian";
import * as net from "net";
import * as path from "path";

// Matches simple_sticky_notes/single_instance.py (HOST, PORT).
const HOST = "127.0.0.1";
const PORT = 38473;
const TIMEOUT_MS = 1500;

export default class OpenAsStickyPlugin extends Plugin {
  async onload(): Promise<void> {
    // Command palette + hotkey-bindable action.
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

    // Right-click on a note (editor tab or file explorer).
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

    // Quick-access ribbon button for the active note.
    this.addRibbonIcon("sticky-note", "Open as sticky note", () => {
      const file = this.app.workspace.getActiveFile();
      if (file && file.extension === "md") void this.openAsSticky(file);
      else new Notice("Open a markdown note first.");
    });
  }

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
        err ? reject(err) : resolve();
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
}
