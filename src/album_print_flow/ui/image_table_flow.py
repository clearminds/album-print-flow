from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QTableWidgetItem

from album_print_flow.ui.table_metadata_flow import reset_table_metadata_tracking


def rebuild_image_row_lookup(window: Any) -> None:
    window.image_row_lookup = {path: row for row, path in enumerate(window.image_paths)}


def row_for_path(window: Any, path: Path) -> int | None:
    row = window.image_row_lookup.get(path)
    if row is not None and 0 <= row < len(window.image_paths):
        if window.image_paths[row] == path:
            return row
    return None


def refresh_image_list_labels(
    window: Any,
    preferred_path: Path | None,
    *,
    table_col_file: int,
    reset_paused: bool,
) -> None:
    if preferred_path is None:
        preferred_path = window.selected_path()

    reset_table_metadata_tracking(
        window,
        clear_indexing_status_message=True,
        reset_paused=reset_paused,
    )

    window._updating_table = True
    window.image_table.blockSignals(True)
    window.image_table.setRowCount(len(window.image_paths))
    window.rebuild_image_row_lookup()
    for row, path in enumerate(window.image_paths):
        window.populate_image_table_row(row, path)

    window.image_table.blockSignals(False)
    window._updating_table = False

    if window.image_paths:
        if preferred_path in window.image_paths:
            window.image_table.setCurrentCell(
                window.image_paths.index(preferred_path),
                table_col_file,
            )
        else:
            window.image_table.setCurrentCell(0, table_col_file)

    window.start_thumbnail_generation()
    window.start_table_metadata_resolution()
    window.update_aspect_navigation_buttons()


def populate_image_table_row(
    window: Any,
    row: int,
    path: Path,
    *,
    table_col_thumb: int,
    table_col_state: int,
    table_col_print: int,
    table_col_file: int,
    table_col_date_used: int,
    table_col_location: int,
    table_col_aspect: int,
) -> None:
    thumb_item = QTableWidgetItem()
    thumbnail = window.thumbnail_cache.get(path, window.thumbnail_placeholder)
    thumb_item.setData(
        Qt.ItemDataRole.DecorationRole,
        thumbnail,
    )

    state_item = QTableWidgetItem(window.image_list_label(path))
    print_item = QTableWidgetItem(window.latest_print_status_for_path(path))
    file_item = QTableWidgetItem(path.name)
    cached_table_values = window.cached_table_values_for_path(path)
    if cached_table_values is None:
        date_text = "…"
        location_text = "…"
        aspect_text = "…"
    else:
        date_text, location_text, aspect_text = cached_table_values

    date_item = QTableWidgetItem(date_text)
    location_item = QTableWidgetItem(location_text)
    aspect_item = QTableWidgetItem(aspect_text)

    if window.is_crop_settings_modified(path):
        state_font = state_item.font()
        state_font.setBold(True)
        state_item.setFont(state_font)
        state_item.setForeground(QColor("#FF9100"))

    thumb_item.setFlags(thumb_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
    state_item.setFlags(state_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
    print_item.setFlags(print_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
    file_item.setFlags(file_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
    date_item.setFlags(date_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
    location_item.setFlags(location_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
    aspect_item.setFlags(aspect_item.flags() & ~Qt.ItemFlag.ItemIsEditable)

    window.image_table.setItem(row, table_col_thumb, thumb_item)
    window.image_table.setItem(row, table_col_state, state_item)
    window.image_table.setItem(row, table_col_print, print_item)
    window.image_table.setItem(row, table_col_file, file_item)
    window.image_table.setItem(row, table_col_date_used, date_item)
    window.image_table.setItem(row, table_col_location, location_item)
    window.image_table.setItem(row, table_col_aspect, aspect_item)


def append_image_rows(
    window: Any,
    paths: list[Path],
    *,
    thumbnail_ui_cache_warmup_max: int,
    table_col_thumb: int,
) -> None:
    if not paths:
        return
    existing = set(window.image_paths)
    new_paths = [path for path in paths if path not in existing]
    if not new_paths:
        return

    window.migrate_thumbnail_cache_for_paths(new_paths)

    window.image_paths.extend(new_paths)
    start_row = window.image_table.rowCount()
    end_row = start_row + len(new_paths)

    window._updating_table = True
    window.image_table.blockSignals(True)
    window.image_table.setRowCount(end_row)
    for offset, path in enumerate(new_paths):
        window.image_row_lookup[path] = start_row + offset
        window.populate_image_table_row(start_row + offset, path)
    window.image_table.blockSignals(False)
    window._updating_table = False

    warmed = 0
    for path in new_paths:
        if path in window.thumbnail_cache or path in window.thumbnail_pending_paths:
            continue

        if warmed < thumbnail_ui_cache_warmup_max:
            cached = window.load_cached_thumbnail(path)
            if cached is not None:
                window.thumbnail_cache[path] = cached
                row = window.row_for_path(path)
                if row is not None:
                    item = window.image_table.item(row, table_col_thumb)
                    if item is not None:
                        item.setData(Qt.ItemDataRole.DecorationRole, cached)
                warmed += 1
                continue

        window.thumbnail_pending_paths.append(path)

    window.fill_thumbnail_workers()
    window.enqueue_table_metadata_for_paths(new_paths)


__all__ = [
    "append_image_rows",
    "populate_image_table_row",
    "rebuild_image_row_lookup",
    "refresh_image_list_labels",
    "row_for_path",
]
