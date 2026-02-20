from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMenu,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QSplitter,
    QStatusBar,
    QTableWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from album_printer.ui.preview_label import PreviewLabel


def initialize_window_shell(
    window: Any,
    *,
    app_display_name: str,
    app_window_icon_fn: Any,
    width: int,
    height: int,
) -> None:
    window.setWindowTitle(app_display_name)
    icon = app_window_icon_fn()
    if icon is not None:
        window.setWindowIcon(icon)
    window.resize(width, height)


def finalize_main_window_setup(
    window: Any,
    *,
    startup_scan_delay_ms: int,
) -> None:
    window.restore_ui_state()
    window.setup_menu()
    window.update_folder_settings_availability()
    window.append_log("INFO", "Application started")
    for line in window.startup_debug_lines:
        window.append_log("DEBUG", line)
    window.refresh_print_queue_table()
    window.update_queue_panel_max_width()
    QTimer.singleShot(
        startup_scan_delay_ms, window.startup_scan_bookmarked_google_albums
    )


def build_main_window_ui(
    window: Any,
    *,
    table_col_thumb: int,
    table_col_state: int,
    table_col_print: int,
    table_col_file: int,
    table_col_date_used: int,
    table_col_location: int,
    table_col_aspect: int,
    reframe_handle_size: int,
    per_image_location_stamp_overrides: list[str],
    log_levels: list[str],
) -> None:
    setup_image_table_widgets(
        window,
        table_col_thumb=table_col_thumb,
        table_col_state=table_col_state,
        table_col_print=table_col_print,
        table_col_file=table_col_file,
        table_col_date_used=table_col_date_used,
        table_col_location=table_col_location,
        table_col_aspect=table_col_aspect,
    )
    setup_preview_widgets(window, reframe_handle_size=reframe_handle_size)
    (
        prev_button,
        next_button,
        print_settings_button,
        print_selected_button,
        print_button,
    ) = setup_primary_action_buttons(window)
    setup_controls_widgets(
        window,
        per_image_location_stamp_overrides=per_image_location_stamp_overrides,
    )
    setup_controls_layout(window)
    setup_log_widgets(window, log_levels=log_levels)
    setup_queue_widgets(window)
    setup_main_layout_widgets(
        window,
        prev_button=prev_button,
        next_button=next_button,
        print_settings_button=print_settings_button,
        print_selected_button=print_selected_button,
        print_button=print_button,
    )
    setup_status_widgets(window)


def setup_image_table_widgets(
    window: Any,
    *,
    table_col_thumb: int,
    table_col_state: int,
    table_col_print: int,
    table_col_file: int,
    table_col_date_used: int,
    table_col_location: int,
    table_col_aspect: int,
) -> None:
    window.image_table = QTableWidget(0, 7)
    window.image_table.setHorizontalHeaderLabels(
        [
            "",
            "State",
            "Print",
            "File",
            "Date",
            "Location",
            "Aspect",
        ]
    )
    window.image_table.setSelectionBehavior(
        QAbstractItemView.SelectionBehavior.SelectRows
    )
    window.image_table.setSelectionMode(
        QAbstractItemView.SelectionMode.ExtendedSelection
    )
    window.image_table.verticalHeader().setVisible(False)
    header = window.image_table.horizontalHeader()
    if isinstance(header, QHeaderView):
        header.setStretchLastSection(True)
        header.resizeSection(table_col_thumb, 64)
        header.resizeSection(table_col_state, 80)
        header.resizeSection(table_col_print, 95)
        header.resizeSection(table_col_file, 280)
        header.resizeSection(table_col_date_used, 170)
        header.resizeSection(table_col_location, 120)
        header.resizeSection(table_col_aspect, 90)
        header.setSortIndicatorShown(True)
        header.sectionClicked.connect(window.on_image_table_header_clicked)
    window.update_table_sort_indicator()
    window.image_table.currentCellChanged.connect(
        window.on_image_table_selection_changed
    )
    window.image_table.verticalScrollBar().valueChanged.connect(
        lambda _value: window.note_table_scrolled()
    )
    window.image_table.horizontalScrollBar().valueChanged.connect(
        lambda _value: window.note_table_scrolled()
    )


