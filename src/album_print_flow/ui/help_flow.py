from __future__ import annotations

from collections.abc import Callable
from typing import Any


def show_about_dialog(
    window: Any,
    *,
    app_display_name: str,
    load_clearminds_head_pixmap_fn: Callable[..., Any],
    load_logo_pixmap_fn: Callable[..., Any],
    app_about_text_fn: Callable[[], str],
    qmessagebox_cls: type,
) -> None:
    logo = load_clearminds_head_pixmap_fn(size=96) or load_logo_pixmap_fn(size=96)
    body = app_about_text_fn()
    box = qmessagebox_cls(window)
    box.setWindowTitle(f"About {app_display_name}")
    box.setText(body)
    box.setIcon(qmessagebox_cls.Icon.Information)
    if logo is not None:
        box.setIconPixmap(logo)
    box.exec()


def show_source_guide_dialog(
    window: Any,
    *,
    open_source_guide_dialog_fn: Callable[[Any], None],
) -> None:
    open_source_guide_dialog_fn(window)


__all__ = [
    "show_about_dialog",
    "show_source_guide_dialog",
]
