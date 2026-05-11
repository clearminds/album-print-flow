from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import sys
from typing import Any

from PIL.ImageQt import ImageQt
from PySide6.QtCore import QMarginsF, QRect, QSizeF, Qt
from PySide6.QtGui import QImage, QPageLayout, QPageSize, QPainter, QPixmap, QTransform
from PySide6.QtPrintSupport import QPrintDialog, QPrinter
from PySide6.QtWidgets import QDialog


def _page_size_for_qt(paper_value: str, width_mm: float, height_mm: float) -> QPageSize:
    """Build QPageSize; use standard Id when possible
    so Windows driver selects that paper."""
    standard_ids = {
        "A4": QPageSize.PageSizeId.A4,
        "A3": QPageSize.PageSizeId.A3,
        "A4+": QPageSize.PageSizeId.A4Plus,
    }
    page_id = standard_ids.get(paper_value)
    if page_id is not None:
        return QPageSize(page_id)
    return QPageSize(
        QSizeF(width_mm, height_mm),
        QPageSize.Unit.Millimeter,
        paper_value,
    )


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

    if sys.platform == "darwin":
        dialog = QPrintDialog(printer, window)
        dialog.setWindowTitle("Print")
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return printed_successfully, [path.name for path in paths], "Print cancelled"

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

    printer.setFullPage(borderless)
    page_size = _page_size_for_qt(page_name, width_mm, height_mm)
    orientation = getattr(window, "print_orientation_value", "Portrait").strip()
    qt_orientation = (
        QPageLayout.Orientation.Landscape
        if orientation == "Landscape"
        else QPageLayout.Orientation.Portrait
    )
    # Use zero margins so the image uses the full page
    margins = QMarginsF(0, 0, 0, 0)
    layout = QPageLayout(
        page_size,
        qt_orientation,
        margins,
        QPageLayout.Unit.Millimeter,
    )
    printer.setPageLayout(layout)

    # Use the printer's actual resolution so our draw coordinates match the device.
    # If we used a fixed 300 DPI but the driver uses 600+, only part of the image
    # would appear (e.g. top-left quarter).
    resolution = printer.resolution()
    if resolution <= 0:
        resolution = 300
    layout_rect = layout.paintRectPixels(resolution)
    layout_w = layout_rect.width()
    layout_h = layout_rect.height()

    def log(msg: str) -> None:
        window.append_log("DEBUG", msg)

    log(
        f"Qt page: paper={page_name}, orientation={orientation}, "
        f"size={width_mm:.1f}x{height_mm:.1f} mm, fullPage={borderless}"
    )
    log(f"Qt printer valid={printer.isValid()}, resolution={resolution} DPI")
    log(f"Qt page rect (layout): {layout_w}x{layout_h} px")
    # Use the largest draw area we can: when fullPage, use paperRect (full paper)
    # to avoid white margins on the sides; otherwise use pageRect (printable area).
    page_rect = layout_rect
    try:
        pr_page = printer.pageRect(QPrinter.Unit.DevicePixel)
        pr_paper = printer.paperRect(QPrinter.Unit.DevicePixel)
        w_page = int(pr_page.width())
        h_page = int(pr_page.height())
        w_paper = int(pr_paper.width())
        h_paper = int(pr_paper.height())
        log(f"Qt page rect (printer printable): {w_page}x{h_page} px")
        log(f"Qt paper rect (printer full): {w_paper}x{h_paper} px")
        if borderless and w_paper > 0 and h_paper > 0:
            # Draw to full paper so we don't get white on the sides.
            page_rect = QRect(int(pr_paper.x()), int(pr_paper.y()), w_paper, h_paper)
            log(
                f"Qt using paper rect for draw (fullPage): "
                f"{page_rect.width()}x{page_rect.height()} px"
            )
        elif w_page > 0 and h_page > 0:
            page_rect = QRect(int(pr_page.x()), int(pr_page.y()), w_page, h_page)
            log(
                f"Qt using page rect for draw: "
                f"{page_rect.width()}x{page_rect.height()} px"
            )
    except Exception:
        pass
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
            tw = target.width()
            th = target.height()
            # When fullPage, scale to slightly larger than page (bleed)
            # so driver margins don't show as white.
            bleed = 1.02 if borderless else 1.0
            tw_fill = int(round(tw * bleed))
            th_fill = int(round(th * bleed))
            pw0 = pixmap.width()
            ph0 = pixmap.height()
            # Rotate image to match page orientation so it fills the page better.
            pw = pw0
            ph = ph0
            page_landscape = tw > th
            image_landscape = pw > ph
            rotated = page_landscape != image_landscape
            if rotated:
                pixmap = pixmap.transformed(
                    QTransform().rotate(90),
                    Qt.TransformationMode.SmoothTransformation,
                )
                pw = pixmap.width()
                ph = pixmap.height()
            if pw <= 0 or ph <= 0:
                continue
            # Scale to fill the page (and bleed when borderless);
            # image may be cropped at edges.
            scale = max(tw_fill / pw, th_fill / ph)
            scaled_w = max(tw_fill, int(round(pw * scale)))
            scaled_h = max(th_fill, int(round(ph * scale)))
            scaled = pixmap.scaled(
                scaled_w,
                scaled_h,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            x = target.x() + (tw - scaled.width()) // 2
            y = target.y() + (th - scaled.height()) // 2
            painter.save()
            if not borderless:
                painter.setClipRect(target)
            painter.drawPixmap(x, y, scaled)
            painter.restore()
            printed_successfully.append(path)
            rot_txt = f" → rotated 90° → {pw}x{ph} px" if rotated else ""
            bleed_txt = f", bleed={bleed}" if borderless else ""
            log(
                f"Qt page {idx + 1} [{path.name}]: "
                f"image {pw0}x{ph0} px{rot_txt}, "
                f"scale={scale:.3f}{bleed_txt}, "
                f"draw {scaled.width()}x{scaled.height()} "
                f"at ({x},{y})"
            )
    finally:
        painter.end()

    return printed_successfully, failed, ""
