from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from urllib.parse import quote

from PySide6.QtCore import QEvent, QObject, Qt, Slot
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtGui import QCursor, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QDockWidget,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSplitter,
    QSlider,
    QToolTip,
    QVBoxLayout,
    QWidget,
)

from album_print_flow.app_constants import TABLE_COL_FILE
from album_print_flow.ui.location_area_flow import normalize_location_areas


@dataclass(frozen=True)
class LocationPanelEntry:
    path: Any
    entry_id: str
    label: str
    has_gps: bool
    has_manual: bool
    latitude: float | None
    longitude: float | None


def _manual_location_for_path(window: Any, path: Any) -> tuple[float, float] | None:
    entry = window.photo_entry_for_path(path)
    manual = entry.get("manual_location")
    if not isinstance(manual, dict):
        return None
    try:
        latitude = float(manual.get("latitude"))
        longitude = float(manual.get("longitude"))
    except (TypeError, ValueError):
        return None
    if -90.0 <= latitude <= 90.0 and -180.0 <= longitude <= 180.0:
        return latitude, longitude
    return None


def _build_location_panel_entries(window: Any) -> list[LocationPanelEntry]:
    entries: list[LocationPanelEntry] = []
    for path in window.image_paths:
        manual_location = _manual_location_for_path(window, path)
        location = window.location_for_path(path)
        has_gps = location is not None
        has_manual = manual_location is not None
        label = path.name
        latitude = None
        longitude = None
        if location is not None:
            latitude, longitude = location
            prefix = "Manual" if has_manual else "GPS"
            label = f"{path.name} ({prefix} {latitude:.5f}, {longitude:.5f})"
        else:
            label = f"{path.name} (No GPS)"

        entry_id = window.metadata_key_for_path(path)
        entries.append(
            LocationPanelEntry(
                path=path,
                entry_id=entry_id,
                label=label,
                has_gps=has_gps,
                has_manual=has_manual,
                latitude=latitude,
                longitude=longitude,
            )
        )

    return entries


def _panel_state_payload(
    window: Any, entries: list[LocationPanelEntry]
) -> dict[str, object]:
    points: list[dict[str, object]] = []
    for entry in entries:
        if not entry.has_gps or entry.latitude is None or entry.longitude is None:
            continue
        points.append(
            {
                "id": entry.entry_id,
                "lat": entry.latitude,
                "lon": entry.longitude,
                "name": entry.label,
            }
        )

    areas = window.location_areas_for_window()
    return {"points": points, "areas": areas}


def _entry_matches_filter(entry: LocationPanelEntry, mode: str) -> bool:
    if mode == "gps":
        return entry.has_gps
    if mode == "manual":
        return entry.has_manual
    if mode == "no_gps":
        return not entry.has_gps
    return True


