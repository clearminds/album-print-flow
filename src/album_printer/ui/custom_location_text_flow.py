from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import QMessageBox

from album_printer.ui.status_presenter import present_status


def load_custom_location_text_history(window: Any) -> None:
    raw_values = window.ui_settings.value("ui/location_custom_text_history", [])
    if isinstance(raw_values, str):
        candidates = [raw_values]
    elif isinstance(raw_values, list | tuple):
        candidates = [str(value) for value in raw_values]
    else:
        candidates = []

    values: list[str] = []
    for candidate in candidates:
        text = str(candidate).strip()
        if text and text not in values:
            values.append(text)
    window.location_custom_text_history = values


def save_custom_location_text_history(window: Any) -> None:
    window.ui_settings.setValue(
        "ui/location_custom_text_history",
        window.location_custom_text_history,
    )
    window.ui_settings.sync()


def register_custom_location_text(window: Any, text: str) -> None:
    normalized = str(text).strip()
    if not normalized:
        return
    if any(
        existing.casefold() == normalized.casefold()
        for existing in window.location_custom_text_history
    ):
        return
    window.location_custom_text_history.append(normalized)
    window.location_custom_text_history = window.location_custom_text_history[-200:]
    window.save_custom_location_text_history()


def current_custom_location_text(window: Any) -> str:
    return str(window.location_custom_text_combo.currentText() or "").strip()


def copy_location_from_previous_image(window: Any) -> None:
    row = window.image_table.currentRow()
    if row <= 0 or row >= len(window.image_paths):
        QMessageBox.information(
            window,
            "Copy Previous Location",
            "No previous image available.",
        )
        return

    previous_path = window.image_paths[row - 1]
    previous_values = window.image_settings_for_path(previous_path)
    previous_mode = str(
        previous_values.get("location_stamp_mode_override", "Default")
    ).strip()

    copied_text = ""
    if previous_mode == "Custom Text":
        copied_text = str(previous_values.get("location_stamp_custom_text", "")).strip()
    else:
        previous_format = window.effective_location_format_for_path(
            previous_path,
            previous_values,
        )
        copied_text = window.format_location(
            window.location_for_path(previous_path),
            path=previous_path,
            format_value=previous_format,
        ).strip()

    if not copied_text:
        QMessageBox.information(
            window,
            "Copy Previous Location",
            "Previous image has no location text.",
        )
        return

    window.location_stamp_override_combo.setCurrentText("Custom Text")
    window.refresh_custom_location_text_options(preferred_text=copied_text)
    window.location_custom_text_combo.setEditText(copied_text)
    window.on_image_settings_changed()
    window.refresh_preview()
    present_status(
        window, f"Copied previous location to custom text: {previous_path.name}"
    )


def refresh_custom_location_text_options(
    window: Any,
    preferred_text: str | None = None,
) -> None:
    image_settings = window.folder_metadata.get("image_settings")
    if not isinstance(image_settings, dict):
        image_settings = {}

    values: set[str] = {
        str(value).strip()
        for value in window.location_custom_text_history
        if str(value).strip()
    }
    for path in window.image_paths:
        key = window.metadata_key_for_path(path)
        entry = image_settings.get(key)
        if not isinstance(entry, dict):
            continue
        text = str(entry.get("location_stamp_custom_text", "")).strip()
        if text:
            values.add(text)

    selected_text = (
        str(preferred_text).strip()
        if preferred_text is not None
        else window.current_custom_location_text()
    )
    options = sorted(values, key=lambda value: value.lower())

    window.location_custom_text_combo.blockSignals(True)
    window.location_custom_text_combo.clear()
    for option in options:
        window.location_custom_text_combo.addItem(option)
    window.location_custom_text_combo.setEditText(selected_text)
    window.location_custom_text_combo.blockSignals(False)


__all__ = [
    "copy_location_from_previous_image",
    "current_custom_location_text",
    "load_custom_location_text_history",
    "refresh_custom_location_text_options",
    "register_custom_location_text",
    "save_custom_location_text_history",
]
