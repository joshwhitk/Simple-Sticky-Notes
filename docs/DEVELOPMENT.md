# Development

## Environment

Current prototype assumptions:

- Windows
- Python 3.14+
- Pillow available for icon generation

The current runtime uses the Python standard library plus native Windows scripting for shortcut creation.

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

## Tests

Run the current unit tests:

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
```

The initial test coverage is focused on storage and session-state logic because those parts are deterministic and safe to automate.

## Repo Conventions

- Keep `STATUS.MD` updated while working.
- Log confirmed bugs in `bugs.md`.
- Add durable tests for repeated bugs in `regression_tests.md` and in code where practical.
- Prefer straightforward storage formats and inspectable files over opaque state.

## Next Development Priorities

- Improve the standalone note window behavior
- Add better session restore coverage
- Add smoke-testable Windows integration behavior
- Package the app for easier installation
