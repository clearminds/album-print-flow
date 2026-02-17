from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class ProcessingSettings:
    orientation: str = "Landscape"
    rotation_degrees: int = 0
    brightness_percent: int = 100
    crop_ratio: str = "2:3"
    crop_zoom_percent: int = 100
    crop_offset_x_percent: int = 0
    crop_offset_y_percent: int = 0
    stamp_mode: str = "None"
    clock_mode: str = "24h"
    corner: str = "Bottom Right"
    stamp_font: str = "Photo Stamp Mono"
    stamp_scale_percent: int = 100
    stamp_offset_x_px: int = 15
    stamp_offset_y_px: int = 15
    stamp_color: str = "#FF9100"
    stamp_border_color: str = "#000000"
    stamp_vertical: bool = False
    datetime_override: datetime | None = None
    location_text: str = ""
    location_stamp_enabled: bool = False
    location_corner: str = "Top Left"
    location_stamp_scale_percent: int = 90
    location_stamp_offset_x_px: int = 15
    location_stamp_offset_y_px: int = 15
    location_stamp_color: str = "#FF9100"
    location_stamp_border_color: str = "#000000"
    location_stamp_vertical: bool = False


__all__ = ["ProcessingSettings"]
