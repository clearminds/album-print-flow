from __future__ import annotations

import importlib.metadata
import platform
import sys
from pathlib import Path

from PySide6.QtCore import Qt, qVersion
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QSplashScreen


def is_debugger_attached() -> bool:
    gettrace = getattr(sys, "gettrace", None)
    if not callable(gettrace):
        return False
    try:
        return gettrace() is not None
    except Exception:
        return False


def app_version() -> str:
    try:
        return importlib.metadata.version("album-print-flow")
    except importlib.metadata.PackageNotFoundError:
        return "1.0.0"


def app_runtime_line() -> str:
    return f"Python {platform.python_version()} • Qt {qVersion()}"


def app_branding_info(
    *,
    app_display_name: str,
    app_tagline: str,
    app_copyright: str,
) -> dict[str, str]:
    version = app_version()
    return {
        "name": app_display_name,
        "tagline": app_tagline,
        "version": version,
        "version_line": f"Version {version}",
        "copyright": app_copyright,
        "runtime": app_runtime_line(),
    }


def app_about_text(
    *,
    app_display_name: str,
    app_tagline: str,
    app_copyright: str,
) -> str:
    info = app_branding_info(
        app_display_name=app_display_name,
        app_tagline=app_tagline,
        app_copyright=app_copyright,
    )
    return (
        f"{info['name']}\n"
        f"{info['version_line']}\n\n"
        f"{info['tagline']}\n\n"
        f"{info['copyright']}\n"
        f"{info['runtime']}"
    )


def logo_path(base_file: Path | None = None) -> Path | None:
    base = (base_file or Path(__file__)).resolve()
    candidates = [
        base.parents[2] / "assets" / "icons" / "png" / "app-icon-256.png",
        base.parents[1] / "assets" / "icons" / "png" / "app-icon-256.png",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def clearminds_head_path(base_file: Path | None = None) -> Path | None:
    base = (base_file or Path(__file__)).resolve()
    candidates = [
        base.parents[2] / "assets" / "branding" / "clearminds-head.png",
        base.parents[1] / "assets" / "branding" / "clearminds-head.png",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def clearminds_wordmark_path(base_file: Path | None = None) -> Path | None:
    base = (base_file or Path(__file__)).resolve()
    candidates = [
        base.parents[2] / "assets" / "branding" / "clearminds-wordmark.png",
        base.parents[1] / "assets" / "branding" / "clearminds-wordmark.png",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def load_logo_pixmap(base_file: Path | None = None, size: int = 160) -> QPixmap | None:
    path = logo_path(base_file)
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


def app_window_icon(base_file: Path | None = None) -> QIcon | None:
    path = logo_path(base_file)
    if path is None:
        return None
    pixmap = QPixmap(str(path))
    if pixmap.isNull():
        return None
    # Provide multiple sizes so Windows uses the correct icon in the taskbar
    # (it often uses 16x16 or 32x32) as well as in the window title.
    icon = QIcon()
    for size in (16, 32, 48, 256):
        scaled = pixmap.scaled(
            size,
            size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        if not scaled.isNull():
            icon.addPixmap(scaled)
    if icon.isNull():
        return None
    return icon


def load_clearminds_head_pixmap(
    base_file: Path | None = None,
    size: int = 64,
) -> QPixmap | None:
    path = clearminds_head_path(base_file)
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


def load_clearminds_wordmark_pixmap(
    base_file: Path | None = None,
    width: int = 180,
) -> QPixmap | None:
    path = clearminds_wordmark_path(base_file)
    if path is None:
        return None
    pixmap = QPixmap(str(path))
    if pixmap.isNull():
        return None
    return pixmap.scaledToWidth(width, Qt.TransformationMode.SmoothTransformation)


def create_splash_screen(
    *,
    app_display_name: str,
    app_tagline: str,
    app_copyright: str,
    base_file: Path,
) -> QSplashScreen:
    width, height = 720, 420
    canvas = QPixmap(width, height)
    canvas.fill(QColor("#0F172A"))

    painter = QPainter(canvas)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

    painter.fillRect(0, 0, width, height, QColor("#111827"))

    info = app_branding_info(
        app_display_name=app_display_name,
        app_tagline=app_tagline,
        app_copyright=app_copyright,
    )

    logo = load_logo_pixmap(base_file, 164)
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

    cm_head = load_clearminds_head_pixmap(base_file, 48)
    if cm_head is not None:
        painter.drawPixmap(width - cm_head.width() - 16, 16, cm_head)

    cm_wordmark = load_clearminds_wordmark_pixmap(base_file, 120)
    if cm_wordmark is not None:
        painter.drawPixmap(16, height - cm_wordmark.height() - 12, cm_wordmark)
    painter.end()

    splash = QSplashScreen(canvas)
    splash.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
    splash.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
    return splash


__all__ = [
    "app_about_text",
    "app_branding_info",
    "app_runtime_line",
    "app_version",
    "app_window_icon",
    "clearminds_head_path",
    "clearminds_wordmark_path",
    "create_splash_screen",
    "is_debugger_attached",
    "load_clearminds_head_pixmap",
    "load_clearminds_wordmark_pixmap",
    "load_logo_pixmap",
    "logo_path",
]
