from __future__ import annotations

from pathlib import Path
from typing import Any


def current_project_settings_payload(window: Any) -> dict[str, object]:
    return {
        "crop_ratio": window.crop_ratio_value,
        "stamp_mode": window.stamp_mode_value,
        "clock_mode": window.clock_mode_value,
        "corner_landscape": window.corner_landscape_value,
        "corner_portrait": window.corner_portrait_value,
        "sort_mode": window.sort_mode_value,
        "sort_column": window.sort_column_value,
        "sort_descending": window.sort_descending_value,
        "stamp_font": window.stamp_font_value,
        "stamp_scale_percent": window.stamp_scale_percent,
        "stamp_offset_x_px": window.stamp_offset_x_px,
        "stamp_offset_y_px": window.stamp_offset_y_px,
        "stamp_color": window.stamp_color_value,
        "stamp_border_color": window.stamp_border_color_value,
        "stamp_vertical": window.stamp_vertical_value,
        "stamp_adaptive_text": window.stamp_adaptive_text_value,
        "adaptive_luminance_threshold": window.adaptive_luminance_threshold_value,
        "location_stamp_mode": window.location_stamp_mode_value,
        "location_format": window.location_format_value,
        "location_corner_landscape": window.location_corner_landscape_value,
        "location_corner_portrait": window.location_corner_portrait_value,
        "location_stamp_scale_percent": window.location_stamp_scale_percent,
        "location_stamp_offset_x_px": window.location_stamp_offset_x_px,
        "location_stamp_offset_y_px": window.location_stamp_offset_y_px,
        "location_stamp_color": window.location_stamp_color_value,
        "location_stamp_border_color": window.location_stamp_border_color_value,
        "location_stamp_vertical": window.location_stamp_vertical_value,
        "location_stamp_adaptive_text": window.location_stamp_adaptive_text_value,
    }


def persist_project_settings(window: Any) -> None:
    window.save_app_project_settings()


def load_app_project_settings(
    window: Any,
    *,
    load_project_settings_from_store_fn: Any,
    crop_ratios: set[str],
    sort_modes: set[str],
    stamp_fonts: set[str],
    stamp_scale_min_percent: int,
    stamp_scale_max_percent: int,
    stamp_offset_min_px: int,
    stamp_offset_max_px: int,
) -> None:
    defaults: dict[str, object] = {
        "crop_ratio": window.crop_ratio_value,
        "stamp_mode": window.stamp_mode_value,
        "clock_mode": window.clock_mode_value,
        "corner_landscape": window.corner_landscape_value,
        "corner_portrait": window.corner_portrait_value,
        "sort_mode": window.sort_mode_value,
        "sort_column": window.sort_column_value,
        "sort_descending": window.sort_descending_value,
        "stamp_font": window.stamp_font_value,
        "stamp_scale_percent": window.stamp_scale_percent,
        "stamp_offset_x_px": window.stamp_offset_x_px,
        "stamp_offset_y_px": window.stamp_offset_y_px,
        "stamp_color": window.stamp_color_value,
        "stamp_border_color": window.stamp_border_color_value,
        "stamp_vertical": window.stamp_vertical_value,
        "stamp_adaptive_text": window.stamp_adaptive_text_value,
        "adaptive_luminance_threshold": window.adaptive_luminance_threshold_value,
        "location_stamp_mode": window.location_stamp_mode_value,
        "location_format": window.location_format_value,
        "location_format_template": window.location_format_template_value,
        "location_corner_landscape": window.location_corner_landscape_value,
        "location_corner_portrait": window.location_corner_portrait_value,
        "location_stamp_scale_percent": window.location_stamp_scale_percent,
        "location_stamp_offset_x_px": window.location_stamp_offset_x_px,
        "location_stamp_offset_y_px": window.location_stamp_offset_y_px,
        "location_stamp_color": window.location_stamp_color_value,
        "location_stamp_border_color": window.location_stamp_border_color_value,
        "location_stamp_vertical": window.location_stamp_vertical_value,
        "location_stamp_adaptive_text": window.location_stamp_adaptive_text_value,
    }
    values = load_project_settings_from_store_fn(
        window.ui_settings,
        defaults,
        crop_ratios=crop_ratios,
        sort_modes=sort_modes,
        sortable_columns=set(window.sortable_columns),
        stamp_fonts=stamp_fonts,
        stamp_scale_min=stamp_scale_min_percent,
        stamp_scale_max=stamp_scale_max_percent,
        stamp_offset_min=stamp_offset_min_px,
        stamp_offset_max=stamp_offset_max_px,
    )

    window.crop_ratio_value = str(values["crop_ratio"])
    window.stamp_mode_value = str(values["stamp_mode"])
    window.clock_mode_value = str(values["clock_mode"])
    window.corner_landscape_value = str(values["corner_landscape"])
    window.corner_portrait_value = str(values["corner_portrait"])
    window.sort_mode_value = str(values["sort_mode"])
    window.sort_column_value = int(values["sort_column"])
    window.sort_descending_value = bool(values["sort_descending"])
    window.stamp_font_value = str(values["stamp_font"])
    window.stamp_scale_percent = int(values["stamp_scale_percent"])
    window.stamp_offset_x_px = int(values["stamp_offset_x_px"])
    window.stamp_offset_y_px = int(values["stamp_offset_y_px"])
    window.stamp_color_value = str(values["stamp_color"])
    window.stamp_border_color_value = str(values["stamp_border_color"])
    window.stamp_vertical_value = bool(values["stamp_vertical"])
    window.stamp_adaptive_text_value = bool(values["stamp_adaptive_text"])
    window.adaptive_luminance_threshold_value = int(
        values["adaptive_luminance_threshold"]
    )
    window.location_stamp_mode_value = str(values["location_stamp_mode"])
    window.location_format_value = str(values["location_format"])
    window.location_format_template_value = str(values["location_format_template"])
    window.location_corner_landscape_value = str(values["location_corner_landscape"])
    window.location_corner_portrait_value = str(values["location_corner_portrait"])
    window.location_stamp_scale_percent = int(values["location_stamp_scale_percent"])
    window.location_stamp_offset_x_px = int(values["location_stamp_offset_x_px"])
    window.location_stamp_offset_y_px = int(values["location_stamp_offset_y_px"])
    window.location_stamp_color_value = str(values["location_stamp_color"])
    window.location_stamp_border_color_value = str(
        values["location_stamp_border_color"]
    )
    window.location_stamp_vertical_value = bool(values["location_stamp_vertical"])
    window.location_stamp_adaptive_text_value = bool(
        values["location_stamp_adaptive_text"]
    )


