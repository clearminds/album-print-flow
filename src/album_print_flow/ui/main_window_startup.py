from __future__ import annotations

from typing import Any

from album_print_flow.ui.main_window_builders import (
    build_main_window_ui,
    finalize_main_window_setup,
    initialize_window_shell,
)
from album_print_flow.ui.main_window_state_init import initialize_main_window_state


def initialize_main_window(
    window: Any,
    startup_cache: dict[str, object] | None,
    *,
    app_display_name: str,
    app_window_icon_fn: Any,
    width: int,
    height: int,
    ipp_capabilities_cls: type,
    source_registry_cls: type,
    folder_source_cls: type,
    google_photos_source_cls: type,
    google_photos_album_url_source_cls: type,
    supported_extensions: tuple[str, ...] | set[str],
    load_source_state_fn: object,
    settings_org: str,
    settings_app: str,
    thumbnail_size: int,
    nominatim_default_reverse_url: str,
    nominatim_default_rate_limit_seconds: float,
    location_format_template_default: str,
    default_stamp_color: str,
    default_stamp_border_color: str,
    table_col_thumb: int,
    table_col_state: int,
    table_col_print: int,
    table_col_file: int,
    table_col_date_used: int,
    table_col_location: int,
    table_col_aspect: int,
    reframe_handle_size: int,
    per_image_location_stamp_overrides: list[str],
    log_levels: list[str],
    startup_scan_delay_ms: int,
) -> None:
    initialize_window_shell(
        window,
        app_display_name=app_display_name,
        app_window_icon_fn=app_window_icon_fn,
        width=width,
        height=height,
    )

    initialize_main_window_state(
        window,
        startup_cache,
        ipp_capabilities_cls=ipp_capabilities_cls,
        source_registry_cls=source_registry_cls,
        folder_source_cls=folder_source_cls,
        google_photos_source_cls=google_photos_source_cls,
        google_photos_album_url_source_cls=google_photos_album_url_source_cls,
        supported_extensions=tuple(supported_extensions),
        load_source_state_fn=load_source_state_fn,
        settings_org=settings_org,
        settings_app=settings_app,
        thumbnail_size=thumbnail_size,
        nominatim_default_reverse_url=nominatim_default_reverse_url,
        nominatim_default_rate_limit_seconds=nominatim_default_rate_limit_seconds,
        location_format_template_default=location_format_template_default,
        default_stamp_color=default_stamp_color,
        default_stamp_border_color=default_stamp_border_color,
        table_col_file=table_col_file,
        table_col_date_used=table_col_date_used,
        table_col_aspect=table_col_aspect,
    )

    build_main_window_ui(
        window,
        table_col_thumb=table_col_thumb,
        table_col_state=table_col_state,
        table_col_print=table_col_print,
        table_col_file=table_col_file,
        table_col_date_used=table_col_date_used,
        table_col_location=table_col_location,
        table_col_aspect=table_col_aspect,
        reframe_handle_size=reframe_handle_size,
        per_image_location_stamp_overrides=per_image_location_stamp_overrides,
        log_levels=log_levels,
    )

    finalize_main_window_setup(window, startup_scan_delay_ms=startup_scan_delay_ms)


__all__ = ["initialize_main_window"]
