from __future__ import annotations

import json
import random
from datetime import datetime
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw
from PIL.ImageQt import ImageQt
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QImage, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSlider,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


def open_project_settings_dialog(
    window: Any,
    *,
    crop_ratios: list[str],
    crop_ratio_labels: dict[str, str],
    location_format_options: list[str],
    location_format_template_default: str,
    location_template_tokens: list[str],
    stamp_fonts: dict[str, str],
    stamp_scale_min_percent: int,
    stamp_scale_max_percent: int,
    stamp_offset_min_px: int,
    stamp_offset_max_px: int,
    default_stamp_color: str,
    default_stamp_border_color: str,
    processing_settings_cls: Any,
    load_image_as_rgb_fn: Any,
    normalized_geocodejson_geocoding_fn: Any,
    normalized_geocodejson_feature_fn: Any,
    render_location_template_fn: Any,
    location_format_needs_reverse_lookup_fn: Any,
    datetime_for_image_fn: Any,
    center_crop_to_ratio_fn: Any,
    apply_stamp_fn: Any,
) -> None:
    dialog = QDialog(window)
    dialog.setWindowTitle("Image Settings")
    dialog.setModal(True)
    dialog.resize(1240, 820)

    preview_source_path: Path | None = None
    preview_source_image: Image.Image | None = None
    placeholder_preview_location = (60.19606, 11.10040)
    placeholder_geocode_payload: dict[str, object] = {
        "features": [
            {
                "properties": {
                    "geocoding": {
                        "label": "1, Løvenbergvegen, Mogreina, Ullensaker, Akershus, 2054, Norway",
                        "housenumber": "1",
                        "street": "Løvenbergvegen",
                        "postcode": "2054",
                        "county": "Akershus",
                        "country": "Norway",
                        "city": "Mogreina",
                        "admin": {
                            "level7": "Ullensaker",
                            "level4": "Akershus",
                            "level2": "Norway",
                        },
                    }
                }
            }
        ]
    }

    def placeholder_preview_image() -> Image.Image:
        placeholder = Image.new("RGB", (1600, 1000), "#253341")
        draw = ImageDraw.Draw(placeholder)
        draw.rectangle((0, 0, 1600, 520), fill="#2f4858")
        draw.polygon([(0, 760), (420, 460), (860, 760)], fill="#455a64")
        draw.polygon([(620, 760), (1040, 400), (1600, 760)], fill="#546e7a")
        draw.ellipse((1210, 120, 1360, 270), fill="#ffe082")
        draw.rectangle((0, 760, 1600, 1000), fill="#37474f")
        return placeholder

    if window.image_paths:
        preview_source_path = random.choice(window.image_paths)
        try:
            preview_source_image = load_image_as_rgb_fn(
                preview_source_path,
                debug_logger=lambda message: window.append_log("DEBUG", message),
            )
        except OSError:
            preview_source_image = None

    if preview_source_image is None:
        preview_source_image = placeholder_preview_image()

    original_values = {
        "crop_ratio_value": window.crop_ratio_value,
        "stamp_mode_value": window.stamp_mode_value,
        "clock_mode_value": window.clock_mode_value,
        "corner_landscape_value": window.corner_landscape_value,
        "corner_portrait_value": window.corner_portrait_value,
        "location_stamp_mode_value": window.location_stamp_mode_value,
        "location_format_value": window.location_format_value,
        "location_format_template_value": window.location_format_template_value,
        "location_corner_landscape_value": window.location_corner_landscape_value,
        "location_corner_portrait_value": window.location_corner_portrait_value,
        "stamp_font_value": window.stamp_font_value,
        "stamp_scale_percent": window.stamp_scale_percent,
        "stamp_offset_x_px": window.stamp_offset_x_px,
        "stamp_offset_y_px": window.stamp_offset_y_px,
        "stamp_vertical_value": window.stamp_vertical_value,
        "stamp_color_value": window.stamp_color_value,
        "stamp_border_color_value": window.stamp_border_color_value,
        "location_stamp_scale_percent": window.location_stamp_scale_percent,
        "location_stamp_offset_x_px": window.location_stamp_offset_x_px,
        "location_stamp_offset_y_px": window.location_stamp_offset_y_px,
        "location_stamp_vertical_value": window.location_stamp_vertical_value,
        "location_stamp_color_value": window.location_stamp_color_value,
        "location_stamp_border_color_value": window.location_stamp_border_color_value,
    }

    layout = QVBoxLayout(dialog)
    info_label = QLabel("These settings are saved for this app.", dialog)
    info_label.setWordWrap(True)
    layout.addWidget(info_label)

    content_layout = QHBoxLayout()
    layout.addLayout(content_layout, 1)

    controls_container = QWidget(dialog)
    controls_container.setMinimumWidth(620)
    form = QFormLayout()
    controls_container.setLayout(form)

    preview_container = QWidget(dialog)
    preview_layout = QVBoxLayout(preview_container)
    preview_layout.setContentsMargins(0, 0, 0, 0)
    preview_title = QLabel("Stamp Preview", dialog)
    preview_title.setStyleSheet("font-weight: 600;")
    preview_layout.addWidget(preview_title)
    preview_source_label = QLabel(
        (
            f"Source: {preview_source_path.name}"
            if preview_source_path is not None
            else "Source: placeholder (sample geocodejson)"
        ),
        dialog,
    )
    preview_source_label.setStyleSheet("color: #9CA3AF;")
    preview_layout.addWidget(preview_source_label)
    preview_random_button = QPushButton("Randomize Preview", dialog)
    preview_random_button.setEnabled(bool(window.image_paths))
    preview_layout.addWidget(preview_random_button)
    preview_label = QLabel(dialog)
    preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    preview_label.setMinimumSize(520, 360)
    preview_label.setStyleSheet("background: #111; border: 1px solid #2f2f2f;")
    preview_layout.addWidget(preview_label, 1)

    content_layout.addWidget(controls_container, 3)
    content_layout.addWidget(preview_container, 2)

    def section_label(text: str) -> QLabel:
        label = QLabel(text, dialog)
        label.setStyleSheet("font-weight: 600;")
        return label

    crop_ratio_combo = QComboBox(dialog)
    for ratio in crop_ratios:
        crop_ratio_combo.addItem(crop_ratio_labels.get(ratio, ratio), ratio)
    ratio_index = crop_ratio_combo.findData(window.crop_ratio_value)
    crop_ratio_combo.setCurrentIndex(ratio_index if ratio_index >= 0 else 0)

    stamp_mode_combo = QComboBox(dialog)
    stamp_mode_combo.addItems(["None", "Date", "Date + Time"])
    stamp_mode_combo.setCurrentText(window.stamp_mode_value)

    clock_mode_combo = QComboBox(dialog)
    clock_mode_combo.addItems(["24h", "12h"])
    clock_mode_combo.setCurrentText(window.clock_mode_value)

    corner_landscape_combo = QComboBox(dialog)
    corner_landscape_combo.addItems(
        ["Bottom Right", "Bottom Left", "Top Right", "Top Left"]
    )
    corner_landscape_combo.setCurrentText(window.corner_landscape_value)

    corner_portrait_combo = QComboBox(dialog)
    corner_portrait_combo.addItems(
        ["Bottom Right", "Bottom Left", "Top Right", "Top Left"]
    )
    corner_portrait_combo.setCurrentText(window.corner_portrait_value)

    location_stamp_mode_combo = QComboBox(dialog)
    location_stamp_mode_combo.addItems(["Off", "Coordinates"])
    location_stamp_mode_combo.setCurrentText(window.location_stamp_mode_value)

    location_format_combo = QComboBox(dialog)
    location_format_combo.addItems(location_format_options)
    location_format_combo.setCurrentText(window.location_format_value)
    gps_pending_label = QLabel(dialog)
    gps_pending_label.setStyleSheet("color: #9CA3AF;")

    def update_dialog_gps_status() -> None:
        previous_format = window.location_format_value
        window.location_format_value = location_format_combo.currentText().strip()
        try:
            resolved, total = window.gps_resolution_progress_counts()
        finally:
            window.location_format_value = previous_format

        pending = max(0, total - resolved)
        if total > 0:
            gps_pending_label.setText(
                f"GPS pending: {pending} ({resolved}/{total} resolved)"
            )
        else:
            gps_pending_label.setText("GPS pending: 0")

    location_format_template_edit = QLineEdit(dialog)
    location_format_template_edit.setText(window.location_format_template_value)
    location_format_template_edit.setPlaceholderText(location_format_template_default)
    location_template_editor_button = QPushButton("Template Editor…", dialog)

    def open_location_template_editor() -> None:
        editor_dialog = QDialog(dialog)
        editor_dialog.setWindowTitle("Location Template Editor")
        editor_dialog.setModal(True)
        editor_dialog.resize(760, 460)

        editor_layout = QVBoxLayout(editor_dialog)
        editor_layout.addWidget(
            QLabel(
                "Click a token to insert it at the cursor position in the template.",
                editor_dialog,
            )
        )

        template_editor = QTextEdit(editor_dialog)
        current_template = location_format_template_edit.text().strip()
        template_editor.setPlainText(
            current_template or location_format_template_default
        )
        editor_layout.addWidget(template_editor, 1)

        preview_label_local = QLabel("Preview", editor_dialog)
        preview_label_local.setStyleSheet("font-weight: 600;")
        editor_layout.addWidget(preview_label_local)

        preview_value_label = QLabel(editor_dialog)
        preview_value_label.setWordWrap(True)
        preview_value_label.setStyleSheet(
            "background: #111; border: 1px solid #2f2f2f; padding: 8px;"
        )
        editor_layout.addWidget(preview_value_label)

        tokens_label = QLabel("Available tokens", editor_dialog)
        tokens_label.setStyleSheet("font-weight: 600;")
        editor_layout.addWidget(tokens_label)

        tokens_container = QWidget(editor_dialog)
        tokens_layout = QVBoxLayout(tokens_container)
        tokens_layout.setContentsMargins(0, 0, 0, 0)
        tokens_layout.setSpacing(6)

        resolved_payload: object = placeholder_geocode_payload
        resolved_payload_source = "Sample data"
        if preview_source_path is not None:
            preview_location = window.location_for_path(preview_source_path)
            if preview_location is not None:
                payload_cache_key = window.nominatim_payload_cache_key(
                    preview_location[0],
                    preview_location[1],
                )
                payload_cached = window.nominatim_cache.get(payload_cache_key)
                if not (isinstance(payload_cached, str) and payload_cached.strip()):
                    window.reverse_geocode_nominatim(
                        preview_location,
                        path=preview_source_path,
                        format_value="Address Label",
                    )
                    payload_cached = window.nominatim_cache.get(payload_cache_key)
                if isinstance(payload_cached, str) and payload_cached.strip():
                    try:
                        parsed_payload = json.loads(payload_cached)
                        if isinstance(parsed_payload, (dict, list)):
                            resolved_payload = parsed_payload
                            resolved_payload_source = (
                                f"Preview image data ({preview_source_path.name})"
                            )
                    except (TypeError, ValueError, json.JSONDecodeError):
                        pass

        preview_source_label_local = QLabel(
            f"Preview source: {resolved_payload_source}",
            editor_dialog,
        )
        preview_source_label_local.setStyleSheet("color: #9CA3AF;")
        editor_layout.addWidget(preview_source_label_local)

        geocoding_values = normalized_geocodejson_geocoding_fn(resolved_payload)
        token_values: dict[str, str] = {
            key: value for key, value in geocoding_values.items() if value
        }
        for field in ("city", "town", "village", "hamlet", "municipality"):
            candidate = geocoding_values.get(field, "")
            if candidate:
                token_values.setdefault("city", candidate)
                break

        feature = normalized_geocodejson_feature_fn(resolved_payload)
        properties = feature.get("properties") if isinstance(feature, dict) else None
        geocoding_raw = (
            properties.get("geocoding") if isinstance(properties, dict) else None
        )
        admin = geocoding_raw.get("admin") if isinstance(geocoding_raw, dict) else None
        if isinstance(admin, dict):
            for key, value in admin.items():
                if not isinstance(key, str) or not isinstance(value, str):
                    continue
                text = value.strip()
                if text:
                    token_values[f"admin.{key}"] = text

        row_layout: QHBoxLayout | None = None
        for index, token in enumerate(location_template_tokens):
            if index % 4 == 0:
                row_layout = QHBoxLayout()
                row_layout.setContentsMargins(0, 0, 0, 0)
                row_layout.setSpacing(6)
                tokens_layout.addLayout(row_layout)
            if row_layout is None:
                continue
            token_text = "{" + token + "}"
            token_value = token_values.get(token, "")
            token_caption = (
                token_text if not token_value else f"{token_text} = {token_value}"
            )
            token_button = QPushButton(token_text, editor_dialog)
            token_button.setText(token_caption)
            token_button.setToolTip(token_caption)
            token_button.clicked.connect(
                lambda _checked=False, text=token_text: template_editor.insertPlainText(
                    text
                )
            )
            row_layout.addWidget(token_button)

        editor_layout.addWidget(tokens_container)

        def update_template_preview() -> None:
            source_text = template_editor.toPlainText().strip()
            rendered = render_location_template_fn(
                source_text or location_format_template_default,
                resolved_payload,
            )
            preview_value_label.setText(rendered or "(empty output)")

        template_editor.textChanged.connect(update_template_preview)
        update_template_preview()

        editor_buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            parent=editor_dialog,
        )
        editor_buttons.accepted.connect(editor_dialog.accept)
        editor_buttons.rejected.connect(editor_dialog.reject)
        editor_layout.addWidget(editor_buttons)

        if editor_dialog.exec() != QDialog.DialogCode.Accepted:
            return

        new_template = template_editor.toPlainText().strip()
        location_format_template_edit.setText(
            new_template or location_format_template_default
        )

    location_template_editor_button.clicked.connect(open_location_template_editor)

    location_corner_landscape_combo = QComboBox(dialog)
    location_corner_landscape_combo.addItems(
        ["Bottom Right", "Bottom Left", "Top Right", "Top Left"]
    )
    location_corner_landscape_combo.setCurrentText(
        window.location_corner_landscape_value
    )

    location_corner_portrait_combo = QComboBox(dialog)
    location_corner_portrait_combo.addItems(
        ["Bottom Right", "Bottom Left", "Top Right", "Top Left"]
    )
    location_corner_portrait_combo.setCurrentText(window.location_corner_portrait_value)

    stamp_font_combo = QComboBox(dialog)
    stamp_font_combo.addItems(list(stamp_fonts.keys()))
    stamp_font_combo.setCurrentText(window.stamp_font_value)

    stamp_scale_slider = QSlider(Qt.Orientation.Horizontal, dialog)
    stamp_scale_slider.setRange(stamp_scale_min_percent, stamp_scale_max_percent)
    stamp_scale_slider.setValue(window.stamp_scale_percent)
    stamp_scale_label = QLabel(f"{window.stamp_scale_percent}%", dialog)
    stamp_scale_spin = QSpinBox(dialog)
    stamp_scale_spin.setRange(stamp_scale_min_percent, stamp_scale_max_percent)
    stamp_scale_spin.setSuffix("%")
    stamp_scale_spin.setValue(window.stamp_scale_percent)
    stamp_scale_slider.valueChanged.connect(
        lambda value: stamp_scale_label.setText(f"{value}%")
    )
    stamp_scale_slider.valueChanged.connect(
        lambda value: (
            stamp_scale_spin.blockSignals(True),
            stamp_scale_spin.setValue(value),
            stamp_scale_spin.blockSignals(False),
        )
    )
    stamp_scale_spin.valueChanged.connect(stamp_scale_slider.setValue)
    stamp_scale_row = QWidget(dialog)
    stamp_scale_layout = QHBoxLayout(stamp_scale_row)
    stamp_scale_layout.setContentsMargins(0, 0, 0, 0)
    stamp_scale_layout.addWidget(stamp_scale_slider)
    stamp_scale_layout.addWidget(stamp_scale_label)
    stamp_scale_layout.addWidget(stamp_scale_spin)

    stamp_offset_x_slider = QSlider(Qt.Orientation.Horizontal, dialog)
    stamp_offset_x_slider.setRange(stamp_offset_min_px, stamp_offset_max_px)
    stamp_offset_x_slider.setValue(window.stamp_offset_x_px)
    stamp_offset_x_label = QLabel(f"{window.stamp_offset_x_px / 10:.1f}%", dialog)
    stamp_offset_x_spin = QDoubleSpinBox(dialog)
    stamp_offset_x_spin.setRange(
        stamp_offset_min_px / 10.0,
        stamp_offset_max_px / 10.0,
    )
    stamp_offset_x_spin.setSingleStep(0.1)
    stamp_offset_x_spin.setDecimals(1)
    stamp_offset_x_spin.setSuffix("%")
    stamp_offset_x_spin.setValue(window.stamp_offset_x_px / 10.0)
    stamp_offset_x_slider.valueChanged.connect(
        lambda value: stamp_offset_x_label.setText(f"{value / 10:.1f}%")
    )
    stamp_offset_x_slider.valueChanged.connect(
        lambda value: (
            stamp_offset_x_spin.blockSignals(True),
            stamp_offset_x_spin.setValue(value / 10.0),
            stamp_offset_x_spin.blockSignals(False),
        )
    )
    stamp_offset_x_spin.valueChanged.connect(
        lambda value: stamp_offset_x_slider.setValue(int(round(value * 10)))
    )
    stamp_offset_x_row = QWidget(dialog)
    stamp_offset_x_layout = QHBoxLayout(stamp_offset_x_row)
    stamp_offset_x_layout.setContentsMargins(0, 0, 0, 0)
    stamp_offset_x_layout.addWidget(stamp_offset_x_slider)
    stamp_offset_x_layout.addWidget(stamp_offset_x_label)
    stamp_offset_x_layout.addWidget(stamp_offset_x_spin)

    stamp_offset_y_slider = QSlider(Qt.Orientation.Horizontal, dialog)
    stamp_offset_y_slider.setRange(stamp_offset_min_px, stamp_offset_max_px)
    stamp_offset_y_slider.setValue(window.stamp_offset_y_px)
    stamp_offset_y_label = QLabel(f"{window.stamp_offset_y_px / 10:.1f}%", dialog)
    stamp_offset_y_spin = QDoubleSpinBox(dialog)
    stamp_offset_y_spin.setRange(
        stamp_offset_min_px / 10.0,
        stamp_offset_max_px / 10.0,
    )
    stamp_offset_y_spin.setSingleStep(0.1)
    stamp_offset_y_spin.setDecimals(1)
    stamp_offset_y_spin.setSuffix("%")
    stamp_offset_y_spin.setValue(window.stamp_offset_y_px / 10.0)
    stamp_offset_y_slider.valueChanged.connect(
        lambda value: stamp_offset_y_label.setText(f"{value / 10:.1f}%")
    )
    stamp_offset_y_slider.valueChanged.connect(
        lambda value: (
            stamp_offset_y_spin.blockSignals(True),
            stamp_offset_y_spin.setValue(value / 10.0),
            stamp_offset_y_spin.blockSignals(False),
        )
    )
    stamp_offset_y_spin.valueChanged.connect(
        lambda value: stamp_offset_y_slider.setValue(int(round(value * 10)))
    )
    stamp_offset_y_row = QWidget(dialog)
    stamp_offset_y_layout = QHBoxLayout(stamp_offset_y_row)
    stamp_offset_y_layout.setContentsMargins(0, 0, 0, 0)
    stamp_offset_y_layout.addWidget(stamp_offset_y_slider)
    stamp_offset_y_layout.addWidget(stamp_offset_y_label)
    stamp_offset_y_layout.addWidget(stamp_offset_y_spin)

    stamp_vertical_checkbox = QCheckBox("Vertical stamp", dialog)
    stamp_vertical_checkbox.setChecked(window.stamp_vertical_value)

    stamp_color_button = QPushButton(dialog)
    stamp_color_reset_button = QPushButton("Reset", dialog)
    stamp_color_value = window.stamp_color_value
    stamp_border_color_button = QPushButton(dialog)
    stamp_border_color_reset_button = QPushButton("Reset", dialog)
    stamp_border_color_value = window.stamp_border_color_value

    def update_stamp_color_button() -> None:
        nonlocal stamp_color_value
        color = QColor(stamp_color_value)
        if not color.isValid():
            color = QColor(default_stamp_color)
            stamp_color_value = color.name().upper()
        text_color = "#000000" if color.lightness() > 128 else "#FFFFFF"
        stamp_color_button.setText(stamp_color_value)
        stamp_color_button.setStyleSheet(
            f"background-color: {stamp_color_value}; color: {text_color};"
        )

    def pick_stamp_color() -> None:
        nonlocal stamp_color_value
        selected = QColorDialog.getColor(QColor(stamp_color_value), dialog)
        if not selected.isValid():
            return
        stamp_color_value = selected.name().upper()
        update_stamp_color_button()

    def reset_stamp_color() -> None:
        nonlocal stamp_color_value
        stamp_color_value = default_stamp_color
        update_stamp_color_button()

    def update_stamp_border_color_button() -> None:
        nonlocal stamp_border_color_value
        color = QColor(stamp_border_color_value)
        if not color.isValid():
            color = QColor(default_stamp_border_color)
            stamp_border_color_value = color.name().upper()
        text_color = "#000000" if color.lightness() > 128 else "#FFFFFF"
        stamp_border_color_button.setText(stamp_border_color_value)
        stamp_border_color_button.setStyleSheet(
            f"background-color: {stamp_border_color_value}; color: {text_color};"
        )

    def pick_stamp_border_color() -> None:
        nonlocal stamp_border_color_value
        selected = QColorDialog.getColor(QColor(stamp_border_color_value), dialog)
        if not selected.isValid():
            return
        stamp_border_color_value = selected.name().upper()
        update_stamp_border_color_button()

    def reset_stamp_border_color() -> None:
        nonlocal stamp_border_color_value
        stamp_border_color_value = default_stamp_border_color
        update_stamp_border_color_button()

    stamp_color_button.clicked.connect(pick_stamp_color)
    stamp_color_reset_button.clicked.connect(reset_stamp_color)
    stamp_border_color_button.clicked.connect(pick_stamp_border_color)
    stamp_border_color_reset_button.clicked.connect(reset_stamp_border_color)
    update_stamp_color_button()
    update_stamp_border_color_button()

    location_stamp_scale_slider = QSlider(Qt.Orientation.Horizontal, dialog)
    location_stamp_scale_slider.setRange(
        stamp_scale_min_percent, stamp_scale_max_percent
    )
    location_stamp_scale_slider.setValue(window.location_stamp_scale_percent)
    location_stamp_scale_label = QLabel(
        f"{window.location_stamp_scale_percent}%", dialog
    )
    location_stamp_scale_spin = QSpinBox(dialog)
    location_stamp_scale_spin.setRange(stamp_scale_min_percent, stamp_scale_max_percent)
    location_stamp_scale_spin.setSuffix("%")
    location_stamp_scale_spin.setValue(window.location_stamp_scale_percent)
    location_stamp_scale_slider.valueChanged.connect(
        lambda value: location_stamp_scale_label.setText(f"{value}%")
    )
    location_stamp_scale_slider.valueChanged.connect(
        lambda value: (
            location_stamp_scale_spin.blockSignals(True),
            location_stamp_scale_spin.setValue(value),
            location_stamp_scale_spin.blockSignals(False),
        )
    )
    location_stamp_scale_spin.valueChanged.connect(location_stamp_scale_slider.setValue)
    location_stamp_scale_row = QWidget(dialog)
    location_stamp_scale_layout = QHBoxLayout(location_stamp_scale_row)
    location_stamp_scale_layout.setContentsMargins(0, 0, 0, 0)
    location_stamp_scale_layout.addWidget(location_stamp_scale_slider)
    location_stamp_scale_layout.addWidget(location_stamp_scale_label)
    location_stamp_scale_layout.addWidget(location_stamp_scale_spin)

    location_stamp_offset_x_slider = QSlider(Qt.Orientation.Horizontal, dialog)
    location_stamp_offset_x_slider.setRange(stamp_offset_min_px, stamp_offset_max_px)
    location_stamp_offset_x_slider.setValue(window.location_stamp_offset_x_px)
    location_stamp_offset_x_label = QLabel(
        f"{window.location_stamp_offset_x_px / 10:.1f}%", dialog
    )
    location_stamp_offset_x_spin = QDoubleSpinBox(dialog)
    location_stamp_offset_x_spin.setRange(
        stamp_offset_min_px / 10.0,
        stamp_offset_max_px / 10.0,
    )
    location_stamp_offset_x_spin.setSingleStep(0.1)
    location_stamp_offset_x_spin.setDecimals(1)
    location_stamp_offset_x_spin.setSuffix("%")
    location_stamp_offset_x_spin.setValue(window.location_stamp_offset_x_px / 10.0)
    location_stamp_offset_x_slider.valueChanged.connect(
        lambda value: location_stamp_offset_x_label.setText(f"{value / 10:.1f}%")
    )
    location_stamp_offset_x_slider.valueChanged.connect(
        lambda value: (
            location_stamp_offset_x_spin.blockSignals(True),
            location_stamp_offset_x_spin.setValue(value / 10.0),
            location_stamp_offset_x_spin.blockSignals(False),
        )
    )
    location_stamp_offset_x_spin.valueChanged.connect(
        lambda value: location_stamp_offset_x_slider.setValue(int(round(value * 10)))
    )
    location_stamp_offset_x_row = QWidget(dialog)
    location_stamp_offset_x_layout = QHBoxLayout(location_stamp_offset_x_row)
    location_stamp_offset_x_layout.setContentsMargins(0, 0, 0, 0)
    location_stamp_offset_x_layout.addWidget(location_stamp_offset_x_slider)
    location_stamp_offset_x_layout.addWidget(location_stamp_offset_x_label)
    location_stamp_offset_x_layout.addWidget(location_stamp_offset_x_spin)

    location_stamp_offset_y_slider = QSlider(Qt.Orientation.Horizontal, dialog)
    location_stamp_offset_y_slider.setRange(stamp_offset_min_px, stamp_offset_max_px)
    location_stamp_offset_y_slider.setValue(window.location_stamp_offset_y_px)
    location_stamp_offset_y_label = QLabel(
        f"{window.location_stamp_offset_y_px / 10:.1f}%", dialog
    )
    location_stamp_offset_y_spin = QDoubleSpinBox(dialog)
    location_stamp_offset_y_spin.setRange(
        stamp_offset_min_px / 10.0,
        stamp_offset_max_px / 10.0,
    )
    location_stamp_offset_y_spin.setSingleStep(0.1)
    location_stamp_offset_y_spin.setDecimals(1)
    location_stamp_offset_y_spin.setSuffix("%")
    location_stamp_offset_y_spin.setValue(window.location_stamp_offset_y_px / 10.0)
    location_stamp_offset_y_slider.valueChanged.connect(
        lambda value: location_stamp_offset_y_label.setText(f"{value / 10:.1f}%")
    )
    location_stamp_offset_y_slider.valueChanged.connect(
        lambda value: (
            location_stamp_offset_y_spin.blockSignals(True),
            location_stamp_offset_y_spin.setValue(value / 10.0),
            location_stamp_offset_y_spin.blockSignals(False),
        )
    )
    location_stamp_offset_y_spin.valueChanged.connect(
        lambda value: location_stamp_offset_y_slider.setValue(int(round(value * 10)))
    )
    location_stamp_offset_y_row = QWidget(dialog)
    location_stamp_offset_y_layout = QHBoxLayout(location_stamp_offset_y_row)
    location_stamp_offset_y_layout.setContentsMargins(0, 0, 0, 0)
    location_stamp_offset_y_layout.addWidget(location_stamp_offset_y_slider)
    location_stamp_offset_y_layout.addWidget(location_stamp_offset_y_label)
    location_stamp_offset_y_layout.addWidget(location_stamp_offset_y_spin)

    location_stamp_vertical_checkbox = QCheckBox("Vertical stamp", dialog)
    location_stamp_vertical_checkbox.setChecked(window.location_stamp_vertical_value)

    location_stamp_color_button = QPushButton(dialog)
    location_stamp_color_reset_button = QPushButton("Reset", dialog)
    location_stamp_color_value = window.location_stamp_color_value
    location_stamp_border_color_button = QPushButton(dialog)
    location_stamp_border_color_reset_button = QPushButton("Reset", dialog)
    location_stamp_border_color_value = window.location_stamp_border_color_value

    def update_location_stamp_color_button() -> None:
        nonlocal location_stamp_color_value
        color = QColor(location_stamp_color_value)
        if not color.isValid():
            color = QColor(default_stamp_color)
            location_stamp_color_value = color.name().upper()
        text_color = "#000000" if color.lightness() > 128 else "#FFFFFF"
        location_stamp_color_button.setText(location_stamp_color_value)
        location_stamp_color_button.setStyleSheet(
            f"background-color: {location_stamp_color_value}; color: {text_color};"
        )

    def pick_location_stamp_color() -> None:
        nonlocal location_stamp_color_value
        selected = QColorDialog.getColor(QColor(location_stamp_color_value), dialog)
        if not selected.isValid():
            return
        location_stamp_color_value = selected.name().upper()
        update_location_stamp_color_button()

    def reset_location_stamp_color() -> None:
        nonlocal location_stamp_color_value
        location_stamp_color_value = default_stamp_color
        update_location_stamp_color_button()

    def update_location_stamp_border_color_button() -> None:
        nonlocal location_stamp_border_color_value
        color = QColor(location_stamp_border_color_value)
        if not color.isValid():
            color = QColor(default_stamp_border_color)
            location_stamp_border_color_value = color.name().upper()
        text_color = "#000000" if color.lightness() > 128 else "#FFFFFF"
        location_stamp_border_color_button.setText(location_stamp_border_color_value)
        location_stamp_border_color_button.setStyleSheet(
            "background-color: "
            f"{location_stamp_border_color_value}; color: {text_color};"
        )

    def pick_location_stamp_border_color() -> None:
        nonlocal location_stamp_border_color_value
        selected = QColorDialog.getColor(
            QColor(location_stamp_border_color_value),
            dialog,
        )
        if not selected.isValid():
            return
        location_stamp_border_color_value = selected.name().upper()
        update_location_stamp_border_color_button()

    def reset_location_stamp_border_color() -> None:
        nonlocal location_stamp_border_color_value
        location_stamp_border_color_value = default_stamp_border_color
        update_location_stamp_border_color_button()

    location_stamp_color_button.clicked.connect(pick_location_stamp_color)
    location_stamp_color_reset_button.clicked.connect(reset_location_stamp_color)
    location_stamp_border_color_button.clicked.connect(pick_location_stamp_border_color)
    location_stamp_border_color_reset_button.clicked.connect(
        reset_location_stamp_border_color
    )
    update_location_stamp_color_button()
    update_location_stamp_border_color_button()

    def apply_dialog_preview_values() -> None:
        window.crop_ratio_value = str(crop_ratio_combo.currentData() or "2:3")
        window.stamp_mode_value = stamp_mode_combo.currentText()
        window.clock_mode_value = clock_mode_combo.currentText()
        window.corner_landscape_value = corner_landscape_combo.currentText()
        window.corner_portrait_value = corner_portrait_combo.currentText()
        window.location_stamp_mode_value = location_stamp_mode_combo.currentText()
        window.location_format_value = location_format_combo.currentText()
        window.location_format_template_value = (
            location_format_template_edit.text().strip()
            or location_format_template_default
        )
        window.location_corner_landscape_value = (
            location_corner_landscape_combo.currentText()
        )
        window.location_corner_portrait_value = (
            location_corner_portrait_combo.currentText()
        )
        window.location_stamp_scale_percent = location_stamp_scale_slider.value()
        window.location_stamp_offset_x_px = location_stamp_offset_x_slider.value()
        window.location_stamp_offset_y_px = location_stamp_offset_y_slider.value()
        window.location_stamp_vertical_value = (
            location_stamp_vertical_checkbox.isChecked()
        )
        window.location_stamp_color_value = location_stamp_color_value
        window.location_stamp_border_color_value = location_stamp_border_color_value
        window.stamp_font_value = stamp_font_combo.currentText()
        window.stamp_scale_percent = stamp_scale_slider.value()
        window.stamp_offset_x_px = stamp_offset_x_slider.value()
        window.stamp_offset_y_px = stamp_offset_y_slider.value()
        window.stamp_vertical_value = stamp_vertical_checkbox.isChecked()
        window.stamp_color_value = stamp_color_value
        window.stamp_border_color_value = stamp_border_color_value
        window.refresh_preview()
        update_settings_stamp_preview()
        update_dialog_gps_status()

    def update_settings_stamp_preview() -> None:
        if preview_source_image is None:
            return

        image = preview_source_image.copy()
        orientation = "Portrait" if image.height > image.width else "Landscape"
        selected_ratio = str(crop_ratio_combo.currentData() or "2:3")
        image = center_crop_to_ratio_fn(
            image,
            orientation,
            selected_ratio,
            zoom_percent=100,
            offset_x_percent=0,
            offset_y_percent=0,
        )

        max_w = 1000
        max_h = 700
        scale = min(max_w / image.width, max_h / image.height, 1.0)
        if scale < 1.0:
            image = image.resize(
                (int(image.width * scale), int(image.height * scale)),
                Image.Resampling.LANCZOS,
            )

        orientation = "Portrait" if image.height > image.width else "Landscape"
        corner = (
            corner_portrait_combo.currentText()
            if orientation == "Portrait"
            else corner_landscape_combo.currentText()
        )
        stamp_mode = stamp_mode_combo.currentText()
        clock_mode = clock_mode_combo.currentText()

        preview_datetime: datetime | None = None
        preview_location: tuple[float, float] | None = None
        if preview_source_path is not None:
            try:
                preview_datetime = datetime_for_image_fn(preview_source_path)
            except OSError:
                preview_datetime = None
            preview_location = window.location_for_path(preview_source_path)
        else:
            preview_location = placeholder_preview_location

        stamp_text_value = ""
        if stamp_mode != "None":
            stamp_dt = preview_datetime or datetime.now()
            if stamp_mode == "Date":
                stamp_text_value = stamp_dt.strftime("%Y-%m-%d")
            elif clock_mode == "12h":
                stamp_text_value = stamp_dt.strftime("%Y-%m-%d %I:%M %p")
            else:
                stamp_text_value = stamp_dt.strftime("%Y-%m-%d %H:%M")

        settings_preview = processing_settings_cls(
            orientation=orientation,
            stamp_mode=stamp_mode,
            clock_mode=clock_mode,
            corner=corner,
            stamp_font=stamp_font_combo.currentText(),
            stamp_scale_percent=stamp_scale_slider.value(),
            stamp_offset_x_px=stamp_offset_x_slider.value(),
            stamp_offset_y_px=stamp_offset_y_slider.value(),
            stamp_color=stamp_color_value,
            stamp_border_color=stamp_border_color_value,
            stamp_vertical=stamp_vertical_checkbox.isChecked(),
            datetime_override=preview_datetime,
        )
        image = apply_stamp_fn(image, stamp_text_value, settings_preview)

        location_text_value = ""
        if (
            location_stamp_mode_combo.currentText() != "Off"
            and preview_location is not None
        ):
            location_format = location_format_combo.currentText()
            if preview_source_path is None and location_format_needs_reverse_lookup_fn(
                location_format
            ):
                if location_format == "Custom Template":
                    location_text_value = render_location_template_fn(
                        location_format_template_edit.text().strip()
                        or location_format_template_default,
                        placeholder_geocode_payload,
                    )
                else:
                    location_text_value = window.format_nominatim_geocodejson(
                        placeholder_geocode_payload,
                        format_value=location_format,
                    )
            else:
                location_text_value = window.format_location(
                    preview_location,
                    path=preview_source_path,
                    format_value=location_format,
                )

        location_corner = (
            location_corner_portrait_combo.currentText()
            if orientation == "Portrait"
            else location_corner_landscape_combo.currentText()
        )
        image = apply_stamp_fn(
            image,
            location_text_value,
            settings_preview,
            corner=location_corner,
            scale_percent=location_stamp_scale_slider.value(),
            offset_x_px=location_stamp_offset_x_slider.value(),
            offset_y_px=location_stamp_offset_y_slider.value(),
            color_value=location_stamp_color_value,
            border_color_value=location_stamp_border_color_value,
            vertical=location_stamp_vertical_checkbox.isChecked(),
        )

        pixmap = QPixmap.fromImage(QImage(ImageQt(image)))
        scaled = pixmap.scaled(
            max(180, preview_label.width()),
            max(140, preview_label.height()),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        preview_label.setPixmap(scaled)

    def randomize_preview_source() -> None:
        nonlocal preview_source_path, preview_source_image
        if not window.image_paths:
            return

        candidates = [
            path for path in window.image_paths if path != preview_source_path
        ]
        if not candidates:
            candidates = list(window.image_paths)

        chosen = random.choice(candidates)
        try:
            preview_source_image = load_image_as_rgb_fn(
                chosen,
                debug_logger=lambda message: window.append_log("DEBUG", message),
            )
            preview_source_path = chosen
            preview_source_label.setText(f"Source: {chosen.name}")
        except OSError:
            preview_source_path = None
            preview_source_image = placeholder_preview_image()
            preview_source_label.setText("Source: placeholder (sample geocodejson)")

        update_settings_stamp_preview()

    preview_random_button.clicked.connect(randomize_preview_source)

    stamp_color_row = QWidget(dialog)
    stamp_color_layout = QHBoxLayout(stamp_color_row)
    stamp_color_layout.setContentsMargins(0, 0, 0, 0)
    stamp_color_layout.addWidget(stamp_color_button)
    stamp_color_layout.addWidget(stamp_color_reset_button)
    stamp_border_color_row = QWidget(dialog)
    stamp_border_color_layout = QHBoxLayout(stamp_border_color_row)
    stamp_border_color_layout.setContentsMargins(0, 0, 0, 0)
    stamp_border_color_layout.addWidget(stamp_border_color_button)
    stamp_border_color_layout.addWidget(stamp_border_color_reset_button)
    location_stamp_color_row = QWidget(dialog)
    location_stamp_color_layout = QHBoxLayout(location_stamp_color_row)
    location_stamp_color_layout.setContentsMargins(0, 0, 0, 0)
    location_stamp_color_layout.addWidget(location_stamp_color_button)
    location_stamp_color_layout.addWidget(location_stamp_color_reset_button)
    location_stamp_border_color_row = QWidget(dialog)
    location_stamp_border_color_layout = QHBoxLayout(location_stamp_border_color_row)
    location_stamp_border_color_layout.setContentsMargins(0, 0, 0, 0)
    location_stamp_border_color_layout.addWidget(location_stamp_border_color_button)
    location_stamp_border_color_layout.addWidget(
        location_stamp_border_color_reset_button
    )
    location_template_row = QWidget(dialog)
    location_template_layout = QHBoxLayout(location_template_row)
    location_template_layout.setContentsMargins(0, 0, 0, 0)
    location_template_layout.addWidget(location_format_template_edit, 1)
    location_template_layout.addWidget(location_template_editor_button)
    clear_image_settings_btn = QPushButton("Clear All Image Settings", dialog)

    crop_ratio_combo.currentIndexChanged.connect(
        lambda _value: apply_dialog_preview_values()
    )
    stamp_mode_combo.currentIndexChanged.connect(
        lambda _value: apply_dialog_preview_values()
    )
    clock_mode_combo.currentIndexChanged.connect(
        lambda _value: apply_dialog_preview_values()
    )
    corner_landscape_combo.currentIndexChanged.connect(
        lambda _value: apply_dialog_preview_values()
    )
    corner_portrait_combo.currentIndexChanged.connect(
        lambda _value: apply_dialog_preview_values()
    )
    location_stamp_mode_combo.currentIndexChanged.connect(
        lambda _value: apply_dialog_preview_values()
    )
    location_format_combo.currentIndexChanged.connect(
        lambda _value: apply_dialog_preview_values()
    )
    location_format_template_edit.textChanged.connect(
        lambda _value: apply_dialog_preview_values()
    )
    location_corner_landscape_combo.currentIndexChanged.connect(
        lambda _value: apply_dialog_preview_values()
    )
    location_corner_portrait_combo.currentIndexChanged.connect(
        lambda _value: apply_dialog_preview_values()
    )
    location_stamp_scale_slider.valueChanged.connect(
        lambda _value: apply_dialog_preview_values()
    )
    location_stamp_offset_x_slider.valueChanged.connect(
        lambda _value: apply_dialog_preview_values()
    )
    location_stamp_offset_y_slider.valueChanged.connect(
        lambda _value: apply_dialog_preview_values()
    )
    location_stamp_vertical_checkbox.toggled.connect(
        lambda _checked: apply_dialog_preview_values()
    )
    stamp_font_combo.currentIndexChanged.connect(
        lambda _value: apply_dialog_preview_values()
    )
    stamp_scale_slider.valueChanged.connect(
        lambda _value: apply_dialog_preview_values()
    )
    stamp_offset_x_slider.valueChanged.connect(
        lambda _value: apply_dialog_preview_values()
    )
    stamp_offset_y_slider.valueChanged.connect(
        lambda _value: apply_dialog_preview_values()
    )
    stamp_vertical_checkbox.toggled.connect(
        lambda _checked: apply_dialog_preview_values()
    )

    original_pick_stamp_color = pick_stamp_color

    def pick_stamp_color_with_preview() -> None:
        original_pick_stamp_color()
        apply_dialog_preview_values()

    stamp_color_button.clicked.disconnect()
    stamp_color_button.clicked.connect(pick_stamp_color_with_preview)

    original_reset_stamp_color = reset_stamp_color

    def reset_stamp_color_with_preview() -> None:
        original_reset_stamp_color()
        apply_dialog_preview_values()

    stamp_color_reset_button.clicked.disconnect()
    stamp_color_reset_button.clicked.connect(reset_stamp_color_with_preview)

    original_pick_stamp_border_color = pick_stamp_border_color

    def pick_stamp_border_color_with_preview() -> None:
        original_pick_stamp_border_color()
        apply_dialog_preview_values()

    stamp_border_color_button.clicked.disconnect()
    stamp_border_color_button.clicked.connect(pick_stamp_border_color_with_preview)

    original_reset_stamp_border_color = reset_stamp_border_color

    def reset_stamp_border_color_with_preview() -> None:
        original_reset_stamp_border_color()
        apply_dialog_preview_values()

    stamp_border_color_reset_button.clicked.disconnect()
    stamp_border_color_reset_button.clicked.connect(
        reset_stamp_border_color_with_preview
    )

    original_pick_location_stamp_color = pick_location_stamp_color

    def pick_location_stamp_color_with_preview() -> None:
        original_pick_location_stamp_color()
        apply_dialog_preview_values()

    location_stamp_color_button.clicked.disconnect()
    location_stamp_color_button.clicked.connect(pick_location_stamp_color_with_preview)

    original_reset_location_stamp_color = reset_location_stamp_color

    def reset_location_stamp_color_with_preview() -> None:
        original_reset_location_stamp_color()
        apply_dialog_preview_values()

    location_stamp_color_reset_button.clicked.disconnect()
    location_stamp_color_reset_button.clicked.connect(
        reset_location_stamp_color_with_preview
    )

    original_pick_location_stamp_border_color = pick_location_stamp_border_color

    def pick_location_stamp_border_color_with_preview() -> None:
        original_pick_location_stamp_border_color()
        apply_dialog_preview_values()

    location_stamp_border_color_button.clicked.disconnect()
    location_stamp_border_color_button.clicked.connect(
        pick_location_stamp_border_color_with_preview
    )

    original_reset_location_stamp_border_color = reset_location_stamp_border_color

    def reset_location_stamp_border_color_with_preview() -> None:
        original_reset_location_stamp_border_color()
        apply_dialog_preview_values()

    location_stamp_border_color_reset_button.clicked.disconnect()
    location_stamp_border_color_reset_button.clicked.connect(
        reset_location_stamp_border_color_with_preview
    )

    def clear_all_image_settings() -> None:
        if window.current_folder is None:
            QMessageBox.information(
                window,
                "No folder loaded",
                "Load a folder first before clearing image settings.",
            )
            return

        reply = QMessageBox.question(
            window,
            "Clear image settings",
            "Clear all per-image settings for this folder?\n"
            "This removes crop/brightness/date/location-stamp overrides for all photos.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        window.folder_metadata["image_settings"] = {}
        window.save_folder_metadata()
        window.refresh_image_list_labels(window.selected_path())
        window.restore_image_settings_for_selected()
        window.refresh_preview()
        QMessageBox.information(
            window,
            "Image settings cleared",
            "All per-image settings in this folder were reset.",
        )

    clear_image_settings_btn.clicked.connect(clear_all_image_settings)

    form.addRow(section_label("Crop & Layout"), QLabel("", dialog))
    form.addRow("Crop Ratio", crop_ratio_combo)
    form.addRow(section_label("Stamp Controls"), QLabel("", dialog))
    form.addRow(section_label("Timestamp Stamp"), QLabel("", dialog))
    form.addRow("Date / Time", stamp_mode_combo)
    form.addRow("Time Format", clock_mode_combo)
    form.addRow("Corner (Landscape)", corner_landscape_combo)
    form.addRow("Corner (Portrait)", corner_portrait_combo)
    form.addRow("Timestamp Font", stamp_font_combo)
    form.addRow("Timestamp Size", stamp_scale_row)
    form.addRow("Timestamp Offset X", stamp_offset_x_row)
    form.addRow("Timestamp Offset Y", stamp_offset_y_row)
    form.addRow("Text Direction", stamp_vertical_checkbox)
    form.addRow("Timestamp Color", stamp_color_row)
    form.addRow("Timestamp Border", stamp_border_color_row)
    form.addRow(section_label("Location Stamp"), QLabel("", dialog))
    form.addRow("Mode", location_stamp_mode_combo)
    form.addRow("Format", location_format_combo)
    form.addRow("GPS Status", gps_pending_label)
    form.addRow("Custom Template", location_template_row)
    form.addRow("Corner (Landscape)", location_corner_landscape_combo)
    form.addRow("Corner (Portrait)", location_corner_portrait_combo)
    form.addRow("Location Size", location_stamp_scale_row)
    form.addRow("Location Offset X", location_stamp_offset_x_row)
    form.addRow("Location Offset Y", location_stamp_offset_y_row)
    form.addRow("Location Text Direction", location_stamp_vertical_checkbox)
    form.addRow("Location Color", location_stamp_color_row)
    form.addRow("Location Border", location_stamp_border_color_row)
    form.addRow(section_label("Folder Actions"), QLabel("", dialog))
    form.addRow("", clear_image_settings_btn)
    update_dialog_gps_status()
    update_settings_stamp_preview()

    buttons = QDialogButtonBox(
        QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
        parent=dialog,
    )
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    layout.addWidget(buttons)

    if dialog.exec() != QDialog.DialogCode.Accepted:
        window.crop_ratio_value = str(original_values["crop_ratio_value"])
        window.stamp_mode_value = str(original_values["stamp_mode_value"])
        window.clock_mode_value = str(original_values["clock_mode_value"])
        window.corner_landscape_value = str(original_values["corner_landscape_value"])
        window.corner_portrait_value = str(original_values["corner_portrait_value"])
        window.location_stamp_mode_value = str(
            original_values["location_stamp_mode_value"]
        )
        window.location_format_value = str(original_values["location_format_value"])
        window.location_format_template_value = str(
            original_values["location_format_template_value"]
        )
        window.location_corner_landscape_value = str(
            original_values["location_corner_landscape_value"]
        )
        window.location_corner_portrait_value = str(
            original_values["location_corner_portrait_value"]
        )
        window.location_stamp_scale_percent = int(
            original_values["location_stamp_scale_percent"]
        )
        window.location_stamp_offset_x_px = int(
            original_values["location_stamp_offset_x_px"]
        )
        window.location_stamp_offset_y_px = int(
            original_values["location_stamp_offset_y_px"]
        )
        window.location_stamp_vertical_value = bool(
            original_values["location_stamp_vertical_value"]
        )
        window.location_stamp_color_value = str(
            original_values["location_stamp_color_value"]
        )
        window.location_stamp_border_color_value = str(
            original_values["location_stamp_border_color_value"]
        )
        window.stamp_font_value = str(original_values["stamp_font_value"])
        window.stamp_scale_percent = int(original_values["stamp_scale_percent"])
        window.stamp_offset_x_px = int(original_values["stamp_offset_x_px"])
        window.stamp_offset_y_px = int(original_values["stamp_offset_y_px"])
        window.stamp_vertical_value = bool(original_values["stamp_vertical_value"])
        window.stamp_color_value = str(original_values["stamp_color_value"])
        window.stamp_border_color_value = str(
            original_values["stamp_border_color_value"]
        )
        window.refresh_preview()
        return

    window.crop_ratio_value = str(crop_ratio_combo.currentData() or "2:3")
    window.stamp_mode_value = stamp_mode_combo.currentText()
    window.clock_mode_value = clock_mode_combo.currentText()
    window.corner_landscape_value = corner_landscape_combo.currentText()
    window.corner_portrait_value = corner_portrait_combo.currentText()
    window.location_stamp_mode_value = location_stamp_mode_combo.currentText()
    window.location_format_value = location_format_combo.currentText()
    window.location_format_template_value = (
        location_format_template_edit.text().strip() or location_format_template_default
    )
    window.location_corner_landscape_value = (
        location_corner_landscape_combo.currentText()
    )
    window.location_corner_portrait_value = location_corner_portrait_combo.currentText()
    window.location_stamp_scale_percent = location_stamp_scale_slider.value()
    window.location_stamp_offset_x_px = location_stamp_offset_x_slider.value()
    window.location_stamp_offset_y_px = location_stamp_offset_y_slider.value()
    window.location_stamp_vertical_value = location_stamp_vertical_checkbox.isChecked()
    window.location_stamp_color_value = location_stamp_color_value
    window.location_stamp_border_color_value = location_stamp_border_color_value
    window.stamp_font_value = stamp_font_combo.currentText()
    window.stamp_scale_percent = stamp_scale_slider.value()
    window.stamp_offset_x_px = stamp_offset_x_slider.value()
    window.stamp_offset_y_px = stamp_offset_y_slider.value()
    window.stamp_vertical_value = stamp_vertical_checkbox.isChecked()
    window.stamp_color_value = stamp_color_value
    window.stamp_border_color_value = stamp_border_color_value

    preferred = window.selected_path()
    window.apply_sort_order(preferred)
    window.persist_project_settings()
    window.refresh_preview()
