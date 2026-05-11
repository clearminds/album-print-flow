from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from PIL import Image, ImageEnhance

from album_print_flow.app_primitives import crop_geometry_for_ratio
from PIL.ImageQt import ImageQt
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QMessageBox


def on_image_settings_changed(window: Any) -> None:
    if window._restoring_settings or window.current_folder is None:
        return

    path = window.selected_path()
    if path is None:
        return

    image_settings = window.folder_metadata.get("image_settings")
    if not isinstance(image_settings, dict):
        image_settings = {}
        window.folder_metadata["image_settings"] = image_settings

    key = window.metadata_key_for_path(path)
    existing = image_settings.get(key)
    if not isinstance(existing, dict):
        existing = {}

    existing["orientation"] = window.current_image_orientation
    existing["rotation_degrees"] = window.current_image_rotation_degrees
    existing["brightness_percent"] = window.brightness_slider.value()
    existing["crop_zoom_percent"] = window.crop_zoom_slider.value()
    existing["crop_offset_x_percent"] = window.crop_x_slider.value()
    existing["crop_offset_y_percent"] = window.crop_y_slider.value()
    existing["location_stamp_mode_override"] = (
        window.location_stamp_override_combo.currentText()
    )
    existing["location_stamp_custom_text"] = window.current_custom_location_text()
    window.register_custom_location_text(existing["location_stamp_custom_text"])
    window.set_image_entry_file_hash(path, existing)
    image_settings[key] = existing
    window.refresh_custom_location_text_options(
        preferred_text=existing["location_stamp_custom_text"]
    )
    window.save_folder_metadata()
    window.sync_global_source_state_from_path(path)
    window.invalidate_table_cache_for_path(path)
    mode_override = window.location_stamp_override_combo.currentText().strip()
    if mode_override == "Custom Text":
        window.location_value_label.setText(
            existing["location_stamp_custom_text"] or "No location"
        )
    else:
        effective_format = window.effective_location_format_for_path(path)
        location_text = window.format_location(
            window.location_for_path(path),
            path=path,
            format_value=effective_format,
        )
        window.location_value_label.setText(location_text or "No location")
    window.refresh_image_list_labels(path)


