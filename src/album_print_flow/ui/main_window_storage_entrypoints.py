from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import QThread
from PySide6.QtGui import QPixmap

from album_print_flow.app_constants import (
    LOG_FILENAME,
    LOG_LEVEL_RANK,
    METADATA_FILENAME,
    SETTINGS_ORG,
    TABLE_COL_FILE,
)
from album_print_flow.source_state_store import save_source_state
from album_print_flow.sources.flows.apply import (
    apply_source_load_result as apply_source_load_result_flow,
)
from album_print_flow.sources.flows.folder_metadata import (
    format_storage_size as format_storage_size_flow,
)
from album_print_flow.sources.flows.folder_metadata import (
    google_photos_album_url_cache_dir as google_photos_album_url_cache_dir_flow,
)
from album_print_flow.sources.flows.folder_metadata import (
    google_photos_cache_dir as google_photos_cache_dir_flow,
)
from album_print_flow.sources.flows.folder_metadata import (
    legacy_metadata_path as legacy_metadata_path_flow,
)
from album_print_flow.sources.flows.folder_metadata import (
    metadata_context_key as metadata_context_key_flow,
)
from album_print_flow.sources.flows.folder_metadata import (
    metadata_index_path as metadata_index_path_flow,
)
from album_print_flow.sources.flows.folder_metadata import (
    metadata_path as metadata_path_flow,
)
from album_print_flow.sources.flows.folder_metadata import (
    metadata_root_path as metadata_root_path_flow,
)
from album_print_flow.sources.flows.folder_metadata import (
    metadata_source_dir as metadata_source_dir_flow,
)
from album_print_flow.sources.flows.folder_metadata import (
    metadata_source_id as metadata_source_id_flow,
)
from album_print_flow.sources.flows.folder_metadata import (
    migrate_thumbnail_cache_file as migrate_thumbnail_cache_file_flow,
)
from album_print_flow.sources.flows.folder_metadata import (
    path_storage_stats as path_storage_stats_flow,
)
from album_print_flow.sources.flows.folder_metadata import (
    remove_path_tree as remove_path_tree_flow,
)
from album_print_flow.sources.flows.folder_metadata import (
    thumbnail_cache_candidate_paths as thumbnail_cache_candidate_paths_flow,
)
from album_print_flow.sources.flows.folder_metadata import (
    thumbnail_cache_context_dir as thumbnail_cache_context_dir_flow,
)
from album_print_flow.sources.flows.folder_metadata import (
    thumbnail_cache_file_path as thumbnail_cache_file_path_flow,
)
from album_print_flow.sources.flows.folder_metadata import (
    thumbnail_cache_legacy_file_path as thumbnail_cache_legacy_file_path_flow,
)
from album_print_flow.sources.flows.folder_metadata import (
    thumbnail_cache_root_path as thumbnail_cache_root_path_flow,
)
from album_print_flow.sources.flows.folder_metadata import (
    update_metadata_index as update_metadata_index_flow,
)
from album_print_flow.sources.flows.metadata_sync import (
    update_source_metadata_for_assets as update_source_metadata_for_assets_flow,
)
from album_print_flow.sources.flows.state_sync import (
    merge_global_source_state_into_folder as merge_global_source_state_into_folder_flow,
)
from album_print_flow.sources.flows.state_sync import (
    sync_global_source_state_from_path as sync_global_source_state_from_path_flow,
)
from album_print_flow.ui.dialog_launchers import (
    open_cache_manager_dialog as open_cache_manager_dialog_flow,
)
from album_print_flow.ui.dialogs.metadata_manager import open_metadata_manager_dialog
from album_print_flow.ui.log_console_flow import append_log as append_log_flow
from album_print_flow.ui.log_console_flow import (
    clear_log_console as clear_log_console_flow,
)
from album_print_flow.ui.log_console_flow import (
    current_log_level_rank as current_log_level_rank_flow,
)
from album_print_flow.ui.log_console_flow import (
    current_log_text_filter as current_log_text_filter_flow,
)
from album_print_flow.ui.log_console_flow import (
    log_entry_visible as log_entry_visible_flow,
)
from album_print_flow.ui.log_console_flow import log_file_path as log_file_path_flow
from album_print_flow.ui.log_console_flow import (
    on_log_level_changed as on_log_level_changed_flow,
)
from album_print_flow.ui.log_console_flow import (
    on_log_text_filter_changed as on_log_text_filter_changed_flow,
)
from album_print_flow.ui.log_console_flow import (
    refresh_log_console as refresh_log_console_flow,
)
from album_print_flow.ui.thumbnail_cache_flow import (
    load_cached_thumbnail as load_cached_thumbnail_flow,
)
from album_print_flow.ui.thumbnail_cache_flow import (
    migrate_thumbnail_cache_for_paths as migrate_thumbnail_cache_for_paths_flow,
)


def sync_global_source_state_from_path(window: Any, path: Path) -> None:
    sync_global_source_state_from_path_flow(
        window,
        path,
        settings_org=SETTINGS_ORG,
        save_source_state_fn=save_source_state,
    )


def merge_global_source_state_into_folder(window: Any) -> bool:
    return merge_global_source_state_into_folder_flow(window)


def update_source_metadata_for_assets(window: Any) -> bool:
    return update_source_metadata_for_assets_flow(window)


def apply_source_load_result(
    window: Any,
    result: Any,
    open_settings_if_new: bool,
    preferred_path: Path | None,
) -> None:
    apply_source_load_result_flow(
        window,
        result,
        open_settings_if_new,
        preferred_path,
        table_col_file=TABLE_COL_FILE,
    )


