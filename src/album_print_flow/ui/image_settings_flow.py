from __future__ import annotations

import hashlib
import math
from collections.abc import Callable, Iterable
from datetime import datetime
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps


def detect_orientation_for_path(window: Any, path: Path) -> str:
    cached = window.orientation_cache.get(path)
    if cached in {"Landscape", "Portrait"}:
        return cached

    orientation = "Landscape"
    width, height = window.image_dimensions_for_path(path)
    if height > width:
        orientation = "Portrait"

    window.orientation_cache[path] = orientation
    return orientation


def image_settings_for_path(
    window: Any,
    path: Path,
    *,
    normalize_rotation_degrees_fn: Callable[[object], int],
    per_image_location_stamp_overrides: Iterable[str],
) -> dict[str, object]:
    image_settings = window.folder_metadata.get("image_settings", {})
    if not isinstance(image_settings, dict):
        image_settings = {}

    key = window.metadata_key_for_path(path)
    values = image_settings.get(key)
    if not isinstance(values, dict):
        legacy_values = image_settings.get(path.name)
        if isinstance(legacy_values, dict):
            values = legacy_values
        else:
            values = {}

    orientation = values.get("orientation")
    has_explicit_orientation = orientation in {"Landscape", "Portrait"}
    if not has_explicit_orientation:
        cached_orientation = window.orientation_cache.get(path)
        if cached_orientation in {"Landscape", "Portrait"}:
            orientation = cached_orientation
        else:
            orientation = "Landscape"

    brightness = values.get("brightness_percent", 100)
    if not isinstance(brightness, int):
        brightness = 100
    brightness = max(window.brightness_slider.minimum(), brightness)
    brightness = min(window.brightness_slider.maximum(), brightness)

    datetime_override = values.get("datetime_override")
    if not isinstance(datetime_override, str):
        datetime_override = ""

    crop_zoom_percent = values.get("crop_zoom_percent", 100)
    if not isinstance(crop_zoom_percent, int):
        crop_zoom_percent = 100
    crop_zoom_percent = max(100, min(300, crop_zoom_percent))

    crop_offset_x_percent = values.get("crop_offset_x_percent", 0)
    if not isinstance(crop_offset_x_percent, int):
        crop_offset_x_percent = 0
    crop_offset_x_percent = max(-100, min(100, crop_offset_x_percent))

    crop_offset_y_percent = values.get("crop_offset_y_percent", 0)
    if not isinstance(crop_offset_y_percent, int):
        crop_offset_y_percent = 0
    crop_offset_y_percent = max(-100, min(100, crop_offset_y_percent))

    rotation_degrees = normalize_rotation_degrees_fn(values.get("rotation_degrees", 0))
    if not has_explicit_orientation and rotation_degrees in {90, 270}:
        orientation = "Portrait" if orientation == "Landscape" else "Landscape"

    location_stamp_mode_override = str(
        values.get("location_stamp_mode_override", "Default")
    ).strip()
    if location_stamp_mode_override == "Coordinates":
        location_stamp_mode_override = "Lat/Lon"
    if location_stamp_mode_override not in per_image_location_stamp_overrides:
        legacy_enabled = values.get("location_stamp_enabled")
        if isinstance(legacy_enabled, bool):
            location_stamp_mode_override = "Default" if legacy_enabled else "Off"
        else:
            location_stamp_mode_override = "Default"

    location_stamp_custom_text = str(
        values.get("location_stamp_custom_text", "")
    ).strip()

    return {
        "orientation": orientation,
        "rotation_degrees": rotation_degrees,
        "brightness_percent": brightness,
        "datetime_override": datetime_override,
        "crop_zoom_percent": crop_zoom_percent,
        "crop_offset_x_percent": crop_offset_x_percent,
        "crop_offset_y_percent": crop_offset_y_percent,
        "location_stamp_mode_override": location_stamp_mode_override,
        "location_stamp_custom_text": location_stamp_custom_text,
    }