def setup_preview_widgets(window: Any, *, reframe_handle_size: int) -> None:
    window.preview_label = PreviewLabel(
        "Load photos to begin",
        reframe_handle_size=reframe_handle_size,
    )
    window.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    window.preview_label.setMinimumSize(1, 1)
    window.preview_label.setStyleSheet("background: #111; color: #ddd;")
    window.preview_label.drag_started.connect(window.on_preview_drag_started)
    window.preview_label.dragged.connect(window.on_preview_dragged)
    window.preview_label.drag_released.connect(window.on_preview_drag_released)
    window.preview_scaled_size = (1, 1)
    window.preview_source_size = (0, 0)
    window.preview_display_rect = (0, 0, 0, 0)
    window._reframe_drag_active = False
    window._reframe_interaction_mode = "pan"
    window._reframe_resize_corner = None
    window._reframe_pan_accum_x = 0.0
    window._reframe_pan_accum_y = 0.0
    window._reframe_zoom_accum = 0.0

    window.preview_container = QScrollArea()
    window.preview_container.setWidget(window.preview_label)
    window.preview_container.setWidgetResizable(True)


def setup_log_widgets(window: Any, *, log_levels: list[str]) -> None:
    window.log_console = QTextEdit()
    window.log_console.setReadOnly(True)
    window.log_console.setPlaceholderText("Log output")
    window.log_console.setMinimumHeight(90)

    window.log_level_combo = QComboBox()
    window.log_level_combo.addItems(log_levels)
    window.log_level_combo.setCurrentText(window.log_level_filter_value)
    window.log_level_combo.currentTextChanged.connect(window.on_log_level_changed)

    window.log_text_filter_input = QLineEdit()
    window.log_text_filter_input.setPlaceholderText("Filter logs (e.g. GOOGLE)")
    window.log_text_filter_input.textChanged.connect(window.on_log_text_filter_changed)

    window.log_clear_button = QPushButton("Clear Logs")
    window.log_clear_button.clicked.connect(window.clear_log_console)


def setup_queue_widgets(window: Any) -> None:
    window.print_queue_table = QTableWidget(0, 5)
    window.print_queue_table.setHorizontalHeaderLabels(
        ["ID", "Status", "Count", "Target", "Detail"]
    )
    window.print_queue_table.setSelectionBehavior(
        QAbstractItemView.SelectionBehavior.SelectRows
    )
    window.print_queue_table.setSelectionMode(
        QAbstractItemView.SelectionMode.SingleSelection
    )
    window.print_queue_table.verticalHeader().setVisible(False)
    queue_header = window.print_queue_table.horizontalHeader()
    if isinstance(queue_header, QHeaderView):
        queue_header.resizeSection(0, 56)
        queue_header.resizeSection(1, 90)
        queue_header.resizeSection(2, 56)
        queue_header.resizeSection(3, 160)
        queue_header.setStretchLastSection(True)

    window.queue_pause_button = QPushButton("Pause Queue")
    window.queue_pause_button.clicked.connect(window.pause_print_queue)
    window.queue_resume_button = QPushButton("Resume Queue")
    window.queue_resume_button.clicked.connect(window.resume_print_queue)
    window.queue_cancel_button = QPushButton("Cancel Selected")
    window.queue_cancel_button.clicked.connect(window.cancel_selected_queue_item)
    window.queue_remove_button = QPushButton("Remove Selected")
    window.queue_remove_button.clicked.connect(window.remove_selected_queue_item)
    window.queue_clear_button = QPushButton("Clear Finished")
    window.queue_clear_button.clicked.connect(window.clear_finished_queue_items)


