from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import QMessageBox

from album_print_flow.app_primitives import crop_geometry_for_ratio, normalize_rotation_degrees


def _explicit_orientation_for_path(window: Any, path: Any) -> str | None:
    settings = window.folder_metadata.get("image_settings")
    if not isinstance(settings, dict):
        return None
    entry = settings.get(window.metadata_key_for_path(path))
    if not isinstance(entry, dict):
        entry = settings.get(path.name)
        if not isinstance(entry, dict):
            return None
    raw = str(entry.get("orientation", "")).strip()
    if raw in {"Landscape", "Portrait"}:
        return raw
    return None


def scan_portrait_crop_candidates(window: Any) -> None:
    if window.current_folder is None or not window.image_paths:
        QMessageBox.information(window, "Scan Portrait Crops", "No images loaded.")
        return

    candidates: list[str] = []
    for path in window.image_paths:
        values = window.image_settings_for_path(path)
        rotation_degrees = normalize_rotation_degrees(values.get("rotation_degrees", 0))
        width, height = window.image_dimensions_for_path(path)
        if rotation_degrees in {90, 270}:
            width, height = height, width

        def crop_area(orientation_value: str) -> int:
            _left, _top, crop_w, crop_h = crop_geometry_for_ratio(
                width,
                height,
                orientation_value,
                window.crop_ratio_value,
                int(values.get("crop_zoom_percent", 100)),
                int(values.get("crop_offset_x_percent", 0)),
                int(values.get("crop_offset_y_percent", 0)),
            )
            return max(1, int(crop_w)) * max(1, int(crop_h))

        area_portrait = crop_area("Portrait")
        area_landscape = crop_area("Landscape")
        if area_portrait <= area_landscape:
            continue

        explicit_orientation = _explicit_orientation_for_path(window, path)
        if explicit_orientation == "Portrait":
            continue

        candidates.append(path.name)

    if not candidates:
        QMessageBox.information(
            window,
            "Scan Portrait Crops",
            "No images found where portrait crop yields a larger area.",
        )
        return

    window.append_log(
        "INFO",
        f"Portrait crop candidates: {len(candidates)} image(s)",
    )
    for name in candidates[:50]:
        window.append_log("INFO", f"Portrait crop candidate: {name}")

    preview = "\n".join(f"- {name}" for name in candidates[:12])
    more = "" if len(candidates) <= 12 else f"\n… and {len(candidates) - 12} more"
    QMessageBox.information(
        window,
        "Scan Portrait Crops",
        f"{len(candidates)} image(s) favor portrait crop:\n\n{preview}{more}",
    )


__all__ = ["scan_portrait_crop_candidates"]
