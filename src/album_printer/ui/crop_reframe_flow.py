from __future__ import annotations

from collections.abc import Callable
from typing import Any


def on_crop_reframe_toggled(window: Any, enabled: bool) -> None:
    window.preview_label.set_drag_enabled(enabled)
    window.preview_label.set_overlay_enabled(enabled)
    window._reframe_drag_active = False
    window._reframe_interaction_mode = "pan"
    window._reframe_resize_corner = None
    window._reframe_pan_accum_x = 0.0
    window._reframe_pan_accum_y = 0.0
    window._reframe_zoom_accum = 0.0
    if enabled:
        window.crop_reframe_button.setText("Reframe Crop (On)")
        window.refresh_preview()
    else:
        window.crop_reframe_button.setText("Reframe Crop")
        window.preview_label.set_overlay_rect(None)
        window.refresh_preview()


def reset_crop_for_selected(window: Any) -> None:
    if window.selected_path() is None:
        return
    window.crop_zoom_slider.setValue(100)
    window.crop_x_slider.setValue(0)
    window.crop_y_slider.setValue(0)
    window.on_image_settings_changed()
    window.refresh_preview()


def resize_corner_at(
    window: Any, x: int, y: int, *, reframe_handle_size: int
) -> str | None:
    rect = window.compute_overlay_rect_for_current_crop()
    if rect is None:
        return None
    left, top, width, height = rect
    if width <= 0 or height <= 0:
        return None
    right = left + width
    bottom = top + height
    threshold = int(reframe_handle_size)
    corners = {
        "top_left": (left, top),
        "top_right": (right, top),
        "bottom_left": (left, bottom),
        "bottom_right": (right, bottom),
    }
    for name, (cx, cy) in corners.items():
        if abs(x - cx) <= threshold and abs(y - cy) <= threshold:
            return name
    return None


def on_preview_drag_started(
    window: Any,
    x: int,
    y: int,
    *,
    reframe_handle_size: int,
) -> None:
    if not window.crop_reframe_button.isChecked():
        window._reframe_interaction_mode = "pan"
        window._reframe_resize_corner = None
        return

    window._reframe_drag_active = False
    window._reframe_pan_accum_x = 0.0
    window._reframe_pan_accum_y = 0.0
    window._reframe_zoom_accum = 0.0

    corner = resize_corner_at(window, x, y, reframe_handle_size=reframe_handle_size)
    if corner is None:
        window._reframe_interaction_mode = "pan"
        window._reframe_resize_corner = None
        return

    window._reframe_interaction_mode = "resize"
    window._reframe_resize_corner = corner


def on_preview_dragged(
    window: Any, delta_x: int, delta_y: int, _x: int, _y: int
) -> None:
    if not window.crop_reframe_button.isChecked():
        return
    if window.selected_path() is None:
        return

    _px, _py, width, height = window.preview_display_rect
    width = max(0, int(width))
    height = max(0, int(height))
    if width <= 0 or height <= 0:
        return

    if window._reframe_interaction_mode == "resize":
        corner = window._reframe_resize_corner or "bottom_right"
        if corner == "bottom_right":
            effective = (delta_x + delta_y) / 2.0
        elif corner == "top_left":
            effective = (-delta_x - delta_y) / 2.0
        elif corner == "top_right":
            effective = (delta_x - delta_y) / 2.0
        else:
            effective = (-delta_x + delta_y) / 2.0

        window._reframe_zoom_accum += (-effective) * 0.35
        zoom_step = int(window._reframe_zoom_accum)
        if zoom_step:
            current_zoom = window.crop_zoom_slider.value()
            next_zoom = max(100, min(300, current_zoom + zoom_step))
            window._reframe_zoom_accum -= zoom_step
            if next_zoom != current_zoom:
                window._reframe_drag_active = True
                window.crop_zoom_slider.blockSignals(True)
                try:
                    window.crop_zoom_slider.setValue(next_zoom)
                finally:
                    window.crop_zoom_slider.blockSignals(False)
                window.crop_zoom_label.setText(f"{next_zoom}%")
                window.update_preview_overlay_rect()
        return

    window._reframe_pan_accum_x += (delta_x / width) * 200.0
    window._reframe_pan_accum_y += (delta_y / height) * 200.0
    delta_percent_x = int(window._reframe_pan_accum_x)
    delta_percent_y = int(window._reframe_pan_accum_y)

    if delta_percent_x:
        window._reframe_pan_accum_x -= delta_percent_x
    if delta_percent_y:
        window._reframe_pan_accum_y -= delta_percent_y

    updated = False
    current_x = window.crop_x_slider.value()
    current_y = window.crop_y_slider.value()

    next_x = current_x
    next_y = current_y

    if delta_percent_x:
        next_x = max(-100, min(100, current_x + delta_percent_x))
    if delta_percent_y:
        next_y = max(-100, min(100, current_y + delta_percent_y))

    if next_x != current_x:
        window.crop_x_slider.blockSignals(True)
        try:
            window.crop_x_slider.setValue(next_x)
        finally:
            window.crop_x_slider.blockSignals(False)
        window.crop_x_label.setText(str(next_x))
        updated = True

    if next_y != current_y:
        window.crop_y_slider.blockSignals(True)
        try:
            window.crop_y_slider.setValue(next_y)
        finally:
            window.crop_y_slider.blockSignals(False)
        window.crop_y_label.setText(str(next_y))
        updated = True

    if updated:
        window._reframe_drag_active = True
        window.update_preview_overlay_rect()


