"""품번/거래처명 자동완성 입력 위젯 (F-08)."""
from typing import List, Optional, Tuple

from PySide6.QtCore import Qt, QStringListModel
from PySide6.QtWidgets import QCompleter, QLineEdit


class KeyedAutocompleteEdit(QLineEdit):
    """표시용 레이블은 자동완성하되, 내부적으로는 DB 키(company_id/item_code)와 매핑한다."""

    def __init__(self, parent=None, placeholder: str = ""):
        super().__init__(parent)
        if placeholder:
            self.setPlaceholderText(placeholder)
        self._label_to_key = {}
        self._completer = QCompleter([], self)
        self._completer.setCaseSensitivity(Qt.CaseInsensitive)
        self._completer.setFilterMode(Qt.MatchContains)
        self._completer.setCompletionMode(QCompleter.PopupCompletion)
        self.setCompleter(self._completer)

    def set_options(self, pairs: List[Tuple[object, str]]) -> None:
        """pairs: [(key, label), ...]"""
        current_key = self.current_key()
        self._label_to_key = {label: key for key, label in pairs}
        model = QStringListModel([label for _, label in pairs], self)
        self._completer.setModel(model)
        if current_key is not None:
            self.set_by_key(current_key)

    def current_key(self) -> Optional[object]:
        return self._label_to_key.get(self.text().strip())

    def set_by_key(self, key: object) -> None:
        for label, k in self._label_to_key.items():
            if k == key:
                self.setText(label)
                return
        self.clear()

    def completer_widget(self) -> QCompleter:
        return self._completer
