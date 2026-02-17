from __future__ import annotations

import time
from typing import Any

from PySide6.QtWidgets import QMessageBox

from album_printer.sources.types import SourceLoadResult


def handle_process_album_sync_live_snapshot(window: Any) -> None:
    if not (window.source_load_in_progress or window.source_refresh_in_progress):
        return
    if not window.album_sync_live_url:
        return

    adapter = window.source_registry.get("google-photos-album-url")
    if adapter is None:
        return

    cached_snapshot_method = getattr(adapter, "cached_snapshot", None)
    if not callable(cached_snapshot_method):
        return

    live_info_method = getattr(adapter, "live_sync_snapshot_info", None)
    current_count = window.album_sync_live_last_asset_count
    live_context_id = ""
    if callable(live_info_method):
        try:
            live_info = live_info_method(window.album_sync_live_url)
        except Exception:
            live_info = None

        if isinstance(live_info, dict):
            live_context_id = str(live_info.get("context_id") or "").strip()
            live_count = live_info.get("item_count")
            if isinstance(live_count, int) and live_count >= 0:
                current_count = live_count

    if current_count <= window.album_sync_live_last_asset_count:
        return

    active_same_context = (
        window.current_source_id == "google-photos-album-url"
        and bool(live_context_id)
        and window.current_source_context_id == live_context_id
    )
    if active_same_context:
        window.album_sync_live_last_asset_count = current_count
        window.update_footer_progress(
            "Album Sync",
            current_count,
            max(1, current_count),
        )
        window.refresh_footer_progress_action()
        window.statusBar().showMessage(
            "Syncing album… discovered "
            f"{current_count} item(s); applying updates when sync completes"
        )
        return

    try:
        snapshot = cached_snapshot_method(window.album_sync_live_url)
    except Exception:
        return

    if not isinstance(snapshot, SourceLoadResult):
        return

    current_count = len(snapshot.assets)
    if current_count <= window.album_sync_live_last_asset_count:
        return

    snapshot_same_context = (
        window.current_source_id == snapshot.source_id
        and window.current_folder is not None
        and window.current_folder == snapshot.metadata_root
    )
    if snapshot_same_context:
        window.album_sync_live_last_asset_count = current_count
        window.update_footer_progress(
            "Album Sync",
            current_count,
            max(1, current_count),
        )
        window.refresh_footer_progress_action()
        window.statusBar().showMessage(
            "Syncing album… discovered "
            f"{current_count} item(s); applying updates when sync completes"
        )
        return

    can_append = (
        window.current_source_id == snapshot.source_id
        and window.current_folder is not None
        and window.current_folder == snapshot.metadata_root
    )
    snapshot_assets_by_path = {asset.local_path: asset for asset in snapshot.assets}
    snapshot_paths = [asset.local_path for asset in snapshot.assets]

    if can_append:
        current_paths_set = set(window.image_paths)
        snapshot_paths_set = set(snapshot_paths)
        if current_paths_set.issubset(snapshot_paths_set):
            new_paths = [
                path for path in snapshot_paths if path not in current_paths_set
            ]
            if new_paths:
                for path in new_paths:
                    asset = snapshot_assets_by_path.get(path)
                    if asset is not None:
                        window.source_assets_by_path[path] = asset
                window.append_image_rows(new_paths)
            can_append = True
        else:
            can_append = False

    if not can_append:
        preferred_path = window.selected_path()
        window.apply_source_load_result(
            snapshot,
            open_settings_if_new=False,
            preferred_path=preferred_path,
        )

    window.album_sync_live_last_asset_count = current_count
    window.statusBar().showMessage(
        f"Syncing album… loaded {current_count} item(s) so far"
    )


def handle_load_google_photos_album_url(window: Any, worker_cls: Any) -> None:
    adapter = window.source_registry.get("google-photos-album-url")
    if adapter is None:
        QMessageBox.warning(
            window,
            "Google Photos Album URL",
            "Google Photos Album URL source is unavailable",
        )
        return

    if window.source_load_in_progress:
        window.cancel_active_source_load_for_switch("Google Photos Album URL")

    choose_method = getattr(adapter, "choose_album_url_via_ui", None)
    if not callable(choose_method):
        window.append_log(
            "WARNING",
            "GOOGLE_ALBUM_URL adapter missing choose_album_url_via_ui; "
            "using blocking load",
        )
        result = adapter.load_via_ui(window)
        if result is None:
            window.append_log("INFO", "GOOGLE_ALBUM_URL load cancelled or failed")
            return

        window.apply_source_load_result(
            result,
            open_settings_if_new=False,
            preferred_path=None,
        )
        window.append_log(
            "INFO",
            "GOOGLE_ALBUM_URL load completed: "
            f"{result.context_label} ({len(result.assets)} assets)",
        )
        return

    selected = choose_method(window)
    if selected is None:
        window.append_log("INFO", "GOOGLE_ALBUM_URL load cancelled")
        return
    normalized_url, loaded_from_bookmark = selected

    cached_result: SourceLoadResult | None = None
    window.album_sync_bootstrap_active = True

    cached_snapshot_method = getattr(adapter, "cached_snapshot", None)
    try:
        if callable(cached_snapshot_method):
            try:
                cached_result = cached_snapshot_method(str(normalized_url))
            except Exception as error:
                cached_result = None
                window.append_log(
                    "DEBUG",
                    f"GOOGLE_ALBUM_URL cached snapshot unavailable: {error}",
                )
            if isinstance(cached_result, SourceLoadResult):
                try:
                    window.apply_source_load_result(
                        cached_result,
                        open_settings_if_new=False,
                        preferred_path=None,
                    )
                    window.statusBar().showMessage(
                        "Loaded cached album view "
                        f"({len(cached_result.assets)} items). Syncing updates…"
                    )
                    window.append_log(
                        "INFO",
                        "GOOGLE_ALBUM_URL loaded cached snapshot: "
                        f"{cached_result.context_label}",
                    )
                except Exception as error:
                    window.append_log(
                        "WARNING",
                        f"GOOGLE_ALBUM_URL cached snapshot apply failed: {error}",
                    )
    finally:
        window.album_sync_bootstrap_active = False

    window.append_log("DEBUG", "GOOGLE_ALBUM_URL load flow started")
    window.source_load_in_progress = True
    window.active_source_load_adapter = adapter
    window.source_load_generation += 1
    load_id = window.source_load_generation
    window.clear_footer_progress()
    window.update_album_sync_stop_availability()
    initial_count = (
        len(cached_result.assets) if isinstance(cached_result, SourceLoadResult) else 0
    )
    window.start_album_sync_live_updates(str(normalized_url), initial_count)
    window.update_footer_progress(
        "Album Sync",
        initial_count,
        max(1, initial_count if initial_count > 0 else 1),
    )
    window.refresh_footer_progress_action()
    window.statusBar().showMessage("Loading Google Photos Album URL in background…")

    payload = {
        "input_url": str(normalized_url),
        "loaded_from_bookmark": bool(loaded_from_bookmark),
    }
    worker = worker_cls(
        request_id=load_id,
        adapter=adapter,
        context_id=str(normalized_url),
        payload=payload,
    )
    worker.signals.finished.connect(window.on_source_load_finished)
    window.source_worker_pool.start(worker)


