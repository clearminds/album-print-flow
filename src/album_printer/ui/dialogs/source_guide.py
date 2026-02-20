from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


def open_source_guide_dialog(window: Any) -> None:
    dialog = QDialog(window)
    dialog.setWindowTitle("Source Guide")
    dialog.setModal(True)
    dialog.resize(720, 520)

    root_layout = QVBoxLayout(dialog)
    intro = QLabel(
        "Choose how to load photos. "
        "Each source can be launched directly from this guide."
    )
    intro.setWordWrap(True)
    root_layout.addWidget(intro)

    loader_map = {
        "folder": getattr(window, "load_folder", None),
        "google-photos": getattr(window, "load_google_photos", None),
        "google-photos-album-url": getattr(
            window, "load_google_photos_album_url", None
        ),
    }

    scroll = QScrollArea(dialog)
    scroll.setWidgetResizable(True)
    content = QWidget(scroll)
    content_layout = QVBoxLayout(content)

    adapters = window.source_registry.all()
    for adapter in adapters:
        source_id = str(getattr(adapter, "source_id", "")).strip()
        label = str(getattr(adapter, "label", source_id or "Source")).strip()
        help_text = str(getattr(adapter, "help_text", "")).strip()
        if not help_text:
            help_text = "No guide text available for this source yet."

        card = QFrame(content)
        card.setFrameShape(QFrame.Shape.StyledPanel)
        card_layout = QVBoxLayout(card)

        title = QLabel(label, card)
        title.setStyleSheet("font-weight: 600;")
        title.setWordWrap(True)
        card_layout.addWidget(title)

        description = QLabel(help_text, card)
        description.setWordWrap(True)
        card_layout.addWidget(description)

        actions_row = QHBoxLayout()
        load_button = QPushButton(f"Load {label}", card)
        loader = loader_map.get(source_id)
        if callable(loader):

            def _launch_selected(
                _checked: bool = False,
                loader_func: Any = loader,
            ) -> None:
                dialog.accept()
                loader_func()

            load_button.clicked.connect(_launch_selected)
        else:
            load_button.setEnabled(False)
            load_button.setToolTip("No direct loader is wired for this source yet.")
        actions_row.addWidget(load_button)
        actions_row.addStretch(1)
        card_layout.addLayout(actions_row)

        content_layout.addWidget(card)

    if not adapters:
        empty = QLabel("No sources are currently registered.", content)
        empty.setWordWrap(True)
        content_layout.addWidget(empty)

    content_layout.addStretch(1)
    scroll.setWidget(content)
    root_layout.addWidget(scroll)

    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close, parent=dialog)
    buttons.rejected.connect(dialog.reject)
    buttons.accepted.connect(dialog.accept)
    root_layout.addWidget(buttons)

    dialog.exec()


__all__ = ["open_source_guide_dialog"]
