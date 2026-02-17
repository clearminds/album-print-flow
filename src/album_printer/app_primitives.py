from __future__ import annotations

import re
from datetime import datetime

from PIL import Image


def parse_datetime_from_filename(filename: str) -> datetime | None:
    patterns = [
        r"(?P<y>\d{4})(?P<m>\d{2})(?P<d>\d{2})[_-]"
        r"(?P<h>\d{2})(?P<mi>\d{2})(?P<s>\d{2})",
        r"(?P<y>\d{4})(?P<m>\d{2})(?P<d>\d{2})[_-](?P<h>\d{2})(?P<mi>\d{2})",
        r"(?P<y>\d{4})(?P<m>\d{2})(?P<d>\d{2})",
    ]
    for pattern in patterns:
        match = re.search(pattern, filename)
        if not match:
            continue
        parts = match.groupdict()
        try:
            return datetime(
                int(parts["y"]),
                int(parts["m"]),
                int(parts["d"]),
                int(parts.get("h") or 0),
                int(parts.get("mi") or 0),
                int(parts.get("s") or 0),
            )
        except ValueError:
            continue
    return None


def parse_datetime_override(value: str) -> datetime | None:
    text = value.strip()
    if not text:
        return None

    if text.endswith("Z"):
        text = text[:-1] + "+00:00"

    try:
        return datetime.fromisoformat(text)
    except ValueError:
        pass

    formats = [
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d",
    ]
    for fmt in formats:
        try:
            parsed = datetime.strptime(text, fmt)
            if fmt == "%Y-%m-%d":
                return parsed.replace(hour=12, minute=0, second=0)
            return parsed
        except ValueError:
            continue
    return None


def _rational_to_float(value: object) -> float | None:
    if isinstance(value, tuple) and len(value) == 2:
        numerator, denominator = value
        try:
            denominator_value = float(denominator)
            if denominator_value == 0:
                return None
            return float(numerator) / denominator_value
        except (TypeError, ValueError, ZeroDivisionError):
            return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _dms_to_decimal(dms_values: object, ref: str) -> float | None:
    if not isinstance(dms_values, (list, tuple)) or len(dms_values) < 3:
        return None

    degrees = _rational_to_float(dms_values[0])
    minutes = _rational_to_float(dms_values[1])
    seconds = _rational_to_float(dms_values[2])
    if degrees is None or minutes is None or seconds is None:
        return None

    value = abs(degrees) + (minutes / 60.0) + (seconds / 3600.0)
    if ref.upper() in {"S", "W"}:
        value = -value
    return value


def decimal_to_dms(value: float, latitude: bool) -> str:
    absolute = abs(value)
    degrees = int(absolute)
    minutes_full = (absolute - degrees) * 60.0
    minutes = int(minutes_full)
    seconds = (minutes_full - minutes) * 60.0
    if latitude:
        hemisphere = "N" if value >= 0 else "S"
    else:
        hemisphere = "E" if value >= 0 else "W"
    return f"{degrees}°{minutes:02d}'{seconds:04.1f}\" {hemisphere}"


def location_format_needs_reverse_lookup(format_value: str) -> bool:
    return format_value in {
        "Address Label",
        "Street Address",
        "City, Region",
        "County, Country",
        "Country",
        "Custom Template",
    }


def _normalized_geocodejson_feature(payload: object) -> dict[str, object]:
    if not isinstance(payload, dict):
        return {}

    raw_features = payload.get("features")
    if isinstance(raw_features, list) and raw_features:
        first = raw_features[0]
        return first if isinstance(first, dict) else {}
    if isinstance(raw_features, dict):
        return raw_features
    return {}


def _normalized_geocodejson_geocoding(payload: object) -> dict[str, str]:
    feature = _normalized_geocodejson_feature(payload)
    if not feature:
        return {}

    properties = feature.get("properties")
    if not isinstance(properties, dict):
        return {}

    geocoding = properties.get("geocoding")
    if not isinstance(geocoding, dict):
        return {}

    result: dict[str, str] = {}
    for key, value in geocoding.items():
        if isinstance(value, str):
            text = value.strip()
            if text:
                result[str(key)] = text
    return result


def render_location_template(template: str, payload: object) -> str:
    geocoding = _normalized_geocodejson_geocoding(payload)
    if not geocoding:
        return ""

    feature = _normalized_geocodejson_feature(payload)
    properties = feature.get("properties") if isinstance(feature, dict) else None
    geocoding_raw = (
        properties.get("geocoding") if isinstance(properties, dict) else None
    )
    admin = geocoding_raw.get("admin") if isinstance(geocoding_raw, dict) else None

    context: dict[str, str] = {key: value for key, value in geocoding.items() if value}
    for field in ("city", "town", "village", "hamlet", "municipality"):
        value = geocoding.get(field, "")
        if value:
            context.setdefault("city", value)
            break

    if isinstance(admin, dict):
        for key, value in admin.items():
            if not isinstance(key, str) or not isinstance(value, str):
                continue
            text = value.strip()
            if text:
                context[f"admin.{key}"] = text

    source = str(template or "").strip()
    if not source:
        return ""

    def _replace(match: re.Match[str]) -> str:
        token = match.group(1).strip()
        return context.get(token, "")

    rendered = re.sub(r"\{([^{}]+)\}", _replace, source)
    rendered = re.sub(r"\s+,", ",", rendered)
    rendered = re.sub(r",\s*,+", ", ", rendered)
    rendered = re.sub(r"\s{2,}", " ", rendered)
    return rendered.strip(" ,")


