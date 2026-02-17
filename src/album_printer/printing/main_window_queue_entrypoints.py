from __future__ import annotations

from pathlib import Path
from typing import Any

from album_printer.ipp_backend import IppBackendError, cancel_ipp_job
from album_printer.printing.flows.orchestrator import (
    cancel_selected_queue_item as cancel_selected_queue_item_flow,
)
from album_printer.printing.flows.orchestrator import (
    process_print_queue as process_print_queue_flow,
)
from album_printer.printing.flows.queue_actions import (
    cancel_selected_queue_item as cancel_selected_queue_item_actions_flow,
)
from album_printer.printing.flows.queue_actions import (
    clear_finished_queue_items as clear_finished_queue_items_actions_flow,
)
from album_printer.printing.flows.queue_actions import (
    current_ipp_target_name as current_ipp_target_name_actions_flow,
)
from album_printer.printing.flows.queue_actions import (
    current_queue_target as current_queue_target_actions_flow,
)
from album_printer.printing.flows.queue_actions import (
    enqueue_print_paths as enqueue_print_paths_actions_flow,
)
from album_printer.printing.flows.queue_actions import (
    pause_print_queue as pause_print_queue_actions_flow,
)
from album_printer.printing.flows.queue_actions import (
    process_print_queue as process_print_queue_actions_flow,
)
from album_printer.printing.flows.queue_actions import (
    refresh_print_queue_table as refresh_print_queue_table_actions_flow,
)
from album_printer.printing.flows.queue_actions import (
    remove_selected_queue_item as remove_selected_queue_item_actions_flow,
)
from album_printer.printing.flows.queue_actions import (
    resume_print_queue as resume_print_queue_actions_flow,
)
from album_printer.printing.flows.queue_management import (
    clear_finished_queue_items as clear_finished_queue_items_flow,
)
from album_printer.printing.flows.queue_management import (
    current_ipp_target_name as current_ipp_target_name_flow,
)
from album_printer.printing.flows.queue_management import (
    current_queue_target as current_queue_target_flow,
)
from album_printer.printing.flows.queue_management import (
    enqueue_print_paths as enqueue_print_paths_flow,
)
from album_printer.printing.flows.queue_management import (
    pause_print_queue as pause_print_queue_flow,
)
from album_printer.printing.flows.queue_management import (
    remove_selected_queue_item as remove_selected_queue_item_flow,
)
from album_printer.printing.flows.queue_management import (
    resume_print_queue as resume_print_queue_flow,
)
from album_printer.printing_helpers import parse_ipp_job_id
from album_printer.ui.print_queue_presenter import (
    refresh_print_queue_table as refresh_print_queue_table_presenter,
)


def refresh_print_queue_table(window: Any) -> None:
    refresh_print_queue_table_actions_flow(
        window,
        refresh_print_queue_table_fn=refresh_print_queue_table_presenter,
    )


def current_queue_target(window: Any) -> str:
    return current_queue_target_actions_flow(
        window,
        current_queue_target_fn=current_queue_target_flow,
    )


def current_ipp_target_name(window: Any) -> str:
    return current_ipp_target_name_actions_flow(
        window,
        current_ipp_target_name_fn=current_ipp_target_name_flow,
    )


def enqueue_print_paths(window: Any, paths: list[Path]) -> None:
    enqueue_print_paths_actions_flow(
        window,
        paths,
        enqueue_print_paths_fn=enqueue_print_paths_flow,
    )


def process_print_queue(window: Any) -> None:
    process_print_queue_actions_flow(
        window,
        process_print_queue_fn=process_print_queue_flow,
    )


def pause_print_queue(window: Any) -> None:
    pause_print_queue_actions_flow(
        window,
        pause_print_queue_fn=pause_print_queue_flow,
    )


def resume_print_queue(window: Any) -> None:
    resume_print_queue_actions_flow(
        window,
        resume_print_queue_fn=resume_print_queue_flow,
    )


def remove_selected_queue_item(window: Any) -> None:
    remove_selected_queue_item_actions_flow(
        window,
        remove_selected_queue_item_fn=remove_selected_queue_item_flow,
    )


def cancel_selected_queue_item(window: Any) -> None:
    cancel_selected_queue_item_actions_flow(
        window,
        cancel_selected_queue_item_fn=cancel_selected_queue_item_flow,
        parse_ipp_job_id_fn=parse_ipp_job_id,
        cancel_ipp_job_fn=cancel_ipp_job,
        ipp_backend_error_type=IppBackendError,
    )


def clear_finished_queue_items(window: Any) -> None:
    clear_finished_queue_items_actions_flow(
        window,
        clear_finished_queue_items_fn=clear_finished_queue_items_flow,
    )


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
