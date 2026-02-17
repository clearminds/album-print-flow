from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt


def update_table_sort_indicator(window: Any) -> None:
    order = (
        Qt.SortOrder.DescendingOrder
        if window.sort_descending_value
        else Qt.SortOrder.AscendingOrder
    )
    window.image_table.horizontalHeader().setSortIndicator(
        window.sort_column_value, order
    )


def sort_key_for_path(
    window: Any,
    path: Path,
    column: int,
    *,
    table_col_file: int,
    table_col_date_used: int,
    table_col_aspect: int,
) -> object:
    if column == table_col_file:
        return path.name.lower()
    if column == table_col_date_used:
        return window.date_used_for_path(path)
    if column == table_col_aspect:
        needs_crop = 1 if window.path_needs_crop_for_aspect(path) else 0
        aspect = window.source_aspect_ratio_label_for_path(path)
        return (needs_crop, aspect, path.name.lower())
    return path.name.lower()


def apply_table_sort(
    window: Any,
    preferred_path: Path | None,
    *,
    table_col_file: int,
    table_col_date_used: int,
    table_col_aspect: int,
) -> None:
    if not window.image_paths:
        window.update_table_sort_indicator()
        return

    window.image_paths.sort(
        key=lambda path: sort_key_for_path(
            window,
            path,
            window.sort_column_value,
            table_col_file=table_col_file,
            table_col_date_used=table_col_date_used,
            table_col_aspect=table_col_aspect,
        ),
        reverse=window.sort_descending_value,
    )
    window.refresh_image_list_labels(preferred_path)
    window.update_table_sort_indicator()


def on_image_table_header_clicked(window: Any, column: int) -> None:
    if column not in window.sortable_columns:
        window.update_table_sort_indicator()
        return

    preferred_path = window.selected_path()
    if window.sort_column_value == column:
        window.sort_descending_value = not window.sort_descending_value
    else:
        window.sort_column_value = column
        window.sort_descending_value = False

    window.apply_table_sort(preferred_path)
    window.persist_project_settings()


__all__ = [
    "apply_table_sort",
    "on_image_table_header_clicked",
    "sort_key_for_path",
    "update_table_sort_indicator",
]
