from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from album_printer.app_constants import (
    LOCATION_FORMAT_OPTIONS,
    PER_IMAGE_LOCATION_STAMP_OVERRIDES,
    TABLE_COL_ASPECT,
    TABLE_COL_DATE_USED,
    TABLE_COL_LOCATION,
    TABLE_METADATA_BATCH_SIZE_IDLE,
    TABLE_METADATA_BATCH_SIZE_SCROLLING,
    TABLE_METADATA_SCROLL_WINDOW_SECONDS,
)
from album_printer.app_image_entrypoints import (
    exif_datetime_for_image,
    exif_location_for_image,
    load_image_as_rgb,
    original_metadata_path_for_image,
)
from album_printer.app_primitives import (
    decimal_to_dms,
    location_format_needs_reverse_lookup,
    normalize_rotation_degrees,
    parse_datetime_from_filename,
    parse_datetime_override,
    parse_ratio_pair,
    ratios_match_either_orientation,
)
from album_printer.ui.footer_progress import (
    gps_resolution_progress_counts as gps_resolution_progress_counts_flow,
)
from album_printer.ui.footer_progress import (
    refresh_gps_resolution_progress as refresh_gps_resolution_progress_flow,
)
from album_printer.ui.image_settings_flow import (
    date_used_and_source_for_path as date_used_and_source_for_path_flow,
)
from album_printer.ui.image_settings_flow import (
    image_dimensions_for_path as image_dimensions_for_path_flow,
)
from album_printer.ui.image_settings_flow import (
    image_settings_for_path as image_settings_for_path_flow,
)
from album_printer.ui.image_settings_flow import (
    path_needs_crop_for_aspect as path_needs_crop_for_aspect_flow,
)
from album_printer.ui.location_lookup_flow import (
    effective_location_format_for_path as effective_location_format_for_path_flow,
)
from album_printer.ui.location_lookup_flow import (
    format_location as format_location_flow,
)
from album_printer.ui.location_lookup_flow import (
    location_for_path as location_for_path_flow,
)
from album_printer.ui.location_lookup_flow import (
    location_lookup_status_for_path as location_lookup_status_for_path_flow,
)
from album_printer.ui.location_lookup_flow import (
    update_location_status_for_path as update_location_status_for_path_flow,
)
from album_printer.ui.table_metadata_flow import (
    current_table_metadata_batch_size as current_table_metadata_batch_size_flow,
)
from album_printer.ui.table_metadata_flow import (
    process_table_metadata_batch as process_table_metadata_batch_flow,
)


def location_for_path(window: Any, path: Path) -> tuple[float, float] | None:
    return location_for_path_flow(
        window,
        path,
        exif_location_for_image_fn=exif_location_for_image,
    )


def format_location(
    window: Any,
    location: tuple[float, float] | None,
    path: Path | None = None,
    format_value: str | None = None,
) -> str:
    return format_location_flow(
        window,
        location,
        path,
        format_value,
        decimal_to_dms_fn=decimal_to_dms,
        location_format_needs_reverse_lookup_fn=location_format_needs_reverse_lookup,
    )


def effective_location_format_for_path(
    window: Any,
    path: Path,
    values: dict[str, object] | None = None,
) -> str | None:
    return effective_location_format_for_path_flow(
        window,
        path,
        values,
        location_format_options=LOCATION_FORMAT_OPTIONS,
    )


def location_lookup_status_for_path(window: Any, path: Path) -> str:
    return location_lookup_status_for_path_flow(
        window,
        path,
        location_format_needs_reverse_lookup_fn=location_format_needs_reverse_lookup,
    )


def update_location_status_for_path(window: Any, path: Path) -> None:
    update_location_status_for_path_flow(
        window,
        path,
        table_col_location=TABLE_COL_LOCATION,
    )


def gps_resolution_progress_counts(window: Any) -> tuple[int, int]:
    return gps_resolution_progress_counts_flow(
        window,
        location_format_needs_reverse_lookup_fn=location_format_needs_reverse_lookup,
    )


def refresh_gps_resolution_progress(window: Any) -> None:
    refresh_gps_resolution_progress_flow(
        window,
        location_format_needs_reverse_lookup_fn=location_format_needs_reverse_lookup,
    )


def image_settings_for_path(window: Any, path: Path) -> dict[str, object]:
    return image_settings_for_path_flow(
        window,
        path,
        normalize_rotation_degrees_fn=normalize_rotation_degrees,
        per_image_location_stamp_overrides=PER_IMAGE_LOCATION_STAMP_OVERRIDES,
    )


def image_dimensions_for_path(window: Any, path: Path) -> tuple[int, int]:
    return image_dimensions_for_path_flow(
        window,
        path,
        original_metadata_path_for_image_fn=original_metadata_path_for_image,
        load_image_as_rgb_fn=load_image_as_rgb,
    )


def path_needs_crop_for_aspect(window: Any, path: Path) -> bool:
    return path_needs_crop_for_aspect_flow(
        window,
        path,
        normalize_rotation_degrees_fn=normalize_rotation_degrees,
        parse_ratio_pair_fn=parse_ratio_pair,
        ratios_match_either_orientation_fn=ratios_match_either_orientation,
    )


def date_used_and_source_for_path(window: Any, path: Path) -> tuple[datetime, str]:
    return date_used_and_source_for_path_flow(
        window,
        path,
        parse_datetime_override_fn=parse_datetime_override,
        exif_datetime_for_image_fn=exif_datetime_for_image,
        parse_datetime_from_filename_fn=parse_datetime_from_filename,
    )


def current_table_metadata_batch_size(window: Any) -> int:
    return current_table_metadata_batch_size_flow(
        window,
        scroll_window_seconds=TABLE_METADATA_SCROLL_WINDOW_SECONDS,
        batch_size_scrolling=TABLE_METADATA_BATCH_SIZE_SCROLLING,
        batch_size_idle=TABLE_METADATA_BATCH_SIZE_IDLE,
    )


def process_table_metadata_batch(window: Any) -> None:
    process_table_metadata_batch_flow(
        window,
        table_col_date_used=TABLE_COL_DATE_USED,
        table_col_location=TABLE_COL_LOCATION,
        table_col_aspect=TABLE_COL_ASPECT,
        scroll_window_seconds=TABLE_METADATA_SCROLL_WINDOW_SECONDS,
        batch_size_scrolling=TABLE_METADATA_BATCH_SIZE_SCROLLING,
        batch_size_idle=TABLE_METADATA_BATCH_SIZE_IDLE,
    )


__all__ = [
    "current_table_metadata_batch_size",
    "date_used_and_source_for_path",
    "effective_location_format_for_path",
    "format_location",
    "gps_resolution_progress_counts",
    "image_dimensions_for_path",
    "image_settings_for_path",
    "location_for_path",
    "location_lookup_status_for_path",
    "path_needs_crop_for_aspect",
    "process_table_metadata_batch",
    "refresh_gps_resolution_progress",
    "update_location_status_for_path",
]
