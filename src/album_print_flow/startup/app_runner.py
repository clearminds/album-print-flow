from __future__ import annotations

import sys
import time
from collections.abc import Sequence
from typing import Any

from PySide6.QtCore import QLoggingCategory, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication


def run_application(
    argv: Sequence[str] | None = None,
    *,
    main_window_cls: type,
    app_display_name: str,
    app_organization_name: str,
    app_organization_domain: str,
    app_desktop_id: str,
    app_window_icon_fn: Any,
    create_splash_screen_fn: Any,
    is_debugger_attached_fn: Any,
    preload_startup_cache_fn: Any,
    parse_cups_options_output_fn: Any,
    get_ipp_capabilities_fn: Any,
    ipp_backend_error_cls: type,
    settings_org: str,
    settings_app: str,
) -> int:
    if sys.platform.startswith("linux"):
        QLoggingCategory.setFilterRules("qt.qpa.services.warning=false")

    QApplication.setApplicationName(app_display_name)
    QApplication.setApplicationDisplayName(app_display_name)
    QApplication.setOrganizationName(app_organization_name)
    QApplication.setOrganizationDomain(app_organization_domain)

    app = QApplication(list(argv or []))
    if hasattr(app, "setDesktopFileName"):
        app.setDesktopFileName(app_desktop_id)
    icon = app_window_icon_fn()
    if icon is not None:
        app.setWindowIcon(icon)
    splash_start = time.perf_counter()
    splash = create_splash_screen_fn()
    splash.showMessage(
        "Initializing…",
        Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom,
        QColor("#D1D5DB"),
    )
    splash.show()
    splash.raise_()
    splash.activateWindow()
    if not is_debugger_attached_fn():
        app.processEvents()

    startup_cache = preload_startup_cache_fn(
        splash=splash,
        parse_cups_options_output_fn=parse_cups_options_output_fn,
        get_ipp_capabilities_fn=get_ipp_capabilities_fn,
        ipp_backend_error_cls=ipp_backend_error_cls,
        settings_org=settings_org,
        settings_app=settings_app,
        is_debugger_attached_fn=is_debugger_attached_fn,
        mode="mixed",
    )

    elapsed = time.perf_counter() - splash_start
    min_splash_seconds = 0.0 if is_debugger_attached_fn() else 0.8
    while elapsed < min_splash_seconds:
        if not is_debugger_attached_fn():
            app.processEvents()
        time.sleep(0.01)
        elapsed = time.perf_counter() - splash_start

    window = main_window_cls(startup_cache=startup_cache)
    window.show()
    splash.finish(window)
    return app.exec()


__all__ = ["run_application"]
