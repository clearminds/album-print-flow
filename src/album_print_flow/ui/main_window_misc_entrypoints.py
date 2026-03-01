from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from album_print_flow.sources.flows.startup_bookmarks import (
    on_startup_bookmark_scan_finished as on_startup_bookmark_scan_finished_flow,
)
from album_print_flow.sources.flows.startup_bookmarks import (
    show_startup_bookmark_updates_prompt as show_startup_bookmark_updates_prompt_flow,
)
from album_print_flow.sources.flows.startup_bookmarks import (
    startup_scan_bookmarked_google_albums as startup_scan_bookmarked_google_albums_flow,
)
from album_print_flow.sources.flows.state_sync import (
    metadata_key_for_path as metadata_key_for_path_flow,
)
from album_print_flow.sources.flows.state_sync import (
    source_captured_at_for_path as source_captured_at_for_path_flow,
)
from album_print_flow.sources.flows.state_sync import (
    source_photo_id_for_path as source_photo_id_for_path_flow,
)
from album_print_flow.sources.flows.sync_controls import (
    cancel_active_source_load_for_switch as cancel_active_source_load_for_switch_flow,
)
from album_print_flow.sources.flows.sync_controls import (
    start_album_sync_live_updates as start_album_sync_live_updates_flow,
)
from album_print_flow.sources.flows.sync_controls import (
    stop_album_sync as stop_album_sync_flow,
)
from album_print_flow.sources.flows.sync_controls import (
    stop_album_sync_live_updates as stop_album_sync_live_updates_flow,
)
from album_print_flow.sources.flows.sync_controls import (
    update_album_sync_stop_availability as update_album_sync_stop_availability_flow,
)
from album_print_flow.ui.album_sync_status_flow import (
    maybe_update_album_sync_status_from_log as maybe_update_album_sync_status_flow,
)
from album_print_flow.ui.control_visibility_flow import (
    update_controls_visibility as update_controls_visibility_flow,
)
from album_print_flow.ui.control_visibility_flow import (
    update_folder_settings_availability as update_folder_settings_availability_flow,
)
from album_print_flow.ui.control_visibility_flow import (
    update_queue_panel_max_width as update_queue_panel_max_width_flow,
)
from album_print_flow.ui.custom_location_text_flow import (
    copy_location_from_previous_image as copy_location_from_previous_image_flow,
)
from album_print_flow.ui.custom_location_text_flow import (
    current_custom_location_text as current_custom_location_text_flow,
)
from album_print_flow.ui.custom_location_text_flow import (
    refresh_custom_location_text_options as refresh_custom_location_text_options_flow,
)
from album_print_flow.ui.dialog_launchers import (
    open_print_settings_dialog as open_print_settings_dialog_flow,
)
from album_print_flow.ui.dialog_launchers import (
    open_project_settings_dialog as open_project_settings_dialog_flow,
)
from album_print_flow.ui.dialog_launchers import (
    open_settings_dialog as open_settings_dialog_flow,
)
from album_print_flow.ui.footer_progress import (
    clear_footer_progress as clear_footer_progress_flow,
)
from album_print_flow.ui.footer_progress import (
    on_footer_progress_action_clicked as on_footer_progress_action_clicked_flow,
)
from album_print_flow.ui.footer_progress import (
    refresh_footer_progress_action as refresh_footer_progress_action_flow,
)
from album_print_flow.ui.footer_progress import (
    set_footer_progress_action as set_footer_progress_action_flow,
)
from album_print_flow.ui.footer_progress import (
    update_footer_progress as update_footer_progress_flow,
)
from album_print_flow.ui.help_flow import show_about_dialog as show_about_dialog_flow
from album_print_flow.ui.help_flow import (
    show_source_guide_dialog as show_source_guide_dialog_flow,
)
from album_print_flow.ui.location_lookup_flow import (
    location_lookup_cache_for_path as location_lookup_cache_for_path_flow,
)
from album_print_flow.ui.location_lookup_flow import (
    location_lookup_cached_value_for_path as location_lookup_cached_value_for_path_flow,
)
from album_print_flow.ui.location_lookup_flow import (
    store_location_lookup_for_path as store_location_lookup_for_path_flow,
)
from album_print_flow.ui.log_console_flow import (
    thread_safe_append_log as thread_safe_append_log_flow,
)
from album_print_flow.ui.menu_flow import setup_menu as setup_menu_flow
from album_print_flow.ui.photo_entry_flow import (
    cached_table_values_for_path as cached_table_values_for_path_flow,
)
from album_print_flow.ui.photo_entry_flow import (
    invalidate_table_cache_for_path as invalidate_table_cache_for_path_flow,
)
from album_print_flow.ui.photo_entry_flow import (
    photo_entry_for_path as photo_entry_for_path_flow,
)
from album_print_flow.ui.photo_entry_flow import (
    store_table_values_for_path as store_table_values_for_path_flow,
)
from album_print_flow.ui.project_state_flow import (
    borderless_enabled as borderless_enabled_flow,
)
from album_print_flow.ui.project_state_flow import (
    current_project_settings_payload as current_project_settings_payload_flow,
)
from album_print_flow.ui.project_state_flow import (
    default_metadata as default_metadata_flow,
)
from album_print_flow.ui.project_state_flow import (
    load_app_print_settings as load_app_print_settings_flow,
)
from album_print_flow.ui.project_state_flow import (
    load_app_project_settings as load_app_project_settings_flow,
)
from album_print_flow.ui.project_state_flow import (
    persist_project_settings as persist_project_settings_flow,
)
from album_print_flow.ui.project_state_flow import (
    save_app_print_settings as save_app_print_settings_flow,
)
from album_print_flow.ui.project_state_flow import (
    save_app_project_settings as save_app_project_settings_flow,
)
from album_print_flow.ui.project_state_flow import selected_path as selected_path_flow
from album_print_flow.ui.table_metadata_flow import (
    toggle_table_metadata_pause as toggle_table_metadata_pause_flow,
)
from album_print_flow.ui.window_state_flow import (
    restore_ui_state as restore_ui_state_flow,
)
from album_print_flow.ui.window_state_flow import save_ui_state as save_ui_state_flow