def setup_primary_action_buttons(window: Any) -> tuple[QPushButton, ...]:
    window.load_button = QPushButton("Load ...")
    window.load_menu = QMenu(window)
    window.load_folder_action = QAction("Folder", window)
    window.load_folder_action.triggered.connect(window.load_folder)
    window.load_google_action = QAction("Google Photos Photo Picker", window)
    window.load_google_action.triggered.connect(window.load_google_photos)
    window.load_google_album_url_action = QAction("Google Photos Album URL", window)
    window.load_google_album_url_action.triggered.connect(
        window.load_google_photos_album_url
    )
    window.load_menu.addAction(window.load_folder_action)
    window.load_menu.addAction(window.load_google_action)
    window.load_menu.addAction(window.load_google_album_url_action)
    window.load_menu.addSeparator()
    window.load_source_guide_action = QAction("Guide Me", window)
    window.load_source_guide_action.triggered.connect(window.show_source_guide_dialog)
    window.load_menu.addAction(window.load_source_guide_action)
    window.load_button.setMenu(window.load_menu)

    window.refresh_folder_button = QPushButton("Quick Reload")
    window.refresh_folder_button.clicked.connect(window.refresh_folder)
    window.refetch_metadata_button = QPushButton("Refetch metadata")
    window.refetch_metadata_button.clicked.connect(window.refresh_folder)
    window.stop_album_sync_button = QPushButton("Stop Album Sync")
    window.stop_album_sync_button.clicked.connect(window.stop_album_sync)
    window.stop_album_sync_button.setEnabled(False)

    prev_button = QPushButton("Previous")
    prev_button.clicked.connect(window.select_previous)

    next_button = QPushButton("Next")
    next_button.clicked.connect(window.select_next)

    window.app_settings_button = QPushButton("Settings")
    window.app_settings_button.clicked.connect(window.open_settings_dialog)

    window.folder_settings_button = QPushButton("Image Settings")
    window.folder_settings_button.clicked.connect(window.open_project_settings_dialog)

    print_settings_button = QPushButton("Printer Settings")
    print_settings_button.clicked.connect(window.open_print_settings_dialog)

    print_selected_button = QPushButton("Print Selected")
    print_selected_button.clicked.connect(window.print_selected)

    print_button = QPushButton("Print All")
    print_button.clicked.connect(window.print_all)

    return (
        prev_button,
        next_button,
        print_settings_button,
        print_selected_button,
        print_button,
    )


