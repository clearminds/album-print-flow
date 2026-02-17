from __future__ import annotations

from collections.abc import Callable
from typing import Any


def setup_menu(
    window: Any,
    *,
    setup_file_load_menu_fn: Callable[..., Any],
    qaction_cls: type,
) -> None:
    file_menu = window.menuBar().addMenu("File")

    setup_file_load_menu_fn(window, file_menu)

    window.refresh_folder_action = qaction_cls("Quick Reload", window)
    window.refresh_folder_action.triggered.connect(window.refresh_folder)
    file_menu.addAction(window.refresh_folder_action)

    window.settings_action = qaction_cls("Settings", window)
    window.settings_action.triggered.connect(window.open_settings_dialog)
    file_menu.addAction(window.settings_action)

    window.folder_settings_action = qaction_cls("Image Settings", window)
    window.folder_settings_action.triggered.connect(window.open_project_settings_dialog)
    file_menu.addAction(window.folder_settings_action)

    window.cache_manager_action = qaction_cls("Metadata Manager", window)
    window.cache_manager_action.triggered.connect(window.open_cache_manager_dialog)
    file_menu.addAction(window.cache_manager_action)

    window.test_google_setup_action = qaction_cls("Test Google Setup", window)
    window.test_google_setup_action.triggered.connect(window.test_google_setup)
    file_menu.addAction(window.test_google_setup_action)

    print_settings_action = qaction_cls("Printer Settings", window)
    print_settings_action.triggered.connect(window.open_print_settings_dialog)
    file_menu.addAction(print_settings_action)

    print_selected_action = qaction_cls("Print Selected", window)
    print_selected_action.triggered.connect(window.print_selected)
    file_menu.addAction(print_selected_action)

    print_action = qaction_cls("Print All", window)
    print_action.triggered.connect(window.print_all)
    file_menu.addAction(print_action)

    help_menu = window.menuBar().addMenu("Help")
    source_guide_action = qaction_cls("Source Guide", window)
    source_guide_action.triggered.connect(window.show_source_guide_dialog)
    help_menu.addAction(source_guide_action)
    about_action = qaction_cls("About", window)
    about_action.triggered.connect(window.show_about_dialog)
    help_menu.addAction(about_action)


__all__ = [
    "setup_menu",
]
