from __future__ import annotations

import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication, QSplashScreen


@dataclass(frozen=True)
class StartupPreloadTask:
    task_id: str
    label: str
    run: Callable[[StartupPreloadContext], None]
    critical: bool = False


@dataclass
class StartupPreloadContext:
    settings: QSettings
    cache: dict[str, object]
    show_step: Callable[[str], None]
    add_debug_line: Callable[[str], None]


def run_startup_preload_tasks(
    splash: QSplashScreen,
    tasks: Sequence[StartupPreloadTask],
    settings_org: str,
    settings_app: str,
    is_debugger_attached_fn: Callable[[], bool],
    mode: str = "mixed",
) -> dict[str, object]:
    preload_started_at = time.perf_counter()
    cache: dict[str, object] = {
        "printers": [],
        "cups_capabilities": {},
        "ipp_capabilities": {},
        "startup_debug_lines": [],
        "preload_results": {},
    }
    startup_debug_lines: list[str] = []
    preload_results: dict[str, dict[str, object]] = {}

    def show_step(message: str) -> None:
        splash.showMessage(
            message,
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom,
            QColor("#D1D5DB"),
        )
        if not is_debugger_attached_fn():
            QApplication.processEvents()

    context = StartupPreloadContext(
        settings=QSettings(settings_org, settings_app),
        cache=cache,
        show_step=show_step,
        add_debug_line=startup_debug_lines.append,
    )

    for task in tasks:
        task_started_at = time.perf_counter()
        show_step(task.label)
        try:
            task.run(context)
            elapsed_ms = (time.perf_counter() - task_started_at) * 1000
            startup_debug_lines.append(
                f"Startup preload {task.task_id}: success in {elapsed_ms:.1f} ms"
            )
            preload_results[task.task_id] = {
                "ok": True,
                "critical": task.critical,
                "elapsed_ms": elapsed_ms,
            }
        except Exception as error:
            elapsed_ms = (time.perf_counter() - task_started_at) * 1000
            startup_debug_lines.append(
                f"Startup preload {task.task_id}: failed ({error}) in {elapsed_ms:.1f} ms"
            )
            preload_results[task.task_id] = {
                "ok": False,
                "critical": task.critical,
                "error": str(error),
                "elapsed_ms": elapsed_ms,
            }
            if mode == "strict" or (mode == "mixed" and task.critical):
                raise

    startup_debug_lines.append(
        "Startup preload total: "
        f"{(time.perf_counter() - preload_started_at) * 1000:.1f} ms"
    )
    cache["startup_debug_lines"] = startup_debug_lines
    cache["preload_results"] = preload_results

    show_step("Starting application…")
    return cache


__all__ = [
    "StartupPreloadContext",
    "StartupPreloadTask",
    "run_startup_preload_tasks",
]
