from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from typesetting_workshop.ui.app_window import AppWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Typesetting Workshop")
    app.setOrganizationName("TypesettingWorkshop")
    window = AppWindow()
    window.show()
    return app.exec()
