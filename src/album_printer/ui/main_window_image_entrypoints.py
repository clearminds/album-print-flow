from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from album_printer.app_constants import (
    PER_IMAGE_LOCATION_STAMP_OVERRIDES,
    REFRAME_HANDLE_SIZE,
    TABLE_COL_FILE,
    TABLE_COL_THUMB,
    THUMBNAIL_MAX_INFLIGHT,
    THUMBNAIL_SIZE,
    THUMBNAIL_UI_CACHE_WARMUP_MAX,
)
from album_printer.app_image_entrypoints import datetime_for_image, load_image_as_rgb
from album_printer.app_primitives import (
    apply_manual_rotation,
    crop_geometry_for_ratio,
    normalize_rotation_degrees,
    parse_datetime_override,
)
from album_printer.app_rendering_entrypoints import render_preview_image
from album_printer.processing_settings import ProcessingSettings
from album_printer.ui.control_visibility_flow import (
    update_aspect_navigation_buttons as update_aspect_navigation_buttons_flow,
    update_date_check_navigation_buttons as update_date_check_navigation_buttons_flow,
    update_fix_navigation_buttons as update_fix_navigation_buttons_flow,
    update_fix_needed_message as update_fix_needed_message_flow,
)
from album_printer.ui.crop_reframe_flow import (
    compute_overlay_rect_for_current_crop as compute_overlay_rect_for_current_crop_flow,
)
from album_printer.ui.crop_reframe_flow import (
    on_crop_reframe_toggled as on_crop_reframe_toggled_flow,
)
from album_printer.ui.crop_reframe_flow import (
    on_preview_drag_released as on_preview_drag_released_flow,
)
from album_printer.ui.crop_reframe_flow import (
    on_preview_drag_started as on_preview_drag_started_flow,
)
from album_printer.ui.crop_reframe_flow import (
    on_preview_dragged as on_preview_dragged_flow,
)
from album_printer.ui.crop_reframe_flow import (
    reset_crop_for_selected as reset_crop_for_selected_flow,
)
from album_printer.ui.crop_reframe_flow import resize_corner_at as resize_corner_at_flow
from album_printer.ui.crop_reframe_flow import (
    update_preview_overlay_rect as update_preview_overlay_rect_flow,
)
from album_printer.ui.datetime_override_flow import (
    clear_datetime_override_for_selected as clear_datetime_override_for_selected_flow,
)
from album_printer.ui.datetime_override_flow import (
    pick_datetime_override as pick_datetime_override_flow,
)
from album_printer.ui.datetime_override_flow import (
    set_datetime_override_for_path as set_datetime_override_for_path_flow,
)
from album_printer.ui.datetime_override_flow import (
    set_datetime_override_for_selected as set_datetime_override_for_selected_flow,
)
from album_printer.ui.image_navigation_flow import (
    select_aspect_mismatch as select_aspect_mismatch_flow,
)
from album_printer.ui.image_navigation_flow import select_next as select_next_flow
from album_printer.ui.image_navigation_flow import (
    select_next_aspect_mismatch as select_next_aspect_mismatch_flow,
)
from album_printer.ui.image_navigation_flow import (
    select_previous as select_previous_flow,
)
from album_printer.ui.image_navigation_flow import (
    select_next_date_check as select_next_date_check_flow,
)
from album_printer.ui.image_navigation_flow import (
    select_previous_aspect_mismatch as select_previous_aspect_mismatch_flow,
)
from album_printer.ui.image_navigation_flow import (
    select_previous_date_check as select_previous_date_check_flow,
)
from album_printer.ui.image_navigation_flow import (
    select_previous_fix as select_previous_fix_flow,
)
from album_printer.ui.image_navigation_flow import (
    select_next_fix as select_next_fix_flow,
)
from album_printer.ui.image_navigation_flow import (
    select_date_check_mismatch as select_date_check_mismatch_flow,
)
from album_printer.ui.image_settings_flow import (
    aspect_ratio_cell_text_for_path as aspect_ratio_cell_text_for_path_flow,
)
from album_printer.ui.image_settings_flow import (
    compute_file_hash as compute_file_hash_flow,
)
from album_printer.ui.image_settings_flow import (
    date_used_for_path as date_used_for_path_flow,
)
from album_printer.ui.image_settings_flow import (
    detect_orientation_for_path as detect_orientation_for_path_flow,
)
from album_printer.ui.image_settings_flow import (
    image_list_label as image_list_label_flow,
)
from album_printer.ui.image_settings_flow import (
    is_crop_settings_modified as is_crop_settings_modified_flow,
)
from album_printer.ui.image_settings_flow import (
    restore_image_settings_for_selected as restore_image_settings_for_selected_flow,
)
from album_printer.ui.image_settings_flow import (
    set_image_entry_file_hash as set_image_entry_file_hash_flow,
)
from album_printer.ui.image_settings_flow import (
    path_needs_date_check as path_needs_date_check_flow,
)
from album_printer.ui.image_settings_flow import (
    path_needs_fix as path_needs_fix_flow,
)
from album_printer.ui.image_settings_flow import (
    fix_needed_message_for_path as fix_needed_message_for_path_flow,
)
from album_printer.ui.image_settings_flow import (
    source_aspect_ratio_label_for_path as source_aspect_ratio_label_for_path_flow,
)
from album_printer.ui.image_settings_flow import (
    sync_image_settings_with_files as sync_image_settings_with_files_flow,
)
from album_printer.ui.image_transform_flow import (
    reset_selected_image_rotation as reset_selected_image_rotation_flow,
)
from album_printer.ui.image_transform_flow import (
    rotate_selected_image_clockwise as rotate_selected_image_clockwise_flow,
)
from album_printer.ui.image_transform_flow import (
    toggle_crop_orientation as toggle_crop_orientation_flow,
)
from album_printer.ui.image_transform_flow import (
    update_crop_orientation_button_text as update_crop_orientation_button_text_flow,
)
from album_printer.ui.image_transform_flow import (
    update_rotate_image_button_text as update_rotate_image_button_text_flow,
)
from album_printer.ui.preview_flow import on_image_changed as on_image_changed_flow
from album_printer.ui.preview_flow import (
    on_image_settings_changed as on_image_settings_changed_flow,
)
from album_printer.ui.preview_flow import (
    on_image_table_selection_changed as on_image_table_selection_changed_flow,
)
from album_printer.ui.preview_flow import (
    processing_settings_for_path as processing_settings_for_path_flow,
)
from album_printer.ui.preview_flow import refresh_preview as refresh_preview_flow
from album_printer.ui.thumbnail_cache_flow import (
    start_thumbnail_generation as start_thumbnail_generation_flow,
)
from album_printer.ui.thumbnail_worker import ThumbnailWorker
from album_printer.ui.thumbnail_worker_flow import (
    fill_thumbnail_workers as fill_thumbnail_workers_flow,
)
from album_printer.ui.thumbnail_worker_flow import (
    on_thumbnail_ready as on_thumbnail_ready_flow,
)
from album_printer.ui.window_event_flow import (
    on_image_table_cell_changed as on_image_table_cell_changed_flow,
)
from album_printer.ui.window_event_flow import (
    on_image_table_cell_double_clicked as on_image_table_cell_double_clicked_flow,
)


