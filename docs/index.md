# Album Print Flow

Desktop tool to load a folder of photos, crop to print ratio, apply lightweight edits, stamp date/date+time, and print to a photo printer (Epson ET-8550 workflow supported).

## Implemented features

- Folder-based image loading (`jpg`, `jpeg`, `png`, `webp`, `tif`, `tiff`, `heic`, `heif`, common RAW formats)
- Unified source loading via `Load ...` menu (source adapter architecture)
  - `Folder` source implemented
  - `Google Photos` source implemented (OAuth login, album select, image download/cache)
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
- Per-image location stamp toggle (`on/off` only; location value is metadata-driven)
- Optional location stamp (independent from date stamp):
  - Project-level mode: `Off` / `Coordinates`
  - Project-level format: `Best Available`, `Lat/Lon`, `DMS`
  - Separate corner selection per orientation
- Image table sorting by clicking sortable column headers (toggle ascending/descending)
- Print actions: `Print Selected` and `Print All`
- Duplicate-print confirmation before printing already printed photos
- Per-image print status + recent print attempt history shown in UI and saved in folder metadata
- Per-image print state actions:
  - `Ignore in Print All`
  - `Mark Printed`
  - `Clear Failed Logs`
  - `Print Again`
- `Print All` now targets only images that are not ignored and not already marked/recorded as printed
- Stable per-photo metadata key support for source-driven identities
- App-level source state JSON for cross-import continuity (`~/.config/album-print-flow/source_state.json`)
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

## Google Photos setup

Detailed setup guide: [Google Photos Setup](google-photos-setup.md)

1. Open Google Cloud Console and create/select a project.
2. Enable API: **Google Photos Picker API** for that project.
3. Configure OAuth consent screen:
  - Choose `External` (or your org default)
  - Fill required app fields
  - Add your Google account under test users (if app is in testing mode)
4. Create OAuth client credentials:
  - Go to **APIs & Services** -> **Credentials**
  - Click **Create Credentials** -> **OAuth client ID**
  - Application type: `Desktop app`
  - Download the JSON file
5. Put the JSON in one of these locations:
  - `~/.config/album-print-flow/google_client_secret.json` (recommended)
  - or set `ALBUM_PRINTER_GOOGLE_CLIENT_SECRET_FILE` to the JSON path.
6. In the app, use `Load ...` -> `Google Photos` and sign in when browser opens.
7. After successful sign-in, the OAuth token is cached for reuse:
  - OS keychain/secret manager when available
  - fallback file: `~/.config/album-print-flow/google_token.json`

If the client JSON is missing, the app now offers an import helper with:

- `Paste JSON` (paste the downloaded credentials directly)
- `Select JSON file...` (choose the downloaded file and save to config path)

Google Photos account management now supports multiple accounts from the load flow:

- First popup lists all added accounts for direct selection
- `Add account...`
- `Manage accounts...` (delete accounts here)

After account sign-in, the app opens Google Photos Picker in your browser so you can
select media from your library and return those selected items to the app.

Note: Picker currently shows recent/search flow rather than explicit album tabs,
so for album-based picking (including shared albums) use search by album title.

The app keeps account-specific token storage and account-scoped album contexts.

Credential file resolution order:

1. `ALBUM_PRINTER_GOOGLE_CLIENT_SECRET_FILE` (explicit override)
2. `~/.config/album-print-flow/google_client_secret.json`
3. Bundled app resource: `album_printer/oauth/google_client_secret.json`

### If you see “Google OAuth client file not found”

Use one of these two fixes:

1. Default location (recommended)

```bash
mkdir -p ~/.config/album-print-flow
cp /path/to/your/google-client-secret.json ~/.config/album-print-flow/google_client_secret.json
```

2. Custom location via environment variable

```bash
export ALBUM_PRINTER_GOOGLE_CLIENT_SECRET_FILE="/absolute/path/to/google-client-secret.json"
PYTHONPATH=src python -m album_printer
```

Checklist:

- Credential type must be `Desktop app` (not Web app).
- OAuth consent screen must be configured in Google Cloud Console.
- JSON file should contain client_id, client_secret, and auth/token URIs.

Notes:

