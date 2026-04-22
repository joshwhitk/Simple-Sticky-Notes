# Contributing

## Current State

This project is in active prototyping. Contributions are welcome, but the main priority is preserving the product direction:

- standalone Windows sticky-note runtime
- markdown note storage
- Obsidian-compatible file layout
- inspectable metadata

## Before Changing Code

- Read [docs/MRD.md](docs/MRD.md)
- Read [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- Check [STATUS.MD](STATUS.MD) for current priorities

## Working Norms

- Keep file formats simple and inspectable.
- Prefer code that is easy to debug on Windows.
- Avoid introducing a dependency that forces Obsidian to be the runtime.
- Add tests around deterministic storage/session logic when behavior changes.

## Reporting Bugs

- Use the GitHub bug report template
- Include:
  - Windows version
  - Python version
  - exact steps
  - expected behavior
  - actual behavior

## Feature Requests

- Explain how the feature fits or conflicts with the product constraints in [docs/MRD.md](docs/MRD.md)
