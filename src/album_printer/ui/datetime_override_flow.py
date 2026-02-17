from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from PySide6.QtCore import QDateTime
from PySide6.QtWidgets import QDateTimeEdit, QDialog, QDialogButtonBox, QVBoxLayout


def set_datetime_override_for_selected(window: Any) -> None:
    path = window.selected_path()
    if path is None or window.current_folder is None:
        return

    parsed = window.pick_datetime_override(path)
    if parsed is None:
        return

    window.set_datetime_override_for_path(path, parsed)


def pick_datetime_override(
    window: Any,
    path: Path,
    *,
    parse_datetime_override_fn: Callable[[str], datetime | None],
    datetime_for_image_fn: Callable[[Path], datetime],
) -> datetime | None:
    current_override = str(
        window.image_settings_for_path(path).get("datetime_override", "")
    )
    initial_dt = parse_datetime_override_fn(current_override)
    if initial_dt is None:
        initial_dt = datetime_for_image_fn(path)

    dialog = QDialog(window)
    dialog.setWindowTitle("Set Date/Time")
    layout = QVBoxLayout(dialog)

    picker = QDateTimeEdit(dialog)
    picker.setCalendarPopup(True)
    picker.setDisplayFormat("yyyy-MM-dd HH:mm")
    picker.setDateTime(
        QDateTime(
            initial_dt.year,
            initial_dt.month,
            initial_dt.day,
            initial_dt.hour,
            initial_dt.minute,
            initial_dt.second,
        )
    )
    layout.addWidget(picker)

    buttons = QDialogButtonBox(
        QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
        parent=dialog,
    )
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    layout.addWidget(buttons)

    if dialog.exec() != QDialog.DialogCode.Accepted:
        return None

    return picker.dateTime().toPython()


def set_datetime_override_for_path(window: Any, path: Path, value: datetime) -> None:
    if window.current_folder is None:
        return

    image_settings = window.folder_metadata.get("image_settings")
    if not isinstance(image_settings, dict):
        image_settings = {}
        window.folder_metadata["image_settings"] = image_settings

    key = window.metadata_key_for_path(path)
    existing = image_settings.get(key)
    if not isinstance(existing, dict):
        existing = {}
    existing["datetime_override"] = value.isoformat(timespec="seconds")
    window.set_image_entry_file_hash(path, existing)
    image_settings[key] = existing
    window.save_folder_metadata()
    window.sync_global_source_state_from_path(path)
    window.datetime_override_label.setText(existing["datetime_override"])
    window.refresh_image_list_labels(path)
    window.refresh_preview()


def clear_datetime_override_for_selected(window: Any) -> None:
    path = window.selected_path()
    if path is None or window.current_folder is None:
        return

    image_settings = window.folder_metadata.get("image_settings")
    if not isinstance(image_settings, dict):
        return

    key = window.metadata_key_for_path(path)
    existing = image_settings.get(key)
    if not isinstance(existing, dict):
        return

    existing.pop("datetime_override", None)
    window.set_image_entry_file_hash(path, existing)
    image_settings[key] = existing
    window.save_folder_metadata()
    window.sync_global_source_state_from_path(path)
    window.datetime_override_label.setText("Auto")
    window.refresh_image_list_labels(path)
    window.refresh_preview()


__all__ = [
    "clear_datetime_override_for_selected",
    "pick_datetime_override",
    "set_datetime_override_for_path",
    "set_datetime_override_for_selected",
]
