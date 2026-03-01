from __future__ import annotations

import time
from urllib import request as urllib_request

from album_print_flow.startup.core.runner import (
    StartupPreloadContext,
    StartupPreloadTask,
)


def build_source_startup_preload_tasks() -> list[StartupPreloadTask]:
    def preload_google_picker(context: StartupPreloadContext) -> None:
        started_at = time.perf_counter()
        context.show_step("Checking Google Photos connectivity…")
        try:
            with urllib_request.urlopen(
                "https://photospicker.googleapis.com/$discovery/rest?version=v1",
                timeout=4,
            ) as response:
                status_code = int(getattr(response, "status", 0) or 0)
            context.add_debug_line(
                "Startup preload Google Picker: reachable"
                + (f" (status={status_code})" if status_code else "")
                + f" in {(time.perf_counter() - started_at) * 1000:.1f} ms"
            )
            context.cache["google_picker_reachable"] = True
        except Exception as error:
            context.add_debug_line(
                "Startup preload Google Picker: unavailable"
                f" ({error}) in {(time.perf_counter() - started_at) * 1000:.1f} ms"
            )
            context.cache["google_picker_reachable"] = False

    return [
        StartupPreloadTask(
            task_id="google-picker-connectivity",
            label="Checking Google Photos connectivity…",
            run=preload_google_picker,
            critical=False,
        )
    ]


__all__ = ["build_source_startup_preload_tasks"]
