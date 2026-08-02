"""F-07: 거래처/품목/거래처별 단가 마스터 데이터 관리."""
import sqlite3

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app import models
from app.excel_export import import_rows_from_excel
from app.ui.autocomplete import KeyedAutocompleteEdit


class MasterDataDialog(QDialog):
    """등록/수정 후 data_changed를 방출해 다른 화면의 자동완성 목록을 갱신하도록 한다."""

    data_changed = Signal()

    def __init__(self, conn: sqlite3.Connection, parent=None):
        super().__init__(parent)
        self.conn = conn
        self.setWindowTitle("마스터 데이터 관리")
        self.resize(700, 500)

        tabs = QTabWidget()
        tabs.addTab(self._build_company_tab(), "거래처")
        tabs.addTab(self._build_item_tab(), "품목")
        tabs.addTab(self._build_price_tab(), "거래처별 단가")

        close_button = QPushButton("닫기")
        close_button.clicked.connect(self.accept)
        button_row = QHBoxLayout()
        button_row.addStretch()
        button_row.addWidget(close_button)

        layout = QVBoxLayout(self)
        layout.addWidget(tabs)
        layout.addLayout(button_row)

    # ---------- 거래처 탭 ----------
    def _build_company_tab(self) -> QWidget:
        widget = QWidget()
        self.company_table = QTableWidget(0, 3)
        self.company_table.setHorizontalHeaderLabels(["ID", "거래처명", "담당자/연락처"])
        self.company_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.company_table.itemSelectionChanged.connect(self._on_company_row_selected)

        self.company_name_edit = QLineEdit()
        self.company_contact_edit = QLineEdit()
        add_button = QPushButton("추가")
        add_button.setProperty("accent", "primary")
        update_button = QPushButton("선택 항목 수정")
        import_button = QPushButton("엑셀로 가져오기")
        add_button.clicked.connect(self._add_company)
        update_button.clicked.connect(self._update_company)
        import_button.clicked.connect(self._import_companies)

        form = QFormLayout()
        form.addRow("거래처명", self.company_name_edit)
        form.addRow("담당자/연락처", self.company_contact_edit)

        button_row = QHBoxLayout()
        button_row.addWidget(add_button)
        button_row.addWidget(update_button)
        button_row.addWidget(import_button)

        layout = QVBoxLayout(widget)
        layout.addWidget(self.company_table)
        layout.addLayout(form)
        layout.addLayout(button_row)

        self._reload_company_table()
        return widget

    def _reload_company_table(self) -> None:
        companies = models.list_companies(self.conn)
        self.company_table.setRowCount(len(companies))
        for r, c in enumerate(companies):
            self.company_table.setItem(r, 0, QTableWidgetItem(str(c["company_id"])))
            self.company_table.setItem(r, 1, QTableWidgetItem(c["company_name"]))
            self.company_table.setItem(r, 2, QTableWidgetItem(c["contact"] or ""))

    def _on_company_row_selected(self) -> None:
        row = self.company_table.currentRow()
        if row < 0:
            return
        self.company_name_edit.setText(self.company_table.item(row, 1).text())
        self.company_contact_edit.setText(self.company_table.item(row, 2).text())

    def _add_company(self) -> None:
        name = self.company_name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "입력 오류", "거래처명을 입력해 주세요.")
            return
        try:
            models.add_company(self.conn, name, self.company_contact_edit.text().strip() or None)
        except sqlite3.IntegrityError:
            QMessageBox.warning(self, "입력 오류", "이미 존재하는 거래처명입니다.")
            return
        self._reload_company_table()
        self._refresh_dependents()

    def _import_companies(self) -> None:
        rows = import_rows_from_excel(self, "거래처 엑셀 가져오기")
        if rows is None:
            return
        added, skipped = models.import_companies(self.conn, rows)
        self._reload_company_table()
        self._refresh_dependents()
        QMessageBox.information(self, "가져오기 완료", f"{added}건 추가, {skipped}건 중복 제외")

    def _update_company(self) -> None:
        row = self.company_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "선택 오류", "수정할 거래처를 목록에서 선택해 주세요.")
            return
        company_id = int(self.company_table.item(row, 0).text())
        name = self.company_name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "입력 오류", "거래처명을 입력해 주세요.")
            return
        try:
            models.update_company(
                self.conn, company_id, name, self.company_contact_edit.text().strip() or None
            )
        except sqlite3.IntegrityError:
            QMessageBox.warning(self, "입력 오류", "이미 존재하는 거래처명입니다.")
            return
        self._reload_company_table()
        self._refresh_dependents()

    # ---------- 품목 탭 ----------
    def _build_item_tab(self) -> QWidget:
        widget = QWidget()
        self.item_table = QTableWidget(0, 4)
        self.item_table.setHorizontalHeaderLabels(["품번", "품명", "기본단가", "기초재고"])
        self.item_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.item_table.itemSelectionChanged.connect(self._on_item_row_selected)

        self.item_code_edit = QLineEdit()
        self.item_name_edit = QLineEdit()
        self.item_price_spin = QDoubleSpinBox()
        self.item_price_spin.setRange(-999_999_999, 999_999_999)
        self.item_price_spin.setDecimals(2)
        self.item_stock_spin = QDoubleSpinBox()
        self.item_stock_spin.setRange(0, 999_999_999)
        self.item_stock_spin.setDecimals(2)

        add_button = QPushButton("추가")
        add_button.setProperty("accent", "primary")
        update_button = QPushButton("선택 항목 수정")
        new_button = QPushButton("새 품목")
        import_button = QPushButton("엑셀로 가져오기")
        add_button.clicked.connect(self._add_item)
        update_button.clicked.connect(self._update_item)
        new_button.clicked.connect(self._clear_item_form)
        import_button.clicked.connect(self._import_items)

        form = QFormLayout()
        form.addRow("품번", self.item_code_edit)
        form.addRow("품명", self.item_name_edit)
        form.addRow("기본단가", self.item_price_spin)
        form.addRow("기초재고", self.item_stock_spin)

        button_row = QHBoxLayout()
        button_row.addWidget(add_button)
        button_row.addWidget(update_button)
        button_row.addWidget(new_button)
        button_row.addWidget(import_button)

        layout = QVBoxLayout(widget)
        layout.addWidget(self.item_table)
        layout.addLayout(form)
        layout.addLayout(button_row)

        self._reload_item_table()
        return widget

    def _reload_item_table(self) -> None:
        items = models.list_items(self.conn)
        self.item_table.setRowCount(len(items))
        for r, i in enumerate(items):
            self.item_table.setItem(r, 0, QTableWidgetItem(i["item_code"]))
            self.item_table.setItem(r, 1, QTableWidgetItem(i["item_name"]))
            self.item_table.setItem(r, 2, QTableWidgetItem(f'{i["default_unit_price"]:,.2f}'))
            self.item_table.setItem(r, 3, QTableWidgetItem(f'{i["initial_stock"]:,.2f}'))

    def _on_item_row_selected(self) -> None:
        row = self.item_table.currentRow()
        if row < 0:
            return
        self.item_code_edit.setText(self.item_table.item(row, 0).text())
        self.item_code_edit.setEnabled(False)  # 품번은 PK이므로 수정 시 변경 불가
        self.item_name_edit.setText(self.item_table.item(row, 1).text())
        self.item_price_spin.setValue(float(self.item_table.item(row, 2).text().replace(",", "")))
        self.item_stock_spin.setValue(float(self.item_table.item(row, 3).text().replace(",", "")))

    def _clear_item_form(self) -> None:
        self.item_table.clearSelection()
        self.item_code_edit.setEnabled(True)
        self.item_code_edit.clear()
        self.item_name_edit.clear()
        self.item_price_spin.setValue(0)
        self.item_stock_spin.setValue(0)

    def _add_item(self) -> None:
        code = self.item_code_edit.text().strip()
        name = self.item_name_edit.text().strip()
        if not code or not name:
            QMessageBox.warning(self, "입력 오류", "품번과 품명을 입력해 주세요.")
            return
        try:
            models.add_item(
                self.conn, code, name, self.item_price_spin.value(), self.item_stock_spin.value()
            )
        except sqlite3.IntegrityError:
            QMessageBox.warning(self, "입력 오류", "이미 존재하는 품번입니다.")
            return
        self._reload_item_table()
        self._clear_item_form()
        self._refresh_dependents()

    def _import_items(self) -> None:
        rows = import_rows_from_excel(self, "품목 엑셀 가져오기")
        if rows is None:
            return
        added, skipped = models.import_items(self.conn, rows)
        self._reload_item_table()
        self._refresh_dependents()
        QMessageBox.information(self, "가져오기 완료", f"{added}건 추가, {skipped}건 중복/오류 제외")

    def _update_item(self) -> None:
        row = self.item_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "선택 오류", "수정할 품목을 목록에서 선택해 주세요.")
            return
        code = self.item_table.item(row, 0).text()
        name = self.item_name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "입력 오류", "품명을 입력해 주세요.")
            return
        models.update_item(self.conn, code, name, self.item_price_spin.value(), self.item_stock_spin.value())
        self._reload_item_table()
        self.item_code_edit.setEnabled(True)
        self._refresh_dependents()

    # ---------- 거래처별 단가 탭 ----------
    def _build_price_tab(self) -> QWidget:
        widget = QWidget()
        self.price_company_combo = QComboBox()
        self.price_company_combo.currentIndexChanged.connect(self._reload_price_table)

        self.price_table = QTableWidget(0, 3)
        self.price_table.setHorizontalHeaderLabels(["품번", "품명", "단가"])
        self.price_table.setEditTriggers(QTableWidget.NoEditTriggers)

        self.price_item_edit = KeyedAutocompleteEdit(placeholder="품번 또는 품명 입력...")
        self.price_value_spin = QDoubleSpinBox()
        self.price_value_spin.setRange(-999_999_999, 999_999_999)
        self.price_value_spin.setDecimals(2)
        save_price_button = QPushButton("단가 저장")
        save_price_button.setProperty("accent", "primary")
        save_price_button.clicked.connect(self._save_price)

        form = QFormLayout()
        form.addRow("품번", self.price_item_edit)
        form.addRow("단가", self.price_value_spin)

        layout = QVBoxLayout(widget)
        layout.addWidget(QLabel("거래처 선택"))
        layout.addWidget(self.price_company_combo)
        layout.addWidget(self.price_table)
        layout.addLayout(form)
        layout.addWidget(save_price_button)

        self._reload_price_company_combo()
        self._reload_price_item_options()
        return widget

    def _reload_price_company_combo(self) -> None:
        self.price_company_combo.blockSignals(True)
        self.price_company_combo.clear()
        for c in models.list_companies(self.conn):
            self.price_company_combo.addItem(c["company_name"], c["company_id"])
        self.price_company_combo.blockSignals(False)
        self._reload_price_table()

    def _reload_price_item_options(self) -> None:
        items = models.list_items(self.conn)
        self.price_item_edit.set_options(
            [(i["item_code"], f'{i["item_code"]} - {i["item_name"]}') for i in items]
        )

    def _reload_price_table(self) -> None:
        company_id = self.price_company_combo.currentData()
        self.price_table.setRowCount(0)
        if company_id is None:
            return
        prices = models.list_prices_for_company(self.conn, company_id)
        self.price_table.setRowCount(len(prices))
        for r, p in enumerate(prices):
            self.price_table.setItem(r, 0, QTableWidgetItem(p["item_code"]))
            self.price_table.setItem(r, 1, QTableWidgetItem(p["item_name"]))
            self.price_table.setItem(r, 2, QTableWidgetItem(f'{p["unit_price"]:,.2f}'))

    def _save_price(self) -> None:
        company_id = self.price_company_combo.currentData()
        item_code = self.price_item_edit.current_key()
        if company_id is None:
            QMessageBox.warning(self, "입력 오류", "거래처를 선택해 주세요.")
            return
        if item_code is None:
            QMessageBox.warning(self, "입력 오류", "품번을 목록에서 선택해 주세요.")
            return
        models.set_company_price(self.conn, company_id, item_code, self.price_value_spin.value())
        self._reload_price_table()

    def _refresh_dependents(self) -> None:
        self._reload_price_company_combo()
        self._reload_price_item_options()
        self.data_changed.emit()
