from __future__ import annotations

import sqlite3
from pathlib import Path
from math import ceil

from PySide6.QtCore import QStandardPaths
from PySide6.QtWidgets import QFileDialog, QMainWindow, QMessageBox, QStatusBar, QTabWidget

from typesetting_workshop.models import AppSettings, CropState
from typesetting_workshop.services.folder_watch import FolderWatchService
from typesetting_workshop.services.importer import PhotoImportService
from typesetting_workshop.services.layout import PAGE_CAPACITY
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
        self.current_page_index = 0
        self.visible_batch = []

        data_root = app_data_root()
        try:
            self.repository = QueueRepository(data_root / "queue.sqlite3")
        except sqlite3.Error:
            self.repository = QueueRepository(":memory:")
            self.persistence_warning = "当前环境无法使用持久化存储，程序已切换为仅当前会话有效的内存队列。"
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

        self.preview_page.printCalibrationRequested.connect(self.print_calibration_page)
        self.preview_page.clearRequested.connect(self.clear_current_queue)
        self.preview_page.clearPrintedRequested.connect(self.clear_printed_and_reload)
        self.preview_page.previousPageRequested.connect(self.show_previous_page)
        self.preview_page.nextPageRequested.connect(self.show_next_page)
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
        total_photos = self.repository.count_photos(self.settings.watch_folder)
        total_pending = self.repository.count_pending(self.settings.watch_folder)
        total_printed = self.repository.count_printed(self.settings.watch_folder)
        page_count = max(1, ceil(total_photos / PAGE_CAPACITY)) if total_photos else 1
        self.current_page_index = min(self.current_page_index, page_count - 1)
        batch = self.repository.get_batch_page(self.settings.watch_folder, self.current_page_index)
        self.visible_batch = batch
        self.preview_page.set_batch(
            batch=batch,
            watch_folder=self.settings.watch_folder,
            total_photos=total_photos,
            total_pending=total_pending,
            total_printed=total_printed,
            current_page=self.current_page_index,
            page_count=page_count,
        )
        self.preview_page.set_clear_printed_enabled(total_printed > 0 and bool(self.settings.watch_folder))
        self._sync_print_button_state()
        self.statusBar().showMessage(
            f"当前监听文件夹共 {total_photos} 张，待打印 {total_pending} 张，当前第 {self.current_page_index + 1} / {page_count} 页",
            3000,
        )

    def handle_settings_changed(self, settings: AppSettings) -> None:
        self.settings = AppSettings(
            watch_folder=settings.watch_folder,
            printer_name=settings.printer_name,
            export_dpi=self.settings.export_dpi,
        )
        self.repository.save_settings(self.settings)
        self.current_page_index = 0
        self.folder_watcher.start(self.settings.watch_folder)
        self.refresh_batch()

    def handle_crop_changed(self, md5_value: str, crop_state: CropState) -> None:
        self.repository.save_crop_state(md5_value, crop_state)

    def clear_current_queue(self) -> None:
        total_pending = self.repository.count_pending(self.settings.watch_folder)
        if total_pending == 0:
            self.show_warning("当前监听文件夹没有可清空的待打印照片。")
            return

        answer = QMessageBox.question(
            self,
            "清空当前队列",
            "确定要清空当前监听文件夹中的待打印照片队列吗？此操作不会删除原始图片文件。",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        removed = self.repository.clear_pending(self.settings.watch_folder)
        self.refresh_batch()
        self.statusBar().showMessage(f"已清空 {removed} 张待打印照片。", 5000)

    def clear_printed_and_reload(self) -> None:
        if not self.settings.watch_folder:
            self.show_warning("请先在设置中选择监听文件夹。")
            return

        total_printed = self.repository.count_printed()
        if total_printed == 0:
            self.show_warning("当前没有可清空的已打印记录。")
            return

        answer = QMessageBox.question(
            self,
            "清空已打印并重载",
            "确定要清空所有已打印记录，并重新加载当前监听文件夹中的图片吗？此操作不会删除原始图片文件。",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        removed = self.repository.clear_printed()
        self.folder_watcher.start(self.settings.watch_folder)
        self.refresh_batch()
        self.statusBar().showMessage(
            f"已清空 {removed} 条已打印记录，并重新加载当前监听文件夹。",
            5000,
        )

    def show_previous_page(self) -> None:
        if self.current_page_index == 0:
            return
        self.current_page_index -= 1
        self.refresh_batch()

    def show_next_page(self) -> None:
        total_photos = self.repository.count_photos(self.settings.watch_folder)
        if total_photos == 0:
            return
        page_count = ceil(total_photos / PAGE_CAPACITY)
        if self.current_page_index + 1 >= page_count:
            return
        self.current_page_index += 1
        self.refresh_batch()

    def export_current_page(self) -> None:
        batch = self.visible_batch
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
        batch = [item for item in self.visible_batch if item.record.status == "pending"]
        if not batch:
            batch = self.visible_batch
        if not batch:
            self.show_warning("当前页没有可打印照片。")
            return
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

    def print_calibration_page(self) -> None:
        success, message = self.print_service.print_calibration_page(
            self.settings.printer_name or "",
            self.settings.export_dpi,
        )
        if not success:
            self.show_warning(message)
            return

        self.statusBar().showMessage(message, 8000)

    def _sync_print_button_state(self) -> None:
        if self.settings.printer_name:
            self.preview_page.set_print_enabled(True)
        else:
            self.preview_page.set_print_enabled(False, "请先在设置中选择打印机。")

    def show_warning(self, message: str) -> None:
        QMessageBox.warning(self, "图片排版工坊", message)
