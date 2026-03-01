from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any


def metadata_key_for_path(window: Any, path: Path) -> str:
    asset = window.source_assets_by_path.get(path)
    if asset is not None and asset.key.strip():
        return asset.key.strip()
    return path.name


def source_photo_id_for_path(window: Any, path: Path) -> str:
    asset = window.source_assets_by_path.get(path)
    if asset is None:
        return ""
    if asset.source_photo_id and asset.source_photo_id.strip():
        return asset.source_photo_id.strip()
    return ""


def source_captured_at_for_path(window: Any, path: Path) -> datetime | None:
    asset = window.source_assets_by_path.get(path)
    if asset is not None and isinstance(asset.captured_at, datetime):
        return asset.captured_at

    entry = window.photo_entry_for_path(path)
    text = str(entry.get("source_captured_at", "")).strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def sync_global_source_state_from_path(
    window: Any,
    path: Path,
    *,
    settings_org: str,
    save_source_state_fn: Callable[[str, dict[str, object]], None],
) -> None:
    photo_id = window.source_photo_id_for_path(path)
    if not photo_id:
        return

    key = window.metadata_key_for_path(path)
    image_settings = window.folder_metadata.get("image_settings")
    photos = window.folder_metadata.get("photos")
    if not isinstance(image_settings, dict) or not isinstance(photos, dict):
        return

    image_entry = image_settings.get(key)
    photo_entry = photos.get(key)
    if not isinstance(image_entry, dict) and not isinstance(photo_entry, dict):
        return

    all_google_state = window.source_state.get("google_photo_state")
    if not isinstance(all_google_state, dict):
        all_google_state = {}
        window.source_state["google_photo_state"] = all_google_state

    state_entry = all_google_state.get(photo_id)
    if not isinstance(state_entry, dict):
        state_entry = {}

    if isinstance(image_entry, dict):
        state_entry["image_settings"] = image_entry
    if isinstance(photo_entry, dict):
        state_entry["photo"] = photo_entry
    state_entry["updated_at"] = datetime.now().isoformat(timespec="seconds")
    all_google_state[photo_id] = state_entry
    save_source_state_fn(settings_org, window.source_state)


def merge_global_source_state_into_folder(window: Any) -> bool:
    all_google_state = window.source_state.get("google_photo_state")
    if not isinstance(all_google_state, dict):
        return False

    image_settings = window.folder_metadata.get("image_settings")
    if not isinstance(image_settings, dict):
        image_settings = {}
        window.folder_metadata["image_settings"] = image_settings

    photos = window.folder_metadata.get("photos")
    if not isinstance(photos, dict):
        photos = {}
        window.folder_metadata["photos"] = photos

    changed = False
    for path in window.image_paths:
        photo_id = window.source_photo_id_for_path(path)
        if not photo_id:
            continue
        state_entry = all_google_state.get(photo_id)
        if not isinstance(state_entry, dict):
            continue

        key = window.metadata_key_for_path(path)
        if key not in image_settings and isinstance(
            state_entry.get("image_settings"), dict
        ):
            image_settings[key] = state_entry["image_settings"]
            changed = True

        if key not in photos and isinstance(state_entry.get("photo"), dict):
            photos[key] = state_entry["photo"]
            changed = True

    return changed


__all__ = [
    "merge_global_source_state_into_folder",
    "metadata_key_for_path",
    "source_captured_at_for_path",
    "source_photo_id_for_path",
    "sync_global_source_state_from_path",
]
