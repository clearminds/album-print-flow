from __future__ import annotations

from PySide6.QtCore import QRect, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QLabel, QWidget


class PreviewLabel(QLabel):
    drag_started = Signal(int, int)
    dragged = Signal(int, int, int, int)
    drag_released = Signal(int, int)

    def __init__(
        self,
        text: str = "",
        parent: QWidget | None = None,
        *,
        reframe_handle_size: int = 14,
    ) -> None:
        super().__init__(text, parent)
        self._drag_enabled = False
        self._last_pos = None
        self._overlay_enabled = False
        self._overlay_rect: QRect | None = None
        self._reframe_handle_size = int(reframe_handle_size)

    def set_drag_enabled(self, enabled: bool) -> None:
        self._drag_enabled = enabled
        self._last_pos = None
        self.setCursor(
            Qt.CursorShape.OpenHandCursor if enabled else Qt.CursorShape.ArrowCursor
        )

    def set_overlay_enabled(self, enabled: bool) -> None:
        self._overlay_enabled = enabled
        self.update()

    def set_overlay_rect(self, rect: tuple[int, int, int, int] | None) -> None:
        if rect is None:
            self._overlay_rect = None
        else:
            x, y, width, height = rect
            self._overlay_rect = QRect(
                int(x), int(y), max(0, int(width)), max(0, int(height))
            )
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        super().paintEvent(event)
        if not self._overlay_enabled:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        full = self.rect()
        overlay = (
            self._overlay_rect.intersected(full) if self._overlay_rect else QRect()
        )

        mask_color = QColor(0, 0, 0, 120)
        if not overlay.isValid() or overlay.width() <= 0 or overlay.height() <= 0:
            painter.fillRect(full, mask_color)
            return

        if overlay.top() > full.top():
            painter.fillRect(
                QRect(
                    full.left(), full.top(), full.width(), overlay.top() - full.top()
                ),
                mask_color,
            )
        bottom_start = overlay.bottom() + 1
        if bottom_start <= full.bottom():
            painter.fillRect(
                QRect(
                    full.left(),
                    bottom_start,
                    full.width(),
                    full.bottom() - bottom_start + 1,
                ),
                mask_color,
            )
        if overlay.left() > full.left():
            painter.fillRect(
                QRect(
                    full.left(),
                    overlay.top(),
                    overlay.left() - full.left(),
                    overlay.height(),
                ),
                mask_color,
            )
        right_start = overlay.right() + 1
        if right_start <= full.right():
            painter.fillRect(
                QRect(
                    right_start,
                    overlay.top(),
                    full.right() - right_start + 1,
                    overlay.height(),
                ),
                mask_color,
            )

        pen = QPen(QColor("#FF9100"))
        pen.setWidth(2)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(overlay)

        handle_half = self._reframe_handle_size // 2
        handle_color = QColor("#FF9100")
        corners = [
            overlay.topLeft(),
            overlay.topRight(),
            overlay.bottomLeft(),
            overlay.bottomRight(),
        ]
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(handle_color)
        for point in corners:
            painter.drawRect(
                point.x() - handle_half,
                point.y() - handle_half,
                self._reframe_handle_size,
                self._reframe_handle_size,
            )

    def _resize_corner_at(self, pos) -> str | None:
        if not self._overlay_enabled or self._overlay_rect is None:
            return None
        overlay = self._overlay_rect
        if not overlay.isValid() or overlay.width() <= 0 or overlay.height() <= 0:
            return None

        x = pos.x()
        y = pos.y()
        threshold = self._reframe_handle_size
        corners = {
            "top_left": overlay.topLeft(),
            "top_right": overlay.topRight(),
            "bottom_left": overlay.bottomLeft(),
            "bottom_right": overlay.bottomRight(),
        }
        for name, point in corners.items():
            if abs(x - point.x()) <= threshold and abs(y - point.y()) <= threshold:
                return name
        return None

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if self._drag_enabled and event.button() == Qt.MouseButton.LeftButton:
            self._last_pos = event.position().toPoint()
            self.drag_started.emit(self._last_pos.x(), self._last_pos.y())
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        pos = event.position().toPoint()
        if self._drag_enabled and self._last_pos is not None:
            delta = pos - self._last_pos
            self._last_pos = pos
            self.dragged.emit(delta.x(), delta.y(), pos.x(), pos.y())
        elif self._drag_enabled:
            corner = self._resize_corner_at(pos)
            if corner in {"top_left", "bottom_right"}:
                self.setCursor(Qt.CursorShape.SizeFDiagCursor)
            elif corner in {"top_right", "bottom_left"}:
                self.setCursor(Qt.CursorShape.SizeBDiagCursor)
            else:
                self.setCursor(Qt.CursorShape.OpenHandCursor)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if self._drag_enabled and event.button() == Qt.MouseButton.LeftButton:
            self._last_pos = None
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            pos = event.position().toPoint()
            self.drag_released.emit(pos.x(), pos.y())
        super().mouseReleaseEvent(event)


__all__ = ["PreviewLabel"]
