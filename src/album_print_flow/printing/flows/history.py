from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from PySide6.QtWidgets import QMessageBox, QTableWidgetItem

from album_print_flow.ui.status_presenter import present_status


def ensure_photo_entry_for_path(window: Any, path: Path) -> dict[str, object]:
    photos = window.folder_metadata.get("photos")
    if not isinstance(photos, dict):
        photos = {}
        window.folder_metadata["photos"] = photos

    key = window.metadata_key_for_path(path)
    entry = photos.get(key)
    if not isinstance(entry, dict):
        entry = {}
    photos[key] = entry
    return entry


def is_already_printed(window: Any, path: Path) -> bool:
    entry = window.photo_entry_for_path(path)
    try:
        return int(entry.get("total_printed", 0)) > 0
    except (TypeError, ValueError):
        return False


def latest_print_status_for_path(window: Any, path: Path) -> str:
    if window.is_ignored_for_print_all(path):
        return "Ignored"

    entry = window.photo_entry_for_path(path)
    status_raw = str(entry.get("last_print_status", "")).strip().lower()
    status_map = {
        "printed": "Printed",
        "failed": "Failed",
        "partial": "Partial",
    }
    if status_raw in status_map:
        return status_map[status_raw]

    try:
        total_printed = int(entry.get("total_printed", 0))
    except (TypeError, ValueError):
        total_printed = 0
    if total_printed > 0:
        return "Printed"
    return "Not Printed"


def is_ignored_for_print_all(window: Any, path: Path) -> bool:
    entry = window.photo_entry_for_path(path)
    return bool(entry.get("ignore_in_print_all", False))


def should_include_in_print_all(window: Any, path: Path) -> bool:
    if window.is_ignored_for_print_all(path):
        return False
    if window.is_already_printed(path):
        return False
    return True


def on_ignore_for_print_all_toggled(window: Any, checked: bool) -> None:
    if window._restoring_settings or window.current_folder is None:
        return
    path = window.selected_path()
    if path is None:
        return

    entry = window.ensure_photo_entry_for_path(path)
    entry["ignore_in_print_all"] = bool(checked)
    window.save_folder_metadata()
    window.sync_global_source_state_from_path(path)
    window.refresh_image_list_labels(path)
    window.update_selected_print_info()


def update_selected_print_info(window: Any) -> None:
    path = window.selected_path()

    def set_attempt_rows(rows: list[tuple[str, str, str, str, str]]) -> None:
        window.print_attempts_table.setRowCount(len(rows))
        for row_index, (
            time_text,
            status_text,
            backend_text,
            job_text,
            error_text,
        ) in enumerate(rows):
            window.print_attempts_table.setItem(
                row_index, 0, QTableWidgetItem(time_text)
            )
            window.print_attempts_table.setItem(
                row_index, 1, QTableWidgetItem(status_text)
            )
            window.print_attempts_table.setItem(
                row_index, 2, QTableWidgetItem(backend_text)
            )
            window.print_attempts_table.setItem(
                row_index, 3, QTableWidgetItem(job_text)
            )
            window.print_attempts_table.setItem(
                row_index, 4, QTableWidgetItem(error_text)
            )

    if path is None:
        window.print_status_label.setText("Not Printed")
        set_attempt_rows([("-", "-", "-", "-", "No Print Attempts")])
        return

    window.print_status_label.setText(window.latest_print_status_for_path(path))
    entry = window.photo_entry_for_path(path)
    attempts = entry.get("print_attempts")

    if not isinstance(attempts, list) or not attempts:
        set_attempt_rows([("-", "-", "-", "-", "No Print Attempts")])
        return

    rows: list[tuple[str, str, str, str, str]] = []
    status_map = {
        "printed": "Printed",
        "failed": "Failed",
        "partial": "Partial",
    }

    for attempt in reversed(attempts[-20:]):
        if isinstance(attempt, str):
            text = attempt.strip()
            if text:
                rows.append(("-", "Unknown", "-", "-", text))
            continue

        if not isinstance(attempt, dict):
            continue

        timestamp = str(attempt.get("timestamp", "")).strip() or "-"
        status_raw = str(attempt.get("status", "")).strip().lower()
        status = status_map.get(
            status_raw, status_raw.title() if status_raw else "Unknown"
        )
        backend = str(attempt.get("backend", "")).strip() or "-"
        job_id = str(attempt.get("job_id", "")).strip() or "-"
        error_text = str(attempt.get("error", "")).strip() or "-"
        rows.append((timestamp, status, backend, job_id, error_text))

    if not rows:
        rows = [("-", "-", "-", "-", "No Print Attempts")]

    set_attempt_rows(rows)


def mark_selected_as_printed(window: Any) -> None:
    if window.current_folder is None:
        return
    path = window.selected_path()
    if path is None:
        return

    entry = window.ensure_photo_entry_for_path(path)
    timestamp = datetime.now().isoformat(timespec="seconds")
    entry["total_printed"] = int(entry.get("total_printed", 0)) + 1
    entry["last_print_status"] = "printed"
    entry["last_printed_at"] = timestamp
    entry["last_print_error"] = ""
    entry["last_printer"] = "Manual"
    entry["last_backend"] = "Manual"
    entry["last_print_job_id"] = f"manual-{uuid.uuid4().hex[:12]}"

    attempts = entry.get("print_attempts")
    if not isinstance(attempts, list):
        attempts = []
    attempts.append(
        {
            "timestamp": timestamp,
            "status": "printed",
            "backend": "Manual",
            "printer": "Manual",
            "job_id": entry["last_print_job_id"],
            "error": "",
        }
    )
    entry["print_attempts"] = attempts[-50:]

    window.save_folder_metadata()
    window.sync_global_source_state_from_path(path)
    window.refresh_image_list_labels(path)
    window.update_selected_print_info()
    present_status(window, f"Marked as printed: {path.name}")


