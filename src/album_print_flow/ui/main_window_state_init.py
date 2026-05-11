from __future__ import annotations

from typing import Any

from PySide6.QtCore import QSettings, Qt, QThreadPool, QTimer
from PySide6.QtGui import QPixmap


def initialize_main_window_state(
    window: Any,
    startup_cache: dict[str, object] | None,
    *,
    ipp_capabilities_cls: type,
    source_registry_cls: type,
    folder_source_cls: type,
    google_photos_source_cls: type,
    google_photos_album_url_source_cls: type,
    supported_extensions: tuple[str, ...],
    load_source_state_fn: object,
    settings_org: str,
    settings_app: str,
    thumbnail_size: int,
    nominatim_default_reverse_url: str,
    nominatim_default_rate_limit_seconds: float,
    location_format_template_default: str,
    default_stamp_color: str,
    default_stamp_border_color: str,
    table_col_file: int,
    table_col_date_used: int,
    table_col_aspect: int,
) -> None:
    startup_cache = startup_cache or {}
    printers_cache = startup_cache.get("printers", [])
    if isinstance(printers_cache, list):
        window.printer_names_cache = [str(name) for name in printers_cache]
    else:
        window.printer_names_cache = []

    cups_cache = startup_cache.get("cups_capabilities", {})
    if isinstance(cups_cache, dict):
        window.cups_capabilities_cache = {
            str(key): value
            for key, value in cups_cache.items()
            if isinstance(value, tuple) and len(value) == 2
        }
    else:
        window.cups_capabilities_cache = {}

    ipp_cache = startup_cache.get("ipp_capabilities", {})
    if isinstance(ipp_cache, dict):
        window.ipp_capabilities_cache = {
            str(key): value
            for key, value in ipp_cache.items()
            if isinstance(value, ipp_capabilities_cls) or value is None
        }
    else:
        window.ipp_capabilities_cache = {}

    startup_debug_cache = startup_cache.get("startup_debug_lines", [])
    if isinstance(startup_debug_cache, list):
        window.startup_debug_lines = [str(line) for line in startup_debug_cache]
    else:
        window.startup_debug_lines = []

    window.image_paths = []
    window.current_index = -1
    window.current_folder = None
    window.current_source_id = "folder"
    window.current_source_context_id = None
    window.source_assets_by_path = {}
    window.source_registry = source_registry_cls(
        [
            folder_source_cls(supported_extensions),
            google_photos_source_cls(debug_logger=window.thread_safe_append_log),
            google_photos_album_url_source_cls(
                debug_logger=window.thread_safe_append_log
            ),
        ]
    )
    window.source_state = load_source_state_fn(settings_org)
    window._restoring_settings = False
    window._updating_table = False
    window.image_row_lookup = {}
    window.thumbnail_cache = {}
    window.thumbnail_pending_paths = []
    window.thumbnail_inflight_paths = set()
    window.thumbnail_generation = 0
    window.thumbnail_thread_pool = QThreadPool.globalInstance()
    window.source_worker_pool = QThreadPool(window)
    window.source_worker_pool.setMaxThreadCount(2)
    window.source_refresh_generation = 0
    window.source_refresh_in_progress = False
    window.source_load_generation = 0
    window.source_load_in_progress = False
    window.active_source_load_adapter = None
    window.startup_bookmark_scan_started = False
    window.startup_bookmark_scan_in_progress = False
    window.album_sync_status_last_update_at = 0.0
    window.album_sync_live_url = ""
    window.album_sync_live_last_asset_count = 0
    window.album_sync_bootstrap_active = False
    window.album_sync_live_timer = QTimer(window)
    window.album_sync_live_timer.setInterval(500)
    window.album_sync_live_timer.timeout.connect(
        window.process_album_sync_live_snapshot
    )
    window.thumbnail_placeholder = QPixmap(thumbnail_size, thumbnail_size)
    window.thumbnail_placeholder.fill(Qt.GlobalColor.darkGray)
    window.table_metadata_generation = 0
    window.table_metadata_pending_paths = []
    window.table_metadata_total_paths = 0
    window.table_metadata_paused = False
    window.table_metadata_last_scroll_at = 0.0
    window.table_metadata_cached_hits = 0
    window.table_metadata_computed_paths = 0
    window.table_metadata_skipped_paths = 0
    window.table_metadata_changed_paths = 0
    window.table_metadata_timer = QTimer(window)
    window.table_metadata_timer.setInterval(16)
    window.table_metadata_timer.timeout.connect(window.process_table_metadata_batch)
    window.orientation_cache = {}
    window.image_dimensions_cache = {}
    window.location_cache = {}
    window.file_hash_cache = {}
    window.preview_render_state_key = None
    window.log_entries = []
    window.log_level_filter_value = "INFO"
    window.log_text_filter_value = ""
    window.print_queue_items = []
    window.print_queue_next_id = 1
    window.print_queue_paused = False
    window.print_queue_processing = False
    window.cups_job_poll_timer = QTimer(window)
    window.cups_job_poll_timer.setInterval(3000)
    window.cups_job_poll_timer.timeout.connect(window.poll_cups_job_statuses)
    window.current_image_orientation = "Landscape"
    window.current_image_rotation_degrees = 0
    window.ui_settings = QSettings(settings_org, settings_app)

    window.nominatim_enabled_value = True
    window.nominatim_reverse_url_value = nominatim_default_reverse_url
    window.nominatim_auth_mode_value = "None"
    window.nominatim_auth_token_value = ""
    window.nominatim_auth_username_value = ""
    window.nominatim_auth_password_value = ""
    window.nominatim_accept_language_value = ""
    window.nominatim_email_value = ""
    window.nominatim_zoom_value = 18
    window.nominatim_rate_limit_seconds_value = nominatim_default_rate_limit_seconds
    window.nominatim_last_request_at = 0.0
    window.nominatim_cache = {}

    window.load_nominatim_settings()
    window.load_nominatim_cache()

    window.folder_metadata = window.default_metadata()

    window.crop_ratio_value = "2:3"
    window.stamp_mode_value = "None"
    window.clock_mode_value = "24h"
    window.corner_landscape_value = "Bottom Right"
    window.corner_portrait_value = "Bottom Right"
    window.paper_value = "10x15 cm"
    window.borderless_mode_value = "enabled"
    window.printer_value = ""
    window.sort_mode_value = "Filename (A-Z)"
    window.sort_column_value = table_col_file
    window.sort_descending_value = False
    window.sortable_columns = {
        table_col_file,
        table_col_date_used,
        table_col_aspect,
    }
    window.stamp_font_value = "Photo Stamp Mono"
    window.stamp_scale_percent = 100
    window.stamp_offset_x_px = 15
    window.stamp_offset_y_px = 15
    window.stamp_color_value = default_stamp_color
    window.stamp_border_color_value = default_stamp_border_color
    window.stamp_vertical_value = False
    window.stamp_adaptive_text_value = False
    window.adaptive_luminance_threshold_value = 128
    window.location_stamp_mode_value = "Off"
    window.location_format_value = "Address Label"
    window.location_format_template_value = location_format_template_default
    window.location_corner_landscape_value = "Top Left"
    window.location_corner_portrait_value = "Top Left"
    window.location_stamp_scale_percent = 90
    window.location_stamp_offset_x_px = 15
    window.location_stamp_offset_y_px = 15
    window.location_stamp_color_value = default_stamp_color
    window.location_stamp_border_color_value = default_stamp_border_color
    window.location_stamp_vertical_value = False
    window.location_stamp_adaptive_text_value = False
    window.location_custom_text_history = []
    window.print_backend_value = "Auto"
    window.ipp_uri_value = ""
    window.ipp_wait_for_completion_value = False
    window.export_root_value = ""
    window.cups_media_value = ""
    window.cups_media_type_value = ""
    window.cups_print_quality_value = ""
    window.borderless_content_scale_percent = 100
    window.cups_media_key = "media"
    window.cups_media_type_key = "media-type"
    window.cups_print_quality_key = "print-quality"
    window.print_orientation_value = "Portrait"

    window.load_app_print_settings()
    window.load_app_project_settings()
    window.load_custom_location_text_history()


__all__ = ["initialize_main_window_state"]
