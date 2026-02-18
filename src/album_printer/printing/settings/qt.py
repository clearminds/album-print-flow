"""Qt backend print settings UI (paper size)."""

from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import QComboBox

from album_printer.app_constants import PAPER_LABELS


def build_paper_section(parent: Any, window: Any) -> dict[str, Any]:
    """Build Qt-specific paper size combo.

    Returns a dict with: paper_combo.
    """
    paper_combo = QComboBox(parent)
    for key, label in sorted(PAPER_LABELS.items(), key=lambda p: p[0]):
        paper_combo.addItem(label, key)
    idx = paper_combo.findData(window.paper_value)
    paper_combo.setCurrentIndex(idx if idx >= 0 else 0)
    return {"paper_combo": paper_combo}
