from __future__ import annotations

from typing import Any

from PySide6.QtCore import QSettings
from PySide6.QtGui import QColor

VALID_CORNERS = {"Bottom Right", "Bottom Left", "Top Right", "Top Left"}
VALID_STAMP_MODES = {"None", "Date", "Date + Time"}
VALID_CLOCK_MODES = {"24h", "12h"}


PROJECT_SETTING_KEYS = [
    "crop_ratio",
    "stamp_mode",
    "clock_mode",
    "corner_landscape",
    "corner_portrait",
    "sort_mode",
    "sort_column",
    "sort_descending",
    "stamp_font",
    "stamp_scale_percent",
    "stamp_offset_x_px",
    "stamp_offset_y_px",
    "stamp_color",
    "stamp_border_color",
    "stamp_vertical",
]


def _as_bool(value: object, default: bool) -> bool:
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


def _as_int(value: object, default: int) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            return default
    return default


def load_app_project_settings(
    settings: QSettings,
    defaults: dict[str, Any],
    *,
    crop_ratios: set[str],
    sort_modes: set[str],
    sortable_columns: set[int],
    stamp_fonts: set[str],
    stamp_scale_min: int,
    stamp_scale_max: int,
    stamp_offset_min: int,
    stamp_offset_max: int,
) -> dict[str, Any]:
    values = dict(defaults)

    crop_ratio = str(settings.value("settings/crop_ratio", values["crop_ratio"]))
    if crop_ratio in crop_ratios:
        values["crop_ratio"] = crop_ratio

    stamp_mode = str(settings.value("settings/stamp_mode", values["stamp_mode"]))
    if stamp_mode in VALID_STAMP_MODES:
        values["stamp_mode"] = stamp_mode

    clock_mode = str(settings.value("settings/clock_mode", values["clock_mode"]))
    if clock_mode in VALID_CLOCK_MODES:
        values["clock_mode"] = clock_mode

    corner_landscape = str(
        settings.value("settings/corner_landscape", values["corner_landscape"])
    )
    if corner_landscape in VALID_CORNERS:
        values["corner_landscape"] = corner_landscape

    corner_portrait = str(
        settings.value("settings/corner_portrait", values["corner_portrait"])
    )
    if corner_portrait in VALID_CORNERS:
        values["corner_portrait"] = corner_portrait

    sort_mode = str(settings.value("settings/sort_mode", values["sort_mode"]))
    if sort_mode in sort_modes:
        values["sort_mode"] = sort_mode

    sort_column = settings.value("settings/sort_column", values["sort_column"])
    sort_descending = settings.value(
        "settings/sort_descending", values["sort_descending"]
    )
    parsed_sort_column = _as_int(sort_column, int(values["sort_column"]))
    if parsed_sort_column in sortable_columns:
        values["sort_column"] = parsed_sort_column
        values["sort_descending"] = _as_bool(
            sort_descending,
            bool(values["sort_descending"]),
        )

    stamp_font = str(settings.value("settings/stamp_font", values["stamp_font"]))
    if stamp_font in stamp_fonts:
        values["stamp_font"] = stamp_font

    stamp_scale = _as_int(
        settings.value("settings/stamp_scale_percent", values["stamp_scale_percent"]),
        int(values["stamp_scale_percent"]),
    )
    values["stamp_scale_percent"] = max(
        stamp_scale_min,
        min(stamp_scale_max, stamp_scale),
    )

    stamp_offset_x = _as_int(
        settings.value("settings/stamp_offset_x_px", values["stamp_offset_x_px"]),
        int(values["stamp_offset_x_px"]),
    )
    values["stamp_offset_x_px"] = max(
        stamp_offset_min,
        min(stamp_offset_max, stamp_offset_x),
    )

    stamp_offset_y = _as_int(
        settings.value("settings/stamp_offset_y_px", values["stamp_offset_y_px"]),
        int(values["stamp_offset_y_px"]),
    )
    values["stamp_offset_y_px"] = max(
        stamp_offset_min,
        min(stamp_offset_max, stamp_offset_y),
    )

    stamp_color = str(settings.value("settings/stamp_color", values["stamp_color"]))
    color = QColor(stamp_color)
    if color.isValid():
        values["stamp_color"] = color.name().upper()

    stamp_border_color = str(
        settings.value("settings/stamp_border_color", values["stamp_border_color"])
    )
    border_color = QColor(stamp_border_color)
    if border_color.isValid():
        values["stamp_border_color"] = border_color.name().upper()

    values["stamp_vertical"] = _as_bool(
        settings.value("settings/stamp_vertical", values["stamp_vertical"]),
        bool(values["stamp_vertical"]),
    )

    return values


def save_app_project_settings(settings: QSettings, values: dict[str, Any]) -> None:
    for key in PROJECT_SETTING_KEYS:
        if key in values:
            settings.setValue(f"settings/{key}", values[key])
    settings.sync()