def clear_failed_logs_for_selected(window: Any) -> None:
    if window.current_folder is None:
        return
    path = window.selected_path()
    if path is None:
        return

    entry = window.ensure_photo_entry_for_path(path)
    attempts = entry.get("print_attempts")
    if isinstance(attempts, list):
        kept: list[object] = []
        for item in attempts:
            if isinstance(item, dict):
                status = str(item.get("status", "")).strip().lower()
                if status == "failed":
                    continue
            kept.append(item)
        entry["print_attempts"] = kept[-50:]

    if str(entry.get("last_print_status", "")).strip().lower() == "failed":
        if window.is_already_printed(path):
            entry["last_print_status"] = "printed"
        else:
            entry["last_print_status"] = ""
    entry["last_print_error"] = ""

    window.save_folder_metadata()
    window.sync_global_source_state_from_path(path)
    window.refresh_image_list_labels(path)
    window.update_selected_print_info()
    present_status(window, f"Cleared failed logs: {path.name}")


def clear_selected_print_status(window: Any) -> None:
    path = window.selected_path()
    if path is None:
        QMessageBox.information(window, "Clear Print Status", "No image selected.")
        return
    if window.current_folder is None:
        return

    entry = window.ensure_photo_entry_for_path(path)
    entry["total_printed"] = 0
    entry["last_print_status"] = ""
    entry["last_print_error"] = ""

    window.save_folder_metadata()
    window.sync_global_source_state_from_path(path)
    window.refresh_image_list_labels(path)
    window.update_selected_print_info()
    present_status(window, f"Cleared print status: {path.name}")


def record_print_history(
    window: Any,
    attempted_paths: list[Path],
    printed_paths: list[Path],
    failed_names: list[str],
    printer_name: str,
    backend: str,
    error: str,
    job_ids: dict[str, str] | None = None,
) -> None:
    if window.current_folder is None or not attempted_paths:
        return

    timestamp = datetime.now().isoformat(timespec="seconds")
    photos = window.folder_metadata.get("photos")
    if not isinstance(photos, dict):
        photos = {}
        window.folder_metadata["photos"] = photos

    printed_set = set(printed_paths)
    effective_job_ids = dict(job_ids or {})
    event_job_ids: dict[str, str] = {}

    for path in attempted_paths:
        photo_key = window.metadata_key_for_path(path)
        entry = photos.get(photo_key)
        if not isinstance(entry, dict):
            entry = {}
        job_id = effective_job_ids.get(photo_key) or effective_job_ids.get(path.name)
        if not job_id:
            job_id = f"{backend.lower()}-{uuid.uuid4().hex[:12]}"
            effective_job_ids[photo_key] = job_id
        event_job_ids[photo_key] = job_id
        status = "printed" if path in printed_set else "failed"
        if status == "printed":
            entry["total_printed"] = int(entry.get("total_printed", 0)) + 1
            entry["last_printed_at"] = timestamp
        entry["last_print_status"] = status
        entry["photo_key"] = photo_key
        entry["source_photo_id"] = window.source_photo_id_for_path(path)
        entry["last_print_job_id"] = job_id
        entry["last_print_error"] = error
        entry["last_printer"] = printer_name
        entry["last_backend"] = backend
        entry["last_project_settings"] = window.current_project_settings_payload()
        entry["last_image_settings"] = window.image_settings_for_path(path)

        attempts = entry.get("print_attempts")
        if not isinstance(attempts, list):
            attempts = []
        attempts.append(
            {
                "timestamp": timestamp,
                "status": status,
                "backend": backend,
                "printer": printer_name,
                "job_id": job_id,
                "error": error,
            }
        )
        entry["print_attempts"] = attempts[-50:]
        photos[photo_key] = entry
        window.sync_global_source_state_from_path(path)

    events = window.folder_metadata.get("print_events")
    if not isinstance(events, list):
        events = []
    events.append(
        {
            "timestamp": timestamp,
            "printer": printer_name,
            "backend": backend,
            "count": len(attempted_paths),
            "printed_count": len(printed_paths),
            "failed": failed_names,
            "error": error,
            "job_ids": event_job_ids,
            "photos": [window.metadata_key_for_path(path) for path in attempted_paths],
            "project_settings": window.current_project_settings_payload(),
        }
    )
    window.folder_metadata["print_events"] = events[-500:]
    window.save_folder_metadata()


__all__ = [
    "clear_failed_logs_for_selected",
    "clear_selected_print_status",
    "ensure_photo_entry_for_path",
    "is_already_printed",
    "is_ignored_for_print_all",
    "latest_print_status_for_path",
    "mark_selected_as_printed",
    "on_ignore_for_print_all_toggled",
    "record_print_history",
    "should_include_in_print_all",
    "update_selected_print_info",
]
