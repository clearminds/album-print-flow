from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any


def location_for_path(
    window: Any,
    path: Path,
    *,
    exif_location_for_image_fn: Callable[[Path], tuple[float, float] | None],
) -> tuple[float, float] | None:
    photo_entry = window.photo_entry_for_path(path)
    manual_location = photo_entry.get("manual_location")
    if isinstance(manual_location, dict):
        try:
            latitude = float(manual_location.get("latitude"))
            longitude = float(manual_location.get("longitude"))
            if -90.0 <= latitude <= 90.0 and -180.0 <= longitude <= 180.0:
                return latitude, longitude
        except (TypeError, ValueError):
            pass

    asset = window.source_assets_by_path.get(path)
    if asset is not None and asset.latitude is not None and asset.longitude is not None:
        return asset.latitude, asset.longitude

    source_location = photo_entry.get("source_location")
    if isinstance(source_location, dict):
        try:
            latitude = float(source_location.get("latitude"))
            longitude = float(source_location.get("longitude"))
            if -90.0 <= latitude <= 90.0 and -180.0 <= longitude <= 180.0:
                return latitude, longitude
        except (TypeError, ValueError):
            pass

    cached = window.location_cache.get(path)
    if path in window.location_cache:
        return cached

    location = exif_location_for_image_fn(path)
    window.location_cache[path] = location
    return location


def location_lookup_cache_for_path(window: Any, path: Path) -> dict[str, str]:
    entry = window.photo_entry_for_path(path)
    raw = entry.get("location_lookup_cache")
    if not isinstance(raw, dict):
        return {}
    cache: dict[str, str] = {}
    for key, value in raw.items():
        if isinstance(key, str) and isinstance(value, str):
            cache[key] = value
    return cache


def location_lookup_cached_value_for_path(
    window: Any,
    path: Path,
    cache_key: str,
) -> str | None:
    per_photo = window.location_lookup_cache_for_path(path)
    if cache_key in per_photo:
        return per_photo[cache_key]
    return window.nominatim_cache.get(cache_key)


def store_location_lookup_for_path(
    window: Any,
    path: Path,
    cache_key: str,
    value: str,
) -> None:
    entry = window.ensure_photo_entry_for_path(path)
    raw = entry.get("location_lookup_cache")
    if not isinstance(raw, dict):
        raw = {}

    previous = raw.get(cache_key)
    if previous == value:
        return

    raw[cache_key] = value
    if len(raw) > 12:
        overflow = len(raw) - 12
        for old_key in list(raw.keys())[:overflow]:
            raw.pop(old_key, None)

    entry["location_lookup_cache"] = raw
    entry["location_lookup_updated_at"] = datetime.now().isoformat(timespec="seconds")
    window.save_folder_metadata()
    window.sync_global_source_state_from_path(path)


def format_location(
    window: Any,
    location: tuple[float, float] | None,
    path: Path | None,
    format_value: str | None,
    *,
    decimal_to_dms_fn: Callable[[float, bool], str],
    location_format_needs_reverse_lookup_fn: Callable[[str], bool],
) -> str:
    if location is None:
        return ""

    area_text = window.location_area_text_for_location(location)
    if area_text:
        return area_text

    selected_format = (format_value or window.location_format_value).strip()
    latitude, longitude = location
    if selected_format == "Lat/Lon":
        return f"{latitude:.5f}, {longitude:.5f}"
    if selected_format == "DMS":
        return (
            f"{decimal_to_dms_fn(latitude, True)}, "
            f"{decimal_to_dms_fn(longitude, False)}"
        )
    if location_format_needs_reverse_lookup_fn(selected_format):
        best_available = window.reverse_geocode_nominatim(
            location,
            path=path,
            format_value=selected_format,
        )
        if best_available:
            return best_available
    return f"{latitude:.5f}, {longitude:.5f}"


def effective_location_format_for_path(
    window: Any,
    path: Path,
    values: dict[str, object] | None,
    *,
    location_format_options: list[str],
) -> str | None:
    if values is None:
        values = window.image_settings_for_path(path)
    mode_override = str(values.get("location_stamp_mode_override", "Default")).strip()

    if mode_override == "Coordinates":
        mode_override = "Lat/Lon"

    if mode_override == "Off":
        return None

    if mode_override == "Custom Text":
        return None

    if mode_override in location_format_options:
        return mode_override

    return window.location_format_value


def location_lookup_status_for_path(
    window: Any,
    path: Path,
    *,
    location_format_needs_reverse_lookup_fn: Callable[[str], bool],
) -> str:
    values = window.image_settings_for_path(path)
    mode_override = str(values.get("location_stamp_mode_override", "Default")).strip()
    if mode_override == "Custom Text":
        custom_text = str(values.get("location_stamp_custom_text", "")).strip()
        return "Custom Text" if custom_text else "Custom Text (empty)"

    location = window.location_for_path(path)
    if location is None:
        return "No GPS"

    selected_format = window.effective_location_format_for_path(path)
    if selected_format is None:
        return "Stamp Off"

    if not location_format_needs_reverse_lookup_fn(selected_format):
        return "Coordinates"

    if not window.nominatim_enabled_value:
        return "Lookup Off"

    if not window.nominatim_reverse_url_value.strip():
        return "No Endpoint"

    latitude, longitude = location
    cache_key = window.nominatim_cache_key(
        latitude,
        longitude,
        format_value=selected_format,
    )
    cached = window.location_lookup_cached_value_for_path(path, cache_key)
    if cached is None:
        return "Pending"
    if cached.strip():
        return "Resolved"
    return "No Result"


def update_location_status_for_path(
    window: Any,
    path: Path,
    *,
    table_col_location: int,
) -> None:
    row = window.row_for_path(path)
    if row is None:
        return
    item = window.image_table.item(row, table_col_location)
    if item is None:
        return
    item.setText(window.location_lookup_status_for_path(path))
    window.invalidate_table_cache_for_path(path)


__all__ = [
    "effective_location_format_for_path",
    "format_location",
    "location_for_path",
    "location_lookup_cache_for_path",
    "location_lookup_cached_value_for_path",
    "location_lookup_status_for_path",
    "store_location_lookup_for_path",
    "update_location_status_for_path",
]
