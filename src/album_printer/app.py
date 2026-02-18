from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import datetime
from pathlib import Path

try:
    import pillow_heif

    pillow_heif.register_heif_opener()
except Exception:
    pillow_heif = None

from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QAction, QPixmap
from PySide6.QtWidgets import QComboBox, QMainWindow, QMessageBox

from album_printer.app_branding import (
    app_window_icon,
    load_clearminds_head_pixmap,
    load_logo_pixmap,
)
from album_printer.app_constants import (
    APP_DESKTOP_ID,
    APP_ORGANIZATION_DOMAIN,
    APP_ORGANIZATION_NAME,
    CROP_RATIO_LABELS,
    CROP_RATIOS,
    LOCATION_FORMAT_OPTIONS,
    LOCATION_FORMAT_TEMPLATE_DEFAULT,
    LOCATION_TEMPLATE_TOKENS,
    LOG_FILENAME,
    LOG_LEVEL_RANK,
    LOG_LEVELS,
    METADATA_FILENAME,
    NOMINATIM_AUTH_MODES,
    NOMINATIM_CACHE_FILENAME,
    NOMINATIM_CACHE_MAX_ENTRIES,
    NOMINATIM_DEFAULT_RATE_LIMIT_SECONDS,
    NOMINATIM_DEFAULT_REVERSE_URL,
    NOMINATIM_ZOOM_LEVEL_OPTIONS,
    PAPER_LABELS,
    PER_IMAGE_LOCATION_STAMP_OVERRIDES,
    PRINT_BACKENDS,
    REFRAME_HANDLE_SIZE,
    SETTINGS_APP,
    SETTINGS_ORG,
    SORT_MODES,
    STAMP_OFFSET_MAX_PX,
    STAMP_OFFSET_MIN_PX,
    STAMP_SCALE_MAX_PERCENT,
    STAMP_SCALE_MIN_PERCENT,
    SUPPORTED_EXTENSIONS,
    TABLE_COL_ASPECT,
    TABLE_COL_DATE_USED,
    TABLE_COL_FILE,
    TABLE_COL_LOCATION,
    TABLE_COL_PRINT,
    TABLE_COL_STATE,
    TABLE_COL_THUMB,
    THUMBNAIL_MAX_INFLIGHT,
    THUMBNAIL_SIZE,
    THUMBNAIL_UI_CACHE_WARMUP_MAX,
)
from album_printer.app_flow_kwargs import (
    load_google_photos_album_url_flow_kwargs,
    main_window_startup_kwargs,
    open_print_settings_dialog_flow_kwargs,
    open_project_settings_dialog_flow_kwargs,
    open_settings_dialog_flow_kwargs,
    print_all_via_cups_flow_kwargs,
    print_all_via_ipp_flow_kwargs,
    print_all_via_qt_flow_kwargs,
    print_borderless_calibration_flow_kwargs,
    refresh_folder_flow_kwargs,
)
from album_printer.app_image_entrypoints import datetime_for_image, load_image_as_rgb
from album_printer.app_primitives import (
    _normalized_geocodejson_feature,
    _normalized_geocodejson_geocoding,
    apply_manual_rotation,
    center_crop_to_ratio,
    crop_geometry_for_ratio,
    location_format_needs_reverse_lookup,
    normalize_rotation_degrees,
    parse_datetime_override,
    ratios_match_either_orientation,
    render_location_template,
)
from album_printer.app_printing_entrypoints import (
    CUPS_KEYS,
    apply_borderless_content_scale,
    create_borderless_calibration_image,
    is_explicit_borderless_media,
    media_size_mm_from_value,
    parse_cups_options_output,
    parse_cups_request_id,
    pretty_option_label,
    query_cups_job_status_text,
    resolve_cups_media_value,
)
from album_printer.app_rendering_entrypoints import (
    DEFAULT_STAMP_BORDER_COLOR,
    DEFAULT_STAMP_COLOR,
    STAMP_FONTS,
    apply_stamp,
    render_image,
    render_preview_image,
)
from album_printer.app_runtime_entrypoints import (
    APP_DISPLAY_NAME,
    app_about_text,
    app_version,
    create_splash_screen,
    is_debugger_attached,
)
from album_printer.ipp_backend import (
    IppBackendError,
    IppCapabilities,
    get_ipp_capabilities,
    print_jobs_via_ipp,
)
from album_printer.location.nominatim_service import (
    reverse_geocode_nominatim as reverse_geocode_nominatim_service,
)
from album_printer.printing.flows.dispatch import (
    execute_print_paths as execute_print_paths_flow,
)
from album_printer.printing.flows.history import (
    clear_failed_logs_for_selected as clear_failed_logs_for_selected_flow,
)
from album_printer.printing.flows.history import (
    clear_selected_print_status as clear_selected_print_status_flow,
)
from album_printer.printing.flows.history import (
    ensure_photo_entry_for_path as ensure_photo_entry_for_path_flow,
)
from album_printer.printing.flows.history import (
    is_already_printed as is_already_printed_flow,
)
from album_printer.printing.flows.history import (
    is_ignored_for_print_all as is_ignored_for_print_all_flow,
)
from album_printer.printing.flows.history import (
    latest_print_status_for_path as latest_print_status_for_path_flow,
)
from album_printer.printing.flows.history import (
    mark_selected_as_printed as mark_selected_as_printed_flow,
)
from album_printer.printing.flows.history import (
    on_ignore_for_print_all_toggled as on_ignore_for_print_all_toggled_flow,
)
from album_printer.printing.flows.history import (
    record_print_history as record_print_history_flow,
)
from album_printer.printing.flows.history import (
    should_include_in_print_all as should_include_in_print_all_flow,
)
from album_printer.printing.flows.history import (
    update_selected_print_info as update_selected_print_info_flow,
)
from album_printer.printing.flows.orchestrator import (
    print_all_via_cups as print_all_via_cups_flow,
)
from album_printer.printing.flows.orchestrator import (
    print_all_via_ipp as print_all_via_ipp_flow,
)
from album_printer.printing.flows.orchestrator import (
    print_all_via_qt as print_all_via_qt_flow,
)
from album_printer.printing.flows.paper import paper_size_mm as paper_size_mm_flow
from album_printer.printing.flows.selection import print_all as print_all_flow
from album_printer.printing.flows.selection import print_paths as print_paths_flow
from album_printer.printing.flows.selection import print_selected as print_selected_flow
from album_printer.printing.flows.selection import (
    selected_paths_for_printing as selected_paths_for_printing_flow,
)
from album_printer.printing.flows.setup import (
    get_cups_capabilities as get_cups_capabilities_flow,
)
from album_printer.printing.flows.setup import (
    is_cups_available as is_cups_available_flow,
)
from album_printer.printing.flows.setup import (
    populate_printers_combo as populate_printers_combo_flow,
)
from album_printer.printing.flows.setup import (
    print_borderless_calibration_pages as print_borderless_calibration_pages_flow,
)
from album_printer.printing.main_window_print_entrypoints import (
    execute_print_paths as execute_print_paths_entrypoint,
)
from album_printer.printing.main_window_print_entrypoints import (
    print_all_via_cups as print_all_via_cups_entrypoint,
)
from album_printer.printing.main_window_print_entrypoints import (
    print_all_via_ipp as print_all_via_ipp_entrypoint,
)
from album_printer.printing.main_window_print_entrypoints import (
    print_all_via_qt as print_all_via_qt_entrypoint,
)
from album_printer.printing.main_window_print_entrypoints import (
    print_borderless_calibration_pages as print_borderless_calibration_pages_entrypoint,
)
from album_printer.printing.main_window_print_entrypoints import (
    print_paths as print_paths_entrypoint,
)
from album_printer.printing.main_window_print_entrypoints import (
    record_print_history as record_print_history_entrypoint,
)
from album_printer.printing.main_window_queue_entrypoints import (
    cancel_selected_queue_item as cancel_selected_queue_item_entrypoint,
)
from album_printer.printing.main_window_queue_entrypoints import (
    clear_finished_queue_items as clear_finished_queue_items_entrypoint,
)
from album_printer.printing.main_window_queue_entrypoints import (
    current_ipp_target_name as current_ipp_target_name_entrypoint,
)
from album_printer.printing.main_window_queue_entrypoints import (
    current_queue_target as current_queue_target_entrypoint,
)
from album_printer.printing.main_window_queue_entrypoints import (
    enqueue_print_paths as enqueue_print_paths_entrypoint,
)
from album_printer.printing.main_window_queue_entrypoints import (
    pause_print_queue as pause_print_queue_entrypoint,
)
from album_printer.printing.main_window_queue_entrypoints import (
    process_print_queue as process_print_queue_entrypoint,
)
from album_printer.printing.main_window_queue_entrypoints import (
    refresh_print_queue_table as refresh_print_queue_table_entrypoint,
)
from album_printer.printing.main_window_queue_entrypoints import (
    remove_selected_queue_item as remove_selected_queue_item_entrypoint,
)
from album_printer.printing.main_window_queue_entrypoints import (
    resume_print_queue as resume_print_queue_entrypoint,
)
from album_printer.processing_settings import ProcessingSettings
from album_printer.settings_store import (
    load_app_project_settings as load_project_settings_from_store,
)
from album_printer.settings_store import (
    save_app_project_settings as save_project_settings_to_store,
)
from album_printer.source_state_store import load_source_state, save_source_state
from album_printer.sources import (
    FolderSource,
    GooglePhotosAlbumUrlSource,
    GooglePhotosSource,
    SourceLoadResult,
)
from album_printer.sources.base import SourceRegistry
from album_printer.sources.flows.album_url import (
    handle_load_google_photos_album_url,
    handle_process_album_sync_live_snapshot,
    handle_source_load_finished,
)
from album_printer.sources.flows.apply import (
    apply_source_load_result as apply_source_load_result_flow,
)
from album_printer.sources.flows.folder_metadata import (
    format_storage_size as format_storage_size_flow,
)
from album_printer.sources.flows.folder_metadata import (
    google_photos_album_url_cache_dir as google_photos_album_url_cache_dir_flow,
)
from album_printer.sources.flows.folder_metadata import (
    google_photos_cache_dir as google_photos_cache_dir_flow,
)
from album_printer.sources.flows.folder_metadata import (
    legacy_metadata_path as legacy_metadata_path_flow,
)
from album_printer.sources.flows.folder_metadata import (
    load_folder_metadata as load_folder_metadata_flow,
)
from album_printer.sources.flows.folder_metadata import (
    metadata_context_key as metadata_context_key_flow,
)
from album_printer.sources.flows.folder_metadata import (
    metadata_index_path as metadata_index_path_flow,
)
from album_printer.sources.flows.folder_metadata import (
    metadata_path as metadata_path_flow,
)
from album_printer.sources.flows.folder_metadata import (
    metadata_root_path as metadata_root_path_flow,
)
from album_printer.sources.flows.folder_metadata import (
    metadata_source_dir as metadata_source_dir_flow,
)
from album_printer.sources.flows.folder_metadata import (
    metadata_source_id as metadata_source_id_flow,
)
from album_printer.sources.flows.folder_metadata import (
    migrate_thumbnail_cache_file as migrate_thumbnail_cache_file_flow,
)
from album_printer.sources.flows.folder_metadata import (
    path_storage_stats as path_storage_stats_flow,
)
from album_printer.sources.flows.folder_metadata import (
    remove_path_tree as remove_path_tree_flow,
)
from album_printer.sources.flows.folder_metadata import (
    save_folder_metadata as save_folder_metadata_flow,
)
from album_printer.sources.flows.folder_metadata import (
    thumbnail_cache_candidate_paths as thumbnail_cache_candidate_paths_flow,
)
from album_printer.sources.flows.folder_metadata import (
    thumbnail_cache_context_dir as thumbnail_cache_context_dir_flow,
)
from album_printer.sources.flows.folder_metadata import (
    thumbnail_cache_file_path as thumbnail_cache_file_path_flow,
)
from album_printer.sources.flows.folder_metadata import (
    thumbnail_cache_legacy_file_path as thumbnail_cache_legacy_file_path_flow,
)
from album_printer.sources.flows.folder_metadata import (
    thumbnail_cache_root_path as thumbnail_cache_root_path_flow,
)
from album_printer.sources.flows.folder_metadata import (
    update_metadata_index as update_metadata_index_flow,
)
from album_printer.sources.flows.load import (
    handle_load_folder,
    handle_load_folder_path,
    handle_load_google_photos,
    handle_refresh_folder,
    handle_source_refresh_finished,
    handle_test_google_setup,
)
from album_printer.sources.flows.metadata_sync import (
    update_source_metadata_for_assets as update_source_metadata_for_assets_flow,
)
from album_printer.sources.flows.startup_bookmarks import (
    on_startup_bookmark_scan_finished as on_startup_bookmark_scan_finished_flow,
)
from album_printer.sources.flows.startup_bookmarks import (
    show_startup_bookmark_updates_prompt as show_startup_bookmark_updates_prompt_flow,
)
from album_printer.sources.flows.startup_bookmarks import (
    startup_scan_bookmarked_google_albums as startup_scan_bookmarked_google_albums_flow,
)
from album_printer.sources.flows.state_sync import (
    merge_global_source_state_into_folder as merge_global_source_state_into_folder_flow,
)
from album_printer.sources.flows.state_sync import (
    metadata_key_for_path as metadata_key_for_path_flow,
)
from album_printer.sources.flows.state_sync import (
    source_captured_at_for_path as source_captured_at_for_path_flow,
)
from album_printer.sources.flows.state_sync import (
    source_photo_id_for_path as source_photo_id_for_path_flow,
)
from album_printer.sources.flows.state_sync import (
    sync_global_source_state_from_path as sync_global_source_state_from_path_flow,
)
from album_printer.sources.flows.sync_controls import (
    cancel_active_source_load_for_switch as cancel_active_source_load_for_switch_flow,
)
from album_printer.sources.flows.sync_controls import (
    start_album_sync_live_updates as start_album_sync_live_updates_flow,
)
from album_printer.sources.flows.sync_controls import (
    stop_album_sync as stop_album_sync_flow,
)
from album_printer.sources.flows.sync_controls import (
    stop_album_sync_live_updates as stop_album_sync_live_updates_flow,
)
from album_printer.sources.flows.sync_controls import (
    update_album_sync_stop_availability as update_album_sync_stop_availability_flow,
)
from album_printer.sources.workers import (
    BookmarkScanWorker,
    SourceLoadWorker,
    SourceRefreshWorker,
)
from album_printer.startup import (
    preload_startup_cache as preload_startup_cache_bootstrap,
)
from album_printer.startup.app_runner import run_application as run_application_flow
from album_printer.ui.album_sync_status_flow import (
    maybe_update_album_sync_status_from_log as maybe_update_album_sync_status_flow,
)
from album_printer.ui.control_visibility_flow import (
    update_aspect_navigation_buttons as update_aspect_navigation_buttons_flow,
)
from album_printer.ui.control_visibility_flow import (
    update_controls_visibility as update_controls_visibility_flow,
)
from album_printer.ui.control_visibility_flow import (
    update_folder_settings_availability as update_folder_settings_availability_flow,
)
from album_printer.ui.control_visibility_flow import (
    update_queue_panel_max_width as update_queue_panel_max_width_flow,
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
from album_printer.ui.custom_location_text_flow import (
    copy_location_from_previous_image as copy_location_from_previous_image_flow,
)
from album_printer.ui.custom_location_text_flow import (
    current_custom_location_text as current_custom_location_text_flow,
)
from album_printer.ui.custom_location_text_flow import (
    load_custom_location_text_history as load_custom_location_text_history_flow,
)
from album_printer.ui.custom_location_text_flow import (
    refresh_custom_location_text_options as refresh_custom_location_text_options_flow,
)
from album_printer.ui.custom_location_text_flow import (
    register_custom_location_text as register_custom_location_text_flow,
)
from album_printer.ui.custom_location_text_flow import (
    save_custom_location_text_history as save_custom_location_text_history_flow,
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
from album_printer.ui.dialog_launchers import (
    open_cache_manager_dialog as open_cache_manager_dialog_flow,
)
from album_printer.ui.dialog_launchers import (
    open_print_settings_dialog as open_print_settings_dialog_flow,
)
from album_printer.ui.dialog_launchers import (
    open_project_settings_dialog as open_project_settings_dialog_flow,
)
from album_printer.ui.dialog_launchers import (
    open_settings_dialog as open_settings_dialog_flow,
)
from album_printer.ui.dialogs.metadata_manager import open_metadata_manager_dialog
from album_printer.ui.dialogs.print_settings import (
    open_print_settings_dialog as open_print_settings_dialog_ui,
)
from album_printer.ui.dialogs.project_settings import (
    open_project_settings_dialog as open_project_settings_dialog_ui,
)
from album_printer.ui.dialogs.settings import (
    open_settings_dialog as open_settings_dialog_ui,
)
from album_printer.ui.dialogs.source_guide import open_source_guide_dialog
from album_printer.ui.footer_progress import (
    clear_footer_progress as clear_footer_progress_flow,
)
from album_printer.ui.footer_progress import (
    on_footer_progress_action_clicked as on_footer_progress_action_clicked_flow,
)
from album_printer.ui.footer_progress import (
    refresh_footer_progress_action as refresh_footer_progress_action_flow,
)
from album_printer.ui.footer_progress import (
    set_footer_progress_action as set_footer_progress_action_flow,
)
from album_printer.ui.footer_progress import (
    update_footer_progress as update_footer_progress_flow,
)
from album_printer.ui.help_flow import show_about_dialog as show_about_dialog_flow
from album_printer.ui.help_flow import (
    show_source_guide_dialog as show_source_guide_dialog_flow,
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
    select_previous_aspect_mismatch as select_previous_aspect_mismatch_flow,
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
    source_aspect_ratio_label_for_path as source_aspect_ratio_label_for_path_flow,
)
from album_printer.ui.image_settings_flow import (
    sync_image_settings_with_files as sync_image_settings_with_files_flow,
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
from album_printer.ui.load_menu import setup_file_load_menu
from album_printer.ui.location_lookup_flow import (
    location_lookup_cache_for_path as location_lookup_cache_for_path_flow,
)
from album_printer.ui.location_lookup_flow import (
    location_lookup_cached_value_for_path as location_lookup_cached_value_for_path_flow,
)
from album_printer.ui.location_lookup_flow import (
    store_location_lookup_for_path as store_location_lookup_for_path_flow,
)
from album_printer.ui.log_console_flow import append_log as append_log_flow
from album_printer.ui.log_console_flow import (
    clear_log_console as clear_log_console_flow,
)
from album_printer.ui.log_console_flow import (
    current_log_level_rank as current_log_level_rank_flow,
)
from album_printer.ui.log_console_flow import (
    current_log_text_filter as current_log_text_filter_flow,
)
from album_printer.ui.log_console_flow import (
    log_entry_visible as log_entry_visible_flow,
)
from album_printer.ui.log_console_flow import log_file_path as log_file_path_flow
from album_printer.ui.log_console_flow import (
    on_log_level_changed as on_log_level_changed_flow,
)
from album_printer.ui.log_console_flow import (
    on_log_text_filter_changed as on_log_text_filter_changed_flow,
)
from album_printer.ui.log_console_flow import (
    refresh_log_console as refresh_log_console_flow,
)
from album_printer.ui.log_console_flow import (
    thread_safe_append_log as thread_safe_append_log_flow,
)
from album_printer.ui.main_window_data_entrypoints import (
    current_table_metadata_batch_size as current_table_metadata_batch_size_entrypoint,
)
from album_printer.ui.main_window_data_entrypoints import (
    date_used_and_source_for_path as date_used_and_source_for_path_entrypoint,
)
from album_printer.ui.main_window_data_entrypoints import (
    effective_location_format_for_path as effective_location_format_for_path_entrypoint,
)
from album_printer.ui.main_window_data_entrypoints import (
    format_location as format_location_entrypoint,
)
from album_printer.ui.main_window_data_entrypoints import (
    gps_resolution_progress_counts as gps_resolution_progress_counts_entrypoint,
)
from album_printer.ui.main_window_data_entrypoints import (
    image_dimensions_for_path as image_dimensions_for_path_entrypoint,
)
from album_printer.ui.main_window_data_entrypoints import (
    image_settings_for_path as image_settings_for_path_entrypoint,
)
from album_printer.ui.main_window_data_entrypoints import (
    location_for_path as location_for_path_entrypoint,
)
from album_printer.ui.main_window_data_entrypoints import (
    location_lookup_status_for_path as location_lookup_status_for_path_entrypoint,
)
from album_printer.ui.main_window_data_entrypoints import (
    path_needs_crop_for_aspect as path_needs_crop_for_aspect_entrypoint,
)
from album_printer.ui.main_window_data_entrypoints import (
    process_table_metadata_batch as process_table_metadata_batch_entrypoint,
)
from album_printer.ui.main_window_data_entrypoints import (
    refresh_gps_resolution_progress as refresh_gps_resolution_progress_entrypoint,
)
from album_printer.ui.main_window_data_entrypoints import (
    update_location_status_for_path as update_location_status_for_path_entrypoint,
)
from album_printer.ui.main_window_startup import initialize_main_window
from album_printer.ui.menu_flow import setup_menu as setup_menu_flow
from album_printer.ui.nominatim_settings_flow import (
    format_nominatim_geocodejson as format_nominatim_geocodejson_flow,
)
from album_printer.ui.nominatim_settings_flow import (
    load_nominatim_cache as load_nominatim_cache_flow,
)
from album_printer.ui.nominatim_settings_flow import (
    load_nominatim_settings as load_nominatim_settings_flow,
)
from album_printer.ui.nominatim_settings_flow import (
    nominatim_cache_key as nominatim_cache_key_flow,
)
from album_printer.ui.nominatim_settings_flow import (
    nominatim_cache_path as nominatim_cache_path_flow,
)
from album_printer.ui.nominatim_settings_flow import (
    nominatim_cache_root as nominatim_cache_root_flow,
)
from album_printer.ui.nominatim_settings_flow import (
    nominatim_payload_cache_key as nominatim_payload_cache_key_flow,
)
from album_printer.ui.nominatim_settings_flow import (
    nominatim_user_agent as nominatim_user_agent_flow,
)
from album_printer.ui.nominatim_settings_flow import (
    reverse_geocode_nominatim as reverse_geocode_nominatim_flow,
)
from album_printer.ui.nominatim_settings_flow import (
    save_nominatim_cache as save_nominatim_cache_flow,
)
from album_printer.ui.nominatim_settings_flow import (
    save_nominatim_settings as save_nominatim_settings_flow,
)
from album_printer.ui.photo_entry_flow import (
    cached_table_values_for_path as cached_table_values_for_path_flow,
)
from album_printer.ui.photo_entry_flow import (
    photo_entry_for_path as photo_entry_for_path_flow,
)
from album_printer.ui.photo_entry_flow import (
    store_table_values_for_path as store_table_values_for_path_flow,
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
from album_printer.ui.project_state_flow import (
    borderless_enabled as borderless_enabled_flow,
)
from album_printer.ui.project_state_flow import (
    current_project_settings_payload as current_project_settings_payload_flow,
)
from album_printer.ui.project_state_flow import (
    default_metadata as default_metadata_flow,
)
from album_printer.ui.project_state_flow import (
    load_app_print_settings as load_app_print_settings_flow,
)
from album_printer.ui.project_state_flow import (
    load_app_project_settings as load_app_project_settings_flow,
)
from album_printer.ui.project_state_flow import (
    persist_project_settings as persist_project_settings_flow,
)
from album_printer.ui.project_state_flow import (
    save_app_print_settings as save_app_print_settings_flow,
)
from album_printer.ui.project_state_flow import (
    save_app_project_settings as save_app_project_settings_flow,
)
from album_printer.ui.project_state_flow import selected_path as selected_path_flow
from album_printer.ui.status_presenter import present_status, present_status_and_log
from album_printer.ui.table_metadata_flow import (
    enqueue_table_metadata_for_paths as enqueue_table_metadata_for_paths_flow,
)
from album_printer.ui.table_metadata_flow import (
    note_table_scrolled as note_table_scrolled_flow,
)
from album_printer.ui.table_metadata_flow import (
    start_table_metadata_resolution as start_table_metadata_resolution_flow,
)
from album_printer.ui.table_metadata_flow import (
    toggle_table_metadata_pause as toggle_table_metadata_pause_flow,
)
from album_printer.ui.table_sort_flow import apply_table_sort as apply_table_sort_flow
from album_printer.ui.table_sort_flow import (
    on_image_table_header_clicked as on_image_table_header_clicked_flow,
)
from album_printer.ui.table_sort_flow import sort_key_for_path as sort_key_for_path_flow
from album_printer.ui.table_sort_flow import (
    update_table_sort_indicator as update_table_sort_indicator_flow,
)
from album_printer.ui.thumbnail_cache_flow import (
    load_cached_thumbnail as load_cached_thumbnail_flow,
)
from album_printer.ui.thumbnail_cache_flow import (
    migrate_thumbnail_cache_for_paths as migrate_thumbnail_cache_for_paths_flow,
)
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
from album_printer.ui.window_event_flow import apply_sort_order as apply_sort_order_flow
from album_printer.ui.window_event_flow import close_event as close_event_flow
from album_printer.ui.window_event_flow import (
    on_image_table_cell_changed as on_image_table_cell_changed_flow,
)
from album_printer.ui.window_event_flow import (
    on_image_table_cell_double_clicked as on_image_table_cell_double_clicked_flow,
)
from album_printer.ui.window_event_flow import resize_event as resize_event_flow
from album_printer.ui.window_state_flow import restore_ui_state as restore_ui_state_flow
from album_printer.ui.window_state_flow import save_ui_state as save_ui_state_flow

OPEN_SETTINGS_DIALOG_FLOW_KWARGS = open_settings_dialog_flow_kwargs(
    nominatim_default_reverse_url=NOMINATIM_DEFAULT_REVERSE_URL,
    nominatim_auth_modes=NOMINATIM_AUTH_MODES,
    nominatim_zoom_level_options=NOMINATIM_ZOOM_LEVEL_OPTIONS,
    app_version_fn=app_version,
    open_settings_dialog_ui_fn=open_settings_dialog_ui,
)

OPEN_PROJECT_SETTINGS_DIALOG_FLOW_KWARGS = open_project_settings_dialog_flow_kwargs(
    crop_ratios=CROP_RATIOS,
    crop_ratio_labels=CROP_RATIO_LABELS,
    location_format_options=LOCATION_FORMAT_OPTIONS,
    location_format_template_default=LOCATION_FORMAT_TEMPLATE_DEFAULT,
    location_template_tokens=LOCATION_TEMPLATE_TOKENS,
    stamp_fonts=STAMP_FONTS,
    stamp_scale_min_percent=STAMP_SCALE_MIN_PERCENT,
    stamp_scale_max_percent=STAMP_SCALE_MAX_PERCENT,
    stamp_offset_min_px=STAMP_OFFSET_MIN_PX,
    stamp_offset_max_px=STAMP_OFFSET_MAX_PX,
    default_stamp_color=DEFAULT_STAMP_COLOR,
    default_stamp_border_color=DEFAULT_STAMP_BORDER_COLOR,
    processing_settings_cls=ProcessingSettings,
    load_image_as_rgb_fn=load_image_as_rgb,
    normalized_geocodejson_geocoding_fn=_normalized_geocodejson_geocoding,
    normalized_geocodejson_feature_fn=_normalized_geocodejson_feature,
    render_location_template_fn=render_location_template,
    location_format_needs_reverse_lookup_fn=location_format_needs_reverse_lookup,
    datetime_for_image_fn=datetime_for_image,
    center_crop_to_ratio_fn=center_crop_to_ratio,
    apply_stamp_fn=apply_stamp,
    open_project_settings_dialog_ui_fn=open_project_settings_dialog_ui,
)

OPEN_PRINT_SETTINGS_DIALOG_FLOW_KWARGS = open_print_settings_dialog_flow_kwargs(
    print_backends=PRINT_BACKENDS,
    ipp_backend_error_cls=IppBackendError,
    get_ipp_capabilities_fn=get_ipp_capabilities,
    pretty_option_label_fn=pretty_option_label,
    is_explicit_borderless_media_fn=is_explicit_borderless_media,
    resolve_cups_media_value_fn=resolve_cups_media_value,
    open_print_settings_dialog_ui_fn=open_print_settings_dialog_ui,
)

LOAD_GOOGLE_PHOTOS_ALBUM_URL_FLOW_KWARGS = load_google_photos_album_url_flow_kwargs(
    worker_cls=SourceLoadWorker,
)

REFRESH_FOLDER_FLOW_KWARGS = refresh_folder_flow_kwargs(
    refresh_worker_cls=SourceRefreshWorker,
)

PRINT_BORDERLESS_CALIBRATION_FLOW_KWARGS = print_borderless_calibration_flow_kwargs(
    media_size_mm_from_value_fn=media_size_mm_from_value,
    create_borderless_calibration_image_fn=create_borderless_calibration_image,
    apply_borderless_content_scale_fn=apply_borderless_content_scale,
    parse_cups_request_id_fn=parse_cups_request_id,
)

PRINT_ALL_VIA_CUPS_FLOW_KWARGS = print_all_via_cups_flow_kwargs(
    resolve_cups_media_value_fn=resolve_cups_media_value,
    render_image_fn=render_image,
    apply_borderless_content_scale_fn=apply_borderless_content_scale,
    parse_cups_request_id_fn=parse_cups_request_id,
    query_cups_job_status_text_fn=query_cups_job_status_text,
)

PRINT_ALL_VIA_QT_FLOW_KWARGS = print_all_via_qt_flow_kwargs(
    media_size_mm_from_value_fn=media_size_mm_from_value,
    render_image_fn=render_image,
    ratios_match_either_orientation_fn=ratios_match_either_orientation,
)

PRINT_ALL_VIA_IPP_FLOW_KWARGS = print_all_via_ipp_flow_kwargs(
    render_image_fn=render_image,
    print_jobs_via_ipp_fn=print_jobs_via_ipp,
    ipp_backend_error_cls=IppBackendError,
)

MAIN_WINDOW_STARTUP_KWARGS = main_window_startup_kwargs(
    app_display_name=APP_DISPLAY_NAME,
    app_window_icon_fn=app_window_icon,
    ipp_capabilities_cls=IppCapabilities,
    source_registry_cls=SourceRegistry,
    folder_source_cls=FolderSource,
    google_photos_source_cls=GooglePhotosSource,
    google_photos_album_url_source_cls=GooglePhotosAlbumUrlSource,
    supported_extensions=SUPPORTED_EXTENSIONS,
    load_source_state_fn=load_source_state,
    settings_org=SETTINGS_ORG,
    settings_app=SETTINGS_APP,
    thumbnail_size=THUMBNAIL_SIZE,
    nominatim_default_reverse_url=NOMINATIM_DEFAULT_REVERSE_URL,
    nominatim_default_rate_limit_seconds=NOMINATIM_DEFAULT_RATE_LIMIT_SECONDS,
    location_format_template_default=LOCATION_FORMAT_TEMPLATE_DEFAULT,
    default_stamp_color=DEFAULT_STAMP_COLOR,
    default_stamp_border_color=DEFAULT_STAMP_BORDER_COLOR,
    table_col_thumb=TABLE_COL_THUMB,
    table_col_state=TABLE_COL_STATE,
    table_col_print=TABLE_COL_PRINT,
    table_col_file=TABLE_COL_FILE,
    table_col_date_used=TABLE_COL_DATE_USED,
    table_col_location=TABLE_COL_LOCATION,
    table_col_aspect=TABLE_COL_ASPECT,
    reframe_handle_size=REFRAME_HANDLE_SIZE,
    per_image_location_stamp_overrides=PER_IMAGE_LOCATION_STAMP_OVERRIDES,
    log_levels=LOG_LEVELS,
)


class MainWindow(QMainWindow):
    log_message_requested = Signal(str, str)

    def __init__(self, startup_cache: dict[str, object] | None = None) -> None:
        super().__init__()
        self.log_message_requested.connect(self.append_log)
        initialize_main_window(
            self,
            startup_cache,
            **MAIN_WINDOW_STARTUP_KWARGS,
        )

    def startup_scan_bookmarked_google_albums(self) -> None:
        startup_scan_bookmarked_google_albums_flow(
            self,
            bookmark_scan_worker_cls=BookmarkScanWorker,
        )

    def on_startup_bookmark_scan_finished(
        self,
        updates: object,
        error: object,
    ) -> None:
        on_startup_bookmark_scan_finished_flow(self, updates, error)

    def show_startup_bookmark_updates_prompt(
        self,
        updates: list[dict[str, object]],
    ) -> None:
        show_startup_bookmark_updates_prompt_flow(self, updates)

    def update_queue_panel_max_width(self) -> None:
        update_queue_panel_max_width_flow(self)

    def restore_ui_state(self) -> None:
        restore_ui_state_flow(
            self,
            is_debugger_attached_fn=is_debugger_attached,
            log_level_rank=LOG_LEVEL_RANK,
        )

    def save_ui_state(self) -> None:
        save_ui_state_flow(self)

    def closeEvent(self, event) -> None:  # noqa: N802
        close_event_flow(
            self,
            event,
            super_close_event_fn=lambda ev: super(MainWindow, self).closeEvent(ev),
        )

    def load_app_print_settings(self) -> None:
        load_app_print_settings_flow(
            self,
            print_backends=set(PRINT_BACKENDS),
            paper_labels=set(PAPER_LABELS),
        )

    def save_app_print_settings(self) -> None:
        save_app_print_settings_flow(self)

    def load_app_project_settings(self) -> None:
        load_app_project_settings_flow(
            self,
            load_project_settings_from_store_fn=load_project_settings_from_store,
            crop_ratios=set(CROP_RATIOS),
            sort_modes=set(SORT_MODES),
            stamp_fonts=set(STAMP_FONTS.keys()),
            stamp_scale_min_percent=STAMP_SCALE_MIN_PERCENT,
            stamp_scale_max_percent=STAMP_SCALE_MAX_PERCENT,
            stamp_offset_min_px=STAMP_OFFSET_MIN_PX,
            stamp_offset_max_px=STAMP_OFFSET_MAX_PX,
        )

    def save_app_project_settings(self) -> None:
        save_app_project_settings_flow(
            self,
            save_project_settings_to_store_fn=save_project_settings_to_store,
        )

    def load_custom_location_text_history(self) -> None:
        load_custom_location_text_history_flow(self)

    def save_custom_location_text_history(self) -> None:
        save_custom_location_text_history_flow(self)

    def register_custom_location_text(self, text: str) -> None:
        register_custom_location_text_flow(self, text)

    def nominatim_cache_root(self) -> Path:
        return nominatim_cache_root_flow(self, settings_org=SETTINGS_ORG)

    def nominatim_cache_path(self) -> Path:
        return nominatim_cache_path_flow(
            self,
            nominatim_cache_filename=NOMINATIM_CACHE_FILENAME,
        )

    def load_nominatim_settings(self) -> None:
        load_nominatim_settings_flow(
            self,
            nominatim_auth_modes=NOMINATIM_AUTH_MODES,
            nominatim_default_rate_limit_seconds=NOMINATIM_DEFAULT_RATE_LIMIT_SECONDS,
        )

    def save_nominatim_settings(self) -> None:
        save_nominatim_settings_flow(self)

    def load_nominatim_cache(self) -> None:
        load_nominatim_cache_flow(self)

    def save_nominatim_cache(self) -> None:
        save_nominatim_cache_flow(
            self,
            nominatim_cache_max_entries=NOMINATIM_CACHE_MAX_ENTRIES,
        )

    def nominatim_user_agent(self) -> str:
        return nominatim_user_agent_flow(self, app_version_fn=app_version)

    def nominatim_cache_key(
        self,
        latitude: float,
        longitude: float,
        format_value: str | None = None,
    ) -> str:
        return nominatim_cache_key_flow(
            self,
            latitude,
            longitude,
            format_value,
        )

    def nominatim_payload_cache_key(
        self,
        latitude: float,
        longitude: float,
    ) -> str:
        return nominatim_payload_cache_key_flow(
            self,
            latitude,
            longitude,
        )

    def format_nominatim_geocodejson(
        self,
        payload: object,
        format_value: str | None = None,
    ) -> str:
        return format_nominatim_geocodejson_flow(
            self,
            payload,
            format_value,
            normalized_geocodejson_geocoding_fn=_normalized_geocodejson_geocoding,
            normalized_geocodejson_feature_fn=_normalized_geocodejson_feature,
            render_location_template_fn=render_location_template,
        )

    def reverse_geocode_nominatim(
        self,
        location: tuple[float, float],
        path: Path | None = None,
        format_value: str | None = None,
    ) -> str:
        return reverse_geocode_nominatim_flow(
            self,
            location,
            path=path,
            format_value=format_value,
            reverse_geocode_nominatim_service_fn=reverse_geocode_nominatim_service,
        )

    def borderless_enabled(self) -> bool:
        return borderless_enabled_flow(self)

    def open_settings_dialog(self) -> None:
        open_settings_dialog_flow(self, **OPEN_SETTINGS_DIALOG_FLOW_KWARGS)

    def setup_menu(self) -> None:
        setup_menu_flow(
            self,
            setup_file_load_menu_fn=setup_file_load_menu,
            qaction_cls=QAction,
        )

    def show_about_dialog(self) -> None:
        show_about_dialog_flow(
            self,
            app_display_name=APP_DISPLAY_NAME,
            load_clearminds_head_pixmap_fn=load_clearminds_head_pixmap,
            load_logo_pixmap_fn=load_logo_pixmap,
            app_about_text_fn=app_about_text,
            qmessagebox_cls=QMessageBox,
        )

    def show_source_guide_dialog(self) -> None:
        show_source_guide_dialog_flow(
            self,
            open_source_guide_dialog_fn=open_source_guide_dialog,
        )

    def default_metadata(self) -> dict[str, object]:
        return default_metadata_flow(self)

    def selected_path(self) -> Path | None:
        return selected_path_flow(self)

    def update_controls_visibility(self) -> None:
        update_controls_visibility_flow(self)

    def update_folder_settings_availability(self) -> None:
        update_folder_settings_availability_flow(self)

    def metadata_key_for_path(self, path: Path) -> str:
        return metadata_key_for_path_flow(self, path)

    def source_photo_id_for_path(self, path: Path) -> str:
        return source_photo_id_for_path_flow(self, path)

    def source_captured_at_for_path(self, path: Path) -> datetime | None:
        return source_captured_at_for_path_flow(self, path)

    def location_for_path(self, path: Path) -> tuple[float, float] | None:
        return location_for_path_entrypoint(self, path)

    def location_lookup_cache_for_path(self, path: Path) -> dict[str, str]:
        return location_lookup_cache_for_path_flow(self, path)

    def location_lookup_cached_value_for_path(
        self,
        path: Path,
        cache_key: str,
    ) -> str | None:
        return location_lookup_cached_value_for_path_flow(self, path, cache_key)

    def store_location_lookup_for_path(
        self,
        path: Path,
        cache_key: str,
        value: str,
    ) -> None:
        store_location_lookup_for_path_flow(self, path, cache_key, value)

    def format_location(
        self,
        location: tuple[float, float] | None,
        path: Path | None = None,
        format_value: str | None = None,
    ) -> str:
        return format_location_entrypoint(self, location, path, format_value)

    def effective_location_format_for_path(
        self,
        path: Path,
        values: dict[str, object] | None = None,
    ) -> str | None:
        return effective_location_format_for_path_entrypoint(self, path, values)

    def location_lookup_status_for_path(self, path: Path) -> str:
        return location_lookup_status_for_path_entrypoint(self, path)

    def update_location_status_for_path(self, path: Path) -> None:
        update_location_status_for_path_entrypoint(self, path)

    def rebuild_image_row_lookup(self) -> None:
        rebuild_image_row_lookup_flow(self)

    def row_for_path(self, path: Path) -> int | None:
        return row_for_path_flow(self, path)

    def sync_global_source_state_from_path(self, path: Path) -> None:
        sync_global_source_state_from_path_flow(
            self,
            path,
            settings_org=SETTINGS_ORG,
            save_source_state_fn=save_source_state,
        )

    def merge_global_source_state_into_folder(self) -> bool:
        return merge_global_source_state_into_folder_flow(self)

    def update_source_metadata_for_assets(self) -> bool:
        return update_source_metadata_for_assets_flow(self)

    def apply_source_load_result(
        self,
        result: SourceLoadResult,
        open_settings_if_new: bool,
        preferred_path: Path | None,
    ) -> None:
        apply_source_load_result_flow(
            self,
            result,
            open_settings_if_new,
            preferred_path,
            table_col_file=TABLE_COL_FILE,
        )

    def metadata_root_path(self) -> Path:
        return metadata_root_path_flow(settings_org=SETTINGS_ORG)

    def metadata_source_id(self) -> str:
        return metadata_source_id_flow(self)

    def metadata_source_dir(self) -> Path:
        return metadata_source_dir_flow(self, settings_org=SETTINGS_ORG)

    @staticmethod
    def format_storage_size(value_bytes: int) -> str:
        return format_storage_size_flow(value_bytes)

    @staticmethod
    def path_storage_stats(path: Path) -> tuple[int, int]:
        return path_storage_stats_flow(path)

    @staticmethod
    def remove_path_tree(path: Path) -> tuple[int, int]:
        return remove_path_tree_flow(path)

    def google_photos_cache_dir(self) -> Path:
        return google_photos_cache_dir_flow(settings_org=SETTINGS_ORG)

    def google_photos_album_url_cache_dir(self) -> Path:
        return google_photos_album_url_cache_dir_flow(settings_org=SETTINGS_ORG)

    def open_cache_manager_dialog(self) -> None:
        open_cache_manager_dialog_flow(
            self,
            open_metadata_manager_dialog_fn=open_metadata_manager_dialog,
        )

    def thumbnail_cache_root_path(self) -> Path:
        return thumbnail_cache_root_path_flow(settings_org=SETTINGS_ORG)

    def thumbnail_cache_context_dir(self) -> Path:
        return thumbnail_cache_context_dir_flow(self, settings_org=SETTINGS_ORG)

    def thumbnail_cache_file_path(self, path: Path) -> Path:
        return thumbnail_cache_file_path_flow(
            self,
            path,
            settings_org=SETTINGS_ORG,
        )

    def thumbnail_cache_legacy_file_path(self, path: Path) -> Path:
        return thumbnail_cache_legacy_file_path_flow(
            self,
            path,
            settings_org=SETTINGS_ORG,
        )

    def thumbnail_cache_candidate_paths(self, path: Path) -> tuple[Path, Path]:
        return thumbnail_cache_candidate_paths_flow(
            self,
            path,
            settings_org=SETTINGS_ORG,
        )

    def load_cached_thumbnail(self, path: Path) -> QPixmap | None:
        return load_cached_thumbnail_flow(self, path)

    def migrate_thumbnail_cache_file(
        self,
        path: Path,
        *,
        source_mtime_ns: int | None = None,
    ) -> bool:
        return migrate_thumbnail_cache_file_flow(
            self,
            path,
            source_mtime_ns=source_mtime_ns,
        )

    def migrate_thumbnail_cache_for_paths(self, paths: list[Path]) -> int:
        return migrate_thumbnail_cache_for_paths_flow(self, paths)

    def metadata_index_path(self) -> Path:
        return metadata_index_path_flow(self)

    def metadata_context_key(self) -> str:
        return metadata_context_key_flow(self)

    def legacy_metadata_path(self) -> Path | None:
        return legacy_metadata_path_flow(self, metadata_filename=METADATA_FILENAME)

    def metadata_path(self) -> Path | None:
        return metadata_path_flow(self)

    def update_metadata_index(self, metadata_file_path: Path) -> None:
        update_metadata_index_flow(self, metadata_file_path)

    def log_file_path(self) -> Path | None:
        return log_file_path_flow(
            self,
            settings_org=SETTINGS_ORG,
            log_filename=LOG_FILENAME,
        )

    def current_log_level_rank(self) -> int:
        return current_log_level_rank_flow(self, log_level_rank=LOG_LEVEL_RANK)

    def current_log_text_filter(self) -> str:
        return current_log_text_filter_flow(self)

    def _log_entry_visible(self, level: str, line: str) -> bool:
        return log_entry_visible_flow(
            self,
            level,
            line,
            log_level_rank=LOG_LEVEL_RANK,
        )

    def refresh_log_console(self) -> None:
        refresh_log_console_flow(self)

    def on_log_level_changed(self, value: str) -> None:
        on_log_level_changed_flow(self, value, log_level_rank=LOG_LEVEL_RANK)

    def on_log_text_filter_changed(self, value: str) -> None:
        on_log_text_filter_changed_flow(self, value)

    def clear_log_console(self) -> None:
        clear_log_console_flow(self)

    def refresh_print_queue_table(self) -> None:
        refresh_print_queue_table_entrypoint(self)

    def current_queue_target(self) -> str:
        return current_queue_target_entrypoint(self)

    def current_ipp_target_name(self) -> str:
        return current_ipp_target_name_entrypoint(self)

    def enqueue_print_paths(self, paths: list[Path]) -> None:
        enqueue_print_paths_entrypoint(self, paths)

    def process_print_queue(self) -> None:
        process_print_queue_entrypoint(self)

    def pause_print_queue(self) -> None:
        pause_print_queue_entrypoint(self)

    def resume_print_queue(self) -> None:
        resume_print_queue_entrypoint(self)

    def remove_selected_queue_item(self) -> None:
        remove_selected_queue_item_entrypoint(self)

    def cancel_selected_queue_item(self) -> None:
        cancel_selected_queue_item_entrypoint(self)

    def clear_finished_queue_items(self) -> None:
        clear_finished_queue_items_entrypoint(self)

    def append_log(self, level: str, message: str) -> None:
        append_log_flow(
            self,
            level,
            message,
            qthread_cls=QThread,
            log_level_rank=LOG_LEVEL_RANK,
        )

    def maybe_update_album_sync_status_from_log(self, level: str, message: str) -> bool:
        return maybe_update_album_sync_status_flow(
            self,
            level,
            message,
            present_status_fn=present_status,
        )

    def update_footer_progress(self, label: str, current: int, total: int) -> None:
        update_footer_progress_flow(self, label, current, total)

    def clear_footer_progress(self) -> None:
        clear_footer_progress_flow(self)

    def gps_resolution_progress_counts(self) -> tuple[int, int]:
        return gps_resolution_progress_counts_entrypoint(self)

    def refresh_gps_resolution_progress(self) -> None:
        refresh_gps_resolution_progress_entrypoint(self)

    def set_footer_progress_action(
        self,
        text: str,
        handler: Callable[[], None] | None,
        *,
        enabled: bool = True,
    ) -> None:
        set_footer_progress_action_flow(
            self,
            text,
            handler,
            enabled=enabled,
        )

    def on_footer_progress_action_clicked(self) -> None:
        on_footer_progress_action_clicked_flow(self)

    def refresh_footer_progress_action(self) -> None:
        refresh_footer_progress_action_flow(self)

    def toggle_table_metadata_pause(self) -> None:
        toggle_table_metadata_pause_flow(
            self,
            present_status_and_log_fn=present_status_and_log,
        )

    def update_album_sync_stop_availability(self) -> None:
        update_album_sync_stop_availability_flow(self)

    def start_album_sync_live_updates(
        self, album_url: str, initial_count: int = 0
    ) -> None:
        start_album_sync_live_updates_flow(self, album_url, initial_count)

    def stop_album_sync_live_updates(self) -> None:
        stop_album_sync_live_updates_flow(self)

    def process_album_sync_live_snapshot(self) -> None:
        handle_process_album_sync_live_snapshot(self)

    def stop_album_sync(self) -> None:
        stop_album_sync_flow(self)

    def cancel_active_source_load_for_switch(self, target_source_label: str) -> None:
        cancel_active_source_load_for_switch_flow(self, target_source_label)

    def thread_safe_append_log(self, level: str, message: str) -> None:
        thread_safe_append_log_flow(self, level, message)

    def current_project_settings_payload(self) -> dict[str, object]:
        return current_project_settings_payload_flow(self)

    def persist_project_settings(self) -> None:
        persist_project_settings_flow(self)

    def image_settings_for_path(self, path: Path) -> dict[str, object]:
        return image_settings_for_path_entrypoint(self, path)

    def compute_file_hash(self, path: Path) -> str:
        return compute_file_hash_flow(self, path)

    def set_image_entry_file_hash(self, path: Path, entry: dict[str, object]) -> None:
        set_image_entry_file_hash_flow(self, path, entry)

    def sync_image_settings_with_files(self) -> int:
        return sync_image_settings_with_files_flow(self)

    def detect_orientation_for_path(self, path: Path) -> str:
        return detect_orientation_for_path_flow(self, path)

    def image_dimensions_for_path(self, path: Path) -> tuple[int, int]:
        return image_dimensions_for_path_entrypoint(self, path)

    def source_aspect_ratio_label_for_path(self, path: Path) -> str:
        return source_aspect_ratio_label_for_path_flow(self, path)

    def path_needs_crop_for_aspect(self, path: Path) -> bool:
        return path_needs_crop_for_aspect_entrypoint(self, path)

    def aspect_ratio_cell_text_for_path(self, path: Path) -> str:
        return aspect_ratio_cell_text_for_path_flow(self, path)

    def update_aspect_navigation_buttons(self) -> None:
        update_aspect_navigation_buttons_flow(self)

    def photo_entry_for_path(self, path: Path) -> dict[str, object]:
        return photo_entry_for_path_flow(self, path)

    def cached_table_values_for_path(self, path: Path) -> tuple[str, str, str] | None:
        return cached_table_values_for_path_flow(self, path)

    def store_table_values_for_path(
        self,
        path: Path,
        date_text: str,
        location_text: str,
        aspect_text: str,
    ) -> bool:
        return store_table_values_for_path_flow(
            self,
            path,
            date_text,
            location_text,
            aspect_text,
        )

    def ensure_photo_entry_for_path(self, path: Path) -> dict[str, object]:
        return ensure_photo_entry_for_path_flow(self, path)

    def is_ignored_for_print_all(self, path: Path) -> bool:
        return is_ignored_for_print_all_flow(self, path)

    def is_already_printed(self, path: Path) -> bool:
        return is_already_printed_flow(self, path)

    def should_include_in_print_all(self, path: Path) -> bool:
        return should_include_in_print_all_flow(self, path)

    def latest_print_status_for_path(self, path: Path) -> str:
        return latest_print_status_for_path_flow(self, path)

    def on_ignore_for_print_all_toggled(self, checked: bool) -> None:
        on_ignore_for_print_all_toggled_flow(self, checked)

    def mark_selected_as_printed(self) -> None:
        mark_selected_as_printed_flow(self)

    def clear_failed_logs_for_selected(self) -> None:
        clear_failed_logs_for_selected_flow(self)

    def clear_selected_print_status(self) -> None:
        clear_selected_print_status_flow(self)

    def update_selected_print_info(self) -> None:
        update_selected_print_info_flow(self)

    def image_list_label(self, path: Path) -> str:
        return image_list_label_flow(self, path)

    def current_custom_location_text(self) -> str:
        return current_custom_location_text_flow(self)

    def copy_location_from_previous_image(self) -> None:
        copy_location_from_previous_image_flow(self)

    def refresh_custom_location_text_options(
        self, preferred_text: str | None = None
    ) -> None:
        refresh_custom_location_text_options_flow(self, preferred_text)

    def is_crop_settings_modified(self, path: Path) -> bool:
        return is_crop_settings_modified_flow(
            self,
            path,
            normalize_rotation_degrees_fn=normalize_rotation_degrees,
        )

    def date_used_for_path(self, path: Path) -> datetime:
        return date_used_for_path_flow(self, path)

    def date_used_and_source_for_path(self, path: Path) -> tuple[datetime, str]:
        return date_used_and_source_for_path_entrypoint(self, path)

    def start_thumbnail_generation(self) -> None:
        start_thumbnail_generation_flow(
            self,
            thumbnail_ui_cache_warmup_max=THUMBNAIL_UI_CACHE_WARMUP_MAX,
        )

    def fill_thumbnail_workers(self) -> None:
        fill_thumbnail_workers_flow(
            self,
            thumbnail_max_inflight=THUMBNAIL_MAX_INFLIGHT,
            thumbnail_worker_cls=ThumbnailWorker,
            load_image_as_rgb_fn=load_image_as_rgb,
            thumbnail_size=THUMBNAIL_SIZE,
        )

    def on_thumbnail_ready(self, path: object, generation: int, image: object) -> None:
        on_thumbnail_ready_flow(
            self,
            path,
            generation,
            image,
            table_col_thumb=TABLE_COL_THUMB,
        )

    def start_table_metadata_resolution(self) -> None:
        start_table_metadata_resolution_flow(self)

    def note_table_scrolled(self) -> None:
        note_table_scrolled_flow(self)

    def current_table_metadata_batch_size(self) -> int:
        return current_table_metadata_batch_size_entrypoint(self)

    def process_table_metadata_batch(self) -> None:
        process_table_metadata_batch_entrypoint(self)

    def refresh_image_list_labels(self, preferred_path: Path | None = None) -> None:
        refresh_image_list_labels_flow(
            self,
            preferred_path,
            table_col_file=TABLE_COL_FILE,
            reset_paused=False,
        )

    def populate_image_table_row(self, row: int, path: Path) -> None:
        populate_image_table_row_flow(
            self,
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

    def enqueue_table_metadata_for_paths(self, paths: list[Path]) -> None:
        enqueue_table_metadata_for_paths_flow(self, paths)

    def append_image_rows(self, paths: list[Path]) -> None:
        append_image_rows_flow(
            self,
            paths,
            thumbnail_ui_cache_warmup_max=THUMBNAIL_UI_CACHE_WARMUP_MAX,
            table_col_thumb=TABLE_COL_THUMB,
        )

    def update_table_sort_indicator(self) -> None:
        update_table_sort_indicator_flow(self)

    def sort_key_for_path(self, path: Path, column: int) -> object:
        return sort_key_for_path_flow(
            self,
            path,
            column,
            table_col_file=TABLE_COL_FILE,
            table_col_date_used=TABLE_COL_DATE_USED,
            table_col_aspect=TABLE_COL_ASPECT,
        )

    def apply_table_sort(self, preferred_path: Path | None = None) -> None:
        apply_table_sort_flow(
            self,
            preferred_path,
            table_col_file=TABLE_COL_FILE,
            table_col_date_used=TABLE_COL_DATE_USED,
            table_col_aspect=TABLE_COL_ASPECT,
        )

    def on_image_table_header_clicked(self, column: int) -> None:
        on_image_table_header_clicked_flow(self, column)

    def apply_sort_order(self, preferred_path: Path | None = None) -> None:
        apply_sort_order_flow(self, preferred_path)

    def load_folder_metadata(self) -> None:
        load_folder_metadata_flow(self)

    def save_folder_metadata(self) -> None:
        save_folder_metadata_flow(self)

    def restore_image_settings_for_selected(self) -> None:
        restore_image_settings_for_selected_flow(
            self,
            per_image_location_stamp_overrides=PER_IMAGE_LOCATION_STAMP_OVERRIDES,
        )

    def set_datetime_override_for_selected(self) -> None:
        set_datetime_override_for_selected_flow(self)

    def pick_datetime_override(self, path: Path) -> datetime | None:
        return pick_datetime_override_flow(
            self,
            path,
            parse_datetime_override_fn=parse_datetime_override,
            datetime_for_image_fn=datetime_for_image,
        )

    def set_datetime_override_for_path(self, path: Path, value: datetime) -> None:
        set_datetime_override_for_path_flow(self, path, value)

    def clear_datetime_override_for_selected(self) -> None:
        clear_datetime_override_for_selected_flow(self)

    def update_crop_orientation_button_text(self) -> None:
        update_crop_orientation_button_text_flow(self)

    def update_rotate_image_button_text(self) -> None:
        update_rotate_image_button_text_flow(self)

    def toggle_crop_orientation(self) -> None:
        toggle_crop_orientation_flow(self)

    def rotate_selected_image_clockwise(self) -> None:
        rotate_selected_image_clockwise_flow(self)

    def reset_selected_image_rotation(self) -> None:
        reset_selected_image_rotation_flow(self)

    def on_crop_reframe_toggled(self, enabled: bool) -> None:
        on_crop_reframe_toggled_flow(self, enabled)

    def reset_crop_for_selected(self) -> None:
        reset_crop_for_selected_flow(self)

    def resize_corner_at(self, x: int, y: int) -> str | None:
        return resize_corner_at_flow(
            self, x, y, reframe_handle_size=REFRAME_HANDLE_SIZE
        )

    def on_preview_drag_started(self, x: int, y: int) -> None:
        on_preview_drag_started_flow(
            self,
            x,
            y,
            reframe_handle_size=REFRAME_HANDLE_SIZE,
        )

    def on_preview_dragged(self, delta_x: int, delta_y: int, _x: int, _y: int) -> None:
        on_preview_dragged_flow(self, delta_x, delta_y, _x, _y)

    def on_preview_drag_released(self, _x: int, _y: int) -> None:
        on_preview_drag_released_flow(self, _x, _y)

    def compute_overlay_rect_for_current_crop(self) -> tuple[int, int, int, int] | None:
        return compute_overlay_rect_for_current_crop_flow(
            self,
            crop_geometry_for_ratio_fn=crop_geometry_for_ratio,
        )

    def update_preview_overlay_rect(self) -> None:
        update_preview_overlay_rect_flow(self)

    def on_image_settings_changed(self, *_args) -> None:
        on_image_settings_changed_flow(self)

    def processing_settings_for_path(self, path: Path) -> ProcessingSettings:
        return processing_settings_for_path_flow(
            self,
            path,
            normalize_rotation_degrees_fn=normalize_rotation_degrees,
            processing_settings_cls=ProcessingSettings,
        )

    def refresh_preview(self) -> None:
        refresh_preview_flow(
            self,
            load_image_as_rgb_fn=load_image_as_rgb,
            apply_manual_rotation_fn=apply_manual_rotation,
            render_preview_image_fn=render_preview_image,
        )

    def resizeEvent(self, event) -> None:  # noqa: N802
        resize_event_flow(
            self,
            event,
            super_resize_event_fn=lambda ev: super(MainWindow, self).resizeEvent(ev),
        )

    def on_image_changed(self, row: int) -> None:
        on_image_changed_flow(self, row)

    def on_image_table_selection_changed(self, current_row: int, *_args) -> None:
        on_image_table_selection_changed_flow(self, current_row)

    def on_image_table_cell_double_clicked(self, row: int, column: int) -> None:
        on_image_table_cell_double_clicked_flow(self, row, column)

    def on_image_table_cell_changed(self, row: int, column: int) -> None:
        on_image_table_cell_changed_flow(self, row, column)

    def select_previous(self) -> None:
        select_previous_flow(self, table_col_file=TABLE_COL_FILE)

    def select_next(self) -> None:
        select_next_flow(self, table_col_file=TABLE_COL_FILE)

    def select_aspect_mismatch(self, step: int) -> None:
        select_aspect_mismatch_flow(self, step, table_col_file=TABLE_COL_FILE)

    def select_previous_aspect_mismatch(self) -> None:
        select_previous_aspect_mismatch_flow(self)

    def select_next_aspect_mismatch(self) -> None:
        select_next_aspect_mismatch_flow(self)

    def populate_printers_combo(self, combo: QComboBox) -> None:
        populate_printers_combo_flow(self, combo)

    def parse_cups_options(
        self, output: str
    ) -> tuple[dict[str, list[str]], dict[str, str]]:
        return parse_cups_options_output(output)

    def is_cups_available(self) -> bool:
        return is_cups_available_flow()

    def get_cups_capabilities(
        self, printer_name: str
    ) -> tuple[dict[str, list[str]], dict[str, str]]:
        return get_cups_capabilities_flow(self, printer_name, CUPS_KEYS)

    def open_project_settings_dialog(self) -> None:
        open_project_settings_dialog_flow(
            self,
            **OPEN_PROJECT_SETTINGS_DIALOG_FLOW_KWARGS,
        )

    def open_print_settings_dialog(self) -> None:
        open_print_settings_dialog_flow(
            self,
            **OPEN_PRINT_SETTINGS_DIALOG_FLOW_KWARGS,
        )

    def load_folder_path(
        self,
        folder_path: Path,
        open_settings_if_new: bool = False,
        preferred_path: Path | None = None,
    ) -> None:
        handle_load_folder_path(
            self,
            folder_path,
            open_settings_if_new,
            preferred_path,
        )

    def load_folder(self) -> None:
        handle_load_folder(self)

    def load_google_photos(self) -> None:
        handle_load_google_photos(self)

    def load_google_photos_album_url(self) -> None:
        handle_load_google_photos_album_url(
            self,
            **LOAD_GOOGLE_PHOTOS_ALBUM_URL_FLOW_KWARGS,
        )

    def on_source_load_finished(
        self,
        load_id: int,
        result: object,
        error: object,
        payload: object,
    ) -> None:
        handle_source_load_finished(self, load_id, result, error, payload)

    def test_google_setup(self) -> None:
        handle_test_google_setup(self)

    def refresh_folder(self) -> None:
        handle_refresh_folder(
            self,
            **REFRESH_FOLDER_FLOW_KWARGS,
        )

    def on_source_refresh_finished(
        self,
        refresh_id: int,
        result: object,
        error: object,
        preferred_path: object,
    ) -> None:
        handle_source_refresh_finished(
            self,
            refresh_id,
            result,
            error,
            preferred_path,
        )

    def paper_size_mm(self) -> tuple[float, float]:
        return paper_size_mm_flow(self.paper_value)

    def print_borderless_calibration_pages(
        self,
        printer_name: str,
        media_value: str,
        media_type_value: str,
        print_quality_value: str,
        scale_values: list[int],
    ) -> tuple[int, list[str]]:
        calibration_flow = print_borderless_calibration_pages_flow
        calibration_kwargs = PRINT_BORDERLESS_CALIBRATION_FLOW_KWARGS
        return print_borderless_calibration_pages_entrypoint(
            self,
            printer_name,
            media_value,
            media_type_value,
            print_quality_value,
            scale_values,
            print_borderless_calibration_pages_flow=calibration_flow,
            print_borderless_calibration_flow_kwargs=calibration_kwargs,
        )

    def print_all_via_cups(
        self, paths: list[Path], printer_name: str
    ) -> tuple[list[Path], list[str], str, dict[str, str]]:
        return print_all_via_cups_entrypoint(
            self,
            paths,
            printer_name,
            print_all_via_cups_flow=print_all_via_cups_flow,
            print_all_via_cups_flow_kwargs=PRINT_ALL_VIA_CUPS_FLOW_KWARGS,
        )

    def print_all_via_qt(
        self, paths: list[Path], printer_name: str
    ) -> tuple[list[Path], list[str], str]:
        return print_all_via_qt_entrypoint(
            self,
            paths,
            printer_name,
            print_all_via_qt_flow=print_all_via_qt_flow,
            print_all_via_qt_flow_kwargs=PRINT_ALL_VIA_QT_FLOW_KWARGS,
        )

    def selected_paths_for_printing(self) -> list[Path]:
        return selected_paths_for_printing_flow(self)

    def print_selected(self) -> None:
        print_selected_flow(self)

    def record_print_history(
        self,
        attempted_paths: list[Path],
        printed_paths: list[Path],
        failed_names: list[str],
        printer_name: str,
        backend: str,
        error: str,
        job_ids: dict[str, str] | None = None,
    ) -> None:
        record_print_history_entrypoint(
            self,
            attempted_paths,
            printed_paths,
            failed_names,
            printer_name,
            backend,
            error,
            job_ids,
            record_print_history_flow=record_print_history_flow,
        )

    def print_all(self) -> None:
        print_all_flow(self)

    def print_paths(self, paths: list[Path]) -> None:
        print_paths_entrypoint(
            self,
            paths,
            print_paths_flow=print_paths_flow,
        )

    def execute_print_paths(
        self, paths: list[Path]
    ) -> tuple[list[Path], list[str], str, str, str, dict[str, str]]:
        return execute_print_paths_entrypoint(
            self,
            paths,
            execute_print_paths_flow=execute_print_paths_flow,
        )

    def print_all_via_ipp(
        self, paths: list[Path], ipp_uri: str
    ) -> tuple[list[Path], list[str], str, dict[str, str]]:
        return print_all_via_ipp_entrypoint(
            self,
            paths,
            ipp_uri,
            print_all_via_ipp_flow=print_all_via_ipp_flow,
            print_all_via_ipp_flow_kwargs=PRINT_ALL_VIA_IPP_FLOW_KWARGS,
        )


def run_application(argv: Sequence[str] | None = None) -> int:
    return run_application_flow(
        argv,
        main_window_cls=MainWindow,
        app_display_name=APP_DISPLAY_NAME,
        app_organization_name=APP_ORGANIZATION_NAME,
        app_organization_domain=APP_ORGANIZATION_DOMAIN,
        app_desktop_id=APP_DESKTOP_ID,
        app_window_icon_fn=app_window_icon,
        create_splash_screen_fn=create_splash_screen,
        is_debugger_attached_fn=is_debugger_attached,
        preload_startup_cache_fn=preload_startup_cache_bootstrap,
        parse_cups_options_output_fn=parse_cups_options_output,
        get_ipp_capabilities_fn=get_ipp_capabilities,
        ipp_backend_error_cls=IppBackendError,
        settings_org=SETTINGS_ORG,
        settings_app=SETTINGS_APP,
    )
