from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import QMessageBox


def startup_scan_bookmarked_google_albums(
    window: Any,
    *,
    bookmark_scan_worker_cls: type,
) -> None:
    if window.startup_bookmark_scan_started or window.startup_bookmark_scan_in_progress:
        return

    adapter = window.source_registry.get("google-photos-album-url")
    if adapter is None:
        return

    check_method = getattr(adapter, "check_bookmarked_updates", None)
    if not callable(check_method):
        return

    window.startup_bookmark_scan_started = True
    window.startup_bookmark_scan_in_progress = True
    window.append_log("DEBUG", "Startup bookmark update check started")

    worker = bookmark_scan_worker_cls(adapter=adapter, max_albums=30)
    worker.signals.finished.connect(window.on_startup_bookmark_scan_finished)
    window.source_worker_pool.start(worker)


def on_startup_bookmark_scan_finished(
    window: Any,
    updates: object,
    error: object,
) -> None:
    window.startup_bookmark_scan_in_progress = False

    if error is not None:
        window.append_log(
            "DEBUG",
            f"Startup bookmark update check failed: {error}",
        )
        return

    if not isinstance(updates, list) or not updates:
        window.append_log("DEBUG", "Startup bookmark update check found no changes")
        return

    normalized_updates: list[dict[str, object]] = [
        entry for entry in updates if isinstance(entry, dict)
    ]
    if not normalized_updates:
        return

    window.show_startup_bookmark_updates_prompt(normalized_updates)


def show_startup_bookmark_updates_prompt(
    window: Any,
    updates: list[dict[str, object]],
) -> None:
    album_count = len(updates)
    total_new = sum(max(0, int(entry.get("new_count", 0) or 0)) for entry in updates)
    total_removed = sum(
        max(0, int(entry.get("removed_count", 0) or 0)) for entry in updates
    )

    lines: list[str] = []
    for entry in updates[:8]:
        name = (
            str(entry.get("name") or entry.get("title") or "Album").strip() or "Album"
        )
        new_count = max(0, int(entry.get("new_count", 0) or 0))
        removed_count = max(0, int(entry.get("removed_count", 0) or 0))
        if removed_count > 0:
            lines.append(f"• {name}: +{new_count}, -{removed_count}")
        else:
            lines.append(f"• {name}: +{new_count}")
    if album_count > len(lines):
        lines.append(f"• …and {album_count - len(lines)} more")

    message = (
        f"Found updates in {album_count} bookmarked Google Photos album(s).\n"
        f"New photos: {total_new}"
    )
    if total_removed > 0:
        message += f"\nRemoved photos: {total_removed}"
    message += "\n\n" + "\n".join(lines)
    message += "\n\nOpen Google Photos Album URL source now?"

    window.append_log(
        "INFO",
        (
            "Startup bookmark update check found changes: "
            f"albums={album_count}, new={total_new}, removed={total_removed}"
        ),
    )

    reply = QMessageBox.question(
        window,
        "Bookmarked albums updated",
        message,
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.Yes,
    )
    if reply == QMessageBox.StandardButton.Yes:
        window.load_google_photos_album_url()


__all__ = [
    "on_startup_bookmark_scan_finished",
    "show_startup_bookmark_updates_prompt",
    "startup_scan_bookmarked_google_albums",
]
