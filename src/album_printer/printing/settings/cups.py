"""CUPS / IPP driver options UI (media, type, quality, borderless, calibration)."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSlider,
    QSpinBox,
    QWidget,
)


def build_driver_options_section(
    parent: Any,
    window: Any,
    *,
    pretty_option_label_fn: Any,
    is_explicit_borderless_media_fn: Any,
    resolve_cups_media_value_fn: Any,
) -> dict[str, Any]:
    """Build driver options widgets (Media, Media Type, Quality, Borderless, Calibration).

    Returns a dict with: section_label, placeholder, media_combo, type_combo, quality_combo,
    borderless_combo, borderless_scale_row, calibration_button, fill_combo_fn, set_placeholder_fn,
    fill_combos_from_cups(printer_name) -> resolved_keys,
    update_borderless_control(backend: str, ipp_caps: Any),
    on_calibration_clicked(dialog, backend_combo, printer_combo).
    """
    section_label = QLabel("Driver Options (CUPS / IPP)", parent)
    section_label.setStyleSheet("font-weight: 600;")
    placeholder = QLabel("", parent)

    media_combo = QComboBox(parent)
    type_combo = QComboBox(parent)
    quality_combo = QComboBox(parent)

    borderless_combo = QComboBox(parent)
    borderless_combo.addItem("Driver default", "default")
    borderless_combo.addItem("Enabled", "enabled")
    borderless_combo.addItem("Disabled", "disabled")
    borderless_index = borderless_combo.findData(window.borderless_mode_value)
    borderless_combo.setCurrentIndex(borderless_index if borderless_index >= 0 else 1)

    borderless_scale_slider = QSlider(Qt.Orientation.Horizontal, parent)
    borderless_scale_slider.setRange(85, 110)
    borderless_scale_slider.setValue(window.borderless_content_scale_percent)
    borderless_scale_slider.setMinimumWidth(260)
    borderless_scale_spin = QSpinBox(parent)
    borderless_scale_spin.setRange(85, 110)
    borderless_scale_spin.setSuffix("%")
    borderless_scale_spin.setValue(window.borderless_content_scale_percent)
    borderless_scale_slider.valueChanged.connect(
        lambda v: (
            borderless_scale_spin.blockSignals(True),
            borderless_scale_spin.setValue(v),
            borderless_scale_spin.blockSignals(False),
        )
    )
    borderless_scale_spin.valueChanged.connect(
        lambda v: borderless_scale_slider.setValue(int(v))
    )
    borderless_scale_row = QWidget(parent)
    borderless_scale_layout = QHBoxLayout(borderless_scale_row)
    borderless_scale_layout.setContentsMargins(0, 0, 0, 0)
    borderless_scale_layout.addWidget(borderless_scale_slider)
    borderless_scale_layout.addWidget(borderless_scale_spin)

    calibration_button = QPushButton("Print Borderless Calibration", parent)

    def fill_combo(
        combo: QComboBox, kind: str, options: list[str], selected: str
    ) -> None:
        combo.clear()
        combo.addItem("(Driver default)", "")
        for option in options:
            combo.addItem(pretty_option_label_fn(kind, option), option)
        idx = combo.findData(selected)
        combo.setCurrentIndex(idx if idx >= 0 else 0)
        combo.setEnabled(combo.count() > 1)

    def set_placeholder(message: str = "(Load options to view)") -> None:
        media_combo.clear()
        media_combo.addItem(message, "")
        type_combo.clear()
        type_combo.addItem(message, "")
        quality_combo.clear()
        quality_combo.addItem(message, "")
        media_combo.setEnabled(False)
        type_combo.setEnabled(False)
        quality_combo.setEnabled(False)

    def fill_combos_from_cups(printer_name: str) -> dict[str, str]:
        caps, resolved_keys = window.get_cups_capabilities(printer_name)
        fill_combo(media_combo, "media", caps.get("media", []), window.cups_media_value)
        fill_combo(
            type_combo,
            "media-type",
            caps.get("media-type", []),
            window.cups_media_type_value,
        )
        fill_combo(
            quality_combo,
            "quality",
            caps.get("print-quality", []),
            window.cups_print_quality_value,
        )
        return resolved_keys

    def update_borderless_control(backend: str, ipp_caps: Any) -> None:
        if backend != "IPP":
            selected_media = str(media_combo.currentData() or "")
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
        if ipp_caps is None:
            borderless_combo.setEnabled(False)
            borderless_combo.setToolTip(
                "Connect to IPP printer first to detect borderless support."
            )
            borderless_scale_slider.setEnabled(False)
            borderless_scale_slider.setToolTip(
                "Only used for CUPS/Auto borderless compensation."
            )
            return
        if ipp_caps.borderless_zero_margins_supported:
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

    def on_calibration_clicked(
        dialog: Any,
        backend_combo: QComboBox,
        printer_combo: QComboBox,
    ) -> None:
        if backend_combo.currentText() == "IPP":
            QMessageBox.information(
                dialog,
                "CUPS required",
                "Borderless calibration currently uses CUPS queue options. "
                "Switch backend to CUPS (or Auto with CUPS) first.",
            )
            return
        printer = printer_combo.currentText().strip()
        if not printer:
            QMessageBox.warning(dialog, "No printer", "Select a CUPS printer first.")
            return
        selected_media = str(media_combo.currentData() or "")
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
            media_type_value=str(type_combo.currentData() or ""),
            print_quality_value=str(quality_combo.currentData() or ""),
            scale_values=scales,
        )
        if queued_count:
            window.append_log(
                "INFO",
                f"Queued borderless calibration set to {printer}: {queued_count} page(s)",
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

    return {
        "section_label": section_label,
        "placeholder": placeholder,
        "media_combo": media_combo,
        "type_combo": type_combo,
        "quality_combo": quality_combo,
        "borderless_combo": borderless_combo,
        "borderless_scale_row": borderless_scale_row,
        "borderless_scale_slider": borderless_scale_slider,
        "calibration_button": calibration_button,
        "fill_combo": fill_combo,
        "set_placeholder": set_placeholder,
        "fill_combos_from_cups": fill_combos_from_cups,
        "update_borderless_control": update_borderless_control,
        "on_calibration_clicked": on_calibration_clicked,
    }
