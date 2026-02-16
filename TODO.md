# TODO: IPP Direct Borderless Printing

Goal: make borderless photo printing work reliably when using direct IPP (no CUPS fallback behavior assumptions).

## 1) Capability detection and gating

- [ ] Confirm we only enable borderless UI when IPP reports true zero-margin support for the selected media.
- [ ] Validate capability parsing against real printer attributes (`media-col-ready`, margins, and size-specific variants).
- [ ] Add explicit diagnostics log line showing why borderless is enabled/disabled for current media.

## 2) Media/profile selection

- [ ] Build deterministic media mapping for photo sizes (starting with 4x6) to exact IPP media values used by Epson.
- [ ] Prefer `media-col`-only payloads for borderless jobs and avoid conflicting top-level media attributes.
- [ ] Verify `media-source=photo` behavior per size/profile and fall back safely when unsupported.

## 3) Job attribute correctness

- [ ] Verify `print-color-mode`, `print-quality`, `printer-resolution`, and `media-type` combinations that printer accepts for borderless.
- [ ] Keep `ipp-attribute-fidelity=true` for borderless and log any rejection details clearly.
- [ ] Add one debug mode that logs full submitted job attributes (sanitized) for reproducible troubleshooting.

## 4) Rendering and scaling consistency

- [ ] Ensure borderless content scaling compensation is applied consistently for IPP direct path (same behavior as CUPS path).
- [ ] Confirm no double-scaling occurs between app-rendered image and printer-side fit/position behavior.
- [ ] Add a deterministic calibration print path for IPP direct backend.

## 5) Status and error reporting

- [ ] Improve IPP job status polling so UI distinguishes: queued, processing, completed, canceled, aborted.
- [ ] Surface actionable error text for common failures (unsupported attributes, media mismatch, transport errors).
- [ ] Store last IPP status/error in metadata similarly to other backends.

## 6) Real-device validation matrix

- [ ] Run controlled tests per paper size: borderless on/off with identical source image.
- [ ] Validate at least 3 scale settings (e.g., 96/98/100) and document visual outcomes.
- [ ] Capture final known-good presets (media, quality, resolution, scale) in project docs.

## 7) Finalization

- [ ] Add a small troubleshooting section to README for IPP borderless requirements and expected printer settings.
- [ ] Add a regression checklist to run before releases affecting print pipeline.
