from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from typesetting_workshop.models import AppSettings


class SettingsPanel(QWidget):
    settingsChanged = Signal(object)
    refreshPrintersRequested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._updating = False

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(24, 24, 24, 24)
        root_layout.setSpacing(16)

        title = QLabel("设置")
        title.setStyleSheet("font-size: 18px; font-weight: 700;")
        root_layout.addWidget(title)

        form_layout = QFormLayout()
        form_layout.setSpacing(12)

        folder_row = QWidget()
        folder_layout = QHBoxLayout(folder_row)
        folder_layout.setContentsMargins(0, 0, 0, 0)
        folder_layout.setSpacing(8)
        self.folder_edit = QLineEdit()
        self.folder_edit.setPlaceholderText("选择要监听照片的文件夹")
        browse_button = QPushButton("浏览...")
        browse_button.clicked.connect(self._choose_folder)
        folder_layout.addWidget(self.folder_edit, stretch=1)
        folder_layout.addWidget(browse_button)
        form_layout.addRow("监听文件夹", folder_row)

        printer_row = QWidget()
        printer_layout = QHBoxLayout(printer_row)
        printer_layout.setContentsMargins(0, 0, 0, 0)
        printer_layout.setSpacing(8)
        self.printer_combo = QComboBox()
        refresh_button = QPushButton("刷新打印机")
        refresh_button.clicked.connect(self.refreshPrintersRequested.emit)
        printer_layout.addWidget(self.printer_combo, stretch=1)
        printer_layout.addWidget(refresh_button)
        form_layout.addRow("打印机", printer_row)

        root_layout.addLayout(form_layout)

        tip = QLabel("设置会立即保存。切换监听文件夹后，预览区只显示当前监听文件夹里的待打印照片。")
        tip.setWordWrap(True)
        root_layout.addWidget(tip)
        root_layout.addStretch(1)

        self.folder_edit.editingFinished.connect(self._emit_settings)
        self.printer_combo.currentIndexChanged.connect(self._emit_settings)

    def set_settings(self, settings: AppSettings, printers: list[str]) -> None:
        self._updating = True
        self.folder_edit.setText(settings.watch_folder)
        self.printer_combo.clear()
        self.printer_combo.addItem("未选择打印机", None)
        for printer_name in printers:
            self.printer_combo.addItem(printer_name, printer_name)
        index = self.printer_combo.findData(settings.printer_name)
        self.printer_combo.setCurrentIndex(index if index >= 0 else 0)
        self._updating = False

    def _emit_settings(self) -> None:
        if self._updating:
            return
        self.settingsChanged.emit(
            AppSettings(
                watch_folder=self.folder_edit.text().strip(),
                printer_name=self.printer_combo.currentData(),
                export_dpi=300,
            )
        )

    def _choose_folder(self) -> None:
        current = self.folder_edit.text().strip()
        folder = QFileDialog.getExistingDirectory(self, "选择监听文件夹", current or "")
        if folder:
            self.folder_edit.setText(folder)
            self._emit_settings()
