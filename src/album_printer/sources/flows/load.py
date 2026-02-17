from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtWidgets import QMessageBox

from album_printer.sources.types import SourceLoadResult


def handle_load_folder(window: Any) -> None:
    if window.source_load_in_progress:
        window.cancel_active_source_load_for_switch("Folder")

    adapter = window.source_registry.get("folder")
    if adapter is None:
        QMessageBox.warning(window, "Load Folder", "Folder source is unavailable")
        return

    result = adapter.load_via_ui(window)
    if result is None:
        return

    window.apply_source_load_result(
        result,
        open_settings_if_new=False,
        preferred_path=None,
    )


def handle_load_folder_path(
    window: Any,
    folder_path: Path,
    open_settings_if_new: bool = False,
    preferred_path: Path | None = None,
) -> None:
    adapter = window.source_registry.get("folder")
    if adapter is None:
        QMessageBox.warning(window, "Load Folder", "Folder source is unavailable")
        return
    try:
        result = adapter.refresh(str(folder_path), preferred_path)
    except OSError:
        QMessageBox.warning(
            window, "Folder Not Found", "Selected folder does not exist"
        )
        return

    window.apply_source_load_result(result, open_settings_if_new, preferred_path)


def handle_load_google_photos(window: Any) -> None:
    if window.source_load_in_progress:
        window.cancel_active_source_load_for_switch("Google Photos")

    adapter = window.source_registry.get("google-photos")
    if adapter is None:
        QMessageBox.warning(
            window,
            "Google Photos",
            "Google Photos source is unavailable",
        )
        return

    window.append_log("DEBUG", "GOOGLE load flow started")
    result = adapter.load_via_ui(window)
    if result is None:
        window.append_log("INFO", "GOOGLE load cancelled or failed")
        return

    window.apply_source_load_result(
        result,
        open_settings_if_new=False,
        preferred_path=None,
    )

    if "::picker:" in result.context_id:
        total_assets = len(result.assets)
        missing_location_assets = sum(
            1
            for asset in result.assets
            if asset.latitude is None or asset.longitude is None
        )
        if total_assets > 0 and missing_location_assets > 0:
            window.append_log(
                "WARNING",
                "GOOGLE Picker metadata limitation: "
                f"{missing_location_assets}/{total_assets} item(s) "
                "missing location metadata",
            )
            QMessageBox.information(
                window,
                "Google Picker metadata limitation",
                "Google Photos Picker downloads may omit location metadata.\n"
                "Location stamp may be unavailable for these items.\n\n"
                f"Missing location metadata: {missing_location_assets}/{total_assets}",
            )

    window.append_log(
        "INFO",
        f"GOOGLE load completed: {result.context_label} ({len(result.assets)} assets)",
    )


def handle_test_google_setup(window: Any) -> None:
    adapter = window.source_registry.get("google-photos")
    if adapter is None:
        QMessageBox.warning(
            window,
            "Google Photos",
            "Google Photos source is unavailable",
        )
        return

    test_method = getattr(adapter, "test_setup_via_ui", None)
    if not callable(test_method):
        QMessageBox.warning(
            window,
            "Google Photos",
            "Google setup test is not supported by the active source adapter.",
        )
        return

    window.append_log("DEBUG", "GOOGLE setup test started")
    succeeded = bool(test_method(window))
    window.append_log(
        "INFO" if succeeded else "WARNING",
        f"GOOGLE setup test {'passed' if succeeded else 'failed'}",
    )


def handle_refresh_folder(window: Any, refresh_worker_cls: Any) -> None:
    if window.source_refresh_in_progress:
        window.statusBar().showMessage("Quick reload already running…")
        return

    if window.current_source_context_id is None:
        QMessageBox.information(window, "Quick Reload", "No source loaded")
        return

    adapter = window.source_registry.get(window.current_source_id)
    if adapter is None:
        QMessageBox.warning(window, "Refresh Source", "Active source is unavailable")
        return

    preferred_path = window.selected_path()
    window.source_refresh_in_progress = True
    window.source_refresh_generation += 1
    refresh_id = window.source_refresh_generation
    window.clear_footer_progress()
    window.update_album_sync_stop_availability()

    if window.current_source_id == "google-photos-album-url":
        window.start_album_sync_live_updates(
            str(window.current_source_context_id or ""),
            len(window.image_paths),
        )

    window.refresh_folder_button.setEnabled(False)
    window.refresh_folder_action.setEnabled(False)
    window.statusBar().showMessage("Quick reload running in background…")
    window.append_log(
        "DEBUG",
        f"Quick reload started for source {window.current_source_id}",
    )

    worker = refresh_worker_cls(
        request_id=refresh_id,
        adapter=adapter,
        context_id=window.current_source_context_id,
        preferred_path=preferred_path,
    )
    worker.signals.finished.connect(window.on_source_refresh_finished)
    window.source_worker_pool.start(worker)


def handle_source_refresh_finished(
    window: Any,
    refresh_id: int,
    result: object,
    error: object,
    preferred_path: object,
) -> None:
    if int(refresh_id) != window.source_refresh_generation:
        return

    window.source_refresh_in_progress = False
    window.stop_album_sync_live_updates()
    window.clear_footer_progress()
    window.update_album_sync_stop_availability()
    window.refresh_folder_button.setEnabled(True)
    window.refresh_folder_action.setEnabled(True)

    if error is not None:
        if isinstance(error, OSError):
            QMessageBox.warning(
                window,
                "Quick Reload",
                "Selected source location is unavailable",
            )
        else:
            QMessageBox.warning(window, "Refresh Source", str(error))
        window.statusBar().showMessage("Quick reload failed")
        window.append_log("WARNING", f"Quick reload failed: {error}")
        return

    if not isinstance(result, SourceLoadResult):
        QMessageBox.warning(
            window,
            "Refresh Source",
            "Refresh did not return a valid source result.",
        )
        window.statusBar().showMessage("Quick reload failed")
        return

    previous_paths = set(window.image_paths)
    preferred = preferred_path if isinstance(preferred_path, Path) else None
    window.apply_source_load_result(
        result,
        open_settings_if_new=False,
        preferred_path=preferred,
    )

    added_paths = [path for path in window.image_paths if path not in previous_paths]
    new_needing_print = sum(
        1 for path in added_paths if window.should_include_in_print_all(path)
    )

    if added_paths:
        message = (
            f"Quick reload complete: {len(added_paths)} new photo(s), "
            f"{new_needing_print} need printing"
        )
        window.statusBar().showMessage(message)
        window.append_log("INFO", message)
    else:
        window.statusBar().showMessage("Quick reload complete: no new photos")
        window.append_log("INFO", f"Refreshed source: {result.context_label}")
