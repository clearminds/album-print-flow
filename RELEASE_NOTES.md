# Album Print Flow — Release Notes

## v1.0.0 (2026-03-01)

First stable release of Album Print Flow.

### Highlights

- Linux-first desktop app for loading, preparing, and printing photo sets.
- Flexible crop workflow with common print ratios (`2:3`, `3:4`, `4:5`, `1:1`, `16:9`), orientation controls, zoom, and XY offsets.
- Reframe mode with drag-based positioning and live preview overlay.
- Lightweight image adjustment with per-photo brightness control.
- Date/time stamping with configurable format (`Date`, `Date + Time`), clock mode (`12h`/`24h`), font, color, direction, corner placement, and XY offsets.
- Optional location stamping from source metadata/EXIF with coordinate formatting options (`Best Available`, `Lat/Lon`, `DMS`).

### Sources

- Local folder source with support for common image/photo formats:
  - `jpg`, `jpeg`, `png`, `webp`, `tif`, `tiff`, `heic`, `heif`
  - common RAW formats (via `rawpy`)
- Google Photos source via OAuth + Picker flow:
  - account sign-in and account switching
  - album/media selection in browser picker
  - local cache + metadata continuity
- Google Photos shared album URL source (`photos.app.goo.gl` / `photos.google.com`) with cached imports.

### Printing & Job Management

- Print actions for `Print Selected` and `Print All`.
- Duplicate-print confirmation for already printed photos.
- Per-photo print state and history persisted in metadata.
- Per-photo actions: ignore in batch print, mark printed, clear failed logs, print again.
- `Print All` targets only photos that are not ignored and not already marked/recorded as printed.
- Multiple print backends: `Auto`, `CUPS`, `Qt`, and `IPP`.

### Platform & Packaging

- Project version: `1.0.0`.
- Python baseline: `>=3.11`.
- Cross-platform build/release workflows configured for Linux, macOS, and Windows artifacts.

### Known Limitations (v1.0.0)

- Google Photos Picker currently emphasizes recent/search flows rather than explicit album-tab browsing.
- Location stamp currently renders coordinate text only (no reverse-geocoded place names).
- IPP direct borderless printing may require printer/profile-specific tuning; CUPS/Qt backends remain available.

### Notes

- This is the initial public stable release.
- For setup and operational details, see:
  - `docs/index.md`
  - `docs/google-photos-setup.md`
