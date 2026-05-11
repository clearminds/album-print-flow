from __future__ import annotations

import json
from typing import Any

from PySide6.QtCore import QObject, Slot
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineCore import QWebEngineSettings
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QMessageBox,
    QVBoxLayout,
)

from album_print_flow.ui.location_area_flow import normalize_location_areas


class LocationAreasBridge(QObject):
    def __init__(self, window: Any) -> None:
        super().__init__()
        self._window = window

    @Slot(result=str)
    def get_initial_state(self) -> str:
        points: list[dict[str, object]] = []
        for path in self._window.image_paths:
            location = self._window.location_for_path(path)
            if location is None:
                continue
            latitude, longitude = location
            points.append(
                {
                    "lat": latitude,
                    "lon": longitude,
                    "name": path.name,
                }
            )

        areas = self._window.location_areas_for_window()
        payload = {"points": points, "areas": areas}
        return json.dumps(payload)

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


def open_location_areas_dialog(window: Any) -> None:
    if window.current_folder is None:
        QMessageBox.information(
            window,
            "Location Areas",
            "Load a folder or source before editing location areas.",
        )
        return

    dialog = QDialog(window)
    dialog.setWindowTitle("Location Areas")
    dialog.setModal(True)
    dialog.resize(980, 720)

    layout = QVBoxLayout(dialog)
    helper = QLabel(
        "Draw polygon areas on the map. Click an area to edit its name and text."
    )
    helper.setWordWrap(True)
    helper.setStyleSheet("color: #9CA3AF;")
    layout.addWidget(helper)

    view = QWebEngineView(dialog)
    view.settings().setAttribute(
        QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls,
        True,
    )
    layout.addWidget(view, 1)

    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close, dialog)
    buttons.rejected.connect(dialog.reject)
    buttons.accepted.connect(dialog.accept)
    layout.addWidget(buttons)

    channel = QWebChannel(view.page())
    bridge = LocationAreasBridge(window)
    channel.registerObject("bridge", bridge)
    view.page().setWebChannel(channel)

    dialog._location_areas_channel = channel
    dialog._location_areas_bridge = bridge

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
  </style>
</head>
<body>
  <div id=\"map\"></div>

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
    const map = L.map("map").setView([59.3, 18.1], 11);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: "&copy; OpenStreetMap",
    }).addTo(map);

    const drawnItems = new L.FeatureGroup();
    map.addLayer(drawnItems);

    const drawControl = new L.Control.Draw({
      edit: { featureGroup: drawnItems },
      draw: {
        polygon: true,
        rectangle: false,
        circle: false,
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

    const clusterGroup = L.markerClusterGroup({
      showCoverageOnHover: false,
      maxClusterRadius: 48,
    });
    map.addLayer(clusterGroup);

    const idSource = () => {
      if (window.crypto && window.crypto.randomUUID) {
        return window.crypto.randomUUID();
      }
      return "area_" + Math.random().toString(36).slice(2);
    };

    const updateLayerStyle = (layer) => {
      const enabled = layer._areaEnabled !== false;
      layer.setStyle({
        color: enabled ? "#ff9100" : "#6b7280",
        fillColor: enabled ? "#ffb74d" : "#6b7280",
        fillOpacity: enabled ? 0.18 : 0.08,
        weight: enabled ? 2 : 1,
      });
      const label = layer._areaName || "Area";
      layer.bindTooltip(label, { sticky: true });
    };

    const editLayerMeta = (layer, initial = false) => {
      const name = window.prompt("Area name", layer._areaName || "");
      if (name === null) {
        if (initial) {
          drawnItems.removeLayer(layer);
        }
        return false;
      }
      const text = window.prompt("Custom text", layer._areaText || "");
      if (text === null) {
        if (initial) {
          drawnItems.removeLayer(layer);
        }
        return false;
      }
      const enabled = window.confirm(
        "Enable this area? Click OK to enable or Cancel to disable."
      );
      layer._areaName = (name || "").trim() || "Area";
      layer._areaText = (text || "").trim();
      layer._areaEnabled = enabled;
      updateLayerStyle(layer);
      return true;
    };

    const saveAreas = () => {
      const areas = [];
      drawnItems.eachLayer((layer) => {
        const latlngs = layer.getLatLngs();
        if (!latlngs || !latlngs.length) {
          return;
        }
        const polygon = latlngs[0].map((pt) => [pt.lat, pt.lng]);
        if (polygon.length < 3) {
          return;
        }
        areas.push({
          id: layer._areaId || idSource(),
          name: layer._areaName || "Area",
          text: layer._areaText || "",
          enabled: layer._areaEnabled !== false,
          polygon,
        });
      });
      if (window.bridge) {
        window.bridge.save_areas(JSON.stringify(areas));
      }
    };

    map.on(L.Draw.Event.CREATED, (event) => {
      const layer = event.layer;
      layer._areaId = idSource();
      layer._areaEnabled = true;
      drawnItems.addLayer(layer);
      if (editLayerMeta(layer, true)) {
        saveAreas();
      }
    });

    map.on(L.Draw.Event.EDITED, () => {
      saveAreas();
    });

    map.on(L.Draw.Event.DELETED, () => {
      saveAreas();
    });

    const addAreaLayer = (area) => {
      if (!area || !area.polygon || area.polygon.length < 3) {
        return;
      }
      const layer = L.polygon(area.polygon);
      layer._areaId = area.id || idSource();
      layer._areaName = area.name || "Area";
      layer._areaText = area.text || "";
      layer._areaEnabled = area.enabled !== false;
      layer.on("click", () => {
        if (editLayerMeta(layer, false)) {
          saveAreas();
        }
      });
      updateLayerStyle(layer);
      drawnItems.addLayer(layer);
    };

    const addPoints = (points) => {
      if (!Array.isArray(points)) {
        return;
      }
      points.forEach((point) => {
        if (typeof point.lat !== "number" || typeof point.lon !== "number") {
          return;
        }
        const marker = L.circleMarker([point.lat, point.lon], {
          radius: 4,
          color: "#60a5fa",
          weight: 1,
          fillColor: "#93c5fd",
          fillOpacity: 0.7,
        });
        if (point.name) {
          marker.bindTooltip(point.name, { sticky: true });
        }
        clusterGroup.addLayer(marker);
      });
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

    new QWebChannel(qt.webChannelTransport, (channel) => {
      window.bridge = channel.objects.bridge;
      const stateJson = window.bridge.get_initial_state();
      let state = { points: [], areas: [] };
      try {
        state = JSON.parse(stateJson);
      } catch (error) {
        state = { points: [], areas: [] };
      }
      addPoints(state.points || []);
      (state.areas || []).forEach((area) => addAreaLayer(area));
      fitToContent();
    });
  </script>
</body>
</html>
"""

    view.setHtml(html)
    dialog.exec()


__all__ = ["open_location_areas_dialog"]