- OAuth token is stored in OS keychain/secret manager when available, with fallback file cache at `~/.config/album-print-flow/google_token.json`.
- Google album cache is stored under `~/.cache/album-print-flow/google-photos/`.
- Cross-import Google photo continuity state is stored at `~/.config/album-print-flow/source_state.json`.
- To bundle default OAuth credentials for distribution, place the JSON at `src/album_printer/oauth/google_client_secret.json` before packaging.

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
- For desktop-portal integration, install desktop entry:
  - source file: `assets/linux/se.clearimnds.album-print-flow.desktop`
  - user install: `~/.local/share/applications/`
  - system install: `/usr/share/applications/`

## GitHub Actions

- `.github/workflows/ci.yml`
  - Runs dev-builds on pull requests (and manual dispatch)
  - Builds on `ubuntu-latest`, `macos-latest`, and `windows-latest`
  - Uploads short-lived artifacts
- `.github/workflows/release.yml`
  - Triggers on tags matching `v*`
  - Tags containing `-alpha`, `-beta`, or `-rc` publish as prereleases
  - Plain tags like `v1.0.0` publish as stable releases
  - Builds Linux + macOS + Windows bundles
  - Publishes release artifacts to GitHub Release

## Source abstraction architecture

Album Print Flow uses a pluggable source architecture to load images from multiple sources.

### Current sources

- **FolderSource**: Loads images from local filesystem folders.
- **GooglePhotosSource**: Loads images from Google Photos via Picker API selection flow.
  - OAuth2 authentication
  - Multiple account support (use/add/delete)
  - Album listing and selection
  - Automatic local photo caching
  - Metadata extraction (capture time + location coordinates)
  - Setup guide: [Google Photos Setup](google-photos-setup.md)

- **GooglePhotosAlbumUrlSource**: Loads shared album links (`photos.app.goo.gl` / `photos.google.com`).
  - Fetches album page HTML and extracts media base URLs (`lh3.googleusercontent.com/pw/...`)
  - Derives stable media keys from base URL SHA-256 prefix
  - Tries to infer capture time and GPS from nearby page content, then falls back to EXIF
  - Downloads/caches files locally and writes a manifest JSON for fast reloads

### Key components

- `SourceAsset`: normalized image asset model with:
  - `key`: stable metadata key (for continuity across re-imports)
  - `display_name`: human-readable name shown in UI
  - `local_path`: local file path used by render/print pipeline
  - `source_photo_id`: optional source-native photo identifier
  - `captured_at`: optional datetime hint from source metadata
  - `latitude` / `longitude`: optional location coordinates

- `SourceLoadResult`: source load container with:
  - `assets`: list of `SourceAsset` objects
  - `source_id` / `source_label`: source identity and display label
  - `context_id` / `context_label`: source context identity (for refresh)
  - `metadata_root`: local metadata root path for this source context
  - `is_new_context`: whether metadata context is newly created

- `SourceAdapter` (protocol): source interface for `load_via_ui(...)` and `refresh(...)`.
- `SourceRegistry`: registry used by app UI to discover and invoke adapters.

### Location metadata

Location data resolution priority in the app is:

1. Source asset location (`SourceAsset.latitude`/`longitude`)
2. Stored source location in folder metadata (`photos[*].source_location`)
3. EXIF GPS coordinates from image files
4. No location

Location is currently rendered as coordinate text (Lat/Lon or DMS based on settings).

## Google Photos Album URL: parsed data and JSON

The album URL loader does **not** use a public Google JSON endpoint. It requests album HTML and extracts data heuristically.

Implementation: [src/album_printer/sources/google_photos_album_url_source.py](src/album_printer/sources/google_photos_album_url_source.py)

### Data extracted from album HTML

- `album_title`: from `og:title` meta tag (fallback: page title / resolved URL)
- `base_urls`: list of media bases matching `https://lh3.googleusercontent.com/pw/...`
- `web_captured_at_map`: optional map `base_url -> ISO datetime` (searched near each media URL)
- `web_location_map`: optional map `base_url -> (latitude, longitude)` (searched near each media URL)

### Local JSON written by the loader

