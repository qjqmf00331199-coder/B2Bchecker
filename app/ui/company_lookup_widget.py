"""F-03: 거래처별 조회 화면 (+F-05 날짜필터, F-06 엑셀 내보내기 연동)."""
import sqlite3

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QCheckBox,
    QDateEdit,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app import models
from app.excel_export import export_table_to_excel
from app.ui.autocomplete import KeyedAutocompleteEdit

COLUMNS = ["품번", "품명", "날짜", "구분", "수량", "단가", "금액"]


class CompanyLookupWidget(QWidget):
    def __init__(self, conn: sqlite3.Connection, parent=None):
        super().__init__(parent)
        self.conn = conn
        self._build_ui()
        self.reload_master_data()

    def _build_ui(self) -> None:
        self.company_edit = KeyedAutocompleteEdit(placeholder="거래처명 입력...")
        self.company_edit.completer_widget().activated.connect(self.refresh)
        self.company_edit.returnPressed.connect(self.refresh)

        self.all_dates_check = QCheckBox("전체 기간")
        self.all_dates_check.setChecked(True)
        self.date_from = QDateEdit(QDate.currentDate().addMonths(-1))
        self.date_to = QDateEdit(QDate.currentDate())
        for edit in (self.date_from, self.date_to):
            edit.setCalendarPopup(True)
            edit.setDisplayFormat("yyyy-MM-dd")
            edit.setEnabled(False)
        self.all_dates_check.toggled.connect(lambda checked: self._toggle_date_filter(not checked))

        self.search_button = QPushButton("조회")
        self.export_button = QPushButton("엑셀로 내보내기")
        self.search_button.clicked.connect(self.refresh)
        self.export_button.clicked.connect(
            lambda: export_table_to_excel(self.table, self, "거래처별조회.xlsx")
        )

        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("거래처"))
        filter_row.addWidget(self.company_edit, 2)
        filter_row.addWidget(self.all_dates_check)
        filter_row.addWidget(QLabel("~"))
        filter_row.addWidget(self.date_from)
        filter_row.addWidget(QLabel("~"))
        filter_row.addWidget(self.date_to)
        filter_row.addWidget(self.search_button)
        filter_row.addWidget(self.export_button)

        self.table = QTableWidget(0, len(COLUMNS))
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)

        layout = QVBoxLayout(self)
        layout.addLayout(filter_row)
        layout.addWidget(self.table)

    def _toggle_date_filter(self, enabled: bool) -> None:
        self.date_from.setEnabled(enabled)
        self.date_to.setEnabled(enabled)

    def reload_master_data(self) -> None:
        companies = models.list_companies(self.conn)
        self.company_edit.set_options([(c["company_id"], c["company_name"]) for c in companies])

    def refresh(self) -> None:
        company_id = self.company_edit.current_key()
        if company_id is None:
            self.table.setRowCount(0)
            return

        date_from = None if self.all_dates_check.isChecked() else self.date_from.date().toString("yyyy-MM-dd")
        date_to = None if self.all_dates_check.isChecked() else self.date_to.date().toString("yyyy-MM-dd")

        rows = models.company_transactions(self.conn, company_id, date_from, date_to)
        self.table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            values = [
                row["item_code"],
                row["item_name"],
                row["tx_date"],
                row["tx_type"],
                f'{row["quantity"]:,.2f}',
                f'{row["unit_price"]:,.2f}',
                f'{row["amount"]:,.2f}',
            ]
            for c, value in enumerate(values):
                self.table.setItem(r, c, QTableWidgetItem(value))
