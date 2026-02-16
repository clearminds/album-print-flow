from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import platform
import random
import re
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from PIL import ExifTags, Image, ImageDraw, ImageEnhance, ImageFont
from PIL.ImageQt import ImageQt
from PySide6.QtCore import (
    QDateTime,
    QMarginsF,
    QObject,
    QRect,
    QRunnable,
    QSettings,
    QSizeF,
    Qt,
    QThreadPool,
    QTimer,
    Signal,
    qVersion,
)
from PySide6.QtGui import (
    QAction,
    QColor,
    QFont,
    QIcon,
    QImage,
    QPageLayout,
    QPageSize,
    QPainter,
    QPen,
    QPixmap,
)
from PySide6.QtPrintSupport import QPrinter, QPrinterInfo
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDateTimeEdit,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QSplashScreen,
    QSplitter,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from album_printer.ipp_backend import (
    IppBackendError,
    IppCapabilities,
    cancel_ipp_job,
    get_ipp_capabilities,
    print_jobs_via_ipp,
)
from album_printer.settings_store import (
    load_app_project_settings as load_project_settings_from_store,
)
from album_printer.settings_store import (
    save_app_project_settings as save_project_settings_to_store,
)

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"}
METADATA_FILENAME = ".album_printer.json"
LOG_FILENAME = "album_printer.log"
LOG_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR"]
LOG_LEVEL_RANK = {"DEBUG": 0, "INFO": 10, "WARNING": 20, "ERROR": 30}
CROP_RATIOS = ["2:3", "3:4", "4:5", "1:1", "16:9"]
CROP_RATIO_LABELS = {
    "2:3": "2:3 (10x15 cm / 4x6 in, 13x18 cm / 5x7 in, 20x30 cm / 8x12 in)",
    "3:4": "3:4 (15x20 cm / 6x8 in)",
    "4:5": "4:5 (20x25 cm / 8x10 in)",
    "1:1": "1:1 (10x10 cm / 4x4 in)",
    "16:9": "16:9 (10x18 cm / 4x7 in, panoramic)",
}
PAPER_LABELS = {
    "10x15 cm": "10x15 cm (4x6 in)",
    "A3": "A3 (11.7x16.5 in)",
    "A3+": "A3+ (13x19 in)",
    "A4": "A4 (8.3x11.7 in)",
    "A4+": "A4+ (8.3x13 in)",
}
SORT_MODES = [
    "Filename (A-Z)",
    "Filename (Z-A)",
    "EXIF Date (Oldest first)",
    "EXIF Date (Newest first)",
    "Filename Date (Oldest first)",
    "Filename Date (Newest first)",
    "File Modified (Oldest first)",
    "File Modified (Newest first)",
]
STAMP_FONTS = {
    "Photo Stamp Mono": "fonts/PhotoStampMono.ttf",
    "Classic Mono": "fonts/ClassicMono.ttf",
}
CUPS_KEYS = ["media", "media-type", "print-quality"]
CUPS_ALIASES = {
    "media": ["media", "pagesize", "page-size", "page_size"],
    "media-type": ["media-type", "mediatype", "media_type"],
    "print-quality": [
        "print-quality",
        "printquality",
        "quality",
        "cupsprintquality",
        "resolution",
    ],
}

TABLE_COL_THUMB = 0
TABLE_COL_STATE = 1
TABLE_COL_PRINT = 2
TABLE_COL_FILE = 3
TABLE_COL_DATE_USED = 4
TABLE_COL_DATE_SOURCE = 5
TABLE_COL_OVERRIDE = 6
THUMBNAIL_SIZE = 40
THUMBNAIL_MAX_INFLIGHT = 4
REFRAME_HANDLE_SIZE = 14
STAMP_SCALE_MIN_PERCENT = 20
STAMP_SCALE_MAX_PERCENT = 180
STAMP_OFFSET_MIN_PX = 0
STAMP_OFFSET_MAX_PX = 240
SETTINGS_ORG = "album-print-flow"
SETTINGS_APP = "AlbumPrintFlow"
DEFAULT_STAMP_COLOR = "#FF9100"
DEFAULT_STAMP_BORDER_COLOR = "#FFFFFF"
PRINT_BACKENDS = ["Auto", "CUPS", "Qt", "IPP"]
APP_DISPLAY_NAME = "Album Print Flow"
APP_COPYRIGHT = "© clearminds, 2026"
APP_TAGLINE = "Photo crop, stamp, and print workflow"

MEDIA_NAME_MAP = {
    "iso_a3_297x420mm": "A3",
    "iso_a4_210x297mm": "A4",
    "iso_a5_148x210mm": "A5",
    "na_letter_8.5x11in": "US Letter",
    "na_legal_8.5x14in": "US Legal",
    "4x6": "4x6 in (10x15 cm)",
    "5x7": "5x7 in",
    "8x10": "8x10 in",
    "10x15cm": "10x15 cm",
    "13x18cm": "13x18 cm",
    "a3": "A3",
    "a4": "A4",
}

MEDIA_TYPE_MAP = {
    "stationery": "Plain Paper",
    "plain": "Plain Paper",
    "photographicglossy": "Photo Glossy",
    "photographicsemigloss": "Photo Semi-Gloss",
    "photographicmatte": "Photo Matte",
    "matte": "Matte",
    "glossy": "Glossy",
    "envelope": "Envelope",
}

QUALITY_MAP = {
    "3": "Draft",
    "4": "Normal",
    "5": "High",
    "draft": "Draft",
    "normal": "Normal",
    "high": "High",
}

DATETIME_ORIGINAL_TAG = next(
    tag for tag, name in ExifTags.TAGS.items() if name == "DateTimeOriginal"
)
DATETIME_DIGITIZED_TAG = next(
    tag for tag, name in ExifTags.TAGS.items() if name == "DateTimeDigitized"
)
DATETIME_TAG = next(tag for tag, name in ExifTags.TAGS.items() if name == "DateTime")
GPS_INFO_TAG = next(
    (tag for tag, name in ExifTags.TAGS.items() if name == "GPSInfo"), None
)


@dataclass
class ProcessingSettings:
    orientation: str = "Landscape"
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
    stamp_color: str = DEFAULT_STAMP_COLOR
    stamp_border_color: str = DEFAULT_STAMP_BORDER_COLOR
    stamp_vertical: bool = False
    datetime_override: datetime | None = None


