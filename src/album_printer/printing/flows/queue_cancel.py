from __future__ import annotations

import shutil
import subprocess
from typing import Any

from PySide6.QtWidgets import QMessageBox


def cancel_selected_queue_item(
    window: Any,
    *,
    parse_ipp_job_id: Any,
    cancel_ipp_job: Any,
    ipp_backend_error_type: type[Exception],
) -> None:
    row = window.print_queue_table.currentRow()
    if row < 0 or row >= len(window.print_queue_items):
        return

    item = window.print_queue_items[row]
    queue_id = item.get("id")
    status = str(item.get("status", ""))

    if status == "Pending":
        item["status"] = "Cancelled"
        item["detail"] = "Cancelled before printing"
        window.append_log("INFO", f"Cancelled queue job #{queue_id} before start")
        window.refresh_print_queue_table()
        QMessageBox.information(
            window,
            "Queue job cancelled",
            f"Queue job #{queue_id} was cancelled before printing started.",
        )
        return

    backend = str(item.get("backend", ""))
    target = str(item.get("target", ""))
    job_ids_raw = item.get("job_ids")
    job_ids = job_ids_raw if isinstance(job_ids_raw, dict) else {}

    if not job_ids:
        QMessageBox.information(
            window,
            "No job IDs",
            "No backend job IDs are available for the selected queue item.",
        )
        return

    confirm = QMessageBox.question(
        window,
        "Cancel backend jobs",
        (
            f"Cancel {len(job_ids)} backend job(s) for queue job #{queue_id}?\n\n"
            f"Backend: {backend or '-'}\n"
            f"Target: {target or '-'}"
        ),
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No,
    )
    if confirm != QMessageBox.StandardButton.Yes:
        window.append_log(
            "INFO",
            f"Cancel aborted by user for queue job #{queue_id}",
        )
        return

    cancelled_count = 0
    errors: list[str] = []

    if backend in {"CUPS", "Auto"}:
        if shutil.which("cancel") is None:
            errors.append("CUPS cancel command not available")
        else:
            for path_name, request_id in job_ids.items():
                request_text = str(request_id).strip()
                if not request_text:
                    continue
                result = subprocess.run(
                    ["cancel", request_text],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if result.returncode == 0:
                    cancelled_count += 1
                else:
                    detail = (result.stderr or result.stdout or "").strip()
                    errors.append(
                        f"{path_name} ({request_text}): {detail or 'cancel failed'}"
                    )
    elif backend == "IPP":
        for path_name, raw_job_id in job_ids.items():
            numeric_job_id = parse_ipp_job_id(str(raw_job_id))
            if numeric_job_id is None:
                errors.append(f"{path_name}: invalid job-id '{raw_job_id}'")
                continue
            try:
                cancel_ipp_job(target, numeric_job_id)
                cancelled_count += 1
            except ipp_backend_error_type as error:
                errors.append(f"{path_name} ({numeric_job_id}): {error}")
    else:
        errors.append(f"Backend '{backend}' does not support cancel")

    if cancelled_count:
        item["status"] = "Cancelled"
        item["detail"] = f"Cancelled {cancelled_count} job(s)"
        window.append_log(
            "INFO",
            f"Cancelled {cancelled_count} backend job(s) for queue job #{queue_id}",
        )

    if errors:
        window.append_log(
            "WARNING",
            "Queue cancel issues: " + " | ".join(errors[:6]),
        )

    window.refresh_print_queue_table()

    if cancelled_count and not errors:
        QMessageBox.information(
            window,
            "Cancel complete",
            f"Cancelled {cancelled_count} backend job(s) for queue job #{queue_id}.",
        )
    elif cancelled_count and errors:
        QMessageBox.warning(
            window,
            "Cancel partial",
            (
                "Cancelled "
                f"{cancelled_count} backend job(s) "
                f"for queue job #{queue_id}.\n\n"
                f"Some cancels failed:\n- " + "\n- ".join(errors[:5])
            ),
        )
    elif errors:
        QMessageBox.warning(
            window,
            "Cancel failed",
            "Could not cancel backend jobs:\n- " + "\n- ".join(errors[:6]),
        )
