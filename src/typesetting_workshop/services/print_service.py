from __future__ import annotations

from PySide6.QtCore import QRectF, QMarginsF
from PySide6.QtGui import QPainter, QPageLayout, QPageSize
from PySide6.QtPrintSupport import QPrinter, QPrinterInfo

from typesetting_workshop.models import PlacedPhoto
from typesetting_workshop.services.renderer import RendererService


class PrintService:
    def __init__(self, renderer: RendererService) -> None:
        self.renderer = renderer

    @staticmethod
    def available_printers() -> list[str]:
        return sorted(printer.printerName() for printer in QPrinterInfo.availablePrinters())

    def _create_printer(self, printer_name: str, dpi: int) -> QPrinter:
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setPrinterName(printer_name)
        printer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
        printer.setPageOrientation(QPageLayout.Orientation.Portrait)
        printer.setResolution(dpi)
        printer.setFullPage(True)
        printer.setPageMargins(QMarginsF(0, 0, 0, 0), QPageLayout.Unit.Millimeter)
        return printer

    def print_batch(self, batch: list[PlacedPhoto], printer_name: str, dpi: int) -> tuple[bool, str]:
        if not batch:
            return False, "当前没有可打印的照片。"
        if not printer_name:
            return False, "请先在设置中选择打印机。"

        printer = self._create_printer(printer_name, dpi)
        if not printer.isValid():
            return False, "所选打印机当前不可用。"

        painter = QPainter()
        if not painter.begin(printer):
            return False, "无法提交打印任务。"

        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
            page_rect = QRectF(printer.paperRect(QPrinter.Unit.DevicePixel))
            self.renderer.paint_page(painter, page_rect, batch)
        finally:
            painter.end()
        return True, "打印任务已提交到系统打印队列。"

    def print_calibration_page(self, printer_name: str, dpi: int) -> tuple[bool, str]:
        if not printer_name:
            return False, "请先在设置中选择打印机。"

        printer = self._create_printer(printer_name, dpi)
        if not printer.isValid():
            return False, "所选打印机当前不可用。"

        painter = QPainter()
        if not painter.begin(printer):
            return False, "无法提交校准页打印任务。"

        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
            page_rect = QRectF(printer.paperRect(QPrinter.Unit.DevicePixel))
            self.renderer.paint_calibration_page(painter, page_rect, dpi=dpi)
        finally:
            painter.end()
        return True, "校准页已提交到系统打印队列，请使用直尺测量标尺和方框尺寸。"
