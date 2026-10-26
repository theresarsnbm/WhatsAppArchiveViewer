from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from app.ui.main_window import MainWindow
from app.ui import theme


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("WhatsApp Archive Viewer")
    app.setOrganizationName("WhatsAppArchiveViewer")
    app.setApplicationDisplayName("WhatsApp Archive Viewer")
    app.setStyleSheet(theme.APP_STYLESHEET)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()