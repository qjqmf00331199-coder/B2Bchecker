"""DESIGN-apple.md 토큰(색/타이포/라운드/여백)을 데스크톱 폼 UI에 맞게 적용한 전역 스타일시트.

제품 사진 갤러리(타일/히어로)는 이 앱(폼+테이블 기반)에 적용 대상이 아니므로 제외하고,
색/타이포/라운드 스케일/버튼 문법/그림자 없음 원칙만 가져온다.
"""

PRIMARY = "#0066cc"
PRIMARY_FOCUS = "#0071e3"
PRIMARY_ACTIVE = "#005bb8"
INK = "#1d1d1f"
INK_MUTED = "#7a7a7a"
CANVAS = "#ffffff"
PARCHMENT = "#f5f5f7"
HAIRLINE = "#e0e0e0"
DIVIDER = "#f0f0f0"
SURFACE_BLACK = "#000000"
SELECTION = "#cfe4fb"

# SF Pro Display/Text에는 한글 글리프가 없어 시스템 한글 폰트로 대체한다(디자인 문서의
# "Note on Font Substitutes" 원칙: system-ui 우선, 라틴 대체는 문서 값을 참고하되
# 한글 UI는 Malgun Gothic으로 대체).
FONT_FAMILY = "Malgun Gothic, Segoe UI, sans-serif"

STYLESHEET = f"""
QMainWindow, QDialog {{
    background: {PARCHMENT};
}}
QWidget {{
    font-family: {FONT_FAMILY};
    font-size: 13px;
    color: {INK};
}}
QGroupBox {{
    background: {CANVAS};
    border: 1px solid {HAIRLINE};
    border-radius: 18px;
    margin-top: 12px;
    padding: 16px;
    font-weight: 600;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
}}
QPushButton {{
    background: {CANVAS};
    color: {PRIMARY};
    border: 1px solid {PRIMARY};
    border-radius: 16px;
    padding: 7px 18px;
}}
QPushButton:hover {{
    background: {PARCHMENT};
}}
QPushButton:pressed {{
    background: {SELECTION};
}}
QPushButton[accent="primary"] {{
    background: {PRIMARY};
    color: #ffffff;
    border: none;
    font-weight: 600;
}}
QPushButton[accent="primary"]:hover {{
    background: {PRIMARY_FOCUS};
}}
QPushButton[accent="primary"]:pressed {{
    background: {PRIMARY_ACTIVE};
}}
QLineEdit, QDoubleSpinBox, QDateEdit, QComboBox {{
    background: {CANVAS};
    border: 1px solid {HAIRLINE};
    border-radius: 10px;
    padding: 6px 12px;
    selection-background-color: {SELECTION};
}}
QLineEdit:focus, QDoubleSpinBox:focus, QDateEdit:focus, QComboBox:focus {{
    border: 1.5px solid {PRIMARY};
}}
QTableWidget {{
    background: {CANVAS};
    border: 1px solid {HAIRLINE};
    border-radius: 12px;
    gridline-color: {DIVIDER};
}}
QTableWidget::item:selected {{
    background: {SELECTION};
    color: {INK};
}}
QHeaderView::section {{
    background: {PARCHMENT};
    color: {INK};
    border: none;
    border-bottom: 1px solid {HAIRLINE};
    padding: 8px;
    font-weight: 600;
}}
QTabWidget::pane {{
    border: 1px solid {HAIRLINE};
    border-radius: 12px;
    background: {CANVAS};
    top: -1px;
}}
QTabBar::tab {{
    padding: 8px 20px;
    margin-right: 4px;
    color: {INK_MUTED};
    background: transparent;
}}
QTabBar::tab:selected {{
    color: {PRIMARY};
    font-weight: 600;
}}
QToolBar {{
    background: {SURFACE_BLACK};
    spacing: 8px;
    padding: 8px;
    border: none;
}}
QToolBar QToolButton {{
    color: #ffffff;
    padding: 6px 14px;
    border-radius: 8px;
}}
QToolBar QToolButton:hover {{
    background: #333333;
}}
QCheckBox {{
    spacing: 8px;
}}
"""
