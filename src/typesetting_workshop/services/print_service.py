from __future__ import annotations

from PySide6.QtCore import QRectF
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

    def print_batch(self, batch: list[PlacedPhoto], printer_name: str, dpi: int) -> tuple[bool, str]:
        if not batch:
            return False, "当前没有可打印的照片。"
        if not printer_name:
            return False, "请先在设置中选择打印机。"

        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setPrinterName(printer_name)
        printer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
        printer.setPageOrientation(QPageLayout.Orientation.Portrait)
        printer.setResolution(dpi)
        printer.setFullPage(True)

        if not printer.isValid():
            return False, "所选打印机当前不可用。"

        image = self.renderer.render_page(batch, dpi)
        painter = QPainter()
        if not painter.begin(printer):
            return False, "无法提交打印任务。"

        try:
            page_rect = printer.pageRect(QPrinter.Unit.DevicePixel)
            painter.drawImage(QRectF(page_rect), image, QRectF(image.rect()))
        finally:
            painter.end()
        return True, "打印任务已提交到系统打印队列。"
