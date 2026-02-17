from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtWidgets import QMessageBox


def selected_paths_for_printing(window: Any) -> list[Path]:
    selected_rows = [
        index.row() for index in window.image_table.selectionModel().selectedRows()
    ]
    selected_rows.sort()

    paths: list[Path] = []
    seen: set[Path] = set()
    for row in selected_rows:
        if row < 0 or row >= len(window.image_paths):
            continue
        path = window.image_paths[row]
        if path in seen:
            continue
        seen.add(path)
        paths.append(path)

    if paths:
        return paths

    current = window.selected_path()
    if current is None:
        return []
    return [current]


def print_selected(window: Any) -> None:
    paths = window.selected_paths_for_printing()
    if not paths:
        QMessageBox.information(
            window, "Nothing selected", "Select one or more images first."
        )
        return
    window.print_paths(paths)


def print_all(window: Any) -> None:
    candidates = [
        path for path in window.image_paths if window.should_include_in_print_all(path)
    ]
    if not candidates:
        QMessageBox.information(
            window,
            "Print All",
            "No images are eligible for Print All (ignored or already printed).",
        )
        return
    skipped = len(window.image_paths) - len(candidates)
    if skipped > 0:
        window.append_log(
            "INFO",
            f"Print All filtered {skipped} image(s) (ignored/already printed)",
        )
    window.print_paths(candidates)


def print_paths(window: Any, paths: list[Path]) -> None:
    if not paths:
        QMessageBox.information(window, "Nothing to print", "Load images first.")
        window.append_log("INFO", "Print requested with no images loaded")
        return

    window.enqueue_print_paths(paths)


__all__ = [
    "print_all",
    "print_paths",
    "print_selected",
    "selected_paths_for_printing",
]
