"""F-04: 통합 대시보드 (상단 입력폼 / 하단좌우 조회 테이블)."""
import sqlite3

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMainWindow, QSplitter, QToolBar

from app.ui.company_lookup_widget import CompanyLookupWidget
from app.ui.item_lookup_widget import ItemLookupWidget
from app.ui.master_data_dialog import MasterDataDialog
from app.ui.transaction_form import TransactionForm


class MainWindow(QMainWindow):
    def __init__(self, conn: sqlite3.Connection):
        super().__init__()
        self.conn = conn
        self.setWindowTitle("B2B 재고/거래 관리")
        self.resize(1200, 800)

        self.transaction_form = TransactionForm(conn)
        self.item_lookup = ItemLookupWidget(conn)
        self.company_lookup = CompanyLookupWidget(conn)

        bottom_splitter = QSplitter(Qt.Horizontal)
        bottom_splitter.addWidget(self.item_lookup)
        bottom_splitter.addWidget(self.company_lookup)

        main_splitter = QSplitter(Qt.Vertical)
        main_splitter.addWidget(self.transaction_form)
        main_splitter.addWidget(bottom_splitter)
        main_splitter.setStretchFactor(0, 0)
        main_splitter.setStretchFactor(1, 1)
        self.setCentralWidget(main_splitter)

        self.transaction_form.transaction_saved.connect(self._on_transaction_saved)

        toolbar = QToolBar("메인")
        self.addToolBar(toolbar)
        master_data_action = toolbar.addAction("마스터 데이터 관리")
        master_data_action.triggered.connect(self._open_master_data_dialog)

    def _on_transaction_saved(self) -> None:
        self.item_lookup.refresh()
        self.company_lookup.refresh()

    def _open_master_data_dialog(self) -> None:
        dialog = MasterDataDialog(self.conn, self)
        dialog.data_changed.connect(self._on_master_data_changed)
        dialog.exec()

    def _on_master_data_changed(self) -> None:
        self.transaction_form.reload_master_data()
        self.item_lookup.reload_master_data()
        self.company_lookup.reload_master_data()
