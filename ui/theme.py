"""浅色主题：调色板与全局样式表。"""

from __future__ import annotations

from PySide6.QtGui import QColor, QFont, QFontDatabase

BG = "#F2F4F7"
SURFACE = "#FFFFFF"
SURFACE_ALT = "#F9FAFB"
BORDER = "#E4E7EC"
BORDER_STRONG = "#D0D5DD"
TEXT = "#101828"
TEXT_MUTED = "#667085"
TEXT_SOFT = "#98A2B3"
ACCENT = "#2563EB"
ACCENT_HOVER = "#1D4ED8"
ACCENT_PRESSED = "#1E40AF"
ACCENT_SOFT = "#EFF4FF"
OK = "#067647"
WARN = "#B54708"
ERR = "#B42318"

MONO_FAMILIES = ("Cascadia Mono", "Consolas", "JetBrains Mono", "Courier New")
UI_FAMILIES = ("Microsoft YaHei UI", "Microsoft YaHei", "Segoe UI", "PingFang SC", "sans-serif")


def qcolor(hex_str: str) -> QColor:
    return QColor(hex_str)


def mono_font(size: int = 9) -> QFont:
    db = QFontDatabase
    families = db.families()
    for name in MONO_FAMILIES:
        if name in families:
            return QFont(name, size)
    font = QFont("Consolas", size)
    font.setStyleHint(QFont.Monospace)
    return font


def ui_font(size: int = 9, weight: int = 400) -> QFont:
    families = QFontDatabase.families()
    for name in UI_FAMILIES:
        if name in families:
            font = QFont(name, size)
            font.setWeight(QFont.Weight(weight))
            return font
    font = QFont()
    font.setPointSize(size)
    font.setWeight(QFont.Weight(weight))
    return font