def setup_controls_widgets(
    window: Any, *, per_image_location_stamp_overrides: list[str]
) -> None:
    window.crop_orientation_button = QPushButton("Crop: Landscape")
    window.crop_orientation_button.clicked.connect(window.toggle_crop_orientation)
    window.rotate_image_button = QPushButton("Rotate 90°")
    window.rotate_image_button.clicked.connect(window.rotate_selected_image_clockwise)
    window.rotate_reset_button = QPushButton("Reset")
    window.rotate_reset_button.clicked.connect(window.reset_selected_image_rotation)
    window.rotate_image_label = QLabel("0°")

    window.crop_reframe_button = QPushButton("Reframe Crop")
    window.crop_reframe_button.setCheckable(True)
    window.crop_reframe_button.toggled.connect(window.on_crop_reframe_toggled)
    window.crop_reset_button = QPushButton("Reset Crop")
    window.crop_reset_button.clicked.connect(window.reset_crop_for_selected)
    window.prev_fix_button = QPushButton("Prev need fix")
    window.prev_fix_button.setToolTip("Previous image that needs fixing (crop or date)")
    window.prev_fix_button.clicked.connect(window.select_previous_fix)
    window.next_fix_button = QPushButton("Next need fix")
    window.next_fix_button.setToolTip("Next image that needs fixing (crop or date)")
    window.next_fix_button.clicked.connect(window.select_next_fix)
    window.fix_needed_label = QLabel("—")
    window.fix_needed_label.setWordWrap(True)
    window.fix_needed_label.setStyleSheet("color: #c0a000;")

    window.datetime_override_button = QPushButton("Set Date/Time")
    window.datetime_override_button.clicked.connect(
        window.set_datetime_override_for_selected
    )

    window.datetime_override_clear_button = QPushButton("Clear")
    window.datetime_override_clear_button.clicked.connect(
        window.clear_datetime_override_for_selected
    )

    window.datetime_override_label = QLabel("Auto")
    window.location_value_label = QLabel("No location")
    window.location_value_label.setWordWrap(True)
    window.location_value_label.setSizePolicy(
        QSizePolicy.Policy.Ignored,
        QSizePolicy.Policy.Preferred,
    )
    window.location_stamp_override_combo = QComboBox()
    window.location_stamp_override_combo.addItems(per_image_location_stamp_overrides)
    window.location_stamp_override_combo.setCurrentText("Default")
    window.location_stamp_override_combo.currentTextChanged.connect(
        window.refresh_preview
    )
    window.location_stamp_override_combo.currentTextChanged.connect(
        window.on_image_settings_changed
    )
    window.location_custom_text_combo = QComboBox()
    window.location_custom_text_combo.setEditable(True)
    window.location_custom_text_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
    window.copy_prev_location_button = QPushButton("Copy Prev")
    window.copy_prev_location_button.clicked.connect(
        window.copy_location_from_previous_image
    )
    custom_location_line_edit = window.location_custom_text_combo.lineEdit()
    if custom_location_line_edit is not None:
        custom_location_line_edit.setPlaceholderText("Custom location text")
        custom_location_line_edit.textChanged.connect(window.refresh_preview)
        custom_location_line_edit.editingFinished.connect(
            window.on_image_settings_changed
        )
    window.location_custom_text_combo.activated.connect(
        lambda _index: window.on_image_settings_changed()
    )

    def update_custom_text_enabled() -> None:
        is_custom = window.location_stamp_override_combo.currentText() == "Custom Text"
        window.location_custom_text_combo.setEnabled(is_custom)

    window.location_stamp_override_combo.currentTextChanged.connect(
        lambda _value: update_custom_text_enabled()
    )
    update_custom_text_enabled()
    window.ignore_for_print_all_checkbox = QCheckBox("Ignore in Print All")
    window.ignore_for_print_all_checkbox.setChecked(False)
    window.ignore_for_print_all_checkbox.toggled.connect(
        window.on_ignore_for_print_all_toggled
    )
    window.mark_printed_button = QPushButton("Mark Printed")
    window.mark_printed_button.clicked.connect(window.mark_selected_as_printed)
    window.clear_failed_logs_button = QPushButton("Clear Failed Logs")
    window.clear_failed_logs_button.clicked.connect(
        window.clear_failed_logs_for_selected
    )
    window.print_again_button = QPushButton("Clear Print Status")
    window.print_again_button.clicked.connect(window.clear_selected_print_status)
    window.print_status_label = QLabel("Not Printed")
    window.print_status_label.setWordWrap(True)
    window.print_attempts_table = QTableWidget(0, 5)
    window.print_attempts_table.setHorizontalHeaderLabels(
        ["Time", "Status", "Backend", "Job", "Error"]
    )
    window.print_attempts_table.setSelectionMode(
        QAbstractItemView.SelectionMode.NoSelection
    )
    window.print_attempts_table.setEditTriggers(
        QAbstractItemView.EditTrigger.NoEditTriggers
    )
    window.print_attempts_table.verticalHeader().setVisible(False)
    window.print_attempts_table.horizontalHeader().resizeSection(0, 128)
    window.print_attempts_table.horizontalHeader().resizeSection(1, 68)
    window.print_attempts_table.horizontalHeader().resizeSection(2, 72)
    window.print_attempts_table.horizontalHeader().resizeSection(3, 92)
    window.print_attempts_table.horizontalHeader().setStretchLastSection(True)
    window.print_attempts_table.setMinimumHeight(120)

    window.brightness_slider = QSlider(Qt.Orientation.Horizontal)
    window.brightness_slider.setRange(50, 150)
    window.brightness_slider.setValue(100)
    window.brightness_slider.valueChanged.connect(window.refresh_preview)
    window.brightness_slider.sliderReleased.connect(window.on_image_settings_changed)

    window.brightness_label = QLabel("100%")
    window.brightness_slider.valueChanged.connect(
        lambda value: window.brightness_label.setText(f"{value}%")
    )

    window.crop_zoom_slider = QSlider(Qt.Orientation.Horizontal)
    window.crop_zoom_slider.setRange(100, 300)
    window.crop_zoom_slider.setValue(100)
    window.crop_zoom_slider.valueChanged.connect(window.refresh_preview)
    window.crop_zoom_slider.sliderReleased.connect(window.on_image_settings_changed)
    window.crop_zoom_label = QLabel("100%")
    window.crop_zoom_slider.valueChanged.connect(
        lambda value: window.crop_zoom_label.setText(f"{value}%")
    )

    window.crop_x_slider = QSlider(Qt.Orientation.Horizontal)
    window.crop_x_slider.setRange(-100, 100)
    window.crop_x_slider.setValue(0)
    window.crop_x_slider.valueChanged.connect(window.refresh_preview)
    window.crop_x_slider.sliderReleased.connect(window.on_image_settings_changed)
    window.crop_x_label = QLabel("0")
    window.crop_x_slider.valueChanged.connect(
        lambda value: window.crop_x_label.setText(str(value))
    )

    window.crop_y_slider = QSlider(Qt.Orientation.Horizontal)
    window.crop_y_slider.setRange(-100, 100)
    window.crop_y_slider.setValue(0)
    window.crop_y_slider.valueChanged.connect(window.refresh_preview)
    window.crop_y_slider.sliderReleased.connect(window.on_image_settings_changed)
    window.crop_y_label = QLabel("0")
    window.crop_y_slider.valueChanged.connect(
        lambda value: window.crop_y_label.setText(str(value))
    )