def _recent_pins_for_window(window: Any) -> list[dict[str, object]]:
    raw = window.folder_metadata.get("recent_pins")
    if not isinstance(raw, list):
        return []
    pins: list[dict[str, object]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        entry_id = str(item.get("id", "")).strip()
        name = str(item.get("name", "")).strip()
        timestamp = str(item.get("timestamp", "")).strip()
        if not entry_id or not name:
            continue
        pins.append(
            {
                "id": entry_id,
                "name": name,
                "timestamp": timestamp,
                "latitude": item.get("latitude"),
                "longitude": item.get("longitude"),
                "previous_manual": item.get("previous_manual"),
            }
        )
    return pins


def _path_for_entry_id(window: Any, entry_id: str) -> Any | None:
    if not entry_id:
        return None
    for path in window.image_paths:
        if window.metadata_key_for_path(path) == entry_id:
            return path
    return None


def _file_url_for_path(path: Any) -> str:
    try:
        return "file:///" + quote(path.as_posix())
    except AttributeError:
        return ""


def _area_lookup(areas: list[dict[str, object]]) -> dict[str, dict[str, object]]:
    lookup: dict[str, dict[str, object]] = {}
    for area in areas:
        area_id = str(area.get("id", "")).strip()
        if area_id:
            lookup[area_id] = area
    return lookup


class LocationAreasPanelBridge(QObject):
    def __init__(self, window: Any) -> None:
        super().__init__()
        self._window = window

    @Slot(result=str)
    def get_initial_state(self) -> str:
        entries = _build_location_panel_entries(self._window)
        payload = _panel_state_payload(self._window, entries)
        return json.dumps(payload)

    @Slot()
    def map_ready(self) -> None:
        self._window.location_panel_map_ready = True
        pending = self._window.location_panel_pending_state
        if pending is not None:
            self._window.location_panel_pending_state = None
            self._window.location_panel_view.page().runJavaScript(
                "window.setMapState(%s);" % json.dumps(pending)
            )
        pending_entry = self._window.location_panel_pending_entry_id
        if pending_entry:
            self._window.location_panel_pending_entry_id = None
            payload = json.dumps(pending_entry)
            self._window.location_panel_view.page().runJavaScript(
                "window.selectEntry(%s);" % payload
            )
            self._window.location_panel_view.page().runJavaScript(
                "window.focusMarker(%s);" % payload
            )

    @Slot(str)
    def save_areas(self, payload: str) -> None:
        if self._window.current_folder is None:
            return
        try:
            raw = json.loads(payload)
        except json.JSONDecodeError:
            return
        if not isinstance(raw, list):
            return

        normalized = normalize_location_areas(raw)
        self._window.store_location_areas(normalized)
        self._window.refresh_preview()
        self._window.refresh_image_list_labels(self._window.selected_path())
        self._window.refresh_location_areas_panel()

    @Slot(str)
    def select_entry(self, entry_id: str) -> None:
        self._window.select_image_by_entry_id(entry_id)

    @Slot(str)
    def select_area(self, area_id: str) -> None:
        self._window.select_location_area(area_id)

    @Slot(float, float)
    def set_manual_location(self, latitude: float, longitude: float) -> None:
        self._window.set_manual_location_for_selected(latitude, longitude)


class _SplitterResetFilter(QObject):
    def __init__(self, window: Any) -> None:
        super().__init__()
        self._window = window

    def eventFilter(self, _watched: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.MouseButtonDblClick:
            _reset_location_panel_splitter(self._window)
            return True
        return False


class _LocationPanelPage(QWebEnginePage):
    def __init__(self, window: Any, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._window = window

    def javaScriptConsoleMessage(
        self,
        level: QWebEnginePage.JavaScriptConsoleMessageLevel,
        message: str,
        line_number: int,
        source_id: str,
    ) -> None:  # noqa: N802
        level_name = {
            QWebEnginePage.JavaScriptConsoleMessageLevel.InfoMessageLevel: "INFO",
            QWebEnginePage.JavaScriptConsoleMessageLevel.WarningMessageLevel: "WARNING",
            QWebEnginePage.JavaScriptConsoleMessageLevel.ErrorMessageLevel: "ERROR",
        }.get(level, "INFO")
        self._window.thread_safe_append_log(
            "INFO",
            f"[MAP_JS:{level_name}] {message} ({source_id}:{line_number})",
        )


def setup_location_areas_panel(window: Any) -> None:
    window.location_panel_map_ready = False
    window.location_panel_pending_state = None
    window.location_panel_pending_entry_id = None
    window.location_panel_syncing = False
    window.location_panel_selected_path = None
    window.location_panel_selected_area_id = None
    window.location_panel_pin_mode = False
    window.location_panel_filter_mode = "all"

    dock = QDockWidget("Location Areas", window)
    dock.setObjectName("locationAreasDock")
    dock.setAllowedAreas(Qt.DockWidgetArea.RightDockWidgetArea)
    dock.setFeatures(
        QDockWidget.DockWidgetFeature.DockWidgetMovable
        | QDockWidget.DockWidgetFeature.DockWidgetFloatable
    )

    panel_container = QWidget(dock)
    panel_layout = QVBoxLayout(panel_container)
    panel_layout.setContentsMargins(6, 6, 6, 6)

    header_row = QHBoxLayout()
    title = QLabel("Location Areas")
    title.setStyleSheet("font-weight: 600;")
    window.location_panel_counts_label = QLabel("GPS 0/0")
    window.location_panel_counts_label.setStyleSheet("color: #9CA3AF;")
    window.location_panel_no_gps_badge = QLabel("No GPS 0")
    window.location_panel_no_gps_badge.setStyleSheet(
        "background: #1f2937; color: #fbbf24; border-radius: 8px; padding: 2px 6px;"
    )
    window.location_panel_refresh_button = QPushButton("Refresh")
    window.location_panel_refresh_button.setMaximumWidth(90)
    window.location_panel_clear_highlight_button = QPushButton("Clear Highlight")
    header_row.addWidget(title)
    header_row.addWidget(window.location_panel_counts_label)
    header_row.addWidget(window.location_panel_no_gps_badge)
    header_row.addStretch(1)
    header_row.addWidget(window.location_panel_refresh_button)
    header_row.addWidget(window.location_panel_clear_highlight_button)
    panel_layout.addLayout(header_row)

    window.location_panel_status_label = QLabel("Map loading...")
    window.location_panel_status_label.setStyleSheet("color: #9CA3AF;")
    panel_layout.addWidget(window.location_panel_status_label)

    area_container = QWidget(panel_container)
    area_layout = QVBoxLayout(area_container)
    area_layout.setContentsMargins(0, 0, 0, 0)

    area_header = QHBoxLayout()
    area_title = QLabel("Areas")
    area_title.setStyleSheet("font-weight: 600;")
    window.location_panel_area_count_label = QLabel("0 areas")
    window.location_panel_area_count_label.setStyleSheet("color: #9CA3AF;")
    window.location_panel_area_zoom_button = QPushButton("Zoom")
    window.location_panel_area_delete_button = QPushButton("Delete")
    area_header.addWidget(area_title)
    area_header.addWidget(window.location_panel_area_count_label)
    area_header.addStretch(1)
    area_header.addWidget(window.location_panel_area_zoom_button)
    area_header.addWidget(window.location_panel_area_delete_button)
    area_layout.addLayout(area_header)

    window.location_panel_area_list = QListWidget(area_container)
    window.location_panel_area_list.setSelectionMode(
        QListWidget.SelectionMode.SingleSelection
    )
    area_layout.addWidget(window.location_panel_area_list)

    area_form = QFormLayout()
    window.location_panel_area_name_input = QLineEdit(area_container)
    window.location_panel_area_text_input = QLineEdit(area_container)
    window.location_panel_area_enabled_checkbox = QCheckBox("Enabled")
    window.location_panel_area_enabled_checkbox.setChecked(True)
    area_form.addRow("Name", window.location_panel_area_name_input)
    area_form.addRow("Custom text", window.location_panel_area_text_input)
    area_form.addRow("", window.location_panel_area_enabled_checkbox)
    area_layout.addLayout(area_form)

    window.location_panel_area_assign_button = QPushButton("Assign selected")
    window.location_panel_area_assign_button.setToolTip(
        "Assign selected images without GPS to this area"
    )
    window.location_panel_area_clear_button = QPushButton("Clear manual")
    window.location_panel_area_clear_button.setToolTip(
        "Clear manual location for selected images"
    )
    assign_row = QHBoxLayout()
    assign_row.addWidget(window.location_panel_area_assign_button)
    assign_row.addWidget(window.location_panel_area_clear_button)
    assign_row.addStretch(1)
    area_layout.addLayout(assign_row)

    window.location_panel_view = QWebEngineView(panel_container)
    window.location_panel_page = _LocationPanelPage(window, window.location_panel_view)
    window.location_panel_view.setPage(window.location_panel_page)
    window.location_panel_view.setMinimumHeight(220)
    window.location_panel_view.settings().setAttribute(
        QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls,
        True,
    )

    split = QSplitter(Qt.Orientation.Vertical, panel_container)
    split.setChildrenCollapsible(False)
    split.addWidget(area_container)
    split.addWidget(window.location_panel_view)
    split.setStretchFactor(0, 2)
    split.setStretchFactor(1, 6)
    panel_layout.addWidget(split, 1)
    window.location_panel_splitter = split
    window.location_panel_splitter_defaults = _default_location_panel_splitter_sizes(
        window
    )
    _apply_location_panel_splitter_sizes(
        window,
        window.ui_settings.value("ui/location_panel_splitter_sizes"),
        fallback=window.location_panel_splitter_defaults,
    )
    window.location_panel_splitter_filter = _SplitterResetFilter(window)
    for index in range(split.count() - 1):
        split.handle(index).installEventFilter(window.location_panel_splitter_filter)

    dock.setWidget(panel_container)
    window.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)
    window.location_areas_dock = dock

    channel = QWebChannel(window.location_panel_view.page())
    bridge = LocationAreasPanelBridge(window)
    channel.registerObject("bridge", bridge)
    window.location_panel_view.page().setWebChannel(channel)
    window.location_panel_channel = channel
    window.location_panel_bridge = bridge


    window.location_panel_refresh_button.clicked.connect(
        window.refresh_location_areas_panel
    )
    window.location_panel_clear_highlight_button.clicked.connect(
        lambda: _clear_map_selection(window)
    )
    window.location_panel_view.loadStarted.connect(
        lambda: window.location_panel_status_label.setText("Map loading...")
    )
    window.location_panel_view.loadFinished.connect(
        lambda ok: window.location_panel_status_label.setText(
            "Map loaded" if ok else "Map failed to load"
        )
    )

    def on_area_selection_changed() -> None:
        if window.location_panel_syncing:
            return
        item = window.location_panel_area_list.currentItem()
        if item is None:
            window.location_panel_selected_area_id = None
            _set_area_form_enabled(window, False)
            return
        area_id = item.data(Qt.ItemDataRole.UserRole)
        window.location_panel_selected_area_id = area_id
        window.select_location_area(area_id)
        _load_selected_area_into_form(window)

    window.location_panel_area_list.currentItemChanged.connect(
        lambda _current, _prev: on_area_selection_changed()
    )

    window.location_panel_area_name_input.editingFinished.connect(
        lambda: _update_selected_area_field(window)
    )
    window.location_panel_area_text_input.editingFinished.connect(
        lambda: _update_selected_area_field(window)
    )
    window.location_panel_area_enabled_checkbox.toggled.connect(
        lambda _checked: _update_selected_area_field(window)
    )
    window.location_panel_area_delete_button.clicked.connect(
        lambda: _delete_selected_area(window)
    )
    window.location_panel_area_zoom_button.clicked.connect(
        lambda: _zoom_selected_area(window)
    )
    window.location_panel_area_assign_button.clicked.connect(
        lambda: _assign_selected_images_to_area(window)
    )
    window.location_panel_area_clear_button.clicked.connect(
        lambda: _clear_manual_location_for_selected_images(window)
    )

    window.location_panel_splitter.splitterMoved.connect(
        lambda _pos, _index: _store_location_panel_splitter_sizes(window)
    )

    html = """<!DOCTYPE html>
<html>
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
  <title>Location Areas</title>
    <link
        rel=\"stylesheet\"
        href=\"https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.css\"
        crossorigin=\"\"
    />
    <link
        rel=\"stylesheet\"
        href=\"https://cdnjs.cloudflare.com/ajax/libs/leaflet.markercluster/1.5.3/MarkerCluster.Default.css\"
        crossorigin=\"\"
    />
    <link
        rel=\"stylesheet\"
        href=\"https://cdnjs.cloudflare.com/ajax/libs/leaflet.draw/1.0.4/leaflet.draw.css\"
        crossorigin=\"\"
    />
  <style>
    html, body { height: 100%; margin: 0; }
    #map { height: 100%; width: 100%; }
    .leaflet-container { background: #111; }
    #empty { position: absolute; top: 10px; right: 12px; z-index: 900; color: #9CA3AF; font: 12px sans-serif; }
        .photo-marker {
            background: #93c5fd;
            border: 1px solid #60a5fa;
            border-radius: 50%;
            width: 8px;
            height: 8px;
            box-shadow: 0 0 0 rgba(249, 115, 22, 0);
        }
        .photo-marker-selected {
            background: #fdba74;
            border: 2px solid #f97316;
            border-radius: 50%;
            width: 12px;
            height: 12px;
            box-shadow: 0 0 8px rgba(249, 115, 22, 0.65);
        }
        .photo-marker-pulse {
            background: #fdba74;
            border: 2px solid #f97316;
            border-radius: 50%;
            width: 14px;
            height: 14px;
            box-shadow: 0 0 12px rgba(249, 115, 22, 0.9);
        }
  </style>
</head>
<body>
  <div id=\"map\"></div>
  <div id=\"empty\"></div>

  <script src=\"qrc:///qtwebchannel/qwebchannel.js\"></script>
    <script
        src=\"https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.js\"
        crossorigin=\"\"
    ></script>
    <script
        src=\"https://cdnjs.cloudflare.com/ajax/libs/leaflet.markercluster/1.5.3/leaflet.markercluster.js\"
        crossorigin=\"\"
    ></script>
    <script
        src=\"https://cdnjs.cloudflare.com/ajax/libs/leaflet.draw/1.0.4/leaflet.draw.js\"
        crossorigin=\"\"
    ></script>

  <script>
        const emptyEl = document.getElementById("empty");
        window.onerror = (message) => {
            emptyEl.textContent = `Map error: ${message}`;
        };
        if (typeof L === "undefined") {
            emptyEl.textContent = "Map error: Leaflet not loaded";
        }
        const map = L.map("map").setView([59.3, 18.1], 11);
        emptyEl.textContent = "Map ready";
        L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
            maxZoom: 19,
            attribution: "&copy; OpenStreetMap",
        }).addTo(map);

    const createClusterGroup = () => {
      if (L.markerClusterGroup) {
        return L.markerClusterGroup({ showCoverageOnHover: false, maxClusterRadius: 48 });
      }
      return L.layerGroup();
    };

        const drawnItems = new L.FeatureGroup();
    map.addLayer(drawnItems);

        let hasUserView = false;
        const markUserView = () => {
            hasUserView = true;
        };
        map.on("dragstart", markUserView);
        map.on("zoomstart", markUserView);

        if (L.Control && L.Control.Draw) {
            const drawControl = new L.Control.Draw({
                edit: { featureGroup: drawnItems },
                draw: {
                    polygon: true,
                    rectangle: true,
                    circle: true,
                    polyline: false,
                    marker: false,
                    circlemarker: false,
                },
            });
            map.addControl(drawControl);
            const editHandler = new L.EditToolbar.Edit(map, {
                featureGroup: drawnItems,
            });
            editHandler.enable();
        } else {
            console.error("Leaflet.draw not available");
            emptyEl.textContent = "Map error: Leaflet.draw not available";
        }

    let clusterGroup = createClusterGroup();
    map.addLayer(clusterGroup);
    const markers = new Map();

        let selectedAreaId = null;
        let selectedEntryId = null;
        let pinMode = false;
        let pulseTimer = null;

        const baseIcon = L.divIcon({
            className: "photo-marker",
            iconSize: [8, 8],
        });
        const selectedIcon = L.divIcon({
            className: "photo-marker-selected",
            iconSize: [12, 12],
        });
        const pulseIcon = L.divIcon({
            className: "photo-marker-pulse",
            iconSize: [14, 14],
        });

    const updateLayerStyle = (layer) => {
      const enabled = layer._areaEnabled !== false;
      const isSelected = selectedAreaId && layer._areaId === selectedAreaId;
      layer.setStyle({
        color: enabled ? "#ff9100" : "#6b7280",
        fillColor: enabled ? "#ffb74d" : "#6b7280",
        fillOpacity: enabled ? 0.18 : 0.08,
        weight: isSelected ? 3 : enabled ? 2 : 1,
      });
      const label = layer._areaName || "Area";
      layer.bindTooltip(label, { sticky: true });
    };

        const saveAreas = () => {
            const areas = [];
            drawnItems.eachLayer((layer) => {
                const name = layer._areaName || "Area";
                const text = layer._areaText || "";
                const enabled = layer._areaEnabled !== false;
                const areaId = layer._areaId || "";

                if (layer instanceof L.Circle) {
                    const center = layer.getLatLng();
                    const radius = layer.getRadius();
                    areas.push({
                        id: areaId,
                        name,
                        text,
                        enabled,
                        shape: "circle",
                        center: [center.lat, center.lng],
                        radius_m: radius,
                    });
                    return;
                }

                if (layer instanceof L.Rectangle) {
                    const bounds = layer.getBounds();
                    const sw = bounds.getSouthWest();
                    const ne = bounds.getNorthEast();
                    areas.push({
                        id: areaId,
                        name,
                        text,
                        enabled,
                        shape: "rectangle",
                        bounds: [[sw.lat, sw.lng], [ne.lat, ne.lng]],
                        polygon: layer.getLatLngs()[0].map((pt) => [pt.lat, pt.lng]),
                    });
                    return;
                }

                const latlngs = layer.getLatLngs();
                if (!latlngs || !latlngs.length) {
                    return;
                }
                const polygon = latlngs[0].map((pt) => [pt.lat, pt.lng]);
                if (polygon.length < 3) {
                    return;
                }
                areas.push({
                    id: areaId,
                    name,
                    text,
                    enabled,
                    shape: "polygon",
                    polygon,
                });
            });
            if (window.bridge) {
                window.bridge.save_areas(JSON.stringify(areas));
            }
        };

        const addAreaLayer = (area) => {
            if (!area) {
                return;
            }
            const shape = (area.shape || "polygon").toLowerCase();
            let layer = null;
            if (shape === "circle") {
                const center = area.center;
                const radius = area.radius_m;
                if (!Array.isArray(center) || center.length !== 2 || !radius) {
                    return;
                }
                layer = L.circle(center, { radius: radius });
            } else if (shape === "rectangle") {
                if (Array.isArray(area.bounds) && area.bounds.length === 2) {
                    layer = L.rectangle(area.bounds);
                } else if (Array.isArray(area.polygon) && area.polygon.length >= 3) {
                    layer = L.rectangle(L.latLngBounds(area.polygon));
                } else {
                    return;
                }
            } else {
                if (!area.polygon || area.polygon.length < 3) {
                    return;
                }
                layer = L.polygon(area.polygon);
            }

            layer._areaId = area.id || "";
            layer._areaName = area.name || "Area";
            layer._areaText = area.text || "";
            layer._areaEnabled = area.enabled !== false;
            layer._areaShape = shape;
            layer.on("click", () => {
                if (window.bridge) {
                    window.bridge.select_area(layer._areaId || "");
                }
            });
            updateLayerStyle(layer);
            drawnItems.addLayer(layer);
        };

        const addPoints = (points) => {
      clusterGroup.clearLayers();
      markers.clear();
      if (!Array.isArray(points)) {
        return;
      }
      points.forEach((point) => {
                const lat = Number(point.lat);
                const lon = Number(point.lon);
                if (!Number.isFinite(lat) || !Number.isFinite(lon)) {
                    return;
                }
                                const marker = L.marker([lat, lon], { icon: baseIcon });
        if (point.name) {
          marker.bindTooltip(point.name, { sticky: true });
        }
        marker.on("click", () => {
          if (window.bridge && point.id) {
            window.bridge.select_entry(point.id);
          }
        });
        clusterGroup.addLayer(marker);
                if (point.id) {
                    markers.set(point.id, marker);
                    if (selectedEntryId && point.id === selectedEntryId) {
                        marker.setIcon(selectedIcon);
                    }
                }
      });
    };

        const stopPulse = () => {
            if (pulseTimer) {
                clearInterval(pulseTimer);
                pulseTimer = null;
            }
        };

        const startPulse = (marker) => {
            stopPulse();
            if (!marker) {
                return;
            }
            let grow = true;
            pulseTimer = setInterval(() => {
                if (grow) {
                    marker.setIcon(pulseIcon);
                } else {
                    marker.setIcon(selectedIcon);
                }
                grow = !grow;
            }, 520);
        };

        const applySelectedMarkerStyle = () => {
            let selectedMarker = null;
            markers.forEach((marker, entryId) => {
                if (selectedEntryId && entryId === selectedEntryId) {
                    marker.setIcon(selectedIcon);
                    selectedMarker = marker;
                } else {
                    marker.setIcon(baseIcon);
                }
            });
            startPulse(selectedMarker);
        };

    const fitToContent = () => {
      const layers = [];
      clusterGroup.eachLayer((layer) => layers.push(layer));
      drawnItems.eachLayer((layer) => layers.push(layer));
      if (!layers.length) {
        return;
      }
      const group = L.featureGroup(layers);
      map.fitBounds(group.getBounds().pad(0.2));
    };

        const updateEmpty = (state) => {
            let count = 0;
            clusterGroup.eachLayer(() => { count += 1; });
            const total = state && typeof state.total === "number" ? state.total : 0;
            const gps = state && typeof state.gps === "number" ? state.gps : count;
            if (count === 0) {
                emptyEl.textContent = `No GPS points loaded (${gps}/${total})`;
            } else {
                emptyEl.textContent = `Points: ${count} (${gps}/${total})`;
            }
        };

        window.setMapState = (payload) => {
      let state = { points: [], areas: [] };
      try {
        state = JSON.parse(payload);
      } catch (error) {
        state = { points: [], areas: [] };
      }
            console.log(`setMapState points=${(state.points || []).length} areas=${(state.areas || []).length}`);
      drawnItems.clearLayers();
      if (Array.isArray(state.areas)) {
        state.areas.forEach((area) => addAreaLayer(area));
      }
      addPoints(state.points || []);
      if (selectedAreaId) {
        drawnItems.eachLayer((layer) => updateLayerStyle(layer));
      }
            applySelectedMarkerStyle();
            if (!hasUserView) {
                fitToContent();
                hasUserView = true;
            }
            updateEmpty(state);
    };

        window.selectEntry = (entryId) => {
            selectedEntryId = entryId || null;
            applySelectedMarkerStyle();
        };

        window.clearSelectedEntry = () => {
            selectedEntryId = null;
            applySelectedMarkerStyle();
        };

        window.focusMarker = (entryId) => {
            window.selectEntry(entryId);
            const marker = markers.get(entryId);
      if (!marker) {
        return;
      }
      if (clusterGroup.zoomToShowLayer) {
                clusterGroup.zoomToShowLayer(marker, () => {
                    map.setView(marker.getLatLng(), Math.max(15, map.getZoom()));
                    marker.setIcon(selectedIcon);
                });
      } else {
                map.setView(marker.getLatLng(), Math.max(15, map.getZoom()));
      }
    };

    window.selectArea = (areaId) => {
      selectedAreaId = areaId || null;
      drawnItems.eachLayer((layer) => updateLayerStyle(layer));
    };

    window.zoomToArea = (areaId) => {
      let target = null;
      drawnItems.eachLayer((layer) => {
        if (layer._areaId === areaId) {
          target = layer;
        }
      });
      if (target) {
        map.fitBounds(target.getBounds().pad(0.2));
      }
    };

    window.setPinMode = (enabled) => {
      pinMode = !!enabled;
    };

    map.on(L.Draw.Event.CREATED, (event) => {
      const layer = event.layer;
      layer._areaId = "area_" + Math.random().toString(36).slice(2);
      layer._areaEnabled = true;
      layer._areaName = "Area";
            const promptedText = window.prompt("Custom text for this area (optional):", "");
            if (promptedText !== null) {
                layer._areaText = String(promptedText).trim();
            } else {
                layer._areaText = "";
            }
            if (layer instanceof L.Circle) {
                layer._areaShape = "circle";
            } else if (layer instanceof L.Rectangle) {
                layer._areaShape = "rectangle";
            } else {
                layer._areaShape = "polygon";
            }
      drawnItems.addLayer(layer);
            selectedAreaId = layer._areaId;
            updateLayerStyle(layer);
            if (window.bridge) {
                window.bridge.select_area(layer._areaId);
            }
      saveAreas();
    });

    map.on(L.Draw.Event.EDITED, () => {
      saveAreas();
    });

    map.on(L.Draw.Event.DELETED, () => {
      saveAreas();
    });

    map.on("click", (event) => {
      if (!pinMode || !window.bridge) {
        return;
      }
      window.bridge.set_manual_location(event.latlng.lat, event.latlng.lng);
    });

        new QWebChannel(qt.webChannelTransport, (channel) => {
      window.bridge = channel.objects.bridge;
      const stateJson = window.bridge.get_initial_state();
            console.log(`bridge ready, state bytes=${stateJson.length}`);
      window.setMapState(stateJson);
      window.bridge.map_ready();
    });
  </script>
</body>
</html>
"""

    window.location_panel_view.setHtml(html)
    window.refresh_location_areas_panel()


def _set_area_form_enabled(window: Any, enabled: bool) -> None:
    window.location_panel_area_name_input.setEnabled(enabled)
    window.location_panel_area_text_input.setEnabled(enabled)
    window.location_panel_area_enabled_checkbox.setEnabled(enabled)
    window.location_panel_area_delete_button.setEnabled(enabled)
    window.location_panel_area_zoom_button.setEnabled(enabled)
    window.location_panel_area_assign_button.setEnabled(enabled)
    window.location_panel_area_clear_button.setEnabled(enabled)


def _selected_paths(window: Any) -> list[Any]:
    selection = window.image_table.selectionModel()
    rows = []
    if selection is not None:
        rows = [index.row() for index in selection.selectedRows()]
    rows.sort()

    paths: list[Any] = []
    seen: set[Any] = set()
    for row in rows:
        if row < 0 or row >= len(window.image_paths):
            continue
        path = window.image_paths[row]
        if path in seen:
            continue
        seen.add(path)
        paths.append(path)

    if paths:
        return paths

    current = window.selected_path()
    if current is None:
        return []
    return [current]


def _polygon_centroid(points: list[list[float]]) -> tuple[float, float] | None:
    if len(points) < 3:
        return None
    area = 0.0
    centroid_lat = 0.0
    centroid_lon = 0.0
    count = len(points)
    for i in range(count):
        lat1, lon1 = points[i]
        lat2, lon2 = points[(i + 1) % count]
        cross = lat1 * lon2 - lat2 * lon1
        area += cross
        centroid_lat += (lat1 + lat2) * cross
        centroid_lon += (lon1 + lon2) * cross

    area *= 0.5
    if abs(area) < 1e-9:
        avg_lat = sum(lat for lat, _lon in points) / len(points)
        avg_lon = sum(lon for _lat, lon in points) / len(points)
        return avg_lat, avg_lon

    factor = 1.0 / (6.0 * area)
    return centroid_lat * factor, centroid_lon * factor


def _area_anchor_location(area: dict[str, object]) -> tuple[float, float] | None:
    shape = str(area.get("shape", "polygon")).strip().lower()
    if shape == "circle":
        center = area.get("center")
        if isinstance(center, (list, tuple)) and len(center) == 2:
            return float(center[0]), float(center[1])
        return None

    if shape == "rectangle":
        bounds = area.get("bounds")
        if isinstance(bounds, (list, tuple)) and len(bounds) == 2:
            try:
                south = float(bounds[0][0])
                west = float(bounds[0][1])
                north = float(bounds[1][0])
                east = float(bounds[1][1])
            except (TypeError, ValueError, IndexError):
                return None
            return (south + north) / 2.0, (west + east) / 2.0

    polygon = area.get("polygon")
    if isinstance(polygon, list) and len(polygon) >= 3:
        try:
            points = [[float(pt[0]), float(pt[1])] for pt in polygon]
        except (TypeError, ValueError, IndexError):
            return None
        return _polygon_centroid(points)
    return None


def _assign_selected_images_to_area(window: Any) -> None:
    area_id = window.location_panel_selected_area_id
    if not area_id:
        QMessageBox.information(window, "Assign to Area", "Select an area first.")
        return

    areas = window.location_areas_for_window()
    area = _area_lookup(areas).get(area_id)
    if area is None:
        QMessageBox.information(window, "Assign to Area", "Selected area not found.")
        return

    anchor = _area_anchor_location(area)
    if anchor is None:
        QMessageBox.information(
            window, "Assign to Area", "Could not determine area center."
        )
        return

    paths = _selected_paths(window)
    if not paths:
        QMessageBox.information(
            window, "Assign to Area", "Select one or more images first."
        )
        return

    latitude, longitude = anchor
    applied = 0
    skipped = 0
    for path in paths:
        if window.location_for_path(path) is not None:
            skipped += 1
            continue
        _set_manual_location(
            window,
            path,
            latitude=latitude,
            longitude=longitude,
            record_pin=True,
        )
        applied += 1

    if applied:
        window.refresh_preview()
        window.refresh_image_list_labels(window.selected_path())
        window.refresh_location_areas_panel()

    if applied and skipped:
        message = f"Assigned {applied} image(s). Skipped {skipped} with GPS."
    elif applied:
        message = f"Assigned {applied} image(s) to the selected area."
    else:
        message = "No images without GPS were selected."

    QMessageBox.information(window, "Assign to Area", message)


def _clear_manual_location_for_selected_images(window: Any) -> None:
    paths = _selected_paths(window)
    if not paths:
        QMessageBox.information(
            window, "Clear Manual Location", "Select one or more images first."
        )
        return

    cleared = 0
    skipped = 0
    for path in paths:
        if _manual_location_for_path(window, path) is None:
            skipped += 1
            continue
        _set_manual_location(
            window,
            path,
            latitude=None,
            longitude=None,
            record_pin=False,
        )
        cleared += 1

    if cleared:
        window.refresh_preview()
        window.refresh_image_list_labels(window.selected_path())
        window.refresh_location_areas_panel()

    if cleared and skipped:
        message = f"Cleared {cleared} manual location(s). Skipped {skipped}."
    elif cleared:
        message = f"Cleared {cleared} manual location(s)."
    else:
        message = "No manual locations found in the selection."

    QMessageBox.information(window, "Clear Manual Location", message)


def _load_selected_area_into_form(window: Any) -> None:
    areas = window.location_areas_for_window()
    lookup = _area_lookup(areas)
    area_id = window.location_panel_selected_area_id
    area = lookup.get(area_id or "")
    if area is None:
        window.location_panel_syncing = True
        window.location_panel_area_name_input.setText("")
        window.location_panel_area_text_input.setText("")
        window.location_panel_area_enabled_checkbox.setChecked(False)
        window.location_panel_syncing = False
        _set_area_form_enabled(window, False)
        return

    window.location_panel_syncing = True
    window.location_panel_area_name_input.setText(str(area.get("name", "")))
    window.location_panel_area_text_input.setText(str(area.get("text", "")))
    window.location_panel_area_enabled_checkbox.setChecked(
        bool(area.get("enabled", True))
    )
    window.location_panel_syncing = False
    _set_area_form_enabled(window, True)


def _update_selected_area_field(window: Any) -> None:
    if window.location_panel_syncing:
        return
    area_id = window.location_panel_selected_area_id
    if not area_id:
        return
    areas = window.location_areas_for_window()
    lookup = _area_lookup(areas)
    area = lookup.get(area_id)
    if area is None:
        return

    area["name"] = window.location_panel_area_name_input.text().strip() or "Area"
    area["text"] = window.location_panel_area_text_input.text().strip()
    area["enabled"] = bool(window.location_panel_area_enabled_checkbox.isChecked())
    window.store_location_areas(list(lookup.values()))
    window.refresh_location_areas_panel()


def _delete_selected_area(window: Any) -> None:
    area_id = window.location_panel_selected_area_id
    if not area_id:
        return
    areas = [
        area
        for area in window.location_areas_for_window()
        if str(area.get("id", "")) != area_id
    ]
    window.store_location_areas(areas)
    window.location_panel_selected_area_id = None
    window.refresh_location_areas_panel()


def _zoom_selected_area(window: Any) -> None:
    area_id = window.location_panel_selected_area_id
    if not area_id or not window.location_panel_map_ready:
        return
    payload = json.dumps(area_id)
    window.location_panel_view.page().runJavaScript(
        "window.zoomToArea(%s);" % payload
    )


def _set_pin_mode(window: Any, enabled: bool) -> None:
    window.location_panel_pin_mode = bool(enabled)
    window.location_panel_pin_hint.setVisible(enabled)
    if window.location_panel_map_ready:
        payload = "true" if enabled else "false"
        window.location_panel_view.page().runJavaScript(
            "window.setPinMode(%s);" % payload
        )


def _store_manual_location(
    window: Any, path: Any, latitude: float, longitude: float
) -> None:
    _set_manual_location(
        window,
        path,
        latitude=latitude,
        longitude=longitude,
        record_pin=True,
    )


def _clear_manual_location_for_selected(window: Any) -> None:
    path = window.location_panel_selected_path or window.selected_path()
    if path is None:
        return
    entry = window.ensure_photo_entry_for_path(path)
    if isinstance(entry.get("manual_location"), dict):
        del entry["manual_location"]
        window.location_cache.pop(path, None)
        window.save_folder_metadata()
        window.sync_global_source_state_from_path(path)
        window.invalidate_table_cache_for_path(path)
        window.refresh_preview()
        window.refresh_image_list_labels(path)
        window.refresh_location_areas_panel()


def _record_recent_pin(
    window: Any,
    path: Any,
    latitude: float,
    longitude: float,
    previous_manual: dict[str, object] | None,
) -> None:
    entry_id = window.metadata_key_for_path(path)
    pins = _recent_pins_for_window(window)
    pins = [pin for pin in pins if pin.get("id") != entry_id]
    pins.insert(
        0,
        {
            "id": entry_id,
            "name": path.name,
            "timestamp": datetime.now().isoformat(timespec="minutes"),
            "latitude": latitude,
            "longitude": longitude,
            "previous_manual": previous_manual,
        },
    )
    window.folder_metadata["recent_pins"] = pins[:20]


def _load_recent_pins(window: Any) -> None:
    pins = _recent_pins_for_window(window)
    window.location_panel_syncing = True
    window.location_panel_recent_list.clear()
    for pin in pins:
        name = str(pin.get("name", "")).strip()
        timestamp = str(pin.get("timestamp", "")).strip()
        label = f"{name} ({timestamp})" if timestamp else name
        item = QListWidgetItem(label)
        item.setData(Qt.ItemDataRole.UserRole, pin.get("id"))
        window.location_panel_recent_list.addItem(item)
    window.location_panel_syncing = False
    window.location_panel_recent_undo_button.setEnabled(bool(pins))
    window.location_panel_recent_edit_button.setEnabled(
        window.location_panel_recent_list.currentItem() is not None
    )


def _clear_recent_pins(window: Any) -> None:
    window.folder_metadata["recent_pins"] = []
    window.save_folder_metadata()
    window.refresh_location_areas_panel()


def _default_location_panel_splitter_sizes(window: Any) -> list[int]:
    total = 0
    if hasattr(window, "location_areas_dock"):
        total = window.location_areas_dock.height()
    if total <= 0:
        screen = window.screen()
        if screen is not None:
            total = screen.availableGeometry().height()
    if total <= 0:
        total = 900

    if total < 720:
        ratios = [0.3, 0.7]
    else:
        ratios = [0.25, 0.75]

    sizes = [max(120, int(total * ratio)) for ratio in ratios]
    return sizes


def _apply_location_panel_splitter_sizes(
    window: Any,
    raw_sizes: object,
    *,
    fallback: list[int],
) -> None:
    sizes: list[int] = []
    if isinstance(raw_sizes, list):
        for value in raw_sizes:
            try:
                parsed = int(value)
            except (TypeError, ValueError):
                continue
            if parsed > 0:
                sizes.append(parsed)
    if len(sizes) == 2:
        window.location_panel_splitter.setSizes(sizes)
    else:
        window.location_panel_splitter.setSizes(fallback)


def _store_location_panel_splitter_sizes(window: Any) -> None:
    if not hasattr(window, "ui_settings"):
        return
    window.ui_settings.setValue(
        "ui/location_panel_splitter_sizes",
        window.location_panel_splitter.sizes(),
    )


def _reset_location_panel_splitter(window: Any) -> None:
    if not hasattr(window, "location_panel_splitter_defaults"):
        return
    window.location_panel_splitter.setSizes(
        list(window.location_panel_splitter_defaults)
    )
    _store_location_panel_splitter_sizes(window)


def _set_manual_location(
    window: Any,
    path: Any,
    *,
    latitude: float | None,
    longitude: float | None,
    record_pin: bool,
) -> None:
    entry = window.ensure_photo_entry_for_path(path)
    previous_manual = entry.get("manual_location")
    previous_payload = None
    if isinstance(previous_manual, dict):
        prev_lat = previous_manual.get("latitude")
        prev_lon = previous_manual.get("longitude")
        try:
            prev_lat = float(prev_lat)
            prev_lon = float(prev_lon)
        except (TypeError, ValueError):
            previous_payload = None
        else:
            previous_payload = {
                "latitude": prev_lat,
                "longitude": prev_lon,
                "updated_at": previous_manual.get("updated_at", ""),
            }

    if latitude is None or longitude is None:
        entry.pop("manual_location", None)
        window.location_cache.pop(path, None)
    else:
        entry["manual_location"] = {
            "latitude": float(latitude),
            "longitude": float(longitude),
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        }
        window.location_cache[path] = (float(latitude), float(longitude))
        if record_pin:
            _record_recent_pin(
                window,
                path,
                float(latitude),
                float(longitude),
                previous_payload,
            )

    window.save_folder_metadata()
    window.sync_global_source_state_from_path(path)
    window.invalidate_table_cache_for_path(path)


def _undo_last_pin_change(window: Any) -> None:
    pins = _recent_pins_for_window(window)
    if not pins:
        return
    per_image = bool(window.location_panel_recent_scope_checkbox.isChecked())
    entry_id = ""
    if per_image:
        entry_id = _selected_recent_entry_id(window)
    if not entry_id:
        entry_id = str(pins[0].get("id", "")).strip()

    last = next((pin for pin in pins if pin.get("id") == entry_id), pins[0])
    path = _path_for_entry_id(window, str(last.get("id", "")).strip())
    if path is None:
        return
    previous = last.get("previous_manual")
    if isinstance(previous, dict):
        try:
            latitude = float(previous.get("latitude"))
            longitude = float(previous.get("longitude"))
        except (TypeError, ValueError):
            latitude = None
            longitude = None
    else:
        latitude = None
        longitude = None

    _set_manual_location(
        window,
        path,
        latitude=latitude,
        longitude=longitude,
        record_pin=False,
    )
    if last is pins[0]:
        window.folder_metadata["recent_pins"] = pins[1:]
    else:
        window.folder_metadata["recent_pins"] = [
            pin for pin in pins if pin.get("id") != last.get("id")
        ]
    window.save_folder_metadata()
    window.refresh_preview()
    window.refresh_image_list_labels(path)
    window.refresh_location_areas_panel()


def _edit_selected_recent_pin(window: Any) -> None:
    entry_id = _selected_recent_entry_id(window)
    if not entry_id:
        return
    pins = _recent_pins_for_window(window)
    pin = next((p for p in pins if p.get("id") == entry_id), None)
    if pin is None:
        return
    path = _path_for_entry_id(window, entry_id)
    if path is None:
        return

    dialog = QDialog(window)
    dialog.setWindowTitle("Edit Pin")
    layout = QFormLayout(dialog)
    lat_input = QDoubleSpinBox(dialog)
    lon_input = QDoubleSpinBox(dialog)
    lat_input.setRange(-90.0, 90.0)
    lon_input.setRange(-180.0, 180.0)
    lat_input.setDecimals(6)
    lon_input.setDecimals(6)
    lat_input.setValue(float(pin.get("latitude") or 0.0))
    lon_input.setValue(float(pin.get("longitude") or 0.0))
    layout.addRow("Latitude", lat_input)
    layout.addRow("Longitude", lon_input)

    buttons = QDialogButtonBox(
        QDialogButtonBox.StandardButton.Ok
        | QDialogButtonBox.StandardButton.Cancel,
        dialog,
    )
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    layout.addRow(buttons)

    if dialog.exec() != QDialog.DialogCode.Accepted:
        return

    latitude = float(lat_input.value())
    longitude = float(lon_input.value())
    _set_manual_location(
        window,
        path,
        latitude=latitude,
        longitude=longitude,
        record_pin=True,
    )
    window.refresh_preview()
    window.refresh_image_list_labels(path)
    window.refresh_location_areas_panel()
    window.focus_location_areas_panel_for_path(path)


def _show_recent_pin_preview(window: Any, item: QListWidgetItem) -> None:
    if item is None:
        return
    entry_id = item.data(Qt.ItemDataRole.UserRole)
    if not entry_id:
        return
    path = _path_for_entry_id(window, entry_id)
    if path is None:
        return
    url = _file_url_for_path(path)
    if not url:
        return
    size = int(window.location_panel_recent_preview_slider.value())
    tooltip = (
        "<div style='text-align:center;'>"
        f"<img src='{url}' width='{size}' /><br />"
        f"{path.name}"
        "</div>"
    )
    QToolTip.showText(QCursor.pos(), tooltip, window.location_panel_recent_list)


def _clear_map_selection(window: Any) -> None:
    if not window.location_panel_map_ready:
        return
    window.location_panel_view.page().runJavaScript("window.clearSelectedEntry();")


def _selected_recent_entry_id(window: Any) -> str:
    item = window.location_panel_recent_list.currentItem()
    if item is None:
        return ""
    entry_id = item.data(Qt.ItemDataRole.UserRole)
    return str(entry_id or "")


def refresh_location_areas_panel(window: Any) -> None:
    if not hasattr(window, "location_panel_view"):
        return

    entries = _build_location_panel_entries(window)
    total = len(entries)
    gps_count = sum(1 for entry in entries if entry.has_gps)
    no_gps_count = sum(1 for entry in entries if not entry.has_gps)
    window.location_panel_counts_label.setText(f"GPS {gps_count}/{total}")
    window.location_panel_no_gps_badge.setText(f"No GPS {no_gps_count}")

    areas = window.location_areas_for_window()
    window.location_panel_area_count_label.setText(f"{len(areas)} areas")
    _load_area_list(window, areas)

    payload = json.dumps(_panel_state_payload(window, entries))
    if window.location_panel_map_ready:
        window.location_panel_view.page().runJavaScript(
            "window.setMapState(%s);" % json.dumps(payload)
        )
        pending_entry = window.location_panel_pending_entry_id
        if pending_entry:
            window.location_panel_pending_entry_id = None
            pending_payload = json.dumps(pending_entry)
            window.location_panel_view.page().runJavaScript(
                "window.selectEntry(%s);" % pending_payload
            )
            window.location_panel_view.page().runJavaScript(
                "window.focusMarker(%s);" % pending_payload
            )
    else:
        window.location_panel_pending_state = payload


def _load_area_list(window: Any, areas: list[dict[str, object]]) -> None:
    window.location_panel_syncing = True
    window.location_panel_area_list.clear()
    selected_id = window.location_panel_selected_area_id
    selected_item = None
    for area in areas:
        area_id = str(area.get("id", "")).strip()
        name = str(area.get("name", "Area")).strip() or "Area"
        item = QListWidgetItem(name)
        item.setData(Qt.ItemDataRole.UserRole, area_id)
        window.location_panel_area_list.addItem(item)
        if selected_id and area_id == selected_id:
            selected_item = item
    if selected_item is not None:
        window.location_panel_area_list.setCurrentItem(selected_item)
    window.location_panel_syncing = False
    _load_selected_area_into_form(window)


def focus_location_areas_panel_for_path(window: Any, path: Any) -> None:
    if not hasattr(window, "location_panel_view"):
        return
    if path is None:
        return

    window.location_panel_selected_path = path
    entry_id = window.metadata_key_for_path(path)
    if window.location_panel_map_ready:
        payload = json.dumps(entry_id)
        window.location_panel_view.page().runJavaScript(
            "window.selectEntry(%s);" % payload
        )
        window.location_panel_view.page().runJavaScript(
            "window.focusMarker(%s);" % payload
        )
    else:
        window.location_panel_pending_entry_id = entry_id



def select_location_area(window: Any, area_id: str) -> None:
    if not area_id:
        return
    window.location_panel_selected_area_id = area_id
    if window.location_panel_map_ready:
        payload = json.dumps(area_id)
        window.location_panel_view.page().runJavaScript(
            "window.selectArea(%s);" % payload
        )

    window.location_panel_syncing = True
    for index in range(window.location_panel_area_list.count()):
        item = window.location_panel_area_list.item(index)
        if item.data(Qt.ItemDataRole.UserRole) == area_id:
            window.location_panel_area_list.setCurrentItem(item)
            break
    window.location_panel_syncing = False
    _load_selected_area_into_form(window)


def select_image_by_entry_id(window: Any, entry_id: str) -> None:
    if not entry_id:
        return
    for path in window.image_paths:
        if window.metadata_key_for_path(path) == entry_id:
            row = window.row_for_path(path)
            if row is not None:
                window.image_table.setCurrentCell(row, TABLE_COL_FILE)
                window.focus_location_areas_panel_for_path(path)
            return


def set_manual_location_for_selected(
    window: Any, latitude: float, longitude: float
) -> None:
    path = window.location_panel_selected_path or window.selected_path()
    if path is None:
        return
    _store_manual_location(window, path, latitude, longitude)
    window.location_panel_pin_button.setChecked(False)
    window.refresh_preview()
    window.refresh_image_list_labels(path)
    window.refresh_location_areas_panel()
    window.focus_location_areas_panel_for_path(path)


__all__ = [
    "focus_location_areas_panel_for_path",
    "refresh_location_areas_panel",
    "select_location_area",
    "select_image_by_entry_id",
    "set_manual_location_for_selected",
    "setup_location_areas_panel",
]