class PreviewLabel(QLabel):
    drag_started = Signal(int, int)
    dragged = Signal(int, int, int, int)
    drag_released = Signal(int, int)

    def __init__(self, text: str = "", parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self._drag_enabled = False
        self._last_pos = None
        self._overlay_enabled = False
        self._overlay_rect: QRect | None = None

    def set_drag_enabled(self, enabled: bool) -> None:
        self._drag_enabled = enabled
        self._last_pos = None
        self.setCursor(
            Qt.CursorShape.OpenHandCursor if enabled else Qt.CursorShape.ArrowCursor
        )

    def set_overlay_enabled(self, enabled: bool) -> None:
        self._overlay_enabled = enabled
        self.update()

    def set_overlay_rect(self, rect: tuple[int, int, int, int] | None) -> None:
        if rect is None:
            self._overlay_rect = None
        else:
            x, y, width, height = rect
            self._overlay_rect = QRect(
                int(x), int(y), max(0, int(width)), max(0, int(height))
            )
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        super().paintEvent(event)
        if not self._overlay_enabled:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        full = self.rect()
        overlay = (
            self._overlay_rect.intersected(full) if self._overlay_rect else QRect()
        )

        mask_color = QColor(0, 0, 0, 120)
        if not overlay.isValid() or overlay.width() <= 0 or overlay.height() <= 0:
            painter.fillRect(full, mask_color)
            return

        if overlay.top() > full.top():
            painter.fillRect(
                QRect(
                    full.left(), full.top(), full.width(), overlay.top() - full.top()
                ),
                mask_color,
            )
        bottom_start = overlay.bottom() + 1
        if bottom_start <= full.bottom():
            painter.fillRect(
                QRect(
                    full.left(),
                    bottom_start,
                    full.width(),
                    full.bottom() - bottom_start + 1,
                ),
                mask_color,
            )
        if overlay.left() > full.left():
            painter.fillRect(
                QRect(
                    full.left(),
                    overlay.top(),
                    overlay.left() - full.left(),
                    overlay.height(),
                ),
                mask_color,
            )
        right_start = overlay.right() + 1
        if right_start <= full.right():
            painter.fillRect(
                QRect(
                    right_start,
                    overlay.top(),
                    full.right() - right_start + 1,
                    overlay.height(),
                ),
                mask_color,
            )

        pen = QPen(QColor("#FF9100"))
        pen.setWidth(2)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(overlay)

        handle_half = REFRAME_HANDLE_SIZE // 2
        handle_color = QColor("#FF9100")
        corners = [
            overlay.topLeft(),
            overlay.topRight(),
            overlay.bottomLeft(),
            overlay.bottomRight(),
        ]
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(handle_color)
        for point in corners:
            painter.drawRect(
                point.x() - handle_half,
                point.y() - handle_half,
                REFRAME_HANDLE_SIZE,
                REFRAME_HANDLE_SIZE,
            )

    def _resize_corner_at(self, pos) -> str | None:
        if not self._overlay_enabled or self._overlay_rect is None:
            return None
        overlay = self._overlay_rect
        if not overlay.isValid() or overlay.width() <= 0 or overlay.height() <= 0:
            return None

        x = pos.x()
        y = pos.y()
        threshold = REFRAME_HANDLE_SIZE
        corners = {
            "top_left": overlay.topLeft(),
            "top_right": overlay.topRight(),
            "bottom_left": overlay.bottomLeft(),
            "bottom_right": overlay.bottomRight(),
        }
        for name, point in corners.items():
            if abs(x - point.x()) <= threshold and abs(y - point.y()) <= threshold:
                return name
        return None

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if self._drag_enabled and event.button() == Qt.MouseButton.LeftButton:
            self._last_pos = event.position().toPoint()
            self.drag_started.emit(self._last_pos.x(), self._last_pos.y())
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        pos = event.position().toPoint()
        if self._drag_enabled and self._last_pos is not None:
            delta = pos - self._last_pos
            self._last_pos = pos
            self.dragged.emit(delta.x(), delta.y(), pos.x(), pos.y())
        elif self._drag_enabled:
            corner = self._resize_corner_at(pos)
            if corner in {"top_left", "bottom_right"}:
                self.setCursor(Qt.CursorShape.SizeFDiagCursor)
            elif corner in {"top_right", "bottom_left"}:
                self.setCursor(Qt.CursorShape.SizeBDiagCursor)
            else:
                self.setCursor(Qt.CursorShape.OpenHandCursor)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if self._drag_enabled and event.button() == Qt.MouseButton.LeftButton:
            self._last_pos = None
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            pos = event.position().toPoint()
            self.drag_released.emit(pos.x(), pos.y())
        super().mouseReleaseEvent(event)


class ThumbnailWorkerSignals(QObject):
    finished = Signal(object, int, object)


class ThumbnailWorker(QRunnable):
    def __init__(self, path: Path, generation: int) -> None:
        super().__init__()
        self.path = path
        self.generation = generation
        self.signals = ThumbnailWorkerSignals()

    def run(self) -> None:
        image: QImage | None = None
        try:
            with Image.open(self.path) as source:
                thumb = source.convert("RGB")
                thumb.thumbnail(
                    (THUMBNAIL_SIZE, THUMBNAIL_SIZE), Image.Resampling.LANCZOS
                )
                image = QImage(ImageQt(thumb))
        except OSError:
            image = None

        self.signals.finished.emit(self.path, self.generation, image)


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


def datetime_for_image(path: Path) -> datetime:
    try:
        with Image.open(path) as image:
            exif = image.getexif() or {}
            for tag in (DATETIME_ORIGINAL_TAG, DATETIME_DIGITIZED_TAG, DATETIME_TAG):
                value = exif.get(tag)
                if not value:
                    continue
                try:
                    return datetime.strptime(str(value), "%Y:%m:%d %H:%M:%S")
                except ValueError:
                    continue
    except OSError:
        pass

    from_filename = parse_datetime_from_filename(path.name)
    if from_filename:
        return from_filename

    return datetime.fromtimestamp(path.stat().st_mtime)


def exif_datetime_for_image(path: Path) -> datetime | None:
    try:
        with Image.open(path) as image:
            exif = image.getexif() or {}
            for tag in (DATETIME_ORIGINAL_TAG, DATETIME_DIGITIZED_TAG, DATETIME_TAG):
                value = exif.get(tag)
                if not value:
                    continue
                try:
                    return datetime.strptime(str(value), "%Y:%m:%d %H:%M:%S")
                except ValueError:
                    continue
    except OSError:
        return None
    return None


def _convert_gps_coordinate(coord: tuple, ref: str) -> float | None:
    """Convert GPS coordinate from degrees/minutes/seconds to decimal.

    Args:
        coord: Tuple of (degrees, minutes, seconds) as rational numbers
        ref: Reference direction (N, S, E, W)

    Returns:
        Decimal coordinate or None if invalid
    """
    try:
        if not coord or len(coord) < 2:
            return None

        # Handle rational numbers (tuples of numerator/denominator)
        def to_float(val):
            if isinstance(val, tuple) and len(val) == 2:
                return float(val[0]) / float(val[1]) if val[1] != 0 else 0
            return float(val)

        degrees = to_float(coord[0])
        minutes = to_float(coord[1])
        seconds = to_float(coord[2]) if len(coord) > 2 else 0

        decimal = degrees + (minutes / 60.0) + (seconds / 3600.0)

        # Apply negative for South and West
        if ref in ("S", "W"):
            decimal = -decimal

        return decimal
    except (ValueError, TypeError, ZeroDivisionError):
        return None


def exif_gps_for_image(path: Path) -> tuple[float, float] | None:
    """Extract GPS coordinates from image EXIF data.

    Args:
        path: Path to image file

    Returns:
        Tuple of (latitude, longitude) in decimal degrees, or None if not available
    """
    if GPS_INFO_TAG is None:
        return None

    try:
        with Image.open(path) as image:
            exif = image.getexif()
            if not exif:
                return None

            gps_info = exif.get(GPS_INFO_TAG)
            if not gps_info:
                return None

            # GPS tags: 1=LatRef, 2=Lat, 3=LonRef, 4=Lon
            lat_ref = gps_info.get(1)
            lat = gps_info.get(2)
            lon_ref = gps_info.get(3)
            lon = gps_info.get(4)

            if not all([lat_ref, lat, lon_ref, lon]):
                return None

            latitude = _convert_gps_coordinate(lat, lat_ref)
            longitude = _convert_gps_coordinate(lon, lon_ref)

            if latitude is None or longitude is None:
                return None

            # Validate reasonable ranges
            if not (-90 <= latitude <= 90) or not (-180 <= longitude <= 180):
                return None

            return (latitude, longitude)
    except (OSError, KeyError, AttributeError):
        return None
    return None


def format_gps_location(lat: float, lon: float) -> str:
    """Format GPS coordinates for display.

    Args:
        lat: Latitude in decimal degrees
        lon: Longitude in decimal degrees

    Returns:
        Formatted location string
    """
    return f"{lat:.6f}, {lon:.6f}"


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


def stamp_text(path: Path, settings: ProcessingSettings) -> str:
    if settings.stamp_mode == "None":
        return ""

    dt = settings.datetime_override or datetime_for_image(path)
    if settings.stamp_mode == "Date":
        return dt.strftime("%Y-%m-%d")
    if settings.clock_mode == "12h":
        return dt.strftime("%Y-%m-%d %I:%M %p")
    return dt.strftime("%Y-%m-%d %H:%M")


def load_stamp_font(
    font_name: str, font_size: int
) -> ImageFont.ImageFont | ImageFont.FreeTypeFont:
    base = Path(__file__).resolve().parent
    relative = STAMP_FONTS.get(font_name, STAMP_FONTS["Photo Stamp Mono"])
    bundled = base / relative
    if bundled.exists():
        try:
            return ImageFont.truetype(str(bundled), font_size)
        except OSError:
            pass

    for fallback in ("DejaVuSansMono.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(fallback, font_size)
        except OSError:
            continue

    return ImageFont.load_default()


def apply_stamp(
    image: Image.Image, text: str, settings: ProcessingSettings
) -> Image.Image:
    if not text:
        return image

    if image.mode != "RGBA":
        image = image.convert("RGBA")

    draw = ImageDraw.Draw(image)

    if settings.orientation == "Portrait":
        base_size = max(26, int(image.width * 0.065))
    else:
        base_size = max(22, int(image.width * 0.048))

    margin_x = int(round(image.width * max(0, settings.stamp_offset_x_px) / 1000.0))
    margin_y = int(round(image.height * max(0, settings.stamp_offset_y_px) / 1000.0))

    font_size = int(base_size * (settings.stamp_scale_percent / 100.0))
    font_size = max(14, font_size)
    font = load_stamp_font(settings.stamp_font, font_size)

    stroke_width = max(2, int(font_size * 0.12))
    color = QColor(settings.stamp_color)
    if not color.isValid():
        color = QColor(DEFAULT_STAMP_COLOR)
    border_color = QColor(settings.stamp_border_color)
    if not border_color.isValid():
        border_color = QColor(DEFAULT_STAMP_BORDER_COLOR)

    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
    text_width = right - left
    text_height = bottom - top

    text_layer = Image.new(
        "RGBA",
        (text_width + stroke_width * 2, text_height + stroke_width * 2),
        (0, 0, 0, 0),
    )
    text_draw = ImageDraw.Draw(text_layer)
    text_draw.text(
        (stroke_width - left, stroke_width - top),
        text,
        fill=(color.red(), color.green(), color.blue()),
        font=font,
        stroke_width=stroke_width,
        stroke_fill=(border_color.red(), border_color.green(), border_color.blue()),
    )

    if settings.stamp_vertical:
        text_layer = text_layer.rotate(90, expand=True)

    stamp_w, stamp_h = text_layer.size

    if "Top" in settings.corner:
        y = margin_y
    else:
        y = image.height - stamp_h - margin_y

    if "Left" in settings.corner:
        x = margin_x
    else:
        x = image.width - stamp_w - margin_x

    x = max(0, min(image.width - stamp_w, x))
    y = max(0, min(image.height - stamp_h, y))

    image.alpha_composite(text_layer, (x, y))
    return image.convert("RGB")


def render_image(path: Path, settings: ProcessingSettings) -> Image.Image:
    with Image.open(path) as source:
        image = source.convert("RGB")

    image = center_crop_to_ratio(
        image,
        settings.orientation,
        settings.crop_ratio,
        settings.crop_zoom_percent,
        settings.crop_offset_x_percent,
        settings.crop_offset_y_percent,
    )
    image = ImageEnhance.Brightness(image).enhance(settings.brightness_percent / 100.0)
    image = apply_stamp(image, stamp_text(path, settings), settings)
    return image


def render_preview_image(
    path: Path, settings: ProcessingSettings, max_dimension: int
) -> Image.Image:
    with Image.open(path) as source:
        image = source.convert("RGB")

    if max_dimension > 0:
        longest = max(image.width, image.height)
        if longest > max_dimension:
            scale = max_dimension / float(longest)
            resized = (
                max(1, int(round(image.width * scale))),
                max(1, int(round(image.height * scale))),
            )
            image = image.resize(resized, Image.Resampling.LANCZOS)

    image = center_crop_to_ratio(
        image,
        settings.orientation,
        settings.crop_ratio,
        settings.crop_zoom_percent,
        settings.crop_offset_x_percent,
        settings.crop_offset_y_percent,
    )
    image = ImageEnhance.Brightness(image).enhance(settings.brightness_percent / 100.0)
    image = apply_stamp(image, stamp_text(path, settings), settings)
    return image


def pretty_option_label(kind: str, raw_value: str) -> str:
    value = (raw_value or "").strip()
    if not value:
        return value

    key = value.lower()
    if kind == "media":
        translated = MEDIA_NAME_MAP.get(key)
    elif kind == "media-type":
        translated = MEDIA_TYPE_MAP.get(key)
    else:
        translated = QUALITY_MAP.get(key)

    if translated:
        return f"{translated} ({value})"

    fallback = value.replace("_", " ").replace("-", " ").strip()
    if fallback and fallback != value:
        fallback = " ".join(part.capitalize() for part in fallback.split())
        return f"{fallback} ({value})"
    return value


def media_size_mm_from_value(media: str) -> tuple[float, float] | None:
    value = (media or "").strip().lower()
    if not value:
        return None

    direct_sizes: dict[str, tuple[float, float]] = {
        "a3": (297.0, 420.0),
        "a4": (210.0, 297.0),
        "a5": (148.0, 210.0),
        "4x6": (101.6, 152.4),
        "5x7": (127.0, 177.8),
        "8x10": (203.2, 254.0),
        "10x15cm": (100.0, 150.0),
        "13x18cm": (130.0, 180.0),
    }
    known = direct_sizes.get(value)
    if known is not None:
        return known

    match = re.search(r"(\d+(?:\.\d+)?)x(\d+(?:\.\d+)?)(mm|cm|in)", value)
    if not match:
        return None

    width = float(match.group(1))
    height = float(match.group(2))
    unit = match.group(3)
    if unit == "mm":
        return width, height
    if unit == "cm":
        return width * 10.0, height * 10.0
    return width * 25.4, height * 25.4


def resolve_cups_media_value(
    selected_media: str,
    supported_media: list[str],
    borderless_enabled: bool,
) -> str:
    requested = (selected_media or "").strip()
    if not requested or not supported_media:
        return requested

    normalized = [(value, value.lower()) for value in supported_media if value]
    requested_lower = requested.lower()

    def find_exact(value: str) -> str | None:
        target = value.lower()
        for original, lower in normalized:
            if lower == target:
                return original
        return None

    exact = find_exact(requested)
    if borderless_enabled:
        if exact and "borderless" in exact.lower():
            return exact

        direct_candidates = (
            f"{requested}.Borderless",
            f"{requested}.borderless",
            f"{requested}Borderless",
            f"T{requested}",
        )
        for candidate in direct_candidates:
            found = find_exact(candidate)
            if found is not None:
                return found

        for original, lower in normalized:
            if requested_lower in lower and "borderless" in lower:
                return original
        return exact or requested

    if exact:
        return exact
    return requested


def is_explicit_borderless_media(media: str) -> bool:
    value = (media or "").strip().lower()
    if not value:
        return False
    return "borderless" in value


def parse_cups_options_output(
    output: str,
) -> tuple[dict[str, list[str]], dict[str, str]]:
    parsed: dict[str, list[str]] = {}
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if ":" not in line:
            continue
        left, right = line.split(":", maxsplit=1)
        key = left.split("/", maxsplit=1)[0].strip().lower()

        tokens = [t.lstrip("*") for t in right.strip().split() if t]
        cleaned: list[str] = []
        for token in tokens:
            if token in cleaned:
                continue
            if token.startswith("("):
                continue
            if re.search(r"[\/=]", token):
                continue
            cleaned.append(token)
        parsed[key] = cleaned

    result = {key: [] for key in CUPS_KEYS}
    resolved_keys = {
        "media": "media",
        "media-type": "media-type",
        "print-quality": "print-quality",
    }
    for canonical, aliases in CUPS_ALIASES.items():
        merged: list[str] = []
        resolved = canonical
        for alias in aliases:
            values = parsed.get(alias, [])
            if values and resolved == canonical:
                resolved = alias
            for option in values:
                if option not in merged:
                    merged.append(option)
        result[canonical] = merged
        resolved_keys[canonical] = resolved
    return result, resolved_keys


def parse_cups_request_id(output: str) -> str:
    text = (output or "").strip()
    if not text:
        return ""
    match = re.search(r"request\s+id\s+is\s+([^\s]+)", text, flags=re.IGNORECASE)
    if not match:
        return ""
    return match.group(1).strip()


def query_cups_job_status_text(request_id: str) -> str:
    job = (request_id or "").strip()
    if not job:
        return ""

    try:
        result = subprocess.run(
            ["lpstat", "-W", "all", "-l", "-o"],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return ""

    output = (result.stdout or "").strip()
    if not output:
        error_text = (result.stderr or "").strip()
        return error_text

    lines = output.splitlines()
    header_index = -1
    for index, raw in enumerate(lines):
        line = raw.strip()
        if line.startswith(job + " ") or line == job:
            header_index = index
            break

    if header_index < 0:
        return ""

    status_value = ""
    fallback_value = ""
    for raw in lines[header_index + 1 :]:
        if raw and not raw.startswith(" ") and not raw.startswith("\t"):
            break
        line = raw.strip()
        if not line:
            continue
        lowered = line.lower()
        if lowered.startswith("status:"):
            status_text = line.split(":", maxsplit=1)[1].strip()
            if status_text:
                status_value = f"Status: {status_text}"
                break
            continue
        if not fallback_value and (
            lowered.startswith("alerts:")
            or lowered.startswith("printer-state-reasons:")
            or lowered.startswith("queued for")
            or lowered.startswith("processing")
            or lowered.startswith("completed")
        ):
            fallback_value = line

    if status_value:
        return status_value
    if fallback_value:
        return fallback_value
    return lines[header_index].strip()


def create_borderless_calibration_image(
    width_px: int,
    height_px: int,
    scale_percent: int,
    test_label: str,
) -> Image.Image:
    width = max(600, int(width_px))
    height = max(600, int(height_px))
    image = Image.new("RGB", (width, height), "#F8FAFC")
    draw = ImageDraw.Draw(image)

    block = max(20, min(width, height) // 24)
    color_a = (240, 244, 248)
    color_b = (222, 230, 238)
    for top in range(0, height, block):
        row = top // block
        for left in range(0, width, block):
            col = left // block
            color = color_a if (row + col) % 2 == 0 else color_b
            draw.rectangle((left, top, left + block - 1, top + block - 1), fill=color)

    border_outer = max(12, min(width, height) // 40)
    border_inner = max(4, border_outer // 3)
    draw.rectangle((0, 0, width - 1, height - 1), outline="#B91C1C", width=border_outer)
    inset = border_outer + border_inner
    draw.rectangle(
        (inset, inset, width - inset - 1, height - inset - 1),
        outline="#111827",
        width=border_inner,
    )

    cx = width // 2
    cy = height // 2
    draw.line((cx, inset, cx, height - inset - 1), fill="#2563EB", width=2)
    draw.line((inset, cy, width - inset - 1, cy), fill="#2563EB", width=2)

    guide_step = max(60, min(width, height) // 12)
    for offset in range(guide_step, min(cx, cy), guide_step):
        draw.rectangle(
            (cx - offset, cy - offset, cx + offset, cy + offset),
            outline="#0F766E",
            width=2,
        )

    marker_size = max(46, min(width, height) // 10)
    corners = [
        (inset, inset),
        (width - inset - marker_size, inset),
        (inset, height - inset - marker_size),
        (width - inset - marker_size, height - inset - marker_size),
    ]
    for left, top in corners:
        draw.rectangle(
            (left, top, left + marker_size, top + marker_size),
            outline="#7C2D12",
            width=max(3, border_inner),
        )

    corner_font_size = max(22, int(min(width, height) * 0.042))
    info_font_size = max(24, int(min(width, height) * 0.046))
    try:
        corner_font = ImageFont.truetype("DejaVuSans-Bold.ttf", corner_font_size)
        info_font = ImageFont.truetype("DejaVuSans-Bold.ttf", info_font_size)
    except OSError:
        corner_font = ImageFont.load_default()
        info_font = ImageFont.load_default()

    draw.text((inset + 12, inset + 8), "TOP LEFT", fill="#111827", font=corner_font)
    draw.text(
        (width - inset - max(180, int(width * 0.18)), inset + 8),
        "TOP RIGHT",
        fill="#111827",
        font=corner_font,
    )
    draw.text(
        (inset + 12, height - inset - max(42, int(height * 0.05))),
        "BOTTOM LEFT",
        fill="#111827",
        font=corner_font,
    )
    draw.text(
        (
            width - inset - max(220, int(width * 0.22)),
            height - inset - max(42, int(height * 0.05)),
        ),
        "BOTTOM RIGHT",
        fill="#111827",
        font=corner_font,
    )

    title = f"BORDERLESS CALIBRATION - SCALE {int(scale_percent)}%"
    subtitle = "Goal: all red/black border lines should remain visible"
    draw.text(
        (inset + 12, cy - max(56, int(height * 0.07))),
        title,
        fill="#0F172A",
        font=info_font,
    )
    draw.text(
        (inset + 12, cy - max(20, int(height * 0.02))),
        subtitle,
        fill="#334155",
        font=info_font,
    )

    marker_w = max(260, int(width * 0.34))
    marker_h = max(72, int(height * 0.12))
    marker_left = cx - marker_w // 2
    marker_top = cy - marker_h // 2 + 48
    draw.rectangle(
        (marker_left, marker_top, marker_left + marker_w, marker_top + marker_h),
        fill="#FFFFFF",
        outline="#0F172A",
        width=max(3, border_inner),
    )

    center_font_size = max(44, int(min(width, height) * 0.095))
    try:
        center_font = ImageFont.truetype("DejaVuSans-Bold.ttf", center_font_size)
    except OSError:
        center_font = ImageFont.load_default()

    center_text = f"TEST {test_label} · {int(scale_percent)}%"
    text_left, text_top, text_right, text_bottom = draw.textbbox(
        (0, 0), center_text, font=center_font
    )
    text_w = text_right - text_left
    text_h = text_bottom - text_top
    text_x = marker_left + (marker_w - text_w) // 2 - text_left
    text_y = marker_top + (marker_h - text_h) // 2 - text_top
    draw.text(
        (text_x, text_y),
        center_text,
        fill="#111827",
        font=center_font,
        stroke_width=2,
        stroke_fill="#FFFFFF",
    )
    return image


def apply_borderless_content_scale(
    image: Image.Image,
    scale_percent: int,
) -> Image.Image:
    scale = max(85, min(110, int(scale_percent)))
    if scale == 100:
        return image

    width = max(1, image.width)
    height = max(1, image.height)
    target_w = max(1, int(round(width * (scale / 100.0))))
    target_h = max(1, int(round(height * (scale / 100.0))))

    resized = image.resize((target_w, target_h), Image.Resampling.LANCZOS)
    if scale < 100:
        canvas = Image.new("RGB", (width, height), "#FFFFFF")
        x = (width - target_w) // 2
        y = (height - target_h) // 2
        canvas.paste(resized, (x, y))
        return canvas

    left = max(0, (target_w - width) // 2)
    top = max(0, (target_h - height) // 2)
    return resized.crop((left, top, left + width, top + height))


def parse_ipp_job_id(value: str) -> int | None:
    text = (value or "").strip()
    if not text:
        return None

    if text.isdigit():
        return int(text)

    match = re.search(r"(\d+)$", text)
    if not match:
        return None
    return int(match.group(1))


def is_debugger_attached() -> bool:
    gettrace = getattr(sys, "gettrace", None)
    if not callable(gettrace):
        return False
    try:
        return gettrace() is not None
    except Exception:
        return False


def preload_startup_cache(
    splash: QSplashScreen,
) -> dict[str, object]:
    preload_started_at = time.perf_counter()
    cache: dict[str, object] = {
        "printers": [],
        "cups_capabilities": {},
        "ipp_capabilities": {},
        "startup_debug_lines": [],
    }

    def show_step(message: str) -> None:
        splash.showMessage(
            message,
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom,
            QColor("#D1D5DB"),
        )
        if not is_debugger_attached():
            QApplication.processEvents()

    settings = QSettings(SETTINGS_ORG, SETTINGS_APP)
    backend = str(settings.value("print/backend", "Auto")).strip()
    selected_printer = str(settings.value("print/printer", "")).strip()
    ipp_uri = str(settings.value("print/ipp_uri", "")).strip()
    startup_debug_lines: list[str] = [f"Startup preload backend={backend or 'Auto'}"]

    preload_printers = backend in {"Auto", "CUPS", "Qt"}
    preload_cups = backend in {"Auto", "CUPS"}
    preload_ipp = backend == "IPP"

    if preload_printers:
        printers_started_at = time.perf_counter()
        show_step("Loading printers…")
        printers = [
            printer.printerName() for printer in QPrinterInfo.availablePrinters()
        ]
        cache["printers"] = printers
        startup_debug_lines.append(
            f"Startup preload printers: {len(printers)} in "
            f"{(time.perf_counter() - printers_started_at) * 1000:.1f} ms"
        )

    cups_cache: dict[str, tuple[dict[str, list[str]], dict[str, str]]] = {}
    if (
        preload_cups
        and selected_printer
        and os.name == "posix"
        and shutil.which("lpoptions") is not None
    ):
        cups_started_at = time.perf_counter()
        show_step(f"Loading paper options for {selected_printer}…")
        try:
            result = subprocess.run(
                ["lpoptions", "-p", selected_printer, "-l"],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0:
                cups_cache[selected_printer] = parse_cups_options_output(result.stdout)
                startup_debug_lines.append(
                    f"Startup preload CUPS({selected_printer}): success in "
                    f"{(time.perf_counter() - cups_started_at) * 1000:.1f} ms"
                )
            else:
                startup_debug_lines.append(
                    f"Startup preload CUPS({selected_printer}): returncode "
                    f"{result.returncode} in "
                    f"{(time.perf_counter() - cups_started_at) * 1000:.1f} ms"
                )
        except OSError:
            startup_debug_lines.append(
                f"Startup preload CUPS({selected_printer}): unavailable"
            )
    cache["cups_capabilities"] = cups_cache

    ipp_cache: dict[str, IppCapabilities | None] = {}
    if preload_ipp and ipp_uri:
        ipp_started_at = time.perf_counter()
        show_step("Loading IPP capabilities…")
        try:
            caps = get_ipp_capabilities(ipp_uri)
            ipp_cache[ipp_uri] = caps
            startup_debug_lines.append(
                "Startup preload IPP: "
                f"media={len(caps.media)}, type={len(caps.media_type)}, "
                f"quality={len(caps.print_quality)} in "
                f"{(time.perf_counter() - ipp_started_at) * 1000:.1f} ms"
            )
        except IppBackendError:
            ipp_cache[ipp_uri] = None
            startup_debug_lines.append(
                f"Startup preload IPP: unavailable in "
                f"{(time.perf_counter() - ipp_started_at) * 1000:.1f} ms"
            )
    cache["ipp_capabilities"] = ipp_cache

    startup_debug_lines.append(
        "Startup preload total: "
        f"{(time.perf_counter() - preload_started_at) * 1000:.1f} ms"
    )
    cache["startup_debug_lines"] = startup_debug_lines

    show_step("Starting application…")
    return cache


def app_version() -> str:
    try:
        return importlib.metadata.version("album-print-flow")
    except importlib.metadata.PackageNotFoundError:
        return "0.1.0"


def app_runtime_line() -> str:
    return f"Python {platform.python_version()} • Qt {qVersion()}"


def app_branding_info() -> dict[str, str]:
    return {
        "name": APP_DISPLAY_NAME,
        "tagline": APP_TAGLINE,
        "version": app_version(),
        "version_line": f"Version {app_version()}",
        "copyright": APP_COPYRIGHT,
        "runtime": app_runtime_line(),
    }


def app_about_text() -> str:
    info = app_branding_info()
    return (
        f"{info['name']}\n"
        f"{info['version_line']}\n\n"
        f"{info['tagline']}\n\n"
        f"{info['copyright']}\n"
        f"{info['runtime']}"
    )


def logo_path() -> Path | None:
    base = Path(__file__).resolve()
    candidates = [
        base.parents[2] / "assets" / "icons" / "png" / "app-icon-256.png",
        base.parents[1] / "assets" / "icons" / "png" / "app-icon-256.png",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def clearminds_head_path() -> Path | None:
    base = Path(__file__).resolve()
    candidates = [
        base.parents[2] / "assets" / "branding" / "clearminds-head.png",
        base.parents[1] / "assets" / "branding" / "clearminds-head.png",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def clearminds_wordmark_path() -> Path | None:
    base = Path(__file__).resolve()
    candidates = [
        base.parents[2] / "assets" / "branding" / "clearminds-wordmark.png",
        base.parents[1] / "assets" / "branding" / "clearminds-wordmark.png",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def load_logo_pixmap(size: int = 160) -> QPixmap | None:
    path = logo_path()
    if path is None:
        return None
    pixmap = QPixmap(str(path))
    if pixmap.isNull():
        return None
    return pixmap.scaled(
        size,
        size,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )


def app_window_icon() -> QIcon | None:
    path = logo_path()
    if path is None:
        return None
    icon = QIcon(str(path))
    if icon.isNull():
        return None
    return icon


def load_clearminds_head_pixmap(size: int = 64) -> QPixmap | None:
    path = clearminds_head_path()
    if path is None:
        return None
    pixmap = QPixmap(str(path))
    if pixmap.isNull():
        return None
    return pixmap.scaled(
        size,
        size,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )


def load_clearminds_wordmark_pixmap(width: int = 180) -> QPixmap | None:
    path = clearminds_wordmark_path()
    if path is None:
        return None
    pixmap = QPixmap(str(path))
    if pixmap.isNull():
        return None
    return pixmap.scaledToWidth(width, Qt.TransformationMode.SmoothTransformation)


def create_splash_screen() -> QSplashScreen:
    width, height = 720, 420
    canvas = QPixmap(width, height)
    canvas.fill(QColor("#0F172A"))

    painter = QPainter(canvas)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

    painter.fillRect(0, 0, width, height, QColor("#111827"))

    info = app_branding_info()

    logo = load_logo_pixmap(164)
    if logo is not None:
        logo_x = (width - logo.width()) // 2
        painter.drawPixmap(logo_x, 64, logo)

    painter.setPen(QColor("#E5E7EB"))
    painter.setFont(QFont("Sans Serif", 20, QFont.Weight.Bold))
    painter.drawText(0, 258, width, 40, Qt.AlignmentFlag.AlignCenter, info["name"])

    painter.setPen(QColor("#9CA3AF"))
    painter.setFont(QFont("Sans Serif", 11))
    painter.drawText(0, 290, width, 30, Qt.AlignmentFlag.AlignCenter, info["tagline"])

    painter.setPen(QColor("#F59E0B"))
    painter.setFont(QFont("Sans Serif", 11, QFont.Weight.DemiBold))
    painter.drawText(
        0,
        322,
        width,
        26,
        Qt.AlignmentFlag.AlignCenter,
        info["version_line"],
    )

    painter.setPen(QColor("#6B7280"))
    painter.setFont(QFont("Sans Serif", 10))
    painter.drawText(0, 374, width, 24, Qt.AlignmentFlag.AlignCenter, info["copyright"])

    cm_head = load_clearminds_head_pixmap(48)
    if cm_head is not None:
        painter.drawPixmap(width - cm_head.width() - 16, 16, cm_head)

    cm_wordmark = load_clearminds_wordmark_pixmap(120)
    if cm_wordmark is not None:
        painter.drawPixmap(16, height - cm_wordmark.height() - 12, cm_wordmark)
    painter.end()

    splash = QSplashScreen(canvas)
    splash.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
    splash.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
    return splash


class MainWindow(QMainWindow):
    def __init__(self, startup_cache: dict[str, object] | None = None) -> None:
        super().__init__()
        self.setWindowTitle(APP_DISPLAY_NAME)
        icon = app_window_icon()
        if icon is not None:
            self.setWindowIcon(icon)
        self.resize(1450, 920)

        startup_cache = startup_cache or {}
        printers_cache = startup_cache.get("printers", [])
        if isinstance(printers_cache, list):
            self.printer_names_cache = [str(name) for name in printers_cache]
        else:
            self.printer_names_cache = []

        cups_cache = startup_cache.get("cups_capabilities", {})
        if isinstance(cups_cache, dict):
            self.cups_capabilities_cache: dict[
                str, tuple[dict[str, list[str]], dict[str, str]]
            ] = {
                str(key): value
                for key, value in cups_cache.items()
                if isinstance(value, tuple) and len(value) == 2
            }
        else:
            self.cups_capabilities_cache = {}

        ipp_cache = startup_cache.get("ipp_capabilities", {})
        if isinstance(ipp_cache, dict):
            self.ipp_capabilities_cache: dict[str, IppCapabilities | None] = {
                str(key): value
                for key, value in ipp_cache.items()
                if isinstance(value, IppCapabilities) or value is None
            }
        else:
            self.ipp_capabilities_cache = {}

        startup_debug_cache = startup_cache.get("startup_debug_lines", [])
        if isinstance(startup_debug_cache, list):
            self.startup_debug_lines = [str(line) for line in startup_debug_cache]
        else:
            self.startup_debug_lines = []

        self.image_paths: list[Path] = []
        self.current_index = -1
        self.current_folder: Path | None = None
        self._restoring_settings = False
        self._updating_table = False
        self.thumbnail_cache: dict[Path, QPixmap] = {}
        self.thumbnail_pending_paths: list[Path] = []
        self.thumbnail_inflight_paths: set[Path] = set()
        self.thumbnail_generation = 0
        self.thumbnail_thread_pool = QThreadPool.globalInstance()
        self.thumbnail_placeholder = QPixmap(THUMBNAIL_SIZE, THUMBNAIL_SIZE)
        self.thumbnail_placeholder.fill(Qt.GlobalColor.darkGray)
        self.orientation_cache: dict[Path, str] = {}
        self.file_hash_cache: dict[Path, tuple[int, int, str]] = {}
        self.log_entries: list[tuple[str, str]] = []
        self.log_level_filter_value = "INFO"
        self.print_queue_items: list[dict[str, object]] = []
        self.print_queue_next_id = 1
        self.print_queue_paused = False
        self.print_queue_processing = False
        self.current_image_orientation = "Landscape"
        self.ui_settings = QSettings(SETTINGS_ORG, SETTINGS_APP)

        self.folder_metadata: dict[str, object] = self.default_metadata()

        self.crop_ratio_value = "2:3"
        self.stamp_mode_value = "None"
        self.clock_mode_value = "24h"
        self.corner_landscape_value = "Bottom Right"
        self.corner_portrait_value = "Bottom Right"
        self.paper_value = "10x15 cm"
        self.borderless_mode_value = "enabled"
        self.printer_value = ""
        self.sort_mode_value = "Filename (A-Z)"
        self.sort_column_value = TABLE_COL_FILE
        self.sort_descending_value = False
        self.sortable_columns = {
            TABLE_COL_FILE,
            TABLE_COL_DATE_USED,
            TABLE_COL_DATE_SOURCE,
            TABLE_COL_OVERRIDE,
        }
        self.stamp_font_value = "Photo Stamp Mono"
        self.stamp_scale_percent = 100
        self.stamp_offset_x_px = 15
        self.stamp_offset_y_px = 15
        self.stamp_color_value = DEFAULT_STAMP_COLOR
        self.stamp_border_color_value = DEFAULT_STAMP_BORDER_COLOR
        self.stamp_vertical_value = False
        self.print_backend_value = "Auto"
        self.ipp_uri_value = ""
        self.ipp_wait_for_completion_value = False
        self.cups_media_value = ""
        self.cups_media_type_value = ""
        self.cups_print_quality_value = ""
        self.borderless_content_scale_percent = 100
        self.cups_media_key = "media"
        self.cups_media_type_key = "media-type"
        self.cups_print_quality_key = "print-quality"
        self.load_app_print_settings()
        self.load_app_project_settings()

        self.image_table = QTableWidget(0, 7)
        self.image_table.setHorizontalHeaderLabels(
            ["", "State", "Print", "File", "Date Used", "Source", "Override"]
        )
        self.image_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.image_table.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection
        )
        self.image_table.verticalHeader().setVisible(False)
        header = self.image_table.horizontalHeader()
        header.setStretchLastSection(True)
        header.resizeSection(TABLE_COL_THUMB, 64)
        header.resizeSection(TABLE_COL_STATE, 80)
        header.resizeSection(TABLE_COL_PRINT, 95)
        header.resizeSection(TABLE_COL_FILE, 280)
        header.resizeSection(TABLE_COL_DATE_USED, 170)
        header.resizeSection(TABLE_COL_DATE_SOURCE, 90)
        header.resizeSection(TABLE_COL_OVERRIDE, 170)
        header.setSortIndicatorShown(True)
        header.sectionClicked.connect(self.on_image_table_header_clicked)
        self.update_table_sort_indicator()
        self.image_table.currentCellChanged.connect(
            self.on_image_table_selection_changed
        )
        self.image_table.cellChanged.connect(self.on_image_table_cell_changed)
        self.image_table.cellDoubleClicked.connect(
            self.on_image_table_cell_double_clicked
        )

        self.preview_label = PreviewLabel("Load a folder to begin")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setMinimumSize(1, 1)
        self.preview_label.setStyleSheet("background: #111; color: #ddd;")
        self.preview_label.drag_started.connect(self.on_preview_drag_started)
        self.preview_label.dragged.connect(self.on_preview_dragged)
        self.preview_label.drag_released.connect(self.on_preview_drag_released)
        self.preview_scaled_size = (1, 1)
        self.preview_source_size = (0, 0)
        self.preview_display_rect = (0, 0, 0, 0)
        self._reframe_drag_active = False
        self._reframe_interaction_mode = "pan"
        self._reframe_resize_corner: str | None = None
        self._reframe_pan_accum_x = 0.0
        self._reframe_pan_accum_y = 0.0
        self._reframe_zoom_accum = 0.0

        self.preview_container = QScrollArea()
        self.preview_container.setWidget(self.preview_label)
        self.preview_container.setWidgetResizable(True)

        load_button = QPushButton("Load Folder")
        load_button.clicked.connect(self.load_folder)

        self.refresh_folder_button = QPushButton("Refresh Folder")
        self.refresh_folder_button.clicked.connect(self.refresh_folder)

        prev_button = QPushButton("Previous")
        prev_button.clicked.connect(self.select_previous)

        next_button = QPushButton("Next")
        next_button.clicked.connect(self.select_next)

        self.folder_settings_button = QPushButton("Settings")
        self.folder_settings_button.clicked.connect(self.open_project_settings_dialog)

        print_settings_button = QPushButton("Printer Settings")
        print_settings_button.clicked.connect(self.open_print_settings_dialog)

        print_selected_button = QPushButton("Print Selected")
        print_selected_button.clicked.connect(self.print_selected)

        print_button = QPushButton("Print All")
        print_button.clicked.connect(self.print_all)

        self.crop_orientation_button = QPushButton("Crop: Landscape")
        self.crop_orientation_button.clicked.connect(self.toggle_crop_orientation)

        self.crop_reframe_button = QPushButton("Reframe Crop")
        self.crop_reframe_button.setCheckable(True)
        self.crop_reframe_button.toggled.connect(self.on_crop_reframe_toggled)
        self.crop_reset_button = QPushButton("Reset Crop")
        self.crop_reset_button.clicked.connect(self.reset_crop_for_selected)

        self.datetime_override_button = QPushButton("Set Date/Time")
        self.datetime_override_button.clicked.connect(
            self.set_datetime_override_for_selected
        )

        self.datetime_override_clear_button = QPushButton("Clear")
        self.datetime_override_clear_button.clicked.connect(
            self.clear_datetime_override_for_selected
        )

        self.datetime_override_label = QLabel("Auto")
        self.print_status_label = QLabel("Not Printed")
        self.print_status_label.setWordWrap(True)
        self.print_attempts_table = QTableWidget(0, 5)
        self.print_attempts_table.setHorizontalHeaderLabels(
            ["Time", "Status", "Backend", "Job", "Error"]
        )
        self.print_attempts_table.setSelectionMode(
            QAbstractItemView.SelectionMode.NoSelection
        )
        self.print_attempts_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.print_attempts_table.verticalHeader().setVisible(False)
        self.print_attempts_table.horizontalHeader().resizeSection(0, 128)
        self.print_attempts_table.horizontalHeader().resizeSection(1, 68)
        self.print_attempts_table.horizontalHeader().resizeSection(2, 72)
        self.print_attempts_table.horizontalHeader().resizeSection(3, 92)
        self.print_attempts_table.horizontalHeader().setStretchLastSection(True)
        self.print_attempts_table.setMinimumHeight(120)

        self.brightness_slider = QSlider(Qt.Orientation.Horizontal)
        self.brightness_slider.setRange(50, 150)
        self.brightness_slider.setValue(100)
        self.brightness_slider.valueChanged.connect(self.refresh_preview)
        self.brightness_slider.sliderReleased.connect(self.on_image_settings_changed)

        self.brightness_label = QLabel("100%")
        self.brightness_slider.valueChanged.connect(
            lambda value: self.brightness_label.setText(f"{value}%")
        )

        self.crop_zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.crop_zoom_slider.setRange(100, 300)
        self.crop_zoom_slider.setValue(100)
        self.crop_zoom_slider.valueChanged.connect(self.refresh_preview)
        self.crop_zoom_slider.sliderReleased.connect(self.on_image_settings_changed)
        self.crop_zoom_label = QLabel("100%")
        self.crop_zoom_slider.valueChanged.connect(
            lambda value: self.crop_zoom_label.setText(f"{value}%")
        )

        self.crop_x_slider = QSlider(Qt.Orientation.Horizontal)
        self.crop_x_slider.setRange(-100, 100)
        self.crop_x_slider.setValue(0)
        self.crop_x_slider.valueChanged.connect(self.refresh_preview)
        self.crop_x_slider.sliderReleased.connect(self.on_image_settings_changed)
        self.crop_x_label = QLabel("0")
        self.crop_x_slider.valueChanged.connect(
            lambda value: self.crop_x_label.setText(str(value))
        )

        self.crop_y_slider = QSlider(Qt.Orientation.Horizontal)
        self.crop_y_slider.setRange(-100, 100)
        self.crop_y_slider.setValue(0)
        self.crop_y_slider.valueChanged.connect(self.refresh_preview)
        self.crop_y_slider.sliderReleased.connect(self.on_image_settings_changed)
        self.crop_y_label = QLabel("0")
        self.crop_y_slider.valueChanged.connect(
            lambda value: self.crop_y_label.setText(str(value))
        )

        controls_layout = QFormLayout()
        controls_layout.addRow("Crop Mode", self.crop_orientation_button)
        reframe_row = QWidget()
        reframe_layout = QHBoxLayout(reframe_row)
        reframe_layout.setContentsMargins(0, 0, 0, 0)
        reframe_layout.addWidget(self.crop_reframe_button)
        reframe_layout.addWidget(self.crop_reset_button)
        controls_layout.addRow("Reframe", reframe_row)

        brightness_row = QWidget()
        brightness_layout = QHBoxLayout(brightness_row)
        brightness_layout.setContentsMargins(0, 0, 0, 0)
        brightness_layout.addWidget(self.brightness_slider)
        brightness_layout.addWidget(self.brightness_label)
        controls_layout.addRow("Brightness", brightness_row)

        zoom_row = QWidget()
        zoom_layout = QHBoxLayout(zoom_row)
        zoom_layout.setContentsMargins(0, 0, 0, 0)
        zoom_layout.addWidget(self.crop_zoom_slider)
        zoom_layout.addWidget(self.crop_zoom_label)
        controls_layout.addRow("Crop Zoom", zoom_row)

        x_row = QWidget()
        x_layout = QHBoxLayout(x_row)
        x_layout.setContentsMargins(0, 0, 0, 0)
        x_layout.addWidget(self.crop_x_slider)
        x_layout.addWidget(self.crop_x_label)
        controls_layout.addRow("Crop X", x_row)

        y_row = QWidget()
        y_layout = QHBoxLayout(y_row)
        y_layout.setContentsMargins(0, 0, 0, 0)
        y_layout.addWidget(self.crop_y_slider)
        y_layout.addWidget(self.crop_y_label)
        controls_layout.addRow("Crop Y", y_row)

        datetime_row = QWidget()
        datetime_layout = QHBoxLayout(datetime_row)
        datetime_layout.setContentsMargins(0, 0, 0, 0)
        datetime_layout.addWidget(self.datetime_override_button)
        datetime_layout.addWidget(self.datetime_override_clear_button)
        controls_layout.addRow("Date/Time", datetime_row)
        controls_layout.addRow("Override", self.datetime_override_label)
        controls_layout.addRow("Last Print", self.print_status_label)
        controls_layout.addRow("Print Attempts", self.print_attempts_table)

        self.controls_widget = QWidget()
        self.controls_widget.setLayout(controls_layout)
        self.controls_widget.setVisible(False)

        self.log_console = QTextEdit()
        self.log_console.setReadOnly(True)
        self.log_console.setPlaceholderText("Log output")
        self.log_console.setMinimumHeight(90)

        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(LOG_LEVELS)
        self.log_level_combo.setCurrentText(self.log_level_filter_value)
        self.log_level_combo.currentTextChanged.connect(self.on_log_level_changed)
        self.log_clear_button = QPushButton("Clear Logs")
        self.log_clear_button.clicked.connect(self.clear_log_console)

        self.print_queue_table = QTableWidget(0, 5)
        self.print_queue_table.setHorizontalHeaderLabels(
            ["ID", "Status", "Count", "Target", "Detail"]
        )
        self.print_queue_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.print_queue_table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.print_queue_table.verticalHeader().setVisible(False)
        queue_header = self.print_queue_table.horizontalHeader()
        queue_header.resizeSection(0, 56)
        queue_header.resizeSection(1, 90)
        queue_header.resizeSection(2, 56)
        queue_header.resizeSection(3, 160)
        queue_header.setStretchLastSection(True)

        self.queue_pause_button = QPushButton("Pause Queue")
        self.queue_pause_button.clicked.connect(self.pause_print_queue)
        self.queue_resume_button = QPushButton("Resume Queue")
        self.queue_resume_button.clicked.connect(self.resume_print_queue)
        self.queue_cancel_button = QPushButton("Cancel Selected")
        self.queue_cancel_button.clicked.connect(self.cancel_selected_queue_item)
        self.queue_remove_button = QPushButton("Remove Selected")
        self.queue_remove_button.clicked.connect(self.remove_selected_queue_item)
        self.queue_clear_button = QPushButton("Clear Finished")
        self.queue_clear_button.clicked.connect(self.clear_finished_queue_items)

        top_actions = QHBoxLayout()
        top_actions.addWidget(load_button)
        top_actions.addWidget(self.refresh_folder_button)
        top_actions.addWidget(prev_button)
        top_actions.addWidget(next_button)
        top_actions.addWidget(self.folder_settings_button)
        top_actions.addWidget(print_settings_button)
        top_actions.addStretch(1)
        top_actions.addWidget(print_selected_button)
        top_actions.addWidget(print_button)

        root = QVBoxLayout()
        root.addLayout(top_actions)

        self.list_preview_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.list_preview_splitter.setChildrenCollapsible(False)
        self.list_preview_splitter.addWidget(self.image_table)
        self.list_preview_splitter.addWidget(self.preview_container)
        self.list_preview_splitter.setStretchFactor(0, 3)
        self.list_preview_splitter.setStretchFactor(1, 6)

        body = QHBoxLayout()
        body.addWidget(self.list_preview_splitter, stretch=9)
        body.addWidget(self.controls_widget, stretch=2)
        main_content = QWidget()
        main_content.setLayout(body)

        log_header = QHBoxLayout()
        log_header.addWidget(QLabel("Log Level"))
        log_header.addWidget(self.log_level_combo)
        log_header.addStretch(1)
        log_header.addWidget(self.log_clear_button)

        log_panel = QWidget()
        log_layout = QVBoxLayout(log_panel)
        log_layout.setContentsMargins(0, 0, 0, 0)
        log_layout.addLayout(log_header)
        log_layout.addWidget(self.log_console)

        queue_header_row = QHBoxLayout()
        queue_header_row.addWidget(QLabel("Print Queue"))
        queue_header_row.addStretch(1)
        queue_header_row.addWidget(self.queue_pause_button)
        queue_header_row.addWidget(self.queue_resume_button)
        queue_header_row.addWidget(self.queue_cancel_button)
        queue_header_row.addWidget(self.queue_remove_button)
        queue_header_row.addWidget(self.queue_clear_button)

        queue_panel = QWidget()
        self.queue_panel = queue_panel
        queue_layout = QVBoxLayout(queue_panel)
        queue_layout.setContentsMargins(0, 0, 0, 0)
        queue_layout.addLayout(queue_header_row)
        queue_layout.addWidget(self.print_queue_table)
        queue_panel.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding
        )

        self.bottom_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.bottom_splitter.setChildrenCollapsible(False)
        self.bottom_splitter.addWidget(log_panel)
        self.bottom_splitter.addWidget(queue_panel)
        self.bottom_splitter.setStretchFactor(0, 3)
        self.bottom_splitter.setStretchFactor(1, 0)

        self.main_vertical_splitter = QSplitter(Qt.Orientation.Vertical)
        self.main_vertical_splitter.setChildrenCollapsible(False)
        self.main_vertical_splitter.addWidget(main_content)
        self.main_vertical_splitter.addWidget(self.bottom_splitter)
        self.main_vertical_splitter.setStretchFactor(0, 8)
        self.main_vertical_splitter.setStretchFactor(1, 2)

        root.addWidget(self.main_vertical_splitter)

        wrapper = QWidget()
        wrapper.setLayout(root)
        self.setCentralWidget(wrapper)
        self.setStatusBar(QStatusBar())

        self.restore_ui_state()

        self.setup_menu()
        self.update_folder_settings_availability()
        self.append_log("INFO", "Application started")
        for line in self.startup_debug_lines:
            self.append_log("DEBUG", line)
        self.refresh_print_queue_table()

    def update_queue_panel_max_width(self) -> None:
        if not hasattr(self, "queue_panel"):
            return

        header = self.print_queue_table.horizontalHeader()
        header.setStretchLastSection(False)
        self.print_queue_table.resizeColumnsToContents()
        detail_col = 4
        detail_width = self.print_queue_table.columnWidth(detail_col)
        self.print_queue_table.setColumnWidth(detail_col, min(detail_width, 340))
        header.setStretchLastSection(True)

        table_width = (
            self.print_queue_table.verticalHeader().width()
            + self.print_queue_table.frameWidth() * 2
            + sum(
                self.print_queue_table.columnWidth(index)
                for index in range(self.print_queue_table.columnCount())
            )
        )
        panel_width = max(420, table_width + 26)
        self.queue_panel.setMaximumWidth(panel_width)

    def restore_ui_state(self) -> None:
        geometry = self.ui_settings.value("ui/geometry")
        if geometry is not None:
            self.restoreGeometry(geometry)

        saved_log_level = (
            str(
                self.ui_settings.value(
                    "ui/log_level_filter", self.log_level_filter_value
                )
            )
            .strip()
            .upper()
        )
        if saved_log_level not in LOG_LEVEL_RANK:
            saved_log_level = "INFO"
        self.log_level_combo.setCurrentText(saved_log_level)

        raw_sizes = self.ui_settings.value("ui/list_preview_sizes")
        sizes: list[int] = []
        if isinstance(raw_sizes, list):
            for value in raw_sizes:
                try:
                    parsed = int(value)
                except (TypeError, ValueError):
                    continue
                if parsed > 0:
                    sizes.append(parsed)
        if len(sizes) == 2:
            self.list_preview_splitter.setSizes(sizes)

        raw_vertical_sizes = self.ui_settings.value("ui/main_vertical_sizes")
        vertical_sizes: list[int] = []
        if isinstance(raw_vertical_sizes, list):
            for value in raw_vertical_sizes:
                try:
                    parsed = int(value)
                except (TypeError, ValueError):
                    continue
                if parsed > 0:
                    vertical_sizes.append(parsed)
        if len(vertical_sizes) == 2:
            self.main_vertical_splitter.setSizes(vertical_sizes)

        raw_bottom_sizes = self.ui_settings.value("ui/bottom_splitter_sizes")
        bottom_sizes: list[int] = []
        if isinstance(raw_bottom_sizes, list):
            for value in raw_bottom_sizes:
                try:
                    parsed = int(value)
                except (TypeError, ValueError):
                    continue
                if parsed > 0:
                    bottom_sizes.append(parsed)
        if len(bottom_sizes) == 2:
            self.bottom_splitter.setSizes(bottom_sizes)
        else:
            fallback_bottom_sizes = self.bottom_splitter.sizes()
            if len(fallback_bottom_sizes) == 2 and all(
                size > 0 for size in fallback_bottom_sizes
            ):
                self.ui_settings.setValue(
                    "ui/bottom_splitter_sizes", fallback_bottom_sizes
                )

    def save_ui_state(self) -> None:
        self.ui_settings.setValue("ui/geometry", self.saveGeometry())
        self.ui_settings.setValue("ui/log_level_filter", self.log_level_filter_value)
        self.ui_settings.setValue(
            "ui/list_preview_sizes", self.list_preview_splitter.sizes()
        )
        self.ui_settings.setValue(
            "ui/main_vertical_sizes", self.main_vertical_splitter.sizes()
        )
        self.ui_settings.setValue(
            "ui/bottom_splitter_sizes", self.bottom_splitter.sizes()
        )
        self.ui_settings.sync()

    def closeEvent(self, event) -> None:  # noqa: N802
        self.save_app_project_settings()
        self.save_app_print_settings()
        self.save_ui_state()
        super().closeEvent(event)

    @staticmethod
    def _as_bool(value: object, default: bool) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            return value != 0
        if isinstance(value, str):
            text = value.strip().lower()
            if text in {"1", "true", "yes", "on"}:
                return True
            if text in {"0", "false", "no", "off", ""}:
                return False
        return default

    @staticmethod
    def _as_int(value: object, default: int) -> int:
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            try:
                return int(value.strip())
            except ValueError:
                return default
        return default

    def load_app_print_settings(self) -> None:
        backend = str(
            self.ui_settings.value("print/backend", self.print_backend_value)
        ).strip()
        if backend in PRINT_BACKENDS:
            self.print_backend_value = backend

        ipp_uri = str(self.ui_settings.value("print/ipp_uri", self.ipp_uri_value))
        self.ipp_uri_value = ipp_uri.strip()
        self.ipp_wait_for_completion_value = self._as_bool(
            self.ui_settings.value(
                "print/ipp_wait_for_completion", self.ipp_wait_for_completion_value
            ),
            self.ipp_wait_for_completion_value,
        )

        self.printer_value = str(
            self.ui_settings.value("print/printer", self.printer_value)
        ).strip()
        self.cups_media_value = str(
            self.ui_settings.value("print/cups_media", self.cups_media_value)
        ).strip()
        self.cups_media_type_value = str(
            self.ui_settings.value("print/cups_media_type", self.cups_media_type_value)
        ).strip()
        self.cups_print_quality_value = str(
            self.ui_settings.value(
                "print/cups_print_quality", self.cups_print_quality_value
            )
        ).strip()
        self.cups_media_key = (
            str(
                self.ui_settings.value("print/cups_media_key", self.cups_media_key)
            ).strip()
            or "media"
        )
        self.cups_media_type_key = (
            str(
                self.ui_settings.value(
                    "print/cups_media_type_key", self.cups_media_type_key
                )
            ).strip()
            or "media-type"
        )
        self.cups_print_quality_key = (
            str(
                self.ui_settings.value(
                    "print/cups_print_quality_key", self.cups_print_quality_key
                )
            ).strip()
            or "print-quality"
        )
        paper_value = str(
            self.ui_settings.value("print/paper", self.paper_value)
        ).strip()
        if paper_value in PAPER_LABELS:
            self.paper_value = paper_value
        borderless_mode = str(
            self.ui_settings.value("print/borderless_mode", self.borderless_mode_value)
        ).strip()
        if borderless_mode in {"default", "enabled", "disabled"}:
            self.borderless_mode_value = borderless_mode
        else:
            legacy_borderless = self._as_bool(
                self.ui_settings.value("print/borderless", True),
                True,
            )
            self.borderless_mode_value = "enabled" if legacy_borderless else "disabled"

        raw_borderless_scale = self._as_int(
            self.ui_settings.value(
                "print/borderless_content_scale_percent",
                self.borderless_content_scale_percent,
            ),
            self.borderless_content_scale_percent,
        )
        self.borderless_content_scale_percent = max(85, min(110, raw_borderless_scale))

    def save_app_print_settings(self) -> None:
        self.ui_settings.setValue("print/backend", self.print_backend_value)
        self.ui_settings.setValue("print/ipp_uri", self.ipp_uri_value)
        self.ui_settings.setValue(
            "print/ipp_wait_for_completion", self.ipp_wait_for_completion_value
        )
        self.ui_settings.setValue("print/printer", self.printer_value)
        self.ui_settings.setValue("print/cups_media", self.cups_media_value)
        self.ui_settings.setValue("print/cups_media_type", self.cups_media_type_value)
        self.ui_settings.setValue(
            "print/cups_print_quality", self.cups_print_quality_value
        )
        self.ui_settings.setValue("print/cups_media_key", self.cups_media_key)
        self.ui_settings.setValue("print/cups_media_type_key", self.cups_media_type_key)
        self.ui_settings.setValue(
            "print/cups_print_quality_key", self.cups_print_quality_key
        )
        self.ui_settings.setValue("print/paper", self.paper_value)
        self.ui_settings.setValue("print/borderless_mode", self.borderless_mode_value)
        self.ui_settings.setValue(
            "print/borderless", self.borderless_mode_value == "enabled"
        )
        self.ui_settings.setValue(
            "print/borderless_content_scale_percent",
            self.borderless_content_scale_percent,
        )
        self.ui_settings.sync()

    def load_app_project_settings(self) -> None:
        defaults: dict[str, object] = {
            "crop_ratio": self.crop_ratio_value,
            "stamp_mode": self.stamp_mode_value,
            "clock_mode": self.clock_mode_value,
            "corner_landscape": self.corner_landscape_value,
            "corner_portrait": self.corner_portrait_value,
            "sort_mode": self.sort_mode_value,
            "sort_column": self.sort_column_value,
            "sort_descending": self.sort_descending_value,
            "stamp_font": self.stamp_font_value,
            "stamp_scale_percent": self.stamp_scale_percent,
            "stamp_offset_x_px": self.stamp_offset_x_px,
            "stamp_offset_y_px": self.stamp_offset_y_px,
            "stamp_color": self.stamp_color_value,
            "stamp_border_color": self.stamp_border_color_value,
            "stamp_vertical": self.stamp_vertical_value,
        }
        values = load_project_settings_from_store(
            self.ui_settings,
            defaults,
            crop_ratios=set(CROP_RATIOS),
            sort_modes=set(SORT_MODES),
            sortable_columns=set(self.sortable_columns),
            stamp_fonts=set(STAMP_FONTS.keys()),
            stamp_scale_min=STAMP_SCALE_MIN_PERCENT,
            stamp_scale_max=STAMP_SCALE_MAX_PERCENT,
            stamp_offset_min=STAMP_OFFSET_MIN_PX,
            stamp_offset_max=STAMP_OFFSET_MAX_PX,
        )

        self.crop_ratio_value = str(values["crop_ratio"])
        self.stamp_mode_value = str(values["stamp_mode"])
        self.clock_mode_value = str(values["clock_mode"])
        self.corner_landscape_value = str(values["corner_landscape"])
        self.corner_portrait_value = str(values["corner_portrait"])
        self.sort_mode_value = str(values["sort_mode"])
        self.sort_column_value = int(values["sort_column"])
        self.sort_descending_value = bool(values["sort_descending"])
        self.stamp_font_value = str(values["stamp_font"])
        self.stamp_scale_percent = int(values["stamp_scale_percent"])
        self.stamp_offset_x_px = int(values["stamp_offset_x_px"])
        self.stamp_offset_y_px = int(values["stamp_offset_y_px"])
        self.stamp_color_value = str(values["stamp_color"])
        self.stamp_border_color_value = str(values["stamp_border_color"])
        self.stamp_vertical_value = bool(values["stamp_vertical"])

    def save_app_project_settings(self) -> None:
        save_project_settings_to_store(
            self.ui_settings,
            {
                "crop_ratio": self.crop_ratio_value,
                "stamp_mode": self.stamp_mode_value,
                "clock_mode": self.clock_mode_value,
                "corner_landscape": self.corner_landscape_value,
                "corner_portrait": self.corner_portrait_value,
                "sort_mode": self.sort_mode_value,
                "sort_column": self.sort_column_value,
                "sort_descending": self.sort_descending_value,
                "stamp_font": self.stamp_font_value,
                "stamp_scale_percent": self.stamp_scale_percent,
                "stamp_offset_x_px": self.stamp_offset_x_px,
                "stamp_offset_y_px": self.stamp_offset_y_px,
                "stamp_color": self.stamp_color_value,
                "stamp_border_color": self.stamp_border_color_value,
                "stamp_vertical": self.stamp_vertical_value,
            },
        )

    def borderless_enabled(self) -> bool:
        return self.borderless_mode_value == "enabled"

    def setup_menu(self) -> None:
        file_menu = self.menuBar().addMenu("File")

        load_action = QAction("Load Folder", self)
        load_action.triggered.connect(self.load_folder)
        file_menu.addAction(load_action)

        self.refresh_folder_action = QAction("Refresh Folder", self)
        self.refresh_folder_action.triggered.connect(self.refresh_folder)
        file_menu.addAction(self.refresh_folder_action)

        self.folder_settings_action = QAction("Settings", self)
        self.folder_settings_action.triggered.connect(self.open_project_settings_dialog)
        file_menu.addAction(self.folder_settings_action)

        print_settings_action = QAction("Printer Settings", self)
        print_settings_action.triggered.connect(self.open_print_settings_dialog)
        file_menu.addAction(print_settings_action)

        print_selected_action = QAction("Print Selected", self)
        print_selected_action.triggered.connect(self.print_selected)
        file_menu.addAction(print_selected_action)

        print_action = QAction("Print All", self)
        print_action.triggered.connect(self.print_all)
        file_menu.addAction(print_action)

        help_menu = self.menuBar().addMenu("Help")
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)

    def show_about_dialog(self) -> None:
        logo = load_clearminds_head_pixmap(96) or load_logo_pixmap(96)
        body = app_about_text()
        box = QMessageBox(self)
        box.setWindowTitle(f"About {APP_DISPLAY_NAME}")
        box.setText(body)
        box.setIcon(QMessageBox.Icon.Information)
        if logo is not None:
            box.setIconPixmap(logo)
        box.exec()

    def default_metadata(self) -> dict[str, object]:
        return {
            "version": 1,
            "image_settings": {},
            "photos": {},
            "print_events": [],
        }

    def selected_path(self) -> Path | None:
        row = self.image_table.currentRow()
        if row < 0 or row >= len(self.image_paths):
            return None
        return self.image_paths[row]

    def update_controls_visibility(self) -> None:
        has_selection = self.selected_path() is not None
        self.controls_widget.setVisible(has_selection)
        if not has_selection and self.crop_reframe_button.isChecked():
            self.crop_reframe_button.setChecked(False)

    def update_folder_settings_availability(self) -> None:
        self.folder_settings_button.setEnabled(True)
        self.folder_settings_action.setEnabled(True)
        available = self.current_folder is not None
        self.refresh_folder_button.setEnabled(available)
        self.refresh_folder_action.setEnabled(available)

    def metadata_path(self) -> Path | None:
        if self.current_folder is None:
            return None
        return self.current_folder / METADATA_FILENAME

    def log_file_path(self) -> Path | None:
        if self.current_folder is not None:
            return self.current_folder / LOG_FILENAME
        return None

    def current_log_level_rank(self) -> int:
        return LOG_LEVEL_RANK.get(self.log_level_filter_value, LOG_LEVEL_RANK["INFO"])

    def refresh_log_console(self) -> None:
        minimum_rank = self.current_log_level_rank()
        self.log_console.clear()
        for level, line in self.log_entries:
            rank = LOG_LEVEL_RANK.get(level, LOG_LEVEL_RANK["INFO"])
            if rank >= minimum_rank:
                self.log_console.append(line)

    def on_log_level_changed(self, value: str) -> None:
        level = value.strip().upper()
        if level not in LOG_LEVEL_RANK:
            level = "INFO"
        self.log_level_filter_value = level
        self.refresh_log_console()

    def clear_log_console(self) -> None:
        self.log_entries = []
        self.log_console.clear()

    def refresh_print_queue_table(self) -> None:
        self.print_queue_table.setRowCount(len(self.print_queue_items))
        for row, item in enumerate(self.print_queue_items):
            queue_id = int(item.get("id", 0))
            status = str(item.get("status", "Pending"))
            paths = item.get("paths", [])
            count = len(paths) if isinstance(paths, list) else 0
            target = str(item.get("target", ""))
            detail = str(item.get("detail", ""))

            id_item = QTableWidgetItem(str(queue_id))
            status_item = QTableWidgetItem(status)
            count_item = QTableWidgetItem(str(count))
            target_item = QTableWidgetItem(target)
            detail_item = QTableWidgetItem(detail)

            id_item.setFlags(id_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            status_item.setFlags(status_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            count_item.setFlags(count_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            target_item.setFlags(target_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            detail_item.setFlags(detail_item.flags() & ~Qt.ItemFlag.ItemIsEditable)

            self.print_queue_table.setItem(row, 0, id_item)
            self.print_queue_table.setItem(row, 1, status_item)
            self.print_queue_table.setItem(row, 2, count_item)
            self.print_queue_table.setItem(row, 3, target_item)
            self.print_queue_table.setItem(row, 4, detail_item)

        self.queue_pause_button.setEnabled(
            self.print_queue_processing
            or any(
                str(item.get("status", "")) == "Pending"
                for item in self.print_queue_items
            )
        )
        self.queue_resume_button.setEnabled(
            self.print_queue_paused
            and any(
                str(item.get("status", "")) == "Pending"
                for item in self.print_queue_items
            )
        )
        self.queue_cancel_button.setEnabled(bool(self.print_queue_items))
        self.update_queue_panel_max_width()

    def current_queue_target(self) -> str:
        backend = self.print_backend_value
        if backend == "IPP":
            return self.current_ipp_target_name()
        if self.printer_value:
            return self.printer_value
        return backend

    def current_ipp_target_name(self) -> str:
        ipp_uri = self.ipp_uri_value.strip()
        if not ipp_uri:
            return "IPP"

        cached = self.ipp_capabilities_cache.get(ipp_uri)
        if isinstance(cached, IppCapabilities):
            friendly = cached.printer_name.strip()
            if friendly:
                return friendly
        return ipp_uri

    def enqueue_print_paths(self, paths: list[Path]) -> None:
        if not paths:
            return
        queue_item = {
            "id": self.print_queue_next_id,
            "paths": list(paths),
            "status": "Pending",
            "target": self.current_queue_target(),
            "detail": "Queued",
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
        self.print_queue_next_id += 1
        self.print_queue_items.append(queue_item)
        self.refresh_print_queue_table()
        self.append_log(
            "INFO",
            f"Queued print job #{queue_item['id']} ({len(paths)} image(s))",
        )
        self.process_print_queue()

    def process_print_queue(self) -> None:
        if self.print_queue_processing or self.print_queue_paused:
            return

        pending_item: dict[str, object] | None = None
        for item in self.print_queue_items:
            if str(item.get("status", "")) == "Pending":
                pending_item = item
                break

        if pending_item is None:
            return

        self.print_queue_processing = True
        pending_item["status"] = "Printing"
        pending_item["detail"] = "Printing in progress"
        self.refresh_print_queue_table()

        paths = pending_item.get("paths", [])
        if not isinstance(paths, list):
            paths = []
        try:
            printed, failed, error, target_name, backend, job_ids = (
                self.execute_print_paths(paths)
            )

            queue_only_backend = backend in {"CUPS", "IPP"}

            if printed and not failed and not error:
                pending_item["status"] = "Queued" if queue_only_backend else "Done"
                pending_item["detail"] = (
                    f"Queued {len(printed)}"
                    if queue_only_backend
                    else f"Printed {len(printed)}"
                )
            elif printed and (failed or error):
                pending_item["status"] = "Partial"
                pending_item["detail"] = (
                    f"Queued {len(printed)}, failed {len(failed)}"
                    if queue_only_backend
                    else f"Printed {len(printed)}, failed {len(failed)}"
                )
            else:
                pending_item["status"] = "Failed"
                pending_item["detail"] = error or "No items printed"

            pending_item["target"] = target_name
            pending_item["backend"] = backend
            pending_item["job_ids"] = dict(job_ids)
        except Exception as error:
            pending_item["status"] = "Failed"
            pending_item["detail"] = f"Queue error: {error}"
            self.append_log("ERROR", f"Queue processing failed: {error}")
        finally:
            self.print_queue_processing = False
            self.refresh_print_queue_table()

            has_pending = any(
                str(item.get("status", "")) == "Pending"
                for item in self.print_queue_items
            )
            if has_pending and not self.print_queue_paused:
                QTimer.singleShot(0, self.process_print_queue)

    def pause_print_queue(self) -> None:
        self.print_queue_paused = True
        self.append_log("INFO", "Print queue paused")
        self.refresh_print_queue_table()

    def resume_print_queue(self) -> None:
        self.print_queue_paused = False
        self.append_log("INFO", "Print queue resumed")
        self.refresh_print_queue_table()
        self.process_print_queue()

    def remove_selected_queue_item(self) -> None:
        row = self.print_queue_table.currentRow()
        if row < 0 or row >= len(self.print_queue_items):
            return
        status = str(self.print_queue_items[row].get("status", ""))
        if status == "Printing":
            QMessageBox.information(
                self,
                "Queue item busy",
                "Cannot remove a job that is currently printing.",
            )
            return
        queue_id = self.print_queue_items[row].get("id")
        self.print_queue_items.pop(row)
        self.append_log("INFO", f"Removed queue job #{queue_id}")
        self.refresh_print_queue_table()

    def cancel_selected_queue_item(self) -> None:
        row = self.print_queue_table.currentRow()
        if row < 0 or row >= len(self.print_queue_items):
            return

        item = self.print_queue_items[row]
        queue_id = item.get("id")
        status = str(item.get("status", ""))

        if status == "Pending":
            item["status"] = "Cancelled"
            item["detail"] = "Cancelled before printing"
            self.append_log("INFO", f"Cancelled queue job #{queue_id} before start")
            self.refresh_print_queue_table()
            QMessageBox.information(
                self,
                "Queue job cancelled",
                f"Queue job #{queue_id} was cancelled before printing started.",
            )
            return

        backend = str(item.get("backend", ""))
        target = str(item.get("target", ""))
        job_ids_raw = item.get("job_ids")
        job_ids = job_ids_raw if isinstance(job_ids_raw, dict) else {}

        if not job_ids:
            QMessageBox.information(
                self,
                "No job IDs",
                "No backend job IDs are available for the selected queue item.",
            )
            return

        confirm = QMessageBox.question(
            self,
            "Cancel backend jobs",
            (
                f"Cancel {len(job_ids)} backend job(s) for queue job #{queue_id}?\n\n"
                f"Backend: {backend or '-'}\n"
                f"Target: {target or '-'}"
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            self.append_log(
                "INFO",
                f"Cancel aborted by user for queue job #{queue_id}",
            )
            return

        cancelled_count = 0
        errors: list[str] = []

        if backend in {"CUPS", "Auto"}:
            if shutil.which("cancel") is None:
                errors.append("CUPS cancel command not available")
            else:
                for path_name, request_id in job_ids.items():
                    request_text = str(request_id).strip()
                    if not request_text:
                        continue
                    result = subprocess.run(
                        ["cancel", request_text],
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    if result.returncode == 0:
                        cancelled_count += 1
                    else:
                        detail = (result.stderr or result.stdout or "").strip()
                        errors.append(
                            f"{path_name} ({request_text}): {detail or 'cancel failed'}"
                        )
        elif backend == "IPP":
            for path_name, raw_job_id in job_ids.items():
                numeric_job_id = parse_ipp_job_id(str(raw_job_id))
                if numeric_job_id is None:
                    errors.append(f"{path_name}: invalid job-id '{raw_job_id}'")
                    continue
                try:
                    cancel_ipp_job(target, numeric_job_id)
                    cancelled_count += 1
                except IppBackendError as error:
                    errors.append(f"{path_name} ({numeric_job_id}): {error}")
        else:
            errors.append(f"Backend '{backend}' does not support cancel")

        if cancelled_count:
            item["status"] = "Cancelled"
            item["detail"] = f"Cancelled {cancelled_count} job(s)"
            self.append_log(
                "INFO",
                f"Cancelled {cancelled_count} backend job(s) for queue job #{queue_id}",
            )

        if errors:
            self.append_log(
                "WARNING",
                "Queue cancel issues: " + " | ".join(errors[:6]),
            )

        self.refresh_print_queue_table()

        if cancelled_count and not errors:
            QMessageBox.information(
                self,
                "Cancel complete",
                "Cancelled "
                f"{cancelled_count} backend job(s) "
                f"for queue job #{queue_id}.",
            )
        elif cancelled_count and errors:
            QMessageBox.warning(
                self,
                "Cancel partial",
                (
                    "Cancelled "
                    f"{cancelled_count} backend job(s) "
                    f"for queue job #{queue_id}.\n\n"
                    f"Some cancels failed:\n- " + "\n- ".join(errors[:5])
                ),
            )
        elif errors:
            QMessageBox.warning(
                self,
                "Cancel failed",
                "Could not cancel backend jobs:\n- " + "\n- ".join(errors[:6]),
            )

    def clear_finished_queue_items(self) -> None:
        finished_states = {"Done", "Failed", "Partial", "Cancelled"}
        before = len(self.print_queue_items)
        self.print_queue_items = [
            item
            for item in self.print_queue_items
            if str(item.get("status", "")) not in finished_states
        ]
        removed = before - len(self.print_queue_items)
        if removed:
            self.append_log("INFO", f"Cleared {removed} finished queue job(s)")
        self.refresh_print_queue_table()

    def append_log(self, level: str, message: str) -> None:
        level_text = level.strip().upper() or "INFO"
        if level_text not in LOG_LEVEL_RANK:
            level_text = "INFO"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"{timestamp} [{level_text}] {message}"
        self.log_entries.append((level_text, line))
        if LOG_LEVEL_RANK[level_text] >= self.current_log_level_rank():
            self.log_console.append(line)

        log_path = self.log_file_path()
        if log_path is None:
            return
        try:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with log_path.open("a", encoding="utf-8") as fh:
                fh.write(line + "\n")
        except OSError:
            return

    def current_project_settings_payload(self) -> dict[str, object]:
        return {
            "crop_ratio": self.crop_ratio_value,
            "stamp_mode": self.stamp_mode_value,
            "clock_mode": self.clock_mode_value,
            "corner_landscape": self.corner_landscape_value,
            "corner_portrait": self.corner_portrait_value,
            "sort_mode": self.sort_mode_value,
            "sort_column": self.sort_column_value,
            "sort_descending": self.sort_descending_value,
            "stamp_font": self.stamp_font_value,
            "stamp_scale_percent": self.stamp_scale_percent,
            "stamp_offset_x_px": self.stamp_offset_x_px,
            "stamp_offset_y_px": self.stamp_offset_y_px,
            "stamp_color": self.stamp_color_value,
            "stamp_border_color": self.stamp_border_color_value,
            "stamp_vertical": self.stamp_vertical_value,
        }

    def persist_project_settings(self) -> None:
        self.save_app_project_settings()

    def image_settings_for_path(self, path: Path) -> dict[str, object]:
        image_settings = self.folder_metadata.get("image_settings", {})
        if not isinstance(image_settings, dict):
            image_settings = {}

        values = image_settings.get(path.name, {})
        if not isinstance(values, dict):
            values = {}

        orientation = values.get("orientation")
        if orientation not in {"Landscape", "Portrait"}:
            orientation = self.detect_orientation_for_path(path)

        brightness = values.get("brightness_percent", 100)
        if not isinstance(brightness, int):
            brightness = 100
        brightness = max(self.brightness_slider.minimum(), brightness)
        brightness = min(self.brightness_slider.maximum(), brightness)

        datetime_override = values.get("datetime_override")
        if not isinstance(datetime_override, str):
            datetime_override = ""

        crop_zoom_percent = values.get("crop_zoom_percent", 100)
        if not isinstance(crop_zoom_percent, int):
            crop_zoom_percent = 100
        crop_zoom_percent = max(100, min(300, crop_zoom_percent))

        crop_offset_x_percent = values.get("crop_offset_x_percent", 0)
        if not isinstance(crop_offset_x_percent, int):
            crop_offset_x_percent = 0
        crop_offset_x_percent = max(-100, min(100, crop_offset_x_percent))

        crop_offset_y_percent = values.get("crop_offset_y_percent", 0)
        if not isinstance(crop_offset_y_percent, int):
            crop_offset_y_percent = 0
        crop_offset_y_percent = max(-100, min(100, crop_offset_y_percent))

        return {
            "orientation": orientation,
            "brightness_percent": brightness,
            "datetime_override": datetime_override,
            "crop_zoom_percent": crop_zoom_percent,
            "crop_offset_x_percent": crop_offset_x_percent,
            "crop_offset_y_percent": crop_offset_y_percent,
        }

    def compute_file_hash(self, path: Path) -> str:
        try:
            stat = path.stat()
        except OSError:
            return ""

        cached = self.file_hash_cache.get(path)
        if cached is not None:
            cached_mtime_ns, cached_size, cached_hash = cached
            if cached_mtime_ns == stat.st_mtime_ns and cached_size == stat.st_size:
                return cached_hash

        digest = hashlib.sha256()
        try:
            with path.open("rb") as file_handle:
                for chunk in iter(lambda: file_handle.read(1024 * 1024), b""):
                    digest.update(chunk)
        except OSError:
            return ""

        file_hash = digest.hexdigest()
        self.file_hash_cache[path] = (stat.st_mtime_ns, stat.st_size, file_hash)
        return file_hash

    def set_image_entry_file_hash(self, path: Path, entry: dict[str, object]) -> None:
        file_hash = self.compute_file_hash(path)
        if file_hash:
            entry["file_hash"] = file_hash

    def sync_image_settings_with_files(self) -> int:
        image_settings = self.folder_metadata.get("image_settings")
        if not isinstance(image_settings, dict):
            return 0

        paths_by_name = {path.name: path for path in self.image_paths}
        has_changes = False
        reset_count = 0

        for name in list(image_settings.keys()):
            entry = image_settings.get(name)
            if not isinstance(entry, dict):
                continue

            path = paths_by_name.get(name)
            if path is None:
                continue

            current_hash = self.compute_file_hash(path)
            if not current_hash:
                continue

            stored_hash = str(entry.get("file_hash", "")).strip()
            if stored_hash and stored_hash != current_hash:
                image_settings.pop(name, None)
                self.orientation_cache.pop(path, None)
                self.thumbnail_cache.pop(path, None)
                has_changes = True
                reset_count += 1
                continue

            if not stored_hash:
                entry["file_hash"] = current_hash
                image_settings[name] = entry
                has_changes = True

        if has_changes:
            self.save_folder_metadata()
        return reset_count

    def detect_orientation_for_path(self, path: Path) -> str:
        cached = self.orientation_cache.get(path)
        if cached in {"Landscape", "Portrait"}:
            return cached

        orientation = "Landscape"
        try:
            with Image.open(path) as image:
                width, height = image.size
            orientation = "Portrait" if height > width else "Landscape"
        except OSError:
            orientation = "Landscape"

        self.orientation_cache[path] = orientation
        return orientation

    def photo_entry_for_path(self, path: Path) -> dict[str, object]:
        photos = self.folder_metadata.get("photos")
        if not isinstance(photos, dict):
            return {}

        entry = photos.get(path.name)
        if not isinstance(entry, dict):
            return {}
        return entry

    def latest_print_status_for_path(self, path: Path) -> str:
        entry = self.photo_entry_for_path(path)
        status_raw = str(entry.get("last_print_status", "")).strip().lower()
        status_map = {
            "printed": "Printed",
            "failed": "Failed",
            "partial": "Partial",
        }
        if status_raw in status_map:
            return status_map[status_raw]

        try:
            total_printed = int(entry.get("total_printed", 0))
        except (TypeError, ValueError):
            total_printed = 0
        if total_printed > 0:
            return "Printed"
        return "Not Printed"

    def update_selected_print_info(self) -> None:
        path = self.selected_path()

        def set_attempt_rows(rows: list[tuple[str, str, str, str, str]]) -> None:
            self.print_attempts_table.setRowCount(len(rows))
            for row_index, (
                time_text,
                status_text,
                backend_text,
                job_text,
                error_text,
            ) in enumerate(rows):
                self.print_attempts_table.setItem(
                    row_index, 0, QTableWidgetItem(time_text)
                )
                self.print_attempts_table.setItem(
                    row_index, 1, QTableWidgetItem(status_text)
                )
                self.print_attempts_table.setItem(
                    row_index, 2, QTableWidgetItem(backend_text)
                )
                self.print_attempts_table.setItem(
                    row_index, 3, QTableWidgetItem(job_text)
                )
                self.print_attempts_table.setItem(
                    row_index, 4, QTableWidgetItem(error_text)
                )

        if path is None:
            self.print_status_label.setText("Not Printed")
            set_attempt_rows([("-", "-", "-", "-", "No Print Attempts")])
            return

        self.print_status_label.setText(self.latest_print_status_for_path(path))
        entry = self.photo_entry_for_path(path)
        attempts = entry.get("print_attempts")

        if not isinstance(attempts, list) or not attempts:
            set_attempt_rows([("-", "-", "-", "-", "No Print Attempts")])
            return

        rows: list[tuple[str, str, str, str, str]] = []
        status_map = {
            "printed": "Printed",
            "failed": "Failed",
            "partial": "Partial",
        }

        for attempt in reversed(attempts[-20:]):
            if isinstance(attempt, str):
                text = attempt.strip()
                if text:
                    rows.append(("-", "Unknown", "-", "-", text))
                continue

            if not isinstance(attempt, dict):
                continue

            timestamp = str(attempt.get("timestamp", "")).strip() or "-"
            status_raw = str(attempt.get("status", "")).strip().lower()
            status = status_map.get(
                status_raw, status_raw.title() if status_raw else "Unknown"
            )
            backend = str(attempt.get("backend", "")).strip() or "-"
            job_id = str(attempt.get("job_id", "")).strip() or "-"
            error_text = str(attempt.get("error", "")).strip() or "-"
            rows.append((timestamp, status, backend, job_id, error_text))

        if not rows:
            rows = [("-", "-", "-", "-", "No Print Attempts")]

        set_attempt_rows(rows)

    def image_list_label(self, path: Path) -> str:
        values = self.image_settings_for_path(path)
        orientation = str(values.get("orientation", "Landscape"))
        orientation_short = "L" if orientation == "Landscape" else "P"
        return f"Mode {orientation_short}"

    def is_crop_settings_modified(self, path: Path) -> bool:
        values = self.image_settings_for_path(path)
        default_orientation = self.detect_orientation_for_path(path)

        if str(values.get("orientation", default_orientation)) != default_orientation:
            return True
        if int(values.get("crop_zoom_percent", 100)) != 100:
            return True
        if int(values.get("crop_offset_x_percent", 0)) != 0:
            return True
        if int(values.get("crop_offset_y_percent", 0)) != 0:
            return True
        return False

    def date_used_for_path(self, path: Path) -> datetime:
        values = self.image_settings_for_path(path)
        override_text = str(values.get("datetime_override", ""))
        override_dt = parse_datetime_override(override_text)
        if override_dt is not None:
            return override_dt
        return datetime_for_image(path)

    def date_used_and_source_for_path(self, path: Path) -> tuple[datetime, str]:
        values = self.image_settings_for_path(path)
        override_text = str(values.get("datetime_override", ""))
        override_dt = parse_datetime_override(override_text)
        if override_dt is not None:
            return override_dt, "Override"

        exif_dt = exif_datetime_for_image(path)
        if exif_dt is not None:
            return exif_dt, "EXIF"

        filename_dt = parse_datetime_from_filename(path.name)
        if filename_dt is not None:
            return filename_dt, "Filename"

        return datetime.fromtimestamp(path.stat().st_mtime), "Modified"

    def start_thumbnail_generation(self) -> None:
        self.thumbnail_generation += 1
        self.thumbnail_pending_paths = [
            path for path in self.image_paths if path not in self.thumbnail_cache
        ]
        self.thumbnail_inflight_paths = set()
        self.fill_thumbnail_workers()

    def fill_thumbnail_workers(self) -> None:
        while (
            self.thumbnail_pending_paths
            and len(self.thumbnail_inflight_paths) < THUMBNAIL_MAX_INFLIGHT
        ):
            path = self.thumbnail_pending_paths.pop(0)
            if path in self.thumbnail_cache or path in self.thumbnail_inflight_paths:
                continue
            self.thumbnail_inflight_paths.add(path)
            worker = ThumbnailWorker(path, self.thumbnail_generation)
            worker.signals.finished.connect(self.on_thumbnail_ready)
            self.thumbnail_thread_pool.start(worker)

    def on_thumbnail_ready(self, path: object, generation: int, image: object) -> None:
        if not isinstance(path, Path):
            return

        self.thumbnail_inflight_paths.discard(path)
        if generation != self.thumbnail_generation:
            return

        if isinstance(image, QImage):
            pixmap = QPixmap.fromImage(image)
        else:
            pixmap = self.thumbnail_placeholder
        self.thumbnail_cache[path] = pixmap

        try:
            row = self.image_paths.index(path)
        except ValueError:
            self.fill_thumbnail_workers()
            return

        item = self.image_table.item(row, TABLE_COL_THUMB)
        if item is not None:
            item.setData(Qt.ItemDataRole.DecorationRole, pixmap)

        self.fill_thumbnail_workers()

    def refresh_image_list_labels(self, preferred_path: Path | None = None) -> None:
        if preferred_path is None:
            preferred_path = self.selected_path()

        self._updating_table = True
        self.image_table.blockSignals(True)
        self.image_table.setRowCount(len(self.image_paths))
        for row, path in enumerate(self.image_paths):
            values = self.image_settings_for_path(path)
            date_used, date_source = self.date_used_and_source_for_path(path)
            override_text = str(values.get("datetime_override", ""))

            thumb_item = QTableWidgetItem()
            thumbnail = self.thumbnail_cache.get(path, self.thumbnail_placeholder)
            thumb_item.setData(
                Qt.ItemDataRole.DecorationRole,
                thumbnail,
            )

            state_item = QTableWidgetItem(self.image_list_label(path))
            print_item = QTableWidgetItem(self.latest_print_status_for_path(path))
            file_item = QTableWidgetItem(path.name)
            date_item = QTableWidgetItem(date_used.strftime("%Y-%m-%d %H:%M"))
            source_item = QTableWidgetItem(date_source)
            override_item = QTableWidgetItem(override_text)

            if self.is_crop_settings_modified(path):
                state_font = state_item.font()
                state_font.setBold(True)
                state_item.setFont(state_font)
                state_item.setForeground(QColor("#FF9100"))

            thumb_item.setFlags(thumb_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            state_item.setFlags(state_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            print_item.setFlags(print_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            file_item.setFlags(file_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            date_item.setFlags(date_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            source_item.setFlags(source_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            override_item.setFlags(override_item.flags() & ~Qt.ItemFlag.ItemIsEditable)

            self.image_table.setItem(row, TABLE_COL_THUMB, thumb_item)
            self.image_table.setItem(row, TABLE_COL_STATE, state_item)
            self.image_table.setItem(row, TABLE_COL_PRINT, print_item)
            self.image_table.setItem(row, TABLE_COL_FILE, file_item)
            self.image_table.setItem(row, TABLE_COL_DATE_USED, date_item)
            self.image_table.setItem(row, TABLE_COL_DATE_SOURCE, source_item)
            self.image_table.setItem(row, TABLE_COL_OVERRIDE, override_item)

        self.image_table.blockSignals(False)
        self._updating_table = False

        if self.image_paths:
            if preferred_path in self.image_paths:
                self.image_table.setCurrentCell(
                    self.image_paths.index(preferred_path),
                    TABLE_COL_FILE,
                )
            else:
                self.image_table.setCurrentCell(0, TABLE_COL_FILE)

        self.start_thumbnail_generation()

    def update_table_sort_indicator(self) -> None:
        order = (
            Qt.SortOrder.DescendingOrder
            if self.sort_descending_value
            else Qt.SortOrder.AscendingOrder
        )
        self.image_table.horizontalHeader().setSortIndicator(
            self.sort_column_value, order
        )

    def sort_key_for_path(self, path: Path, column: int) -> object:
        if column == TABLE_COL_FILE:
            return path.name.lower()
        if column == TABLE_COL_DATE_USED:
            return self.date_used_for_path(path)
        if column == TABLE_COL_DATE_SOURCE:
            _date_used, source = self.date_used_and_source_for_path(path)
            return source
        if column == TABLE_COL_OVERRIDE:
            values = self.image_settings_for_path(path)
            return str(values.get("datetime_override", "")).lower()
        return path.name.lower()

    def apply_table_sort(self, preferred_path: Path | None = None) -> None:
        if not self.image_paths:
            self.update_table_sort_indicator()
            return

        self.image_paths.sort(
            key=lambda path: self.sort_key_for_path(path, self.sort_column_value),
            reverse=self.sort_descending_value,
        )
        self.refresh_image_list_labels(preferred_path)
        self.update_table_sort_indicator()

    def on_image_table_header_clicked(self, column: int) -> None:
        if column not in self.sortable_columns:
            self.update_table_sort_indicator()
            return

        preferred_path = self.selected_path()
        if self.sort_column_value == column:
            self.sort_descending_value = not self.sort_descending_value
        else:
            self.sort_column_value = column
            self.sort_descending_value = False

        self.apply_table_sort(preferred_path)
        self.persist_project_settings()

    def apply_sort_order(self, preferred_path: Path | None = None) -> None:
        self.apply_table_sort(preferred_path)

    def load_folder_metadata(self) -> None:
        path = self.metadata_path()
        if path is None or not path.exists():
            self.folder_metadata = self.default_metadata()
            return

        try:
            with path.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
            if isinstance(data, dict):
                self.folder_metadata = self.default_metadata() | data
            else:
                self.folder_metadata = self.default_metadata()
        except (OSError, json.JSONDecodeError):
            self.folder_metadata = self.default_metadata()

    def save_folder_metadata(self) -> None:
        path = self.metadata_path()
        if path is None:
            return

        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(".json.tmp")
            with tmp.open("w", encoding="utf-8") as fh:
                json.dump(self.folder_metadata, fh, indent=2, ensure_ascii=False)
            tmp.replace(path)
        except OSError:
            return

    def restore_image_settings_for_selected(self) -> None:
        path = self.selected_path()
        if path is None:
            return

        values = self.image_settings_for_path(path)
        self._restoring_settings = True
        try:
            self.current_image_orientation = str(values["orientation"])
            self.brightness_slider.setValue(int(values["brightness_percent"]))
            self.crop_zoom_slider.setValue(int(values["crop_zoom_percent"]))
            self.crop_x_slider.setValue(int(values["crop_offset_x_percent"]))
            self.crop_y_slider.setValue(int(values["crop_offset_y_percent"]))
            self.update_crop_orientation_button_text()
            dt_value = str(values.get("datetime_override", ""))
            self.datetime_override_label.setText(dt_value if dt_value else "Auto")
        finally:
            self._restoring_settings = False

    def set_datetime_override_for_selected(self) -> None:
        path = self.selected_path()
        if path is None or self.current_folder is None:
            return

        parsed = self.pick_datetime_override(path)
        if parsed is None:
            return

        self.set_datetime_override_for_path(path, parsed)

    def pick_datetime_override(self, path: Path) -> datetime | None:
        current_override = str(
            self.image_settings_for_path(path).get("datetime_override", "")
        )
        initial_dt = parse_datetime_override(current_override)
        if initial_dt is None:
            initial_dt = datetime_for_image(path)

        dialog = QDialog(self)
        dialog.setWindowTitle("Set Date/Time")
        layout = QVBoxLayout(dialog)

        picker = QDateTimeEdit(dialog)
        picker.setCalendarPopup(True)
        picker.setDisplayFormat("yyyy-MM-dd HH:mm")
        picker.setDateTime(
            QDateTime(
                initial_dt.year,
                initial_dt.month,
                initial_dt.day,
                initial_dt.hour,
                initial_dt.minute,
                initial_dt.second,
            )
        )
        layout.addWidget(picker)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            parent=dialog,
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return None

        return picker.dateTime().toPython()

    def set_datetime_override_for_path(self, path: Path, value: datetime) -> None:
        if self.current_folder is None:
            return

        image_settings = self.folder_metadata.get("image_settings")
        if not isinstance(image_settings, dict):
            image_settings = {}
            self.folder_metadata["image_settings"] = image_settings

        existing = image_settings.get(path.name)
        if not isinstance(existing, dict):
            existing = {}
        existing["datetime_override"] = value.isoformat(timespec="seconds")
        self.set_image_entry_file_hash(path, existing)
        image_settings[path.name] = existing
        self.save_folder_metadata()
        self.datetime_override_label.setText(existing["datetime_override"])
        self.refresh_image_list_labels(path)
        self.refresh_preview()

    def clear_datetime_override_for_selected(self) -> None:
        path = self.selected_path()
        if path is None or self.current_folder is None:
            return

        image_settings = self.folder_metadata.get("image_settings")
        if not isinstance(image_settings, dict):
            return

        existing = image_settings.get(path.name)
        if not isinstance(existing, dict):
            return

        existing.pop("datetime_override", None)
        self.set_image_entry_file_hash(path, existing)
        image_settings[path.name] = existing
        self.save_folder_metadata()
        self.datetime_override_label.setText("Auto")
        self.refresh_image_list_labels(path)
        self.refresh_preview()

    def update_crop_orientation_button_text(self) -> None:
        self.crop_orientation_button.setText(f"Crop: {self.current_image_orientation}")

    def toggle_crop_orientation(self) -> None:
        if self.current_folder is None or self.selected_path() is None:
            return

        self.current_image_orientation = (
            "Portrait" if self.current_image_orientation == "Landscape" else "Landscape"
        )
        self.update_crop_orientation_button_text()
        self.on_image_settings_changed()
        self.refresh_preview()

    def on_crop_reframe_toggled(self, enabled: bool) -> None:
        self.preview_label.set_drag_enabled(enabled)
        self.preview_label.set_overlay_enabled(enabled)
        self._reframe_drag_active = False
        self._reframe_interaction_mode = "pan"
        self._reframe_resize_corner = None
        self._reframe_pan_accum_x = 0.0
        self._reframe_pan_accum_y = 0.0
        self._reframe_zoom_accum = 0.0
        if enabled:
            self.crop_reframe_button.setText("Reframe Crop (On)")
            self.update_preview_overlay_rect()
        else:
            self.crop_reframe_button.setText("Reframe Crop")
            self.preview_label.set_overlay_rect(None)
            self.refresh_preview()

    def reset_crop_for_selected(self) -> None:
        if self.selected_path() is None:
            return
        self.crop_zoom_slider.setValue(100)
        self.crop_x_slider.setValue(0)
        self.crop_y_slider.setValue(0)
        self.on_image_settings_changed()
        self.refresh_preview()

    def resize_corner_at(self, x: int, y: int) -> str | None:
        rect = self.compute_overlay_rect_for_current_crop()
        if rect is None:
            return None
        left, top, width, height = rect
        if width <= 0 or height <= 0:
            return None
        right = left + width
        bottom = top + height
        threshold = REFRAME_HANDLE_SIZE
        corners = {
            "top_left": (left, top),
            "top_right": (right, top),
            "bottom_left": (left, bottom),
            "bottom_right": (right, bottom),
        }
        for name, (cx, cy) in corners.items():
            if abs(x - cx) <= threshold and abs(y - cy) <= threshold:
                return name
        return None

    def on_preview_drag_started(self, x: int, y: int) -> None:
        if not self.crop_reframe_button.isChecked():
            self._reframe_interaction_mode = "pan"
            self._reframe_resize_corner = None
            return

        self._reframe_drag_active = False
        self._reframe_pan_accum_x = 0.0
        self._reframe_pan_accum_y = 0.0
        self._reframe_zoom_accum = 0.0

        corner = self.resize_corner_at(x, y)
        if corner is None:
            self._reframe_interaction_mode = "pan"
            self._reframe_resize_corner = None
            return

        self._reframe_interaction_mode = "resize"
        self._reframe_resize_corner = corner

    def on_preview_dragged(self, delta_x: int, delta_y: int, _x: int, _y: int) -> None:
        if not self.crop_reframe_button.isChecked():
            return
        if self.selected_path() is None:
            return

        _px, _py, width, height = self.preview_display_rect
        width = max(0, int(width))
        height = max(0, int(height))
        if width <= 0 or height <= 0:
            return

        if self._reframe_interaction_mode == "resize":
            corner = self._reframe_resize_corner or "bottom_right"
            if corner == "bottom_right":
                effective = (delta_x + delta_y) / 2.0
            elif corner == "top_left":
                effective = (-delta_x - delta_y) / 2.0
            elif corner == "top_right":
                effective = (delta_x - delta_y) / 2.0
            else:
                effective = (-delta_x + delta_y) / 2.0

            self._reframe_zoom_accum += (-effective) * 0.35
            zoom_step = int(self._reframe_zoom_accum)
            if zoom_step:
                current_zoom = self.crop_zoom_slider.value()
                next_zoom = max(100, min(300, current_zoom + zoom_step))
                self._reframe_zoom_accum -= zoom_step
                if next_zoom != current_zoom:
                    self._reframe_drag_active = True
                    self.crop_zoom_slider.blockSignals(True)
                    try:
                        self.crop_zoom_slider.setValue(next_zoom)
                    finally:
                        self.crop_zoom_slider.blockSignals(False)
                    self.crop_zoom_label.setText(f"{next_zoom}%")
                    self.update_preview_overlay_rect()
            return

        self._reframe_pan_accum_x += (delta_x / width) * 200.0
        self._reframe_pan_accum_y += (delta_y / height) * 200.0
        delta_percent_x = int(self._reframe_pan_accum_x)
        delta_percent_y = int(self._reframe_pan_accum_y)

        if delta_percent_x:
            self._reframe_pan_accum_x -= delta_percent_x
        if delta_percent_y:
            self._reframe_pan_accum_y -= delta_percent_y

        updated = False
        current_x = self.crop_x_slider.value()
        current_y = self.crop_y_slider.value()

        next_x = current_x
        next_y = current_y

        if delta_percent_x:
            next_x = max(-100, min(100, current_x + delta_percent_x))
        if delta_percent_y:
            next_y = max(-100, min(100, current_y + delta_percent_y))

        if next_x != current_x:
            self.crop_x_slider.blockSignals(True)
            try:
                self.crop_x_slider.setValue(next_x)
            finally:
                self.crop_x_slider.blockSignals(False)
            self.crop_x_label.setText(str(next_x))
            updated = True

        if next_y != current_y:
            self.crop_y_slider.blockSignals(True)
            try:
                self.crop_y_slider.setValue(next_y)
            finally:
                self.crop_y_slider.blockSignals(False)
            self.crop_y_label.setText(str(next_y))
            updated = True

        if updated:
            self._reframe_drag_active = True
            self.update_preview_overlay_rect()

    def on_preview_drag_released(self, _x: int, _y: int) -> None:
        self._reframe_interaction_mode = "pan"
        self._reframe_resize_corner = None
        self._reframe_pan_accum_x = 0.0
        self._reframe_pan_accum_y = 0.0
        self._reframe_zoom_accum = 0.0
        if not self._reframe_drag_active:
            return
        self._reframe_drag_active = False
        self.on_image_settings_changed()
        self.refresh_preview()

    def compute_overlay_rect_for_current_crop(self) -> tuple[int, int, int, int] | None:
        path = self.selected_path()
        if path is None:
            return None
        source_width, source_height = self.preview_source_size
        display_x, display_y, display_w, display_h = self.preview_display_rect
        if source_width <= 0 or source_height <= 0:
            return None
        if display_w <= 0 or display_h <= 0:
            return None

        settings = self.processing_settings_for_path(path)
        crop_left, crop_top, crop_w, crop_h = crop_geometry_for_ratio(
            source_width,
            source_height,
            settings.orientation,
            settings.crop_ratio,
            settings.crop_zoom_percent,
            settings.crop_offset_x_percent,
            settings.crop_offset_y_percent,
        )
        if crop_w <= 0 or crop_h <= 0:
            return None

        scale_x = display_w / source_width
        scale_y = display_h / source_height

        x1 = display_x + int(round(crop_left * scale_x))
        y1 = display_y + int(round(crop_top * scale_y))
        x2 = display_x + int(round((crop_left + crop_w) * scale_x))
        y2 = display_y + int(round((crop_top + crop_h) * scale_y))

        min_x = display_x
        min_y = display_y
        max_x = display_x + display_w
        max_y = display_y + display_h

        x1 = max(min_x, min(max_x, x1))
        y1 = max(min_y, min(max_y, y1))
        x2 = max(min_x, min(max_x, x2))
        y2 = max(min_y, min(max_y, y2))

        width = max(1, x2 - x1)
        height = max(1, y2 - y1)
        return x1, y1, width, height

    def update_preview_overlay_rect(self) -> None:
        overlay_enabled = self.crop_reframe_button.isChecked()
        self.preview_label.set_overlay_enabled(overlay_enabled)
        if not overlay_enabled:
            self.preview_label.set_overlay_rect(None)
            return
        self.preview_label.set_overlay_rect(
            self.compute_overlay_rect_for_current_crop()
        )

    def on_image_settings_changed(self, *_args) -> None:
        if self._restoring_settings or self.current_folder is None:
            return

        path = self.selected_path()
        if path is None:
            return

        image_settings = self.folder_metadata.get("image_settings")
        if not isinstance(image_settings, dict):
            image_settings = {}
            self.folder_metadata["image_settings"] = image_settings

        existing = image_settings.get(path.name)
        if not isinstance(existing, dict):
            existing = {}

        existing["orientation"] = self.current_image_orientation
        existing["brightness_percent"] = self.brightness_slider.value()
        existing["crop_zoom_percent"] = self.crop_zoom_slider.value()
        existing["crop_offset_x_percent"] = self.crop_x_slider.value()
        existing["crop_offset_y_percent"] = self.crop_y_slider.value()
        self.set_image_entry_file_hash(path, existing)
        image_settings[path.name] = existing
        self.save_folder_metadata()
        self.refresh_image_list_labels(path)

    def processing_settings_for_path(self, path: Path) -> ProcessingSettings:
        image_settings = self.image_settings_for_path(path)

        if path == self.selected_path():
            image_settings = {
                **image_settings,
                "orientation": self.current_image_orientation,
                "brightness_percent": self.brightness_slider.value(),
                "crop_zoom_percent": self.crop_zoom_slider.value(),
                "crop_offset_x_percent": self.crop_x_slider.value(),
                "crop_offset_y_percent": self.crop_y_slider.value(),
            }

        stamp_mode = "None"
        clock_mode = "24h"
        orientation = str(image_settings.get("orientation", "Landscape"))
        corner = "Bottom Right"
        stamp_mode = self.stamp_mode_value
        clock_mode = self.clock_mode_value
        if orientation == "Portrait":
            corner = self.corner_portrait_value
        else:
            corner = self.corner_landscape_value

        return ProcessingSettings(
            orientation=orientation,
            brightness_percent=int(image_settings.get("brightness_percent", 100)),
            crop_ratio=self.crop_ratio_value,
            crop_zoom_percent=int(image_settings.get("crop_zoom_percent", 100)),
            crop_offset_x_percent=int(image_settings.get("crop_offset_x_percent", 0)),
            crop_offset_y_percent=int(image_settings.get("crop_offset_y_percent", 0)),
            stamp_mode=stamp_mode,
            clock_mode=clock_mode,
            corner=corner,
            stamp_font=self.stamp_font_value,
            stamp_scale_percent=self.stamp_scale_percent,
            stamp_offset_x_px=self.stamp_offset_x_px,
            stamp_offset_y_px=self.stamp_offset_y_px,
            stamp_color=self.stamp_color_value,
            stamp_border_color=self.stamp_border_color_value,
            stamp_vertical=self.stamp_vertical_value,
            datetime_override=parse_datetime_override(
                str(image_settings.get("datetime_override", ""))
            ),
        )

    def refresh_preview(self) -> None:
        path = self.selected_path()
        if path is None:
            self.preview_source_size = (0, 0)
            self.preview_display_rect = (0, 0, 0, 0)
            self.preview_label.set_overlay_rect(None)
            return

        settings = self.processing_settings_for_path(path)
        reframe_active = self.crop_reframe_button.isChecked()
        max_preview_dimension = max(
            1200,
            int(max(self.preview_label.width(), self.preview_label.height()) * 2),
        )

        try:
            if reframe_active:
                with Image.open(path) as source:
                    image = source.convert("RGB")
                longest = max(image.width, image.height)
                if longest > max_preview_dimension:
                    scale = max_preview_dimension / float(longest)
                    resized = (
                        max(1, int(round(image.width * scale))),
                        max(1, int(round(image.height * scale))),
                    )
                    image = image.resize(resized, Image.Resampling.LANCZOS)
                image = ImageEnhance.Brightness(image).enhance(
                    settings.brightness_percent / 100.0
                )
                image = apply_stamp(image, stamp_text(path, settings), settings)
                self.preview_source_size = (max(1, image.width), max(1, image.height))
            else:
                image = render_preview_image(path, settings, max_preview_dimension)
                self.preview_source_size = (0, 0)
        except OSError as error:
            QMessageBox.critical(self, "Preview failed", str(error))
            self.preview_source_size = (0, 0)
            self.preview_display_rect = (0, 0, 0, 0)
            self.preview_label.set_overlay_rect(None)
            return

        qt_image = QImage(ImageQt(image))
        pixmap = QPixmap.fromImage(qt_image)
        scaled = pixmap.scaled(
            self.preview_container.viewport().size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.preview_scaled_size = (scaled.width(), scaled.height())
        viewport_size = self.preview_container.viewport().size()
        label_w = max(0, viewport_size.width())
        label_h = max(0, viewport_size.height())
        scaled_w = max(0, scaled.width())
        scaled_h = max(0, scaled.height())
        left = max(0, (label_w - scaled_w) // 2)
        top = max(0, (label_h - scaled_h) // 2)
        self.preview_display_rect = (left, top, scaled_w, scaled_h)
        self.preview_label.setPixmap(scaled)
        if reframe_active:
            self.update_preview_overlay_rect()
        else:
            self.preview_label.set_overlay_enabled(False)
            self.preview_label.set_overlay_rect(None)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self.refresh_preview()

    def on_image_changed(self, row: int) -> None:
        self.current_index = row
        self.update_controls_visibility()
        self.update_selected_print_info()
        if row < 0 or row >= len(self.image_paths):
            if self.crop_reframe_button.isChecked():
                self.crop_reframe_button.setChecked(False)
            self.preview_label.setText("Load a folder to begin")
            self.preview_label.setPixmap(QPixmap())
            self.preview_source_size = (0, 0)
            self.preview_display_rect = (0, 0, 0, 0)
            self.preview_label.set_overlay_rect(None)
            return
        self.restore_image_settings_for_selected()
        self.refresh_preview()

    def on_image_table_selection_changed(self, current_row: int, *_args) -> None:
        self.on_image_changed(current_row)

    def on_image_table_cell_double_clicked(self, row: int, column: int) -> None:
        if column != TABLE_COL_OVERRIDE:
            return
        if row < 0 or row >= len(self.image_paths):
            return

        path = self.image_paths[row]
        parsed = self.pick_datetime_override(path)
        if parsed is None:
            return

        self.set_datetime_override_for_path(path, parsed)

    def on_image_table_cell_changed(self, row: int, column: int) -> None:
        if self._updating_table or column != TABLE_COL_OVERRIDE:
            return
        if row < 0 or row >= len(self.image_paths):
            return

        path = self.image_paths[row]
        item = self.image_table.item(row, column)
        text = item.text().strip() if item else ""

        image_settings = self.folder_metadata.get("image_settings")
        if not isinstance(image_settings, dict):
            image_settings = {}
            self.folder_metadata["image_settings"] = image_settings

        existing = image_settings.get(path.name)
        if not isinstance(existing, dict):
            existing = {}

        if text:
            parsed = parse_datetime_override(text)
            if parsed is None:
                QMessageBox.warning(
                    self,
                    "Invalid date/time",
                    "Use YYYY-MM-DD HH:MM (or YYYY-MM-DD).",
                )
                self.refresh_image_list_labels(path)
                return
            existing["datetime_override"] = parsed.isoformat(timespec="seconds")
        else:
            existing.pop("datetime_override", None)

        self.set_image_entry_file_hash(path, existing)
        image_settings[path.name] = existing
        self.save_folder_metadata()
        if self.selected_path() == path:
            dt_value = str(existing.get("datetime_override", ""))
            self.datetime_override_label.setText(dt_value if dt_value else "Auto")
            self.refresh_preview()
        self.refresh_image_list_labels(path)

    def select_previous(self) -> None:
        if not self.image_paths:
            return
        self.image_table.setCurrentCell(max(0, self.image_table.currentRow() - 1), 0)

    def select_next(self) -> None:
        if not self.image_paths:
            return
        self.image_table.setCurrentCell(
            min(len(self.image_paths) - 1, self.image_table.currentRow() + 1),
            TABLE_COL_FILE,
        )

    def populate_printers_combo(self, combo: QComboBox) -> None:
        current = combo.currentText()
        combo.clear()
        if not self.printer_names_cache:
            printers = QPrinterInfo.availablePrinters()
            self.printer_names_cache = [printer.printerName() for printer in printers]
        combo.addItems(self.printer_names_cache)
        if current:
            idx = combo.findText(current)
            if idx >= 0:
                combo.setCurrentIndex(idx)

    def parse_cups_options(
        self, output: str
    ) -> tuple[dict[str, list[str]], dict[str, str]]:
        return parse_cups_options_output(output)

    def is_cups_available(self) -> bool:
        return os.name == "posix" and shutil.which("lp") and shutil.which("lpoptions")

    def get_cups_capabilities(
        self, printer_name: str
    ) -> tuple[dict[str, list[str]], dict[str, str]]:
        if not printer_name or not self.is_cups_available():
            empty = {key: [] for key in CUPS_KEYS}
            defaults = {
                "media": "media",
                "media-type": "media-type",
                "print-quality": "print-quality",
            }
            return empty, defaults

        cached = self.cups_capabilities_cache.get(printer_name)
        if cached is not None:
            return cached

        try:
            result = subprocess.run(
                ["lpoptions", "-p", printer_name, "-l"],
                capture_output=True,
                text=True,
                check=False,
            )
        except OSError:
            empty = {key: [] for key in CUPS_KEYS}
            defaults = {
                "media": "media",
                "media-type": "media-type",
                "print-quality": "print-quality",
            }
            return empty, defaults

        if result.returncode != 0:
            empty = {key: [] for key in CUPS_KEYS}
            defaults = {
                "media": "media",
                "media-type": "media-type",
                "print-quality": "print-quality",
            }
            return empty, defaults

        parsed = self.parse_cups_options(result.stdout)
        self.cups_capabilities_cache[printer_name] = parsed
        return parsed

    def open_project_settings_dialog(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("Settings")
        dialog.setModal(True)
        dialog.resize(1240, 820)

        preview_source_path: Path | None = None
        preview_source_image: Image.Image | None = None

        def placeholder_preview_image() -> Image.Image:
            placeholder = Image.new("RGB", (1600, 1000), "#253341")
            draw = ImageDraw.Draw(placeholder)
            draw.rectangle((0, 0, 1600, 520), fill="#2f4858")
            draw.polygon([(0, 760), (420, 460), (860, 760)], fill="#455a64")
            draw.polygon([(620, 760), (1040, 400), (1600, 760)], fill="#546e7a")
            draw.ellipse((1210, 120, 1360, 270), fill="#ffe082")
            draw.rectangle((0, 760, 1600, 1000), fill="#37474f")
            return placeholder

        if self.image_paths:
            preview_source_path = random.choice(self.image_paths)
            try:
                with Image.open(preview_source_path) as source:
                    preview_source_image = source.convert("RGB")
            except OSError:
                preview_source_image = None

        if preview_source_image is None:
            preview_source_image = placeholder_preview_image()

        original_values = {
            "crop_ratio_value": self.crop_ratio_value,
            "stamp_mode_value": self.stamp_mode_value,
            "clock_mode_value": self.clock_mode_value,
            "corner_landscape_value": self.corner_landscape_value,
            "corner_portrait_value": self.corner_portrait_value,
            "stamp_font_value": self.stamp_font_value,
            "stamp_scale_percent": self.stamp_scale_percent,
            "stamp_offset_x_px": self.stamp_offset_x_px,
            "stamp_offset_y_px": self.stamp_offset_y_px,
            "stamp_vertical_value": self.stamp_vertical_value,
            "stamp_color_value": self.stamp_color_value,
            "stamp_border_color_value": self.stamp_border_color_value,
        }

        layout = QVBoxLayout(dialog)
        info_label = QLabel("These settings are saved for this app.", dialog)
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        content_layout = QHBoxLayout()
        layout.addLayout(content_layout, 1)

        controls_container = QWidget(dialog)
        controls_container.setMinimumWidth(620)
        form = QFormLayout()
        controls_container.setLayout(form)

        preview_container = QWidget(dialog)
        preview_layout = QVBoxLayout(preview_container)
        preview_layout.setContentsMargins(0, 0, 0, 0)
        preview_title = QLabel("Stamp Preview", dialog)
        preview_title.setStyleSheet("font-weight: 600;")
        preview_layout.addWidget(preview_title)
        preview_source_label = QLabel(
            (
                f"Source: {preview_source_path.name}"
                if preview_source_path is not None
                else "Source: placeholder"
            ),
            dialog,
        )
        preview_source_label.setStyleSheet("color: #9CA3AF;")
        preview_layout.addWidget(preview_source_label)
        preview_random_button = QPushButton("Randomize Preview", dialog)
        preview_random_button.setEnabled(bool(self.image_paths))
        preview_layout.addWidget(preview_random_button)
        preview_label = QLabel(dialog)
        preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview_label.setMinimumSize(520, 360)
        preview_label.setStyleSheet("background: #111; border: 1px solid #2f2f2f;")
        preview_layout.addWidget(preview_label, 1)

        content_layout.addWidget(controls_container, 3)
        content_layout.addWidget(preview_container, 2)

        def section_label(text: str) -> QLabel:
            label = QLabel(text, dialog)
            label.setStyleSheet("font-weight: 600;")
            return label

        crop_ratio_combo = QComboBox(dialog)
        for ratio in CROP_RATIOS:
            crop_ratio_combo.addItem(CROP_RATIO_LABELS.get(ratio, ratio), ratio)
        ratio_index = crop_ratio_combo.findData(self.crop_ratio_value)
        crop_ratio_combo.setCurrentIndex(ratio_index if ratio_index >= 0 else 0)

        stamp_mode_combo = QComboBox(dialog)
        stamp_mode_combo.addItems(["None", "Date", "Date + Time"])
        stamp_mode_combo.setCurrentText(self.stamp_mode_value)

        clock_mode_combo = QComboBox(dialog)
        clock_mode_combo.addItems(["24h", "12h"])
        clock_mode_combo.setCurrentText(self.clock_mode_value)

        corner_landscape_combo = QComboBox(dialog)
        corner_landscape_combo.addItems(
            ["Bottom Right", "Bottom Left", "Top Right", "Top Left"]
        )
        corner_landscape_combo.setCurrentText(self.corner_landscape_value)

        corner_portrait_combo = QComboBox(dialog)
        corner_portrait_combo.addItems(
            ["Bottom Right", "Bottom Left", "Top Right", "Top Left"]
        )
        corner_portrait_combo.setCurrentText(self.corner_portrait_value)

        stamp_font_combo = QComboBox(dialog)
        stamp_font_combo.addItems(list(STAMP_FONTS.keys()))
        stamp_font_combo.setCurrentText(self.stamp_font_value)

        stamp_scale_slider = QSlider(Qt.Orientation.Horizontal, dialog)
        stamp_scale_slider.setRange(STAMP_SCALE_MIN_PERCENT, STAMP_SCALE_MAX_PERCENT)
        stamp_scale_slider.setValue(self.stamp_scale_percent)
        stamp_scale_label = QLabel(f"{self.stamp_scale_percent}%", dialog)
        stamp_scale_spin = QSpinBox(dialog)
        stamp_scale_spin.setRange(STAMP_SCALE_MIN_PERCENT, STAMP_SCALE_MAX_PERCENT)
        stamp_scale_spin.setSuffix("%")
        stamp_scale_spin.setValue(self.stamp_scale_percent)
        stamp_scale_slider.valueChanged.connect(
            lambda value: stamp_scale_label.setText(f"{value}%")
        )
        stamp_scale_slider.valueChanged.connect(
            lambda value: (
                stamp_scale_spin.blockSignals(True),
                stamp_scale_spin.setValue(value),
                stamp_scale_spin.blockSignals(False),
            )
        )
        stamp_scale_spin.valueChanged.connect(stamp_scale_slider.setValue)
        stamp_scale_row = QWidget(dialog)
        stamp_scale_layout = QHBoxLayout(stamp_scale_row)
        stamp_scale_layout.setContentsMargins(0, 0, 0, 0)
        stamp_scale_layout.addWidget(stamp_scale_slider)
        stamp_scale_layout.addWidget(stamp_scale_label)
        stamp_scale_layout.addWidget(stamp_scale_spin)

        stamp_offset_x_slider = QSlider(Qt.Orientation.Horizontal, dialog)
        stamp_offset_x_slider.setRange(STAMP_OFFSET_MIN_PX, STAMP_OFFSET_MAX_PX)
        stamp_offset_x_slider.setValue(self.stamp_offset_x_px)
        stamp_offset_x_label = QLabel(f"{self.stamp_offset_x_px / 10:.1f}%", dialog)
        stamp_offset_x_spin = QDoubleSpinBox(dialog)
        stamp_offset_x_spin.setRange(
            STAMP_OFFSET_MIN_PX / 10.0,
            STAMP_OFFSET_MAX_PX / 10.0,
        )
        stamp_offset_x_spin.setSingleStep(0.1)
        stamp_offset_x_spin.setDecimals(1)
        stamp_offset_x_spin.setSuffix("%")
        stamp_offset_x_spin.setValue(self.stamp_offset_x_px / 10.0)
        stamp_offset_x_slider.valueChanged.connect(
            lambda value: stamp_offset_x_label.setText(f"{value / 10:.1f}%")
        )
        stamp_offset_x_slider.valueChanged.connect(
            lambda value: (
                stamp_offset_x_spin.blockSignals(True),
                stamp_offset_x_spin.setValue(value / 10.0),
                stamp_offset_x_spin.blockSignals(False),
            )
        )
        stamp_offset_x_spin.valueChanged.connect(
            lambda value: stamp_offset_x_slider.setValue(int(round(value * 10)))
        )
        stamp_offset_x_row = QWidget(dialog)
        stamp_offset_x_layout = QHBoxLayout(stamp_offset_x_row)
        stamp_offset_x_layout.setContentsMargins(0, 0, 0, 0)
        stamp_offset_x_layout.addWidget(stamp_offset_x_slider)
        stamp_offset_x_layout.addWidget(stamp_offset_x_label)
        stamp_offset_x_layout.addWidget(stamp_offset_x_spin)

        stamp_offset_y_slider = QSlider(Qt.Orientation.Horizontal, dialog)
        stamp_offset_y_slider.setRange(STAMP_OFFSET_MIN_PX, STAMP_OFFSET_MAX_PX)
        stamp_offset_y_slider.setValue(self.stamp_offset_y_px)
        stamp_offset_y_label = QLabel(f"{self.stamp_offset_y_px / 10:.1f}%", dialog)
        stamp_offset_y_spin = QDoubleSpinBox(dialog)
        stamp_offset_y_spin.setRange(
            STAMP_OFFSET_MIN_PX / 10.0,
            STAMP_OFFSET_MAX_PX / 10.0,
        )
        stamp_offset_y_spin.setSingleStep(0.1)
        stamp_offset_y_spin.setDecimals(1)
        stamp_offset_y_spin.setSuffix("%")
        stamp_offset_y_spin.setValue(self.stamp_offset_y_px / 10.0)
        stamp_offset_y_slider.valueChanged.connect(
            lambda value: stamp_offset_y_label.setText(f"{value / 10:.1f}%")
        )
        stamp_offset_y_slider.valueChanged.connect(
            lambda value: (
                stamp_offset_y_spin.blockSignals(True),
                stamp_offset_y_spin.setValue(value / 10.0),
                stamp_offset_y_spin.blockSignals(False),
            )
        )
        stamp_offset_y_spin.valueChanged.connect(
            lambda value: stamp_offset_y_slider.setValue(int(round(value * 10)))
        )
        stamp_offset_y_row = QWidget(dialog)
        stamp_offset_y_layout = QHBoxLayout(stamp_offset_y_row)
        stamp_offset_y_layout.setContentsMargins(0, 0, 0, 0)
        stamp_offset_y_layout.addWidget(stamp_offset_y_slider)
        stamp_offset_y_layout.addWidget(stamp_offset_y_label)
        stamp_offset_y_layout.addWidget(stamp_offset_y_spin)

        stamp_vertical_checkbox = QCheckBox("Vertical stamp", dialog)
        stamp_vertical_checkbox.setChecked(self.stamp_vertical_value)

        stamp_color_button = QPushButton(dialog)
        stamp_color_reset_button = QPushButton("Reset", dialog)
        stamp_color_value = self.stamp_color_value
        stamp_border_color_button = QPushButton(dialog)
        stamp_border_color_reset_button = QPushButton("Reset", dialog)
        stamp_border_color_value = self.stamp_border_color_value

        def update_stamp_color_button() -> None:
            nonlocal stamp_color_value
            color = QColor(stamp_color_value)
            if not color.isValid():
                color = QColor(DEFAULT_STAMP_COLOR)
                stamp_color_value = color.name().upper()
            text_color = "#000000" if color.lightness() > 128 else "#FFFFFF"
            stamp_color_button.setText(stamp_color_value)
            stamp_color_button.setStyleSheet(
                f"background-color: {stamp_color_value}; color: {text_color};"
            )

        def pick_stamp_color() -> None:
            nonlocal stamp_color_value
            selected = QColorDialog.getColor(QColor(stamp_color_value), dialog)
            if not selected.isValid():
                return
            stamp_color_value = selected.name().upper()
            update_stamp_color_button()

        def reset_stamp_color() -> None:
            nonlocal stamp_color_value
            stamp_color_value = DEFAULT_STAMP_COLOR
            update_stamp_color_button()

        def update_stamp_border_color_button() -> None:
            nonlocal stamp_border_color_value
            color = QColor(stamp_border_color_value)
            if not color.isValid():
                color = QColor(DEFAULT_STAMP_BORDER_COLOR)
                stamp_border_color_value = color.name().upper()
            text_color = "#000000" if color.lightness() > 128 else "#FFFFFF"
            stamp_border_color_button.setText(stamp_border_color_value)
            stamp_border_color_button.setStyleSheet(
                f"background-color: {stamp_border_color_value}; color: {text_color};"
            )

        def pick_stamp_border_color() -> None:
            nonlocal stamp_border_color_value
            selected = QColorDialog.getColor(QColor(stamp_border_color_value), dialog)
            if not selected.isValid():
                return
            stamp_border_color_value = selected.name().upper()
            update_stamp_border_color_button()

        def reset_stamp_border_color() -> None:
            nonlocal stamp_border_color_value
            stamp_border_color_value = DEFAULT_STAMP_BORDER_COLOR
            update_stamp_border_color_button()

        stamp_color_button.clicked.connect(pick_stamp_color)
        stamp_color_reset_button.clicked.connect(reset_stamp_color)
        stamp_border_color_button.clicked.connect(pick_stamp_border_color)
        stamp_border_color_reset_button.clicked.connect(reset_stamp_border_color)
        update_stamp_color_button()
        update_stamp_border_color_button()

        def apply_dialog_preview_values() -> None:
            self.crop_ratio_value = str(crop_ratio_combo.currentData() or "2:3")
            self.stamp_mode_value = stamp_mode_combo.currentText()
            self.clock_mode_value = clock_mode_combo.currentText()
            self.corner_landscape_value = corner_landscape_combo.currentText()
            self.corner_portrait_value = corner_portrait_combo.currentText()
            self.stamp_font_value = stamp_font_combo.currentText()
            self.stamp_scale_percent = stamp_scale_slider.value()
            self.stamp_offset_x_px = stamp_offset_x_slider.value()
            self.stamp_offset_y_px = stamp_offset_y_slider.value()
            self.stamp_vertical_value = stamp_vertical_checkbox.isChecked()
            self.stamp_color_value = stamp_color_value
            self.stamp_border_color_value = stamp_border_color_value
            self.refresh_preview()
            update_settings_stamp_preview()

        def update_settings_stamp_preview() -> None:
            if preview_source_image is None:
                return

            image = preview_source_image.copy()
            max_w = 1000
            max_h = 700
            scale = min(max_w / image.width, max_h / image.height, 1.0)
            if scale < 1.0:
                image = image.resize(
                    (int(image.width * scale), int(image.height * scale)),
                    Image.Resampling.LANCZOS,
                )

            orientation = "Portrait" if image.height > image.width else "Landscape"
            corner = (
                corner_portrait_combo.currentText()
                if orientation == "Portrait"
                else corner_landscape_combo.currentText()
            )
            stamp_mode = stamp_mode_combo.currentText()
            clock_mode = clock_mode_combo.currentText()

            stamp_text_value = ""
            if stamp_mode == "Date":
                stamp_text_value = "2026-02-16"
            elif stamp_mode == "Date + Time":
                if clock_mode == "12h":
                    stamp_text_value = "2026-02-16 02:35 PM"
                else:
                    stamp_text_value = "2026-02-16 14:35"

            settings_preview = ProcessingSettings(
                orientation=orientation,
                stamp_mode=stamp_mode,
                clock_mode=clock_mode,
                corner=corner,
                stamp_font=stamp_font_combo.currentText(),
                stamp_scale_percent=stamp_scale_slider.value(),
                stamp_offset_x_px=stamp_offset_x_slider.value(),
                stamp_offset_y_px=stamp_offset_y_slider.value(),
                stamp_color=stamp_color_value,
                stamp_border_color=stamp_border_color_value,
                stamp_vertical=stamp_vertical_checkbox.isChecked(),
            )
            image = apply_stamp(image, stamp_text_value, settings_preview)

            pixmap = QPixmap.fromImage(QImage(ImageQt(image)))
            scaled = pixmap.scaled(
                max(180, preview_label.width()),
                max(140, preview_label.height()),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            preview_label.setPixmap(scaled)

        def randomize_preview_source() -> None:
            nonlocal preview_source_path, preview_source_image
            if not self.image_paths:
                return

            candidates = [
                path for path in self.image_paths if path != preview_source_path
            ]
            if not candidates:
                candidates = list(self.image_paths)

            chosen = random.choice(candidates)
            try:
                with Image.open(chosen) as source:
                    preview_source_image = source.convert("RGB")
                preview_source_path = chosen
                preview_source_label.setText(f"Source: {chosen.name}")
            except OSError:
                preview_source_path = None
                preview_source_image = placeholder_preview_image()
                preview_source_label.setText("Source: placeholder")

            update_settings_stamp_preview()

        preview_random_button.clicked.connect(randomize_preview_source)

        stamp_color_row = QWidget(dialog)
        stamp_color_layout = QHBoxLayout(stamp_color_row)
        stamp_color_layout.setContentsMargins(0, 0, 0, 0)
        stamp_color_layout.addWidget(stamp_color_button)
        stamp_color_layout.addWidget(stamp_color_reset_button)
        stamp_border_color_row = QWidget(dialog)
        stamp_border_color_layout = QHBoxLayout(stamp_border_color_row)
        stamp_border_color_layout.setContentsMargins(0, 0, 0, 0)
        stamp_border_color_layout.addWidget(stamp_border_color_button)
        stamp_border_color_layout.addWidget(stamp_border_color_reset_button)
        clear_image_settings_btn = QPushButton("Clear All Image Settings", dialog)

        crop_ratio_combo.currentIndexChanged.connect(
            lambda _value: apply_dialog_preview_values()
        )
        stamp_mode_combo.currentIndexChanged.connect(
            lambda _value: apply_dialog_preview_values()
        )
        clock_mode_combo.currentIndexChanged.connect(
            lambda _value: apply_dialog_preview_values()
        )
        corner_landscape_combo.currentIndexChanged.connect(
            lambda _value: apply_dialog_preview_values()
        )
        corner_portrait_combo.currentIndexChanged.connect(
            lambda _value: apply_dialog_preview_values()
        )
        stamp_font_combo.currentIndexChanged.connect(
            lambda _value: apply_dialog_preview_values()
        )
        stamp_scale_slider.valueChanged.connect(
            lambda _value: apply_dialog_preview_values()
        )
        stamp_offset_x_slider.valueChanged.connect(
            lambda _value: apply_dialog_preview_values()
        )
        stamp_offset_y_slider.valueChanged.connect(
            lambda _value: apply_dialog_preview_values()
        )
        stamp_vertical_checkbox.toggled.connect(
            lambda _checked: apply_dialog_preview_values()
        )

        original_pick_stamp_color = pick_stamp_color

        def pick_stamp_color_with_preview() -> None:
            original_pick_stamp_color()
            apply_dialog_preview_values()

        stamp_color_button.clicked.disconnect()
        stamp_color_button.clicked.connect(pick_stamp_color_with_preview)

        original_reset_stamp_color = reset_stamp_color

        def reset_stamp_color_with_preview() -> None:
            original_reset_stamp_color()
            apply_dialog_preview_values()

        stamp_color_reset_button.clicked.disconnect()
        stamp_color_reset_button.clicked.connect(reset_stamp_color_with_preview)

        original_pick_stamp_border_color = pick_stamp_border_color

        def pick_stamp_border_color_with_preview() -> None:
            original_pick_stamp_border_color()
            apply_dialog_preview_values()

        stamp_border_color_button.clicked.disconnect()
        stamp_border_color_button.clicked.connect(pick_stamp_border_color_with_preview)

        original_reset_stamp_border_color = reset_stamp_border_color

        def reset_stamp_border_color_with_preview() -> None:
            original_reset_stamp_border_color()
            apply_dialog_preview_values()

        stamp_border_color_reset_button.clicked.disconnect()
        stamp_border_color_reset_button.clicked.connect(
            reset_stamp_border_color_with_preview
        )

        def clear_all_image_settings() -> None:
            if self.current_folder is None:
                QMessageBox.information(
                    self,
                    "No folder loaded",
                    "Load a folder first before clearing image settings.",
                )
                return

            reply = QMessageBox.question(
                self,
                "Clear image settings",
                "Clear all per-image settings for this folder?\n"
                "This removes crop/brightness/date overrides for all photos.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

            self.folder_metadata["image_settings"] = {}
            self.save_folder_metadata()
            self.refresh_image_list_labels(self.selected_path())
            self.restore_image_settings_for_selected()
            self.refresh_preview()
            QMessageBox.information(
                self,
                "Image settings cleared",
                "All per-image settings in this folder were reset.",
            )

        clear_image_settings_btn.clicked.connect(clear_all_image_settings)

        form.addRow(section_label("Crop & Layout"), QLabel("", dialog))
        form.addRow("Crop Ratio", crop_ratio_combo)
        form.addRow(section_label("Stamp"), QLabel("", dialog))
        form.addRow("Stamp", stamp_mode_combo)
        form.addRow("Time Format", clock_mode_combo)
        form.addRow("Corner (Landscape)", corner_landscape_combo)
        form.addRow("Corner (Portrait)", corner_portrait_combo)
        form.addRow("Stamp Font", stamp_font_combo)
        form.addRow("Stamp Size", stamp_scale_row)
        form.addRow("Stamp Offset X", stamp_offset_x_row)
        form.addRow("Stamp Offset Y", stamp_offset_y_row)
        form.addRow("Text Direction", stamp_vertical_checkbox)
        form.addRow("Stamp Color", stamp_color_row)
        form.addRow("Border Color", stamp_border_color_row)
        form.addRow(section_label("Folder Actions"), QLabel("", dialog))
        form.addRow("", clear_image_settings_btn)
        update_settings_stamp_preview()

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            parent=dialog,
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            self.crop_ratio_value = str(original_values["crop_ratio_value"])
            self.stamp_mode_value = str(original_values["stamp_mode_value"])
            self.clock_mode_value = str(original_values["clock_mode_value"])
            self.corner_landscape_value = str(original_values["corner_landscape_value"])
            self.corner_portrait_value = str(original_values["corner_portrait_value"])
            self.stamp_font_value = str(original_values["stamp_font_value"])
            self.stamp_scale_percent = int(original_values["stamp_scale_percent"])
            self.stamp_offset_x_px = int(original_values["stamp_offset_x_px"])
            self.stamp_offset_y_px = int(original_values["stamp_offset_y_px"])
            self.stamp_vertical_value = bool(original_values["stamp_vertical_value"])
            self.stamp_color_value = str(original_values["stamp_color_value"])
            self.stamp_border_color_value = str(
                original_values["stamp_border_color_value"]
            )
            self.refresh_preview()
            return

        self.crop_ratio_value = str(crop_ratio_combo.currentData() or "2:3")
        self.stamp_mode_value = stamp_mode_combo.currentText()
        self.clock_mode_value = clock_mode_combo.currentText()
        self.corner_landscape_value = corner_landscape_combo.currentText()
        self.corner_portrait_value = corner_portrait_combo.currentText()
        self.stamp_font_value = stamp_font_combo.currentText()
        self.stamp_scale_percent = stamp_scale_slider.value()
        self.stamp_offset_x_px = stamp_offset_x_slider.value()
        self.stamp_offset_y_px = stamp_offset_y_slider.value()
        self.stamp_vertical_value = stamp_vertical_checkbox.isChecked()
        self.stamp_color_value = stamp_color_value
        self.stamp_border_color_value = stamp_border_color_value

        preferred = self.selected_path()
        self.apply_sort_order(preferred)
        self.persist_project_settings()
        self.refresh_preview()

    def open_print_settings_dialog(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("Printer Settings")
        dialog.setModal(True)
        dialog.resize(820, 560)

        layout = QVBoxLayout(dialog)
        info_label = QLabel("These settings apply globally across folders.", dialog)
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        form = QFormLayout()

        def section_label(text: str) -> QLabel:
            label = QLabel(text, dialog)
            label.setStyleSheet("font-weight: 600;")
            return label

        backend_combo = QComboBox(dialog)
        backend_combo.addItems(PRINT_BACKENDS)
        backend_combo.setCurrentText(self.print_backend_value)

        ipp_uri_edit = QLineEdit(dialog)
        ipp_uri_edit.setPlaceholderText("ipps://EPSON1234.local:631/ipp/print")
        ipp_uri_edit.setText(self.ipp_uri_value)
        ipp_uri_label: QWidget | None = None
        ipp_test_button = QPushButton("Test IPP Connection", dialog)

        ipp_send_mode_combo = QComboBox(dialog)
        ipp_send_mode_combo.addItem("Wait for completion (sequential)", True)
        ipp_send_mode_combo.addItem("Queue only (faster)", False)
        mode_index = ipp_send_mode_combo.findData(self.ipp_wait_for_completion_value)
        ipp_send_mode_combo.setCurrentIndex(mode_index if mode_index >= 0 else 0)

        printer_combo = QComboBox(dialog)
        self.populate_printers_combo(printer_combo)
        if self.printer_value:
            printer_combo.setCurrentText(self.printer_value)

        refresh_printers_btn = QPushButton("Refresh Printers", dialog)

        borderless_combo = QComboBox(dialog)
        borderless_combo.addItem("Driver default", "default")
        borderless_combo.addItem("Enabled", "enabled")
        borderless_combo.addItem("Disabled", "disabled")
        borderless_index = borderless_combo.findData(self.borderless_mode_value)
        borderless_combo.setCurrentIndex(
            borderless_index if borderless_index >= 0 else 1
        )

        borderless_scale_slider = QSlider(Qt.Orientation.Horizontal, dialog)
        borderless_scale_slider.setRange(85, 110)
        borderless_scale_slider.setValue(self.borderless_content_scale_percent)
        borderless_scale_slider.setMinimumWidth(260)
        borderless_scale_spin = QSpinBox(dialog)
        borderless_scale_spin.setRange(85, 110)
        borderless_scale_spin.setSuffix("%")
        borderless_scale_spin.setValue(self.borderless_content_scale_percent)
        borderless_scale_slider.valueChanged.connect(
            lambda value: (
                borderless_scale_spin.blockSignals(True),
                borderless_scale_spin.setValue(value),
                borderless_scale_spin.blockSignals(False),
            )
        )
        borderless_scale_spin.valueChanged.connect(
            lambda value: borderless_scale_slider.setValue(int(value))
        )
        borderless_scale_row = QWidget(dialog)
        borderless_scale_layout = QHBoxLayout(borderless_scale_row)
        borderless_scale_layout.setContentsMargins(0, 0, 0, 0)
        borderless_scale_layout.addWidget(borderless_scale_slider)
        borderless_scale_layout.addWidget(borderless_scale_spin)

        ipp_caps_for_dialog: IppCapabilities | None = None

        def update_borderless_control() -> None:
            if backend_combo.currentText() != "IPP":
                selected_media = str(cups_media_combo.currentData() or "")
                if is_explicit_borderless_media(selected_media):
                    enabled_index = borderless_combo.findData("enabled")
                    if enabled_index >= 0:
                        borderless_combo.setCurrentIndex(enabled_index)
                    borderless_combo.setEnabled(False)
                    borderless_combo.setToolTip(
                        "Selected media is already a borderless variant."
                    )
                    borderless_scale_slider.setEnabled(True)
                    borderless_scale_slider.setToolTip(
                        "Compensate printer borderless expansion by shrinking content."
                    )
                    return

                borderless_combo.setEnabled(True)
                borderless_combo.setToolTip("")
                borderless_scale_slider.setEnabled(
                    str(borderless_combo.currentData() or "") == "enabled"
                )
                borderless_scale_slider.setToolTip(
                    "Only used when Borderless is enabled for CUPS/Auto."
                )
                return

            caps = ipp_caps_for_dialog

            if caps is None:
                borderless_combo.setEnabled(False)
                borderless_combo.setToolTip(
                    "Connect to IPP printer first to detect borderless support."
                )
                borderless_scale_slider.setEnabled(False)
                borderless_scale_slider.setToolTip(
                    "Only used for CUPS/Auto borderless compensation."
                )
                return

            if caps.borderless_zero_margins_supported:
                borderless_combo.setEnabled(True)
                borderless_combo.setToolTip("")
                borderless_scale_slider.setEnabled(False)
                borderless_scale_slider.setToolTip(
                    "Only used for CUPS/Auto borderless compensation."
                )
                return

            disabled_index = borderless_combo.findData("disabled")
            if disabled_index >= 0:
                borderless_combo.setCurrentIndex(disabled_index)
            borderless_combo.setEnabled(False)
            borderless_combo.setToolTip(
                "This IPP printer does not advertise 0-margin borderless support."
            )
            borderless_scale_slider.setEnabled(False)
            borderless_scale_slider.setToolTip(
                "Only used for CUPS/Auto borderless compensation."
            )

        ipp_printer_name_value = ""

        def update_printer_combo_for_backend() -> None:
            backend = backend_combo.currentText()
            if backend == "IPP":
                printer_combo.clear()
                printer_combo.addItem(ipp_printer_name_value or "(unknown)")
                printer_combo.setEnabled(False)
                refresh_printers_btn.setEnabled(False)
            else:
                current = self.printer_value
                self.populate_printers_combo(printer_combo)
                if current:
                    printer_combo.setCurrentText(current)
                printer_combo.setEnabled(True)
                refresh_printers_btn.setEnabled(True)

        cups_media_combo = QComboBox(dialog)
        cups_media_type_combo = QComboBox(dialog)
        cups_quality_combo = QComboBox(dialog)
        calibration_button = QPushButton("Print Borderless Calibration", dialog)
        cups_media_key_value = self.cups_media_key
        cups_media_type_key_value = self.cups_media_type_key
        cups_print_quality_key_value = self.cups_print_quality_key

        def fill_cups_combo(
            combo: QComboBox, kind: str, options: list[str], selected: str
        ) -> None:
            combo.clear()
            combo.addItem("(Driver default)", "")
            for option in options:
                combo.addItem(pretty_option_label(kind, option), option)
            idx = combo.findData(selected)
            combo.setCurrentIndex(idx if idx >= 0 else 0)
            combo.setEnabled(combo.count() > 1)

        def set_cups_placeholder(message: str = "(Load options to view)") -> None:
            cups_media_combo.clear()
            cups_media_combo.addItem(message, "")
            cups_media_type_combo.clear()
            cups_media_type_combo.addItem(message, "")
            cups_quality_combo.clear()
            cups_quality_combo.addItem(message, "")
            cups_media_combo.setEnabled(False)
            cups_media_type_combo.setEnabled(False)
            cups_quality_combo.setEnabled(False)

        def update_backend_visibility() -> None:
            backend = backend_combo.currentText()
            show_printer = backend in {"Auto", "CUPS", "IPP"}
            printer_combo.setVisible(show_printer)
            refresh_printers_btn.setVisible(show_printer)

            show_ipp = backend == "IPP"
            ipp_uri_edit.setVisible(show_ipp)
            ipp_test_button.setVisible(show_ipp)
            ipp_send_mode_combo.setVisible(show_ipp)
            if ipp_uri_label is not None:
                ipp_uri_label.setVisible(show_ipp)

            update_printer_combo_for_backend()

            show_cups_options = backend in {"Auto", "CUPS", "IPP"}
            cups_media_combo.setVisible(show_cups_options)
            cups_media_type_combo.setVisible(show_cups_options)
            cups_quality_combo.setVisible(show_cups_options)

        def update_cups_controls() -> None:
            nonlocal cups_media_key_value, cups_media_type_key_value
            nonlocal cups_print_quality_key_value
            nonlocal ipp_printer_name_value
            nonlocal ipp_caps_for_dialog
            if backend_combo.currentText() == "IPP":
                ipp_uri = ipp_uri_edit.text().strip()
                caps = self.ipp_capabilities_cache.get(ipp_uri)
                try:
                    if caps is None and ipp_uri:
                        caps = get_ipp_capabilities(ipp_uri)
                        self.ipp_capabilities_cache[ipp_uri] = caps
                except IppBackendError:
                    caps = None
                    if ipp_uri:
                        self.ipp_capabilities_cache[ipp_uri] = None

                if caps is None:
                    ipp_caps_for_dialog = None
                    ipp_printer_name_value = ""
                    update_printer_combo_for_backend()
                    update_borderless_control()
                    cups_media_combo.clear()
                    cups_media_combo.addItem("(IPP unavailable)", "")
                    cups_media_type_combo.clear()
                    cups_media_type_combo.addItem("(IPP unavailable)", "")
                    cups_quality_combo.clear()
                    cups_quality_combo.addItem("(IPP unavailable)", "")
                    cups_media_combo.setEnabled(False)
                    cups_media_type_combo.setEnabled(False)
                    cups_quality_combo.setEnabled(False)
                else:
                    ipp_caps_for_dialog = caps
                    ipp_printer_name_value = caps.printer_name.strip()
                    update_printer_combo_for_backend()
                    update_borderless_control()
                    fill_cups_combo(
                        cups_media_combo,
                        "media",
                        caps.media,
                        self.cups_media_value,
                    )
                    fill_cups_combo(
                        cups_media_type_combo,
                        "media-type",
                        caps.media_type,
                        self.cups_media_type_value,
                    )
                    fill_cups_combo(
                        cups_quality_combo,
                        "quality",
                        [str(value) for value in caps.print_quality],
                        self.cups_print_quality_value,
                    )
                return

            ipp_caps_for_dialog = None
            update_borderless_control()

            caps, resolved_keys = self.get_cups_capabilities(
                printer_combo.currentText()
            )
            cups_media_key_value = resolved_keys.get("media", cups_media_key_value)
            cups_media_type_key_value = resolved_keys.get(
                "media-type", cups_media_type_key_value
            )
            cups_print_quality_key_value = resolved_keys.get(
                "print-quality", cups_print_quality_key_value
            )
            fill_cups_combo(
                cups_media_combo,
                "media",
                caps.get("media", []),
                self.cups_media_value,
            )
            fill_cups_combo(
                cups_media_type_combo,
                "media-type",
                caps.get("media-type", []),
                self.cups_media_type_value,
            )
            fill_cups_combo(
                cups_quality_combo,
                "quality",
                caps.get("print-quality", []),
                self.cups_print_quality_value,
            )

        def test_ipp_connection() -> None:
            nonlocal ipp_printer_name_value
            nonlocal ipp_caps_for_dialog
            uri = ipp_uri_edit.text().strip()
            if not uri:
                QMessageBox.warning(
                    dialog,
                    "No IPP URI",
                    "Enter an IPP/IPPS URI first.",
                )
                return
            if backend_combo.currentText() != "IPP":
                QMessageBox.information(
                    dialog,
                    "IPP backend not selected",
                    "Select Print Backend = IPP to test and load IPP options.",
                )
                return

            try:
                caps = get_ipp_capabilities(uri)
                self.ipp_capabilities_cache[uri] = caps
            except IppBackendError as error:
                self.ipp_capabilities_cache[uri] = None
                QMessageBox.warning(dialog, "IPP connection failed", str(error))
                set_cups_placeholder("(IPP unavailable)")
                return

            ipp_printer_name_value = caps.printer_name.strip()
            ipp_caps_for_dialog = caps
            update_printer_combo_for_backend()
            update_borderless_control()

            fill_cups_combo(
                cups_media_combo,
                "media",
                caps.media,
                self.cups_media_value,
            )
            fill_cups_combo(
                cups_media_type_combo,
                "media-type",
                caps.media_type,
                self.cups_media_type_value,
            )
            fill_cups_combo(
                cups_quality_combo,
                "quality",
                [str(value) for value in caps.print_quality],
                self.cups_print_quality_value,
            )
            QMessageBox.information(
                dialog,
                "IPP connected",
                f"Connected to {uri}\n"
                f"Printer: {ipp_printer_name_value or '(unknown)'}\n"
                f"Media: {len(caps.media)}\n"
                f"Media Type: {len(caps.media_type)}\n"
                f"Quality: {len(caps.print_quality)}",
            )

        def refresh_printers() -> None:
            current = printer_combo.currentText()
            self.populate_printers_combo(printer_combo)
            if current:
                printer_combo.setCurrentText(current)
            update_cups_controls()

        def print_borderless_calibration() -> None:
            backend = backend_combo.currentText()
            if backend == "IPP":
                QMessageBox.information(
                    dialog,
                    "CUPS required",
                    "Borderless calibration currently uses CUPS queue options. "
                    "Switch backend to CUPS (or Auto with CUPS) first.",
                )
                return

            printer = printer_combo.currentText().strip()
            if not printer:
                QMessageBox.warning(
                    dialog,
                    "No printer",
                    "Select a CUPS printer first.",
                )
                return

            selected_media = str(cups_media_combo.currentData() or "")
            if not selected_media:
                QMessageBox.warning(
                    dialog,
                    "No media",
                    "Select a media size first (for example 4x6.Borderless).",
                )
                return

            effective_media_value = resolve_cups_media_value(
                selected_media,
                self.get_cups_capabilities(printer)[0].get("media", []),
                True,
            )

            scales = [95, 97, 99]
            queued_count, errors = self.print_borderless_calibration_pages(
                printer_name=printer,
                media_value=effective_media_value,
                media_type_value=str(cups_media_type_combo.currentData() or ""),
                print_quality_value=str(cups_quality_combo.currentData() or ""),
                scale_values=scales,
            )

            if queued_count:
                self.append_log(
                    "INFO",
                    "Queued borderless calibration set to "
                    f"{printer}: {queued_count} page(s)",
                )

            if errors:
                QMessageBox.warning(
                    dialog,
                    "Calibration print partial",
                    "Some calibration pages failed:\n\n" + "\n".join(errors[:4]),
                )
                return

            chooser = QMessageBox(dialog)
            chooser.setWindowTitle("Calibration queued")
            chooser.setIcon(QMessageBox.Icon.Information)
            chooser.setText(
                "Queued calibration pages 1/2/3.\n"
                "After you compare prints, choose which page looks best."
            )
            chooser.setInformativeText(
                f"1 | {scales[0]}%   ·   2 | {scales[1]}%   ·   3 | {scales[2]}%\n"
                f"Between 1-2: {(scales[0] + scales[1]) // 2}%   ·   "
                f"Between 2-3: {(scales[1] + scales[2]) // 2}%\n"
                "You can also keep current and decide later."
            )
            mid_12 = (scales[0] + scales[1]) // 2
            mid_23 = (scales[1] + scales[2]) // 2
            button_1 = chooser.addButton(
                f"Use 1 ({scales[0]}%)", QMessageBox.ButtonRole.AcceptRole
            )
            button_12 = chooser.addButton(
                f"Use 1-2 Mid ({mid_12}%)", QMessageBox.ButtonRole.AcceptRole
            )
            button_2 = chooser.addButton(
                f"Use 2 ({scales[1]}%)", QMessageBox.ButtonRole.AcceptRole
            )
            button_23 = chooser.addButton(
                f"Use 2-3 Mid ({mid_23}%)", QMessageBox.ButtonRole.AcceptRole
            )
            button_3 = chooser.addButton(
                f"Use 3 ({scales[2]}%)", QMessageBox.ButtonRole.AcceptRole
            )
            chooser.addButton("Keep current", QMessageBox.ButtonRole.RejectRole)
            chooser.exec()

            chosen_scale: int | None = None
            clicked = chooser.clickedButton()
            if clicked == button_1:
                chosen_scale = scales[0]
            elif clicked == button_2:
                chosen_scale = scales[1]
            elif clicked == button_3:
                chosen_scale = scales[2]
            elif clicked == button_12:
                chosen_scale = mid_12
            elif clicked == button_23:
                chosen_scale = mid_23

            if chosen_scale is not None:
                borderless_scale_slider.setValue(chosen_scale)
                self.append_log(
                    "INFO",
                    "Applied Borderless Content Scale from calibration: "
                    f"{chosen_scale}%",
                )

        refresh_printers_btn.clicked.connect(refresh_printers)
        ipp_test_button.clicked.connect(test_ipp_connection)
        calibration_button.clicked.connect(print_borderless_calibration)
        printer_combo.currentTextChanged.connect(lambda _value: update_cups_controls())
        cups_media_combo.currentIndexChanged.connect(
            lambda _value: update_borderless_control()
        )
        borderless_combo.currentIndexChanged.connect(
            lambda _value: update_borderless_control()
        )
        backend_combo.currentTextChanged.connect(
            lambda _value: (update_backend_visibility(), update_cups_controls())
        )
        ipp_uri_edit.editingFinished.connect(update_cups_controls)
        update_backend_visibility()
        set_cups_placeholder()
        update_borderless_control()

        form.addRow(section_label("Backend"), QLabel("", dialog))
        form.addRow("Print Backend", backend_combo)
        form.addRow("IPP URI", ipp_uri_edit)
        ipp_uri_label = form.labelForField(ipp_uri_edit)
        form.addRow("IPP Send Mode", ipp_send_mode_combo)
        form.addRow("", ipp_test_button)
        form.addRow(section_label("Destination"), QLabel("", dialog))
        form.addRow("Printer", printer_combo)
        form.addRow("", refresh_printers_btn)
        form.addRow(section_label("Driver Options"), QLabel("", dialog))
        form.addRow("Media", cups_media_combo)
        form.addRow("Borderless", borderless_combo)
        form.addRow("Borderless Content Scale", borderless_scale_row)
        form.addRow("Media Type", cups_media_type_combo)
        form.addRow("Quality", cups_quality_combo)
        form.addRow("Calibration", calibration_button)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            parent=dialog,
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        update_cups_controls()

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self.print_backend_value = backend_combo.currentText()
        self.ipp_uri_value = ipp_uri_edit.text().strip()
        self.ipp_wait_for_completion_value = bool(ipp_send_mode_combo.currentData())
        self.printer_value = printer_combo.currentText().strip()
        self.borderless_mode_value = str(borderless_combo.currentData() or "enabled")
        self.borderless_content_scale_percent = borderless_scale_slider.value()
        self.cups_media_value = str(cups_media_combo.currentData() or "")
        self.cups_media_type_value = str(cups_media_type_combo.currentData() or "")
        self.cups_print_quality_value = str(cups_quality_combo.currentData() or "")
        self.cups_media_key = cups_media_key_value
        self.cups_media_type_key = cups_media_type_key_value
        self.cups_print_quality_key = cups_print_quality_key_value
        self.save_app_print_settings()

    def load_folder_path(
        self,
        folder_path: Path,
        open_settings_if_new: bool = True,
        preferred_path: Path | None = None,
    ) -> None:
        if not folder_path.exists():
            QMessageBox.warning(
                self, "Folder Not Found", "Selected folder does not exist"
            )
            return

        metadata_exists = (folder_path / METADATA_FILENAME).exists()

        self.current_folder = folder_path
        self.update_folder_settings_availability()
        self.thumbnail_generation += 1
        self.thumbnail_cache = {}
        self.thumbnail_pending_paths = []
        self.thumbnail_inflight_paths = set()
        self.orientation_cache = {}
        self.file_hash_cache = {}
        self.load_folder_metadata()

        self.image_paths = sorted(
            [
                p
                for p in folder_path.iterdir()
                if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
            ]
        )

        reset_count = self.sync_image_settings_with_files()

        self.apply_sort_order(preferred_path)

        self.append_log(
            "INFO", f"Loaded folder: {folder_path} ({len(self.image_paths)} image(s))"
        )
        if reset_count:
            self.append_log(
                "WARNING",
                f"Reset per-image settings for {reset_count} changed file(s)",
            )

        if not self.image_paths:
            self.current_index = -1
            self.update_controls_visibility()
            self.preview_label.setText("No compatible images in selected folder")
            self.preview_label.setPixmap(QPixmap())
            self.statusBar().showMessage("No images found")
            self.append_log("WARNING", "No compatible images found in selected folder")
            return

        if self.image_table.currentRow() < 0:
            self.image_table.setCurrentCell(0, TABLE_COL_FILE)

        photo_data = self.folder_metadata.get("photos")
        total_printed = 0
        if isinstance(photo_data, dict):
            for entry in photo_data.values():
                if isinstance(entry, dict):
                    total_printed += int(entry.get("total_printed", 0))

        message = f"Loaded {len(self.image_paths)} image(s) from {folder_path}"
        if total_printed:
            message += f". Print history: {total_printed} total prints"
        self.statusBar().showMessage(message)

        if not metadata_exists and open_settings_if_new:
            self.open_project_settings_dialog()

    def load_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select image folder")
        if not folder:
            return

        self.load_folder_path(
            Path(folder), open_settings_if_new=True, preferred_path=None
        )

    def refresh_folder(self) -> None:
        if self.current_folder is None:
            QMessageBox.information(self, "Refresh Folder", "No folder loaded")
            return

        self.load_folder_path(
            self.current_folder,
            open_settings_if_new=False,
            preferred_path=self.selected_path(),
        )
        self.append_log("INFO", f"Refreshed folder: {self.current_folder}")

    def paper_size_mm(self) -> tuple[float, float]:
        paper = self.paper_value
        if paper == "A3":
            return (297.0, 420.0)
        if paper == "A3+":
            return (329.0, 483.0)
        if paper == "A4":
            return (210.0, 297.0)
        if paper == "A4+":
            return (210.0, 330.0)
        return (100.0, 150.0)

    def print_borderless_calibration_pages(
        self,
        printer_name: str,
        media_value: str,
        media_type_value: str,
        print_quality_value: str,
        scale_values: list[int],
    ) -> tuple[int, list[str]]:
        if not printer_name:
            return 0, ["No printer selected"]

        unique_scales: list[int] = []
        for value in scale_values:
            normalized = max(85, min(110, int(value)))
            if normalized not in unique_scales:
                unique_scales.append(normalized)
        if not unique_scales:
            unique_scales = [95, 93, 90]

        media_size = media_size_mm_from_value(media_value)
        if media_size is None:
            media_size = (101.6, 152.4)
        width_mm, height_mm = media_size
        width_px = max(800, int(round(width_mm * 12)))
        height_px = max(800, int(round(height_mm * 12)))

        queued = 0
        errors: list[str] = []

        with tempfile.TemporaryDirectory(prefix="album_printer_cal_") as temp_dir:
            for test_index, scale_percent in enumerate(unique_scales, start=1):
                file_name = f"borderless-calibration-{test_index}-{scale_percent}.jpg"
                out = Path(temp_dir) / file_name
                image = create_borderless_calibration_image(
                    width_px,
                    height_px,
                    scale_percent,
                    str(test_index),
                )
                image = apply_borderless_content_scale(image, scale_percent)
                image.save(out, format="JPEG", quality=95, optimize=True)

                command = ["lp", "-d", printer_name]
                if media_value:
                    command.extend(["-o", f"{self.cups_media_key}={media_value}"])
                if media_type_value:
                    command.extend(
                        ["-o", f"{self.cups_media_type_key}={media_type_value}"]
                    )
                if print_quality_value:
                    command.extend(
                        [
                            "-o",
                            f"{self.cups_print_quality_key}={print_quality_value}",
                        ]
                    )
                command.extend(
                    [
                        "-o",
                        "scaling=100",
                        "-o",
                        "position=center",
                        "-t",
                        f"Borderless Calibration {scale_percent}%",
                        str(out),
                    ]
                )

                result = subprocess.run(
                    command, capture_output=True, text=True, check=False
                )
                if result.returncode == 0:
                    queued += 1
                    request_id = parse_cups_request_id(result.stdout)
                    if request_id:
                        self.append_log(
                            "DEBUG",
                            f"CUPS calibration queued {file_name} as {request_id}",
                        )
                    else:
                        self.append_log("DEBUG", f"CUPS calibration queued {file_name}")
                else:
                    detail = (
                        (result.stderr or "").strip()
                        or (result.stdout or "").strip()
                        or "no output"
                    )
                    errors.append(f"{scale_percent}%: {detail}")

        return queued, errors

    def print_all_via_cups(
        self, paths: list[Path], printer_name: str
    ) -> tuple[list[Path], list[str], str, dict[str, str]]:
        printed_successfully: list[Path] = []
        failed: list[str] = []
        job_ids: dict[str, str] = {}
        borderless = self.borderless_enabled()

        caps, _resolved_keys = self.get_cups_capabilities(printer_name)
        effective_media_value = resolve_cups_media_value(
            self.cups_media_value,
            caps.get("media", []),
            borderless,
        )

        self.append_log(
            "DEBUG",
            (
                f"CUPS print start: printer={printer_name}, count={len(paths)}, "
                f"media={effective_media_value or self.cups_media_value or 'default'}, "
                f"media_type={self.cups_media_type_value or 'default'}, "
                f"quality={self.cups_print_quality_value or 'default'}, "
                f"borderless_scale={self.borderless_content_scale_percent}%"
            ),
        )
        if self.cups_media_value and effective_media_value != self.cups_media_value:
            self.append_log(
                "DEBUG",
                (
                    "CUPS media remap: "
                    "requested="
                    f"{self.cups_media_value} "
                    f"effective={effective_media_value}"
                ),
            )

        with tempfile.TemporaryDirectory(prefix="album_printer_") as temp_dir:
            for path in paths:
                out = Path(temp_dir) / f"{path.stem}.jpg"
                try:
                    image = render_image(path, self.processing_settings_for_path(path))
                    if borderless:
                        image = apply_borderless_content_scale(
                            image,
                            self.borderless_content_scale_percent,
                        )
                    image.save(out, format="JPEG", quality=95, optimize=True)
                except OSError as error:
                    failed.append(path.name)
                    self.append_log(
                        "DEBUG",
                        f"CUPS render failed for {path.name}: {error}",
                    )
                    continue

                command = ["lp", "-d", printer_name]
                if effective_media_value:
                    command.extend(
                        ["-o", f"{self.cups_media_key}={effective_media_value}"]
                    )
                if self.cups_media_type_value:
                    command.extend(
                        [
                            "-o",
                            f"{self.cups_media_type_key}={self.cups_media_type_value}",
                        ]
                    )
                if self.cups_print_quality_value:
                    command.extend(
                        [
                            "-o",
                            f"{self.cups_print_quality_key}="
                            f"{self.cups_print_quality_value}",
                        ]
                    )

                if borderless:
                    command.extend(
                        [
                            "-o",
                            "scaling=100",
                            "-o",
                            "position=center",
                        ]
                    )

                command.append(str(out))
                try:
                    result = subprocess.run(
                        command, capture_output=True, text=True, check=False
                    )
                except OSError as error:
                    self.append_log("ERROR", f"CUPS command failed: {error}")
                    return printed_successfully, failed, str(error), job_ids

                if result.returncode == 0:
                    printed_successfully.append(path)
                    request_id = parse_cups_request_id(result.stdout)
                    if request_id:
                        job_ids[path.name] = request_id
                        self.append_log(
                            "DEBUG", f"CUPS queued {path.name} as {request_id}"
                        )
                        status_text = query_cups_job_status_text(request_id)
                        if status_text:
                            self.append_log(
                                "DEBUG",
                                f"CUPS job {request_id}: {status_text}",
                            )
                    else:
                        self.append_log("DEBUG", f"CUPS queued {path.name}")
                else:
                    failed.append(path.name)
                    stderr = (result.stderr or "").strip()
                    stdout = (result.stdout or "").strip()
                    detail = stderr or stdout or "no output"
                    self.append_log(
                        "DEBUG",
                        (
                            f"CUPS failed {path.name}: returncode={result.returncode}, "
                            f"detail={detail[:220]}"
                        ),
                    )

        return printed_successfully, failed, "", job_ids

    def print_all_via_qt(
        self, paths: list[Path], printer_name: str
    ) -> tuple[list[Path], list[str], str]:
        printed_successfully: list[Path] = []
        failed: list[str] = []

        self.append_log(
            "DEBUG",
            f"Qt print start: printer={printer_name}, count={len(paths)}",
        )

        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setPrinterName(printer_name)

        borderless = self.borderless_enabled()
        media_size = media_size_mm_from_value(self.cups_media_value)
        if media_size is not None:
            width_mm, height_mm = media_size
            page_name = self.cups_media_value
            self.append_log(
                "DEBUG",
                f"Qt page size inferred from media '{self.cups_media_value}': "
                f"{width_mm:.1f}x{height_mm:.1f} mm",
            )
        else:
            width_mm, height_mm = self.paper_size_mm()
            page_name = self.paper_value
            if self.cups_media_value:
                self.append_log(
                    "DEBUG",
                    "Qt could not infer page size from media "
                    f"'{self.cups_media_value}', using fallback '{self.paper_value}'",
                )

        printer.setFullPage(borderless)
        page_size = QPageSize(
            QSizeF(width_mm, height_mm), QPageSize.Unit.Millimeter, page_name
        )
        margins = QMarginsF(0, 0, 0, 0) if borderless else QMarginsF(5, 5, 5, 5)
        layout = QPageLayout(
            page_size,
            QPageLayout.Orientation.Portrait,
            margins,
            QPageLayout.Unit.Millimeter,
        )
        printer.setPageLayout(layout)

        page_rect = printer.pageRect(QPrinter.Unit.DevicePixel)
        page_w = page_rect.width()
        page_h = page_rect.height()

        painter = QPainter(printer)
        if not painter.isActive():
            return printed_successfully, failed, "Could not start Qt print job"

        try:
            for idx, path in enumerate(paths):
                if idx > 0:
                    printer.newPage()

                try:
                    image = render_image(path, self.processing_settings_for_path(path))
                except OSError as error:
                    failed.append(path.name)
                    self.append_log(
                        "DEBUG",
                        f"Qt render failed for {path.name}: {error}",
                    )
                    continue

                pixmap = QPixmap.fromImage(QImage(ImageQt(image)))

                target = page_rect
                if width_mm and height_mm:
                    paper_ratio = width_mm / height_mm
                    page_ratio = page_w / page_h if page_h else 1
                    if abs(paper_ratio - page_ratio) > 0.01:
                        if page_ratio > paper_ratio:
                            target_w = int(page_h * paper_ratio)
                            x = (page_w - target_w) // 2
                            target = page_rect.adjusted(
                                x, 0, -(page_w - target_w - x), 0
                            )
                        else:
                            target_h = int(page_w / paper_ratio)
                            y = (page_h - target_h) // 2
                            target = page_rect.adjusted(
                                0, y, 0, -(page_h - target_h - y)
                            )

                scaled = pixmap.scaled(
                    target.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                x = target.x() + (target.width() - scaled.width()) // 2
                y = target.y() + (target.height() - scaled.height()) // 2
                painter.drawPixmap(x, y, scaled)
                printed_successfully.append(path)
                self.append_log("DEBUG", f"Qt queued {path.name}")
        finally:
            painter.end()

        return printed_successfully, failed, ""

    def selected_paths_for_printing(self) -> list[Path]:
        selected_rows = [
            index.row() for index in self.image_table.selectionModel().selectedRows()
        ]
        selected_rows.sort()

        paths: list[Path] = []
        seen: set[Path] = set()
        for row in selected_rows:
            if row < 0 or row >= len(self.image_paths):
                continue
            path = self.image_paths[row]
            if path in seen:
                continue
            seen.add(path)
            paths.append(path)

        if paths:
            return paths

        current = self.selected_path()
        if current is None:
            return []
        return [current]

    def print_selected(self) -> None:
        paths = self.selected_paths_for_printing()
        if not paths:
            QMessageBox.information(
                self, "Nothing selected", "Select one or more images first."
            )
            return
        self.print_paths(paths)

    def record_print_history(
        self,
        attempted_paths: list[Path],
        printed_paths: list[Path],
        failed_names: list[str],
        printer_name: str,
        backend: str,
        error: str,
        job_ids: dict[str, str] | None = None,
    ) -> None:
        if self.current_folder is None or not attempted_paths:
            return

        timestamp = datetime.now().isoformat(timespec="seconds")
        photos = self.folder_metadata.get("photos")
        if not isinstance(photos, dict):
            photos = {}
            self.folder_metadata["photos"] = photos

        printed_set = set(printed_paths)
        effective_job_ids = dict(job_ids or {})
        event_job_ids: dict[str, str] = {}

        for path in attempted_paths:
            entry = photos.get(path.name)
            if not isinstance(entry, dict):
                entry = {}
            job_id = effective_job_ids.get(path.name)
            if not job_id:
                job_id = f"{backend.lower()}-{uuid.uuid4().hex[:12]}"
                effective_job_ids[path.name] = job_id
            event_job_ids[path.name] = job_id
            status = "printed" if path in printed_set else "failed"
            if status == "printed":
                entry["total_printed"] = int(entry.get("total_printed", 0)) + 1
                entry["last_printed_at"] = timestamp
            entry["last_print_status"] = status
            entry["last_print_job_id"] = job_id
            entry["last_print_error"] = error
            entry["last_printer"] = printer_name
            entry["last_backend"] = backend
            entry["last_project_settings"] = self.current_project_settings_payload()
            entry["last_image_settings"] = self.image_settings_for_path(path)

            attempts = entry.get("print_attempts")
            if not isinstance(attempts, list):
                attempts = []
            attempts.append(
                {
                    "timestamp": timestamp,
                    "status": status,
                    "backend": backend,
                    "printer": printer_name,
                    "job_id": job_id,
                    "error": error,
                }
            )
            entry["print_attempts"] = attempts[-50:]
            photos[path.name] = entry

        events = self.folder_metadata.get("print_events")
        if not isinstance(events, list):
            events = []
        events.append(
            {
                "timestamp": timestamp,
                "printer": printer_name,
                "backend": backend,
                "count": len(attempted_paths),
                "printed_count": len(printed_paths),
                "failed": failed_names,
                "error": error,
                "job_ids": event_job_ids,
                "photos": [path.name for path in attempted_paths],
                "project_settings": self.current_project_settings_payload(),
            }
        )
        self.folder_metadata["print_events"] = events[-500:]
        self.save_folder_metadata()

    def print_all(self) -> None:
        self.print_paths(list(self.image_paths))

    def print_paths(self, paths: list[Path]) -> None:
        if not paths:
            QMessageBox.information(self, "Nothing to print", "Load images first.")
            self.append_log("INFO", "Print requested with no images loaded")
            return

        self.enqueue_print_paths(paths)

    def execute_print_paths(
        self, paths: list[Path]
    ) -> tuple[list[Path], list[str], str, str, str, dict[str, str]]:
        if not paths:
            return [], [], "No images provided.", "", self.print_backend_value, {}

        self.append_log(
            "DEBUG",
            "Print request files: " + ", ".join(path.name for path in paths),
        )

        photos = self.folder_metadata.get("photos")
        duplicate_names: list[str] = []
        if isinstance(photos, dict):
            for path in paths:
                photo_meta = photos.get(path.name)
                if not isinstance(photo_meta, dict):
                    continue
                if int(photo_meta.get("total_printed", 0)) > 0:
                    duplicate_names.append(path.name)

        if duplicate_names:
            examples = "\n".join(f"- {name}" for name in duplicate_names[:5])
            message = (
                f"{len(duplicate_names)} selected photo(s) were already printed "
                "before.\n\n"
                "Examples:\n"
                f"{examples}\n\n"
                "Print anyway?"
            )
            reply = QMessageBox.question(
                self,
                "Already printed photos",
                message,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                self.append_log(
                    "INFO",
                    "Print cancelled by user due to already printed photo selection",
                )
                return (
                    [],
                    [],
                    "Cancelled by user",
                    "",
                    self.print_backend_value,
                    {},
                )

        backend = self.print_backend_value
        printer_name = self.printer_value
        job_ids: dict[str, str] = {}
        self.append_log(
            "DEBUG",
            (
                f"Print start: backend={backend}, printer={printer_name or '-'}, "
                f"ipp_uri={self.ipp_uri_value or '-'}, count={len(paths)}"
            ),
        )

        if backend == "IPP":
            if not self.ipp_uri_value:
                QMessageBox.warning(
                    self,
                    "No IPP URI",
                    "Set an IPP URI in Print Settings when Print Backend is IPP.",
                )
                self.append_log(
                    "ERROR", "Print failed: IPP backend selected without IPP URI"
                )
                return (
                    [],
                    [path.name for path in paths],
                    "IPP URI is missing",
                    "",
                    backend,
                    {},
                )

            ipp_uri = self.ipp_uri_value.strip()
            if ipp_uri and ipp_uri not in self.ipp_capabilities_cache:
                try:
                    self.ipp_capabilities_cache[ipp_uri] = get_ipp_capabilities(ipp_uri)
                except IppBackendError:
                    self.ipp_capabilities_cache[ipp_uri] = None

            printed, failed, error, job_ids = self.print_all_via_ipp(
                paths, self.ipp_uri_value
            )
            target_name = self.current_ipp_target_name()
        else:
            if backend == "CUPS":
                if not printer_name:
                    QMessageBox.warning(
                        self,
                        "No printer",
                        "No printer selected. Open Print Settings "
                        "and choose a printer first.",
                    )
                    self.append_log(
                        "ERROR", "Print failed: CUPS backend selected without printer"
                    )
                    return (
                        [],
                        [path.name for path in paths],
                        "Printer is missing",
                        "",
                        backend,
                        {},
                    )
                if not self.is_cups_available():
                    QMessageBox.warning(
                        self,
                        "CUPS unavailable",
                        "CUPS backend selected, but CUPS tools are not available.",
                    )
                    self.append_log("ERROR", "Print failed: CUPS tools are unavailable")
                    return (
                        [],
                        [path.name for path in paths],
                        "CUPS tools unavailable",
                        "",
                        backend,
                        {},
                    )
                printed, failed, error, job_ids = self.print_all_via_cups(
                    paths, printer_name
                )
            elif backend == "Qt":
                if not printer_name:
                    default_printer = QPrinterInfo.defaultPrinter()
                    if default_printer and default_printer.printerName():
                        printer_name = default_printer.printerName()
                    else:
                        QMessageBox.warning(
                            self,
                            "No printer",
                            "No printer selected and no default Qt printer found.",
                        )
                        self.append_log(
                            "ERROR", "Print failed: no selected/default Qt printer"
                        )
                        return (
                            [],
                            [path.name for path in paths],
                            "No Qt printer available",
                            "",
                            backend,
                            {},
                        )
                printed, failed, error = self.print_all_via_qt(paths, printer_name)
            else:
                if not printer_name:
                    QMessageBox.warning(
                        self,
                        "No printer",
                        "No printer selected. Open Print Settings "
                        "and choose a printer first.",
                    )
                    self.append_log(
                        "ERROR", "Print failed: Auto backend without selected printer"
                    )
                    return (
                        [],
                        [path.name for path in paths],
                        "Printer is missing",
                        "",
                        backend,
                        {},
                    )
                if self.is_cups_available():
                    printed, failed, error, job_ids = self.print_all_via_cups(
                        paths, printer_name
                    )
                else:
                    printed, failed, error = self.print_all_via_qt(paths, printer_name)
            target_name = printer_name

        self.record_print_history(
            paths,
            printed,
            failed,
            target_name,
            backend,
            error,
            job_ids=job_ids,
        )
        self.refresh_image_list_labels(self.selected_path())
        self.update_selected_print_info()

        queue_only_backend = backend in {"CUPS", "IPP"}
        action_word = "Queued" if queue_only_backend else "Sent"
        message = f"{action_word} {len(printed)} image(s) to {target_name}."
        if error:
            message += f" Error: {error}"
        if failed:
            message += f" Failed: {', '.join(failed[:5])}"

        log_level = "ERROR" if error else ("WARNING" if failed else "INFO")
        count_label = "queued" if queue_only_backend else "printed"
        summary = (
            f"Print queued via {backend} to {target_name}: "
            f"{count_label}={len(printed)}, failed={len(failed)}"
        )
        self.append_log(
            log_level,
            summary,
        )
        if error:
            self.append_log("ERROR", f"Print backend error: {error}")
        if failed:
            self.append_log("DEBUG", "Print failed files: " + ", ".join(failed))

        self.statusBar().showMessage(message)
        return printed, failed, error, target_name, backend, job_ids

    def print_all_via_ipp(
        self, paths: list[Path], ipp_uri: str
    ) -> tuple[list[Path], list[str], str, dict[str, str]]:
        wait_for_completion = self.ipp_wait_for_completion_value
        if wait_for_completion:
            self.append_log(
                "WARNING",
                "IPP wait-for-completion is currently forced "
                "to queue-only to avoid UI blocking.",
            )
            wait_for_completion = False

        self.append_log(
            "DEBUG",
            (
                f"IPP print start: uri={ipp_uri}, count={len(paths)}, "
                f"wait_for_completion={wait_for_completion}, "
                f"media={self.cups_media_value or 'default'}, "
                f"media_type={self.cups_media_type_value or 'default'}, "
                f"quality={self.cups_print_quality_value or 'default'}"
            ),
        )
        with tempfile.TemporaryDirectory(prefix="album_printer_ipp_") as temp_dir:
            render_targets: list[Path] = []
            render_map: dict[Path, Path] = {}
            failed: list[str] = []

            for source in paths:
                out = Path(temp_dir) / f"{source.stem}.jpg"
                try:
                    image = render_image(
                        source, self.processing_settings_for_path(source)
                    )
                    image.save(out, format="JPEG", quality=95, optimize=True)
                    render_targets.append(out)
                    render_map[out] = source
                except OSError as error:
                    failed.append(source.name)
                    self.append_log(
                        "DEBUG",
                        f"IPP render failed for {source.name}: {error}",
                    )

            if not render_targets:
                return [], failed, "No printable images were rendered for IPP.", {}

            try:
                printed_rendered, failed_rendered, error, rendered_job_ids = (
                    print_jobs_via_ipp(
                        ipp_uri=ipp_uri,
                        image_files=render_targets,
                        media=self.cups_media_value,
                        media_type=self.cups_media_type_value,
                        print_quality=self.cups_print_quality_value,
                        borderless_mode=self.borderless_mode_value,
                        wait_for_completion=wait_for_completion,
                        debug_logger=lambda message: self.append_log("DEBUG", message),
                    )
                )
            except IppBackendError as exc:
                self.append_log("ERROR", f"IPP backend exception: {exc}")
                return [], [path.name for path in paths], str(exc), {}

            printed_sources = [
                render_map[path] for path in printed_rendered if path in render_map
            ]
            job_ids: dict[str, str] = {}
            for rendered_name, job_id in rendered_job_ids.items():
                for rendered_path, source_path in render_map.items():
                    if rendered_path.name == rendered_name:
                        job_ids[source_path.name] = job_id
                        break
            failed.extend(failed_rendered)
            for path in printed_sources:
                self.append_log("DEBUG", f"IPP queued {path.name}")
            if failed_rendered:
                self.append_log(
                    "DEBUG",
                    "IPP backend failed files: " + ", ".join(failed_rendered),
                )
            if error:
                self.append_log("DEBUG", f"IPP backend detail: {error}")
            return printed_sources, failed, error, job_ids


def run_application(argv: Sequence[str] | None = None) -> int:
    app = QApplication(list(argv or []))
    icon = app_window_icon()
    if icon is not None:
        app.setWindowIcon(icon)
    splash_start = time.perf_counter()
    splash = create_splash_screen()
    splash.showMessage(
        "Initializing…",
        Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom,
        QColor("#D1D5DB"),
    )
    splash.show()
    splash.raise_()
    splash.activateWindow()
    if not is_debugger_attached():
        app.processEvents()

    startup_cache = preload_startup_cache(splash)

    elapsed = time.perf_counter() - splash_start
    min_splash_seconds = 0.0 if is_debugger_attached() else 0.8
    while elapsed < min_splash_seconds:
        if not is_debugger_attached():
            app.processEvents()
        time.sleep(0.01)
        elapsed = time.perf_counter() - splash_start

    window = MainWindow(startup_cache=startup_cache)
    window.show()
    splash.finish(window)
    return app.exec()