def setup_controls_layout(window: Any) -> None:
    controls_layout = QFormLayout()
    controls_layout.addRow("Crop Mode", window.crop_orientation_button)
    rotate_row = QWidget()
    rotate_layout = QHBoxLayout(rotate_row)
    rotate_layout.setContentsMargins(0, 0, 0, 0)
    rotate_layout.addWidget(window.rotate_image_button)
    rotate_layout.addWidget(window.rotate_reset_button)
    rotate_layout.addWidget(window.rotate_image_label)
    rotate_layout.addStretch(1)
    controls_layout.addRow("Rotation", rotate_row)
    reframe_row = QWidget()
    reframe_layout = QHBoxLayout(reframe_row)
    reframe_layout.setContentsMargins(0, 0, 0, 0)
    reframe_layout.addWidget(window.crop_reframe_button)
    reframe_layout.addWidget(window.crop_reset_button)
    controls_layout.addRow("Reframe", reframe_row)
    fix_row = QWidget()
    fix_layout = QHBoxLayout(fix_row)
    fix_layout.setContentsMargins(0, 0, 0, 0)
    fix_layout.addWidget(window.prev_fix_button)
    fix_layout.addWidget(window.next_fix_button)
    controls_layout.addRow("Fix", fix_row)
    controls_layout.addRow("Needs fixing", window.fix_needed_label)

    brightness_row = QWidget()
    brightness_layout = QHBoxLayout(brightness_row)
    brightness_layout.setContentsMargins(0, 0, 0, 0)
    brightness_layout.addWidget(window.brightness_slider)
    brightness_layout.addWidget(window.brightness_label)
    controls_layout.addRow("Brightness", brightness_row)

    zoom_row = QWidget()
    zoom_layout = QHBoxLayout(zoom_row)
    zoom_layout.setContentsMargins(0, 0, 0, 0)
    zoom_layout.addWidget(window.crop_zoom_slider)
    zoom_layout.addWidget(window.crop_zoom_label)
    controls_layout.addRow("Crop Zoom", zoom_row)

    x_row = QWidget()
    x_layout = QHBoxLayout(x_row)
    x_layout.setContentsMargins(0, 0, 0, 0)
    x_layout.addWidget(window.crop_x_slider)
    x_layout.addWidget(window.crop_x_label)
    controls_layout.addRow("Crop X", x_row)

    y_row = QWidget()
    y_layout = QHBoxLayout(y_row)
    y_layout.setContentsMargins(0, 0, 0, 0)
    y_layout.addWidget(window.crop_y_slider)
    y_layout.addWidget(window.crop_y_label)
    controls_layout.addRow("Crop Y", y_row)

    datetime_row = QWidget()
    datetime_layout = QHBoxLayout(datetime_row)
    datetime_layout.setContentsMargins(0, 0, 0, 0)
    datetime_layout.addWidget(window.datetime_override_button)
    datetime_layout.addWidget(window.datetime_override_clear_button)
    controls_layout.addRow("Date/Time", datetime_row)
    controls_layout.addRow("Override", window.datetime_override_label)
    controls_layout.addRow("Location", window.location_value_label)
    controls_layout.addRow("Location Stamp", window.location_stamp_override_combo)
    custom_location_row = QWidget()
    custom_location_layout = QHBoxLayout(custom_location_row)
    custom_location_layout.setContentsMargins(0, 0, 0, 0)
    custom_location_layout.addWidget(window.location_custom_text_combo)
    custom_location_layout.addWidget(window.copy_prev_location_button)
    controls_layout.addRow("Custom Location", custom_location_row)
    controls_layout.addRow("Print All", window.ignore_for_print_all_checkbox)
    state_actions_row = QWidget()
    state_actions_layout = QHBoxLayout(state_actions_row)
    state_actions_layout.setContentsMargins(0, 0, 0, 0)
    state_actions_layout.addWidget(window.mark_printed_button)
    state_actions_layout.addWidget(window.clear_failed_logs_button)
    state_actions_layout.addWidget(window.print_again_button)
    controls_layout.addRow("State Actions", state_actions_row)
    controls_layout.addRow("Last Print", window.print_status_label)
    controls_layout.addRow("Print Attempts", window.print_attempts_table)

    window.controls_widget = QWidget()
    window.controls_widget.setLayout(controls_layout)
    window.controls_widget.setVisible(False)