QSS = f"""
* {{
    font-family: "Microsoft YaHei UI", "Microsoft YaHei", "Segoe UI";
    outline: none;
}}

QWidget {{
    color: {TEXT};
    font-size: 13px;
}}

QMainWindow, QDialog {{
    background: {BG};
}}

QToolTip {{
    background: #1F2937;
    color: #F9FAFB;
    border: none;
    padding: 6px 8px;
    font-size: 12px;
}}

/* ---------- 卡片 ---------- */
QFrame#Card {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 10px;
}}

QFrame#Header {{
    background: {SURFACE};
    border-bottom: 1px solid {BORDER};
}}

QFrame#Footer {{
    background: {SURFACE};
    border-top: 1px solid {BORDER};
}}

QFrame#Divider {{
    background: {BORDER};
    max-height: 1px;
    border: none;
}}

/* ---------- 文本 ---------- */
QLabel#Title {{
    font-size: 19px;
    font-weight: 600;
    color: {TEXT};
}}

QLabel#Subtitle {{
    color: {TEXT_MUTED};
    font-size: 12px;
}}

QLabel#SectionTitle {{
    font-size: 13px;
    font-weight: 600;
    color: {TEXT};
}}

QLabel#FieldLabel {{
    color: #475467;
    font-size: 12.5px;
}}

QLabel#Hint {{
    color: {TEXT_MUTED};
    font-size: 12px;
}}

QLabel#Mono {{
    font-family: "Cascadia Mono", "Consolas", monospace;
    font-size: 12px;
    color: #344054;
}}

QLabel#MicroHint {{
    color: {TEXT_SOFT};
    font-size: 11.5px;
}}

QLabel#Link {{
    color: {ACCENT};
    font-size: 12px;
}}

QLabel#Badge {{
    background: {ACCENT_SOFT};
    color: {ACCENT_HOVER};
    border-radius: 5px;
    padding: 2px 7px;
    font-size: 11.5px;
}}

QLabel#EmptyTitle {{
    color: #475467;
    font-size: 14px;
    font-weight: 600;
}}

QLabel#EmptyHint {{
    color: {TEXT_SOFT};
    font-size: 12.5px;
}}

/* ---------- 按钮 ---------- */
QPushButton {{
    background: {SURFACE};
    border: 1px solid {BORDER_STRONG};
    border-radius: 7px;
    padding: 6px 13px;
    color: #344054;
    font-size: 13px;
}}
QPushButton:hover {{
    background: #F9FAFB;
    border-color: #B4BCC8;
}}
QPushButton:pressed {{
    background: #F2F4F7;
}}
QPushButton:disabled {{
    color: {TEXT_SOFT};
    border-color: {BORDER};
    background: {SURFACE_ALT};
}}

QPushButton[role="primary"] {{
    background: {ACCENT};
    border: 1px solid {ACCENT};
    color: #FFFFFF;
    font-weight: 600;
    padding: 8px 20px;
}}
QPushButton[role="primary"]:hover {{
    background: {ACCENT_HOVER};
    border-color: {ACCENT_HOVER};
}}
QPushButton[role="primary"]:pressed {{
    background: {ACCENT_PRESSED};
}}
QPushButton[role="primary"]:disabled {{
    background: #B9C6E6;
    border-color: #B9C6E6;
    color: #F2F4F7;
}}

QPushButton[role="ghost"] {{
    background: transparent;
    border: none;
    color: #475467;
    padding: 6px 9px;
}}
QPushButton[role="ghost"]:hover {{
    background: #F2F4F7;
    color: {TEXT};
}}

QPushButton[role="danger"] {{
    color: {ERR};
    border-color: #F3C6C0;
}}
QPushButton[role="danger"]:hover {{
    background: #FEF3F2;
    border-color: #E9A9A1;
}}

/* ---------- 输入控件 ---------- */
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
    background: {SURFACE};
    border: 1px solid {BORDER_STRONG};
    border-radius: 6px;
    padding: 5px 8px;
    min-height: 20px;
    selection-background-color: {ACCENT_SOFT};
    selection-color: {TEXT};
}}
QLineEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover, QComboBox:hover {{
    border-color: #B4BCC8;
}}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
    border-color: {ACCENT};
    background: #FFFFFF;
}}
QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled, QComboBox:disabled {{
    background: {SURFACE_ALT};
    color: {TEXT_SOFT};
    border-color: {BORDER};
}}

QSpinBox, QDoubleSpinBox {{
    padding-right: 18px;
}}
QSpinBox::up-button, QDoubleSpinBox::up-button,
QSpinBox::down-button, QDoubleSpinBox::down-button {{
    width: 16px;
    background: transparent;
    border: none;
}}
QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {{
    background: #EEF2F6;
    border-radius: 3px;
}}

QComboBox::drop-down {{
    border: none;
    width: 20px;
}}
QComboBox::down-arrow {{
    image: url(__CHEVRON__);
    width: 10px;
    height: 6px;
}}
QComboBox QAbstractItemView {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 4px;
    selection-background-color: {ACCENT_SOFT};
    selection-color: {TEXT};
    outline: none;
}}

QCheckBox {{
    spacing: 7px;
    color: #344054;
}}
QCheckBox::indicator {{
    width: 15px;
    height: 15px;
    border-radius: 4px;
    border: 1px solid {BORDER_STRONG};
    background: {SURFACE};
}}
QCheckBox::indicator:hover {{
    border-color: {ACCENT};
}}
QCheckBox::indicator:checked {{
    background: {ACCENT};
    border-color: {ACCENT};
    image: url(__CHECK__);
}}
QCheckBox::indicator:checked:disabled {{
    background: #B9C6E6;
    border-color: #B9C6E6;
}}

/* ---------- 标签页（分段控件风格） ---------- */
QTabWidget::pane {{
    border: none;
    background: transparent;
}}
QTabBar {{
    qproperty-drawBase: 0;
}}
QTabBar::tab {{
    background: {SURFACE_ALT};
    border: 1px solid {BORDER};
    border-radius: 7px;
    padding: 6px 13px;
    margin-right: 5px;
    color: #475467;
    font-size: 12.5px;
}}
QTabBar::tab:hover {{
    background: #F2F4F7;
    color: {TEXT};
}}
QTabBar::tab:selected {{
    background: {ACCENT_SOFT};
    border-color: #BFD3FE;
    color: {ACCENT_HOVER};
    font-weight: 600;
}}

/* ---------- 表格 ---------- */
QTableView {{
    background: {SURFACE};
    border: none;
    gridline-color: transparent;
    selection-background-color: #F0F5FF;
    selection-color: {TEXT};
    alternate-background-color: #FCFCFD;
}}
QTableView::item {{
    padding: 5px 8px;
    border-bottom: 1px solid #F2F4F7;
}}
QTableView::item:selected {{
    background: #F0F5FF;
    color: {TEXT};
}}
QHeaderView::section {{
    background: {SURFACE_ALT};
    color: {TEXT_MUTED};
    border: none;
    border-bottom: 1px solid {BORDER};
    border-right: 1px solid #F2F4F7;
    padding: 7px 8px;
    font-size: 12px;
    font-weight: 600;
}}
QHeaderView::section:last {{
    border-right: none;
}}

/* ---------- 进度条 ---------- */
QProgressBar {{
    background: #EAECF0;
    border: none;
    border-radius: 4px;
    height: 8px;
    text-align: center;
    color: transparent;
}}
QProgressBar::chunk {{
    background: {ACCENT};
    border-radius: 4px;
}}

/* ---------- 滚动区 ---------- */
QScrollArea {{
    border: none;
    background: transparent;
}}
QScrollArea > QWidget#qt_scrollarea_viewport {{
    background: transparent;
}}
QScrollArea > QWidget > QWidget {{
    background: transparent;
}}
QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 2px;
}}
QScrollBar::handle:vertical {{
    background: #D0D5DD;
    border-radius: 4px;
    min-height: 28px;
}}
QScrollBar::handle:vertical:hover {{
    background: #B4BCC8;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    height: 0;
    background: transparent;
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 10px;
    margin: 2px;
}}
QScrollBar::handle:horizontal {{
    background: #D0D5DD;
    border-radius: 4px;
    min-width: 28px;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal,
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
    width: 0;
    background: transparent;
}}

/* ---------- 日志 ---------- */
QPlainTextEdit#Log {{
    background: {SURFACE_ALT};
    border: 1px solid {BORDER};
    border-radius: 8px;
    color: #344054;
    font-family: "Cascadia Mono", "Consolas", monospace;
    font-size: 12px;
    padding: 8px;
}}

QSplitter::handle {{
    background: transparent;
    width: 10px;
}}

QMenu {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 5px;
}}
QMenu::item {{
    padding: 6px 22px 6px 14px;
    border-radius: 5px;
}}
QMenu::item:selected {{
    background: {ACCENT_SOFT};
    color: {TEXT};
}}
QMenu::separator {{
    height: 1px;
    background: {BORDER};
    margin: 4px 6px;
}}

QGraphicsView {{
    border: 1px solid {BORDER};
    border-radius: 8px;
    background: #0F1115;
}}
"""


