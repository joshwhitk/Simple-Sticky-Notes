import esbuild from "esbuild";

// Bundle main.ts -> main.js, leaving Obsidian/Electron/Node built-ins external
// (they're provided by the Obsidian runtime; isDesktopOnly lets us use `net`).
await esbuild.build({
  entryPoints: ["main.ts"],
  bundle: true,
  external: ["obsidian", "electron", "net", "path", "fs", "os"],
  format: "cjs",
  target: "es2018",
  platform: "node",
  logLevel: "info",
  sourcemap: false,
  outfile: "main.js",
});
