from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPen

from typesetting_workshop.models import CropState, PlacedPhoto
from typesetting_workshop.services.layout import (
    A4_HEIGHT_MM,
    A4_WIDTH_MM,
    PAGE_CAPACITY,
    SLOT_SIZE_MM,
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
        self.paint_page(painter, QRectF(0, 0, width_px, height_px), batch, dpi=dpi)
        painter.end()
        return image

    def render_calibration_page(self, dpi: int) -> QImage:
        width_px, height_px = page_size_pixels(dpi)
        image = QImage(width_px, height_px, QImage.Format.Format_ARGB32_Premultiplied)
        image.setDotsPerMeterX(round(dpi / 0.0254))
        image.setDotsPerMeterY(round(dpi / 0.0254))
        image.fill(Qt.GlobalColor.white)

        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        self.paint_calibration_page(painter, QRectF(0, 0, width_px, height_px), dpi=dpi)
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
        self.paint_page(painter, target_rect, batch, selected_md5=selected_md5)

    def paint_page(
        self,
        painter: QPainter,
        target_rect: QRectF,
        batch: list[PlacedPhoto],
        selected_md5: str | None = None,
        dpi: int | None = None,
    ) -> None:
        self._paint_page(painter, target_rect, batch, selected_md5, dpi)

    def paint_calibration_page(
        self,
        painter: QPainter,
        target_rect: QRectF,
        dpi: int | None = None,
    ) -> None:
        painter.save()
        painter.fillRect(target_rect, QColor("#ffffff"))

        page_rect, scale = self._page_geometry(target_rect)
        painter.setPen(QPen(QColor("#d0d5dd"), 1.2))
        painter.drawRect(page_rect)

        self._draw_calibration_grid(painter, page_rect, scale)
        self._draw_calibration_rulers(painter, page_rect, scale, dpi)

        painter.restore()

    def get_slot_rects(self, target_rect: QRectF) -> dict[int, QRectF]:
        page_rect, scale = self._page_geometry(target_rect)
        rects: dict[int, QRectF] = {}
        for slot in SLOTS:
            rects[slot.slot_index] = QRectF(
                page_rect.left() + slot.x_mm * scale,
                page_rect.top() + slot.y_mm * scale,
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

    def _page_geometry(self, target_rect: QRectF) -> tuple[QRectF, float]:
        scale = min(target_rect.width() / A4_WIDTH_MM, target_rect.height() / A4_HEIGHT_MM)
        page_width = A4_WIDTH_MM * scale
        page_height = A4_HEIGHT_MM * scale
        origin_x = target_rect.left() + (target_rect.width() - page_width) / 2.0
        origin_y = target_rect.top() + (target_rect.height() - page_height) / 2.0
        return QRectF(origin_x, origin_y, page_width, page_height), scale

    def _mm_rect(self, page_rect: QRectF, scale: float, x_mm: float, y_mm: float, w_mm: float, h_mm: float) -> QRectF:
        return QRectF(
            page_rect.left() + x_mm * scale,
            page_rect.top() + y_mm * scale,
            w_mm * scale,
            h_mm * scale,
        )

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

    def _draw_calibration_grid(self, painter: QPainter, page_rect: QRectF, scale: float) -> None:
        minor_pen = QPen(QColor("#e5e7eb"), 1)
        major_pen = QPen(QColor("#cbd5e1"), 1.3)

        for mm in range(0, int(A4_WIDTH_MM) + 1, 10):
            painter.setPen(major_pen if mm % 50 == 0 else minor_pen)
            x = page_rect.left() + mm * scale
            painter.drawLine(x, page_rect.top(), x, page_rect.bottom())

        for mm in range(0, int(A4_HEIGHT_MM) + 1, 10):
            painter.setPen(major_pen if mm % 50 == 0 else minor_pen)
            y = page_rect.top() + mm * scale
            painter.drawLine(page_rect.left(), y, page_rect.right(), y)

    def _draw_calibration_rulers(
        self,
        painter: QPainter,
        page_rect: QRectF,
        scale: float,
        dpi: int | None,
    ) -> None:
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSizeF(13 if dpi is None else max(18.0, mm_to_pixels(5, dpi)))
        body_font = QFont()
        body_font.setPointSizeF(9 if dpi is None else max(12.0, mm_to_pixels(3.2, dpi)))

        painter.setFont(title_font)
        painter.setPen(QColor("#111827"))
        title_rect = self._mm_rect(page_rect, scale, 15, 8, 180, 10)
        painter.drawText(title_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, "打印校准页")

        painter.setFont(body_font)
        hint_rect = self._mm_rect(page_rect, scale, 15, 18, 180, 12)
        painter.drawText(
            hint_rect,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
            "请使用直尺测量下方的 100mm 标尺和 74mm 方框，确认打印尺寸是否准确。",
        )

        ruler_pen = QPen(QColor("#111827"), 2)
        painter.setPen(ruler_pen)

        horizontal_y = page_rect.top() + 42 * scale
        horizontal_start_x = page_rect.left() + 25 * scale
        horizontal_end_x = page_rect.left() + 125 * scale
        painter.drawLine(horizontal_start_x, horizontal_y, horizontal_end_x, horizontal_y)
        for mm in range(0, 101, 10):
            x = horizontal_start_x + mm * scale
            tick = 10 if mm % 50 == 0 else 6
            painter.drawLine(x, horizontal_y - tick, x, horizontal_y + tick)
            label_rect = QRectF(x - 18, horizontal_y - 24, 36, 14)
            painter.drawText(label_rect, Qt.AlignmentFlag.AlignCenter, str(mm))
        painter.drawText(
            self._mm_rect(page_rect, scale, 25, 45, 100, 8),
            Qt.AlignmentFlag.AlignCenter,
            "水平标尺 100mm",
        )

        vertical_x = page_rect.left() + 30 * scale
        vertical_start_y = page_rect.top() + 65 * scale
        vertical_end_y = page_rect.top() + 165 * scale
        painter.drawLine(vertical_x, vertical_start_y, vertical_x, vertical_end_y)
        for mm in range(0, 101, 10):
            y = vertical_start_y + mm * scale
            tick = 10 if mm % 50 == 0 else 6
            painter.drawLine(vertical_x - tick, y, vertical_x + tick, y)
            label_rect = QRectF(vertical_x + 8, y - 8, 28, 16)
            painter.drawText(label_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, str(mm))
        painter.drawText(
            self._mm_rect(page_rect, scale, 18, 170, 40, 8),
            Qt.AlignmentFlag.AlignLeft,
            "垂直标尺 100mm",
        )

        square_rect = self._mm_rect(page_rect, scale, 105, 70, SLOT_SIZE_MM, SLOT_SIZE_MM)
        painter.setPen(QPen(QColor("#dc2626"), 2.4))
        painter.drawRect(square_rect)
        painter.setPen(QColor("#111827"))
        painter.drawText(
            self._mm_rect(page_rect, scale, 100, 146, 86, 10),
            Qt.AlignmentFlag.AlignCenter,
            f"参考方框 {int(SLOT_SIZE_MM)}mm x {int(SLOT_SIZE_MM)}mm",
        )

        center_rect = self._mm_rect(page_rect, scale, 95, 200, 20, 20)
        painter.setPen(QPen(QColor("#2563eb"), 1.8))
        painter.drawEllipse(center_rect)
        painter.drawLine(center_rect.center().x() - 12, center_rect.center().y(), center_rect.center().x() + 12, center_rect.center().y())
        painter.drawLine(center_rect.center().x(), center_rect.center().y() - 12, center_rect.center().x(), center_rect.center().y() + 12)
        painter.setPen(QColor("#111827"))
        painter.drawText(
            self._mm_rect(page_rect, scale, 72, 222, 66, 8),
            Qt.AlignmentFlag.AlignCenter,
            "中心对位参考",
        )
