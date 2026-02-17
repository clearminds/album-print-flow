from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)


def open_metadata_manager_dialog(window: Any) -> None:
    dialog = QDialog(window)
    dialog.setWindowTitle("Metadata Manager")
    dialog.setModal(True)
    dialog.resize(820, 640)

    layout = QVBoxLayout(dialog)
    intro = QLabel(
        "Inspect metadata usage and clear or rebuild metadata for current/source/global scope."
    )
    intro.setWordWrap(True)
    layout.addWidget(intro)
    warning_label = QLabel(
        "⚠ Some actions are destructive and cannot be undone. "
        "Clearing metadata removes per-image overrides, print state history, and lookup cache entries for affected scopes."
    )
    warning_label.setWordWrap(True)
    layout.addWidget(warning_label)

    stats_form = QFormLayout()
    active_source_value = QLabel("")
    active_context_value = QLabel("")
    current_metadata_value = QLabel("")
    source_metadata_value = QLabel("")
    global_metadata_value = QLabel("")
    index_value = QLabel("")
    current_metadata_path_value = QLabel("")
    source_metadata_path_value = QLabel("")
    global_metadata_path_value = QLabel("")
    index_path_value = QLabel("")

    for label_widget in (
        current_metadata_path_value,
        source_metadata_path_value,
        global_metadata_path_value,
        index_path_value,
    ):
        label_widget.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        label_widget.setWordWrap(True)

    stats_form.addRow("Active source", active_source_value)
    stats_form.addRow("Active context", active_context_value)
    stats_form.addRow("Current metadata", current_metadata_value)
    stats_form.addRow("Source metadata", source_metadata_value)
    stats_form.addRow("Global metadata", global_metadata_value)
    stats_form.addRow("Index", index_value)
    stats_form.addRow("Current path", current_metadata_path_value)
    stats_form.addRow("Source dir", source_metadata_path_value)
    stats_form.addRow("Global dir", global_metadata_path_value)
    stats_form.addRow("Index path", index_path_value)
    layout.addLayout(stats_form)

    details_label = QLabel("Indexed contexts", dialog)
    details_label.setStyleSheet("font-weight: 600;")
    layout.addWidget(details_label)

    details_text = QTextEdit(dialog)
    details_text.setReadOnly(True)
    details_text.setMinimumHeight(200)
    layout.addWidget(details_text)

    actions_layout = QVBoxLayout()

    metadata_row = QHBoxLayout()
    clear_current_metadata_button = QPushButton("Clear Current Metadata")
    clear_source_metadata_button = QPushButton("Clear Current Source Metadata")
    clear_all_metadata_button = QPushButton("Clear All Metadata")
    rebuild_current_metadata_button = QPushButton("Rebuild Current Metadata File")
    clear_current_metadata_button.setToolTip(
        "Removes metadata only for the current source context."
    )
    clear_source_metadata_button.setToolTip(
        "Removes all metadata entries for the active source type."
    )
    clear_all_metadata_button.setToolTip(
        "Removes metadata for all source contexts. This is global."
    )
    rebuild_current_metadata_button.setToolTip(
        "Writes current in-memory metadata back to the active metadata file."
    )
    metadata_row.addWidget(clear_current_metadata_button)
    metadata_row.addWidget(clear_source_metadata_button)
    metadata_row.addWidget(clear_all_metadata_button)
    metadata_row.addWidget(rebuild_current_metadata_button)
    actions_layout.addLayout(metadata_row)

    layout.addLayout(actions_layout)

    buttons = QDialogButtonBox(dialog)
    refresh_button = buttons.addButton(
        "Refresh", QDialogButtonBox.ButtonRole.ActionRole
    )
    close_button = buttons.addButton(QDialogButtonBox.StandardButton.Close)
    close_button.clicked.connect(dialog.reject)
    layout.addWidget(buttons)

    def load_index_entries(index_path: Path) -> list[dict[str, object]]:
        if not index_path.exists():
            return []
        try:
            with index_path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except (OSError, json.JSONDecodeError):
            return []

        raw_entries = payload.get("entries") if isinstance(payload, dict) else None
        if not isinstance(raw_entries, dict):
            return []
        entries: list[dict[str, object]] = []
        for key, value in raw_entries.items():
            if isinstance(value, dict):
                entries.append({"digest": str(key), **value})
        entries.sort(
            key=lambda item: str(item.get("updated_at", "")),
            reverse=True,
        )
        return entries

    def update_stats() -> None:
        active_source = window.metadata_source_id()
        active_context = window.metadata_context_key() or "(no active context)"
        active_source_value.setText(active_source)
        active_context_value.setText(active_context)

        metadata_path = window.metadata_path()
        if metadata_path is not None and metadata_path.exists():
            count, size = window.path_storage_stats(metadata_path)
            current_metadata_value.setText(
                f"{count} file • {window.format_storage_size(size)}"
            )
        else:
            current_metadata_value.setText("0 files • 0 B")
        current_metadata_path_value.setText(
            str(metadata_path) if metadata_path is not None else "(none)"
        )

        source_dir = window.metadata_source_dir()
        source_count, source_size = window.path_storage_stats(source_dir)
        source_metadata_value.setText(
            f"{source_count} files • {window.format_storage_size(source_size)}"
        )
        source_metadata_path_value.setText(str(source_dir))

        all_metadata_count, all_metadata_size = window.path_storage_stats(
            window.metadata_root_path()
        )
        global_metadata_value.setText(
            f"{all_metadata_count} files • {window.format_storage_size(all_metadata_size)}"
        )
        global_metadata_path_value.setText(str(window.metadata_root_path()))

        index_path = window.metadata_index_path()
        index_entries = load_index_entries(index_path)
        index_count, index_size = window.path_storage_stats(index_path)
        index_value.setText(
            f"{len(index_entries)} entries • {index_count} file • {window.format_storage_size(index_size)}"
        )
        index_path_value.setText(str(index_path))

        details_lines: list[str] = []
        if not index_entries:
            details_lines.append("No indexed metadata contexts for current source.")
        else:
            for entry in index_entries[:120]:
                display_context = (
                    str(entry.get("display_context") or "").strip()
                    or "(unknown context)"
                )
                updated_at = str(entry.get("updated_at") or "")
                metadata_file = str(entry.get("metadata_file") or "")
                details_lines.append(
                    f"• {display_context}\n"
                    f"  file={metadata_file or '(none)'}"
                    + (f" | updated={updated_at}" if updated_at else "")
                )
            if len(index_entries) > 120:
                details_lines.append(f"…and {len(index_entries) - 120} more")
        details_text.setPlainText("\n".join(details_lines))

        clear_current_metadata_button.setEnabled(
            metadata_path is not None and metadata_path.exists()
        )
        clear_source_metadata_button.setEnabled(source_dir.exists())
        clear_all_metadata_button.setEnabled(window.metadata_root_path().exists())
        rebuild_current_metadata_button.setEnabled(
            metadata_path is not None and window.current_folder is not None
        )

    def confirm(title: str, text: str, details: str = "") -> bool:
        box = QMessageBox(dialog)
        box.setWindowTitle(title)
        box.setIcon(QMessageBox.Icon.Warning)
        box.setText(text)
        if details:
            box.setInformativeText(details)
        box.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        box.setDefaultButton(QMessageBox.StandardButton.No)
        return box.exec() == QMessageBox.StandardButton.Yes

    def clear_current_metadata() -> None:
        metadata_path = window.metadata_path()
        if metadata_path is None or not metadata_path.exists():
            QMessageBox.information(
                dialog, "Metadata Manager", "No current metadata to clear."
            )
            return
        if not confirm(
            "Clear Current Metadata",
            "Clear metadata for current source context?",
            "Per-image overrides, print flags, and logs for this context will be removed.",
        ):
            return
        count, size = window.remove_path_tree(metadata_path)
        window.folder_metadata = window.default_metadata()
        if window.image_paths:
            window.refresh_image_list_labels(window.selected_path())
            window.update_selected_print_info()
        window.append_log(
            "INFO",
            f"Metadata Manager cleared current metadata: {count} file(s), {window.format_storage_size(size)}",
        )
        window.statusBar().showMessage("Cleared current metadata")
        update_stats()

    def clear_source_metadata() -> None:
        source_dir = window.metadata_source_dir()
        source_id = window.metadata_source_id()
        if not source_dir.exists():
            QMessageBox.information(
                dialog,
                "Metadata Manager",
                "No metadata found for current source.",
            )
            return
        if not confirm(
            "Clear Current Source Metadata",
            f"Clear all metadata for source '{source_id}'?",
            "This removes every context under this source type.",
        ):
            return
        count, size = window.remove_path_tree(source_dir)
        window.folder_metadata = window.default_metadata()
        if window.image_paths:
            window.refresh_image_list_labels(window.selected_path())
            window.update_selected_print_info()
        window.append_log(
            "INFO",
            f"Metadata Manager cleared source metadata ({source_id}): {count} file(s), {window.format_storage_size(size)}",
        )
        window.statusBar().showMessage(f"Cleared metadata for source {source_id}")
        update_stats()

    def clear_all_metadata() -> None:
        root = window.metadata_root_path()
        if not root.exists():
            QMessageBox.information(
                dialog, "Metadata Manager", "No metadata cache found."
            )
            return
        if not confirm(
            "Clear All Metadata",
            "Clear all metadata for all source contexts?",
            "This removes saved settings/history for every source context.",
        ):
            return
        count, size = window.remove_path_tree(root)
        window.folder_metadata = window.default_metadata()
        if window.image_paths:
            window.refresh_image_list_labels(window.selected_path())
            window.update_selected_print_info()
        window.append_log(
            "INFO",
            f"Metadata Manager cleared all metadata: {count} file(s), {window.format_storage_size(size)}",
        )
        window.statusBar().showMessage("Cleared all metadata")
        update_stats()

    def rebuild_current_metadata() -> None:
        metadata_path = window.metadata_path()
        if metadata_path is None or window.current_folder is None:
            QMessageBox.information(
                dialog,
                "Metadata Manager",
                "No active source context to rebuild.",
            )
            return
        window.save_folder_metadata()
        window.append_log(
            "INFO",
            f"Metadata Manager rebuilt current metadata file: {metadata_path}",
        )
        window.statusBar().showMessage("Rebuilt current metadata file")
        update_stats()

    refresh_button.clicked.connect(update_stats)
    clear_current_metadata_button.clicked.connect(clear_current_metadata)
    clear_source_metadata_button.clicked.connect(clear_source_metadata)
    clear_all_metadata_button.clicked.connect(clear_all_metadata)
    rebuild_current_metadata_button.clicked.connect(rebuild_current_metadata)

    update_stats()
    dialog.exec()
