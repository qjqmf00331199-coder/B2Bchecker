"""프로그램 진입점."""
import sys

from PySide6.QtWidgets import QApplication

from app import db
from app.ui import theme
from app.ui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setStyleSheet(theme.STYLESHEET)
    conn = db.connect()
    window = MainWindow(conn)
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
