from __future__ import annotations

from pathlib import Path
from typing import Any

import album_printer.metadata_store as metadata_store


def metadata_root_path(*, settings_org: str) -> Path:
    return metadata_store.metadata_root_path(settings_org)


def metadata_source_id(window: Any) -> str:
    return str(window.current_source_id or "").strip() or "unknown"


def metadata_source_dir(window: Any, *, settings_org: str) -> Path:
    return metadata_store.metadata_source_dir(
        settings_org,
        window.metadata_source_id(),
    )


def format_storage_size(value_bytes: int) -> str:
    return metadata_store.format_storage_size(value_bytes)


def path_storage_stats(path: Path) -> tuple[int, int]:
    return metadata_store.path_storage_stats(path)


def remove_path_tree(path: Path) -> tuple[int, int]:
    return metadata_store.remove_path_tree(path)


def google_photos_cache_dir(*, settings_org: str) -> Path:
    return metadata_store.google_photos_cache_dir(settings_org)


def google_photos_album_url_cache_dir(*, settings_org: str) -> Path:
    return metadata_store.google_photos_album_url_cache_dir(settings_org)


def thumbnail_cache_root_path(*, settings_org: str) -> Path:
    return metadata_store.thumbnail_cache_root_path(settings_org)


def thumbnail_cache_context_dir(window: Any, *, settings_org: str) -> Path:
    return metadata_store.thumbnail_cache_context_dir(
        settings_org,
        window.metadata_source_id(),
        window.metadata_context_key(),
    )


def thumbnail_cache_file_path(window: Any, path: Path, *, settings_org: str) -> Path:
    return metadata_store.thumbnail_cache_file_path(
        settings_org,
        window.metadata_source_id(),
        window.metadata_context_key(),
        path.name,
    )


def thumbnail_cache_legacy_file_path(
    window: Any,
    path: Path,
    *,
    settings_org: str,
) -> Path:
    return metadata_store.thumbnail_cache_legacy_file_path(
        settings_org,
        window.metadata_source_id(),
        window.metadata_context_key(),
        path.name,
    )


def thumbnail_cache_candidate_paths(
    window: Any,
    path: Path,
    *,
    settings_org: str,
) -> tuple[Path, Path]:
    return metadata_store.thumbnail_cache_candidate_paths(
        settings_org,
        window.metadata_source_id(),
        window.metadata_context_key(),
        path.name,
    )


def migrate_thumbnail_cache_file(
    window: Any,
    path: Path,
    *,
    source_mtime_ns: int | None = None,
) -> bool:
    cache_path, legacy_cache_path = window.thumbnail_cache_candidate_paths(path)
    return metadata_store.migrate_thumbnail_cache_file(
        path,
        cache_path,
        legacy_cache_path,
        source_mtime_ns=source_mtime_ns,
    )


def metadata_index_path(window: Any) -> Path:
    return metadata_store.metadata_index_path(window.metadata_source_dir())


def metadata_context_key(window: Any) -> str:
    return metadata_store.metadata_context_key(
        str(window.current_source_id or ""),
        str(window.current_source_context_id or ""),
        window.current_folder,
    )


def legacy_metadata_path(window: Any, *, metadata_filename: str) -> Path | None:
    if window.current_folder is None:
        return None
    return window.current_folder / metadata_filename


def metadata_path(window: Any) -> Path | None:
    return metadata_store.metadata_file_path(
        window.metadata_source_dir(),
        window.metadata_context_key(),
    )


def update_metadata_index(window: Any, metadata_file_path: Path) -> None:
    context_key = window.metadata_context_key()
    if not context_key:
        return

    source_id = window.metadata_source_id()
    context_id = str(window.current_source_context_id or "").strip()
    if not context_id and window.current_folder is not None:
        context_id = str(window.current_folder.resolve())

    display_context = context_id
    if source_id == "folder" and window.current_folder is not None:
        display_context = str(window.current_folder.resolve())

    index_path = window.metadata_index_path()
    metadata_store.update_metadata_index(
        index_path,
        metadata_file_path,
        source_id=source_id,
        context_id=context_id,
        context_key=context_key,
        display_context=display_context,
    )


def load_folder_metadata(window: Any) -> None:
    path = window.metadata_path()
    if path is None:
        window.folder_metadata = window.default_metadata()
        return

    if not path.exists():
        legacy_path = window.legacy_metadata_path()
        if legacy_path is not None and legacy_path.exists():
            legacy_data = metadata_store.load_json_dict(legacy_path)
            if legacy_data is not None:
                window.folder_metadata = window.default_metadata() | legacy_data
                window.save_folder_metadata()
                window.append_log(
                    "INFO",
                    "Migrated legacy metadata to app config store",
                )
                return

        window.folder_metadata = window.default_metadata()
        return

    payload = metadata_store.load_json_dict(path)
    if payload is None:
        window.folder_metadata = window.default_metadata()
        return

    window.folder_metadata = window.default_metadata() | payload
    window.update_metadata_index(path)


def save_folder_metadata(window: Any) -> None:
    path = window.metadata_path()
    if path is None:
        return

    saved = metadata_store.save_metadata_file(path, window.folder_metadata)
    if saved:
        window.update_metadata_index(path)


__all__ = [
    "format_storage_size",
    "google_photos_album_url_cache_dir",
    "google_photos_cache_dir",
    "legacy_metadata_path",
    "load_folder_metadata",
    "metadata_context_key",
    "metadata_index_path",
    "metadata_path",
    "metadata_root_path",
    "metadata_source_dir",
    "metadata_source_id",
    "migrate_thumbnail_cache_file",
    "path_storage_stats",
    "remove_path_tree",
    "save_folder_metadata",
    "thumbnail_cache_candidate_paths",
    "thumbnail_cache_context_dir",
    "thumbnail_cache_file_path",
    "thumbnail_cache_legacy_file_path",
    "thumbnail_cache_root_path",
    "update_metadata_index",
]
