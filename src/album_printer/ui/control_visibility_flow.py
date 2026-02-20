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
    window.update_fix_navigation_buttons()
    window.update_fix_needed_message()


def update_folder_settings_availability(window: Any) -> None:
    window.folder_settings_button.setEnabled(True)
    window.folder_settings_action.setEnabled(True)
    available = window.current_source_context_id is not None
    window.refresh_folder_button.setEnabled(available)
    window.refresh_folder_action.setEnabled(available)
    url_source = getattr(window, "current_source_id", None) == "google-photos-album-url"
    if hasattr(window, "refetch_metadata_button"):
        window.refetch_metadata_button.setEnabled(available and url_source)
    if hasattr(window, "refetch_metadata_action"):
        window.refetch_metadata_action.setEnabled(available and url_source)


def update_aspect_navigation_buttons(window: Any) -> None:
    """Legacy: now unified with fix navigation."""
    update_fix_navigation_buttons(window)


def update_date_check_navigation_buttons(window: Any) -> None:
    """Legacy: now unified with fix navigation."""
    update_fix_navigation_buttons(window)


def update_fix_navigation_buttons(window: Any) -> None:
    """Enable Prev/Next need fix when any image has crop or date issue."""
    has_images = bool(window.image_paths)
    has_any_fix = False
    for path in window.image_paths:
        if window.path_needs_fix(path):
            has_any_fix = True
            break
    enabled = bool(has_images and has_any_fix)
    if hasattr(window, "prev_fix_button"):
        window.prev_fix_button.setEnabled(enabled)
    if hasattr(window, "next_fix_button"):
        window.next_fix_button.setEnabled(enabled)


def update_fix_needed_message(window: Any) -> None:
    """Set the fix-needed label to what’s wrong with the current image, or empty."""
    if not hasattr(window, "fix_needed_label"):
        return
    path = window.selected_path()
    if path is None:
        window.fix_needed_label.setText("")
        return
    msg = window.fix_needed_message_for_path(path)
    window.fix_needed_label.setText(msg if msg else "—")


__all__ = [
    "update_aspect_navigation_buttons",
    "update_controls_visibility",
    "update_date_check_navigation_buttons",
    "update_folder_settings_availability",
    "update_fix_navigation_buttons",
    "update_fix_needed_message",
    "update_queue_panel_max_width",
]
