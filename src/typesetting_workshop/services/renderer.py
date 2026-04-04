from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPen

from typesetting_workshop.models import CropState, PlacedPhoto
from typesetting_workshop.services.layout import (
    A4_HEIGHT_MM,
    A4_WIDTH_MM,
    PAGE_CAPACITY,
    SLOTS,
    mm_to_pixels,
    page_size_pixels,
)


class RendererService:
    def __init__(self) -> None:
        self._image_cache: dict[str, QImage] = {}

    def render_page(self, batch: list[PlacedPhoto], dpi: int) -> QImage:
        width_px, height_px = page_size_pixels(dpi)
        image = QImage(width_px, height_px, QImage.Format.Format_ARGB32_Premultiplied)
        image.setDotsPerMeterX(round(dpi / 0.0254))
        image.setDotsPerMeterY(round(dpi / 0.0254))
        image.fill(Qt.GlobalColor.white)

        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        self._paint_page(painter, QRectF(0, 0, width_px, height_px), batch, None, dpi)
        painter.end()
        return image

    def export_page(self, destination: str, batch: list[PlacedPhoto], dpi: int) -> None:
        image = self.render_page(batch, dpi)
        image.save(destination, "PNG")

    def draw_preview(
        self,
        painter: QPainter,
        target_rect: QRectF,
        batch: list[PlacedPhoto],
        selected_md5: str | None,
    ) -> None:
        self._paint_page(painter, target_rect, batch, selected_md5, None)

    def get_slot_rects(self, target_rect: QRectF) -> dict[int, QRectF]:
        scale = min(target_rect.width() / A4_WIDTH_MM, target_rect.height() / A4_HEIGHT_MM)
        page_width = A4_WIDTH_MM * scale
        page_height = A4_HEIGHT_MM * scale
        origin_x = target_rect.left() + (target_rect.width() - page_width) / 2.0
        origin_y = target_rect.top() + (target_rect.height() - page_height) / 2.0
        rects: dict[int, QRectF] = {}
        for slot in SLOTS:
            rects[slot.slot_index] = QRectF(
                origin_x + slot.x_mm * scale,
                origin_y + slot.y_mm * scale,
                slot.width_mm * scale,
                slot.height_mm * scale,
            )
        return rects

    def get_image(self, managed_path: str) -> QImage:
        cached = self._image_cache.get(managed_path)
        if cached is not None:
            return cached

        image = QImage(managed_path)
        if image.isNull():
            image = QImage(1, 1, QImage.Format.Format_ARGB32_Premultiplied)
            image.fill(Qt.GlobalColor.lightGray)
        self._image_cache[managed_path] = image
        return image

    def get_drag_limits(self, managed_path: str, target_rect: QRectF, crop_state: CropState) -> tuple[float, float]:
        image = self.get_image(managed_path)
        if image.isNull():
            return 0.0, 0.0
        scale = max(target_rect.width() / image.width(), target_rect.height() / image.height())
        scale *= crop_state.clamped().zoom
        scaled_width = image.width() * scale
        scaled_height = image.height() * scale
        return max(0.0, scaled_width - target_rect.width()), max(0.0, scaled_height - target_rect.height())

    def _paint_page(
        self,
        painter: QPainter,
        page_rect: QRectF,
        batch: list[PlacedPhoto],
        selected_md5: str | None,
        dpi: int | None,
    ) -> None:
        painter.save()
        painter.fillRect(page_rect, QColor("#ffffff"))
        painter.setPen(QPen(QColor("#d0d5dd"), 1.2))
        painter.drawRect(page_rect)

        batch_by_slot = {placed.slot_index: placed for placed in batch}
        slot_rects = self.get_slot_rects(page_rect)
        for slot_index in range(PAGE_CAPACITY):
            placed = batch_by_slot.get(slot_index)
            self._paint_slot(
                painter,
                slot_rects[slot_index],
                placed,
                placed is not None and placed.record.md5 == selected_md5,
                dpi,
            )
        painter.restore()

    def _paint_slot(
        self,
        painter: QPainter,
        slot_rect: QRectF,
        placed: PlacedPhoto | None,
        highlight: bool,
        dpi: int | None,
    ) -> None:
        painter.save()
        painter.fillRect(slot_rect, QColor("#f8fafc"))

        if placed is not None:
            image = self.get_image(placed.record.managed_path)
            self._draw_cover_image(painter, slot_rect, image, placed.crop_state)
        else:
            painter.setPen(QPen(QColor("#94a3b8"), 1, Qt.PenStyle.DashLine))
            painter.drawRect(slot_rect)
            font = QFont()
            font.setPointSizeF(10 if dpi is None else max(14.0, mm_to_pixels(4, dpi)))
            painter.setFont(font)
            painter.setPen(QColor("#64748b"))
            painter.drawText(slot_rect, Qt.AlignmentFlag.AlignCenter, "空白")

        painter.setPen(QPen(QColor("#2563eb") if highlight else QColor("#cbd5e1"), 3 if highlight else 1.5))
        painter.drawRect(slot_rect)
        painter.restore()

    def _draw_cover_image(
        self,
        painter: QPainter,
        target_rect: QRectF,
        image: QImage,
        crop_state: CropState,
    ) -> None:
        if image.isNull():
            painter.fillRect(target_rect, QColor("#e2e8f0"))
            return

        normalized = crop_state.clamped()
        base_scale = max(target_rect.width() / image.width(), target_rect.height() / image.height())
        scale = base_scale * normalized.zoom
        scaled_width = image.width() * scale
        scaled_height = image.height() * scale
        overflow_x = max(0.0, scaled_width - target_rect.width())
        overflow_y = max(0.0, scaled_height - target_rect.height())

        image_x = target_rect.left() - overflow_x / 2.0 + (overflow_x / 2.0) * normalized.offset_x
        image_y = target_rect.top() - overflow_y / 2.0 + (overflow_y / 2.0) * normalized.offset_y
        image_rect = QRectF(image_x, image_y, scaled_width, scaled_height)

        painter.save()
        painter.setClipRect(target_rect)
        painter.drawImage(image_rect, image)
        painter.restore()