def startup_scan_bookmarked_google_albums(
    window: Any, bookmark_scan_worker_cls: Any
) -> None:
    startup_scan_bookmarked_google_albums_flow(
        window,
        bookmark_scan_worker_cls=bookmark_scan_worker_cls,
    )


def on_startup_bookmark_scan_finished(
    window: Any,
    updates: object,
    error: object,
) -> None:
    on_startup_bookmark_scan_finished_flow(window, updates, error)


def show_startup_bookmark_updates_prompt(
    window: Any,
    updates: list[dict[str, object]],
) -> None:
    show_startup_bookmark_updates_prompt_flow(window, updates)


def update_queue_panel_max_width(window: Any) -> None:
    update_queue_panel_max_width_flow(window)


def restore_ui_state(
    window: Any,
    *,
    is_debugger_attached_fn: Callable[..., Any],
    log_level_rank: dict[str, int],
) -> None:
    restore_ui_state_flow(
        window,
        is_debugger_attached_fn=is_debugger_attached_fn,
        log_level_rank=log_level_rank,
    )


def save_ui_state(window: Any) -> None:
    save_ui_state_flow(window)


def load_app_print_settings(
    window: Any,
    *,
    print_backends: set[str],
    paper_labels: set[str],
) -> None:
    load_app_print_settings_flow(
        window,
        print_backends=print_backends,
        paper_labels=paper_labels,
    )


def save_app_print_settings(window: Any) -> None:
    save_app_print_settings_flow(window)


def load_app_project_settings(
    window: Any,
    *,
    load_project_settings_from_store_fn: Callable[..., Any],
    crop_ratios: set[str],
    sort_modes: set[str],
    stamp_fonts: set[str],
    stamp_scale_min_percent: int,
    stamp_scale_max_percent: int,
    stamp_offset_min_px: int,
    stamp_offset_max_px: int,
) -> None:
    load_app_project_settings_flow(
        window,
        load_project_settings_from_store_fn=load_project_settings_from_store_fn,
        crop_ratios=crop_ratios,
        sort_modes=sort_modes,
        stamp_fonts=stamp_fonts,
        stamp_scale_min_percent=stamp_scale_min_percent,
        stamp_scale_max_percent=stamp_scale_max_percent,
        stamp_offset_min_px=stamp_offset_min_px,
        stamp_offset_max_px=stamp_offset_max_px,
    )


