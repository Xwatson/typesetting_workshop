from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPainterPath, QPen

from typesetting_workshop.models import CropState, PlacedPhoto
from typesetting_workshop.services.layout import (
    A4_HEIGHT_MM,
    A4_WIDTH_MM,
    CUT_GUIDE_X_MM,
    IMAGE_DIAMETER_MM,
    OUTER_DIAMETER_MM,
    PAGE_CAPACITY,
    SAFE_AREA_DIAMETER_MM,
    SLOT_SIZE_MM,
    SLOTS,
    WHITE_MARGIN_PER_SIDE_MM,
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
        self._draw_center_cut_guide(painter, page_rect, dpi)

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
        painter.fillRect(slot_rect, QColor("#ffffff"))
        outer_circle_rect = self._circle_rect(slot_rect, OUTER_DIAMETER_MM, SLOT_SIZE_MM)
        image_circle_rect = self._circle_rect(slot_rect, IMAGE_DIAMETER_MM, SLOT_SIZE_MM)
        safe_area_rect = self._circle_rect(slot_rect, SAFE_AREA_DIAMETER_MM, SLOT_SIZE_MM)

        if placed is not None:
            image = self.get_image(placed.record.managed_path)
            self._draw_cover_image(painter, image_circle_rect, image, placed.crop_state)
        else:
            if dpi is None:
                painter.setPen(QPen(QColor("#94a3b8"), 1, Qt.PenStyle.DashLine))
                painter.drawEllipse(outer_circle_rect)
                font = QFont()
                font.setPointSizeF(10)
                painter.setFont(font)
                painter.setPen(QColor("#64748b"))
                painter.drawText(outer_circle_rect, Qt.AlignmentFlag.AlignCenter, "空白")

        if dpi is None:
            painter.setPen(QPen(QColor("#2563eb") if highlight else QColor("#cbd5e1"), 3 if highlight else 1.5))
            painter.drawEllipse(outer_circle_rect)
            painter.setPen(QPen(QColor("#dc2626"), 1.2, Qt.PenStyle.DashLine))
            painter.drawEllipse(image_circle_rect)
            painter.setPen(QPen(QColor("#f59e0b"), 1.0, Qt.PenStyle.DotLine))
            painter.drawEllipse(safe_area_rect)
            if placed is not None and placed.record.status == "printed":
                self._draw_printed_badge(painter, outer_circle_rect)
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
        clip_path = QPainterPath()
        clip_path.addEllipse(target_rect)
        painter.setClipPath(clip_path)
        painter.drawImage(image_rect, image)
        painter.restore()

    def _circle_rect(self, slot_rect: QRectF, diameter_mm: float, slot_size_mm: float) -> QRectF:
        inset_ratio = max(0.0, slot_size_mm - diameter_mm) / slot_size_mm / 2.0
        inset_x = slot_rect.width() * inset_ratio
        inset_y = slot_rect.height() * inset_ratio
        return slot_rect.adjusted(inset_x, inset_y, -inset_x, -inset_y)

    def _draw_printed_badge(self, painter: QPainter, circle_rect: QRectF) -> None:
        painter.save()
        overlay_path = QPainterPath()
        overlay_path.addEllipse(circle_rect)
        painter.setClipPath(overlay_path)
        painter.fillRect(circle_rect, QColor(15, 23, 42, 72))
        painter.restore()

        badge_rect = QRectF(
            circle_rect.left() + 6,
            circle_rect.top() + 6,
            min(circle_rect.width() - 12, 54),
            22,
        )
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#16a34a"))
        painter.drawRoundedRect(badge_rect, 8, 8)

        font = QFont()
        font.setBold(True)
        font.setPointSizeF(9.5)
        painter.setFont(font)
        painter.setPen(QColor("#ffffff"))
        painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, "已打印")

    def _draw_center_cut_guide(self, painter: QPainter, page_rect: QRectF, dpi: int | None) -> None:
        painter.save()
        color = QColor(148, 163, 184, 180 if dpi is None else 220)
        pen = QPen(color, 1.1 if dpi is None else 1.4, Qt.PenStyle.DashLine)
        painter.setPen(pen)
        center_x = page_rect.left() + (CUT_GUIDE_X_MM / A4_WIDTH_MM) * page_rect.width()
        top = page_rect.top() + 8
        bottom = page_rect.bottom() - 8
        painter.drawLine(center_x, top, center_x, bottom)
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
            "请测量 100mm 标尺、72mm 外切圆、64mm 铺图圆，并参考 54mm 安全区，确认裁切容错是否足够。",
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

        outer_circle_rect = self._mm_rect(page_rect, scale, 105, 70, OUTER_DIAMETER_MM, OUTER_DIAMETER_MM)
        image_circle_rect = self._mm_rect(
            page_rect,
            scale,
            105 + WHITE_MARGIN_PER_SIDE_MM,
            70 + WHITE_MARGIN_PER_SIDE_MM,
            IMAGE_DIAMETER_MM,
            IMAGE_DIAMETER_MM,
        )
        safe_margin_mm = (OUTER_DIAMETER_MM - SAFE_AREA_DIAMETER_MM) / 2.0
        safe_area_rect = self._mm_rect(
            page_rect,
            scale,
            105 + safe_margin_mm,
            70 + safe_margin_mm,
            SAFE_AREA_DIAMETER_MM,
            SAFE_AREA_DIAMETER_MM,
        )
        painter.setPen(QPen(QColor("#2563eb"), 2.4))
        painter.drawEllipse(outer_circle_rect)
        painter.setPen(QPen(QColor("#dc2626"), 2.0, Qt.PenStyle.DashLine))
        painter.drawEllipse(image_circle_rect)
        painter.setPen(QPen(QColor("#f59e0b"), 1.6, Qt.PenStyle.DotLine))
        painter.drawEllipse(safe_area_rect)
        painter.setPen(QColor("#111827"))
        painter.drawText(
            self._mm_rect(page_rect, scale, 84, 146, 118, 20),
            Qt.AlignmentFlag.AlignCenter,
            f"外切圆 {int(OUTER_DIAMETER_MM)}mm，铺图圆 {int(IMAGE_DIAMETER_MM)}mm，安全区 {int(SAFE_AREA_DIAMETER_MM)}mm",
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
