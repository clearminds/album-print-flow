from __future__ import annotations

from collections.abc import Callable
from typing import Any

from album_printer.startup.core.contributors.printing import (
    build_printing_startup_preload_tasks,
)
from album_printer.startup.core.contributors.source_connectivity import (
    build_source_startup_preload_tasks,
)
from album_printer.startup.core.runner import StartupPreloadTask


def build_startup_preload_tasks(
    parse_cups_options_output_fn: Callable[
        [str], tuple[dict[str, list[str]], dict[str, str]]
    ],
    get_ipp_capabilities_fn: Callable[[str], Any],
    ipp_backend_error_cls: type[Exception],
) -> list[StartupPreloadTask]:
    return [
        *build_printing_startup_preload_tasks(
            parse_cups_options_output_fn=parse_cups_options_output_fn,
            get_ipp_capabilities_fn=get_ipp_capabilities_fn,
            ipp_backend_error_cls=ipp_backend_error_cls,
        ),
        *build_source_startup_preload_tasks(),
    ]


__all__ = ["build_startup_preload_tasks"]
