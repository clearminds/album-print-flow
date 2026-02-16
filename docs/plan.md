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

## Phase 3

- Signed/notarized releases
- Per-printer presets and saved profiles
- Batch export (non-print) pipeline
