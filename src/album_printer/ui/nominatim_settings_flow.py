from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any


def nominatim_cache_root(window: Any, *, settings_org: str) -> Path:
    return Path.home() / ".cache" / settings_org


def nominatim_cache_path(window: Any, *, nominatim_cache_filename: str) -> Path:
    return window.nominatim_cache_root() / nominatim_cache_filename


def load_nominatim_settings(
    window: Any,
    *,
    nominatim_auth_modes: set[str],
    nominatim_default_rate_limit_seconds: float,
) -> None:
    window.nominatim_enabled_value = bool(
        window.ui_settings.value("nominatim/enabled", window.nominatim_enabled_value)
    )
    window.nominatim_reverse_url_value = str(
        window.ui_settings.value(
            "nominatim/reverse_url", window.nominatim_reverse_url_value
        )
        or ""
    ).strip()
    window.nominatim_auth_mode_value = str(
        window.ui_settings.value(
            "nominatim/auth_mode", window.nominatim_auth_mode_value
        )
        or "None"
    ).strip()
    if window.nominatim_auth_mode_value not in nominatim_auth_modes:
        window.nominatim_auth_mode_value = "None"

    window.nominatim_auth_token_value = str(
        window.ui_settings.value(
            "nominatim/auth_token", window.nominatim_auth_token_value
        )
        or ""
    ).strip()
    window.nominatim_auth_username_value = str(
        window.ui_settings.value(
            "nominatim/auth_username", window.nominatim_auth_username_value
        )
        or ""
    ).strip()
    window.nominatim_auth_password_value = str(
        window.ui_settings.value(
            "nominatim/auth_password", window.nominatim_auth_password_value
        )
        or ""
    )
    window.nominatim_accept_language_value = str(
        window.ui_settings.value(
            "nominatim/accept_language", window.nominatim_accept_language_value
        )
        or ""
    ).strip()
    window.nominatim_email_value = str(
        window.ui_settings.value("nominatim/email", window.nominatim_email_value) or ""
    ).strip()

    try:
        zoom_value = int(
            window.ui_settings.value("nominatim/zoom", window.nominatim_zoom_value)
        )
    except (TypeError, ValueError):
        zoom_value = 18
    window.nominatim_zoom_value = max(0, min(18, zoom_value))

    try:
        rate_limit = float(
            window.ui_settings.value(
                "nominatim/rate_limit_seconds",
                window.nominatim_rate_limit_seconds_value,
            )
        )
    except (TypeError, ValueError):
        rate_limit = nominatim_default_rate_limit_seconds
    window.nominatim_rate_limit_seconds_value = max(1.0, rate_limit)


def save_nominatim_settings(window: Any) -> None:
    window.ui_settings.setValue("nominatim/enabled", window.nominatim_enabled_value)
    window.ui_settings.setValue(
        "nominatim/reverse_url", window.nominatim_reverse_url_value
    )
    window.ui_settings.setValue("nominatim/auth_mode", window.nominatim_auth_mode_value)
    window.ui_settings.setValue(
        "nominatim/auth_token", window.nominatim_auth_token_value
    )
    window.ui_settings.setValue(
        "nominatim/auth_username", window.nominatim_auth_username_value
    )
    window.ui_settings.setValue(
        "nominatim/auth_password", window.nominatim_auth_password_value
    )
    window.ui_settings.setValue(
        "nominatim/accept_language", window.nominatim_accept_language_value
    )
    window.ui_settings.setValue("nominatim/email", window.nominatim_email_value)
    window.ui_settings.setValue("nominatim/zoom", window.nominatim_zoom_value)
    window.ui_settings.setValue(
        "nominatim/rate_limit_seconds", window.nominatim_rate_limit_seconds_value
    )
    window.ui_settings.sync()


def load_nominatim_cache(window: Any) -> None:
    path = window.nominatim_cache_path()
    if not path.exists():
        window.nominatim_cache = {}
        return
    try:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError):
        window.nominatim_cache = {}
        return

    if not isinstance(payload, dict):
        window.nominatim_cache = {}
        return

    cache: dict[str, str] = {}
    for key, value in payload.items():
        if isinstance(key, str) and isinstance(value, str):
            cache[key] = value
    window.nominatim_cache = cache


def save_nominatim_cache(window: Any, *, nominatim_cache_max_entries: int) -> None:
    if len(window.nominatim_cache) > nominatim_cache_max_entries:
        overflow = len(window.nominatim_cache) - nominatim_cache_max_entries
        for key in list(window.nominatim_cache.keys())[:overflow]:
            window.nominatim_cache.pop(key, None)

    path = window.nominatim_cache_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".json.tmp")
        with tmp.open("w", encoding="utf-8") as handle:
            json.dump(window.nominatim_cache, handle, ensure_ascii=False, indent=2)
        tmp.replace(path)
    except OSError:
        return


