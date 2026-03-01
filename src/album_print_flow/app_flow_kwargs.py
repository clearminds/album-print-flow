from __future__ import annotations


def open_settings_dialog_flow_kwargs(
    *,
    nominatim_default_reverse_url: str,
    nominatim_auth_modes: list[str],
    nominatim_zoom_level_options: list[tuple[int, str]],
    app_version_fn: object,
    open_settings_dialog_ui_fn: object,
) -> dict[str, object]:
    return {
        "nominatim_default_reverse_url": nominatim_default_reverse_url,
        "nominatim_auth_modes": nominatim_auth_modes,
        "nominatim_zoom_level_options": nominatim_zoom_level_options,
        "app_version_fn": app_version_fn,
        "open_settings_dialog_ui_fn": open_settings_dialog_ui_fn,
    }


def open_project_settings_dialog_flow_kwargs(
    *,
    crop_ratios: list[str],
    crop_ratio_labels: dict[str, str],
    location_format_options: list[str],
    location_format_template_default: str,
    location_template_tokens: list[str],
    stamp_fonts: dict[str, str],
    stamp_scale_min_percent: int,
    stamp_scale_max_percent: int,
    stamp_offset_min_px: int,
    stamp_offset_max_px: int,
    default_stamp_color: str,
    default_stamp_border_color: str,
    processing_settings_cls: object,
    load_image_as_rgb_fn: object,
    normalized_geocodejson_geocoding_fn: object,
    normalized_geocodejson_feature_fn: object,
    render_location_template_fn: object,
    location_format_needs_reverse_lookup_fn: object,
    datetime_for_image_fn: object,
    center_crop_to_ratio_fn: object,
    apply_stamp_fn: object,
    open_project_settings_dialog_ui_fn: object,
) -> dict[str, object]:
    return {
        "crop_ratios": crop_ratios,
        "crop_ratio_labels": crop_ratio_labels,
        "location_format_options": location_format_options,
        "location_format_template_default": location_format_template_default,
        "location_template_tokens": location_template_tokens,
        "stamp_fonts": stamp_fonts,
        "stamp_scale_min_percent": stamp_scale_min_percent,
        "stamp_scale_max_percent": stamp_scale_max_percent,
        "stamp_offset_min_px": stamp_offset_min_px,
        "stamp_offset_max_px": stamp_offset_max_px,
        "default_stamp_color": default_stamp_color,
        "default_stamp_border_color": default_stamp_border_color,
        "processing_settings_cls": processing_settings_cls,
        "load_image_as_rgb_fn": load_image_as_rgb_fn,
        "normalized_geocodejson_geocoding_fn": normalized_geocodejson_geocoding_fn,
        "normalized_geocodejson_feature_fn": normalized_geocodejson_feature_fn,
        "render_location_template_fn": render_location_template_fn,
        "location_format_needs_reverse_lookup_fn": (
            location_format_needs_reverse_lookup_fn
        ),
        "datetime_for_image_fn": datetime_for_image_fn,
        "center_crop_to_ratio_fn": center_crop_to_ratio_fn,
        "apply_stamp_fn": apply_stamp_fn,
        "open_project_settings_dialog_ui_fn": open_project_settings_dialog_ui_fn,
    }


def open_print_settings_dialog_flow_kwargs(
    *,
    print_backends: list[str],
    ipp_backend_error_cls: object,
    get_ipp_capabilities_fn: object,
    pretty_option_label_fn: object,
    is_explicit_borderless_media_fn: object,
    resolve_cups_media_value_fn: object,
    open_print_settings_dialog_ui_fn: object,
) -> dict[str, object]:
    return {
        "print_backends": print_backends,
        "ipp_backend_error_cls": ipp_backend_error_cls,
        "get_ipp_capabilities_fn": get_ipp_capabilities_fn,
        "pretty_option_label_fn": pretty_option_label_fn,
        "is_explicit_borderless_media_fn": is_explicit_borderless_media_fn,
        "resolve_cups_media_value_fn": resolve_cups_media_value_fn,
        "open_print_settings_dialog_ui_fn": open_print_settings_dialog_ui_fn,
    }