def compute_file_hash(window: Any, path: Path) -> str:
    return compute_file_hash_flow(window, path)


def set_image_entry_file_hash(
    window: Any, path: Path, entry: dict[str, object]
) -> None:
    set_image_entry_file_hash_flow(window, path, entry)


def sync_image_settings_with_files(window: Any) -> int:
    return sync_image_settings_with_files_flow(window)


def detect_orientation_for_path(window: Any, path: Path) -> str:
    return detect_orientation_for_path_flow(window, path)


def source_aspect_ratio_label_for_path(window: Any, path: Path) -> str:
    return source_aspect_ratio_label_for_path_flow(window, path)


def aspect_ratio_cell_text_for_path(window: Any, path: Path) -> str:
    return aspect_ratio_cell_text_for_path_flow(window, path)


def update_aspect_navigation_buttons(window: Any) -> None:
    update_aspect_navigation_buttons_flow(window)


def update_date_check_navigation_buttons(window: Any) -> None:
    update_date_check_navigation_buttons_flow(window)


def update_fix_navigation_buttons(window: Any) -> None:
    update_fix_navigation_buttons_flow(window)


def update_fix_needed_message(window: Any) -> None:
    update_fix_needed_message_flow(window)


def path_needs_fix(window: Any, path: Path) -> bool:
    return path_needs_fix_flow(window, path)


