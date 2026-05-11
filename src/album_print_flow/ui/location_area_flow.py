from __future__ import annotations

import math
from typing import Any
from uuid import uuid4


def normalize_location_areas(raw: object) -> list[dict[str, object]]:
    if not isinstance(raw, list):
        return []

    normalized: list[dict[str, object]] = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue

        shape = str(entry.get("shape", "polygon")).strip().lower()

        if shape == "circle":
            center = entry.get("center")
            if not isinstance(center, (list, tuple)) or len(center) != 2:
                continue
            try:
                center_lat = float(center[0])
                center_lon = float(center[1])
                radius = float(entry.get("radius_m"))
            except (TypeError, ValueError):
                continue
            if not (
                -90.0 <= center_lat <= 90.0
                and -180.0 <= center_lon <= 180.0
                and radius > 0.0
            ):
                continue

            name = str(entry.get("name", "")).strip()
            if not name:
                name = f"Area {len(normalized) + 1}"

            text = str(entry.get("text", "")).strip()
            enabled = entry.get("enabled")
            enabled_value = True if enabled is None else bool(enabled)

            area_id = str(entry.get("id", "")).strip()
            if not area_id:
                area_id = uuid4().hex

            normalized.append(
                {
                    "id": area_id,
                    "name": name,
                    "text": text,
                    "enabled": enabled_value,
                    "shape": "circle",
                    "center": [center_lat, center_lon],
                    "radius_m": radius,
                }
            )
            continue

        raw_polygon = entry.get("polygon")
        points: list[list[float]] = []
        if isinstance(raw_polygon, list):
            for item in raw_polygon:
                if not isinstance(item, (list, tuple)) or len(item) != 2:
                    continue
                try:
                    lat = float(item[0])
                    lon = float(item[1])
                except (TypeError, ValueError):
                    continue
                if -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0:
                    points.append([lat, lon])

        if len(points) < 3:
            bounds = entry.get("bounds")
            if (
                shape == "rectangle"
                and isinstance(bounds, (list, tuple))
                and len(bounds) == 2
            ):
                try:
                    south = float(bounds[0][0])
                    west = float(bounds[0][1])
                    north = float(bounds[1][0])
                    east = float(bounds[1][1])
                except (TypeError, ValueError, IndexError):
                    continue
                if (
                    -90.0 <= south <= 90.0
                    and -90.0 <= north <= 90.0
                    and -180.0 <= west <= 180.0
                    and -180.0 <= east <= 180.0
                ):
                    points = [
                        [south, west],
                        [south, east],
                        [north, east],
                        [north, west],
                    ]
            if len(points) < 3:
                continue

        name = str(entry.get("name", "")).strip()
        if not name:
            name = f"Area {len(normalized) + 1}"

        text = str(entry.get("text", "")).strip()
        enabled = entry.get("enabled")
        enabled_value = True if enabled is None else bool(enabled)

        area_id = str(entry.get("id", "")).strip()
        if not area_id:
            area_id = uuid4().hex

        normalized.append(
            {
                "id": area_id,
                "name": name,
                "text": text,
                "enabled": enabled_value,
                "shape": "rectangle" if shape == "rectangle" else "polygon",
                "polygon": points,
                "bounds": entry.get("bounds") if shape == "rectangle" else None,
            }
        )

    return normalized


def _load_global_location_areas(window: Any) -> list[dict[str, object]]:
    raw = window.ui_settings.value("location/areas")
    return normalize_location_areas(raw)


def _store_global_location_areas(
    window: Any, areas: list[dict[str, object]]
) -> list[dict[str, object]]:
    normalized = normalize_location_areas(areas)
    window.ui_settings.setValue("location/areas", normalized)
    window.ui_settings.sync()
    return normalized


def _maybe_migrate_folder_location_areas(window: Any) -> list[dict[str, object]]:
    global_areas = _load_global_location_areas(window)
    if global_areas:
        return global_areas
    raw = window.folder_metadata.get("location_areas")
    migrated = normalize_location_areas(raw)
    if migrated:
        return _store_global_location_areas(window, migrated)
    return []


def location_areas_for_window(window: Any) -> list[dict[str, object]]:
    return _maybe_migrate_folder_location_areas(window)


def store_location_areas(
    window: Any, areas: list[dict[str, object]]
) -> list[dict[str, object]]:
    return _store_global_location_areas(window, areas)


def _point_in_polygon(
    latitude: float,
    longitude: float,
    polygon: list[list[float]],
) -> bool:
    inside = False
    count = len(polygon)
    if count < 3:
        return False

    j = count - 1
    for i in range(count):
        lat_i, lon_i = polygon[i]
        lat_j, lon_j = polygon[j]
        intersects = (lat_i > latitude) != (lat_j > latitude)
        if intersects:
            denom = (lat_j - lat_i) or 1e-12
            lon_at_lat = (lon_j - lon_i) * (latitude - lat_i) / denom + lon_i
            if longitude < lon_at_lat:
                inside = not inside
        j = i
    return inside


def _haversine_m(
    lat1: float, lon1: float, lat2: float, lon2: float
) -> float:
    rad = math.radians
    dlat = rad(lat2 - lat1)
    dlon = rad(lon2 - lon1)
    lat1 = rad(lat1)
    lat2 = rad(lat2)
    sin_dlat = math.sin(dlat / 2.0)
    sin_dlon = math.sin(dlon / 2.0)
    a = sin_dlat**2 + math.cos(lat1) * math.cos(lat2) * sin_dlon**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return 6371000.0 * c


def location_area_text_for_location(
    window: Any,
    location: tuple[float, float] | None,
) -> str | None:
    if location is None:
        return None

    latitude, longitude = location
    areas = window.location_areas_for_window()
    for area in areas:
        if not area.get("enabled", True):
            continue
        text = str(area.get("text", "")).strip()
        if not text:
            continue
        shape = str(area.get("shape", "polygon")).strip().lower()
        if shape == "circle":
            center = area.get("center")
            radius = area.get("radius_m")
            if (
                isinstance(center, (list, tuple))
                and len(center) == 2
                and isinstance(radius, (int, float))
            ):
                center_lat = float(center[0])
                center_lon = float(center[1])
                if _haversine_m(latitude, longitude, center_lat, center_lon) <= float(
                    radius
                ):
                    return text
            continue

        polygon = area.get("polygon")
        if not isinstance(polygon, list):
            continue
        if _point_in_polygon(latitude, longitude, polygon):
            return text

    return None


def location_area_text_for_path(window: Any, path: Any) -> str | None:
    location = window.location_for_path(path)
    return location_area_text_for_location(window, location)


__all__ = [
    "location_area_text_for_location",
    "location_area_text_for_path",
    "location_areas_for_window",
    "normalize_location_areas",
    "store_location_areas",
]
