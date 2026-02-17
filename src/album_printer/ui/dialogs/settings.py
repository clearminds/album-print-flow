from __future__ import annotations

import base64
import json
from typing import Any
from urllib import parse as urllib_parse
from urllib import request as urllib_request

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


def open_settings_dialog(
    window: Any,
    *,
    nominatim_default_reverse_url: str,
    nominatim_auth_modes: list[str],
    nominatim_zoom_level_options: list[tuple[int, str]],
    app_version_fn: Any,
) -> None:
    dialog = QDialog(window)
    dialog.setWindowTitle("Settings")
    dialog.setModal(True)
    dialog.resize(860, 680)

    layout = QVBoxLayout(dialog)

    def section_label(text: str) -> QLabel:
        label = QLabel(text, dialog)
        label.setStyleSheet("font-weight: 600;")
        return label

    layout.addWidget(section_label("Accounts / Entries"))

    account_providers: list[tuple[str, object]] = []
    provider_labels: dict[str, str] = {}
    provider_map: dict[str, object] = {}
    provider_combo = QComboBox(dialog)
    for adapter in window.source_registry.all():
        list_fn = getattr(adapter, "list_accounts", None)
        add_fn = getattr(adapter, "add_account_interactive", None)
        delete_fn = getattr(adapter, "delete_account", None)
        refresh_fn = getattr(adapter, "refresh_account_oauth", None)
        if not callable(list_fn):
            continue
        if not callable(add_fn) or not callable(delete_fn) or not callable(refresh_fn):
            continue
        source_id = str(getattr(adapter, "source_id", "")).strip()
        source_label = str(getattr(adapter, "label", source_id)).strip() or source_id
        if not source_id:
            continue
        account_providers.append((source_id, adapter))
        provider_labels[source_id] = source_label
        provider_map[source_id] = adapter

    provider_row = QWidget(dialog)
    provider_layout = QHBoxLayout(provider_row)
    provider_layout.setContentsMargins(0, 0, 0, 0)
    provider_layout.addWidget(QLabel("Source", dialog))
    provider_layout.addWidget(provider_combo, 1)
    layout.addWidget(provider_row)

    account_list = QListWidget(dialog)
    account_list.setMinimumHeight(180)
    layout.addWidget(account_list)

    account_button_row = QHBoxLayout()
    add_account_btn = QPushButton("Add", dialog)
    refresh_oauth_btn = QPushButton("Refresh", dialog)
    delete_account_btn = QPushButton("Delete", dialog)
    account_button_row.addWidget(add_account_btn)
    account_button_row.addWidget(refresh_oauth_btn)
    account_button_row.addWidget(delete_account_btn)
    account_button_row.addStretch(1)
    layout.addLayout(account_button_row)

    google_cache_row = QHBoxLayout()
    keep_google_metadata_checkbox = QCheckBox("Keep metadata", dialog)
    keep_google_metadata_checkbox.setChecked(True)
    clear_google_cache_btn = QPushButton("Clear Google Media Cache", dialog)
    google_cache_row.addWidget(clear_google_cache_btn)
    google_cache_row.addWidget(keep_google_metadata_checkbox)
    google_cache_row.addStretch(1)
    layout.addLayout(google_cache_row)

    layout.addWidget(section_label("Nominatim"))
    nominatim_info = QLabel(
        "Public Nominatim policy: maximum 1 request/second, identifiable User-Agent, and local caching. Used for non-coordinate location formats.",
        dialog,
    )
    nominatim_info.setWordWrap(True)
    layout.addWidget(nominatim_info)

    nominatim_form = QFormLayout()
    nominatim_enabled_checkbox = QCheckBox(
        "Enable reverse geocoding for location text", dialog
    )
    nominatim_enabled_checkbox.setChecked(window.nominatim_enabled_value)

    nominatim_url_edit = QLineEdit(dialog)
    nominatim_url_edit.setText(window.nominatim_reverse_url_value)
    nominatim_url_edit.setPlaceholderText(nominatim_default_reverse_url)

    nominatim_auth_mode_combo = QComboBox(dialog)
    nominatim_auth_mode_combo.addItems(nominatim_auth_modes)
    nominatim_auth_mode_combo.setCurrentText(window.nominatim_auth_mode_value)

    nominatim_auth_token_edit = QLineEdit(dialog)
    nominatim_auth_token_edit.setText(window.nominatim_auth_token_value)
    nominatim_auth_token_edit.setPlaceholderText("Bearer token")
    nominatim_auth_token_edit.setEchoMode(QLineEdit.EchoMode.Password)

    nominatim_auth_username_edit = QLineEdit(dialog)
    nominatim_auth_username_edit.setText(window.nominatim_auth_username_value)
    nominatim_auth_username_edit.setPlaceholderText("Basic auth username")

    nominatim_auth_password_edit = QLineEdit(dialog)
    nominatim_auth_password_edit.setText(window.nominatim_auth_password_value)
    nominatim_auth_password_edit.setPlaceholderText("Basic auth password")
    nominatim_auth_password_edit.setEchoMode(QLineEdit.EchoMode.Password)

    nominatim_accept_language_edit = QLineEdit(dialog)
    nominatim_accept_language_edit.setText(window.nominatim_accept_language_value)
    nominatim_accept_language_edit.setPlaceholderText("e.g. en,sv-SE,sv")

    nominatim_zoom_combo = QComboBox(dialog)
    for zoom_value, zoom_label in nominatim_zoom_level_options:
        nominatim_zoom_combo.addItem(zoom_label, zoom_value)
    current_zoom = max(0, min(18, int(window.nominatim_zoom_value)))
    current_zoom_index = nominatim_zoom_combo.findData(current_zoom)
    if current_zoom_index < 0:
        current_zoom_index = nominatim_zoom_combo.findData(18)
    if current_zoom_index >= 0:
        nominatim_zoom_combo.setCurrentIndex(current_zoom_index)

    nominatim_email_edit = QLineEdit(dialog)
    nominatim_email_edit.setText(window.nominatim_email_value)
    nominatim_email_edit.setPlaceholderText("optional@example.com")

    nominatim_rate_spin = QDoubleSpinBox(dialog)
    nominatim_rate_spin.setRange(1.0, 30.0)
    nominatim_rate_spin.setSingleStep(0.1)
    nominatim_rate_spin.setDecimals(1)
    nominatim_rate_spin.setValue(window.nominatim_rate_limit_seconds_value)
    nominatim_rate_spin.setSuffix(" s")

    nominatim_form.addRow("", nominatim_enabled_checkbox)
    nominatim_form.addRow("Reverse URL", nominatim_url_edit)
    nominatim_form.addRow("Auth Mode", nominatim_auth_mode_combo)
    nominatim_form.addRow("Bearer Token", nominatim_auth_token_edit)
    nominatim_form.addRow("Basic Username", nominatim_auth_username_edit)
    nominatim_form.addRow("Basic Password", nominatim_auth_password_edit)
    nominatim_form.addRow("Accept-Language", nominatim_accept_language_edit)
    nominatim_form.addRow("Zoom Level", nominatim_zoom_combo)
    nominatim_form.addRow("Email (optional)", nominatim_email_edit)
    nominatim_form.addRow("Min Request Delay", nominatim_rate_spin)

    nominatim_test_button = QPushButton("Nominatim Test", dialog)
    nominatim_form.addRow("", nominatim_test_button)
    layout.addLayout(nominatim_form)

    def update_auth_visibility() -> None:
        mode = nominatim_auth_mode_combo.currentText().strip()
        nominatim_auth_token_edit.setEnabled(mode == "Bearer Token")
        nominatim_auth_username_edit.setEnabled(mode == "Basic Auth")
        nominatim_auth_password_edit.setEnabled(mode == "Basic Auth")

    nominatim_auth_mode_combo.currentTextChanged.connect(
        lambda _value: update_auth_visibility()
    )
    update_auth_visibility()

    def test_nominatim_request() -> None:
        def selected_nominatim_zoom() -> int:
            selected = nominatim_zoom_combo.currentData()
            try:
                return max(0, min(18, int(selected)))
            except (TypeError, ValueError):
                return 18

        reverse_url = nominatim_url_edit.text().strip()
        if not reverse_url:
            QMessageBox.warning(
                dialog,
                "Settings",
                "Reverse URL is required for Nominatim test.",
            )
            return

        test_location = None
        selected = window.selected_path()
        if selected is not None:
            test_location = window.location_for_path(selected)
        if test_location is None:
            test_location = (59.3293, 18.0686)

        latitude, longitude = test_location
        params: dict[str, str] = {
            "format": "geocodejson",
            "addressdetails": "1",
            "lat": f"{latitude:.8f}",
            "lon": f"{longitude:.8f}",
            "zoom": str(selected_nominatim_zoom()),
        }

        accept_language = nominatim_accept_language_edit.text().strip()
        if accept_language:
            params["accept-language"] = accept_language

        email_value = nominatim_email_edit.text().strip()
        if email_value:
            params["email"] = email_value

        separator = "&" if "?" in reverse_url else "?"
        url = f"{reverse_url}{separator}{urllib_parse.urlencode(params)}"
        request = urllib_request.Request(url)

        user_agent = f"AlbumPrintFlow/{app_version_fn()} (Album Print Flow)"
        if email_value:
            user_agent = f"{user_agent} contact={email_value}"
        request.add_header("User-Agent", user_agent)
        if accept_language:
            request.add_header("Accept-Language", accept_language)

        auth_mode = nominatim_auth_mode_combo.currentText().strip()
        token_value = nominatim_auth_token_edit.text().strip()
        username_value = nominatim_auth_username_edit.text().strip()
        password_value = nominatim_auth_password_edit.text()
        if auth_mode == "Bearer Token" and token_value:
            request.add_header("Authorization", f"Bearer {token_value}")
        elif auth_mode == "Basic Auth" and username_value:
            token = f"{username_value}:{password_value}".encode()
            request.add_header(
                "Authorization",
                "Basic " + base64.b64encode(token).decode("ascii"),
            )

        try:
            with urllib_request.urlopen(request, timeout=12) as response:
                payload_text = response.read().decode("utf-8", errors="replace")
            payload = json.loads(payload_text)
        except Exception as error:
            window.append_log("WARNING", f"NOMINATIM test failed: {error}")
            QMessageBox.critical(
                dialog,
                "Nominatim Test",
                f"Request failed: {error}",
            )
            return

        if not isinstance(payload, dict):
            QMessageBox.warning(
                dialog,
                "Nominatim Test",
                "Unexpected response payload.",
            )
            return

        display_name = window.format_nominatim_geocodejson(
            payload,
            format_value="Address Label",
        )

        if display_name:
            window.append_log(
                "INFO",
                f"NOMINATIM test ok: lat={latitude:.6f} lon={longitude:.6f}",
            )
            QMessageBox.information(
                dialog,
                "Nominatim Test",
                "Request succeeded.\n\n"
                f"Location: {latitude:.6f}, {longitude:.6f}\n"
                f"Result: {display_name}",
            )
            return

        QMessageBox.warning(
            dialog,
            "Nominatim Test",
            "Request succeeded but no address label was returned.",
        )

    nominatim_test_button.clicked.connect(test_nominatim_request)

    def provider_rows(source_id: str, adapter: object) -> list[dict[str, object]]:
        list_fn = getattr(adapter, "list_accounts", None)
        if not callable(list_fn):
            return []
        try:
            rows = list_fn()
        except Exception as error:
            window.append_log(
                "WARNING", f"Account list failed for {source_id}: {error}"
            )
            return []
        if not isinstance(rows, list):
            return []
        return [row for row in rows if isinstance(row, dict)]

    def repopulate_provider_combo() -> None:
        selected_source_id = str(provider_combo.currentData() or "").strip()
        provider_combo.blockSignals(True)
        provider_combo.clear()
        for source_id, adapter in account_providers:
            base_label = provider_labels.get(source_id, source_id)
            rows = provider_rows(source_id, adapter)
            entry_count = len(rows)
            provider_combo.addItem(f"{base_label} ({entry_count})", source_id)

        if provider_combo.count() > 0:
            selected_index = 0
            if selected_source_id:
                for index in range(provider_combo.count()):
                    if (
                        str(provider_combo.itemData(index) or "").strip()
                        == selected_source_id
                    ):
                        selected_index = index
                        break
            provider_combo.setCurrentIndex(selected_index)
        provider_combo.blockSignals(False)

    def repopulate_accounts() -> None:
        account_list.clear()
        selected_source_id = str(provider_combo.currentData() or "").strip()
        if not selected_source_id and account_providers:
            selected_source_id = account_providers[0][0]

        adapter = provider_map.get(selected_source_id)
        if adapter is not None and selected_source_id:
            rows = provider_rows(selected_source_id, adapter)
            for row in rows:
                account_id = str(row.get("account_id", "")).strip()
                if not account_id:
                    continue
                source_label = (
                    str(row.get("source_label", selected_source_id)).strip()
                    or selected_source_id
                )
                account_label = str(row.get("label", account_id)).strip() or account_id
                item = QListWidgetItem(f"{source_label}: {account_label}")
                item.setData(
                    int(Qt.ItemDataRole.UserRole), (selected_source_id, account_id)
                )
                account_list.addItem(item)

        has_selection = account_list.count() > 0
        delete_account_btn.setEnabled(has_selection)
        refresh_oauth_btn.setEnabled(has_selection)
        if has_selection and account_list.currentRow() < 0:
            account_list.setCurrentRow(0)

    def add_account() -> None:
        source_id = str(provider_combo.currentData() or "").strip()
        adapter = provider_map.get(source_id)
        if adapter is None:
            return
        add_fn = getattr(adapter, "add_account_interactive", None)
        if not callable(add_fn):
            return
        if bool(add_fn(window)):
            repopulate_provider_combo()
            repopulate_accounts()

    def selected_account() -> tuple[str, str] | None:
        item = account_list.currentItem()
        if item is None:
            return None
        raw = item.data(int(Qt.ItemDataRole.UserRole))
        if not isinstance(raw, tuple) or len(raw) != 2:
            return None
        source_id = str(raw[0] or "").strip()
        account_id = str(raw[1] or "").strip()
        if not source_id or not account_id:
            return None
        return source_id, account_id

    def delete_account() -> None:
        selected = selected_account()
        if selected is None:
            return
        source_id, account_id = selected
        adapter = provider_map.get(source_id)
        if adapter is None:
            return
        reply = QMessageBox.question(
            dialog,
            "Settings",
            "Delete this selected entry?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        delete_fn = getattr(adapter, "delete_account", None)
        if callable(delete_fn) and bool(delete_fn(account_id)):
            repopulate_provider_combo()
            repopulate_accounts()

    def refresh_oauth() -> None:
        selected = selected_account()
        if selected is None:
            return
        source_id, account_id = selected
        adapter = provider_map.get(source_id)
        if adapter is None:
            return
        refresh_fn = getattr(adapter, "refresh_account_oauth", None)
        if callable(refresh_fn) and bool(refresh_fn(window, account_id)):
            repopulate_provider_combo()
            repopulate_accounts()
            QMessageBox.information(
                dialog,
                "Settings",
                "Entry refreshed successfully.",
            )

    provider_combo.currentIndexChanged.connect(lambda _index: repopulate_accounts())
    repopulate_provider_combo()

    def clear_google_media_cache() -> None:
        google_adapter = provider_map.get("google-photos")
        if google_adapter is None:
            QMessageBox.information(
                dialog,
                "Settings",
                "Google Photos provider is not available.",
            )
            return

        clear_fn = getattr(google_adapter, "clear_media_cache", None)
        if not callable(clear_fn):
            QMessageBox.information(
                dialog,
                "Settings",
                "Google media cache clear is not supported by this provider.",
            )
            return

        keep_metadata = keep_google_metadata_checkbox.isChecked()
        keep_text = "keep metadata files" if keep_metadata else "remove metadata too"
        confirm = QMessageBox.question(
            dialog,
            "Clear Google Media Cache",
            f"Clear downloaded Google image cache now?\nMode: {keep_text}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        try:
            result = clear_fn(keep_metadata=keep_metadata)
        except Exception as error:
            QMessageBox.critical(
                dialog,
                "Clear Google Media Cache",
                f"Failed to clear cache: {error}",
            )
            return

        if not isinstance(result, dict):
            result = {}

        deleted_files = int(result.get("deleted_files", 0))
        kept_metadata = int(result.get("kept_metadata", 0))
        accounts = int(result.get("accounts", 0))
        errors = int(result.get("errors", 0))

        window.append_log(
            "INFO",
            "Cleared Google media cache "
            f"(accounts={accounts}, deleted={deleted_files}, "
            f"kept_metadata={kept_metadata}, errors={errors})",
        )

        message = (
            f"Accounts touched: {accounts}\n"
            f"Deleted files: {deleted_files}\n"
            f"Kept metadata: {kept_metadata}\n"
            f"Errors: {errors}"
        )
        if errors > 0:
            QMessageBox.warning(dialog, "Clear Google Media Cache", message)
        else:
            QMessageBox.information(dialog, "Clear Google Media Cache", message)

    add_account_btn.clicked.connect(add_account)
    delete_account_btn.clicked.connect(delete_account)
    refresh_oauth_btn.clicked.connect(refresh_oauth)
    clear_google_cache_btn.clicked.connect(clear_google_media_cache)
    repopulate_accounts()

    buttons = QDialogButtonBox(
        QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
        parent=dialog,
    )
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    layout.addWidget(buttons)

    if dialog.exec() != QDialog.DialogCode.Accepted:
        return

    window.nominatim_enabled_value = nominatim_enabled_checkbox.isChecked()
    window.nominatim_reverse_url_value = nominatim_url_edit.text().strip()
    window.nominatim_auth_mode_value = nominatim_auth_mode_combo.currentText().strip()
    window.nominatim_auth_token_value = nominatim_auth_token_edit.text().strip()
    window.nominatim_auth_username_value = nominatim_auth_username_edit.text().strip()
    window.nominatim_auth_password_value = nominatim_auth_password_edit.text()
    window.nominatim_accept_language_value = (
        nominatim_accept_language_edit.text().strip()
    )
    selected_zoom = nominatim_zoom_combo.currentData()
    try:
        window.nominatim_zoom_value = max(0, min(18, int(selected_zoom)))
    except (TypeError, ValueError):
        window.nominatim_zoom_value = 18
    window.nominatim_email_value = nominatim_email_edit.text().strip()
    window.nominatim_rate_limit_seconds_value = max(
        1.0, float(nominatim_rate_spin.value())
    )
    window.save_nominatim_settings()
    window.save_app_project_settings()
    window.refresh_preview()