def compute_file_hash(window: Any, path: Path) -> str:
    try:
        stat = path.stat()
    except OSError:
        return ""

    cached = window.file_hash_cache.get(path)
    if cached is not None:
        cached_mtime_ns, cached_size, cached_hash = cached
        if cached_mtime_ns == stat.st_mtime_ns and cached_size == stat.st_size:
            return cached_hash

    digest = hashlib.sha256()
    try:
        with path.open("rb") as file_handle:
            for chunk in iter(lambda: file_handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError:
        return ""

    file_hash = digest.hexdigest()
    window.file_hash_cache[path] = (stat.st_mtime_ns, stat.st_size, file_hash)
    return file_hash


def set_image_entry_file_hash(
    window: Any, path: Path, entry: dict[str, object]
) -> None:
    file_hash = window.compute_file_hash(path)
    if file_hash:
        entry["file_hash"] = file_hash


def sync_image_settings_with_files(window: Any) -> int:
    image_settings = window.folder_metadata.get("image_settings")
    if not isinstance(image_settings, dict):
        return 0

    paths_by_key = {
        window.metadata_key_for_path(path): path for path in window.image_paths
    }
    has_changes = False
    reset_count = 0

    for key in list(image_settings.keys()):
        entry = image_settings.get(key)
        if not isinstance(entry, dict):
            continue

        path = paths_by_key.get(key)
        if path is None:
            continue

        current_hash = window.compute_file_hash(path)
        if not current_hash:
            continue

        stored_hash = str(entry.get("file_hash", "")).strip()
        if stored_hash and stored_hash != current_hash:
            image_settings.pop(key, None)
            window.orientation_cache.pop(path, None)
            window.image_dimensions_cache.pop(path, None)
            window.thumbnail_cache.pop(path, None)
            has_changes = True
            reset_count += 1
            continue

        if not stored_hash:
            entry["file_hash"] = current_hash
            image_settings[key] = entry
            has_changes = True

    if has_changes:
        window.save_folder_metadata()
    return reset_count


def image_dimensions_for_path(
    window: Any,
    path: Path,
    *,
    original_metadata_path_for_image_fn: Callable[[Path], Path],
    load_image_as_rgb_fn: Callable[..., Any],
) -> tuple[int, int]:
    cached = window.image_dimensions_cache.get(path)
    if cached is not None:
        return cached

    metadata_path = original_metadata_path_for_image_fn(path)
    try:
        with Image.open(metadata_path) as image:
            width, height = ImageOps.exif_transpose(image).size
        result = (max(1, int(width)), max(1, int(height)))
    except OSError:
        try:
            image = load_image_as_rgb_fn(
                path,
                debug_logger=lambda message: window.append_log("DEBUG", message),
            )
            width, height = image.size
            result = (max(1, int(width)), max(1, int(height)))
        except OSError:
            result = (1, 1)
    window.image_dimensions_cache[path] = result
    return result


def source_aspect_ratio_label_for_path(window: Any, path: Path) -> str:
    width, height = window.image_dimensions_for_path(path)
    divisor = math.gcd(width, height)
    if divisor <= 0:
        return "1:1"
    return f"{max(1, width // divisor)}:{max(1, height // divisor)}"


def path_needs_crop_for_aspect(
    window: Any,
    path: Path,
    *,
    normalize_rotation_degrees_fn: Callable[[object], int],
    parse_ratio_pair_fn: Callable[[str, tuple[float, float]], tuple[float, float]],
    ratios_match_either_orientation_fn: Callable[..., bool],
) -> bool:
    if window.is_crop_settings_modified(path):
        return False
    values = window.image_settings_for_path(path)
    width, height = window.image_dimensions_for_path(path)
    rotation_degrees = normalize_rotation_degrees_fn(values.get("rotation_degrees", 0))
    if rotation_degrees in {90, 270}:
        width, height = height, width
    if width <= 0 or height <= 0:
        return False
    source_ratio = width / float(height)
    ratio_w, ratio_h = parse_ratio_pair_fn(window.crop_ratio_value, (2.0, 3.0))
    return not ratios_match_either_orientation_fn(
        source_ratio,
        ratio_w,
        ratio_h,
        tolerance=0.01,
    )


def aspect_ratio_cell_text_for_path(window: Any, path: Path) -> str:
    label = window.source_aspect_ratio_label_for_path(path)
    if window.is_crop_settings_modified(path):
        return f"{label} • Fixed"
    if window.path_needs_crop_for_aspect(path):
        return f"{label} ⚠"
    return f"{label} ✓"


def image_list_label(window: Any, path: Path) -> str:
    values = window.image_settings_for_path(path)
    orientation = str(values.get("orientation", "Landscape"))
    orientation_short = "L" if orientation == "Landscape" else "P"
    return f"Mode {orientation_short}"


def is_crop_settings_modified(
    window: Any,
    path: Path,
    *,
    normalize_rotation_degrees_fn: Callable[[object], int],
) -> bool:
    values = window.image_settings_for_path(path)
    default_orientation = window.orientation_cache.get(path)
    if default_orientation in {"Landscape", "Portrait"}:
        if str(values.get("orientation", default_orientation)) != default_orientation:
            return True
    if normalize_rotation_degrees_fn(values.get("rotation_degrees", 0)) != 0:
        return True
    if int(values.get("crop_zoom_percent", 100)) != 100:
        return True
    if int(values.get("crop_offset_x_percent", 0)) != 0:
        return True
    if int(values.get("crop_offset_y_percent", 0)) != 0:
        return True
    return False


def date_used_for_path(window: Any, path: Path) -> datetime:
    date_used, _source = window.date_used_and_source_for_path(path)
    return date_used


def date_used_and_source_for_path(
    window: Any,
    path: Path,
    *,
    parse_datetime_override_fn: Callable[[str], datetime | None],
    exif_datetime_for_image_fn: Callable[[Path], datetime | None],
    parse_datetime_from_filename_fn: Callable[[str], datetime | None],
) -> tuple[datetime, str]:
    values = window.image_settings_for_path(path)
    override_text = str(values.get("datetime_override", ""))
    override_dt = parse_datetime_override_fn(override_text)
    if override_dt is not None:
        return override_dt, "Override"

    source_captured_at = window.source_captured_at_for_path(path)
    if source_captured_at is not None:
        return source_captured_at, "Source"

    exif_dt = exif_datetime_for_image_fn(path)
    if exif_dt is not None:
        return exif_dt, "EXIF"

    filename_dt = parse_datetime_from_filename_fn(path.name)
    if filename_dt is not None:
        return filename_dt, "Filename"

    return datetime.fromtimestamp(path.stat().st_mtime), "Modified"


def path_needs_date_check(window: Any, path: Path) -> bool:
    """True when the date shown is file modified time
    and may need manual verification."""
    _dt, source = window.date_used_and_source_for_path(path)
    return source == "Modified"


def path_needs_fix(window: Any, path: Path) -> bool:
    """True when image needs attention: crop aspect
    mismatch and/or date may be wrong."""
    return window.path_needs_crop_for_aspect(path) or window.path_needs_date_check(path)


def fix_needed_message_for_path(window: Any, path: Path) -> str:
    """Short message describing what needs fixing for
    this image, or empty if nothing."""
    parts = []
    if window.path_needs_crop_for_aspect(path):
        parts.append("Crop aspect mismatch")
    if window.path_needs_date_check(path):
        parts.append("Date may be wrong (file date)")
    return " • ".join(parts) if parts else ""


def restore_image_settings_for_selected(
    window: Any,
    *,
    per_image_location_stamp_overrides: Iterable[str],
) -> None:
    path = window.selected_path()
    if path is None:
        return

    key = window.metadata_key_for_path(path)
    image_settings = window.folder_metadata.get("image_settings")
    has_explicit_orientation = False
    if isinstance(image_settings, dict):
        raw_entry = image_settings.get(key)
        if not isinstance(raw_entry, dict):
            legacy_entry = image_settings.get(path.name)
            if isinstance(legacy_entry, dict):
                raw_entry = legacy_entry
        if isinstance(raw_entry, dict):
            raw_orientation = raw_entry.get("orientation")
            has_explicit_orientation = raw_orientation in {"Landscape", "Portrait"}

    if not has_explicit_orientation and path not in window.orientation_cache:
        window.detect_orientation_for_path(path)

    values = window.image_settings_for_path(path)
    window._restoring_settings = True
    try:
        window.current_image_orientation = str(values["orientation"])
        window.current_image_rotation_degrees = int(values.get("rotation_degrees", 0))
        window.brightness_slider.setValue(int(values["brightness_percent"]))
        window.crop_zoom_slider.setValue(int(values["crop_zoom_percent"]))
        window.crop_x_slider.setValue(int(values["crop_offset_x_percent"]))
        window.crop_y_slider.setValue(int(values["crop_offset_y_percent"]))
        mode_override = str(
            values.get("location_stamp_mode_override", "Default")
        ).strip()
        if mode_override not in per_image_location_stamp_overrides:
            mode_override = "Default"
        window.location_stamp_override_combo.setCurrentText(mode_override)
        custom_text = str(values.get("location_stamp_custom_text", "")).strip()
        window.refresh_custom_location_text_options(preferred_text=custom_text)
        window.update_crop_orientation_button_text()
        window.update_rotate_image_button_text()
        dt_value = str(values.get("datetime_override", ""))
        window.datetime_override_label.setText(dt_value if dt_value else "Auto")
        if mode_override == "Custom Text":
            location_text = custom_text
        else:
            effective_format = window.effective_location_format_for_path(path, values)
            location_text = window.format_location(
                window.location_for_path(path),
                path=path,
                format_value=effective_format,
            )
        window.location_value_label.setText(location_text or "No location")
        window.ignore_for_print_all_checkbox.setChecked(
            window.is_ignored_for_print_all(path)
        )
    finally:
        window._restoring_settings = False
