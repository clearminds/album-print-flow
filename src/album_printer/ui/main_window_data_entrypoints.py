from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from album_printer.app_constants import (
    LOCATION_FORMAT_OPTIONS,
    PER_IMAGE_LOCATION_STAMP_OVERRIDES,
    TABLE_COL_ASPECT,
    TABLE_COL_DATE_USED,
    TABLE_COL_FILE,
    TABLE_COL_LOCATION,
    TABLE_COL_PRINT,
    TABLE_COL_STATE,
    TABLE_COL_THUMB,
    TABLE_METADATA_BATCH_SIZE_IDLE,
    TABLE_METADATA_BATCH_SIZE_SCROLLING,
    TABLE_METADATA_SCROLL_WINDOW_SECONDS,
    THUMBNAIL_UI_CACHE_WARMUP_MAX,
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
from album_printer.sources.flows.folder_metadata import (
    load_folder_metadata as load_folder_metadata_flow,
)
from album_printer.sources.flows.folder_metadata import (
    save_folder_metadata as save_folder_metadata_flow,
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
from album_printer.ui.image_table_flow import (
    append_image_rows as append_image_rows_flow,
)
from album_printer.ui.image_table_flow import (
    populate_image_table_row as populate_image_table_row_flow,
)
from album_printer.ui.image_table_flow import (
    rebuild_image_row_lookup as rebuild_image_row_lookup_flow,
)
from album_printer.ui.image_table_flow import (
    refresh_image_list_labels as refresh_image_list_labels_flow,
)
from album_printer.ui.image_table_flow import row_for_path as row_for_path_flow
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
    enqueue_table_metadata_for_paths as enqueue_table_metadata_for_paths_flow,
)
from album_printer.ui.table_metadata_flow import (
    note_table_scrolled as note_table_scrolled_flow,
)
from album_printer.ui.table_metadata_flow import (
    process_table_metadata_batch as process_table_metadata_batch_flow,
)
from album_printer.ui.table_metadata_flow import (
    start_table_metadata_resolution as start_table_metadata_resolution_flow,
)
from album_printer.ui.table_sort_flow import apply_table_sort as apply_table_sort_flow
from album_printer.ui.table_sort_flow import (
    on_image_table_header_clicked as on_image_table_header_clicked_flow,
)
from album_printer.ui.table_sort_flow import sort_key_for_path as sort_key_for_path_flow
from album_printer.ui.table_sort_flow import (
    update_table_sort_indicator as update_table_sort_indicator_flow,
)
from album_printer.ui.window_event_flow import apply_sort_order as apply_sort_order_flow


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
    window.update_fix_navigation_buttons()
    window.update_fix_needed_message()


def rebuild_image_row_lookup(window: Any) -> None:
    rebuild_image_row_lookup_flow(window)


def row_for_path(window: Any, path: Path) -> int | None:
    return row_for_path_flow(window, path)


def start_table_metadata_resolution(window: Any) -> None:
    start_table_metadata_resolution_flow(window)


def note_table_scrolled(window: Any) -> None:
    note_table_scrolled_flow(window)


def refresh_image_list_labels(
    window: Any,
    preferred_path: Path | None = None,
) -> None:
    refresh_image_list_labels_flow(
        window,
        preferred_path,
        table_col_file=TABLE_COL_FILE,
        reset_paused=False,
    )


def populate_image_table_row(window: Any, row: int, path: Path) -> None:
    populate_image_table_row_flow(
        window,
        row,
        path,
        table_col_thumb=TABLE_COL_THUMB,
        table_col_state=TABLE_COL_STATE,
        table_col_print=TABLE_COL_PRINT,
        table_col_file=TABLE_COL_FILE,
        table_col_date_used=TABLE_COL_DATE_USED,
        table_col_location=TABLE_COL_LOCATION,
        table_col_aspect=TABLE_COL_ASPECT,
    )


def enqueue_table_metadata_for_paths(window: Any, paths: list[Path]) -> None:
    enqueue_table_metadata_for_paths_flow(window, paths)


def append_image_rows(window: Any, paths: list[Path]) -> None:
    append_image_rows_flow(
        window,
        paths,
        thumbnail_ui_cache_warmup_max=THUMBNAIL_UI_CACHE_WARMUP_MAX,
        table_col_thumb=TABLE_COL_THUMB,
    )


def update_table_sort_indicator(window: Any) -> None:
    update_table_sort_indicator_flow(window)


def sort_key_for_path(window: Any, path: Path, column: int) -> object:
    return sort_key_for_path_flow(
        window,
        path,
        column,
        table_col_file=TABLE_COL_FILE,
        table_col_date_used=TABLE_COL_DATE_USED,
        table_col_aspect=TABLE_COL_ASPECT,
    )


def apply_table_sort(window: Any, preferred_path: Path | None = None) -> None:
    apply_table_sort_flow(
        window,
        preferred_path,
        table_col_file=TABLE_COL_FILE,
        table_col_date_used=TABLE_COL_DATE_USED,
        table_col_aspect=TABLE_COL_ASPECT,
    )


def on_image_table_header_clicked(window: Any, column: int) -> None:
    on_image_table_header_clicked_flow(window, column)


def apply_sort_order(window: Any, preferred_path: Path | None = None) -> None:
    apply_sort_order_flow(window, preferred_path)


def load_folder_metadata(window: Any) -> None:
    load_folder_metadata_flow(window)


def save_folder_metadata(window: Any) -> None:
    save_folder_metadata_flow(window)


__all__ = [
    "append_image_rows",
    "apply_sort_order",
    "apply_table_sort",
    "current_table_metadata_batch_size",
    "date_used_and_source_for_path",
    "enqueue_table_metadata_for_paths",
    "effective_location_format_for_path",
    "format_location",
    "gps_resolution_progress_counts",
    "image_dimensions_for_path",
    "image_settings_for_path",
    "load_folder_metadata",
    "location_for_path",
    "location_lookup_status_for_path",
    "note_table_scrolled",
    "on_image_table_header_clicked",
    "path_needs_crop_for_aspect",
    "populate_image_table_row",
    "process_table_metadata_batch",
    "refresh_gps_resolution_progress",
    "refresh_image_list_labels",
    "rebuild_image_row_lookup",
    "row_for_path",
    "save_folder_metadata",
    "sort_key_for_path",
    "start_table_metadata_resolution",
    "update_table_sort_indicator",
    "update_location_status_for_path",
]
