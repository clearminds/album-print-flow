from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTableWidgetItem


def refresh_print_queue_table(window: Any) -> None:
    window.print_queue_table.setRowCount(len(window.print_queue_items))
    for row, item in enumerate(window.print_queue_items):
        queue_id = int(item.get("id", 0))
        status = str(item.get("status", "Pending"))
        paths = item.get("paths", [])
        count = len(paths) if isinstance(paths, list) else 0
        target = str(item.get("target", ""))
        detail = str(item.get("detail", ""))

        id_item = QTableWidgetItem(str(queue_id))
        status_item = QTableWidgetItem(status)
        count_item = QTableWidgetItem(str(count))
        target_item = QTableWidgetItem(target)
        detail_item = QTableWidgetItem(detail)

        id_item.setFlags(id_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        status_item.setFlags(status_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        count_item.setFlags(count_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        target_item.setFlags(target_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        detail_item.setFlags(detail_item.flags() & ~Qt.ItemFlag.ItemIsEditable)

        window.print_queue_table.setItem(row, 0, id_item)
        window.print_queue_table.setItem(row, 1, status_item)
        window.print_queue_table.setItem(row, 2, count_item)
        window.print_queue_table.setItem(row, 3, target_item)
        window.print_queue_table.setItem(row, 4, detail_item)

    if window.print_queue_items:
        total_images = 0
        completed_images = 0
        active_jobs = 0
        for item in window.print_queue_items:
            paths = item.get("paths")
            inferred_total = len(paths) if isinstance(paths, list) else 0
            item_total = int(item.get("total_images", inferred_total) or 0)
            item_completed = int(item.get("completed_images", 0) or 0)

            total_images += max(0, item_total)
            completed_images += max(0, min(item_completed, item_total))

            if str(item.get("status", "")) == "Printing":
                active_jobs += 1

        if total_images <= 0:
            total_images = len(window.print_queue_items)
            completed_images = min(completed_images, total_images)
        if not window.queue_progress_bar.isVisible():
            window.queue_progress_bar.show()
        window.queue_progress_bar.setRange(0, total_images)
        window.queue_progress_bar.setValue(max(0, min(completed_images, total_images)))
        suffix = f" • active {active_jobs}" if active_jobs else ""
        window.queue_progress_bar.setFormat(
            f"Queue {completed_images}/{total_images} images{suffix}"
        )
    else:
        window.queue_progress_bar.hide()
        window.queue_progress_bar.setRange(0, 1)
        window.queue_progress_bar.setValue(0)
        window.queue_progress_bar.setFormat("Queue 0/0")

    window.queue_pause_button.setEnabled(
        window.print_queue_processing
        or any(
            str(item.get("status", "")) == "Pending"
            for item in window.print_queue_items
        )
    )
    window.queue_resume_button.setEnabled(
        window.print_queue_paused
        and any(
            str(item.get("status", "")) == "Pending"
            for item in window.print_queue_items
        )
    )
    window.queue_cancel_button.setEnabled(bool(window.print_queue_items))
    window.update_queue_panel_max_width()
