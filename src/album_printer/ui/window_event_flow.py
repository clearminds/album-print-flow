from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any


def close_event(
    window: Any, event: object, *, super_close_event_fn: Callable[[object], None]
) -> None:
    window.save_app_project_settings()
    window.save_app_print_settings()
    window.save_nominatim_settings()
    window.save_nominatim_cache()
    window.save_ui_state()
    super_close_event_fn(event)


def resize_event(
    window: Any, event: object, *, super_resize_event_fn: Callable[[object], None]
) -> None:
    super_resize_event_fn(event)
    window.refresh_preview()


def apply_sort_order(window: Any, preferred_path: Path | None = None) -> None:
    window.apply_table_sort(preferred_path)


def on_image_table_cell_double_clicked(window: Any, row: int, column: int) -> None:
    _ = window
    _ = row
    _ = column
    return


def on_image_table_cell_changed(window: Any, row: int, column: int) -> None:
    _ = window
    _ = row
    _ = column
    return


__all__ = [
    "apply_sort_order",
    "close_event",
    "on_image_table_cell_changed",
    "on_image_table_cell_double_clicked",
    "resize_event",
]
