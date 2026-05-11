from __future__ import annotations

from datetime import datetime
from typing import Any

from PySide6.QtWidgets import QMessageBox

from album_print_flow.ui.status_presenter import present_log


def current_ipp_target_name(window: Any) -> str:
    ipp_uri = str(window.ipp_uri_value).strip()
    if not ipp_uri:
        return "IPP"

    cached = window.ipp_capabilities_cache.get(ipp_uri)
    if cached is not None:
        friendly = str(getattr(cached, "printer_name", "")).strip()
        if friendly:
            return friendly
    return ipp_uri


def current_queue_target(window: Any) -> str:
    backend = str(window.print_backend_value)
    if backend == "IPP":
        return current_ipp_target_name(window)
    if window.printer_value:
        return str(window.printer_value)
    return backend


def enqueue_print_paths(window: Any, paths: list[object]) -> None:
    if not paths:
        return
    queue_paths_batches = [list(paths)]
    if len(paths) > 1 and window.print_backend_value != "Export JPG":
        queue_paths_batches = [[path] for path in paths]

    queue_ids: list[int] = []
    for batch in queue_paths_batches:
        total_images = len(batch)
        queue_item = {
            "id": window.print_queue_next_id,
            "paths": list(batch),
            "total_images": total_images,
            "completed_images": 0,
            "status": "Pending",
            "target": current_queue_target(window),
            "detail": "Queued",
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
        window.print_queue_next_id += 1
        window.print_queue_items.append(queue_item)
        queue_ids.append(int(queue_item["id"]))

    window.refresh_print_queue_table()
    if len(queue_paths_batches) == 1:
        present_log(
            window,
            "INFO",
            f"Queued print job #{queue_ids[0]} ({len(paths)} image(s))",
        )
    else:
        present_log(
            window,
            "INFO",
            (
                f"Queued {len(queue_paths_batches)} print jobs "
                f"(1 image each, {len(paths)} total image(s))"
            ),
        )
    window.process_print_queue()


def pause_print_queue(window: Any) -> None:
    window.print_queue_paused = True
    present_log(window, "INFO", "Print queue paused")
    window.refresh_print_queue_table()


def resume_print_queue(window: Any) -> None:
    window.print_queue_paused = False
    present_log(window, "INFO", "Print queue resumed")
    window.refresh_print_queue_table()
    window.process_print_queue()


def remove_selected_queue_item(window: Any) -> None:
    row = window.print_queue_table.currentRow()
    if row < 0 or row >= len(window.print_queue_items):
        return
    status = str(window.print_queue_items[row].get("status", ""))
    if status == "Printing":
        QMessageBox.information(
            window,
            "Queue item busy",
            "Cannot remove a job that is currently printing.",
        )
        return
    queue_id = window.print_queue_items[row].get("id")
    window.print_queue_items.pop(row)
    present_log(window, "INFO", f"Removed queue job #{queue_id}")
    window.refresh_print_queue_table()


def clear_finished_queue_items(window: Any) -> None:
    finished_states = {"Done", "Failed", "Partial", "Cancelled"}
    before = len(window.print_queue_items)
    window.print_queue_items = [
        item
        for item in window.print_queue_items
        if str(item.get("status", "")) not in finished_states
    ]
    removed = before - len(window.print_queue_items)
    if removed:
        present_log(window, "INFO", f"Cleared {removed} finished queue job(s)")
    window.refresh_print_queue_table()


__all__ = [
    "clear_finished_queue_items",
    "current_ipp_target_name",
    "current_queue_target",
    "enqueue_print_paths",
    "pause_print_queue",
    "remove_selected_queue_item",
    "resume_print_queue",
]
