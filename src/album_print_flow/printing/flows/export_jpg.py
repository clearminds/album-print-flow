from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
from typing import Any

from PIL import ExifTags, Image

from album_print_flow.image_io_helpers import original_metadata_path_for_image


def _unique_output_path(export_dir: Path, stem: str, suffix: str) -> Path:
    candidate = export_dir / f"{stem}{suffix}"
    if not candidate.exists():
        return candidate

    counter = 2
    while True:
        numbered = export_dir / f"{stem}_{counter}{suffix}"
        if not numbered.exists():
            return numbered
        counter += 1


def _export_stem_for_path(date_used: datetime | None, path: Path) -> str:
    if isinstance(date_used, datetime):
        return date_used.strftime("%Y%m%d%H%M%S")
    return path.stem


_EXIF_TAGS = ExifTags.TAGS
_ORIENTATION_TAG = next(
    (tag for tag, name in _EXIF_TAGS.items() if name == "Orientation"),
    None,
)
_DATETIME_ORIGINAL_TAG = next(
    (tag for tag, name in _EXIF_TAGS.items() if name == "DateTimeOriginal"),
    None,
)
_DATETIME_DIGITIZED_TAG = next(
    (tag for tag, name in _EXIF_TAGS.items() if name == "DateTimeDigitized"),
    None,
)
_DATETIME_TAG = next(
    (tag for tag, name in _EXIF_TAGS.items() if name == "DateTime"),
    None,
)
_USER_COMMENT_TAG = next(
    (tag for tag, name in _EXIF_TAGS.items() if name == "UserComment"),
    None,
)
_IMAGE_DESCRIPTION_TAG = next(
    (tag for tag, name in _EXIF_TAGS.items() if name == "ImageDescription"),
    None,
)
_SOFTWARE_TAG = next(
    (tag for tag, name in _EXIF_TAGS.items() if name == "Software"),
    None,
)


def _encode_user_comment(text: str) -> bytes:
    prefix = b"ASCII\x00\x00\x00"
    return prefix + text.encode("ascii", errors="replace")


def _build_export_exif(
    window: Any,
    path: Path,
    settings: Any,
    export_started_at: datetime,
    date_used: datetime,
) -> bytes | None:
    metadata_path = original_metadata_path_for_image(path)
    try:
        with Image.open(metadata_path) as source:
            exif = source.getexif()
    except OSError:
        return None

    if exif is None:
        return None

    payload = {
        "app": "album-print-flow",
        "exported_at": export_started_at.isoformat(timespec="seconds"),
        "source_name": path.name,
        "source_key": window.metadata_key_for_path(path),
        "source_hash": window.compute_file_hash(path),
        "date_used": date_used.isoformat(),
        "settings": {
            "orientation": settings.orientation,
            "rotation_degrees": settings.rotation_degrees,
            "crop_ratio": settings.crop_ratio,
            "crop_zoom_percent": settings.crop_zoom_percent,
            "crop_offset_x_percent": settings.crop_offset_x_percent,
            "crop_offset_y_percent": settings.crop_offset_y_percent,
            "datetime_override": (
                settings.datetime_override.isoformat()
                if settings.datetime_override
                else ""
            ),
        },
    }

    reference_text = json.dumps(payload, ensure_ascii=True, separators=(",", ":"))

    if _ORIENTATION_TAG is not None:
        exif[_ORIENTATION_TAG] = 1
    effective_dt = settings.datetime_override or date_used
    if isinstance(effective_dt, datetime):
        stamp_value = effective_dt.strftime("%Y:%m:%d %H:%M:%S")
        if _DATETIME_ORIGINAL_TAG is not None:
            exif[_DATETIME_ORIGINAL_TAG] = stamp_value
        if _DATETIME_DIGITIZED_TAG is not None:
            exif[_DATETIME_DIGITIZED_TAG] = stamp_value
        if _DATETIME_TAG is not None:
            exif[_DATETIME_TAG] = stamp_value
    if _SOFTWARE_TAG is not None:
        exif[_SOFTWARE_TAG] = "album-print-flow"
    if _IMAGE_DESCRIPTION_TAG is not None:
        exif[_IMAGE_DESCRIPTION_TAG] = "album-print-flow export"
    if _USER_COMMENT_TAG is not None:
        exif[_USER_COMMENT_TAG] = _encode_user_comment(reference_text)

    try:
        return exif.tobytes()
    except Exception:
        return None


def export_all_as_jpg(
    window: Any,
    paths: list[Path],
    export_root: str,
    render_image_fn: Any,
    *,
    settings_by_path: dict[Path, Any] | None = None,
    date_used_by_path: dict[Path, datetime] | None = None,
    log_fn: Any | None = None,
    progress_fn: Any | None = None,
) -> tuple[list[Path], list[str], str, str, dict[str, str]]:
    if not export_root:
        return [], [path.name for path in paths], "Export folder is missing", "", {}

    base_dir = Path(export_root).expanduser()
    try:
        base_dir.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        return [], [path.name for path in paths], str(error), "", {}

    export_root_dir = base_dir / "Printed"
    try:
        export_root_dir.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        return [], [path.name for path in paths], str(error), "", {}

    export_started_at = datetime.now()
    timestamp = export_started_at.strftime("%Y%m%d%H%M")
    export_dir = export_root_dir / timestamp
    try:
        export_dir.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        return [], [path.name for path in paths], str(error), "", {}

    exported: list[Path] = []
    failed: list[str] = []
    job_ids: dict[str, str] = {}

    if log_fn is not None:
        log_fn(
            "DEBUG",
            f"Export JPG start: root={base_dir}, dir={export_dir}, count={len(paths)}",
        )

    ordered_paths = sorted(
        paths,
        key=lambda item: (
            (date_used_by_path or {}).get(item) or window.date_used_for_path(item),
            item.name,
        ),
    )

    total = len(ordered_paths)
    processed = 0
    for path in ordered_paths:
        try:
            settings = (
                (settings_by_path or {}).get(path)
                or window.processing_settings_for_path(path)
            )
            image = render_image_fn(
                path,
                settings,
                debug_logger=lambda message: window.append_log("DEBUG", message),
            )
            date_used = (
                (date_used_by_path or {}).get(path) or window.date_used_for_path(path)
            )
            stem = _export_stem_for_path(date_used, path)
            out = _unique_output_path(export_dir, stem, ".jpg")
            exif_bytes = _build_export_exif(
                window,
                path,
                settings,
                export_started_at,
                date_used,
            )
            if exif_bytes:
                image.save(
                    out,
                    format="JPEG",
                    quality=95,
                    optimize=True,
                    exif=exif_bytes,
                )
            else:
                image.save(out, format="JPEG", quality=95, optimize=True)
            exported.append(path)
            job_ids[path.name] = out.name
        except OSError as error:
            failed.append(path.name)
            if log_fn is not None:
                log_fn(
                    "DEBUG",
                    f"Export JPG failed for {path.name}: {error}",
                )
        finally:
            processed += 1
            if progress_fn is not None:
                progress_fn(processed, total, path.name)

    return exported, failed, "", str(export_dir), job_ids


__all__ = ["export_all_as_jpg"]
