from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QMessageBox

from album_print_flow.sources.types import SourceLoadResult


def apply_source_load_result(
    window: Any,
    result: SourceLoadResult,
    open_settings_if_new: bool,
    preferred_path: Path | None,
    *,
    table_col_file: int,
) -> None:
    previous_source_id = window.current_source_id
    previous_context_id = window.current_source_context_id
    previous_thumbnail_cache = window.thumbnail_cache

    window.current_source_id = result.source_id
    window.current_source_context_id = result.context_id

    folder_path = result.metadata_root
    if folder_path is None:
        QMessageBox.warning(
            window,
            "Unsupported Source",
            "This source does not provide a local project folder yet.",
        )
        return

    window.current_folder = folder_path
    window.update_folder_settings_availability()

    incoming_paths = [asset.local_path for asset in result.assets]
    incoming_path_set = set(incoming_paths)
    preserved_thumbnail_cache: dict[Path, QPixmap] = {}
    if (
        previous_source_id == result.source_id
        and previous_context_id == result.context_id
        and previous_thumbnail_cache
    ):
        for path, pixmap in previous_thumbnail_cache.items():
            if path not in incoming_path_set:
                continue
            cache_candidates = [
                window.thumbnail_cache_file_path(path),
                window.thumbnail_cache_legacy_file_path(path),
            ]
            try:
                source_mtime_ns = path.stat().st_mtime_ns
            except OSError:
                continue
            for cache_path in cache_candidates:
                try:
                    cache_mtime_ns = cache_path.stat().st_mtime_ns
                except OSError:
                    continue
                if cache_mtime_ns >= source_mtime_ns:
                    preserved_thumbnail_cache[path] = pixmap
                    break

    window.thumbnail_generation += 1
    window.thumbnail_cache = preserved_thumbnail_cache
    window.thumbnail_pending_paths = []
    window.thumbnail_inflight_paths = set()
    window.orientation_cache = {}
    window.image_dimensions_cache = {}
    window.location_cache = {}
    window.file_hash_cache = {}

    metadata_already_exists = False
    metadata_target = window.metadata_path()
    if metadata_target is not None and metadata_target.exists():
        metadata_already_exists = True

    window.load_folder_metadata()

    window.source_assets_by_path = {asset.local_path: asset for asset in result.assets}
    window.image_paths = incoming_paths

    metadata_changed = False
    if window.merge_global_source_state_into_folder():
        metadata_changed = True
    if window.update_source_metadata_for_assets():
        metadata_changed = True
    if metadata_changed:
        window.save_folder_metadata()
        window.update_aspect_navigation_buttons()

    reset_count = 0
    if window.current_source_id == "folder":
        reset_count = window.sync_image_settings_with_files()
    else:
        window.append_log(
            "DEBUG",
            f"Skipped file-hash settings sync for source {window.current_source_id}",
        )

    window.apply_sort_order(preferred_path)

    window.append_log(
        "INFO",
        f"Loaded {result.source_label}: {result.context_label} "
        f"({len(window.image_paths)} image(s))",
    )
    if reset_count:
        window.append_log(
            "WARNING",
            f"Reset per-image settings for {reset_count} changed file(s)",
        )

    if not window.image_paths:
        window.current_index = -1
        window.update_controls_visibility()
        window.preview_label.setText("No compatible images in selected source")
        window.preview_label.setPixmap(QPixmap())
        window.statusBar().showMessage("No images found")
        window.append_log("WARNING", "No compatible images found in selected source")
        return

    if window.image_table.currentRow() < 0:
        window.image_table.setCurrentCell(0, table_col_file)

    photo_data = window.folder_metadata.get("photos")
    total_printed = 0
    if isinstance(photo_data, dict):
        for entry in photo_data.values():
            if isinstance(entry, dict):
                total_printed += int(entry.get("total_printed", 0))

    message = f"Loaded {len(window.image_paths)} image(s) from {result.context_label}"
    if total_printed:
        message += f". Print history: {total_printed} total prints"
    window.statusBar().showMessage(message)

    if (not metadata_already_exists) and open_settings_if_new:
        window.open_project_settings_dialog()

    window.refresh_gps_resolution_progress()