def metadata_root_path() -> Path:
    return metadata_root_path_flow(settings_org=SETTINGS_ORG)


def metadata_source_id(window: Any) -> str:
    return metadata_source_id_flow(window)


def metadata_source_dir(window: Any) -> Path:
    return metadata_source_dir_flow(window, settings_org=SETTINGS_ORG)


def format_storage_size(value_bytes: int) -> str:
    return format_storage_size_flow(value_bytes)


def path_storage_stats(path: Path) -> tuple[int, int]:
    return path_storage_stats_flow(path)


def remove_path_tree(path: Path) -> tuple[int, int]:
    return remove_path_tree_flow(path)


def google_photos_cache_dir() -> Path:
    return google_photos_cache_dir_flow(settings_org=SETTINGS_ORG)


def google_photos_album_url_cache_dir() -> Path:
    return google_photos_album_url_cache_dir_flow(settings_org=SETTINGS_ORG)


def open_cache_manager_dialog(window: Any) -> None:
    open_cache_manager_dialog_flow(
        window,
        open_metadata_manager_dialog_fn=open_metadata_manager_dialog,
    )


def thumbnail_cache_root_path() -> Path:
    return thumbnail_cache_root_path_flow(settings_org=SETTINGS_ORG)


def thumbnail_cache_context_dir(window: Any) -> Path:
    return thumbnail_cache_context_dir_flow(window, settings_org=SETTINGS_ORG)


def thumbnail_cache_file_path(window: Any, path: Path) -> Path:
    return thumbnail_cache_file_path_flow(
        window,
        path,
        settings_org=SETTINGS_ORG,
    )


def thumbnail_cache_legacy_file_path(window: Any, path: Path) -> Path:
    return thumbnail_cache_legacy_file_path_flow(
        window,
        path,
        settings_org=SETTINGS_ORG,
    )


def thumbnail_cache_candidate_paths(window: Any, path: Path) -> tuple[Path, Path]:
    return thumbnail_cache_candidate_paths_flow(
        window,
        path,
        settings_org=SETTINGS_ORG,
    )


def load_cached_thumbnail(window: Any, path: Path) -> QPixmap | None:
    return load_cached_thumbnail_flow(window, path)


def migrate_thumbnail_cache_file(
    window: Any,
    path: Path,
    *,
    source_mtime_ns: int | None = None,
) -> bool:
    return migrate_thumbnail_cache_file_flow(
        window,
        path,
        source_mtime_ns=source_mtime_ns,
    )


def migrate_thumbnail_cache_for_paths(window: Any, paths: list[Path]) -> int:
    return migrate_thumbnail_cache_for_paths_flow(window, paths)


def metadata_index_path(window: Any) -> Path:
    return metadata_index_path_flow(window)


def metadata_context_key(window: Any) -> str:
    return metadata_context_key_flow(window)


def legacy_metadata_path(window: Any) -> Path | None:
    return legacy_metadata_path_flow(window, metadata_filename=METADATA_FILENAME)


def metadata_path(window: Any) -> Path | None:
    return metadata_path_flow(window)


def update_metadata_index(window: Any, metadata_file_path: Path) -> None:
    update_metadata_index_flow(window, metadata_file_path)


def log_file_path(window: Any) -> Path | None:
    return log_file_path_flow(
        window,
        settings_org=SETTINGS_ORG,
        log_filename=LOG_FILENAME,
    )


def current_log_level_rank(window: Any) -> int:
    return current_log_level_rank_flow(window, log_level_rank=LOG_LEVEL_RANK)


def current_log_text_filter(window: Any) -> str:
    return current_log_text_filter_flow(window)


def log_entry_visible(window: Any, level: str, line: str) -> bool:
    return log_entry_visible_flow(
        window,
        level,
        line,
        log_level_rank=LOG_LEVEL_RANK,
    )


def refresh_log_console(window: Any) -> None:
    refresh_log_console_flow(window)


def on_log_level_changed(window: Any, value: str) -> None:
    on_log_level_changed_flow(window, value, log_level_rank=LOG_LEVEL_RANK)


def on_log_text_filter_changed(window: Any, value: str) -> None:
    on_log_text_filter_changed_flow(window, value)


def clear_log_console(window: Any) -> None:
    clear_log_console_flow(window)


def append_log(window: Any, level: str, message: str) -> None:
    append_log_flow(
        window,
        level,
        message,
        qthread_cls=QThread,
        log_level_rank=LOG_LEVEL_RANK,
    )


__all__ = [
    "append_log",
    "apply_source_load_result",
    "clear_log_console",
    "current_log_level_rank",
    "current_log_text_filter",
    "format_storage_size",
    "google_photos_album_url_cache_dir",
    "google_photos_cache_dir",
    "legacy_metadata_path",
    "load_cached_thumbnail",
    "log_entry_visible",
    "log_file_path",
    "merge_global_source_state_into_folder",
    "metadata_context_key",
    "metadata_index_path",
    "metadata_path",
    "metadata_root_path",
    "metadata_source_dir",
    "metadata_source_id",
    "migrate_thumbnail_cache_file",
    "migrate_thumbnail_cache_for_paths",
    "on_log_level_changed",
    "on_log_text_filter_changed",
    "open_cache_manager_dialog",
    "path_storage_stats",
    "refresh_log_console",
    "remove_path_tree",
    "sync_global_source_state_from_path",
    "thumbnail_cache_candidate_paths",
    "thumbnail_cache_context_dir",
    "thumbnail_cache_file_path",
    "thumbnail_cache_legacy_file_path",
    "thumbnail_cache_root_path",
    "update_metadata_index",
    "update_source_metadata_for_assets",
]
