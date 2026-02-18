from __future__ import annotations

import subprocess
import sys
from typing import Any

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from album_printer.printing.settings import (
    build_driver_options_section,
    build_ipp_section,
    build_paper_section,
)


def open_print_settings_dialog(
    window: Any,
    *,
    print_backends: list[str],
    ipp_backend_error_cls: type[Exception],
    get_ipp_capabilities_fn: Any,
    pretty_option_label_fn: Any,
    is_explicit_borderless_media_fn: Any,
    resolve_cups_media_value_fn: Any,
) -> None:
    dialog = QDialog(window)
    dialog.setWindowTitle("Printer Settings")
    dialog.setModal(True)
    dialog.resize(820, 560)

    layout = QVBoxLayout(dialog)
    info_label = QLabel("These settings apply globally across folders.", dialog)
    info_label.setWordWrap(True)
    layout.addWidget(info_label)
    form = QFormLayout()

    def section_label(text: str) -> QLabel:
        label = QLabel(text, dialog)
        label.setStyleSheet("font-weight: 600;")
        return label

    backend_combo = QComboBox(dialog)
    backend_combo.addItems(print_backends)
    backend_combo.setCurrentText(window.print_backend_value)

    ipp_section = build_ipp_section(
        dialog,
        window,
        get_ipp_capabilities_fn=get_ipp_capabilities_fn,
        ipp_backend_error_cls=ipp_backend_error_cls,
        pretty_option_label_fn=pretty_option_label_fn,
    )
    ipp_uri_edit = ipp_section["uri_edit"]
    ipp_test_button = ipp_section["test_button"]
    ipp_send_mode_combo = ipp_section["send_mode_combo"]

    printer_combo = QComboBox(dialog)
    printer_combo.addItem("(Loading printers…)")
    printer_combo.setEnabled(False)
    refresh_printers_btn = QPushButton("Refresh Printers", dialog)

    cups_section = build_driver_options_section(
        dialog,
        window,
        pretty_option_label_fn=pretty_option_label_fn,
        is_explicit_borderless_media_fn=is_explicit_borderless_media_fn,
        resolve_cups_media_value_fn=resolve_cups_media_value_fn,
    )
    driver_section_label = cups_section["section_label"]
    driver_placeholder = cups_section["placeholder"]
    cups_media_combo = cups_section["media_combo"]
    cups_media_type_combo = cups_section["type_combo"]
    cups_quality_combo = cups_section["quality_combo"]
    borderless_combo = cups_section["borderless_combo"]
    borderless_scale_row = cups_section["borderless_scale_row"]
    borderless_scale_slider = cups_section["borderless_scale_slider"]
    calibration_button = cups_section["calibration_button"]
    set_cups_placeholder = cups_section["set_placeholder"]
    fill_combos_from_cups = cups_section["fill_combos_from_cups"]
    update_borderless_control = cups_section["update_borderless_control"]
    on_calibration_clicked = cups_section["on_calibration_clicked"]

    qt_section = build_paper_section(dialog, window)
    paper_combo = qt_section["paper_combo"]
    orientation_combo = qt_section["orientation_combo"]
    if sys.platform == "win32":
        paper_combo.setToolTip(
            "On Windows, set the same paper in your printer's preferences "
            "(e.g. Devices and Printers → printer → Printing preferences), "
            "or the system default may be used."
        )

    printer_prefs_btn = QPushButton("Printer preferences…", dialog)
    printer_prefs_btn.setToolTip(
        "Open this printer's Windows preferences to set paper type, quality, "
        "and other options (Qt/Auto printing uses these settings)."
    )

    windows_paper_notice = QLabel(dialog)
    windows_paper_notice.setWordWrap(True)
    windows_paper_notice.setStyleSheet(
        "font-size: 11pt; color: #1a1a1a; padding: 8px; "
        "background-color: #fef3c7; border: 1px solid #f59e0b; border-radius: 4px;"
    )
    windows_paper_notice.setText(
        "On Windows, the app cannot choose the paper in the printer. "
        "You must set the same paper size here and in your printer's preferences "
        "(click \"Printer preferences…\" below), and choose the same size there "
        "(e.g. 10×15 cm / 4×6 in). If the sizes don't match, the wrong paper may be used "
        "and the print may not fill the page."
    )

    fetch_status_label = QLabel("Opening dialog…", dialog)
    fetch_status_label.setStyleSheet("color: #9CA3AF;")

    ipp_caps_for_dialog: Any = None
    ipp_printer_name_value = ""
    printers_loaded = False
    cups_media_key_value = window.cups_media_key
    cups_media_type_key_value = window.cups_media_type_key
    cups_print_quality_key_value = window.cups_print_quality_key

    def set_fetch_status(message: str) -> None:
        fetch_status_label.setText(message)

    def update_printer_combo_for_backend() -> None:
        nonlocal printers_loaded
        backend = backend_combo.currentText()
        if backend == "IPP":
            printer_combo.clear()
            printer_combo.addItem(ipp_printer_name_value or "(unknown)")
            printer_combo.setEnabled(False)
            refresh_printers_btn.setEnabled(False)
        else:
            if not printers_loaded:
                if printer_combo.count() == 0:
                    printer_combo.addItem("(Loading printers…)")
                printer_combo.setEnabled(False)
                refresh_printers_btn.setEnabled(False)
                return
            current = window.printer_value
            window.populate_printers_combo(printer_combo)
            if current:
                printer_combo.setCurrentText(current)
            printer_combo.setEnabled(True)
            refresh_printers_btn.setEnabled(True)

    def update_cups_controls() -> None:
        nonlocal cups_media_key_value, cups_media_type_key_value
        nonlocal cups_print_quality_key_value, ipp_caps_for_dialog
        nonlocal ipp_printer_name_value
        set_fetch_status("Loading printer capabilities…")
        backend = backend_combo.currentText()
        if backend == "Auto" and not window.is_cups_available():
            set_fetch_status("Auto → Qt (CUPS not available)")
            return
        if backend == "IPP":
            uri = ipp_uri_edit.text().strip()
            caps = ipp_section["fill_combos_from_ipp"](
                uri, cups_media_combo, cups_media_type_combo, cups_quality_combo
            )
            ipp_caps_for_dialog = caps
            if caps is None:
                ipp_printer_name_value = ""
                update_printer_combo_for_backend()
                update_borderless_control(backend, None)
                set_cups_placeholder("(IPP unavailable)")
                set_fetch_status("IPP capabilities unavailable")
            else:
                ipp_printer_name_value = caps.printer_name.strip()
                update_printer_combo_for_backend()
                update_borderless_control(backend, caps)
                set_fetch_status("IPP capabilities loaded")
            return
        ipp_caps_for_dialog = None
        update_borderless_control(backend, None)
        resolved = fill_combos_from_cups(printer_combo.currentText())
        cups_media_key_value = resolved.get("media", cups_media_key_value)
        cups_media_type_key_value = resolved.get(
            "media-type", cups_media_type_key_value
        )
        cups_print_quality_key_value = resolved.get(
            "print-quality", cups_print_quality_key_value
        )
        set_fetch_status("Printer capabilities loaded")

    def update_backend_visibility() -> None:
        backend = backend_combo.currentText()
        # Auto: show the same options as whatever would actually be used
        if backend == "Auto":
            effective = "CUPS" if window.is_cups_available() else "Qt"
        else:
            effective = backend
        show_printer = effective in {"CUPS", "IPP", "Qt"}
        show_ipp = effective == "IPP"
        show_paper = effective == "Qt"
        show_cups_options = effective in {"CUPS", "IPP"}

        def set_row_visible(widget: QWidget, visible: bool) -> None:
            widget.setVisible(visible)
            label = form.labelForField(widget)
            if label is not None:
                label.setVisible(visible)

        set_row_visible(printer_combo, show_printer)
        set_row_visible(refresh_printers_btn, show_printer)
        set_row_visible(paper_combo, show_paper)
        set_row_visible(orientation_combo, show_paper)
        show_printer_prefs = show_paper and sys.platform == "win32"
        set_row_visible(printer_prefs_btn, show_printer_prefs)
        windows_paper_notice.setVisible(show_printer_prefs)
        label = form.labelForField(windows_paper_notice)
        if label is not None:
            label.setVisible(show_printer_prefs)
        ipp_uri_edit.setVisible(show_ipp)
        ipp_test_button.setVisible(show_ipp)
        ipp_send_mode_combo.setVisible(show_ipp)
        ipp_uri_label = form.labelForField(ipp_uri_edit)
        if ipp_uri_label is not None:
            ipp_uri_label.setVisible(show_ipp)
        driver_section_label.setVisible(show_cups_options)
        driver_placeholder.setVisible(show_cups_options)
        set_row_visible(cups_media_combo, show_cups_options)
        set_row_visible(borderless_combo, show_cups_options)
        set_row_visible(borderless_scale_row, show_cups_options)
        set_row_visible(cups_media_type_combo, show_cups_options)
        set_row_visible(cups_quality_combo, show_cups_options)
        set_row_visible(calibration_button, show_cups_options)
        update_printer_combo_for_backend()

    def test_ipp_connection() -> None:
        nonlocal ipp_caps_for_dialog, ipp_printer_name_value
        caps = ipp_section["on_test_clicked"](
            dialog,
            cups_media_combo,
            cups_media_type_combo,
            cups_quality_combo,
            set_cups_placeholder,
        )
        if caps is not None:
            ipp_printer_name_value = caps.printer_name.strip()
            ipp_caps_for_dialog = caps
            update_printer_combo_for_backend()
            update_borderless_control(backend_combo.currentText(), caps)

    def refresh_printers() -> None:
        set_fetch_status("Refreshing printer list…")
        current = printer_combo.currentText()
        window.populate_printers_combo(printer_combo)
        if current:
            printer_combo.setCurrentText(current)
        update_cups_controls()

    def open_printer_preferences() -> None:
        if sys.platform != "win32":
            return
        name = printer_combo.currentText().strip()
        if not name:
            QMessageBox.warning(
                dialog,
                "No printer selected",
                "Select a printer above, then use this button to set paper type and quality.",
            )
            return
        try:
            subprocess.Popen(
                ["rundll32", "printui.dll,PrintUIEntry", "/e", "/n", name],
            )
        except OSError as e:
            QMessageBox.warning(
                dialog,
                "Could not open preferences",
                f"Failed to open printer preferences: {e}",
            )

    refresh_printers_btn.clicked.connect(refresh_printers)
    printer_prefs_btn.clicked.connect(open_printer_preferences)
    ipp_test_button.clicked.connect(test_ipp_connection)
    calibration_button.clicked.connect(
        lambda: on_calibration_clicked(dialog, backend_combo, printer_combo)
    )
    printer_combo.currentTextChanged.connect(lambda _: update_cups_controls())
    cups_media_combo.currentIndexChanged.connect(
        lambda: update_borderless_control(
            backend_combo.currentText(), ipp_caps_for_dialog
        )
    )
    borderless_combo.currentIndexChanged.connect(
        lambda: update_borderless_control(
            backend_combo.currentText(), ipp_caps_for_dialog
        )
    )
    backend_combo.currentTextChanged.connect(
        lambda _: (update_backend_visibility(), update_cups_controls())
    )
    ipp_uri_edit.editingFinished.connect(update_cups_controls)

    form.addRow(section_label("Backend"), QLabel("", dialog))
    form.addRow("Print Backend", backend_combo)
    form.addRow("IPP URI", ipp_uri_edit)
    form.addRow("IPP Send Mode", ipp_send_mode_combo)
    form.addRow("", ipp_test_button)
    form.addRow(section_label("Destination"), QLabel("", dialog))
    form.addRow("Printer", printer_combo)
    form.addRow("", refresh_printers_btn)
    form.addRow("Paper", paper_combo)
    form.addRow("Orientation", orientation_combo)
    form.addRow("", printer_prefs_btn)
    form.addRow("", windows_paper_notice)
    form.addRow("Status", fetch_status_label)
    form.addRow(driver_section_label, driver_placeholder)
    form.addRow("Media", cups_media_combo)
    form.addRow("Borderless", borderless_combo)
    form.addRow("Borderless Content Scale", borderless_scale_row)
    form.addRow("Media Type", cups_media_type_combo)
    form.addRow("Quality", cups_quality_combo)
    form.addRow("Calibration", calibration_button)
    layout.addLayout(form)

    update_backend_visibility()
    set_cups_placeholder()
    update_borderless_control(backend_combo.currentText(), ipp_caps_for_dialog)

    buttons = QDialogButtonBox(
        QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
        parent=dialog,
    )
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    layout.addWidget(buttons)

    def load_initial_printer_state() -> None:
        nonlocal printers_loaded
        set_fetch_status("Loading printer list…")
        window.populate_printers_combo(printer_combo)
        printers_loaded = True
        if window.printer_value:
            printer_combo.setCurrentText(window.printer_value)
        else:
            printer_combo.setEnabled(printer_combo.count() > 0)
        refresh_printers_btn.setEnabled(printer_combo.count() > 0)
        update_cups_controls()

    QTimer.singleShot(0, load_initial_printer_state)

    if dialog.exec() != QDialog.DialogCode.Accepted:
        return

    window.print_backend_value = backend_combo.currentText()
    window.ipp_uri_value = ipp_uri_edit.text().strip()
    window.ipp_wait_for_completion_value = bool(ipp_send_mode_combo.currentData())
    window.printer_value = printer_combo.currentText().strip()
    paper_value = paper_combo.currentData()
    if isinstance(paper_value, str):
        window.paper_value = paper_value
    orientation_value = orientation_combo.currentData()
    if isinstance(orientation_value, str):
        window.print_orientation_value = orientation_value
    window.borderless_mode_value = str(borderless_combo.currentData() or "enabled")
    window.borderless_content_scale_percent = borderless_scale_slider.value()
    window.cups_media_value = str(cups_media_combo.currentData() or "")
    window.cups_media_type_value = str(cups_media_type_combo.currentData() or "")
    window.cups_print_quality_value = str(cups_quality_combo.currentData() or "")
    window.cups_media_key = cups_media_key_value
    window.cups_media_type_key = cups_media_type_key_value
    window.cups_print_quality_key = cups_print_quality_key_value
    window.save_app_print_settings()