def fix_needed_message_for_path(window: Any, path: Path) -> str:
    return fix_needed_message_for_path_flow(window, path)


def path_needs_date_check(window: Any, path: Path) -> bool:
    return path_needs_date_check_flow(window, path)


def image_list_label(window: Any, path: Path) -> str:
    return image_list_label_flow(window, path)


def is_crop_settings_modified(window: Any, path: Path) -> bool:
    return is_crop_settings_modified_flow(
        window,
        path,
        normalize_rotation_degrees_fn=normalize_rotation_degrees,
    )


def date_used_for_path(window: Any, path: Path) -> datetime:
    return date_used_for_path_flow(window, path)


def restore_image_settings_for_selected(window: Any) -> None:
    restore_image_settings_for_selected_flow(
        window,
        per_image_location_stamp_overrides=PER_IMAGE_LOCATION_STAMP_OVERRIDES,
    )


def set_datetime_override_for_selected(window: Any) -> None:
    set_datetime_override_for_selected_flow(window)


def pick_datetime_override(window: Any, path: Path) -> datetime | None:
    return pick_datetime_override_flow(
        window,
        path,
        parse_datetime_override_fn=parse_datetime_override,
        datetime_for_image_fn=datetime_for_image,
    )


def set_datetime_override_for_path(window: Any, path: Path, value: datetime) -> None:
    set_datetime_override_for_path_flow(window, path, value)


def clear_datetime_override_for_selected(window: Any) -> None:
    clear_datetime_override_for_selected_flow(window)


def update_crop_orientation_button_text(window: Any) -> None:
    update_crop_orientation_button_text_flow(window)


def update_rotate_image_button_text(window: Any) -> None:
    update_rotate_image_button_text_flow(window)


def toggle_crop_orientation(window: Any) -> None:
    toggle_crop_orientation_flow(window)


def rotate_selected_image_clockwise(window: Any) -> None:
    rotate_selected_image_clockwise_flow(window)


def reset_selected_image_rotation(window: Any) -> None:
    reset_selected_image_rotation_flow(window)


def on_crop_reframe_toggled(window: Any, enabled: bool) -> None:
    on_crop_reframe_toggled_flow(window, enabled)


def reset_crop_for_selected(window: Any) -> None:
    reset_crop_for_selected_flow(window)


def resize_corner_at(window: Any, x: int, y: int) -> str | None:
    return resize_corner_at_flow(window, x, y, reframe_handle_size=REFRAME_HANDLE_SIZE)


def on_preview_drag_started(window: Any, x: int, y: int) -> None:
    on_preview_drag_started_flow(
        window,
        x,
        y,
        reframe_handle_size=REFRAME_HANDLE_SIZE,
    )


def on_preview_dragged(
    window: Any,
    delta_x: int,
    delta_y: int,
    x: int,
    y: int,
) -> None:
    on_preview_dragged_flow(window, delta_x, delta_y, x, y)


def on_preview_drag_released(window: Any, x: int, y: int) -> None:
    on_preview_drag_released_flow(window, x, y)


def compute_overlay_rect_for_current_crop(
    window: Any,
) -> tuple[int, int, int, int] | None:
    return compute_overlay_rect_for_current_crop_flow(
        window,
        crop_geometry_for_ratio_fn=crop_geometry_for_ratio,
    )


def update_preview_overlay_rect(window: Any) -> None:
    update_preview_overlay_rect_flow(window)


def on_image_settings_changed(window: Any, *args: object) -> None:
    on_image_settings_changed_flow(window)


def processing_settings_for_path(window: Any, path: Path) -> ProcessingSettings:
    return processing_settings_for_path_flow(
        window,
        path,
        normalize_rotation_degrees_fn=normalize_rotation_degrees,
        processing_settings_cls=ProcessingSettings,
    )


def refresh_preview(window: Any) -> None:
    refresh_preview_flow(
        window,
        load_image_as_rgb_fn=load_image_as_rgb,
        apply_manual_rotation_fn=apply_manual_rotation,
        render_preview_image_fn=render_preview_image,
    )


def on_image_changed(window: Any, row: int) -> None:
    on_image_changed_flow(window, row)


def on_image_table_selection_changed(
    window: Any,
    current_row: int,
    *args: object,
) -> None:
    on_image_table_selection_changed_flow(window, current_row)


def on_image_table_cell_double_clicked(window: Any, row: int, column: int) -> None:
    on_image_table_cell_double_clicked_flow(window, row, column)