def load_google_photos_album_url_flow_kwargs(
    *, worker_cls: object
) -> dict[str, object]:
    return {
        "worker_cls": worker_cls,
    }


def refresh_folder_flow_kwargs(*, refresh_worker_cls: object) -> dict[str, object]:
    return {
        "refresh_worker_cls": refresh_worker_cls,
    }


def print_borderless_calibration_flow_kwargs(
    *,
    media_size_mm_from_value_fn: object,
    create_borderless_calibration_image_fn: object,
    apply_borderless_content_scale_fn: object,
    parse_cups_request_id_fn: object,
) -> dict[str, object]:
    return {
        "media_size_mm_from_value_fn": media_size_mm_from_value_fn,
        "create_borderless_calibration_image_fn": (
            create_borderless_calibration_image_fn
        ),
        "apply_borderless_content_scale_fn": apply_borderless_content_scale_fn,
        "parse_cups_request_id_fn": parse_cups_request_id_fn,
    }


def print_all_via_cups_flow_kwargs(
    *,
    resolve_cups_media_value_fn: object,
    render_image_fn: object,
    apply_borderless_content_scale_fn: object,
    parse_cups_request_id_fn: object,
    query_cups_job_status_text_fn: object,
) -> dict[str, object]:
    return {
        "resolve_cups_media_value_fn": resolve_cups_media_value_fn,
        "render_image_fn": render_image_fn,
        "apply_borderless_content_scale_fn": apply_borderless_content_scale_fn,
        "parse_cups_request_id_fn": parse_cups_request_id_fn,
        "query_cups_job_status_text_fn": query_cups_job_status_text_fn,
    }


def print_all_via_qt_flow_kwargs(
    *,
    media_size_mm_from_value_fn: object,
    render_image_fn: object,
    ratios_match_either_orientation_fn: object,
) -> dict[str, object]:
    return {
        "media_size_mm_from_value_fn": media_size_mm_from_value_fn,
        "render_image_fn": render_image_fn,
        "ratios_match_either_orientation_fn": ratios_match_either_orientation_fn,
    }


def print_all_via_ipp_flow_kwargs(
    *,
    render_image_fn: object,
    print_jobs_via_ipp_fn: object,
    ipp_backend_error_cls: object,
) -> dict[str, object]:
    return {
        "render_image_fn": render_image_fn,
        "print_jobs_via_ipp_fn": print_jobs_via_ipp_fn,
        "ipp_backend_error_cls": ipp_backend_error_cls,
    }


def location_for_path_flow_kwargs(
    *, exif_location_for_image_fn: object
) -> dict[str, object]:
    return {
        "exif_location_for_image_fn": exif_location_for_image_fn,
    }


def format_location_flow_kwargs(
    *,
    decimal_to_dms_fn: object,
    location_format_needs_reverse_lookup_fn: object,
) -> dict[str, object]:
    return {
        "decimal_to_dms_fn": decimal_to_dms_fn,
        "location_format_needs_reverse_lookup_fn": (
            location_format_needs_reverse_lookup_fn
        ),
    }


def effective_location_format_flow_kwargs(
    *, location_format_options: list[str]
) -> dict[str, object]:
    return {
        "location_format_options": location_format_options,
    }


def location_lookup_status_flow_kwargs(
    *, location_format_needs_reverse_lookup_fn: object
) -> dict[str, object]:
    return {
        "location_format_needs_reverse_lookup_fn": (
            location_format_needs_reverse_lookup_fn
        ),
    }


def update_location_status_flow_kwargs(*, table_col_location: int) -> dict[str, object]:
    return {
        "table_col_location": table_col_location,
    }


def image_settings_for_path_flow_kwargs(
    *,
    normalize_rotation_degrees_fn: object,
    per_image_location_stamp_overrides: list[str],
) -> dict[str, object]:
    return {
        "normalize_rotation_degrees_fn": normalize_rotation_degrees_fn,
        "per_image_location_stamp_overrides": per_image_location_stamp_overrides,
    }


