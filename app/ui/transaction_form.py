"""F-01: 거래 등록 입력 폼."""
import sqlite3

from PySide6.QtCore import Signal, QDate
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app import models
from app.excel_export import import_rows_from_excel
from app.ui.autocomplete import KeyedAutocompleteEdit


class TransactionForm(QWidget):
    """거래 등록 폼. 저장에 성공하면 transaction_saved 시그널을 방출한다."""

    transaction_saved = Signal()

    def __init__(self, conn: sqlite3.Connection, parent=None):
        super().__init__(parent)
        self.conn = conn
        self._build_ui()
        self.reload_master_data()

    def _build_ui(self) -> None:
        self.date_edit = QDateEdit(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("yyyy-MM-dd")

        self.company_edit = KeyedAutocompleteEdit(placeholder="거래처명 입력...")
        self.item_edit = KeyedAutocompleteEdit(placeholder="품번 또는 품명 입력...")

        self.type_combo = QComboBox()
        self.type_combo.addItems(["입고", "출고"])

        self.quantity_spin = QDoubleSpinBox()
        self.quantity_spin.setRange(0, 999_999_999)
        self.quantity_spin.setDecimals(2)

        self.unit_price_spin = QDoubleSpinBox()
        self.unit_price_spin.setRange(-999_999_999, 999_999_999)
        self.unit_price_spin.setDecimals(2)

        self.amount_label = QLabel("0")

        self.save_button = QPushButton("저장")
        self.save_button.setProperty("accent", "primary")
        self.import_button = QPushButton("엑셀로 가져오기")

        form = QFormLayout()
        form.addRow("날짜", self.date_edit)
        form.addRow("거래처", self.company_edit)
        form.addRow("품번", self.item_edit)
        form.addRow("구분", self.type_combo)
        form.addRow("수량", self.quantity_spin)
        form.addRow("단가", self.unit_price_spin)
        form.addRow("금액", self.amount_label)

        button_row = QHBoxLayout()
        button_row.addStretch()
        button_row.addWidget(self.import_button)
        button_row.addWidget(self.save_button)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addLayout(button_row)

        self.company_edit.completer_widget().activated.connect(self._on_company_or_item_selected)
        self.company_edit.editingFinished.connect(self._on_company_or_item_selected)
        self.item_edit.completer_widget().activated.connect(self._on_company_or_item_selected)
        self.item_edit.editingFinished.connect(self._on_company_or_item_selected)
        self.quantity_spin.valueChanged.connect(self._recalc_amount)
        self.unit_price_spin.valueChanged.connect(self._recalc_amount)
        self.save_button.clicked.connect(self._on_save)
        self.import_button.clicked.connect(self._on_import)

    def reload_master_data(self) -> None:
        companies = models.list_companies(self.conn)
        items = models.list_items(self.conn)
        self.company_edit.set_options([(c["company_id"], c["company_name"]) for c in companies])
        self.item_edit.set_options(
            [(i["item_code"], f'{i["item_code"]} - {i["item_name"]}') for i in items]
        )

    def _on_company_or_item_selected(self) -> None:
        company_id = self.company_edit.current_key()
        item_code = self.item_edit.current_key()
        if company_id is None or item_code is None:
            return
        price = models.resolve_unit_price(self.conn, company_id, item_code)
        self.unit_price_spin.setValue(price)
        self._recalc_amount()

    def _recalc_amount(self) -> None:
        amount = self.quantity_spin.value() * self.unit_price_spin.value()
        self.amount_label.setText(f"{amount:,.2f}")

    def _on_save(self) -> None:
        company_id = self.company_edit.current_key()
        item_code = self.item_edit.current_key()
        if company_id is None:
            QMessageBox.warning(self, "입력 오류", "거래처를 목록에서 선택해 주세요.")
            return
        if item_code is None:
            QMessageBox.warning(self, "입력 오류", "품번을 목록에서 선택해 주세요.")
            return
        try:
            models.add_transaction(
                self.conn,
                self.date_edit.date().toString("yyyy-MM-dd"),
                company_id,
                item_code,
                self.type_combo.currentText(),
                self.quantity_spin.value(),
                self.unit_price_spin.value(),
            )
        except ValueError as exc:
            QMessageBox.warning(self, "입력 오류", str(exc))
            return

        self._reset_form()
        self.transaction_saved.emit()

    def _on_import(self) -> None:
        rows = import_rows_from_excel(self, "거래내역 엑셀 가져오기")
        if rows is None:
            return
        added, failed = models.import_transactions(self.conn, rows)
        QMessageBox.information(self, "가져오기 완료", f"{added}건 추가, {failed}건 실패")
        if added:
            self.transaction_saved.emit()

    def _reset_form(self) -> None:
        self.date_edit.setDate(QDate.currentDate())
        self.company_edit.clear()
        self.item_edit.clear()
        self.type_combo.setCurrentIndex(0)
        self.quantity_spin.setValue(0)
        self.unit_price_spin.setValue(0)
        self._recalc_amount()
