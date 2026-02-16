# Album Print Flow

Desktop tool to load a folder of photos, crop to print ratio, apply lightweight edits, stamp date/date+time and location, and print to a photo printer (Epson ET-8550 workflow supported).

## Implemented features

- **Source abstraction layer**: Pluggable architecture for loading images from multiple sources
  - Folder-based loading (`jpg`, `jpeg`, `png`, `webp`, `tif`, `tiff`)
  - **Google Photos integration** (OAuth2, album loading, automatic caching)
  - Stable asset IDs for cross-import metadata continuity
- Per-image crop controls:
  - Ratios: `2:3`, `3:4`, `4:5`, `1:1`, `16:9`
  - `Landscape` / `Portrait`, zoom, and X/Y offsets
  - Reframe mode with drag on preview and live crop overlay box
- Basic editing: brightness slider (`50%` to `150%`)
- **Date/time stamp overlay**:
  - `None`, `Date`, `Date + Time`
  - `12h` or `24h`
  - Corner selection per orientation
  - Font, size, color, text direction
  - X/Y pixel offsets from selected corner
- **Location stamp overlay** (independent from date stamp):
  - Optional second stamp for location data
  - Extracted from EXIF GPS coordinates
  - Separate corner and offset settings
  - Per-image enable/disable toggle
  - Automatic priority: Google metadata → EXIF GPS → none
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

## Source abstraction architecture

Album Print Flow uses a pluggable source architecture to support loading images from multiple sources:

### Current sources

- **FolderSource**: Loads images from local filesystem folders
- **GooglePhotosSource**: Loads images from Google Photos albums
  - OAuth2 authentication
  - Album listing and selection
  - Automatic photo caching
  - Location and datetime metadata extraction
  - See [GOOGLE_PHOTOS_SETUP.md](GOOGLE_PHOTOS_SETUP.md) for setup instructions

### Key components

- `SourceAsset`: Normalized representation of an image asset with:
  - `asset_id`: Stable unique identifier for metadata continuity
  - `display_name`: Human-readable name shown in UI
  - `local_path`: Path to cached/downloaded image file (required for rendering)
  - `datetime_hint`: Optional datetime metadata
  - `location`: Optional location string (GPS coordinates or place name)

- `SourceLoadResult`: Container for load operation results with:
  - `assets`: List of loaded SourceAsset objects
  - `source_id`: Identifier for the source type
  - `source_token`: Instance identifier for this specific load
  - `metadata_path`: Path for storing source-specific metadata

- `SourceAdapter`: Base interface for implementing new sources
- `SourceRegistry`: Central registry for discovering and using adapters

### Location metadata

Location data is extracted with the following priority:
1. Google Photos metadata (when Google Photos source is used)
2. EXIF GPS coordinates from image files
3. None (if no location data available)

The location is displayed as GPS coordinates (latitude, longitude) and can be optionally stamped on images using the location stamp feature.

## Location stamp feature

Location stamps provide a second independent stamp overlay for displaying location data:

- **Separate configuration**: Independent corner, offset, and style settings from date stamp
- **Per-image control**: Enable/disable toggle for each image (no manual text editing)
- **Rendering condition**: Location stamp appears only when:
  - Project-level location stamp is enabled
  - Per-image toggle is ON
  - Location data exists for the image
- **Data source**: Automatically extracted from EXIF GPS or Google Photos metadata

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

## Third-party attributions

- See `THIRD_PARTY_NOTICES.md` for bundled fonts/assets and source/license references.

## Project TODO

- See `TODO.md` for the current direct IPP borderless printing work checklist.
