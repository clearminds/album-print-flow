from __future__ import annotations

from collections.abc import Callable
from typing import Any

from album_print_flow.startup.core.registry import build_startup_preload_tasks
from album_print_flow.startup.core.runner import run_startup_preload_tasks


def preload_startup_cache(
    *,
    splash: Any,
    parse_cups_options_output_fn: Callable[
        [str], tuple[dict[str, list[str]], dict[str, str]]
    ],
    get_ipp_capabilities_fn: Callable[[str], Any],
    ipp_backend_error_cls: type[Exception],
    settings_org: str,
    settings_app: str,
    is_debugger_attached_fn: Callable[[], bool],
    mode: str = "mixed",
) -> dict[str, object]:
    tasks = build_startup_preload_tasks(
        parse_cups_options_output_fn=parse_cups_options_output_fn,
        get_ipp_capabilities_fn=get_ipp_capabilities_fn,
        ipp_backend_error_cls=ipp_backend_error_cls,
    )

    cache = run_startup_preload_tasks(
        splash=splash,
        tasks=tasks,
        settings_org=settings_org,
        settings_app=settings_app,
        is_debugger_attached_fn=is_debugger_attached_fn,
        mode=mode,
    )

    cache.setdefault("printers", [])
    cache.setdefault("cups_capabilities", {})
    cache.setdefault("ipp_capabilities", {})
    cache.setdefault("startup_debug_lines", [])
    return cache


__all__ = ["preload_startup_cache"]
