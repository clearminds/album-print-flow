from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any


def refresh_print_queue_table(
    window: Any,
    *,
    refresh_print_queue_table_fn: Callable[[Any], None],
) -> None:
    refresh_print_queue_table_fn(window)


def current_queue_target(
    window: Any,
    *,
    current_queue_target_fn: Callable[[Any], str],
) -> str:
    return current_queue_target_fn(window)


def current_ipp_target_name(
    window: Any,
    *,
    current_ipp_target_name_fn: Callable[[Any], str],
) -> str:
    return current_ipp_target_name_fn(window)


def enqueue_print_paths(
    window: Any,
    paths: list[Path],
    *,
    enqueue_print_paths_fn: Callable[[Any, list[Path]], None],
) -> None:
    enqueue_print_paths_fn(window, paths)


def process_print_queue(
    window: Any,
    *,
    process_print_queue_fn: Callable[[Any], None],
) -> None:
    process_print_queue_fn(window)


def pause_print_queue(
    window: Any,
    *,
    pause_print_queue_fn: Callable[[Any], None],
) -> None:
    pause_print_queue_fn(window)


def resume_print_queue(
    window: Any,
    *,
    resume_print_queue_fn: Callable[[Any], None],
) -> None:
    resume_print_queue_fn(window)


def remove_selected_queue_item(
    window: Any,
    *,
    remove_selected_queue_item_fn: Callable[[Any], None],
) -> None:
    remove_selected_queue_item_fn(window)


def cancel_selected_queue_item(
    window: Any,
    *,
    cancel_selected_queue_item_fn: Callable[..., None],
    parse_ipp_job_id_fn: Callable[[str], int | None],
    cancel_ipp_job_fn: Callable[..., Any],
    ipp_backend_error_type: type[Exception],
) -> None:
    cancel_selected_queue_item_fn(
        window,
        parse_ipp_job_id=parse_ipp_job_id_fn,
        cancel_ipp_job=cancel_ipp_job_fn,
        ipp_backend_error_type=ipp_backend_error_type,
    )


def clear_finished_queue_items(
    window: Any,
    *,
    clear_finished_queue_items_fn: Callable[[Any], None],
) -> None:
    clear_finished_queue_items_fn(window)


__all__ = [
    "cancel_selected_queue_item",
    "clear_finished_queue_items",
    "current_ipp_target_name",
    "current_queue_target",
    "enqueue_print_paths",
    "pause_print_queue",
    "process_print_queue",
    "refresh_print_queue_table",
    "remove_selected_queue_item",
    "resume_print_queue",
]
