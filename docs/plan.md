# Implementation plan

## Phase 1 (done)

- Core desktop app scaffold (Python + PySide6)
- Folder import + image list
- Crop ratios with orientation mode
- Per-image crop zoom + X/Y offsets
- Reframe crop with drag + preview overlay
- Brightness slider
- Date/date+time stamp (12h/24h)
- Stamp corner controls + X/Y corner offsets
- Print-all flow with workflow-level paper settings
- Print Selected action alongside Print All
- Duplicate-print confirmation
- Per-image print status and print-attempt history in UI
- Column-header sorting (asc/desc)
- GitHub Actions CI + release packaging

## Phase 2 (next)

- Improve output rendering consistency (preview vs print)
- Expand and validate printer capability mappings (media/type/quality) across more models
- Better print history browsing/filtering for large folders

## Phase 2A (next): Google Photos Album URL source

- Add a new load option: `Google Photos Album URL`
- Accept shared album URLs and resolve them to a stable source context ID
- Download media with metadata-preserving variants (`=d` first) and keep original bytes where possible
- Build source metadata sidecars per asset so date/location are read from original source data
- Integrate source in existing load/refresh flow and source-state persistence
- Add clear warning text when location metadata is missing on downloaded bytes

### Phase 2A.1 (MVP)

- Support public/shared album URLs entered manually in a dialog
- Load album assets into cache and render in current workflow
- Refresh re-checks album and adds newly discovered items
- Keep implementation read-only and resilient to partial failures

### Phase 2A.2

- Add bookmarked album list (name + URL + last sync)
- Add quick-load and remove bookmark actions
- Track per-album sync summary (new/unchanged/failed)

### Phase 2A.3

- Add optional background monitor/polling for bookmarked albums
- Notify when new images are detected
- Add per-bookmark polling interval and enable/disable toggle

### Notes

- Share-page embedded JSON is not a reliable source of explicit location fields.
- Current best signal is extracting EXIF/GPS from downloaded original bytes when available.
- This source should be treated as best-effort because Google may change share-page internals.

## Phase 3

- Signed/notarized releases
- Per-printer presets and saved profiles
- Batch export (non-print) pipeline
