"""프로그램 진입점."""
import sys

from PySide6.QtWidgets import QApplication, QMessageBox

from app import db, updater
from app.ui import theme
from app.ui.main_window import MainWindow


def _check_update() -> bool:
    """업데이트 적용해서 재시작했으면 True."""
    updater.cleanup_old_file()
    update = updater.check_for_update()
    if update is None:
        return False

    reply = QMessageBox.question(
        None,
        "업데이트 확인",
        "새 버전이 있습니다. 지금 업데이트하시겠습니까?",
    )
    if reply != QMessageBox.StandardButton.Yes:
        return False

    if not updater.download_and_apply(update["download_url"]):
        QMessageBox.warning(None, "업데이트 실패", "업데이트에 실패했습니다. 계속 실행합니다.")
        return False

    QMessageBox.information(None, "업데이트 완료", "업데이트가 완료되었습니다. 새 버전으로 다시 시작합니다.")
    return True


def main() -> int:
    app = QApplication(sys.argv)
    app.setStyleSheet(theme.STYLESHEET)

    if _check_update():
        return 0

    conn = db.connect()
    window = MainWindow(conn)
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
