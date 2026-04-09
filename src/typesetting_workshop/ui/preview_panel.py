from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from typesetting_workshop.models import PlacedPhoto
from typesetting_workshop.services.layout import PAGE_CAPACITY
from typesetting_workshop.services.renderer import RendererService
from typesetting_workshop.ui.preview_canvas import PreviewCanvas


class PreviewPanel(QWidget):
    exportRequested = Signal()
    printRequested = Signal()
    printCalibrationRequested = Signal()
    clearRequested = Signal()
    clearPrintedRequested = Signal()
    previousPageRequested = Signal()
    nextPageRequested = Signal()
    cropChanged = Signal(str, object)

    def __init__(self, renderer: RendererService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.batch: list[PlacedPhoto] = []

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(16, 16, 16, 16)
        root_layout.setSpacing(12)

        self.watch_folder_label = QLabel("当前监听文件夹：未设置")
        self.watch_folder_label.setWordWrap(True)
        self.watch_folder_label.setStyleSheet("font-size: 13px; color: #475467;")
        root_layout.addWidget(self.watch_folder_label)

        toolbar_layout = QHBoxLayout()
        self.summary_label = QLabel(
            f"总照片：0 张，待打印：0 张，已打印：0 张，本页显示：0 / {PAGE_CAPACITY}"
        )
        self.summary_label.setStyleSheet("font-size: 14px; font-weight: 600;")
        toolbar_layout.addWidget(self.summary_label)
        toolbar_layout.addStretch(1)

        self.previous_button = QPushButton("上一页")
        self.page_label = QLabel("第 1 / 1 页")
        self.next_button = QPushButton("下一页")
        self.calibration_button = QPushButton("打印校准页")
        self.clear_button = QPushButton("清空当前队列")
        self.clear_printed_button = QPushButton("清空已打印并重载")
        self.export_button = QPushButton("导出当前排版 PNG")
        self.print_button = QPushButton("打印当前批次")
        toolbar_layout.addWidget(self.previous_button)
        toolbar_layout.addWidget(self.page_label)
        toolbar_layout.addWidget(self.next_button)
        toolbar_layout.addWidget(self.calibration_button)
        toolbar_layout.addWidget(self.clear_button)
        toolbar_layout.addWidget(self.clear_printed_button)
        toolbar_layout.addWidget(self.export_button)
        toolbar_layout.addWidget(self.print_button)
        root_layout.addLayout(toolbar_layout)

        content_layout = QHBoxLayout()
        content_layout.setSpacing(16)
        self.canvas = PreviewCanvas(renderer)
        self.canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        content_layout.addWidget(self.canvas, stretch=1)

        sidebar = QWidget()
        sidebar.setFixedWidth(280)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(16, 16, 16, 16)
        sidebar_layout.setSpacing(12)

        title_label = QLabel("单图调整")
        title_label.setStyleSheet("font-size: 16px; font-weight: 700;")
        sidebar_layout.addWidget(title_label)

        self.selection_label = QLabel("未选择照片")
        self.selection_label.setWordWrap(True)
        sidebar_layout.addWidget(self.selection_label)

        self.zoom_label = QLabel("缩放：-")
        sidebar_layout.addWidget(self.zoom_label)

        tip_label = QLabel("滚轮可缩放照片，按住鼠标左键拖拽可调整照片在画框中的裁切位置。")
        tip_label.setWordWrap(True)
        tip_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        sidebar_layout.addWidget(tip_label)

        self.reset_button = QPushButton("重置当前照片裁切")
        self.reset_button.setEnabled(False)
        sidebar_layout.addWidget(self.reset_button)
        sidebar_layout.addStretch(1)
        content_layout.addWidget(sidebar)
        root_layout.addLayout(content_layout)

        self.calibration_button.clicked.connect(self.printCalibrationRequested.emit)
        self.clear_button.clicked.connect(self.clearRequested.emit)
        self.clear_printed_button.clicked.connect(self.clearPrintedRequested.emit)
        self.previous_button.clicked.connect(self.previousPageRequested.emit)
        self.next_button.clicked.connect(self.nextPageRequested.emit)
        self.export_button.clicked.connect(self.exportRequested.emit)
        self.print_button.clicked.connect(self.printRequested.emit)
        self.reset_button.clicked.connect(self.canvas.reset_selected_crop)
        self.canvas.photoSelected.connect(self._handle_selection_changed)
        self.canvas.cropChanged.connect(self._handle_crop_changed)

    def set_batch(
        self,
        batch: list[PlacedPhoto],
        watch_folder: str,
        total_photos: int,
        total_pending: int,
        total_printed: int,
        current_page: int,
        page_count: int,
    ) -> None:
        self.batch = batch
        self.canvas.set_batch(batch)

        self.watch_folder_label.setText(
            f"当前监听文件夹：{watch_folder if watch_folder else '未设置'}"
        )
        self.summary_label.setText(
            f"总照片：{total_photos} 张，待打印：{total_pending} 张，已打印：{total_printed} 张，本页显示：{len(batch)} / {PAGE_CAPACITY}"
        )
        self.page_label.setText(f"第 {current_page + 1} / {page_count} 页")
        self.previous_button.setEnabled(current_page > 0)
        self.next_button.setEnabled(current_page + 1 < page_count)

        has_batch = bool(batch)
        has_pending = any(item.record.status == "pending" for item in batch)
        self.clear_button.setEnabled(total_pending > 0)
        self.export_button.setEnabled(has_batch)
        self.print_button.setEnabled(has_batch)
        self.print_button.setText("打印当前批次" if has_pending else "再次打印当前批次")
        if not has_batch:
            self.selection_label.setText("当前没有待排版照片")
            self.zoom_label.setText("缩放：-")
            self.reset_button.setEnabled(False)
            self.print_button.setText("打印当前批次")

    def set_print_enabled(self, enabled: bool, reason: str | None = None) -> None:
        has_batch = bool(self.batch)
        self.print_button.setEnabled(enabled and has_batch)
        self.calibration_button.setEnabled(enabled)
        self.print_button.setToolTip(reason or "")
        self.calibration_button.setToolTip(reason or "")

    def set_clear_printed_enabled(self, enabled: bool) -> None:
        self.clear_printed_button.setEnabled(enabled)

    def _handle_selection_changed(self, md5_value: str | None) -> None:
        if md5_value is None:
            self.selection_label.setText("未选择照片")
            self.zoom_label.setText("缩放：-")
            self.reset_button.setEnabled(False)
            return

        placed = next((item for item in self.batch if item.record.md5 == md5_value), None)
        if placed is None:
            return

        self.selection_label.setText(
            f"文件：{Path(placed.record.source_path).name}\n状态：{'已打印' if placed.record.status == 'printed' else '待打印'}\nMD5：{placed.record.md5[:10]}..."
        )
        self.zoom_label.setText(f"缩放：{placed.crop_state.zoom:.1f}x")
        self.reset_button.setEnabled(True)

    def _handle_crop_changed(self, md5_value: str, crop_state: object) -> None:
        self.cropChanged.emit(md5_value, crop_state)
        self._handle_selection_changed(md5_value)
