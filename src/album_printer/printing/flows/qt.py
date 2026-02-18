from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from PIL.ImageQt import ImageQt
from PySide6.QtCore import QMarginsF, QSizeF, Qt
from PySide6.QtGui import QImage, QPageLayout, QPageSize, QPainter, QPixmap
from PySide6.QtPrintSupport import QPrinter


def print_all_via_qt(
    window: Any,
    paths: list[Path],
    printer_name: str,
    media_size_mm_from_value_fn: Callable[[str], tuple[float, float] | None],
    render_image_fn: Callable[..., Any],
    ratios_match_either_orientation_fn: Callable[[float, float, float, float], bool],
) -> tuple[list[Path], list[str], str]:
    printed_successfully: list[Path] = []
    failed: list[str] = []

    window.append_log(
        "DEBUG",
        f"Qt print start: printer={printer_name}, count={len(paths)}",
    )

    printer = QPrinter(QPrinter.PrinterMode.HighResolution)
    printer.setPrinterName(printer_name)

    borderless = window.borderless_enabled()
    media_size = media_size_mm_from_value_fn(window.cups_media_value)
    if media_size is not None:
        width_mm, height_mm = media_size
        page_name = window.cups_media_value
        window.append_log(
            "DEBUG",
            f"Qt page size inferred from media '{window.cups_media_value}': "
            f"{width_mm:.1f}x{height_mm:.1f} mm",
        )
    else:
        width_mm, height_mm = window.paper_size_mm()
        page_name = window.paper_value
        if window.cups_media_value:
            window.append_log(
                "DEBUG",
                "Qt could not infer page size from media "
                f"'{window.cups_media_value}', using fallback '{window.paper_value}'",
            )

    # Use a fixed resolution so layout-based pixel rect matches the paint device
    # (on Windows, pageRect(DevicePixel) can be wrong or not match our page size)
    resolution = 300
    printer.setResolution(resolution)
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

    # Use the layout's paint rect in pixels so coordinates match our page size
    # (critical on Windows where driver may not report pageRect correctly)
    page_rect = layout.paintRectPixels(resolution)
    page_w = page_rect.width()
    page_h = page_rect.height()
    if page_w <= 0 or page_h <= 0:
        return (
            printed_successfully,
            failed,
            "Invalid page size (layout paint rect is empty)",
        )

    painter = QPainter(printer)
    if not painter.isActive():
        return printed_successfully, failed, "Could not start Qt print job"

    try:
        for idx, path in enumerate(paths):
            if idx > 0:
                printer.newPage()

            try:
                image = render_image_fn(
                    path,
                    window.processing_settings_for_path(path),
                    debug_logger=lambda message: window.append_log("DEBUG", message),
                )
            except OSError as error:
                failed.append(path.name)
                window.append_log(
                    "DEBUG",
                    f"Qt render failed for {path.name}: {error}",
                )
                continue

            pixmap = QPixmap.fromImage(QImage(ImageQt(image)))

            target = page_rect
            if width_mm and height_mm:
                paper_ratio = width_mm / height_mm
                page_ratio = page_w / page_h if page_h else 1
                if not ratios_match_either_orientation_fn(
                    page_ratio,
                    width_mm,
                    height_mm,
                    tolerance=0.01,
                ):
                    if page_ratio > paper_ratio:
                        target_w = int(page_h * paper_ratio)
                        x = (page_w - target_w) // 2
                        target = page_rect.adjusted(x, 0, -(page_w - target_w - x), 0)
                    else:
                        target_h = int(page_w / paper_ratio)
                        y = (page_h - target_h) // 2
                        target = page_rect.adjusted(0, y, 0, -(page_h - target_h - y))

            scaled = pixmap.scaled(
                int(target.width()),
                int(target.height()),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            x = target.x() + (target.width() - scaled.width()) // 2
            y = target.y() + (target.height() - scaled.height()) // 2
            painter.drawPixmap(x, y, scaled)
            printed_successfully.append(path)
            window.append_log("DEBUG", f"Qt queued {path.name}")
    finally:
        painter.end()

    return printed_successfully, failed, ""
