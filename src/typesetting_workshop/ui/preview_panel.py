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
from typesetting_workshop.services.renderer import RendererService
from typesetting_workshop.ui.preview_canvas import PreviewCanvas


class PreviewPanel(QWidget):
    exportRequested = Signal()
    printRequested = Signal()
    clearRequested = Signal()
    cropChanged = Signal(str, object)

    def __init__(self, renderer: RendererService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.batch: list[PlacedPhoto] = []

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(16, 16, 16, 16)
        root_layout.setSpacing(12)

        toolbar_layout = QHBoxLayout()
        self.summary_label = QLabel("待打印照片：0")
        self.summary_label.setStyleSheet("font-size: 14px; font-weight: 600;")
        toolbar_layout.addWidget(self.summary_label)
        toolbar_layout.addStretch(1)

        self.clear_button = QPushButton("清空当前队列")
        self.export_button = QPushButton("导出当前排版 PNG")
        self.print_button = QPushButton("打印当前批次")
        toolbar_layout.addWidget(self.clear_button)
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

        self.clear_button.clicked.connect(self.clearRequested.emit)
        self.export_button.clicked.connect(self.exportRequested.emit)
        self.print_button.clicked.connect(self.printRequested.emit)
        self.reset_button.clicked.connect(self.canvas.reset_selected_crop)
        self.canvas.photoSelected.connect(self._handle_selection_changed)
        self.canvas.cropChanged.connect(self._handle_crop_changed)

    def set_batch(self, batch: list[PlacedPhoto], total_pending: int) -> None:
        self.batch = batch
        self.canvas.set_batch(batch)
        self.summary_label.setText(f"待打印照片：{total_pending} 张，本页展示：{len(batch)} / 6")
        has_batch = bool(batch)
        self.clear_button.setEnabled(has_batch)
        self.export_button.setEnabled(has_batch)
        self.print_button.setEnabled(has_batch)
        if not has_batch:
            self.selection_label.setText("当前没有待排版照片")
            self.zoom_label.setText("缩放：-")
            self.reset_button.setEnabled(False)

    def set_print_enabled(self, enabled: bool, reason: str | None = None) -> None:
        self.print_button.setEnabled(enabled and bool(self.batch))
        self.print_button.setToolTip(reason or "")

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
            f"文件：{Path(placed.record.source_path).name}\nMD5：{placed.record.md5[:10]}..."
        )
        self.zoom_label.setText(f"缩放：{placed.crop_state.zoom:.1f}x")
        self.reset_button.setEnabled(True)

    def _handle_crop_changed(self, md5_value: str, crop_state: object) -> None:
        self.cropChanged.emit(md5_value, crop_state)
        self._handle_selection_changed(md5_value)