def nominatim_user_agent(window: Any, *, app_version_fn: Any) -> str:
    base = f"AlbumPrintFlow/{app_version_fn()} (Album Print Flow)"
    email = window.nominatim_email_value.strip()
    if email:
        return f"{base} contact={email}"
    return base


def nominatim_cache_key(
    window: Any,
    latitude: float,
    longitude: float,
    format_value: str | None = None,
) -> str:
    lat = round(latitude, 6)
    lon = round(longitude, 6)
    effective_format = (format_value or window.location_format_value).strip()
    template_part = ""
    if effective_format == "Custom Template":
        template_part = f"|tpl={window.location_format_template_value.strip()}"
    return (
        f"{window.nominatim_reverse_url_value}|{lat:.6f}|{lon:.6f}|"
        f"z{window.nominatim_zoom_value}|lang={window.nominatim_accept_language_value}|"
        f"fmt={effective_format}{template_part}"
    )


def nominatim_payload_cache_key(
    window: Any,
    latitude: float,
    longitude: float,
) -> str:
    lat = round(latitude, 6)
    lon = round(longitude, 6)
    return (
        f"payload|{window.nominatim_reverse_url_value}|{lat:.6f}|{lon:.6f}|"
        f"z{window.nominatim_zoom_value}|lang={window.nominatim_accept_language_value}"
    )


def format_nominatim_geocodejson(
    window: Any,
    payload: object,
    format_value: str | None = None,
    *,
    normalized_geocodejson_geocoding_fn: Callable[[object], dict[str, str]],
    normalized_geocodejson_feature_fn: Callable[[object], dict[str, object]],
    render_location_template_fn: Callable[[str, object], str],
) -> str:
    geocoding = normalized_geocodejson_geocoding_fn(payload)
    if not geocoding:
        return ""

    label = geocoding.get("label", "")
    street = geocoding.get("street", "")
    house_number = geocoding.get("housenumber", "")
    postcode = geocoding.get("postcode", "")
    county = geocoding.get("county", "")
    country = geocoding.get("country", "")

    admin_region = ""
    feature = normalized_geocodejson_feature_fn(payload)
    properties = feature.get("properties") if isinstance(feature, dict) else None
    geocoding_raw = (
        properties.get("geocoding") if isinstance(properties, dict) else None
    )
    admin = geocoding_raw.get("admin") if isinstance(geocoding_raw, dict) else None
    if isinstance(admin, dict):
        for key in ("level6", "level5", "level4", "level3"):
            value = admin.get(key)
            if isinstance(value, str) and value.strip():
                admin_region = value.strip()
                break

    selected_format = (format_value or window.location_format_value).strip()
    if selected_format == "Address Label":
        return label
    if selected_format == "Street Address":
        street_text = " ".join(part for part in [house_number, street] if part)
        if street_text:
            return street_text
        return label
    if selected_format == "City, Region":
        city = ""
        for field in ("city", "town", "village", "hamlet", "municipality"):
            value = geocoding.get(field, "")
            if value:
                city = value
                break
        city_region = ", ".join(part for part in [city, admin_region] if part)
        if city_region:
            return city_region
        return label
    if selected_format == "County, Country":
        county_country = ", ".join(part for part in [county, country] if part)
        if county_country:
            return county_country
        return label
    if selected_format == "Country":
        if country:
            return country
        return label
    if selected_format == "Custom Template":
        rendered = render_location_template_fn(
            window.location_format_template_value,
            payload,
        )
        if rendered:
            return rendered
        return label

    if label:
        return label

    fallback_parts = [
        " ".join(part for part in [house_number, street] if part),
        postcode,
        county,
        country,
    ]
    fallback = ", ".join(part for part in fallback_parts if part)
    return fallback


def reverse_geocode_nominatim(
    window: Any,
    location: tuple[float, float],
    path: Path | None = None,
    format_value: str | None = None,
    *,
    reverse_geocode_nominatim_service_fn: Any,
) -> str:
    return reverse_geocode_nominatim_service_fn(
        window,
        location,
        path=path,
        format_value=format_value,
    )


__all__ = [
    "format_nominatim_geocodejson",
    "load_nominatim_cache",
    "load_nominatim_settings",
    "nominatim_cache_key",
    "nominatim_cache_path",
    "nominatim_payload_cache_key",
    "nominatim_cache_root",
    "nominatim_user_agent",
    "reverse_geocode_nominatim",
    "save_nominatim_cache",
    "save_nominatim_settings",
]
