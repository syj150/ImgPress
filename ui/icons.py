"""矢量绘制的界面图标。

不依赖外部图片资源，全部用 QPainter 现画，按 1x/2x 两种像素密度塞进 QIcon，
在高 DPI 下不会发虚。线条颜色跟随主题，悬停时切换为强调色。
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QImage, QPainter, QPainterPath, QPen, QPixmap

from . import theme

SIZES = (16, 20, 24, 32)


def _canvas(size: int, painter_fn) -> QPixmap:
    """在 size×size 的逻辑坐标里作画，实际按 2x 渲染并设置 DPR。"""
    scale = 2
    img = QImage(size * scale, size * scale, QImage.Format_ARGB32)
    img.fill(Qt.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing, True)
    p.scale(scale, scale)
    painter_fn(p, float(size))
    p.end()
    pm = QPixmap.fromImage(img)
    pm.setDevicePixelRatio(scale)
    return pm


def _pen(color: QColor, width: float) -> QPen:
    pen = QPen(color, width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    return pen


def _gear(p: QPainter, s: float, color: QColor) -> None:
    c = s / 2
    p.setPen(Qt.NoPen)
    p.setBrush(color)
    # 齿数随尺寸调整：小尺寸用 6 齿，否则 16px 下会糊成一圈
    teeth = 6 if s <= 20 else 8
    tooth_w = s * (0.20 if teeth == 6 else 0.17)
    for i in range(teeth):
        p.save()
        p.translate(c, c)
        p.rotate(i * (360 / teeth))
        p.drawRoundedRect(
            QRectF(-tooth_w / 2, -s * 0.47, tooth_w, s * 0.21),
            tooth_w * 0.30,
            tooth_w * 0.30,
        )
        p.restore()
    # 环体
    p.setPen(_pen(color, s * 0.16))
    p.setBrush(Qt.NoBrush)
    p.drawEllipse(QPointF(c, c), s * 0.25, s * 0.25)


def _file_plus(p: QPainter, s: float, color: QColor) -> None:
    w = s * 0.10
    p.setPen(_pen(color, w))
    p.setBrush(Qt.NoBrush)
    x0, y0, x1, y1 = s * 0.26, s * 0.12, s * 0.74, s * 0.88
    fold = s * 0.18
    doc = QPainterPath()
    doc.moveTo(x0 + s * 0.06, y0)
    doc.lineTo(x1 - fold, y0)
    doc.lineTo(x1, y0 + fold)
    doc.lineTo(x1, y1 - s * 0.06)
    doc.quadTo(x1, y1, x1 - s * 0.06, y1)
    doc.lineTo(x0 + s * 0.06, y1)
    doc.quadTo(x0, y1, x0, y1 - s * 0.06)
    doc.lineTo(x0, y0 + s * 0.06)
    doc.quadTo(x0, y0, x0 + s * 0.06, y0)
    p.drawPath(doc)
    # 折角
    p.drawLine(QPointF(x1 - fold, y0), QPointF(x1 - fold, y0 + fold))
    p.drawLine(QPointF(x1 - fold, y0 + fold), QPointF(x1, y0 + fold))
    # 加号
    cy = y1 - s * 0.24
    arm = s * 0.105
    p.drawLine(QPointF(cx := s * 0.50, cy - arm), QPointF(cx, cy + arm))
    p.drawLine(QPointF(cx - arm, cy), QPointF(cx + arm, cy))


def _folder_plus(p: QPainter, s: float, color: QColor) -> None:
    w = s * 0.10
    p.setPen(_pen(color, w))
    p.setBrush(Qt.NoBrush)
    x0, x1 = s * 0.12, s * 0.88
    y0, y1 = s * 0.20, s * 0.84
    path = QPainterPath()
    path.moveTo(x0, y1 - s * 0.06)
    path.lineTo(x0, y0 + s * 0.06)
    path.quadTo(x0, y0, x0 + s * 0.06, y0)
    path.lineTo(s * 0.40, y0)
    path.quadTo(s * 0.46, y0, s * 0.49, y0 + s * 0.05)
    path.lineTo(s * 0.53, y0 + s * 0.12)
    path.lineTo(x1 - s * 0.06, y0 + s * 0.12)
    path.quadTo(x1, y0 + s * 0.12, x1, y0 + s * 0.18)
    path.lineTo(x1, y1 - s * 0.06)
    path.quadTo(x1, y1, x1 - s * 0.06, y1)
    path.lineTo(x0 + s * 0.06, y1)
    path.quadTo(x0, y1, x0, y1 - s * 0.06)
    p.drawPath(path)
    cy = s * 0.52
    arm = s * 0.11
    p.drawLine(QPointF(s * 0.50 - arm, cy), QPointF(s * 0.50 + arm, cy))
    p.drawLine(QPointF(s * 0.50, cy - arm), QPointF(s * 0.50, cy + arm))


DRAWERS = {
    "gear": _gear,
    "file_plus": _file_plus,
    "folder_plus": _folder_plus,
}


def make(name: str, color: str = theme.TEXT_MUTED) -> QIcon:
    """生成图标。

    只提供 Normal / Disabled 两态：QIcon 的 Active 态会被"获得焦点的按钮"占用，
    用作悬停色会导致第一个按钮常亮，反而不像可点击，所以悬停反馈交给按钮底色。
    """
    drawer = DRAWERS[name]
    normal = QColor(color)
    disabled = QColor(theme.TEXT_SOFT)
    icon = QIcon()
    for size in SIZES:
        icon.addPixmap(_canvas(size, lambda p, s: drawer(p, s, normal)), QIcon.Normal, QIcon.Off)
        icon.addPixmap(_canvas(size, lambda p, s: drawer(p, s, disabled)), QIcon.Disabled, QIcon.Off)
    return icon
