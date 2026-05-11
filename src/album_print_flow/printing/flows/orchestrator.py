from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from album_print_flow.printing.flows.cups import (
    print_all_via_cups as print_all_via_cups_flow,
)
from album_print_flow.printing.flows.dispatch import (
    execute_print_paths as execute_print_paths_flow,
)
from album_print_flow.printing.flows.export_jpg import (
    export_all_as_jpg as export_all_as_jpg_flow,
)
from album_print_flow.printing.flows.ipp import (
    print_all_via_ipp as print_all_via_ipp_flow,
)
from album_print_flow.printing.flows.qt import print_all_via_qt as print_all_via_qt_flow
from album_print_flow.printing.flows.queue_cancel import (
    cancel_selected_queue_item as cancel_selected_queue_item_flow,
)
from album_print_flow.printing.flows.queue_controller import (
    process_print_queue as process_print_queue_flow,
)


def process_print_queue(window: Any) -> None:
    process_print_queue_flow(window)


def cancel_selected_queue_item(
    window: Any,
    *,
    parse_ipp_job_id: Any,
    cancel_ipp_job: Any,
    ipp_backend_error_type: type[Exception],
) -> None:
    cancel_selected_queue_item_flow(
        window,
        parse_ipp_job_id=parse_ipp_job_id,
        cancel_ipp_job=cancel_ipp_job,
        ipp_backend_error_type=ipp_backend_error_type,
    )


def print_all_via_cups(
    window: Any,
    paths: list[Path],
    printer_name: str,
    resolve_cups_media_value_fn: Callable[[str, list[str], bool], str],
    render_image_fn: Callable[..., Any],
    apply_borderless_content_scale_fn: Callable[[Any, int], Any],
    parse_cups_request_id_fn: Callable[[str], str],
    query_cups_job_status_text_fn: Callable[[str], str],
) -> tuple[list[Path], list[str], str, dict[str, str]]:
    return print_all_via_cups_flow(
        window,
        paths,
        printer_name,
        resolve_cups_media_value_fn,
        render_image_fn,
        apply_borderless_content_scale_fn,
        parse_cups_request_id_fn,
        query_cups_job_status_text_fn,
    )


def print_all_via_qt(
    window: Any,
    paths: list[Path],
    printer_name: str,
    media_size_mm_from_value_fn: Callable[[str], tuple[float, float] | None],
    render_image_fn: Callable[..., Any],
    ratios_match_either_orientation_fn: Callable[[float, float, float, float], bool],
) -> tuple[list[Path], list[str], str]:
    return print_all_via_qt_flow(
        window,
        paths,
        printer_name,
        media_size_mm_from_value_fn,
        render_image_fn,
        ratios_match_either_orientation_fn,
    )


def print_all_via_ipp(
    window: Any,
    paths: list[Path],
    ipp_uri: str,
    render_image_fn: Callable[..., Any],
    print_jobs_via_ipp_fn: Callable[
        ..., tuple[list[Path], list[str], str, dict[str, str]]
    ],
    ipp_backend_error_cls: type[Exception],
) -> tuple[list[Path], list[str], str, dict[str, str]]:
    return print_all_via_ipp_flow(
        window,
        paths,
        ipp_uri,
        render_image_fn,
        print_jobs_via_ipp_fn,
        ipp_backend_error_cls,
    )


def export_all_as_jpg(
    window: Any,
    paths: list[Path],
    export_root: str,
    render_image_fn: Callable[..., Any],
    *,
    settings_by_path: dict[Path, Any] | None = None,
    date_used_by_path: dict[Path, datetime] | None = None,
    log_fn: Any | None = None,
    progress_fn: Any | None = None,
) -> tuple[list[Path], list[str], str, str, dict[str, str]]:
    return export_all_as_jpg_flow(
        window,
        paths,
        export_root,
        render_image_fn,
        settings_by_path=settings_by_path,
        date_used_by_path=date_used_by_path,
        log_fn=log_fn,
        progress_fn=progress_fn,
    )


def execute_print_paths(
    window: Any,
    paths: list[Path],
) -> tuple[list[Path], list[str], str, str, str, dict[str, str]]:
    return execute_print_paths_flow(window, paths)


__all__ = [
    "cancel_selected_queue_item",
    "execute_print_paths",
    "export_all_as_jpg",
    "print_all_via_cups",
    "print_all_via_ipp",
    "print_all_via_qt",
    "process_print_queue",
]