def save_app_project_settings(
    window: Any,
    *,
    save_project_settings_to_store_fn: Any,
) -> None:
    save_project_settings_to_store_fn(
        window.ui_settings,
        {
            "crop_ratio": window.crop_ratio_value,
            "stamp_mode": window.stamp_mode_value,
            "clock_mode": window.clock_mode_value,
            "corner_landscape": window.corner_landscape_value,
            "corner_portrait": window.corner_portrait_value,
            "sort_mode": window.sort_mode_value,
            "sort_column": window.sort_column_value,
            "sort_descending": window.sort_descending_value,
            "stamp_font": window.stamp_font_value,
            "stamp_scale_percent": window.stamp_scale_percent,
            "stamp_offset_x_px": window.stamp_offset_x_px,
            "stamp_offset_y_px": window.stamp_offset_y_px,
            "stamp_color": window.stamp_color_value,
            "stamp_border_color": window.stamp_border_color_value,
            "stamp_vertical": window.stamp_vertical_value,
            "stamp_adaptive_text": window.stamp_adaptive_text_value,
            "adaptive_luminance_threshold": window.adaptive_luminance_threshold_value,
            "location_stamp_mode": window.location_stamp_mode_value,
            "location_format": window.location_format_value,
            "location_format_template": window.location_format_template_value,
            "location_corner_landscape": window.location_corner_landscape_value,
            "location_corner_portrait": window.location_corner_portrait_value,
            "location_stamp_scale_percent": window.location_stamp_scale_percent,
            "location_stamp_offset_x_px": window.location_stamp_offset_x_px,
            "location_stamp_offset_y_px": window.location_stamp_offset_y_px,
            "location_stamp_color": window.location_stamp_color_value,
            "location_stamp_border_color": window.location_stamp_border_color_value,
            "location_stamp_vertical": window.location_stamp_vertical_value,
            "location_stamp_adaptive_text": window.location_stamp_adaptive_text_value,
        },
    )


