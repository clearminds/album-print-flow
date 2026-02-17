from __future__ import annotations

from typing import Any

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu


def setup_file_load_menu(window: Any, file_menu: QMenu) -> QMenu:
    load_menu = file_menu.addMenu("Load ...")

    window.load_folder_menu_action = QAction("Folder", window)
    window.load_folder_menu_action.triggered.connect(window.load_folder)
    load_menu.addAction(window.load_folder_menu_action)

    window.load_google_menu_action = QAction("Google Photos Photo Picker", window)
    window.load_google_menu_action.triggered.connect(window.load_google_photos)
    load_menu.addAction(window.load_google_menu_action)

    window.load_google_album_url_menu_action = QAction(
        "Google Photos Album URL", window
    )
    window.load_google_album_url_menu_action.triggered.connect(
        window.load_google_photos_album_url
    )
    load_menu.addAction(window.load_google_album_url_menu_action)

    window.load_source_guide_menu_action = QAction("Guide Me", window)
    window.load_source_guide_menu_action.triggered.connect(
        window.show_source_guide_dialog
    )
    load_menu.addSeparator()
    load_menu.addAction(window.load_source_guide_menu_action)

    return load_menu
