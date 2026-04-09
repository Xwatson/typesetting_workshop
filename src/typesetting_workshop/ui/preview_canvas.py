from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QMouseEvent, QPaintEvent, QPainter, QWheelEvent
from PySide6.QtWidgets import QWidget

from typesetting_workshop.models import CropState, PlacedPhoto
from typesetting_workshop.services.renderer import RendererService


class PreviewCanvas(QWidget):
    photoSelected = Signal(object)
    cropChanged = Signal(str, object)

    def __init__(self, renderer: RendererService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.renderer = renderer
        self.batch: list[PlacedPhoto] = []
        self.selected_md5: str | None = None
        self.dragging_md5: str | None = None
        self.last_mouse_position = QPointF()
        self.setMinimumSize(620, 760)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def set_batch(self, batch: list[PlacedPhoto]) -> None:
        self.batch = batch
        if self.selected_md5 and not any(item.record.md5 == self.selected_md5 for item in batch):
            self.selected_md5 = None
            self.photoSelected.emit(None)
        self.update()

    def reset_selected_crop(self) -> None:
        placed = self._selected_photo()
        if placed is None:
            return
        placed.crop_state = CropState()
        self.cropChanged.emit(placed.record.md5, placed.crop_state)
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.fillRect(self.rect(), QColor("#eef2f7"))
        self.renderer.draw_preview(painter, self._page_area(), self.batch, self.selected_md5)
        painter.end()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return
        self.setFocus(Qt.FocusReason.MouseFocusReason)
        placed = self._photo_at(event.position())
        if placed is None:
            self.selected_md5 = None
            self.dragging_md5 = None
            self.photoSelected.emit(None)
            self.update()
            return

        self.selected_md5 = placed.record.md5
        self.dragging_md5 = placed.record.md5
        self.last_mouse_position = event.position()
        self.photoSelected.emit(placed.record.md5)
        self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if not self.dragging_md5:
            return
        placed = self._selected_photo()
        if placed is None:
            return

        slot_rect = self._slot_rect_for_md5(placed.record.md5)
        if slot_rect is None:
            return

        delta = event.position() - self.last_mouse_position
        overflow_x, overflow_y = self.renderer.get_drag_limits(placed.record.managed_path, slot_rect, placed.crop_state)

        if overflow_x > 0:
            placed.crop_state.offset_x += delta.x() / (overflow_x / 2.0)
        if overflow_y > 0:
            placed.crop_state.offset_y += delta.y() / (overflow_y / 2.0)

        placed.crop_state = placed.crop_state.clamped()
        self.last_mouse_position = event.position()
        self.cropChanged.emit(placed.record.md5, placed.crop_state)
        self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging_md5 = None

    def wheelEvent(self, event: QWheelEvent) -> None:
        placed = self._photo_at(event.position())
        if placed is None:
            return
        step = 0.1 if event.angleDelta().y() > 0 else -0.1
        placed.crop_state.zoom = min(max(placed.crop_state.zoom + step, 1.0), 4.0)
        self.selected_md5 = placed.record.md5
        self.photoSelected.emit(placed.record.md5)
        self.cropChanged.emit(placed.record.md5, placed.crop_state)
        self.update()

    def keyPressEvent(self, event) -> None:  # type: ignore[override]
        key_to_delta = {
            Qt.Key.Key_Left: (-1.0, 0.0),
            Qt.Key.Key_Right: (1.0, 0.0),
            Qt.Key.Key_Up: (0.0, -1.0),
            Qt.Key.Key_Down: (0.0, 1.0),
        }
        delta = key_to_delta.get(event.key())
        if delta is None:
            if event.key() in {Qt.Key.Key_Plus, Qt.Key.Key_Equal, Qt.Key.Key_Asterisk}:
                if self._zoom_selected_photo(0.05):
                    event.accept()
                    return
            if event.key() in {Qt.Key.Key_Minus, Qt.Key.Key_Underscore, Qt.Key.Key_Slash}:
                if self._zoom_selected_photo(-0.05):
                    event.accept()
                    return
            super().keyPressEvent(event)
            return

        if self._nudge_selected_photo(*delta):
            event.accept()
            return

        super().keyPressEvent(event)

    def _page_area(self) -> QRectF:
        margin = 24.0
        return QRectF(margin, margin, max(1.0, self.width() - margin * 2), max(1.0, self.height() - margin * 2))

    def _photo_at(self, position: QPointF) -> PlacedPhoto | None:
        rects = self.renderer.get_slot_rects(self._page_area())
        for placed in self.batch:
            slot_rect = rects.get(placed.slot_index)
            if slot_rect is not None and slot_rect.contains(position):
                return placed
        return None

    def _slot_rect_for_md5(self, md5_value: str) -> QRectF | None:
        rects = self.renderer.get_slot_rects(self._page_area())
        for placed in self.batch:
            if placed.record.md5 == md5_value:
                return rects.get(placed.slot_index)
        return None

    def _selected_photo(self) -> PlacedPhoto | None:
        for placed in self.batch:
            if placed.record.md5 == self.selected_md5:
                return placed
        return None

    def _nudge_selected_photo(self, delta_x: float, delta_y: float) -> bool:
        placed = self._selected_photo()
        if placed is None:
            return False

        slot_rect = self._slot_rect_for_md5(placed.record.md5)
        if slot_rect is None:
            return False

        overflow_x, overflow_y = self.renderer.get_drag_limits(
            placed.record.managed_path,
            slot_rect,
            placed.crop_state,
        )

        changed = False
        if overflow_x > 0:
            placed.crop_state.offset_x += delta_x / (overflow_x / 2.0)
            changed = True
        if overflow_y > 0:
            placed.crop_state.offset_y += delta_y / (overflow_y / 2.0)
            changed = True

        if not changed:
            return False

        placed.crop_state = placed.crop_state.clamped()
        self.cropChanged.emit(placed.record.md5, placed.crop_state)
        self.update()
        return True

    def _zoom_selected_photo(self, delta_zoom: float) -> bool:
        placed = self._selected_photo()
        if placed is None:
            return False

        previous_zoom = placed.crop_state.zoom
        placed.crop_state.zoom = min(max(previous_zoom + delta_zoom, 1.0), 4.0)
        if placed.crop_state.zoom == previous_zoom:
            return False

        self.cropChanged.emit(placed.record.md5, placed.crop_state)
        self.update()
        return True
