from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
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

    ipp_uri_edit = QLineEdit(dialog)
    ipp_uri_edit.setPlaceholderText("ipps://EPSON1234.local:631/ipp/print")
    ipp_uri_edit.setText(window.ipp_uri_value)
    ipp_uri_label: QWidget | None = None
    ipp_test_button = QPushButton("Test IPP Connection", dialog)

    ipp_send_mode_combo = QComboBox(dialog)
    ipp_send_mode_combo.addItem("Wait for completion (sequential)", True)
    ipp_send_mode_combo.addItem("Queue only (faster)", False)
    mode_index = ipp_send_mode_combo.findData(window.ipp_wait_for_completion_value)
    ipp_send_mode_combo.setCurrentIndex(mode_index if mode_index >= 0 else 0)

    printer_combo = QComboBox(dialog)
    printer_combo.addItem("(Loading printers…)")
    printer_combo.setEnabled(False)

    refresh_printers_btn = QPushButton("Refresh Printers", dialog)

    borderless_combo = QComboBox(dialog)
    borderless_combo.addItem("Driver default", "default")
    borderless_combo.addItem("Enabled", "enabled")
    borderless_combo.addItem("Disabled", "disabled")
    borderless_index = borderless_combo.findData(window.borderless_mode_value)
    borderless_combo.setCurrentIndex(borderless_index if borderless_index >= 0 else 1)

    borderless_scale_slider = QSlider(Qt.Orientation.Horizontal, dialog)
    borderless_scale_slider.setRange(85, 110)
    borderless_scale_slider.setValue(window.borderless_content_scale_percent)
    borderless_scale_slider.setMinimumWidth(260)
    borderless_scale_spin = QSpinBox(dialog)
    borderless_scale_spin.setRange(85, 110)
    borderless_scale_spin.setSuffix("%")
    borderless_scale_spin.setValue(window.borderless_content_scale_percent)
    borderless_scale_slider.valueChanged.connect(
        lambda value: (
            borderless_scale_spin.blockSignals(True),
            borderless_scale_spin.setValue(value),
            borderless_scale_spin.blockSignals(False),
        )
    )
    borderless_scale_spin.valueChanged.connect(
        lambda value: borderless_scale_slider.setValue(int(value))
    )
    borderless_scale_row = QWidget(dialog)
    borderless_scale_layout = QHBoxLayout(borderless_scale_row)
    borderless_scale_layout.setContentsMargins(0, 0, 0, 0)
    borderless_scale_layout.addWidget(borderless_scale_slider)
    borderless_scale_layout.addWidget(borderless_scale_spin)

    ipp_caps_for_dialog: Any | None = None

    def update_borderless_control() -> None:
        if backend_combo.currentText() != "IPP":
            selected_media = str(cups_media_combo.currentData() or "")
            if is_explicit_borderless_media_fn(selected_media):
                enabled_index = borderless_combo.findData("enabled")
                if enabled_index >= 0:
                    borderless_combo.setCurrentIndex(enabled_index)
                borderless_combo.setEnabled(False)
                borderless_combo.setToolTip(
                    "Selected media is already a borderless variant."
                )
                borderless_scale_slider.setEnabled(True)
                borderless_scale_slider.setToolTip(
                    "Compensate printer borderless expansion by shrinking content."
                )
                return

            borderless_combo.setEnabled(True)
            borderless_combo.setToolTip("")
            borderless_scale_slider.setEnabled(
                str(borderless_combo.currentData() or "") == "enabled"
            )
            borderless_scale_slider.setToolTip(
                "Only used when Borderless is enabled for CUPS/Auto."
            )
            return

        caps = ipp_caps_for_dialog

        if caps is None:
            borderless_combo.setEnabled(False)
            borderless_combo.setToolTip(
                "Connect to IPP printer first to detect borderless support."
            )
            borderless_scale_slider.setEnabled(False)
            borderless_scale_slider.setToolTip(
                "Only used for CUPS/Auto borderless compensation."
            )
            return

        if caps.borderless_zero_margins_supported:
            borderless_combo.setEnabled(True)
            borderless_combo.setToolTip("")
            borderless_scale_slider.setEnabled(False)
            borderless_scale_slider.setToolTip(
                "Only used for CUPS/Auto borderless compensation."
            )
            return

        disabled_index = borderless_combo.findData("disabled")
        if disabled_index >= 0:
            borderless_combo.setCurrentIndex(disabled_index)
        borderless_combo.setEnabled(False)
        borderless_combo.setToolTip(
            "This IPP printer does not advertise 0-margin borderless support."
        )
        borderless_scale_slider.setEnabled(False)
        borderless_scale_slider.setToolTip(
            "Only used for CUPS/Auto borderless compensation."
        )

    ipp_printer_name_value = ""
    printers_loaded = False

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

    cups_media_combo = QComboBox(dialog)
    cups_media_type_combo = QComboBox(dialog)
    cups_quality_combo = QComboBox(dialog)
    fetch_status_label = QLabel("Opening dialog…", dialog)
    fetch_status_label.setStyleSheet("color: #9CA3AF;")
    calibration_button = QPushButton("Print Borderless Calibration", dialog)
    cups_media_key_value = window.cups_media_key
    cups_media_type_key_value = window.cups_media_type_key
    cups_print_quality_key_value = window.cups_print_quality_key

    def fill_cups_combo(
        combo: QComboBox, kind: str, options: list[str], selected: str
    ) -> None:
        combo.clear()
        combo.addItem("(Driver default)", "")
        for option in options:
            combo.addItem(pretty_option_label_fn(kind, option), option)
        idx = combo.findData(selected)
        combo.setCurrentIndex(idx if idx >= 0 else 0)
        combo.setEnabled(combo.count() > 1)

    def set_cups_placeholder(message: str = "(Load options to view)") -> None:
        cups_media_combo.clear()
        cups_media_combo.addItem(message, "")
        cups_media_type_combo.clear()
        cups_media_type_combo.addItem(message, "")
        cups_quality_combo.clear()
        cups_quality_combo.addItem(message, "")
        cups_media_combo.setEnabled(False)
        cups_media_type_combo.setEnabled(False)
        cups_quality_combo.setEnabled(False)

    def set_fetch_status(message: str) -> None:
        fetch_status_label.setText(message)

    def update_backend_visibility() -> None:
        backend = backend_combo.currentText()
        show_printer = backend in {"Auto", "CUPS", "IPP"}
        printer_combo.setVisible(show_printer)
        refresh_printers_btn.setVisible(show_printer)

        show_ipp = backend == "IPP"
        ipp_uri_edit.setVisible(show_ipp)
        ipp_test_button.setVisible(show_ipp)
        ipp_send_mode_combo.setVisible(show_ipp)
        if ipp_uri_label is not None:
            ipp_uri_label.setVisible(show_ipp)

        update_printer_combo_for_backend()

        show_cups_options = backend in {"Auto", "CUPS", "IPP"}
        cups_media_combo.setVisible(show_cups_options)
        cups_media_type_combo.setVisible(show_cups_options)
        cups_quality_combo.setVisible(show_cups_options)

    def update_cups_controls() -> None:
        nonlocal cups_media_key_value, cups_media_type_key_value
        nonlocal cups_print_quality_key_value
        nonlocal ipp_printer_name_value
        nonlocal ipp_caps_for_dialog
        set_fetch_status("Loading printer capabilities…")
        if backend_combo.currentText() == "IPP":
            ipp_uri = ipp_uri_edit.text().strip()
            caps = window.ipp_capabilities_cache.get(ipp_uri)
            try:
                if caps is None and ipp_uri:
                    caps = get_ipp_capabilities_fn(ipp_uri)
                    window.ipp_capabilities_cache[ipp_uri] = caps
            except ipp_backend_error_cls:
                caps = None
                if ipp_uri:
                    window.ipp_capabilities_cache[ipp_uri] = None

            if caps is None:
                ipp_caps_for_dialog = None
                ipp_printer_name_value = ""
                update_printer_combo_for_backend()
                update_borderless_control()
                cups_media_combo.clear()
                cups_media_combo.addItem("(IPP unavailable)", "")
                cups_media_type_combo.clear()
                cups_media_type_combo.addItem("(IPP unavailable)", "")
                cups_quality_combo.clear()
                cups_quality_combo.addItem("(IPP unavailable)", "")
                cups_media_combo.setEnabled(False)
                cups_media_type_combo.setEnabled(False)
                cups_quality_combo.setEnabled(False)
                set_fetch_status("IPP capabilities unavailable")
            else:
                ipp_caps_for_dialog = caps
                ipp_printer_name_value = caps.printer_name.strip()
                update_printer_combo_for_backend()
                update_borderless_control()
                fill_cups_combo(
                    cups_media_combo,
                    "media",
                    caps.media,
                    window.cups_media_value,
                )
                fill_cups_combo(
                    cups_media_type_combo,
                    "media-type",
                    caps.media_type,
                    window.cups_media_type_value,
                )
                fill_cups_combo(
                    cups_quality_combo,
                    "quality",
                    [str(value) for value in caps.print_quality],
                    window.cups_print_quality_value,
                )
                set_fetch_status("IPP capabilities loaded")
            return

        ipp_caps_for_dialog = None
        update_borderless_control()

        caps, resolved_keys = window.get_cups_capabilities(printer_combo.currentText())
        cups_media_key_value = resolved_keys.get("media", cups_media_key_value)
        cups_media_type_key_value = resolved_keys.get(
            "media-type", cups_media_type_key_value
        )
        cups_print_quality_key_value = resolved_keys.get(
            "print-quality", cups_print_quality_key_value
        )
        fill_cups_combo(
            cups_media_combo,
            "media",
            caps.get("media", []),
            window.cups_media_value,
        )
        fill_cups_combo(
            cups_media_type_combo,
            "media-type",
            caps.get("media-type", []),
            window.cups_media_type_value,
        )
        fill_cups_combo(
            cups_quality_combo,
            "quality",
            caps.get("print-quality", []),
            window.cups_print_quality_value,
        )
        set_fetch_status("Printer capabilities loaded")

    def test_ipp_connection() -> None:
        nonlocal ipp_printer_name_value
        nonlocal ipp_caps_for_dialog
        uri = ipp_uri_edit.text().strip()
        if not uri:
            QMessageBox.warning(
                dialog,
                "No IPP URI",
                "Enter an IPP/IPPS URI first.",
            )
            return
        if backend_combo.currentText() != "IPP":
            QMessageBox.information(
                dialog,
                "IPP backend not selected",
                "Select Print Backend = IPP to test and load IPP options.",
            )
            return

        try:
            caps = get_ipp_capabilities_fn(uri)
            window.ipp_capabilities_cache[uri] = caps
        except ipp_backend_error_cls as error:
            window.ipp_capabilities_cache[uri] = None
            QMessageBox.warning(dialog, "IPP connection failed", str(error))
            set_cups_placeholder("(IPP unavailable)")
            return

        ipp_printer_name_value = caps.printer_name.strip()
        ipp_caps_for_dialog = caps
        update_printer_combo_for_backend()
        update_borderless_control()

        fill_cups_combo(
            cups_media_combo,
            "media",
            caps.media,
            window.cups_media_value,
        )
        fill_cups_combo(
            cups_media_type_combo,
            "media-type",
            caps.media_type,
            window.cups_media_type_value,
        )
        fill_cups_combo(
            cups_quality_combo,
            "quality",
            [str(value) for value in caps.print_quality],
            window.cups_print_quality_value,
        )
        QMessageBox.information(
            dialog,
            "IPP connected",
            f"Connected to {uri}\n"
            f"Printer: {ipp_printer_name_value or '(unknown)'}\n"
            f"Media: {len(caps.media)}\n"
            f"Media Type: {len(caps.media_type)}\n"
            f"Quality: {len(caps.print_quality)}",
        )

    def refresh_printers() -> None:
        set_fetch_status("Refreshing printer list…")
        current = printer_combo.currentText()
        window.populate_printers_combo(printer_combo)
        if current:
            printer_combo.setCurrentText(current)
        update_cups_controls()

    def print_borderless_calibration() -> None:
        backend = backend_combo.currentText()
        if backend == "IPP":
            QMessageBox.information(
                dialog,
                "CUPS required",
                "Borderless calibration currently uses CUPS queue options. "
                "Switch backend to CUPS (or Auto with CUPS) first.",
            )
            return

        printer = printer_combo.currentText().strip()
        if not printer:
            QMessageBox.warning(
                dialog,
                "No printer",
                "Select a CUPS printer first.",
            )
            return

        selected_media = str(cups_media_combo.currentData() or "")
        if not selected_media:
            QMessageBox.warning(
                dialog,
                "No media",
                "Select a media size first (for example 4x6.Borderless).",
            )
            return

        effective_media_value = resolve_cups_media_value_fn(
            selected_media,
            window.get_cups_capabilities(printer)[0].get("media", []),
            True,
        )

        scales = [95, 97, 99]
        queued_count, errors = window.print_borderless_calibration_pages(
            printer_name=printer,
            media_value=effective_media_value,
            media_type_value=str(cups_media_type_combo.currentData() or ""),
            print_quality_value=str(cups_quality_combo.currentData() or ""),
            scale_values=scales,
        )

        if queued_count:
            window.append_log(
                "INFO",
                "Queued borderless calibration set to "
                f"{printer}: {queued_count} page(s)",
            )

        if errors:
            QMessageBox.warning(
                dialog,
                "Calibration print partial",
                "Some calibration pages failed:\n\n" + "\n".join(errors[:4]),
            )
            return

        chooser = QMessageBox(dialog)
        chooser.setWindowTitle("Calibration queued")
        chooser.setIcon(QMessageBox.Icon.Information)
        chooser.setText(
            "Queued calibration pages 1/2/3.\n"
            "After you compare prints, choose which page looks best."
        )
        chooser.setInformativeText(
            f"1 | {scales[0]}%   ·   2 | {scales[1]}%   ·   3 | {scales[2]}%\n"
            f"Between 1-2: {(scales[0] + scales[1]) // 2}%   ·   "
            f"Between 2-3: {(scales[1] + scales[2]) // 2}%\n"
            "You can also keep current and decide later."
        )
        mid_12 = (scales[0] + scales[1]) // 2
        mid_23 = (scales[1] + scales[2]) // 2
        button_1 = chooser.addButton(
            f"Use 1 ({scales[0]}%)", QMessageBox.ButtonRole.AcceptRole
        )
        button_12 = chooser.addButton(
            f"Use 1-2 Mid ({mid_12}%)", QMessageBox.ButtonRole.AcceptRole
        )
        button_2 = chooser.addButton(
            f"Use 2 ({scales[1]}%)", QMessageBox.ButtonRole.AcceptRole
        )
        button_23 = chooser.addButton(
            f"Use 2-3 Mid ({mid_23}%)", QMessageBox.ButtonRole.AcceptRole
        )
        button_3 = chooser.addButton(
            f"Use 3 ({scales[2]}%)", QMessageBox.ButtonRole.AcceptRole
        )
        chooser.addButton("Keep current", QMessageBox.ButtonRole.RejectRole)
        chooser.exec()

        chosen_scale: int | None = None
        clicked = chooser.clickedButton()
        if clicked == button_1:
            chosen_scale = scales[0]
        elif clicked == button_2:
            chosen_scale = scales[1]
        elif clicked == button_3:
            chosen_scale = scales[2]
        elif clicked == button_12:
            chosen_scale = mid_12
        elif clicked == button_23:
            chosen_scale = mid_23

        if chosen_scale is not None:
            borderless_scale_slider.setValue(chosen_scale)
            window.append_log(
                "INFO",
                f"Applied Borderless Content Scale from calibration: {chosen_scale}%",
            )

    refresh_printers_btn.clicked.connect(refresh_printers)
    ipp_test_button.clicked.connect(test_ipp_connection)
    calibration_button.clicked.connect(print_borderless_calibration)
    printer_combo.currentTextChanged.connect(lambda _value: update_cups_controls())
    cups_media_combo.currentIndexChanged.connect(
        lambda _value: update_borderless_control()
    )
    borderless_combo.currentIndexChanged.connect(
        lambda _value: update_borderless_control()
    )
    backend_combo.currentTextChanged.connect(
        lambda _value: (update_backend_visibility(), update_cups_controls())
    )
    ipp_uri_edit.editingFinished.connect(update_cups_controls)
    update_backend_visibility()
    set_cups_placeholder()
    update_borderless_control()

    form.addRow(section_label("Backend"), QLabel("", dialog))
    form.addRow("Print Backend", backend_combo)
    form.addRow("IPP URI", ipp_uri_edit)
    ipp_uri_label = form.labelForField(ipp_uri_edit)
    form.addRow("IPP Send Mode", ipp_send_mode_combo)
    form.addRow("", ipp_test_button)
    form.addRow(section_label("Destination"), QLabel("", dialog))
    form.addRow("Printer", printer_combo)
    form.addRow("", refresh_printers_btn)
    form.addRow("Status", fetch_status_label)
    form.addRow(section_label("Driver Options"), QLabel("", dialog))
    form.addRow("Media", cups_media_combo)
    form.addRow("Borderless", borderless_combo)
    form.addRow("Borderless Content Scale", borderless_scale_row)
    form.addRow("Media Type", cups_media_type_combo)
    form.addRow("Quality", cups_quality_combo)
    form.addRow("Calibration", calibration_button)
    layout.addLayout(form)

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
    window.borderless_mode_value = str(borderless_combo.currentData() or "enabled")
    window.borderless_content_scale_percent = borderless_scale_slider.value()
    window.cups_media_value = str(cups_media_combo.currentData() or "")
    window.cups_media_type_value = str(cups_media_type_combo.currentData() or "")
    window.cups_print_quality_value = str(cups_quality_combo.currentData() or "")
    window.cups_media_key = cups_media_key_value
    window.cups_media_type_key = cups_media_type_key_value
    window.cups_print_quality_key = cups_print_quality_key_value
    window.save_app_print_settings()
