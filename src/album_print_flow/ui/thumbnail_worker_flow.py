from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap


def fill_thumbnail_workers(
    window: Any,
    *,
    thumbnail_max_inflight: int,
    thumbnail_worker_cls: type,
    load_image_as_rgb_fn: object,
    thumbnail_size: int,
) -> None:
    while (
        window.thumbnail_pending_paths
        and len(window.thumbnail_inflight_paths) < thumbnail_max_inflight
    ):
        path = window.thumbnail_pending_paths.pop()
        if path in window.thumbnail_cache or path in window.thumbnail_inflight_paths:
            continue
        window.thumbnail_inflight_paths.add(path)
        worker = thumbnail_worker_cls(
            path,
            window.thumbnail_generation,
            window.thumbnail_cache_file_path(path),
            window.thumbnail_cache_legacy_file_path(path),
            load_image_as_rgb_fn=load_image_as_rgb_fn,
            thumbnail_size=thumbnail_size,
        )
        worker.signals.finished.connect(window.on_thumbnail_ready)
        window.thumbnail_thread_pool.start(worker)


def on_thumbnail_ready(
    window: Any,
    path: object,
    generation: int,
    image: object,
    *,
    table_col_thumb: int,
) -> None:
    if not isinstance(path, Path):
        return

    window.thumbnail_inflight_paths.discard(path)
    if generation != window.thumbnail_generation:
        return

    if isinstance(image, QImage):
        pixmap = QPixmap.fromImage(image)
    else:
        pixmap = window.thumbnail_placeholder
    window.thumbnail_cache[path] = pixmap

    row = window.row_for_path(path)
    if row is None:
        window.fill_thumbnail_workers()
        return

    item = window.image_table.item(row, table_col_thumb)
    if item is not None:
        item.setData(Qt.ItemDataRole.DecorationRole, pixmap)

    window.fill_thumbnail_workers()


__all__ = [
    "fill_thumbnail_workers",
    "on_thumbnail_ready",
]
