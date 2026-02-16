# Album Printer

Desktop tool to load a folder of photos, crop to print ratio, apply lightweight edits, stamp date/date+time, and print to a photo printer (Epson ET-8550 workflow supported).

## Implemented features

- Folder-based image loading (`jpg`, `jpeg`, `png`, `webp`, `tif`, `tiff`)
- Per-image crop controls:
  - Ratios: `2:3`, `3:4`, `4:5`, `1:1`, `16:9`
  - `Landscape` / `Portrait`, zoom, and X/Y offsets
  - Reframe mode with drag on preview and live crop overlay box
- Basic editing: brightness slider (`50%` to `150%`)
- Date/time stamp overlay:
  - `None`, `Date`, `Date + Time`
  - `12h` or `24h`
  - Corner selection per orientation
  - Font, size, color, text direction
  - X/Y pixel offsets from selected corner
- Per-image date/time override (`Set Date/Time` / `Clear`)
- Image table sorting by clicking sortable column headers (toggle ascending/descending)
- Print actions: `Print Selected` and `Print All`
- Duplicate-print confirmation before printing already printed photos
- Per-image print status + recent print attempt history shown in UI and saved in folder metadata
- Print backends: `Auto`, `CUPS`, `Qt`, `IPP` with backend-specific settings
- GitHub Actions CI and tag-based release packaging

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .[dev]
PYTHONPATH=src python -m album_printer
```

## Pre-commit checks

This project uses [pre-commit](https://pre-commit.com/) for automatic quality checks.

```bash
source .venv/bin/activate
pre-commit install
pre-commit run --all-files
```

Configured hooks include:

- Syntax/config checks (`check-ast`, `check-yaml`, `check-toml`, `check-json`)
- Formatting/import order (`black`, `isort`, `ruff-format`)
- Linting and safe auto-fixes (`ruff --fix`, `flake8`)
- Hygiene checks (trailing whitespace, EOF newline, merge conflict markers, debug statements)

Formatting/lint configuration is aligned to Black's 88-char line length across Black, isort, Ruff, and Flake8.

## Make commands

```bash
make venv
make install-dev
make hooks
make lint
make fmt
make run
```

- `make lint` runs full pre-commit checks.
- `make fmt` runs Black + isort + Ruff formatting/fixes.

## VS Code debugging

Debug launch profiles are available in `.vscode/launch.json`:

- `Album Printer (module)`
- `Album Printer (file)`

Both run with `PYTHONPATH=src` in the integrated terminal.

## Build locally (PyInstaller)

```bash
source .venv/bin/activate
pyinstaller --noconfirm --clean --name album-printer --windowed --paths src --collect-data album_printer src/album_printer/main.py
```

Output bundle is in `dist/`:

- Linux/Windows: `dist/album-printer`
- macOS: `dist/album-printer.app`

## Print notes (Linux)

- Ensure CUPS is installed and running.
- Confirm ET-8550 is visible from system printing first.
- App printer list is sourced from Qt/CUPS discovery.

## GitHub Actions

- `.github/workflows/ci.yml`
  - Runs dev-builds on pull requests (and manual dispatch)
  - Builds on `ubuntu-latest`, `macos-latest`, and `windows-latest`
  - Uploads short-lived artifacts
- `.github/workflows/release.yml`
  - Triggers on tags matching `v*`
  - Tags containing `-alpha`, `-beta`, or `-rc` publish as prereleases
  - Plain tags like `v0.1.0` publish as stable releases
  - Builds Linux + macOS + Windows bundles
  - Publishes release artifacts to GitHub Release

## Current limitations

- No dedicated undo/redo for per-image crop/brightness/date changes.
- Print settings are still streamlined compared to full printer driver UIs.
- Unsigned packages for now (signing/notarization roadmap later).
- macOS users may need to allow the app in Gatekeeper on first launch.
- Windows users may see SmartScreen warnings until code signing is added.
