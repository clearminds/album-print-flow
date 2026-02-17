from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from album_printer.ui.status_presenter import present_status


def reset_table_metadata_tracking(
    window: Any,
    *,
    clear_indexing_status_message: bool,
    reset_paused: bool,
) -> None:
    window.table_metadata_generation += 1
    window.table_metadata_timer.stop()
    window.table_metadata_pending_paths = []
    window.table_metadata_total_paths = 0
    window.table_metadata_cached_hits = 0
    window.table_metadata_computed_paths = 0
    window.table_metadata_skipped_paths = 0
    window.table_metadata_changed_paths = 0
    if reset_paused:
        window.table_metadata_paused = False
    if clear_indexing_status_message:
        current_status = window.statusBar().currentMessage()
        if current_status.startswith("Indexing metadata…"):
            window.statusBar().clearMessage()


def start_table_metadata_resolution(window: Any) -> None:
    if (
        window.source_load_in_progress
        or window.source_refresh_in_progress
        or window.album_sync_bootstrap_active
    ) and window.current_source_id == "google-photos-album-url":
        reset_table_metadata_tracking(
            window,
            clear_indexing_status_message=False,
            reset_paused=True,
        )
        window.clear_footer_progress()
        present_status(window, "Metadata indexing deferred until album sync completes")
        window.append_log(
            "DEBUG",
            "Metadata indexing deferred while album sync is active",
        )
        return

    window.table_metadata_generation += 1
    total_paths = len(window.image_paths)
    window.table_metadata_pending_paths = [
        path
        for path in window.image_paths
        if window.cached_table_values_for_path(path) is None
    ]
    window.table_metadata_cached_hits = max(
        0,
        total_paths - len(window.table_metadata_pending_paths),
    )
    window.table_metadata_computed_paths = 0
    window.table_metadata_skipped_paths = 0
    window.table_metadata_changed_paths = 0
    window.table_metadata_total_paths = len(window.table_metadata_pending_paths)
    window.table_metadata_paused = False
    if not window.table_metadata_pending_paths:
        window.table_metadata_timer.stop()
        window.clear_footer_progress()
        window.append_log(
            "DEBUG",
            "Metadata cache summary: "
            f"total={total_paths} "
            f"cached_hits={window.table_metadata_cached_hits} "
            "queued=0 computed=0 skipped=0 changed=0",
        )
        present_status(window, "Metadata cache ready", 800)
        return
    window.append_log(
        "DEBUG",
        "Metadata cache summary: "
        f"total={total_paths} "
        f"cached_hits={window.table_metadata_cached_hits} "
        f"queued={window.table_metadata_total_paths}",
    )
    window.update_footer_progress("Metadata", 0, window.table_metadata_total_paths)
    present_status(window, f"Indexing metadata… 0/{window.table_metadata_total_paths}")
    window.table_metadata_timer.start()


def note_table_scrolled(
    window: Any,
    *,
    monotonic_fn: Callable[[], float] = time.monotonic,
) -> None:
    window.table_metadata_last_scroll_at = monotonic_fn()


def current_table_metadata_batch_size(
    window: Any,
    *,
    scroll_window_seconds: float,
    batch_size_scrolling: int,
    batch_size_idle: int,
    monotonic_fn: Callable[[], float] = time.monotonic,
) -> int:
    elapsed = monotonic_fn() - window.table_metadata_last_scroll_at
    if elapsed < scroll_window_seconds:
        return max(1, int(batch_size_scrolling))
    return max(1, int(batch_size_idle))