def center_crop_to_ratio(
    image: Image.Image,
    orientation: str,
    ratio: str,
    zoom_percent: int = 100,
    offset_x_percent: int = 0,
    offset_y_percent: int = 0,
) -> Image.Image:
    left, top, crop_width, crop_height = crop_geometry_for_ratio(
        image.width,
        image.height,
        orientation,
        ratio,
        zoom_percent,
        offset_x_percent,
        offset_y_percent,
    )
    return image.crop((left, top, left + crop_width, top + crop_height))


def crop_geometry_for_ratio(
    width: int,
    height: int,
    orientation: str,
    ratio: str,
    zoom_percent: int = 100,
    offset_x_percent: int = 0,
    offset_y_percent: int = 0,
) -> tuple[int, int, int, int]:
    width = max(1, int(width))
    height = max(1, int(height))

    try:
        a, b = ratio.split(":", maxsplit=1)
        rw = float(a)
        rh = float(b)
        if rw <= 0 or rh <= 0:
            raise ValueError("invalid")
    except (ValueError, TypeError):
        rw, rh = 2.0, 3.0

    target_ratio = rh / rw if orientation == "Landscape" else rw / rh
    source_ratio = width / height

    if source_ratio > target_ratio:
        base_crop_height = height
        base_crop_width = int(height * target_ratio)
    else:
        base_crop_width = width
        base_crop_height = int(width / target_ratio)

    zoom = max(100, zoom_percent) / 100.0
    crop_width = max(1, int(base_crop_width / zoom))
    crop_height = max(1, int(base_crop_height / zoom))

    center_left = (width - crop_width) // 2
    center_top = (height - crop_height) // 2

    max_shift_x = (width - crop_width) // 2
    max_shift_y = (height - crop_height) // 2
    shift_x = int(max_shift_x * (offset_x_percent / 100.0))
    shift_y = int(max_shift_y * (offset_y_percent / 100.0))

    left = max(0, min(width - crop_width, center_left + shift_x))
    top = max(0, min(height - crop_height, center_top + shift_y))
    return left, top, crop_width, crop_height


def target_aspect_ratio_for_orientation(orientation: str, ratio: str) -> float:
    try:
        a, b = ratio.split(":", maxsplit=1)
        rw = float(a)
        rh = float(b)
        if rw <= 0 or rh <= 0:
            raise ValueError("invalid")
    except (ValueError, TypeError):
        rw, rh = 2.0, 3.0
    return rh / rw if orientation == "Landscape" else rw / rh


def parse_ratio_pair(
    value: object, fallback: tuple[float, float] = (2.0, 3.0)
) -> tuple[float, float]:
    try:
        raw_w, raw_h = str(value or "").split(":", maxsplit=1)
        ratio_w = float(raw_w)
        ratio_h = float(raw_h)
        if ratio_w <= 0 or ratio_h <= 0:
            raise ValueError("invalid")
        return ratio_w, ratio_h
    except (TypeError, ValueError):
        return fallback


def ratios_match_either_orientation(
    source_ratio: float,
    target_w: float,
    target_h: float,
    tolerance: float = 0.01,
) -> bool:
    ratio_a = target_w / target_h
    ratio_b = target_h / target_w
    return (
        min(
            abs(source_ratio - ratio_a),
            abs(source_ratio - ratio_b),
        )
        <= tolerance
    )


def normalize_rotation_degrees(value: object) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return 0
    normalized = parsed % 360
    if normalized in {0, 90, 180, 270}:
        return normalized
    return 0


def apply_manual_rotation(image: Image.Image, rotation_degrees: int) -> Image.Image:
    normalized = normalize_rotation_degrees(rotation_degrees)
    if normalized == 0:
        return image
    return image.rotate(-normalized, expand=True)


__all__ = [
    "_dms_to_decimal",
    "_normalized_geocodejson_feature",
    "_normalized_geocodejson_geocoding",
    "_rational_to_float",
    "apply_manual_rotation",
    "center_crop_to_ratio",
    "crop_geometry_for_ratio",
    "decimal_to_dms",
    "location_format_needs_reverse_lookup",
    "normalize_rotation_degrees",
    "parse_datetime_from_filename",
    "parse_datetime_override",
    "parse_ratio_pair",
    "ratios_match_either_orientation",
    "render_location_template",
    "target_aspect_ratio_for_orientation",
]