def image_dimensions_flow_kwargs(
    *,
    original_metadata_path_for_image_fn: object,
    load_image_as_rgb_fn: object,
) -> dict[str, object]:
    return {
        "original_metadata_path_for_image_fn": original_metadata_path_for_image_fn,
        "load_image_as_rgb_fn": load_image_as_rgb_fn,
    }


def path_needs_crop_flow_kwargs(
    *,
    normalize_rotation_degrees_fn: object,
    parse_ratio_pair_fn: object,
    ratios_match_either_orientation_fn: object,
) -> dict[str, object]:
    return {
        "normalize_rotation_degrees_fn": normalize_rotation_degrees_fn,
        "parse_ratio_pair_fn": parse_ratio_pair_fn,
        "ratios_match_either_orientation_fn": ratios_match_either_orientation_fn,
    }


def date_used_and_source_flow_kwargs(
    *,
    parse_datetime_override_fn: object,
    exif_datetime_for_image_fn: object,
    parse_datetime_from_filename_fn: object,
) -> dict[str, object]:
    return {
        "parse_datetime_override_fn": parse_datetime_override_fn,
        "exif_datetime_for_image_fn": exif_datetime_for_image_fn,
        "parse_datetime_from_filename_fn": parse_datetime_from_filename_fn,
    }


def current_table_metadata_batch_size_flow_kwargs(
    *,
    scroll_window_seconds: float,
    batch_size_scrolling: int,
    batch_size_idle: int,
) -> dict[str, object]:
    return {
        "scroll_window_seconds": scroll_window_seconds,
        "batch_size_scrolling": batch_size_scrolling,
        "batch_size_idle": batch_size_idle,
    }


def process_table_metadata_batch_flow_kwargs(
    *,
    table_col_date_used: int,
    table_col_location: int,
    table_col_aspect: int,
    scroll_window_seconds: float,
    batch_size_scrolling: int,
    batch_size_idle: int,
) -> dict[str, object]:
    return {
        "table_col_date_used": table_col_date_used,
        "table_col_location": table_col_location,
        "table_col_aspect": table_col_aspect,
        "scroll_window_seconds": scroll_window_seconds,
        "batch_size_scrolling": batch_size_scrolling,
        "batch_size_idle": batch_size_idle,
    }


def main_window_startup_kwargs(
    *,
    app_display_name: str,
    app_window_icon_fn: object,
    ipp_capabilities_cls: object,
    source_registry_cls: object,
    folder_source_cls: object,
    google_photos_source_cls: object,
    google_photos_album_url_source_cls: object,
    supported_extensions: set[str],
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
) -> dict[str, object]:
    return {
        "app_display_name": app_display_name,
        "app_window_icon_fn": app_window_icon_fn,
        "width": 1450,
        "height": 920,
        "ipp_capabilities_cls": ipp_capabilities_cls,
        "source_registry_cls": source_registry_cls,
        "folder_source_cls": folder_source_cls,
        "google_photos_source_cls": google_photos_source_cls,
        "google_photos_album_url_source_cls": google_photos_album_url_source_cls,
        "supported_extensions": supported_extensions,
        "load_source_state_fn": load_source_state_fn,
        "settings_org": settings_org,
        "settings_app": settings_app,
        "thumbnail_size": thumbnail_size,
        "nominatim_default_reverse_url": nominatim_default_reverse_url,
        "nominatim_default_rate_limit_seconds": nominatim_default_rate_limit_seconds,
        "location_format_template_default": location_format_template_default,
        "default_stamp_color": default_stamp_color,
        "default_stamp_border_color": default_stamp_border_color,
        "table_col_thumb": table_col_thumb,
        "table_col_state": table_col_state,
        "table_col_print": table_col_print,
        "table_col_file": table_col_file,
        "table_col_date_used": table_col_date_used,
        "table_col_location": table_col_location,
        "table_col_aspect": table_col_aspect,
        "reframe_handle_size": reframe_handle_size,
        "per_image_location_stamp_overrides": per_image_location_stamp_overrides,
        "log_levels": log_levels,
        "startup_scan_delay_ms": 1400,
    }


