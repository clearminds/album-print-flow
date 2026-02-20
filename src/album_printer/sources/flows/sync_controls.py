from __future__ import annotations

from typing import Any

from album_printer.ui.status_presenter import present_status


def update_album_sync_stop_availability(window: Any) -> None:
    adapter = window.active_source_load_adapter
    if adapter is None:
        adapter = window.source_registry.get("google-photos-album-url")
    running = window.source_load_in_progress or window.source_refresh_in_progress
    can_cancel = callable(getattr(adapter, "request_cancel", None))
    window.stop_album_sync_button.setEnabled(bool(running and can_cancel))


def start_album_sync_live_updates(
    window: Any,
    album_url: str,
    initial_count: int = 0,
) -> None:
    window.album_sync_live_url = str(album_url or "")
    window.album_sync_live_last_asset_count = max(0, int(initial_count))
    if window.album_sync_live_url:
        window.album_sync_live_timer.start()


def stop_album_sync_live_updates(window: Any) -> None:
    window.album_sync_live_timer.stop()
    window.album_sync_live_url = ""
    window.album_sync_live_last_asset_count = 0


def stop_album_sync(window: Any) -> None:
    if not (window.source_load_in_progress or window.source_refresh_in_progress):
        present_status(window, "No album sync is currently running")
        window.stop_album_sync_button.setEnabled(False)
        return

    adapter = window.active_source_load_adapter
    if adapter is None:
        adapter = window.source_registry.get("google-photos-album-url")
    cancel_method = getattr(adapter, "request_cancel", None)
    if not callable(cancel_method):
        present_status(
            window,
            "Active album source does not support cancellation",
        )
        window.stop_album_sync_button.setEnabled(False)
        return

    cancel_method()
    window.stop_album_sync_button.setEnabled(False)
    present_status(window, "Stopping album sync…")
    window.append_log("INFO", "GOOGLE_ALBUM_URL cancellation requested")


def cancel_active_source_load_for_switch(
    window: Any,
    target_source_label: str,
) -> None:
    if not window.source_load_in_progress:
        return

    adapter = window.active_source_load_adapter
    cancel_method = getattr(adapter, "request_cancel", None)
    if callable(cancel_method):
        try:
            cancel_method()
        except Exception:
            pass

    window.source_load_generation += 1
    window.source_load_in_progress = False
    window.active_source_load_adapter = None
    window.stop_album_sync_live_updates()
    window.clear_footer_progress()
    window.update_album_sync_stop_availability()
    window.load_button.setEnabled(True)
    window.load_folder_action.setEnabled(True)
    window.load_google_action.setEnabled(True)
    window.load_google_album_url_action.setEnabled(True)
    window.load_folder_menu_action.setEnabled(True)
    window.load_google_menu_action.setEnabled(True)
    window.load_google_album_url_menu_action.setEnabled(True)
    present_status(window, f"Switching source to {target_source_label}…")
    window.append_log(
        "INFO",
        f"Source switch requested -> {target_source_label}; previous load cancelled",
    )


__all__ = [
    "cancel_active_source_load_for_switch",
    "start_album_sync_live_updates",
    "stop_album_sync",
    "stop_album_sync_live_updates",
    "update_album_sync_stop_availability",
]