def processing_settings_for_path(
    window: Any,
    path: Path,
    *,
    normalize_rotation_degrees_fn: Callable[[object], int],
    processing_settings_cls: Any,
) -> Any:
    image_settings = window.image_settings_for_path(path)
    resolved_datetime = window.date_used_for_path(path)

    if path == window.selected_path():
        image_settings = {
            **image_settings,
            "orientation": window.current_image_orientation,
            "rotation_degrees": window.current_image_rotation_degrees,
            "brightness_percent": window.brightness_slider.value(),
            "crop_zoom_percent": window.crop_zoom_slider.value(),
            "crop_offset_x_percent": window.crop_x_slider.value(),
            "crop_offset_y_percent": window.crop_y_slider.value(),
            "location_stamp_mode_override": (
                window.location_stamp_override_combo.currentText()
            ),
            "location_stamp_custom_text": window.current_custom_location_text(),
        }

    orientation = str(image_settings.get("orientation", "Landscape"))
    rotation_degrees = normalize_rotation_degrees_fn(
        image_settings.get("rotation_degrees", 0)
    )
    stored_settings = window.folder_metadata.get("image_settings", {})
    entry = None
    if isinstance(stored_settings, dict):
        entry = stored_settings.get(window.metadata_key_for_path(path))
        if not isinstance(entry, dict):
            entry = stored_settings.get(path.name)
            if not isinstance(entry, dict):
                entry = None

    has_explicit_orientation = (
        isinstance(entry, dict)
        and str(entry.get("orientation", "")) in {"Landscape", "Portrait"}
    )

    if not has_explicit_orientation:
        width, height = window.image_dimensions_for_path(path)
        if rotation_degrees in {90, 270}:
            width, height = height, width

        def crop_area(orientation_value: str) -> int:
            _left, _top, crop_w, crop_h = crop_geometry_for_ratio(
                width,
                height,
                orientation_value,
                window.crop_ratio_value,
                int(image_settings.get("crop_zoom_percent", 100)),
                int(image_settings.get("crop_offset_x_percent", 0)),
                int(image_settings.get("crop_offset_y_percent", 0)),
            )
            return max(1, int(crop_w)) * max(1, int(crop_h))

        # Choose the orientation that yields the larger crop area.
        if crop_area("Portrait") > crop_area("Landscape"):
            orientation = "Portrait"

    stamp_mode = window.stamp_mode_value
    clock_mode = window.clock_mode_value
    if orientation == "Portrait":
        corner = window.corner_portrait_value
        location_corner = window.location_corner_portrait_value
    else:
        corner = window.corner_landscape_value
        location_corner = window.location_corner_landscape_value

    mode_override = str(
        image_settings.get("location_stamp_mode_override", "Default")
    ).strip()
    custom_location_text = str(
        image_settings.get("location_stamp_custom_text", "")
    ).strip()

    if mode_override == "Custom Text":
        location_text = custom_location_text
        location_stamp_enabled = bool(location_text)
    else:
        effective_format = window.effective_location_format_for_path(
            path, image_settings
        )
        location_text = window.format_location(
            window.location_for_path(path),
            path=path,
            format_value=effective_format,
        )

        effective_location_stamp_mode = window.location_stamp_mode_value
        if effective_format is None:
            effective_location_stamp_mode = "Off"
        location_stamp_enabled = effective_location_stamp_mode != "Off" and bool(
            location_text
        )

    return processing_settings_cls(
        orientation=orientation,
        rotation_degrees=rotation_degrees,
        brightness_percent=int(image_settings.get("brightness_percent", 100)),
        crop_ratio=window.crop_ratio_value,
        crop_zoom_percent=int(image_settings.get("crop_zoom_percent", 100)),
        crop_offset_x_percent=int(image_settings.get("crop_offset_x_percent", 0)),
        crop_offset_y_percent=int(image_settings.get("crop_offset_y_percent", 0)),
        stamp_mode=stamp_mode,
        clock_mode=clock_mode,
        corner=corner,
        stamp_font=window.stamp_font_value,
        stamp_scale_percent=window.stamp_scale_percent,
        stamp_offset_x_px=window.stamp_offset_x_px,
        stamp_offset_y_px=window.stamp_offset_y_px,
        stamp_color=window.stamp_color_value,
        stamp_border_color=window.stamp_border_color_value,
        stamp_vertical=window.stamp_vertical_value,
        stamp_adaptive_text=window.stamp_adaptive_text_value,
        adaptive_luminance_threshold=window.adaptive_luminance_threshold_value,
        datetime_override=resolved_datetime,
        location_text=location_text,
        location_stamp_enabled=location_stamp_enabled,
        location_corner=location_corner,
        location_stamp_scale_percent=window.location_stamp_scale_percent,
        location_stamp_offset_x_px=window.location_stamp_offset_x_px,
        location_stamp_offset_y_px=window.location_stamp_offset_y_px,
        location_stamp_color=window.location_stamp_color_value,
        location_stamp_border_color=window.location_stamp_border_color_value,
        location_stamp_vertical=window.location_stamp_vertical_value,
        location_stamp_adaptive_text=window.location_stamp_adaptive_text_value,
    )