def save_app_project_settings(
    window: Any,
    *,
    save_project_settings_to_store_fn: Callable[..., Any],
) -> None:
    save_app_project_settings_flow(
        window,
        save_project_settings_to_store_fn=save_project_settings_to_store_fn,
    )


def borderless_enabled(window: Any) -> bool:
    return borderless_enabled_flow(window)


def open_settings_dialog(window: Any, **kwargs: Any) -> None:
    open_settings_dialog_flow(window, **kwargs)


def setup_menu(
    window: Any,
    *,
    setup_file_load_menu_fn: Callable[..., Any],
    qaction_cls: Any,
) -> None:
    setup_menu_flow(
        window,
        setup_file_load_menu_fn=setup_file_load_menu_fn,
        qaction_cls=qaction_cls,
    )


def show_about_dialog(
    window: Any,
    *,
    app_display_name: str,
    load_clearminds_head_pixmap_fn: Callable[..., Any],
    load_logo_pixmap_fn: Callable[..., Any],
    app_about_text_fn: Callable[..., Any],
    qmessagebox_cls: Any,
) -> None:
    show_about_dialog_flow(
        window,
        app_display_name=app_display_name,
        load_clearminds_head_pixmap_fn=load_clearminds_head_pixmap_fn,
        load_logo_pixmap_fn=load_logo_pixmap_fn,
        app_about_text_fn=app_about_text_fn,
        qmessagebox_cls=qmessagebox_cls,
    )


def show_source_guide_dialog(
    window: Any,
    *,
    open_source_guide_dialog_fn: Callable[..., Any],
) -> None:
    show_source_guide_dialog_flow(
        window,
        open_source_guide_dialog_fn=open_source_guide_dialog_fn,
    )


def default_metadata(window: Any) -> dict[str, object]:
    return default_metadata_flow(window)


def selected_path(window: Any) -> Path | None:
    return selected_path_flow(window)


def update_controls_visibility(window: Any) -> None:
    update_controls_visibility_flow(window)


def update_folder_settings_availability(window: Any) -> None:
    update_folder_settings_availability_flow(window)


def metadata_key_for_path(window: Any, path: Path) -> str:
    return metadata_key_for_path_flow(window, path)


def source_photo_id_for_path(window: Any, path: Path) -> str:
    return source_photo_id_for_path_flow(window, path)


def source_captured_at_for_path(window: Any, path: Path) -> datetime | None:
    return source_captured_at_for_path_flow(window, path)


def location_lookup_cache_for_path(window: Any, path: Path) -> dict[str, str]:
    return location_lookup_cache_for_path_flow(window, path)


def location_lookup_cached_value_for_path(
    window: Any,
    path: Path,
    cache_key: str,
) -> str | None:
    return location_lookup_cached_value_for_path_flow(window, path, cache_key)


def store_location_lookup_for_path(
    window: Any,
    path: Path,
    cache_key: str,
    value: str,
) -> None:
    store_location_lookup_for_path_flow(window, path, cache_key, value)


def maybe_update_album_sync_status_from_log(
    window: Any,
    level: str,
    message: str,
    *,
    present_status_fn: Callable[..., Any],
) -> bool:
    return maybe_update_album_sync_status_flow(
        window,
        level,
        message,
        present_status_fn=present_status_fn,
    )


def update_footer_progress(window: Any, label: str, current: int, total: int) -> None:
    update_footer_progress_flow(window, label, current, total)


def clear_footer_progress(window: Any) -> None:
    clear_footer_progress_flow(window)


def set_footer_progress_action(
    window: Any,
    text: str,
    handler: Callable[[], None] | None,
    *,
    enabled: bool = True,
) -> None:
    set_footer_progress_action_flow(
        window,
        text,
        handler,
        enabled=enabled,
    )


def on_footer_progress_action_clicked(window: Any) -> None:
    on_footer_progress_action_clicked_flow(window)


def refresh_footer_progress_action(window: Any) -> None:
    refresh_footer_progress_action_flow(window)