def setup_main_layout_widgets(
    window: Any,
    *,
    prev_button: QWidget,
    next_button: QWidget,
    print_settings_button: QWidget,
    print_selected_button: QWidget,
    print_button: QWidget,
) -> None:
    top_actions = QHBoxLayout()
    top_actions.addWidget(window.load_button)
    top_actions.addWidget(window.refresh_folder_button)
    top_actions.addWidget(window.refetch_metadata_button)
    top_actions.addWidget(window.stop_album_sync_button)
    top_actions.addWidget(prev_button)
    top_actions.addWidget(next_button)
    top_actions.addWidget(window.app_settings_button)
    top_actions.addWidget(window.folder_settings_button)
    top_actions.addWidget(print_settings_button)
    top_actions.addStretch(1)
    top_actions.addWidget(print_selected_button)
    top_actions.addWidget(print_button)

    root = QVBoxLayout()
    root.addLayout(top_actions)

    window.list_preview_splitter = QSplitter(Qt.Orientation.Horizontal)
    window.list_preview_splitter.setChildrenCollapsible(False)
    window.list_preview_splitter.addWidget(window.image_table)
    window.list_preview_splitter.addWidget(window.preview_container)
    window.list_preview_splitter.setStretchFactor(0, 3)
    window.list_preview_splitter.setStretchFactor(1, 6)

    window.content_splitter = QSplitter(Qt.Orientation.Horizontal)
    window.content_splitter.setChildrenCollapsible(False)
    window.content_splitter.addWidget(window.list_preview_splitter)
    window.content_splitter.addWidget(window.controls_widget)
    window.content_splitter.setStretchFactor(0, 9)
    window.content_splitter.setStretchFactor(1, 2)

    body = QHBoxLayout()
    body.addWidget(window.content_splitter)
    main_content = QWidget()
    main_content.setLayout(body)

    log_header = QHBoxLayout()
    log_header.addWidget(QLabel("Filter"))
    log_header.addWidget(window.log_text_filter_input)
    log_header.addWidget(QLabel("Log Level"))
    log_header.addWidget(window.log_level_combo)
    log_header.addStretch(1)
    log_header.addWidget(window.log_clear_button)

    log_panel = QWidget()
    log_layout = QVBoxLayout(log_panel)
    log_layout.setContentsMargins(0, 0, 0, 0)
    log_layout.addLayout(log_header)
    log_layout.addWidget(window.log_console)

    queue_header_row = QHBoxLayout()
    queue_header_row.addWidget(QLabel("Print Queue"))
    queue_header_row.addStretch(1)
    queue_header_row.addWidget(window.queue_pause_button)
    queue_header_row.addWidget(window.queue_resume_button)
    queue_header_row.addWidget(window.queue_cancel_button)
    queue_header_row.addWidget(window.queue_remove_button)
    queue_header_row.addWidget(window.queue_clear_button)

    window.queue_progress_bar = QProgressBar()
    window.queue_progress_bar.setTextVisible(True)
    window.queue_progress_bar.setRange(0, 1)
    window.queue_progress_bar.setValue(0)
    window.queue_progress_bar.setFormat("Queue 0/0")
    window.queue_progress_bar.hide()

    queue_panel = QWidget()
    window.queue_panel = queue_panel
    queue_layout = QVBoxLayout(queue_panel)
    queue_layout.setContentsMargins(0, 0, 0, 0)
    queue_layout.addLayout(queue_header_row)
    queue_layout.addWidget(window.queue_progress_bar)
    queue_layout.addWidget(window.print_queue_table)
    queue_panel.setSizePolicy(
        QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding
    )

    window.bottom_splitter = QSplitter(Qt.Orientation.Horizontal)
    window.bottom_splitter.setChildrenCollapsible(False)
    window.bottom_splitter.addWidget(log_panel)
    window.bottom_splitter.addWidget(queue_panel)
    window.bottom_splitter.setStretchFactor(0, 3)
    window.bottom_splitter.setStretchFactor(1, 0)

    window.main_vertical_splitter = QSplitter(Qt.Orientation.Vertical)
    window.main_vertical_splitter.setChildrenCollapsible(False)
    window.main_vertical_splitter.addWidget(main_content)
    window.main_vertical_splitter.addWidget(window.bottom_splitter)
    window.main_vertical_splitter.setStretchFactor(0, 8)
    window.main_vertical_splitter.setStretchFactor(1, 2)

    root.addWidget(window.main_vertical_splitter)

    wrapper = QWidget()
    wrapper.setLayout(root)
    window.setCentralWidget(wrapper)


