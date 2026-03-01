from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

from PySide6.QtPrintSupport import QPrinterInfo
from PySide6.QtWidgets import QComboBox


def populate_printers_combo(window: Any, combo: QComboBox) -> None:
    current = combo.currentText()
    combo.clear()
    if not window.printer_names_cache:
        printers = QPrinterInfo.availablePrinters()
        window.printer_names_cache = [printer.printerName() for printer in printers]
    combo.addItems(window.printer_names_cache)
    if current:
        idx = combo.findText(current)
        if idx >= 0:
            combo.setCurrentIndex(idx)


def is_cups_available() -> bool:
    return (
        os.name == "posix"
        and bool(shutil.which("lp"))
        and bool(shutil.which("lpoptions"))
    )


def get_cups_capabilities(
    window: Any,
    printer_name: str,
    cups_keys: list[str],
) -> tuple[dict[str, list[str]], dict[str, str]]:
    defaults = {
        "media": "media",
        "media-type": "media-type",
        "print-quality": "print-quality",
    }
    empty = {key: [] for key in cups_keys}

    if not printer_name or not is_cups_available():
        return empty, defaults

    cached = window.cups_capabilities_cache.get(printer_name)
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
        return empty, defaults

    if result.returncode != 0:
        return empty, defaults

    parsed = window.parse_cups_options(result.stdout)
    window.cups_capabilities_cache[printer_name] = parsed
    return parsed


def print_borderless_calibration_pages(
    window: Any,
    printer_name: str,
    media_value: str,
    media_type_value: str,
    print_quality_value: str,
    scale_values: list[int],
    media_size_mm_from_value_fn: Callable[[str], tuple[float, float] | None],
    create_borderless_calibration_image_fn: Callable[[int, int, int, str], Any],
    apply_borderless_content_scale_fn: Callable[[Any, int], Any],
    parse_cups_request_id_fn: Callable[[str], str],
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

    media_size = media_size_mm_from_value_fn(media_value)
    if media_size is None:
        media_size = (101.6, 152.4)
    width_mm, height_mm = media_size
    width_px = max(800, int(round(width_mm * 12)))
    height_px = max(800, int(round(height_mm * 12)))

    queued = 0
    errors: list[str] = []

    with tempfile.TemporaryDirectory(prefix="album_print_flow_cal_") as temp_dir:
        for test_index, scale_percent in enumerate(unique_scales, start=1):
            file_name = f"borderless-calibration-{test_index}-{scale_percent}.jpg"
            out = Path(temp_dir) / file_name
            image = create_borderless_calibration_image_fn(
                width_px,
                height_px,
                scale_percent,
                str(test_index),
            )
            image = apply_borderless_content_scale_fn(image, scale_percent)
            image.save(out, format="JPEG", quality=95, optimize=True)

            command = ["lp", "-d", printer_name]
            if media_value:
                command.extend(["-o", f"{window.cups_media_key}={media_value}"])
            if media_type_value:
                command.extend(
                    ["-o", f"{window.cups_media_type_key}={media_type_value}"]
                )
            if print_quality_value:
                command.extend(
                    [
                        "-o",
                        f"{window.cups_print_quality_key}={print_quality_value}",
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
                request_id = parse_cups_request_id_fn(result.stdout)
                if request_id:
                    window.append_log(
                        "DEBUG",
                        f"CUPS calibration queued {file_name} as {request_id}",
                    )
                else:
                    window.append_log("DEBUG", f"CUPS calibration queued {file_name}")
            else:
                detail = (
                    (result.stderr or "").strip()
                    or (result.stdout or "").strip()
                    or "no output"
                )
                errors.append(f"{scale_percent}%: {detail}")

    return queued, errors


__all__ = [
    "populate_printers_combo",
    "is_cups_available",
    "get_cups_capabilities",
    "print_borderless_calibration_pages",
]