def build_app_flow_kwargs(**kwargs: object) -> dict[str, dict[str, object]]:
    """Build the full app flow kwargs dict from the flat kwargs passed by app.py."""
    return {
        "open_settings_dialog": open_settings_dialog_flow_kwargs(
            nominatim_default_reverse_url=kwargs["nominatim_default_reverse_url"],
            nominatim_auth_modes=kwargs["nominatim_auth_modes"],
            nominatim_zoom_level_options=kwargs["nominatim_zoom_level_options"],
            app_version_fn=kwargs["app_version_fn"],
            open_settings_dialog_ui_fn=kwargs["open_settings_dialog_ui_fn"],
        ),
        "open_project_settings_dialog": open_project_settings_dialog_flow_kwargs(
            crop_ratios=kwargs["crop_ratios"],
            crop_ratio_labels=kwargs["crop_ratio_labels"],
            location_format_options=kwargs["location_format_options"],
            location_format_template_default=kwargs["location_format_template_default"],
            location_template_tokens=kwargs["location_template_tokens"],
            stamp_fonts=kwargs["stamp_fonts"],
            stamp_scale_min_percent=kwargs["stamp_scale_min_percent"],
            stamp_scale_max_percent=kwargs["stamp_scale_max_percent"],
            stamp_offset_min_px=kwargs["stamp_offset_min_px"],
            stamp_offset_max_px=kwargs["stamp_offset_max_px"],
            default_stamp_color=kwargs["default_stamp_color"],
            default_stamp_border_color=kwargs["default_stamp_border_color"],
            processing_settings_cls=kwargs["processing_settings_cls"],
            load_image_as_rgb_fn=kwargs["load_image_as_rgb_fn"],
            normalized_geocodejson_geocoding_fn=kwargs[
                "normalized_geocodejson_geocoding_fn"
            ],
            normalized_geocodejson_feature_fn=kwargs[
                "normalized_geocodejson_feature_fn"
            ],
            render_location_template_fn=kwargs["render_location_template_fn"],
            location_format_needs_reverse_lookup_fn=kwargs[
                "location_format_needs_reverse_lookup_fn"
            ],
            datetime_for_image_fn=kwargs["datetime_for_image_fn"],
            center_crop_to_ratio_fn=kwargs["center_crop_to_ratio_fn"],
            apply_stamp_fn=kwargs["apply_stamp_fn"],
            open_project_settings_dialog_ui_fn=kwargs[
                "open_project_settings_dialog_ui_fn"
            ],
        ),
        "open_print_settings_dialog": open_print_settings_dialog_flow_kwargs(
            print_backends=kwargs["print_backends"],
            ipp_backend_error_cls=kwargs["ipp_backend_error_cls"],
            get_ipp_capabilities_fn=kwargs["get_ipp_capabilities_fn"],
            pretty_option_label_fn=kwargs["pretty_option_label_fn"],
            is_explicit_borderless_media_fn=kwargs["is_explicit_borderless_media_fn"],
            resolve_cups_media_value_fn=kwargs["resolve_cups_media_value_fn"],
            open_print_settings_dialog_ui_fn=kwargs["open_print_settings_dialog_ui_fn"],
        ),
        "load_google_photos_album_url": load_google_photos_album_url_flow_kwargs(
            worker_cls=kwargs["source_load_worker_cls"],
        ),
        "refresh_folder": refresh_folder_flow_kwargs(
            refresh_worker_cls=kwargs["source_refresh_worker_cls"],
        ),
        "print_borderless_calibration": print_borderless_calibration_flow_kwargs(
            media_size_mm_from_value_fn=kwargs["media_size_mm_from_value_fn"],
            create_borderless_calibration_image_fn=kwargs[
                "create_borderless_calibration_image_fn"
            ],
            apply_borderless_content_scale_fn=kwargs[
                "apply_borderless_content_scale_fn"
            ],
            parse_cups_request_id_fn=kwargs["parse_cups_request_id_fn"],
        ),
        "print_all_via_cups": print_all_via_cups_flow_kwargs(
            resolve_cups_media_value_fn=kwargs["resolve_cups_media_value_fn"],
            render_image_fn=kwargs["render_image_fn"],
            apply_borderless_content_scale_fn=kwargs[
                "apply_borderless_content_scale_fn"
            ],
            parse_cups_request_id_fn=kwargs["parse_cups_request_id_fn"],
            query_cups_job_status_text_fn=kwargs["query_cups_job_status_text_fn"],
        ),
        "print_all_via_qt": print_all_via_qt_flow_kwargs(
            media_size_mm_from_value_fn=kwargs["media_size_mm_from_value_fn"],
            render_image_fn=kwargs["render_image_fn"],
            ratios_match_either_orientation_fn=kwargs[
                "ratios_match_either_orientation_fn"
            ],
        ),
        "print_all_via_ipp": print_all_via_ipp_flow_kwargs(
            render_image_fn=kwargs["render_image_fn"],
            print_jobs_via_ipp_fn=kwargs["print_jobs_via_ipp_fn"],
            ipp_backend_error_cls=kwargs["ipp_backend_error_cls"],
        ),
        "main_window_startup": main_window_startup_kwargs(
            app_display_name=kwargs["app_display_name"],
            app_window_icon_fn=kwargs["app_window_icon_fn"],
            ipp_capabilities_cls=kwargs["ipp_capabilities_cls"],
            source_registry_cls=kwargs["source_registry_cls"],
            folder_source_cls=kwargs["folder_source_cls"],
            google_photos_source_cls=kwargs["google_photos_source_cls"],
            google_photos_album_url_source_cls=kwargs[
                "google_photos_album_url_source_cls"
            ],
            supported_extensions=kwargs["supported_extensions"],
            load_source_state_fn=kwargs["load_source_state_fn"],
            settings_org=kwargs["settings_org"],
            settings_app=kwargs["settings_app"],
            thumbnail_size=kwargs["thumbnail_size"],
            nominatim_default_reverse_url=kwargs["nominatim_default_reverse_url"],
            nominatim_default_rate_limit_seconds=kwargs[
                "nominatim_default_rate_limit_seconds"
            ],
            location_format_template_default=kwargs["location_format_template_default"],
            default_stamp_color=kwargs["default_stamp_color"],
            default_stamp_border_color=kwargs["default_stamp_border_color"],
            table_col_thumb=kwargs["table_col_thumb"],
            table_col_state=kwargs["table_col_state"],
            table_col_print=kwargs["table_col_print"],
            table_col_file=kwargs["table_col_file"],
            table_col_date_used=kwargs["table_col_date_used"],
            table_col_location=kwargs["table_col_location"],
            table_col_aspect=kwargs["table_col_aspect"],
            reframe_handle_size=kwargs["reframe_handle_size"],
            per_image_location_stamp_overrides=kwargs[
                "per_image_location_stamp_overrides"
            ],
            log_levels=kwargs["log_levels"],
        ),
    }


__all__ = [
    "build_app_flow_kwargs",
    "current_table_metadata_batch_size_flow_kwargs",
    "date_used_and_source_flow_kwargs",
    "effective_location_format_flow_kwargs",
    "format_location_flow_kwargs",
    "image_dimensions_flow_kwargs",
    "image_settings_for_path_flow_kwargs",
    "load_google_photos_album_url_flow_kwargs",
    "location_for_path_flow_kwargs",
    "location_lookup_status_flow_kwargs",
    "main_window_startup_kwargs",
    "open_print_settings_dialog_flow_kwargs",
    "open_project_settings_dialog_flow_kwargs",
    "open_settings_dialog_flow_kwargs",
    "path_needs_crop_flow_kwargs",
    "print_all_via_cups_flow_kwargs",
    "print_all_via_ipp_flow_kwargs",
    "print_all_via_qt_flow_kwargs",
    "print_borderless_calibration_flow_kwargs",
    "process_table_metadata_batch_flow_kwargs",
    "refresh_folder_flow_kwargs",
    "update_location_status_flow_kwargs",
]
