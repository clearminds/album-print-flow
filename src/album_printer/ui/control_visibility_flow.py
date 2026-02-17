from __future__ import annotations

from typing import Any


def update_queue_panel_max_width(window: Any) -> None:
    if not hasattr(window, "queue_panel"):
        return

    header = window.print_queue_table.horizontalHeader()
    header.setStretchLastSection(False)
    window.print_queue_table.resizeColumnsToContents()
    detail_col = 4
    detail_width = window.print_queue_table.columnWidth(detail_col)
    window.print_queue_table.setColumnWidth(detail_col, min(detail_width, 340))
    header.setStretchLastSection(True)

    table_width = (
        window.print_queue_table.verticalHeader().width()
        + window.print_queue_table.frameWidth() * 2
        + sum(
            window.print_queue_table.columnWidth(index)
            for index in range(window.print_queue_table.columnCount())
        )
    )
    panel_width = max(420, table_width + 26)
    window.queue_panel.setMaximumWidth(panel_width)


def update_controls_visibility(window: Any) -> None:
    has_selection = window.selected_path() is not None
    window.controls_widget.setVisible(has_selection)
    if not has_selection and window.crop_reframe_button.isChecked():
        window.crop_reframe_button.setChecked(False)
    window.update_aspect_navigation_buttons()


def update_folder_settings_availability(window: Any) -> None:
    window.folder_settings_button.setEnabled(True)
    window.folder_settings_action.setEnabled(True)
    available = window.current_source_context_id is not None
    window.refresh_folder_button.setEnabled(available)
    window.refresh_folder_action.setEnabled(available)


def update_aspect_navigation_buttons(window: Any) -> None:
    has_images = bool(window.image_paths)
    has_mismatch = False
    for path in window.image_paths:
        cached_values = window.cached_table_values_for_path(path)
        if cached_values is None:
            continue
        _date_text, _location_text, aspect_text = cached_values
        if "⚠" in aspect_text:
            has_mismatch = True
            break
    enabled = bool(has_images and has_mismatch)
    window.crop_prev_mismatch_button.setEnabled(enabled)
    window.crop_next_mismatch_button.setEnabled(enabled)


__all__ = [
    "update_aspect_navigation_buttons",
    "update_controls_visibility",
    "update_folder_settings_availability",
    "update_queue_panel_max_width",
]