def handle_source_load_finished(
    window: Any,
    load_id: int,
    result: object,
    error: object,
    payload: object,
) -> None:
    if int(load_id) != window.source_load_generation:
        return

    finished_start = time.perf_counter()

    window.source_load_in_progress = False
    window.active_source_load_adapter = None
    window.stop_album_sync_live_updates()
    window.clear_footer_progress()
    window.update_album_sync_stop_availability()
    window.append_log(
        "DEBUG",
        "GOOGLE_ALBUM_URL finish step=teardown "
        f"ms={(time.perf_counter() - finished_start) * 1000:.1f}",
    )

    if error is not None:
        QMessageBox.warning(window, "Google Photos Album URL", str(error))
        window.statusBar().showMessage("Google Photos Album URL load failed")
        window.append_log("WARNING", f"GOOGLE_ALBUM_URL load failed: {error}")
        return

    if not isinstance(result, SourceLoadResult):
        QMessageBox.warning(
            window,
            "Google Photos Album URL",
            "Google Photos Album URL did not return a valid result.",
        )
        window.statusBar().showMessage("Google Photos Album URL load failed")
        return

    new_paths = [asset.local_path for asset in result.assets]
    current_paths_set = set(window.image_paths)
    new_paths_set = set(new_paths)
    unchanged_asset_set = (
        window.current_source_id == result.source_id
        and window.current_source_context_id == result.context_id
        and len(window.image_paths) == len(new_paths)
        and current_paths_set == new_paths_set
    )

    if unchanged_asset_set:
        window.source_assets_by_path = {
            asset.local_path: asset for asset in result.assets
        }
        window.statusBar().showMessage(
            "Google Photos Album URL sync complete "
            f"({len(new_paths)} items, no list changes)",
            1800,
        )
        window.append_log(
            "DEBUG",
            "GOOGLE_ALBUM_URL sync finished with unchanged asset set; "
            "skipped full table rebuild, metadata re-index, and metadata rewrite",
        )
    else:
        window.apply_source_load_result(
            result,
            open_settings_if_new=False,
            preferred_path=None,
        )
    window.append_log(
        "DEBUG",
        "GOOGLE_ALBUM_URL finish step=apply_result "
        f"unchanged={unchanged_asset_set} "
        f"ms={(time.perf_counter() - finished_start) * 1000:.1f}",
    )

    if isinstance(payload, dict) and not bool(payload.get("loaded_from_bookmark")):
        window.append_log(
            "DEBUG",
            "GOOGLE_ALBUM_URL background load skipped modal bookmark prompt; "
            "use Settings to save entries",
        )

    window.append_log(
        "DEBUG",
        "GOOGLE_ALBUM_URL finish step=post_prompt "
        f"ms={(time.perf_counter() - finished_start) * 1000:.1f}",
    )

    total_assets = len(result.assets)
    missing_location_assets = sum(
        1
        for asset in result.assets
        if asset.latitude is None or asset.longitude is None
    )
    if total_assets > 0 and missing_location_assets > 0:
        window.append_log(
            "WARNING",
            "GOOGLE_ALBUM_URL missing location metadata: "
            f"{missing_location_assets}/{total_assets} item(s)",
        )

    window.append_log(
        "DEBUG",
        "GOOGLE_ALBUM_URL finish step=location_summary "
        f"ms={(time.perf_counter() - finished_start) * 1000:.1f}",
    )

    window.append_log(
        "INFO",
        "GOOGLE_ALBUM_URL load completed: "
        f"{result.context_label} ({len(result.assets)} assets)",
    )
    window.append_log(
        "DEBUG",
        "GOOGLE_ALBUM_URL finish step=done "
        f"total_ms={(time.perf_counter() - finished_start) * 1000:.1f}",
    )