def _draw_check(path) -> None:
    from PySide6.QtCore import QPointF, Qt
    from PySide6.QtGui import QImage, QPainter, QPen

    img = QImage(48, 48, QImage.Format_ARGB32)
    img.fill(Qt.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing, True)
    pen = QPen(QColor("#FFFFFF"), 7.0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    p.setPen(pen)
    p.drawPolyline([QPointF(12, 25), QPointF(21, 34), QPointF(37, 14)])
    p.end()
    img.save(str(path), "PNG")


def _draw_chevron(path) -> None:
    from PySide6.QtCore import QPointF, Qt
    from PySide6.QtGui import QImage, QPainter, QPen

    img = QImage(40, 24, QImage.Format_ARGB32)
    img.fill(Qt.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing, True)
    pen = QPen(QColor("#475467"), 4.2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    p.setPen(pen)
    p.drawPolyline([QPointF(8, 8), QPointF(20, 19), QPointF(32, 8)])
    p.end()
    img.save(str(path), "PNG")


def ensure_assets() -> tuple[str, str]:
    from core import paths

    folder = paths.cache_dir() / "ui"
    folder.mkdir(parents=True, exist_ok=True)
    check = folder / "check.png"
    chevron = folder / "chevron.png"
    if not check.exists():
        _draw_check(check)
    if not chevron.exists():
        _draw_chevron(chevron)
    return check.as_posix(), chevron.as_posix()


def stylesheet() -> str:
    check, chevron = ensure_assets()
    return QSS.replace("__CHECK__", check).replace("__CHEVRON__", chevron)


def apply(app) -> None:
    from PySide6.QtGui import QPalette

    app.setStyle("Fusion")
    app.setFont(ui_font(9))
    app.setStyleSheet(stylesheet())
    palette = app.palette()
    palette.setColor(QPalette.Link, qcolor(ACCENT))
    palette.setColor(QPalette.LinkVisited, qcolor(ACCENT_PRESSED))
    app.setPalette(palette)
