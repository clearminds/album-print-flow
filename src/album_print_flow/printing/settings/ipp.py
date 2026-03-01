"""IPP backend print settings UI (URI, test connection, send mode)."""

from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import QComboBox, QLineEdit, QMessageBox, QPushButton


def build_ipp_section(
    parent: Any,
    window: Any,
    *,
    get_ipp_capabilities_fn: Any,
    ipp_backend_error_cls: type[Exception],
    pretty_option_label_fn: Any,
) -> dict[str, Any]:
    """Build IPP-specific widgets (URI, test button, send mode).

    Returns a dict with: uri_edit, test_button,
    send_mode_combo, and
    fill_combos_from_ipp(uri, media_combo, type_combo,
    quality_combo) -> caps or None,
    on_test_clicked(dialog, media_combo, type_combo,
    quality_combo, fill_combo_fn, set_placeholder_fn).
    """
    uri_edit = QLineEdit(parent)
    uri_edit.setPlaceholderText("ipps://EPSON1234.local:631/ipp/print")
    uri_edit.setText(window.ipp_uri_value)

    test_button = QPushButton("Test IPP Connection", parent)

    send_mode_combo = QComboBox(parent)
    send_mode_combo.addItem("Wait for completion (sequential)", True)
    send_mode_combo.addItem("Queue only (faster)", False)
    mode_index = send_mode_combo.findData(window.ipp_wait_for_completion_value)
    send_mode_combo.setCurrentIndex(mode_index if mode_index >= 0 else 0)

    def fill_combos_from_ipp(
        uri: str,
        media_combo: QComboBox,
        type_combo: QComboBox,
        quality_combo: QComboBox,
    ) -> Any:
        caps = window.ipp_capabilities_cache.get(uri)
        try:
            if caps is None and uri:
                caps = get_ipp_capabilities_fn(uri)
                window.ipp_capabilities_cache[uri] = caps
        except ipp_backend_error_cls:
            caps = None
            if uri:
                window.ipp_capabilities_cache[uri] = None

        if caps is None:
            return None
        media_combo.clear()
        media_combo.addItem("(Driver default)", "")
        for option in caps.media:
            media_combo.addItem(pretty_option_label_fn("media", option), option)
        idx = media_combo.findData(window.cups_media_value)
        media_combo.setCurrentIndex(idx if idx >= 0 else 0)
        media_combo.setEnabled(media_combo.count() > 1)

        type_combo.clear()
        type_combo.addItem("(Driver default)", "")
        for option in caps.media_type:
            type_combo.addItem(pretty_option_label_fn("media-type", option), option)
        idx = type_combo.findData(window.cups_media_type_value)
        type_combo.setCurrentIndex(idx if idx >= 0 else 0)
        type_combo.setEnabled(type_combo.count() > 1)

        quality_combo.clear()
        quality_combo.addItem("(Driver default)", "")
        for option in caps.print_quality:
            quality_combo.addItem(
                pretty_option_label_fn("quality", str(option)), str(option)
            )
        idx = quality_combo.findData(window.cups_print_quality_value)
        quality_combo.setCurrentIndex(idx if idx >= 0 else 0)
        quality_combo.setEnabled(quality_combo.count() > 1)
        return caps

    def on_test_clicked(
        dialog: Any,
        media_combo: QComboBox,
        type_combo: QComboBox,
        quality_combo: QComboBox,
        set_placeholder_fn: Any,
    ) -> Any:
        uri = uri_edit.text().strip()
        if not uri:
            QMessageBox.warning(dialog, "No IPP URI", "Enter an IPP/IPPS URI first.")
            return None
        try:
            caps = get_ipp_capabilities_fn(uri)
            window.ipp_capabilities_cache[uri] = caps
        except ipp_backend_error_cls as error:
            window.ipp_capabilities_cache[uri] = None
            QMessageBox.warning(dialog, "IPP connection failed", str(error))
            set_placeholder_fn("(IPP unavailable)")
            return None
        fill_combos_from_ipp(uri, media_combo, type_combo, quality_combo)
        QMessageBox.information(
            dialog,
            "IPP connected",
            f"Connected to {uri}\n"
            f"Printer: {caps.printer_name.strip() or '(unknown)'}\n"
            f"Media: {len(caps.media)}\n"
            f"Media Type: {len(caps.media_type)}\n"
            f"Quality: {len(caps.print_quality)}",
        )
        return caps

    return {
        "uri_edit": uri_edit,
        "test_button": test_button,
        "send_mode_combo": send_mode_combo,
        "fill_combos_from_ipp": fill_combos_from_ipp,
        "on_test_clicked": on_test_clicked,
    }