def on_image_table_cell_changed(window: Any, row: int, column: int) -> None:
    on_image_table_cell_changed_flow(window, row, column)


def select_previous(window: Any) -> None:
    select_previous_flow(window, table_col_file=TABLE_COL_FILE)


def select_next(window: Any) -> None:
    select_next_flow(window, table_col_file=TABLE_COL_FILE)


def select_aspect_mismatch(window: Any, step: int) -> None:
    select_aspect_mismatch_flow(window, step, table_col_file=TABLE_COL_FILE)


def select_previous_aspect_mismatch(window: Any) -> None:
    select_previous_aspect_mismatch_flow(window, table_col_file=TABLE_COL_FILE)


def select_next_aspect_mismatch(window: Any) -> None:
    select_next_aspect_mismatch_flow(window, table_col_file=TABLE_COL_FILE)


def select_previous_fix(window: Any) -> None:
    select_previous_fix_flow(window, table_col_file=TABLE_COL_FILE)


def select_next_fix(window: Any) -> None:
    select_next_fix_flow(window, table_col_file=TABLE_COL_FILE)


def select_date_check_mismatch(window: Any, step: int) -> None:
    select_date_check_mismatch_flow(window, step, table_col_file=TABLE_COL_FILE)


def select_previous_date_check(window: Any) -> None:
    select_previous_date_check_flow(window, table_col_file=TABLE_COL_FILE)


def select_next_date_check(window: Any) -> None:
    select_next_date_check_flow(window, table_col_file=TABLE_COL_FILE)


def start_thumbnail_generation(window: Any) -> None:
    start_thumbnail_generation_flow(
        window,
        thumbnail_ui_cache_warmup_max=THUMBNAIL_UI_CACHE_WARMUP_MAX,
    )


def fill_thumbnail_workers(window: Any) -> None:
    fill_thumbnail_workers_flow(
        window,
        thumbnail_max_inflight=THUMBNAIL_MAX_INFLIGHT,
        thumbnail_worker_cls=ThumbnailWorker,
        load_image_as_rgb_fn=load_image_as_rgb,
        thumbnail_size=THUMBNAIL_SIZE,
    )


def on_thumbnail_ready(
    window: Any, path: object, generation: int, image: object
) -> None:
    on_thumbnail_ready_flow(
        window,
        path,
        generation,
        image,
        table_col_thumb=TABLE_COL_THUMB,
    )


__all__ = [
    "aspect_ratio_cell_text_for_path",
    "clear_datetime_override_for_selected",
    "compute_file_hash",
    "compute_overlay_rect_for_current_crop",
    "date_used_for_path",
    "detect_orientation_for_path",
    "fill_thumbnail_workers",
    "image_list_label",
    "is_crop_settings_modified",
    "on_crop_reframe_toggled",
    "on_image_changed",
    "on_image_settings_changed",
    "on_image_table_cell_changed",
    "on_image_table_cell_double_clicked",
    "on_image_table_selection_changed",
    "on_preview_drag_released",
    "on_preview_drag_started",
    "on_preview_dragged",
    "on_thumbnail_ready",
    "path_needs_date_check",
    "path_needs_fix",
    "fix_needed_message_for_path",
    "pick_datetime_override",
    "processing_settings_for_path",
    "refresh_preview",
    "reset_crop_for_selected",
    "reset_selected_image_rotation",
    "resize_corner_at",
    "restore_image_settings_for_selected",
    "rotate_selected_image_clockwise",
    "select_aspect_mismatch",
    "select_next",
    "select_next_aspect_mismatch",
    "select_next_date_check",
    "select_previous",
    "select_previous_aspect_mismatch",
    "select_previous_date_check",
    "select_previous_fix",
    "select_next_fix",
    "select_date_check_mismatch",
    "set_datetime_override_for_path",
    "set_datetime_override_for_selected",
    "set_image_entry_file_hash",
    "source_aspect_ratio_label_for_path",
    "start_thumbnail_generation",
    "sync_image_settings_with_files",
    "toggle_crop_orientation",
    "update_aspect_navigation_buttons",
    "update_crop_orientation_button_text",
    "update_date_check_navigation_buttons",
    "update_fix_navigation_buttons",
    "update_fix_needed_message",
    "update_preview_overlay_rect",
    "update_rotate_image_button_text",
]