def on_preview_drag_released(window: Any, _x: int, _y: int) -> None:
    window._reframe_interaction_mode = "pan"
    window._reframe_resize_corner = None
    window._reframe_pan_accum_x = 0.0
    window._reframe_pan_accum_y = 0.0
    window._reframe_zoom_accum = 0.0
    if not window._reframe_drag_active:
        return
    window._reframe_drag_active = False
    window.on_image_settings_changed()
    window.refresh_preview()


def compute_overlay_rect_for_current_crop(
    window: Any,
    *,
    crop_geometry_for_ratio_fn: Callable[
        [int, int, str, str, int, int, int], tuple[int, int, int, int]
    ],
) -> tuple[int, int, int, int] | None:
    path = window.selected_path()
    if path is None:
        return None
    source_width, source_height = window.preview_source_size
    display_x, display_y, display_w, display_h = window.preview_display_rect
    if source_width <= 0 or source_height <= 0:
        return None
    if display_w <= 0 or display_h <= 0:
        return None

    settings = window.processing_settings_for_path(path)
    crop_left, crop_top, crop_w, crop_h = crop_geometry_for_ratio_fn(
        source_width,
        source_height,
        settings.orientation,
        settings.crop_ratio,
        settings.crop_zoom_percent,
        settings.crop_offset_x_percent,
        settings.crop_offset_y_percent,
    )
    if crop_w <= 0 or crop_h <= 0:
        return None

    scale_x = display_w / source_width
    scale_y = display_h / source_height

    x1 = display_x + int(round(crop_left * scale_x))
    y1 = display_y + int(round(crop_top * scale_y))
    x2 = display_x + int(round((crop_left + crop_w) * scale_x))
    y2 = display_y + int(round((crop_top + crop_h) * scale_y))

    min_x = display_x
    min_y = display_y
    max_x = display_x + display_w
    max_y = display_y + display_h

    x1 = max(min_x, min(max_x, x1))
    y1 = max(min_y, min(max_y, y1))
    x2 = max(min_x, min(max_x, x2))
    y2 = max(min_y, min(max_y, y2))

    width = max(1, x2 - x1)
    height = max(1, y2 - y1)
    return x1, y1, width, height


def update_preview_overlay_rect(window: Any) -> None:
    overlay_enabled = window.crop_reframe_button.isChecked()
    window.preview_label.set_overlay_enabled(overlay_enabled)
    if not overlay_enabled:
        window.preview_label.set_overlay_rect(None)
        return
    window.preview_label.set_overlay_rect(
        window.compute_overlay_rect_for_current_crop()
    )


__all__ = [
    "compute_overlay_rect_for_current_crop",
    "on_crop_reframe_toggled",
    "on_preview_drag_released",
    "on_preview_drag_started",
    "on_preview_dragged",
    "reset_crop_for_selected",
    "resize_corner_at",
    "update_preview_overlay_rect",
]
