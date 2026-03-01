from __future__ import annotations

from collections.abc import Callable
from typing import Any


def restore_ui_state(
    window: Any,
    *,
    is_debugger_attached_fn: Callable[[], bool],
    log_level_rank: dict[str, int],
) -> None:
    geometry = window.ui_settings.value("ui/geometry")
    if geometry is not None:
        window.restoreGeometry(geometry)

    stored_log_level = window.ui_settings.value("ui/log_level_filter", None)
    if stored_log_level is None and is_debugger_attached_fn():
        saved_log_level = "DEBUG"
    else:
        saved_log_level = str(stored_log_level or window.log_level_filter_value)
    saved_log_level = saved_log_level.strip().upper()
    if saved_log_level not in log_level_rank:
        saved_log_level = "INFO"
    window.log_level_combo.setCurrentText(saved_log_level)

    saved_log_text_filter = str(
        window.ui_settings.value("ui/log_text_filter", window.log_text_filter_value)
    ).strip()
    window.log_text_filter_input.setText(saved_log_text_filter)

    raw_sizes = window.ui_settings.value("ui/list_preview_sizes")
    sizes: list[int] = []
    if isinstance(raw_sizes, list):
        for value in raw_sizes:
            try:
                parsed = int(value)
            except (TypeError, ValueError):
                continue
            if parsed > 0:
                sizes.append(parsed)
    if len(sizes) == 2:
        window.list_preview_splitter.setSizes(sizes)

    raw_content_sizes = window.ui_settings.value("ui/content_splitter_sizes")
    content_sizes: list[int] = []
    if isinstance(raw_content_sizes, list):
        for value in raw_content_sizes:
            try:
                parsed = int(value)
            except (TypeError, ValueError):
                continue
            if parsed > 0:
                content_sizes.append(parsed)
    if len(content_sizes) == 2:
        window.content_splitter.setSizes(content_sizes)

    raw_vertical_sizes = window.ui_settings.value("ui/main_vertical_sizes")
    vertical_sizes: list[int] = []
    if isinstance(raw_vertical_sizes, list):
        for value in raw_vertical_sizes:
            try:
                parsed = int(value)
            except (TypeError, ValueError):
                continue
            if parsed > 0:
                vertical_sizes.append(parsed)
    if len(vertical_sizes) == 2:
        window.main_vertical_splitter.setSizes(vertical_sizes)

    raw_bottom_sizes = window.ui_settings.value("ui/bottom_splitter_sizes")
    bottom_sizes: list[int] = []
    if isinstance(raw_bottom_sizes, list):
        for value in raw_bottom_sizes:
            try:
                parsed = int(value)
            except (TypeError, ValueError):
                continue
            if parsed > 0:
                bottom_sizes.append(parsed)
    if len(bottom_sizes) == 2:
        window.bottom_splitter.setSizes(bottom_sizes)
    else:
        fallback_bottom_sizes = window.bottom_splitter.sizes()
        if len(fallback_bottom_sizes) == 2 and all(
            size > 0 for size in fallback_bottom_sizes
        ):
            window.ui_settings.setValue(
                "ui/bottom_splitter_sizes", fallback_bottom_sizes
            )


def save_ui_state(window: Any) -> None:
    window.ui_settings.setValue("ui/geometry", window.saveGeometry())
    window.ui_settings.setValue("ui/log_level_filter", window.log_level_filter_value)
    window.ui_settings.setValue("ui/log_text_filter", window.log_text_filter_value)
    window.ui_settings.setValue(
        "ui/list_preview_sizes", window.list_preview_splitter.sizes()
    )
    window.ui_settings.setValue(
        "ui/content_splitter_sizes", window.content_splitter.sizes()
    )
    window.ui_settings.setValue(
        "ui/main_vertical_sizes", window.main_vertical_splitter.sizes()
    )
    window.ui_settings.setValue(
        "ui/bottom_splitter_sizes", window.bottom_splitter.sizes()
    )
    window.ui_settings.sync()


__all__ = ["restore_ui_state", "save_ui_state"]
