"""可复用的小部件：卡片、字段行、禁用滚轮误触的输入控件。"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


class Card(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Card")


class Divider(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Divider")
        self.setFixedHeight(1)


class _NoWheel:
    """滚轮在未聚焦时不改变数值，让事件继续传给外层滚动区。"""

    def wheelEvent(self, event):  # noqa: N802
        if self.hasFocus():
            super().wheelEvent(event)
        else:
            event.ignore()


class Spin(_NoWheel, QSpinBox):
    pass


class DSpin(_NoWheel, QDoubleSpinBox):
    pass


class Combo(_NoWheel, QComboBox):
    pass


class Check(QCheckBox):
    def __init__(self, text: str = "", tip: str = "", parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        if tip:
            self.setToolTip(tip)


def section_label(text: str, tip: str = "") -> QLabel:
    label = QLabel(text)
    label.setObjectName("SectionTitle")
    if tip:
        label.setToolTip(tip)
    return label


def hint_label(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("Hint")
    label.setWordWrap(True)
    return label


def field_label(text: str, tip: str = "") -> QLabel:
    label = QLabel(text)
    label.setObjectName("FieldLabel")
    if tip:
        label.setToolTip(tip)
    return label


class InfoDot(QLabel):
    """参数说明入口：悬停显示参数手册要点。"""

    def __init__(self, tip: str, parent: QWidget | None = None) -> None:
        super().__init__("?", parent)
        self.setToolTip(tip)
        self.setFixedSize(15, 15)
        self.setAlignment(Qt.AlignCenter)
        self.setCursor(Qt.WhatsThisCursor)
        self.setStyleSheet(
            "QLabel{color:#98A2B3;border:1px solid #E1E5EA;border-radius:7px;"
            "font-size:10px;background:transparent;}"
            "QLabel:hover{color:#2563EB;border-color:#BFD3FE;background:#EFF4FF;}"
        )


def row_with(widget: QWidget, tip: str = "", trailing: QWidget | None = None) -> QWidget:
    box = QWidget()
    layout = QHBoxLayout(box)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(6)
    layout.addWidget(widget, 1)
    if trailing is not None:
        layout.addWidget(trailing, 0)
    if tip:
        layout.addWidget(InfoDot(tip), 0)
    return box


def vstack(*widgets: QWidget, spacing: int = 8, margins: tuple[int, int, int, int] = (0, 0, 0, 0)) -> QWidget:
    box = QWidget()
    layout = QVBoxLayout(box)
    layout.setContentsMargins(*margins)
    layout.setSpacing(spacing)
    for w in widgets:
        layout.addWidget(w)
    return box


def hstack(*widgets: QWidget, spacing: int = 8, margins: tuple[int, int, int, int] = (0, 0, 0, 0)) -> QWidget:
    box = QWidget()
    layout = QHBoxLayout(box)
    layout.setContentsMargins(*margins)
    layout.setSpacing(spacing)
    for w in widgets:
        layout.addWidget(w)
    return box