def setup_status_widgets(window: Any) -> None:
    window.setStatusBar(QStatusBar())
    window.footer_progress_bar = QProgressBar(window)
    window.footer_progress_bar.setMinimumWidth(220)
    window.footer_progress_bar.setTextVisible(True)
    window.footer_progress_bar.setRange(0, 1)
    window.footer_progress_bar.setValue(0)
    window.footer_progress_bar.setFormat("Progress %v/%m")
    window.footer_progress_bar.hide()
    window.statusBar().addPermanentWidget(window.footer_progress_bar)
    window.footer_progress_action_button = QPushButton(window)
    window.footer_progress_action_button.setVisible(False)
    window.footer_progress_action_button.clicked.connect(
        window.on_footer_progress_action_clicked
    )
    window.statusBar().addPermanentWidget(window.footer_progress_action_button)
    window.footer_progress_action_handler = None


__all__ = [
    "build_main_window_ui",
    "finalize_main_window_setup",
    "initialize_window_shell",
    "setup_image_table_widgets",
    "setup_controls_layout",
    "setup_controls_widgets",
    "setup_main_layout_widgets",
    "setup_primary_action_buttons",
    "setup_log_widgets",
    "setup_preview_widgets",
    "setup_queue_widgets",
    "setup_status_widgets",
]
