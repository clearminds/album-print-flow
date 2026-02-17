from __future__ import annotations

from typing import Any


def update_source_metadata_for_assets(window: Any) -> bool:
    photos = window.folder_metadata.get("photos")
    if not isinstance(photos, dict):
        photos = {}
        window.folder_metadata["photos"] = photos

    changed = False
    for path, asset in window.source_assets_by_path.items():
        key = window.metadata_key_for_path(path)
        entry = photos.get(key)
        if not isinstance(entry, dict):
            entry = {}

        if entry.get("source_id") != window.current_source_id:
            entry["source_id"] = window.current_source_id
            changed = True

        display_name = str(asset.display_name or "").strip()
        if display_name and entry.get("source_display_name") != display_name:
            entry["source_display_name"] = display_name
            changed = True

        local_path_text = str(asset.local_path)
        if entry.get("source_local_path") != local_path_text:
            entry["source_local_path"] = local_path_text
            changed = True

        if (
            asset.source_photo_id
            and entry.get("source_photo_id") != asset.source_photo_id
        ):
            entry["source_photo_id"] = asset.source_photo_id
            changed = True

        if asset.captured_at is not None:
            captured_text = asset.captured_at.isoformat(timespec="seconds")
            if entry.get("source_captured_at") != captured_text:
                entry["source_captured_at"] = captured_text
                changed = True

        source_data = asset.source_data
        if isinstance(source_data, dict):
            existing_source_data = entry.get("source_data")
            if (
                not isinstance(existing_source_data, dict)
                or existing_source_data != source_data
            ):
                entry["source_data"] = source_data
                changed = True

        if asset.latitude is not None and asset.longitude is not None:
            source_location = entry.get("source_location")
            if not isinstance(source_location, dict):
                source_location = {}
            latitude = float(asset.latitude)
            longitude = float(asset.longitude)
            if (
                source_location.get("latitude") != latitude
                or source_location.get("longitude") != longitude
            ):
                source_location["latitude"] = latitude
                source_location["longitude"] = longitude
                entry["source_location"] = source_location
                changed = True

        photos[key] = entry

    return changed