1. Loader state (bookmarks + recent):
   - Path: `~/.config/album-print-flow/google_album_url_state.json`
   - Top-level shape:

```json
{
  "version": 1,
  "bookmarks_by_account": {
    "<account-or-__default__>": [
      {
        "name": "Family Album",
        "url": "https://photos.app.goo.gl/...",
        "added_at": "2026-02-16T10:22:00",
        "last_loaded_at": "2026-02-16T10:35:12",
        "last_context_id": "https://photos.google.com/share/...",
        "last_asset_count": 128,
        "last_new_count": 3
      }
    ]
  },
  "recent_by_account": {
    "<account-or-__default__>": [
      {
        "url": "https://photos.app.goo.gl/...",
        "title": "Family Album",
        "context_id": "https://photos.google.com/share/...",
        "loaded_at": "2026-02-16T10:35:12",
        "asset_count": 128,
        "new_count": 3
      }
    ]
  }
}
```

2. Per-album manifest (download/cache index):
   - Path: `~/.cache/album-print-flow/google-photos-albums/<album-hash>/manifest.json`
   - Top-level shape:

```json
{
  "version": 1,
  "album_url": "https://photos.app.goo.gl/...",
  "resolved_url": "https://photos.google.com/share/...",
  "title": "Family Album",
  "last_sync_at": "2026-02-16T10:35:12",
  "last_sync_total": 128,
  "last_sync_new": 3,
  "last_sync_removed": 0,
  "last_sync_failed": 1,
  "activity": {
    "owner_name": "Daniel Yifter Eriksson",
    "participants": ["Daniel Yifter Eriksson"],
    "participant_count": 1,
    "participant_avatars": ["https://lh3.googleusercontent.com/a/..."],
    "activity_timestamp_count": 164,
    "activity_oldest_at": "2025-05-11T08:19:34+00:00",
    "activity_latest_at": "2026-02-15T10:42:17+00:00",
    "comments_ui_present": true,
    "embedded_activity_payload": true
  },
  "items": {
    "<media_key>": {
      "key": "8f1a...",
      "base_url": "https://lh3.googleusercontent.com/pw/...",
      "file_name": "8f1a....jpg",
      "order": 17,
      "last_seen_at": "2026-02-16T10:35:12",
      "download_variant": "download",
      "content_type": "image/jpeg",
      "captured_at": "2025-08-09T12:15:01",
      "latitude": 59.3293,
      "longitude": 18.0686
    }
  }
}
```

Notes for `activity`:
- It is **best-effort** and parsed from embedded page payload, not an official activity API.
- Field availability can change when Google changes page internals.
- It is intended for diagnostics/change hints, not strict schema guarantees.

### Data passed into app assets

Each loaded `SourceAsset` receives:

- `key` / `source_photo_id`: derived media key
- `display_name`: cached filename
- `local_path`: downloaded local file path
- `captured_at`: web hint or EXIF fallback
- `latitude` / `longitude`: web hint or EXIF fallback
- `source_data`:
  - `album_url`
  - `album_title`
  - `media_key`
  - `media_base_url`
  - `download_variant`
  - `content_type`

## Location stamp feature

Location stamp is a second, independent overlay from timestamp stamp.

- **Separate configuration**: independent mode/format/corner settings from timestamp settings.
- **Per-image control**: per-image on/off toggle (`Location stamp`) without manual location text editing.
- **Render conditions**: location stamp appears only when all are true:
  - project-level location mode is not `Off`
  - per-image location toggle is enabled
  - location data exists for the image
- **Data source**: source metadata first, then EXIF GPS fallback.

## Current limitations

- No dedicated undo/redo for per-image crop/brightness/date changes.
- Print settings are still streamlined compared to full printer driver UIs.
- Unsigned packages for now (signing/notarization roadmap later).
- macOS users may need to allow the app in Gatekeeper on first launch.
- Windows users may see SmartScreen warnings until code signing is added.
- RAW support depends on decoder availability for the specific camera format.

## Third-party attributions

- See [Third-Party Notices](third-party-notices.md) for bundled fonts/assets and source/license references.

## Project TODO

- See [Project TODO](project-todo.md) for the current direct IPP borderless printing work checklist.
