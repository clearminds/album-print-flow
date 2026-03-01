from __future__ import annotations

from collections.abc import Callable
from typing import Any


def open_project_settings_dialog(
    window: Any,
    *,
    crop_ratios: list[str],
    crop_ratio_labels: dict[str, str],
    location_format_options: list[str],
    location_format_template_default: str,
    location_template_tokens: dict[str, str],
    stamp_fonts: list[str],
    stamp_scale_min_percent: int,
    stamp_scale_max_percent: int,
    stamp_offset_min_px: int,
    stamp_offset_max_px: int,
    default_stamp_color: str,
    default_stamp_border_color: str,
    processing_settings_cls: Any,
    load_image_as_rgb_fn: Callable[..., Any],
    normalized_geocodejson_geocoding_fn: Callable[..., Any],
    normalized_geocodejson_feature_fn: Callable[..., Any],
    render_location_template_fn: Callable[..., Any],
    location_format_needs_reverse_lookup_fn: Callable[[str], bool],
    datetime_for_image_fn: Callable[..., Any],
    center_crop_to_ratio_fn: Callable[..., Any],
    apply_stamp_fn: Callable[..., Any],
    open_project_settings_dialog_ui_fn: Callable[..., Any],
) -> None:
    open_project_settings_dialog_ui_fn(
        window,
        crop_ratios=crop_ratios,
        crop_ratio_labels=crop_ratio_labels,
        location_format_options=location_format_options,
        location_format_template_default=location_format_template_default,
        location_template_tokens=location_template_tokens,
        stamp_fonts=stamp_fonts,
        stamp_scale_min_percent=stamp_scale_min_percent,
        stamp_scale_max_percent=stamp_scale_max_percent,
        stamp_offset_min_px=stamp_offset_min_px,
        stamp_offset_max_px=stamp_offset_max_px,
        default_stamp_color=default_stamp_color,
        default_stamp_border_color=default_stamp_border_color,
        processing_settings_cls=processing_settings_cls,
        load_image_as_rgb_fn=load_image_as_rgb_fn,
        normalized_geocodejson_geocoding_fn=normalized_geocodejson_geocoding_fn,
        normalized_geocodejson_feature_fn=normalized_geocodejson_feature_fn,
        render_location_template_fn=render_location_template_fn,
        location_format_needs_reverse_lookup_fn=location_format_needs_reverse_lookup_fn,
        datetime_for_image_fn=datetime_for_image_fn,
        center_crop_to_ratio_fn=center_crop_to_ratio_fn,
        apply_stamp_fn=apply_stamp_fn,
    )


def open_print_settings_dialog(
    window: Any,
    *,
    print_backends: list[str],
    ipp_backend_error_cls: type[Exception],
    get_ipp_capabilities_fn: Callable[..., Any],
    pretty_option_label_fn: Callable[[str], str],
    is_explicit_borderless_media_fn: Callable[[str], bool],
    resolve_cups_media_value_fn: Callable[..., Any],
    open_print_settings_dialog_ui_fn: Callable[..., Any],
) -> None:
    open_print_settings_dialog_ui_fn(
        window,
        print_backends=print_backends,
        ipp_backend_error_cls=ipp_backend_error_cls,
        get_ipp_capabilities_fn=get_ipp_capabilities_fn,
        pretty_option_label_fn=pretty_option_label_fn,
        is_explicit_borderless_media_fn=is_explicit_borderless_media_fn,
        resolve_cups_media_value_fn=resolve_cups_media_value_fn,
    )


def open_settings_dialog(
    window: Any,
    *,
    nominatim_default_reverse_url: str,
    nominatim_auth_modes: list[str],
    nominatim_zoom_level_options: list[tuple[str, int]],
    app_version_fn: Callable[..., Any],
    open_settings_dialog_ui_fn: Callable[..., Any],
) -> None:
    open_settings_dialog_ui_fn(
        window,
        nominatim_default_reverse_url=nominatim_default_reverse_url,
        nominatim_auth_modes=nominatim_auth_modes,
        nominatim_zoom_level_options=nominatim_zoom_level_options,
        app_version_fn=app_version_fn,
    )


def open_cache_manager_dialog(
    window: Any,
    *,
    open_metadata_manager_dialog_fn: Callable[[Any], None],
) -> None:
    open_metadata_manager_dialog_fn(window)


__all__ = [
    "open_cache_manager_dialog",
    "open_print_settings_dialog",
    "open_project_settings_dialog",
    "open_settings_dialog",
]