def toggle_table_metadata_pause(
    window: Any,
    *,
    present_status_and_log_fn: Callable[..., Any],
) -> None:
    toggle_table_metadata_pause_flow(
        window,
        present_status_and_log_fn=present_status_and_log_fn,
    )


def update_album_sync_stop_availability(window: Any) -> None:
    update_album_sync_stop_availability_flow(window)


def start_album_sync_live_updates(
    window: Any,
    album_url: str,
    initial_count: int = 0,
) -> None:
    start_album_sync_live_updates_flow(window, album_url, initial_count)


def stop_album_sync_live_updates(window: Any) -> None:
    stop_album_sync_live_updates_flow(window)


def stop_album_sync(window: Any) -> None:
    stop_album_sync_flow(window)


def cancel_active_source_load_for_switch(window: Any, target_source_label: str) -> None:
    cancel_active_source_load_for_switch_flow(window, target_source_label)


def thread_safe_append_log(window: Any, level: str, message: str) -> None:
    thread_safe_append_log_flow(window, level, message)


def current_project_settings_payload(window: Any) -> dict[str, object]:
    return current_project_settings_payload_flow(window)


def persist_project_settings(window: Any) -> None:
    persist_project_settings_flow(window)


def photo_entry_for_path(window: Any, path: Path) -> dict[str, object]:
    return photo_entry_for_path_flow(window, path)


def cached_table_values_for_path(
    window: Any,
    path: Path,
) -> tuple[str, str, str] | None:
    return cached_table_values_for_path_flow(window, path)


def invalidate_table_cache_for_path(window: Any, path: Path) -> None:
    invalidate_table_cache_for_path_flow(window, path)


def store_table_values_for_path(
    window: Any,
    path: Path,
    date_text: str,
    location_text: str,
    aspect_text: str,
) -> bool:
    return store_table_values_for_path_flow(
        window,
        path,
        date_text,
        location_text,
        aspect_text,
    )


def current_custom_location_text(window: Any) -> str:
    return current_custom_location_text_flow(window)


def copy_location_from_previous_image(window: Any) -> None:
    copy_location_from_previous_image_flow(window)


def refresh_custom_location_text_options(
    window: Any,
    preferred_text: str | None = None,
) -> None:
    refresh_custom_location_text_options_flow(window, preferred_text)


def open_project_settings_dialog(window: Any, **kwargs: Any) -> None:
    open_project_settings_dialog_flow(window, **kwargs)


def open_print_settings_dialog(window: Any, **kwargs: Any) -> None:
    open_print_settings_dialog_flow(window, **kwargs)


__all__ = [
    "borderless_enabled",
    "cached_table_values_for_path",
    "invalidate_table_cache_for_path",
    "cancel_active_source_load_for_switch",
    "clear_footer_progress",
    "copy_location_from_previous_image",
    "current_custom_location_text",
    "current_project_settings_payload",
    "default_metadata",
    "load_app_print_settings",
    "load_app_project_settings",
    "location_lookup_cache_for_path",
    "location_lookup_cached_value_for_path",
    "maybe_update_album_sync_status_from_log",
    "metadata_key_for_path",
    "on_footer_progress_action_clicked",
    "on_startup_bookmark_scan_finished",
    "open_print_settings_dialog",
    "open_project_settings_dialog",
    "open_settings_dialog",
    "persist_project_settings",
    "photo_entry_for_path",
    "refresh_custom_location_text_options",
    "refresh_footer_progress_action",
    "restore_ui_state",
    "save_app_print_settings",
    "save_app_project_settings",
    "save_ui_state",
    "selected_path",
    "setup_menu",
    "show_about_dialog",
    "show_source_guide_dialog",
    "show_startup_bookmark_updates_prompt",
    "source_captured_at_for_path",
    "source_photo_id_for_path",
    "start_album_sync_live_updates",
    "startup_scan_bookmarked_google_albums",
    "stop_album_sync",
    "stop_album_sync_live_updates",
    "store_location_lookup_for_path",
    "store_table_values_for_path",
    "set_footer_progress_action",
    "thread_safe_append_log",
    "toggle_table_metadata_pause",
    "update_album_sync_stop_availability",
    "update_controls_visibility",
    "update_folder_settings_availability",
    "update_footer_progress",
    "update_queue_panel_max_width",
]