def load_app_print_settings(
    window: Any,
    *,
    print_backends: set[str],
    paper_labels: set[str],
) -> None:
    def as_bool(value: object, default: bool) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            return value != 0
        if isinstance(value, str):
            text = value.strip().lower()
            if text in {"1", "true", "yes", "on"}:
                return True
            if text in {"0", "false", "no", "off", ""}:
                return False
        return default

    def as_int(value: object, default: int) -> int:
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            try:
                return int(value.strip())
            except ValueError:
                return default
        return default

    backend = str(
        window.ui_settings.value("print/backend", window.print_backend_value)
    ).strip()
    if backend in print_backends:
        window.print_backend_value = backend

    ipp_uri = str(window.ui_settings.value("print/ipp_uri", window.ipp_uri_value))
    window.ipp_uri_value = ipp_uri.strip()
    window.ipp_wait_for_completion_value = as_bool(
        window.ui_settings.value(
            "print/ipp_wait_for_completion", window.ipp_wait_for_completion_value
        ),
        window.ipp_wait_for_completion_value,
    )

    export_root = str(
        window.ui_settings.value("print/export_root", window.export_root_value)
    )
    window.export_root_value = export_root.strip()

    window.printer_value = str(
        window.ui_settings.value("print/printer", window.printer_value)
    ).strip()
    window.cups_media_value = str(
        window.ui_settings.value("print/cups_media", window.cups_media_value)
    ).strip()
    window.cups_media_type_value = str(
        window.ui_settings.value("print/cups_media_type", window.cups_media_type_value)
    ).strip()
    window.cups_print_quality_value = str(
        window.ui_settings.value(
            "print/cups_print_quality", window.cups_print_quality_value
        )
    ).strip()
    window.cups_media_key = (
        str(
            window.ui_settings.value("print/cups_media_key", window.cups_media_key)
        ).strip()
        or "media"
    )
    window.cups_media_type_key = (
        str(
            window.ui_settings.value(
                "print/cups_media_type_key", window.cups_media_type_key
            )
        ).strip()
        or "media-type"
    )
    window.cups_print_quality_key = (
        str(
            window.ui_settings.value(
                "print/cups_print_quality_key", window.cups_print_quality_key
            )
        ).strip()
        or "print-quality"
    )
    paper_value = str(
        window.ui_settings.value("print/paper", window.paper_value)
    ).strip()
    if paper_value in paper_labels:
        window.paper_value = paper_value
    borderless_mode = str(
        window.ui_settings.value("print/borderless_mode", window.borderless_mode_value)
    ).strip()
    if borderless_mode in {"default", "enabled", "disabled"}:
        window.borderless_mode_value = borderless_mode
    else:
        legacy_borderless = as_bool(
            window.ui_settings.value("print/borderless", True), True
        )
        window.borderless_mode_value = "enabled" if legacy_borderless else "disabled"

    raw_borderless_scale = as_int(
        window.ui_settings.value(
            "print/borderless_content_scale_percent",
            window.borderless_content_scale_percent,
        ),
        window.borderless_content_scale_percent,
    )
    window.borderless_content_scale_percent = max(85, min(110, raw_borderless_scale))

    orientation = str(
        window.ui_settings.value("print/orientation", window.print_orientation_value)
    ).strip()
    if orientation in {"Portrait", "Landscape"}:
        window.print_orientation_value = orientation


def save_app_print_settings(window: Any) -> None:
    window.ui_settings.setValue("print/backend", window.print_backend_value)
    window.ui_settings.setValue("print/ipp_uri", window.ipp_uri_value)
    window.ui_settings.setValue(
        "print/ipp_wait_for_completion", window.ipp_wait_for_completion_value
    )
    window.ui_settings.setValue("print/export_root", window.export_root_value)
    window.ui_settings.setValue("print/printer", window.printer_value)
    window.ui_settings.setValue("print/cups_media", window.cups_media_value)
    window.ui_settings.setValue("print/cups_media_type", window.cups_media_type_value)
    window.ui_settings.setValue(
        "print/cups_print_quality", window.cups_print_quality_value
    )
    window.ui_settings.setValue("print/cups_media_key", window.cups_media_key)
    window.ui_settings.setValue("print/cups_media_type_key", window.cups_media_type_key)
    window.ui_settings.setValue(
        "print/cups_print_quality_key", window.cups_print_quality_key
    )
    window.ui_settings.setValue("print/paper", window.paper_value)
    window.ui_settings.setValue("print/borderless_mode", window.borderless_mode_value)
    window.ui_settings.setValue(
        "print/borderless", window.borderless_mode_value == "enabled"
    )
    window.ui_settings.setValue(
        "print/borderless_content_scale_percent",
        window.borderless_content_scale_percent,
    )
    window.ui_settings.setValue("print/orientation", window.print_orientation_value)
    window.ui_settings.sync()


def borderless_enabled(window: Any) -> bool:
    return window.borderless_mode_value == "enabled"


def default_metadata(_window: Any) -> dict[str, object]:
    return {
        "version": 1,
        "image_settings": {},
        "photos": {},
        "print_events": [],
        "location_areas": [],
        "recent_pins": [],
    }


def selected_path(window: Any) -> Path | None:
    row = window.image_table.currentRow()
    if row < 0 or row >= len(window.image_paths):
        return None
    return window.image_paths[row]


__all__ = [
    "borderless_enabled",
    "current_project_settings_payload",
    "default_metadata",
    "load_app_print_settings",
    "load_app_project_settings",
    "persist_project_settings",
    "save_app_print_settings",
    "save_app_project_settings",
    "selected_path",
]
