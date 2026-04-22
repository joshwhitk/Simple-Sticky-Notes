# Development

## Environment

Current prototype assumptions:

- Windows
- Python 3.14+
- `Pillow` for icon loading and packaging
- `pystray` for the Windows tray icon and background-app controls

The current runtime uses Tkinter plus a small tray dependency, along with native Windows scripting for shortcut creation.

## Running Locally

```powershell
python main.py
```

Create a new note directly:

```powershell
python main.py --new-note
```

Install Windows integration:

```powershell
python main.py --install-windows-integration
```

Build the packaged app and installer:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File installer\build.ps1
```

## Moving The Repo

The app code is portable across workspace moves because project-relative paths are derived from the current file locations at runtime.

After moving the repo folder, rebuild the Windows shortcuts so the desktop and startup launchers stop pointing at the old path:

```powershell
python main.py --install-windows-integration
```

If you have an older app process running from the previous location, stop it before relaunching from the new folder.

## Tests

Run the current unit tests:

```powershell
python -m unittest -v
```

Current automated coverage includes storage behavior, menu regression cases, runtime recovery markers, and Obsidian URI generation because those parts are deterministic and safe to automate.

## Repo Conventions

- Keep `STATUS.MD` updated while working.
- Log confirmed bugs in `bugs.md`.
- Add durable tests for repeated bugs in `regression_tests.md` and in code where practical.
- Prefer straightforward storage formats and inspectable files over opaque state.

## Next Development Priorities

- Validate the packaged installer end-to-end
- Add broader multi-monitor and power-event coverage
- Measure idle resource usage
