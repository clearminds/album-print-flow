from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtGui import QPixmap


def load_cached_thumbnail(window: Any, path: Path) -> QPixmap | None:
    try:
        source_mtime_ns = path.stat().st_mtime_ns
    except OSError:
        return None

    cache_path, legacy_cache_path = window.thumbnail_cache_candidate_paths(path)
    for candidate in (cache_path, legacy_cache_path):
        if candidate == legacy_cache_path and not cache_path.exists():
            window.migrate_thumbnail_cache_file(path, source_mtime_ns=source_mtime_ns)
            if cache_path.exists():
                candidate = cache_path

        try:
            cache_mtime_ns = candidate.stat().st_mtime_ns
        except OSError:
            continue
        if cache_mtime_ns < source_mtime_ns:
            continue

        pixmap = QPixmap(str(candidate))
        if pixmap.isNull():
            continue

        if candidate != cache_path:
            image = pixmap.toImage()
            if not image.isNull():
                try:
                    cache_path.parent.mkdir(parents=True, exist_ok=True)
                    image.save(str(cache_path), "PNG")
                except OSError:
                    pass

        return pixmap

    return None


def migrate_thumbnail_cache_for_paths(window: Any, paths: list[Path]) -> int:
    migrated = 0
    for path in paths:
        if window.migrate_thumbnail_cache_file(path):
            migrated += 1
    return migrated


def start_thumbnail_generation(
    window: Any,
    *,
    thumbnail_ui_cache_warmup_max: int,
) -> None:
    window.thumbnail_generation += 1
    migrated = window.migrate_thumbnail_cache_for_paths(window.image_paths)
    if migrated > 0:
        window.append_log(
            "DEBUG",
            "Thumbnail cache migration renamed "
            f"{migrated} legacy file(s) to hashed format",
        )
    pending: list[Path] = []
    warmed = 0
    in_memory_hits = 0
    for path in window.image_paths:
        if path in window.thumbnail_cache:
            in_memory_hits += 1
            continue

        if warmed < thumbnail_ui_cache_warmup_max:
            cached = window.load_cached_thumbnail(path)
            if cached is not None:
                window.thumbnail_cache[path] = cached
                warmed += 1
                continue

        pending.append(path)

    window.thumbnail_pending_paths = pending
    window.thumbnail_inflight_paths = set()
    window.append_log(
        "DEBUG",
        "Thumbnail generation queued: "
        f"total={len(window.image_paths)} "
        f"memory_hits={in_memory_hits} "
        f"disk_warmup={warmed} "
        f"pending={len(window.thumbnail_pending_paths)}",
    )
    window.fill_thumbnail_workers()


__all__ = [
    "load_cached_thumbnail",
    "migrate_thumbnail_cache_for_paths",
    "start_thumbnail_generation",
]
