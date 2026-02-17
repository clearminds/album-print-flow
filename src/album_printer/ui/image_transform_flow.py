from __future__ import annotations

from typing import Any


def update_crop_orientation_button_text(window: Any) -> None:
    window.crop_orientation_button.setText(f"Crop: {window.current_image_orientation}")


def update_rotate_image_button_text(window: Any) -> None:
    window.rotate_image_label.setText(f"{window.current_image_rotation_degrees}°")


def toggle_crop_orientation(window: Any) -> None:
    if window.current_folder is None or window.selected_path() is None:
        return

    window.current_image_orientation = (
        "Portrait" if window.current_image_orientation == "Landscape" else "Landscape"
    )
    window.update_crop_orientation_button_text()
    window.on_image_settings_changed()
    window.refresh_preview()


def rotate_selected_image_clockwise(window: Any) -> None:
    if window.current_folder is None or window.selected_path() is None:
        return
    window.current_image_rotation_degrees = (
        window.current_image_rotation_degrees + 90
    ) % 360
    window.update_rotate_image_button_text()
    window.on_image_settings_changed()
    window.refresh_preview()


def reset_selected_image_rotation(window: Any) -> None:
    if window.current_folder is None or window.selected_path() is None:
        return
    if window.current_image_rotation_degrees == 0:
        return
    window.current_image_rotation_degrees = 0
    window.update_rotate_image_button_text()
    window.on_image_settings_changed()
    window.refresh_preview()
