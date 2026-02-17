from __future__ import annotations

from typing import Any

from album_printer.ui.status_presenter import present_status


def select_previous(window: Any, *, table_col_file: int) -> None:
    if not window.image_paths:
        return
    window.image_table.setCurrentCell(
        max(0, window.image_table.currentRow() - 1),
        table_col_file,
    )


def select_next(window: Any, *, table_col_file: int) -> None:
    if not window.image_paths:
        return
    window.image_table.setCurrentCell(
        min(len(window.image_paths) - 1, window.image_table.currentRow() + 1),
        table_col_file,
    )


def select_aspect_mismatch(window: Any, step: int, *, table_col_file: int) -> None:
    total = len(window.image_paths)
    if total <= 0:
        return
    current = window.image_table.currentRow()
    if step > 0:
        start_index = max(-1, current)
        for index in range(start_index + 1, total):
            path = window.image_paths[index]
            if window.path_needs_crop_for_aspect(path):
                window.image_table.setCurrentCell(index, table_col_file)
                return
        present_status(window, "We are on last image now", 2000)
        return

    start_index = current if 0 <= current < total else total
    for index in range(start_index - 1, -1, -1):
        path = window.image_paths[index]
        if window.path_needs_crop_for_aspect(path):
            window.image_table.setCurrentCell(index, table_col_file)
            return
    present_status(window, "We are on first image now", 2000)


def select_previous_aspect_mismatch(window: Any) -> None:
    window.select_aspect_mismatch(-1)


def select_next_aspect_mismatch(window: Any) -> None:
    window.select_aspect_mismatch(1)


__all__ = [
    "select_aspect_mismatch",
    "select_next",
    "select_next_aspect_mismatch",
    "select_previous",
    "select_previous_aspect_mismatch",
]
