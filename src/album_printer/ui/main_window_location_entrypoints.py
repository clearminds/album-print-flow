from __future__ import annotations

from pathlib import Path
from typing import Any

from album_printer.app_constants import (
    NOMINATIM_AUTH_MODES,
    NOMINATIM_CACHE_FILENAME,
    NOMINATIM_CACHE_MAX_ENTRIES,
    NOMINATIM_DEFAULT_RATE_LIMIT_SECONDS,
    SETTINGS_ORG,
)
from album_printer.app_primitives import (
    _normalized_geocodejson_feature,
    _normalized_geocodejson_geocoding,
    render_location_template,
)
from album_printer.app_runtime_entrypoints import app_version
from album_printer.location.nominatim_service import (
    reverse_geocode_nominatim as reverse_geocode_nominatim_service,
)
from album_printer.ui.custom_location_text_flow import (
    load_custom_location_text_history as load_custom_location_text_history_flow,
)
from album_printer.ui.custom_location_text_flow import (
    register_custom_location_text as register_custom_location_text_flow,
)
from album_printer.ui.custom_location_text_flow import (
    save_custom_location_text_history as save_custom_location_text_history_flow,
)
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


def load_custom_location_text_history(window: Any) -> None:
    load_custom_location_text_history_flow(window)


def save_custom_location_text_history(window: Any) -> None:
    save_custom_location_text_history_flow(window)


def register_custom_location_text(window: Any, text: str) -> None:
    register_custom_location_text_flow(window, text)


def nominatim_cache_root(window: Any) -> Path:
    return nominatim_cache_root_flow(window, settings_org=SETTINGS_ORG)


def nominatim_cache_path(window: Any) -> Path:
    return nominatim_cache_path_flow(
        window,
        nominatim_cache_filename=NOMINATIM_CACHE_FILENAME,
    )


def load_nominatim_settings(window: Any) -> None:
    load_nominatim_settings_flow(
        window,
        nominatim_auth_modes=NOMINATIM_AUTH_MODES,
        nominatim_default_rate_limit_seconds=NOMINATIM_DEFAULT_RATE_LIMIT_SECONDS,
    )


def save_nominatim_settings(window: Any) -> None:
    save_nominatim_settings_flow(window)


def load_nominatim_cache(window: Any) -> None:
    load_nominatim_cache_flow(window)


def save_nominatim_cache(window: Any) -> None:
    save_nominatim_cache_flow(
        window,
        nominatim_cache_max_entries=NOMINATIM_CACHE_MAX_ENTRIES,
    )


def nominatim_user_agent(window: Any) -> str:
    return nominatim_user_agent_flow(window, app_version_fn=app_version)


def nominatim_cache_key(
    window: Any,
    latitude: float,
    longitude: float,
    format_value: str | None = None,
) -> str:
    return nominatim_cache_key_flow(
        window,
        latitude,
        longitude,
        format_value,
    )


def nominatim_payload_cache_key(
    window: Any,
    latitude: float,
    longitude: float,
) -> str:
    return nominatim_payload_cache_key_flow(
        window,
        latitude,
        longitude,
    )


def format_nominatim_geocodejson(
    window: Any,
    payload: object,
    format_value: str | None = None,
) -> str:
    return format_nominatim_geocodejson_flow(
        window,
        payload,
        format_value,
        normalized_geocodejson_geocoding_fn=_normalized_geocodejson_geocoding,
        normalized_geocodejson_feature_fn=_normalized_geocodejson_feature,
        render_location_template_fn=render_location_template,
    )


def reverse_geocode_nominatim(
    window: Any,
    location: tuple[float, float],
    path: Path | None = None,
    format_value: str | None = None,
) -> str:
    return reverse_geocode_nominatim_flow(
        window,
        location,
        path=path,
        format_value=format_value,
        reverse_geocode_nominatim_service_fn=reverse_geocode_nominatim_service,
    )


__all__ = [
    "format_nominatim_geocodejson",
    "load_custom_location_text_history",
    "load_nominatim_cache",
    "load_nominatim_settings",
    "nominatim_cache_key",
    "nominatim_cache_path",
    "nominatim_cache_root",
    "nominatim_payload_cache_key",
    "nominatim_user_agent",
    "register_custom_location_text",
    "reverse_geocode_nominatim",
    "save_custom_location_text_history",
    "save_nominatim_cache",
    "save_nominatim_settings",
]
