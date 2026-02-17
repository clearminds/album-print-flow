from __future__ import annotations

from typing import Any

from PySide6.QtCore import QTimer


def process_print_queue(window: Any) -> None:
    if window.print_queue_processing or window.print_queue_paused:
        return

    pending_item: dict[str, object] | None = None
    for item in window.print_queue_items:
        if str(item.get("status", "")) == "Pending":
            pending_item = item
            break

    if pending_item is None:
        return

    window.print_queue_processing = True
    pending_item["status"] = "Printing"
    pending_item["completed_images"] = 0
    pending_item["detail"] = "Printing in progress"
    window.refresh_print_queue_table()

    paths = pending_item.get("paths", [])
    if not isinstance(paths, list):
        paths = []
    try:
        printed, failed, error, target_name, backend, job_ids = (
            window.execute_print_paths(paths)
        )

        queue_only_backend = backend in {"CUPS", "IPP"}

        if printed and not failed and not error:
            pending_item["status"] = "Queued" if queue_only_backend else "Done"
            pending_item["detail"] = (
                f"Queued {len(printed)}"
                if queue_only_backend
                else f"Printed {len(printed)}"
            )
            pending_item["completed_images"] = len(printed)
        elif printed and (failed or error):
            pending_item["status"] = "Partial"
            pending_item["detail"] = (
                f"Queued {len(printed)}, failed {len(failed)}"
                if queue_only_backend
                else f"Printed {len(printed)}, failed {len(failed)}"
            )
            pending_item["completed_images"] = len(printed) + len(failed)
        else:
            pending_item["status"] = "Failed"
            pending_item["detail"] = error or "No items printed"
            pending_item["completed_images"] = 0

        pending_item["target"] = target_name
        pending_item["backend"] = backend
        pending_item["job_ids"] = dict(job_ids)
    except Exception as error:
        pending_item["status"] = "Failed"
        pending_item["detail"] = f"Queue error: {error}"
        window.append_log("ERROR", f"Queue processing failed: {error}")
    finally:
        window.print_queue_processing = False
        window.refresh_print_queue_table()

        has_pending = any(
            str(item.get("status", "")) == "Pending"
            for item in window.print_queue_items
        )
        if has_pending and not window.print_queue_paused:
            QTimer.singleShot(0, window.process_print_queue)