def process_table_metadata_batch(
    window: Any,
    *,
    table_col_date_used: int,
    table_col_location: int,
    table_col_aspect: int,
    scroll_window_seconds: float,
    batch_size_scrolling: int,
    batch_size_idle: int,
    monotonic_fn: Callable[[], float] = time.monotonic,
) -> None:
    if window.table_metadata_paused:
        return

    if not window.table_metadata_pending_paths:
        window.table_metadata_timer.stop()
        if window.table_metadata_total_paths > 0:
            total_paths = window.table_metadata_total_paths
            window.update_footer_progress(
                "Metadata",
                total_paths,
                total_paths,
            )
            present_status(
                window,
                f"Metadata indexing complete ({total_paths}/{total_paths})",
                1500,
            )
            window.append_log(
                "DEBUG",
                "Metadata indexing summary: "
                f"cached_hits={window.table_metadata_cached_hits} "
                f"queued={window.table_metadata_total_paths} "
                f"computed={window.table_metadata_computed_paths} "
                f"skipped={window.table_metadata_skipped_paths} "
                f"changed={window.table_metadata_changed_paths}",
            )
            window.table_metadata_paused = False
            window.clear_footer_progress()
        window.table_metadata_total_paths = 0
        return

    current_generation = window.table_metadata_generation
    batch_size = current_table_metadata_batch_size(
        window,
        scroll_window_seconds=scroll_window_seconds,
        batch_size_scrolling=batch_size_scrolling,
        batch_size_idle=batch_size_idle,
        monotonic_fn=monotonic_fn,
    )
    batch = window.table_metadata_pending_paths[:batch_size]
    del window.table_metadata_pending_paths[:batch_size]
    metadata_changed = False

    window._updating_table = True
    window.image_table.blockSignals(True)
    try:
        for path in batch:
            if current_generation != window.table_metadata_generation:
                return

            if path not in window.image_paths:
                continue

            row = window.row_for_path(path)
            if row is None:
                continue

            try:
                date_used, _date_source = window.date_used_and_source_for_path(path)
                location_status = window.location_lookup_status_for_path(path)
                aspect_text = window.aspect_ratio_cell_text_for_path(path)
                date_text = date_used.strftime("%Y-%m-%d %H:%M")
            except Exception as error:
                window.table_metadata_skipped_paths += 1
                window.append_log(
                    "DEBUG",
                    f"Metadata indexing skipped for {path.name}: {error}",
                )
                continue

            date_item = window.image_table.item(row, table_col_date_used)
            if date_item is not None:
                date_item.setText(date_text)

            location_item = window.image_table.item(row, table_col_location)
            if location_item is not None:
                location_item.setText(location_status)

            aspect_item = window.image_table.item(row, table_col_aspect)
            if aspect_item is not None:
                aspect_item.setText(aspect_text)

            if window.store_table_values_for_path(
                path,
                date_text,
                location_status,
                aspect_text,
            ):
                metadata_changed = True
                window.table_metadata_changed_paths += 1
            window.table_metadata_computed_paths += 1
    finally:
        window.image_table.blockSignals(False)
        window._updating_table = False

    if metadata_changed:
        window.save_folder_metadata()

    if not window.table_metadata_pending_paths:
        total_paths = window.table_metadata_total_paths
        window.table_metadata_timer.stop()
        window.update_footer_progress(
            "Metadata",
            total_paths,
            total_paths,
        )
        present_status(
            window,
            f"Metadata indexing complete ({total_paths}/{total_paths})",
            1500,
        )
        window.append_log(
            "DEBUG",
            "Metadata indexing summary: "
            f"cached_hits={window.table_metadata_cached_hits} "
            f"queued={window.table_metadata_total_paths} "
            f"computed={window.table_metadata_computed_paths} "
            f"skipped={window.table_metadata_skipped_paths} "
            f"changed={window.table_metadata_changed_paths}",
        )
        window.table_metadata_paused = False
        window.clear_footer_progress()
        window.table_metadata_total_paths = 0
        return

    completed = window.table_metadata_total_paths - len(
        window.table_metadata_pending_paths
    )
    window.update_footer_progress(
        "Metadata", completed, window.table_metadata_total_paths
    )
    present_status(
        window,
        f"Indexing metadata… {completed}/{window.table_metadata_total_paths}",
    )


def toggle_table_metadata_pause(
    window: Any,
    *,
    present_status_and_log_fn: Callable[..., None],
) -> None:
    if window.table_metadata_total_paths <= 0:
        window.table_metadata_paused = False
        window.refresh_footer_progress_action()
        return

    if not window.table_metadata_paused:
        window.table_metadata_paused = True
        window.table_metadata_timer.stop()
        present_status_and_log_fn(
            window,
            level="INFO",
            message="Metadata indexing paused",
        )
    else:
        window.table_metadata_paused = False
        window.table_metadata_timer.start()
        present_status_and_log_fn(
            window,
            level="INFO",
            message="Metadata indexing resumed",
        )

    window.refresh_footer_progress_action()


def enqueue_table_metadata_for_paths(window: Any, paths: list[Path]) -> None:
    if not paths:
        return
    additions = [
        path
        for path in paths
        if (
            window.row_for_path(path) is not None
            and path not in window.table_metadata_pending_paths
            and window.cached_table_values_for_path(path) is None
        )
    ]
    if not additions:
        return

    if window.table_metadata_total_paths <= 0:
        window.table_metadata_generation += 1
        window.table_metadata_pending_paths = list(additions)
        window.table_metadata_total_paths = len(additions)
        window.table_metadata_paused = False
        window.update_footer_progress("Metadata", 0, window.table_metadata_total_paths)
        present_status(
            window, f"Indexing metadata… 0/{window.table_metadata_total_paths}"
        )
        window.table_metadata_timer.start()
        return

    window.table_metadata_pending_paths.extend(additions)
    window.table_metadata_total_paths += len(additions)
    completed = window.table_metadata_total_paths - len(
        window.table_metadata_pending_paths
    )
    window.update_footer_progress(
        "Metadata", completed, window.table_metadata_total_paths
    )


__all__ = [
    "current_table_metadata_batch_size",
    "enqueue_table_metadata_for_paths",
    "note_table_scrolled",
    "process_table_metadata_batch",
    "reset_table_metadata_tracking",
    "start_table_metadata_resolution",
    "toggle_table_metadata_pause",
]
