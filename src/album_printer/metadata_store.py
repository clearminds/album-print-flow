from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
from datetime import datetime
from pathlib import Path


def metadata_root_path(settings_org: str) -> Path:
    return Path.home() / ".config" / str(settings_org) / "metadata"


def metadata_source_dir(settings_org: str, source_id: str) -> Path:
    safe_source_id = re.sub(r"[^A-Za-z0-9._-]+", "_", str(source_id or ""))
    safe_source_id = safe_source_id.strip("._") or "unknown"
    return metadata_root_path(settings_org) / safe_source_id


def format_storage_size(value_bytes: int) -> str:
    size = max(0, int(value_bytes))
    units = ["B", "KB", "MB", "GB", "TB"]
    unit_index = 0
    value = float(size)
    while value >= 1024.0 and unit_index < len(units) - 1:
        value /= 1024.0
        unit_index += 1
    if unit_index == 0:
        return f"{int(value)} {units[unit_index]}"
    return f"{value:.1f} {units[unit_index]}"


def path_storage_stats(path: Path) -> tuple[int, int]:
    if not path.exists():
        return 0, 0
    if path.is_file():
        try:
            return 1, int(path.stat().st_size)
        except OSError:
            return 0, 0

    file_count = 0
    total_size = 0
    for root, _dirs, files in os.walk(path):
        root_path = Path(root)
        for file_name in files:
            file_path = root_path / file_name
            try:
                total_size += int(file_path.stat().st_size)
                file_count += 1
            except OSError:
                continue
    return file_count, total_size


def remove_path_tree(path: Path) -> tuple[int, int]:
    file_count, total_size = path_storage_stats(path)
    if not path.exists():
        return 0, 0
    try:
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
    except OSError:
        return 0, 0
    return file_count, total_size


def google_photos_cache_dir(settings_org: str) -> Path:
    return Path.home() / ".cache" / str(settings_org) / "google-photos"


def google_photos_album_url_cache_dir(settings_org: str) -> Path:
    return Path.home() / ".cache" / str(settings_org) / "google-photos-albums"


def thumbnail_cache_root_path(settings_org: str) -> Path:
    return Path.home() / ".cache" / str(settings_org) / "thumbnails"


def thumbnail_cache_context_dir(
    settings_org: str,
    source_id: str,
    context_key: str,
) -> Path:
    safe_source_id = re.sub(r"[^A-Za-z0-9._-]+", "_", str(source_id or ""))
    safe_source_id = safe_source_id.strip("._") or "unknown"
    context_digest = (
        hashlib.sha256(str(context_key).encode("utf-8")).hexdigest()[:20]
        if context_key
        else "default"
    )
    return thumbnail_cache_root_path(settings_org) / safe_source_id / context_digest


def thumbnail_cache_file_path(
    settings_org: str,
    source_id: str,
    context_key: str,
    file_name: str,
) -> Path:
    hash_input = f"{(context_key or 'default')}::{file_name}"
    cache_key = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()[:32]
    return (
        thumbnail_cache_context_dir(settings_org, source_id, context_key)
        / f"{cache_key}.png"
    )


def thumbnail_cache_legacy_file_path(
    settings_org: str,
    source_id: str,
    context_key: str,
    file_name: str,
) -> Path:
    safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", str(file_name or "")).strip("._")
    if not safe_name:
        safe_name = "image"
    return (
        thumbnail_cache_context_dir(settings_org, source_id, context_key)
        / f"{safe_name}.png"
    )


def thumbnail_cache_candidate_paths(
    settings_org: str,
    source_id: str,
    context_key: str,
    file_name: str,
) -> tuple[Path, Path]:
    return (
        thumbnail_cache_file_path(settings_org, source_id, context_key, file_name),
        thumbnail_cache_legacy_file_path(
            settings_org, source_id, context_key, file_name
        ),
    )


def migrate_thumbnail_cache_file(
    path: Path,
    cache_path: Path,
    legacy_cache_path: Path,
    *,
    source_mtime_ns: int | None = None,
) -> bool:
    if cache_path.exists() or not legacy_cache_path.exists():
        return False

    if source_mtime_ns is None:
        try:
            source_mtime_ns = path.stat().st_mtime_ns
        except OSError:
            return False

    try:
        legacy_mtime_ns = legacy_cache_path.stat().st_mtime_ns
    except OSError:
        return False
    if legacy_mtime_ns < source_mtime_ns:
        return False

    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        legacy_cache_path.replace(cache_path)
        return True
    except OSError:
        return False


def metadata_index_path(source_dir: Path) -> Path:
    return source_dir / "index.json"


def metadata_context_key(
    source_id: str,
    context_id: str,
    current_folder: Path | None,
) -> str:
    resolved_source_id = str(source_id or "").strip() or "unknown"
    resolved_context_id = str(context_id or "").strip()
    if not resolved_context_id and current_folder is not None:
        resolved_context_id = str(current_folder.resolve())
    if not resolved_context_id:
        return ""
    return f"{resolved_source_id}::{resolved_context_id}"


def metadata_file_path(source_dir: Path, context_key: str) -> Path | None:
    if not context_key:
        return None
    digest = hashlib.sha256(context_key.encode("utf-8")).hexdigest()
    return source_dir / f"{digest}.json"


def update_metadata_index(
    index_path: Path,
    metadata_file_path: Path,
    *,
    source_id: str,
    context_id: str,
    context_key: str,
    display_context: str,
) -> None:
    try:
        entries_payload: dict[str, object] = {
            "version": 1,
            "entries": {},
        }
        if index_path.exists():
            with index_path.open("r", encoding="utf-8") as handle:
                existing_payload = json.load(handle)
            if isinstance(existing_payload, dict):
                entries_payload = {**entries_payload, **existing_payload}

        raw_entries = entries_payload.get("entries")
        if not isinstance(raw_entries, dict):
            raw_entries = {}
        entries_payload["entries"] = raw_entries

        raw_entries[metadata_file_path.stem] = {
            "source_id": source_id,
            "context_id": context_id,
            "context_key": context_key,
            "display_context": display_context,
            "metadata_file": metadata_file_path.name,
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        }

        index_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = index_path.with_suffix(".json.tmp")
        with tmp.open("w", encoding="utf-8") as handle:
            json.dump(entries_payload, handle, indent=2, ensure_ascii=False)
        tmp.replace(index_path)
    except (OSError, json.JSONDecodeError):
        return


def load_json_dict(path: Path) -> dict[str, object] | None:
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if isinstance(payload, dict):
            return payload
    except (OSError, json.JSONDecodeError):
        return None
    return None


def load_metadata_with_defaults(
    path: Path, defaults: dict[str, object]
) -> dict[str, object]:
    payload = load_json_dict(path)
    if payload is None:
        return dict(defaults)
    return dict(defaults) | payload


def save_metadata_file(path: Path, payload: dict[str, object]) -> bool:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".json.tmp")
        with tmp.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
        tmp.replace(path)
        return True
    except OSError:
        return False
