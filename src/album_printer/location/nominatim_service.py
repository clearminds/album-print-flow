from __future__ import annotations

import base64
import json
import time
from pathlib import Path
from typing import Any
from urllib import parse as urllib_parse
from urllib import request as urllib_request


def reverse_geocode_nominatim(
    window: Any,
    location: tuple[float, float],
    path: Path | None = None,
    format_value: str | None = None,
) -> str:
    if not window.nominatim_enabled_value:
        return ""

    base_url = window.nominatim_reverse_url_value.strip()
    if not base_url:
        return ""

    latitude, longitude = location
    cache_key = window.nominatim_cache_key(
        latitude,
        longitude,
        format_value=format_value,
    )
    payload_cache_key = window.nominatim_payload_cache_key(latitude, longitude)
    cached = None
    if path is not None:
        cached = window.location_lookup_cached_value_for_path(path, cache_key)
    if cached is None:
        cached = window.nominatim_cache.get(cache_key)
    if cached is not None:
        return cached

    payload_cached = window.nominatim_cache.get(payload_cache_key)
    if isinstance(payload_cached, str) and payload_cached.strip():
        try:
            payload = json.loads(payload_cached)
            rendered = window.format_nominatim_geocodejson(
                payload,
                format_value=format_value,
            )
            window.nominatim_cache[cache_key] = rendered
            if path is not None:
                window.store_location_lookup_for_path(path, cache_key, rendered)
            return rendered
        except (TypeError, ValueError, json.JSONDecodeError):
            window.nominatim_cache.pop(payload_cache_key, None)

    min_delay_seconds = max(1.0, window.nominatim_rate_limit_seconds_value)
    elapsed = time.monotonic() - window.nominatim_last_request_at
    if elapsed < min_delay_seconds:
        time.sleep(min_delay_seconds - elapsed)

    params: dict[str, str] = {
        "format": "geocodejson",
        "addressdetails": "1",
        "lat": f"{latitude:.8f}",
        "lon": f"{longitude:.8f}",
        "zoom": str(max(0, min(18, window.nominatim_zoom_value))),
    }
    if window.nominatim_accept_language_value.strip():
        params["accept-language"] = window.nominatim_accept_language_value.strip()
    if window.nominatim_email_value.strip():
        params["email"] = window.nominatim_email_value.strip()

    separator = "&" if "?" in base_url else "?"
    url = f"{base_url}{separator}{urllib_parse.urlencode(params)}"
    request = urllib_request.Request(url)
    request.add_header("User-Agent", window.nominatim_user_agent())
    if window.nominatim_accept_language_value.strip():
        request.add_header(
            "Accept-Language", window.nominatim_accept_language_value.strip()
        )

    auth_mode = window.nominatim_auth_mode_value.strip()
    if auth_mode == "Bearer Token" and window.nominatim_auth_token_value.strip():
        request.add_header(
            "Authorization",
            f"Bearer {window.nominatim_auth_token_value.strip()}",
        )
    elif auth_mode == "Basic Auth" and window.nominatim_auth_username_value.strip():
        token = (
            f"{window.nominatim_auth_username_value}:"
            f"{window.nominatim_auth_password_value}"
        ).encode()
        request.add_header(
            "Authorization",
            "Basic " + base64.b64encode(token).decode("ascii"),
        )

    result = ""
    try:
        with urllib_request.urlopen(request, timeout=12) as response:
            raw = response.read().decode("utf-8", errors="replace")
            payload = json.loads(raw)
        result = window.format_nominatim_geocodejson(payload, format_value=format_value)
        if isinstance(payload, dict) or isinstance(payload, list):
            window.nominatim_cache[payload_cache_key] = json.dumps(
                payload,
                ensure_ascii=False,
            )
        window.append_log(
            "DEBUG",
            "NOMINATIM reverse lookup ok "
            f"lat={latitude:.6f} lon={longitude:.6f} has_result={bool(result)}",
        )
    except Exception as error:
        window.append_log(
            "WARNING",
            "NOMINATIM reverse lookup failed "
            f"lat={latitude:.6f} lon={longitude:.6f}: {error}",
        )
        result = ""
    finally:
        window.nominatim_last_request_at = time.monotonic()

    window.nominatim_cache[cache_key] = result
    if path is not None:
        window.store_location_lookup_for_path(path, cache_key, result)
    window.save_nominatim_cache()
    window.refresh_gps_resolution_progress()
    return result
