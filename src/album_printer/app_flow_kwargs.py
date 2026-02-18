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


__all__ = [
    "load_google_photos_album_url_flow_kwargs",
    "open_print_settings_dialog_flow_kwargs",
    "open_project_settings_dialog_flow_kwargs",
    "open_settings_dialog_flow_kwargs",
    "print_all_via_cups_flow_kwargs",
    "print_all_via_ipp_flow_kwargs",
    "print_all_via_qt_flow_kwargs",
    "print_borderless_calibration_flow_kwargs",
    "refresh_folder_flow_kwargs",
]
