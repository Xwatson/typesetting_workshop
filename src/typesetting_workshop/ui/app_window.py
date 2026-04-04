from __future__ import annotations

import sqlite3
from pathlib import Path

from PySide6.QtCore import QStandardPaths
from PySide6.QtWidgets import QFileDialog, QMainWindow, QMessageBox, QStatusBar, QTabWidget

from typesetting_workshop.models import AppSettings, CropState
from typesetting_workshop.services.folder_watch import FolderWatchService
from typesetting_workshop.services.importer import PhotoImportService
from typesetting_workshop.services.print_service import PrintService
from typesetting_workshop.services.renderer import RendererService
from typesetting_workshop.services.repository import QueueRepository
from typesetting_workshop.ui.preview_panel import PreviewPanel
from typesetting_workshop.ui.settings_panel import SettingsPanel


def app_data_root() -> Path:
    base = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
    candidates = [Path(base).expanduser()] if base else []
    candidates.append(Path.cwd() / ".typesetting-workshop-data")

    for candidate in candidates:
        try:
            root = candidate.resolve()
            root.mkdir(parents=True, exist_ok=True)
            return root
        except OSError:
            continue

    raise OSError("无法创建应用数据目录。")


class AppWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("图片排版工坊")
        self.resize(1280, 900)
        self.persistence_warning: str | None = None

        data_root = app_data_root()
        try:
            self.repository = QueueRepository(data_root / "queue.sqlite3")
        except sqlite3.Error:
            self.repository = QueueRepository(":memory:")
            self.persistence_warning = (
                "当前环境无法使用持久化存储，程序已切换为仅当前会话有效的内存队列。"
            )
        self.renderer = RendererService()
        self.importer = PhotoImportService(self.repository, data_root / "imported_images")
        self.folder_watcher = FolderWatchService(self.importer)
        self.print_service = PrintService(self.renderer)
        self.settings = self.repository.load_settings()

        tabs = QTabWidget()
        self.preview_page = PreviewPanel(self.renderer)
        self.settings_page = SettingsPanel()
        tabs.addTab(self.preview_page, "预览")
        tabs.addTab(self.settings_page, "设置")
        self.setCentralWidget(tabs)
        self.setStatusBar(QStatusBar())

        self.preview_page.exportRequested.connect(self.export_current_page)
        self.preview_page.printRequested.connect(self.print_current_batch)
        self.preview_page.cropChanged.connect(self.handle_crop_changed)
        self.settings_page.settingsChanged.connect(self.handle_settings_changed)
        self.settings_page.refreshPrintersRequested.connect(self.refresh_printers)
        self.folder_watcher.photosChanged.connect(self.refresh_batch)
        self.folder_watcher.errorOccurred.connect(self.show_warning)

        self.refresh_printers()
        self.folder_watcher.start(self.settings.watch_folder)
        self.refresh_batch()
        if self.persistence_warning:
            self.statusBar().showMessage(self.persistence_warning, 8000)

    def closeEvent(self, event) -> None:  # type: ignore[override]
        self.folder_watcher.stop()
        self.repository.close()
        super().closeEvent(event)

    def refresh_printers(self) -> None:
        printers = self.print_service.available_printers()
        self.settings_page.set_settings(self.settings, printers)
        self._sync_print_button_state()

    def refresh_batch(self) -> None:
        batch = self.repository.get_current_batch()
        total_pending = self.repository.count_pending()
        self.preview_page.set_batch(batch, total_pending)
        self._sync_print_button_state()
        self.statusBar().showMessage(f"待打印照片：{total_pending} 张", 3000)

    def handle_settings_changed(self, settings: AppSettings) -> None:
        self.settings = AppSettings(
            watch_folder=settings.watch_folder,
            printer_name=settings.printer_name,
            export_dpi=self.settings.export_dpi,
        )
        self.repository.save_settings(self.settings)
        self.folder_watcher.start(self.settings.watch_folder)
        self.refresh_batch()

    def handle_crop_changed(self, md5_value: str, crop_state: CropState) -> None:
        self.repository.save_crop_state(md5_value, crop_state)

    def export_current_page(self) -> None:
        batch = self.repository.get_current_batch()
        if not batch:
            self.show_warning("当前没有可导出的照片。")
            return

        destination, _ = QFileDialog.getSaveFileName(
            self,
            "导出当前排版",
            str(Path.home() / "图片排版.png"),
            "PNG 文件 (*.png)",
        )
        if not destination:
            return

        self.renderer.export_page(destination, batch, self.settings.export_dpi)
        self.statusBar().showMessage(f"已导出到：{destination}", 5000)

    def print_current_batch(self) -> None:
        batch = self.repository.get_current_batch()
        success, message = self.print_service.print_batch(
            batch,
            self.settings.printer_name or "",
            self.settings.export_dpi,
        )
        if not success:
            self.show_warning(message)
            return

        self.repository.mark_printed([item.record.md5 for item in batch])
        self.refresh_batch()
        self.statusBar().showMessage(message, 5000)

    def _sync_print_button_state(self) -> None:
        if self.settings.printer_name:
            self.preview_page.set_print_enabled(True)
        else:
            self.preview_page.set_print_enabled(False, "请先在设置中选择打印机。")

    def show_warning(self, message: str) -> None:
        QMessageBox.warning(self, "图片排版工坊", message)