def refresh_preview(
    window: Any,
    *,
    load_image_as_rgb_fn: Callable[..., Any],
    apply_manual_rotation_fn: Callable[[Any, int], Any],
    render_preview_image_fn: Callable[..., Any],
) -> None:
    path = window.selected_path()
    if path is None:
        window.preview_source_size = (0, 0)
        window.preview_display_rect = (0, 0, 0, 0)
        window.preview_label.set_overlay_rect(None)
        window.preview_render_state_key = None
        return

    settings = window.processing_settings_for_path(path)
    reframe_active = window.crop_reframe_button.isChecked()
    max_preview_dimension = max(
        1200,
        int(max(window.preview_label.width(), window.preview_label.height()) * 2),
    )
    viewport_size = window.preview_container.viewport().size()
    try:
        path_stat = path.stat()
        path_mtime_ns = int(path_stat.st_mtime_ns)
        path_size = int(path_stat.st_size)
    except OSError:
        path_mtime_ns = 0
        path_size = 0
    preview_key = (
        str(path),
        path_mtime_ns,
        path_size,
        reframe_active,
        max_preview_dimension,
        int(viewport_size.width()),
        int(viewport_size.height()),
        settings.orientation,
        settings.rotation_degrees,
        settings.brightness_percent,
        settings.crop_ratio,
        settings.crop_zoom_percent,
        settings.crop_offset_x_percent,
        settings.crop_offset_y_percent,
        settings.stamp_mode,
        settings.clock_mode,
        settings.corner,
        settings.stamp_font,
        settings.stamp_scale_percent,
        settings.stamp_offset_x_px,
        settings.stamp_offset_y_px,
        settings.stamp_color,
        settings.stamp_border_color,
        settings.stamp_vertical,
        settings.stamp_adaptive_text,
        settings.adaptive_luminance_threshold,
        (settings.datetime_override.isoformat() if settings.datetime_override else ""),
        settings.location_text,
        settings.location_stamp_enabled,
        settings.location_corner,
        settings.location_stamp_scale_percent,
        settings.location_stamp_offset_x_px,
        settings.location_stamp_offset_y_px,
        settings.location_stamp_color,
        settings.location_stamp_border_color,
        settings.location_stamp_vertical,
        settings.location_stamp_adaptive_text,
    )
    if preview_key == window.preview_render_state_key:
        window.update_location_status_for_path(path)
        return
    window.preview_render_state_key = preview_key

    try:
        if reframe_active:
            image = load_image_as_rgb_fn(
                path,
                debug_logger=lambda message: window.append_log("DEBUG", message),
            )
            image = apply_manual_rotation_fn(image, settings.rotation_degrees)
            longest = max(image.width, image.height)
            if longest > max_preview_dimension:
                scale = max_preview_dimension / float(longest)
                resized = (
                    max(1, int(round(image.width * scale))),
                    max(1, int(round(image.height * scale))),
                )
                image = image.resize(resized, Image.Resampling.LANCZOS)
            image = ImageEnhance.Brightness(image).enhance(
                settings.brightness_percent / 100.0
            )
            window.preview_source_size = (max(1, image.width), max(1, image.height))
        else:
            image = render_preview_image_fn(
                path,
                settings,
                max_preview_dimension,
                debug_logger=lambda message: window.append_log("DEBUG", message),
            )
            window.preview_source_size = (0, 0)
    except OSError as error:
        window.preview_render_state_key = None
        QMessageBox.critical(window, "Preview failed", str(error))
        window.preview_source_size = (0, 0)
        window.preview_display_rect = (0, 0, 0, 0)
        window.preview_label.set_overlay_rect(None)
        return

    qt_image = QImage(ImageQt(image))
    pixmap = QPixmap.fromImage(qt_image)
    scaled = pixmap.scaled(
        int(viewport_size.width()),
        int(viewport_size.height()),
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
    window.preview_scaled_size = (scaled.width(), scaled.height())
    label_w = max(0, viewport_size.width())
    label_h = max(0, viewport_size.height())
    scaled_w = max(0, scaled.width())
    scaled_h = max(0, scaled.height())
    left = max(0, (label_w - scaled_w) // 2)
    top = max(0, (label_h - scaled_h) // 2)
    window.preview_display_rect = (left, top, scaled_w, scaled_h)
    window.preview_label.setPixmap(scaled)
    if reframe_active:
        window.update_preview_overlay_rect()
    else:
        window.preview_label.set_overlay_enabled(False)
        window.preview_label.set_overlay_rect(None)

    window.update_location_status_for_path(path)


def on_image_changed(window: Any, row: int) -> None:
    window.current_index = row
    window.update_controls_visibility()
    window.update_selected_print_info()
    if row < 0 or row >= len(window.image_paths):
        if window.crop_reframe_button.isChecked():
            window.crop_reframe_button.setChecked(False)
        window.preview_label.setText("Load photos to begin")
        window.preview_label.setPixmap(QPixmap())
        window.preview_source_size = (0, 0)
        window.preview_display_rect = (0, 0, 0, 0)
        window.preview_label.set_overlay_rect(None)
        window.location_value_label.setText("No location")
        window.location_stamp_override_combo.setCurrentText("Default")
        window.ignore_for_print_all_checkbox.setChecked(False)
        return
    window.restore_image_settings_for_selected()
    window.refresh_preview()
    window.focus_location_areas_panel_for_path(window.selected_path())


def on_image_table_selection_changed(window: Any, current_row: int) -> None:
    window.on_image_changed(current_row)


__all__ = [
    "on_image_changed",
    "on_image_settings_changed",
    "on_image_table_selection_changed",
    "processing_settings_for_path",
    "refresh_preview",
]
