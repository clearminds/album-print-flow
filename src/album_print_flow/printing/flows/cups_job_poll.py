from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

TERMINAL_STATES = {"completed", "canceled", "aborted", "not-found"}


def start_cups_job_poll_if_needed(window: Any) -> None:
    has_queued = any(
        str(item.get("status", "")) == "Queued"
        and str(item.get("backend", "")) == "CUPS"
        and isinstance(item.get("job_ids"), dict)
        and item["job_ids"]
        for item in window.print_queue_items
    )
    if has_queued and not window.cups_job_poll_timer.isActive():
        window.cups_job_poll_timer.start()
        window.append_log("DEBUG", "CUPS job poll timer started")


def poll_cups_job_statuses(
    window: Any,
    *,
    query_cups_job_state_fn: Callable[[str], str],
) -> None:
    queued_items = [
        item
        for item in window.print_queue_items
        if str(item.get("status", "")) == "Queued"
        and str(item.get("backend", "")) == "CUPS"
        and isinstance(item.get("job_ids"), dict)
        and item["job_ids"]
    ]

    if not queued_items:
        window.cups_job_poll_timer.stop()
        window.append_log("DEBUG", "CUPS job poll timer stopped (no queued items)")
        return

    any_updated = False
    for item in queued_items:
        job_ids: dict[str, str] = item["job_ids"]
        all_terminal = True
        any_failed = False

        for _file_name, request_id in job_ids.items():
            state = query_cups_job_state_fn(request_id)
            if state not in TERMINAL_STATES:
                all_terminal = False
                continue
            if state in {"canceled", "aborted"}:
                any_failed = True
            elif state == "not-found":
                any_failed = True

        if not all_terminal:
            continue

        paths = item.get("paths", [])
        total_count = len(paths) if isinstance(paths, list) else 0

        if any_failed:
            item["status"] = "Failed"
            item["detail"] = "CUPS job failed or canceled"
            _update_photo_statuses(window, item, job_ids, query_cups_job_state_fn)
        else:
            item["status"] = "Done"
            item["detail"] = f"Printed {total_count}"
        any_updated = True
        window.append_log(
            "INFO",
            f"CUPS poll: queue #{item.get('id')} → {item['status']}",
        )

    if any_updated:
        window.refresh_print_queue_table()
        window.refresh_image_list_labels(window.selected_path())
        window.update_selected_print_info()

    still_queued = any(
        str(item.get("status", "")) == "Queued"
        and str(item.get("backend", "")) == "CUPS"
        for item in window.print_queue_items
    )
    if not still_queued:
        window.cups_job_poll_timer.stop()
        window.append_log("DEBUG", "CUPS job poll timer stopped (all resolved)")


def _update_photo_statuses(
    window: Any,
    item: dict[str, object],
    job_ids: dict[str, str],
    query_cups_job_state_fn: Callable[[str], str],
) -> None:
    paths = item.get("paths", [])
    if not isinstance(paths, list):
        return

    photos = window.folder_metadata.get("photos")
    if not isinstance(photos, dict):
        return

    for path in paths:
        if not isinstance(path, Path):
            continue
        file_name = path.name
        request_id = job_ids.get(file_name, "")
        if not request_id:
            continue

        state = query_cups_job_state_fn(request_id)
        photo_key = window.metadata_key_for_path(path)
        entry = photos.get(photo_key)
        if not isinstance(entry, dict):
            continue

        if state == "completed":
            entry["last_print_status"] = "printed"
        elif state in {"canceled", "aborted", "not-found"}:
            entry["last_print_status"] = "failed"

    window.save_folder_metadata()


__all__ = [
    "poll_cups_job_statuses",
    "start_cups_job_poll_if_needed",
]
