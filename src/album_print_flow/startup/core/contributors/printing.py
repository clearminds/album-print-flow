from __future__ import annotations

import os
import shutil
import subprocess
import time
from collections.abc import Callable
from typing import Any

from PySide6.QtPrintSupport import QPrinterInfo

from album_print_flow.startup.core.runner import (
    StartupPreloadContext,
    StartupPreloadTask,
)


def build_printing_startup_preload_tasks(
    parse_cups_options_output_fn: Callable[
        [str], tuple[dict[str, list[str]], dict[str, str]]
    ],
    get_ipp_capabilities_fn: Callable[[str], Any],
    ipp_backend_error_cls: type[Exception],
) -> list[StartupPreloadTask]:
    def preload_print_backend(context: StartupPreloadContext) -> None:
        settings = context.settings
        backend = str(settings.value("print/backend", "Auto")).strip()
        selected_printer = str(settings.value("print/printer", "")).strip()
        ipp_uri = str(settings.value("print/ipp_uri", "")).strip()
        context.add_debug_line(f"Startup preload backend={backend or 'Auto'}")

        preload_printers = backend in {"Auto", "CUPS", "Qt"}
        preload_cups = backend in {"Auto", "CUPS"}
        preload_ipp = backend == "IPP"

        if preload_printers:
            printers_started_at = time.perf_counter()
            context.show_step("Loading printers…")
            printers = [
                printer.printerName() for printer in QPrinterInfo.availablePrinters()
            ]
            context.cache["printers"] = printers
            context.add_debug_line(
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
            context.show_step(f"Loading paper options for {selected_printer}…")
            try:
                result = subprocess.run(
                    ["lpoptions", "-p", selected_printer, "-l"],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if result.returncode == 0:
                    cups_cache[selected_printer] = parse_cups_options_output_fn(
                        result.stdout
                    )
                    context.add_debug_line(
                        f"Startup preload CUPS({selected_printer}): success in "
                        f"{(time.perf_counter() - cups_started_at) * 1000:.1f} ms"
                    )
                else:
                    context.add_debug_line(
                        f"Startup preload CUPS({selected_printer}): returncode "
                        f"{result.returncode} in "
                        f"{(time.perf_counter() - cups_started_at) * 1000:.1f} ms"
                    )
            except OSError:
                context.add_debug_line(
                    f"Startup preload CUPS({selected_printer}): unavailable"
                )
        context.cache["cups_capabilities"] = cups_cache

        ipp_cache: dict[str, object | None] = {}
        if preload_ipp and ipp_uri:
            ipp_started_at = time.perf_counter()
            context.show_step("Loading IPP capabilities…")
            try:
                caps = get_ipp_capabilities_fn(ipp_uri)
                ipp_cache[ipp_uri] = caps
                media = len(getattr(caps, "media", []))
                media_type = len(getattr(caps, "media_type", []))
                quality = len(getattr(caps, "print_quality", []))
                context.add_debug_line(
                    "Startup preload IPP: "
                    f"media={media}, type={media_type}, "
                    f"quality={quality} in "
                    f"{(time.perf_counter() - ipp_started_at) * 1000:.1f} ms"
                )
            except ipp_backend_error_cls:
                ipp_cache[ipp_uri] = None
                context.add_debug_line(
                    f"Startup preload IPP: unavailable in "
                    f"{(time.perf_counter() - ipp_started_at) * 1000:.1f} ms"
                )
        context.cache["ipp_capabilities"] = ipp_cache

    return [
        StartupPreloadTask(
            task_id="printing-backend",
            label="Loading print backend data…",
            run=preload_print_backend,
            critical=False,
        )
    ]


__all__ = ["build_printing_startup_preload_tasks"]
