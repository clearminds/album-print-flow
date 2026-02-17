from __future__ import annotations

from collections.abc import Callable
from typing import Any


def update_footer_progress(window: Any, label: str, current: int, total: int) -> None:
    if total <= 0:
        window.clear_footer_progress()
        return

    safe_total = max(1, int(total))
    safe_current = max(0, min(int(current), safe_total))
    if not window.footer_progress_bar.isVisible():
        window.footer_progress_bar.show()
    window.footer_progress_bar.setRange(0, safe_total)
    window.footer_progress_bar.setValue(safe_current)
    window.footer_progress_bar.setFormat(f"{label} {safe_current}/{safe_total}")
    window.refresh_footer_progress_action()


def clear_footer_progress(window: Any) -> None:
    window.footer_progress_bar.hide()
    window.footer_progress_bar.setRange(0, 1)
    window.footer_progress_bar.setValue(0)
    window.footer_progress_bar.setFormat("Progress %v/%m")
    window.refresh_footer_progress_action()


def gps_resolution_progress_counts(
    window: Any,
    *,
    location_format_needs_reverse_lookup_fn: Callable[[str], bool],
) -> tuple[int, int]:
    if not window.nominatim_enabled_value:
        return 0, 0
    if not window.nominatim_reverse_url_value.strip():
        return 0, 0
    if not window.image_paths:
        return 0, 0

    resolved = 0
    total = 0
    for path in window.image_paths:
        values = window.image_settings_for_path(path)
        effective_format = window.effective_location_format_for_path(path, values)
        if not effective_format or not location_format_needs_reverse_lookup_fn(
            effective_format
        ):
            continue
        location = window.location_for_path(path)
        if location is None:
            continue

        total += 1
        cache_key = window.nominatim_cache_key(
            location[0],
            location[1],
            format_value=effective_format,
        )
        cached = window.location_lookup_cached_value_for_path(path, cache_key)
        if cached is not None:
            resolved += 1

    return resolved, total


def refresh_gps_resolution_progress(
    window: Any,
    *,
    location_format_needs_reverse_lookup_fn: Callable[[str], bool],
) -> None:
    if window.source_load_in_progress or window.source_refresh_in_progress:
        return
    if window.table_metadata_total_paths > 0:
        return

    resolved, total = gps_resolution_progress_counts(
        window,
        location_format_needs_reverse_lookup_fn=location_format_needs_reverse_lookup_fn,
    )
    if total <= 0 or resolved >= total:
        if (
            window.footer_progress_bar.isVisible()
            and window.footer_progress_bar.format().startswith("GPS ")
        ):
            window.clear_footer_progress()
        return

    window.update_footer_progress("GPS", resolved, total)


def set_footer_progress_action(
    window: Any,
    text: str,
    handler: Callable[[], None] | None,
    *,
    enabled: bool = True,
) -> None:
    window.footer_progress_action_handler = handler
    if handler is None or not text:
        window.footer_progress_action_button.setVisible(False)
        window.footer_progress_action_button.setEnabled(False)
        window.footer_progress_action_button.setText("")
        return
    window.footer_progress_action_button.setText(text)
    window.footer_progress_action_button.setEnabled(bool(enabled))
    window.footer_progress_action_button.setVisible(True)


def on_footer_progress_action_clicked(window: Any) -> None:
    handler = window.footer_progress_action_handler
    if handler is None:
        return
    try:
        handler()
    except Exception as error:
        window.append_log("WARNING", f"Progress action failed: {error}")


def refresh_footer_progress_action(window: Any) -> None:
    if not window.footer_progress_bar.isVisible():
        window.set_footer_progress_action("", None, enabled=False)
        return

    if window.source_load_in_progress or window.source_refresh_in_progress:
        active_source_id = str(window.current_source_id or "")
        adapter = window.active_source_load_adapter
        adapter_source_id = str(getattr(adapter, "source_id", "") or "")
        if (
            active_source_id == "google-photos-album-url"
            or adapter_source_id == "google-photos-album-url"
        ):
            if adapter is None:
                adapter = window.source_registry.get("google-photos-album-url")
            can_cancel = callable(getattr(adapter, "request_cancel", None))
            if can_cancel:
                window.set_footer_progress_action(
                    "Stop", window.stop_album_sync, enabled=True
                )
                return
    if window.table_metadata_total_paths > 0:
        label = "Resume" if window.table_metadata_paused else "Pause"
        window.set_footer_progress_action(
            label,
            window.toggle_table_metadata_pause,
            enabled=True,
        )
        return
    window.set_footer_progress_action("", None, enabled=False)


__all__ = [
    "clear_footer_progress",
    "gps_resolution_progress_counts",
    "on_footer_progress_action_clicked",
    "refresh_footer_progress_action",
    "refresh_gps_resolution_progress",
    "set_footer_progress_action",
    "update_footer_progress",
]
