from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any


def photo_entry_for_path(window: Any, path: Path) -> dict[str, object]:
    photos = window.folder_metadata.get("photos")
    if not isinstance(photos, dict):
        return {}

    key = window.metadata_key_for_path(path)
    entry = photos.get(key)
    if not isinstance(entry, dict):
        legacy_entry = photos.get(path.name)
        if isinstance(legacy_entry, dict):
            entry = legacy_entry
        else:
            return {}
    return entry


def cached_table_values_for_path(
    window: Any,
    path: Path,
) -> tuple[str, str, str] | None:
    entry = window.photo_entry_for_path(path)
    cache_raw = entry.get("table_cache")
    if not isinstance(cache_raw, dict):
        return None

    date_text = str(cache_raw.get("date_used", "")).strip()
    location_text = str(cache_raw.get("location_status", "")).strip()
    aspect_text = str(cache_raw.get("aspect_text", "")).strip()
    if not date_text or not location_text or not aspect_text:
        return None
    if location_text == "Pending":
        return None
    return date_text, location_text, aspect_text


def store_table_values_for_path(
    window: Any,
    path: Path,
    date_text: str,
    location_text: str,
    aspect_text: str,
) -> bool:
    clean_date = str(date_text or "").strip()
    clean_location = str(location_text or "").strip()
    clean_aspect = str(aspect_text or "").strip()
    if not clean_date or not clean_location or not clean_aspect:
        return False

    entry = window.ensure_photo_entry_for_path(path)
    cache_raw = entry.get("table_cache")
    if not isinstance(cache_raw, dict):
        cache_raw = {}

    changed = (
        str(cache_raw.get("date_used", "")).strip() != clean_date
        or str(cache_raw.get("location_status", "")).strip() != clean_location
        or str(cache_raw.get("aspect_text", "")).strip() != clean_aspect
    )
    if not changed:
        return False

    cache_raw["date_used"] = clean_date
    cache_raw["location_status"] = clean_location
    cache_raw["aspect_text"] = clean_aspect
    cache_raw["updated_at"] = datetime.now().isoformat(timespec="seconds")
    entry["table_cache"] = cache_raw
    return True


def invalidate_table_cache_for_path(window: Any, path: Path) -> None:
    entry = window.photo_entry_for_path(path)
    if isinstance(entry.get("table_cache"), dict):
        del entry["table_cache"]


__all__ = [
    "cached_table_values_for_path",
    "invalidate_table_cache_for_path",
    "photo_entry_for_path",
    "store_table_values_for_path",
]
