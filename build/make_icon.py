"""生成 assets/icon.ico（多尺寸 PNG 压缩 ICO），纯 Qt 绘制，无需外部素材。

构图：白色照片卡片（内含山形与太阳）被左右两支向内箭头挤压 —— 表示"图片压缩"。
小尺寸（16/24）自动降级细节：去掉太阳、加粗箭头，保证缩到任务栏仍可辨认。

用法：
    python build/make_icon.py            生成 ico + png
    python build/make_icon.py --preview  额外输出各尺寸对照图 build/icon_preview.png
"""

from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QImage, QLinearGradient, QPainter, QPainterPath, QPolygonF

ROOT = Path(__file__).resolve().parents[1]
SIZES = (16, 24, 32, 48, 64, 128, 256)

WHITE = QColor("#FFFFFF")
CUT = QColor("#1B4FCB")  # 卡片内部镂空的颜色，与背景深蓝接近
SUPERSAMPLE = 4


def _background(p: QPainter) -> None:
    path = QPainterPath()
    path.addRoundedRect(QRectF(6, 6, 244, 244), 56, 56)
    grad = QLinearGradient(0, 0, 0, 256)
    grad.setColorAt(0.0, QColor("#4C8DF7"))
    grad.setColorAt(0.55, QColor("#2563EB"))
    grad.setColorAt(1.0, QColor("#1A48C4"))
    p.fillPath(path, QBrush(grad))

    gloss = QLinearGradient(0, 6, 0, 150)
    gloss.setColorAt(0.0, QColor(255, 255, 255, 52))
    gloss.setColorAt(1.0, QColor(255, 255, 255, 0))
    p.fillPath(path, QBrush(gloss))


def _photo_card(p: QPainter, tier: int, with_arrows: bool) -> None:
    """白色照片卡片：圆角矩形 + 镂空的山形与太阳。"""
    if with_arrows:
        rect, radius = QRectF(80, 80, 96, 96), 17
    else:
        # 16px：没有箭头，卡片独占版面，稍微放大
        rect, radius = QRectF(74, 74, 108, 108), 20

    card = QPainterPath()
    card.addRoundedRect(rect, radius, radius)
    p.fillPath(card, QBrush(WHITE))

    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(CUT))

    if tier >= 2:
        p.drawEllipse(QPointF(152, 106), 9.5, 9.5)
        # 双峰山形：右峰略低，与左峰部分重叠
        p.drawPolygon(QPolygonF([QPointF(92, 168), QPointF(114, 130), QPointF(136, 168)]))
        p.drawPolygon(QPolygonF([QPointF(126, 168), QPointF(148, 140), QPointF(168, 168)]))
    elif tier == 1:
        p.drawPolygon(QPolygonF([QPointF(92, 168), QPointF(128, 124), QPointF(164, 168)]))
    else:
        p.drawPolygon(QPolygonF([QPointF(86, 170), QPointF(128, 116), QPointF(170, 170)]))


def _arrow(p: QPainter, direction: int, tier: int) -> None:
    """向内挤压的箭头。direction=1 从左侧指右，-1 从右侧指左。"""
    if tier >= 2:
        shaft = QRectF(24, 116, 28, 24)
        head = [QPointF(52, 98), QPointF(52, 158), QPointF(76, 128)]
    else:
        # 24px：缩短箭杆、加高箭头，缩小时不至于糊成白点
        shaft = QRectF(22, 112, 26, 32)
        head = [QPointF(48, 90), QPointF(48, 166), QPointF(76, 128)]

    if direction < 0:  # 镜像到右侧
        shaft = QRectF(256 - shaft.x() - shaft.width(), shaft.y(), shaft.width(), shaft.height())
        head = [QPointF(256 - pt.x(), pt.y()) for pt in head]

    path = QPainterPath()
    path.addRect(shaft)
    path.addPolygon(QPolygonF(head))
    path = path.simplified()
    p.setPen(Qt.NoPen)
    p.fillPath(path, QBrush(WHITE))


def render(size: int) -> QImage:
    px = size * SUPERSAMPLE
    img = QImage(px, px, QImage.Format_ARGB32)
    img.fill(Qt.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing, True)
    p.scale(px / 256.0, px / 256.0)

    # 16px 去掉箭头，只保留照片卡片，避免三个元素挤成一团
    with_arrows = size > 16
    tier = 0 if size <= 16 else 1 if size <= 24 else 2

    _background(p)
    if with_arrows:
        _arrow(p, 1, tier)
        _arrow(p, -1, tier)
    _photo_card(p, tier, with_arrows)
    p.end()

    return img.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)


def build_ico() -> Path:
    frames: list[tuple[int, bytes]] = []
    tmp_path = ROOT / "build" / "_tmp_icon.png"
    for size in SIZES:
        img = render(size)
        img.save(str(tmp_path), "PNG")
        frames.append((size, tmp_path.read_bytes()))
    tmp_path.unlink(missing_ok=True)

    header = struct.pack("<HHH", 0, 1, len(frames))
    offset = 6 + 16 * len(frames)
    entries = b""
    payload = b""
    for size, data in frames:
        dim = 0 if size >= 256 else size
        entries += struct.pack("<BBBBHHII", dim, dim, 0, 0, 1, 32, len(data), offset)
        offset += len(data)
        payload += data

    out = ROOT / "assets" / "icon.ico"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(header + entries + payload)

    render(256).save(str(ROOT / "assets" / "icon.png"), "PNG")
    return out


def build_preview() -> Path:
    """对照图：上排原始尺寸，下排小尺寸放大 8 倍（最近邻），便于检查清晰度。"""
    sheet = QImage(1180, 470, QImage.Format_ARGB32)
    sheet.fill(QColor("#F2F4F7"))
    p = QPainter(sheet)
    p.setRenderHint(QPainter.SmoothPixmapTransform, True)

    x = 24
    for size in (256, 128, 64, 48, 32, 24, 16):
        img = render(size)
        p.drawImage(x, 20, img)
        p.setPen(QColor("#667085"))
        p.drawText(QRectF(x, 20 + max(size, 16) + 6, 120, 18), Qt.AlignLeft, f"{size}px")
        x += max(size, 24) + 26

    x = 24
    for size in (16, 24, 32, 48):
        img = render(size).scaled(size * 8, size * 8, Qt.KeepAspectRatio, Qt.FastTransformation)
        p.drawImage(x, 330, img)
        p.setPen(QColor("#667085"))
        p.drawText(QRectF(x, 330 + size * 8 + 4, 200, 18), Qt.AlignLeft, f"{size}px ×8")
        x += size * 8 + 30

    p.end()
    out = ROOT / "build" / "icon_preview.png"
    sheet.save(str(out), "PNG")
    return out


def main() -> int:
    from PySide6.QtWidgets import QApplication

    ap = argparse.ArgumentParser()
    ap.add_argument("--preview", action="store_true")
    args = ap.parse_args()

    app = QApplication(sys.argv)  # noqa: F841
    path = build_ico()
    print(f"icon written: {path}  ({path.stat().st_size} bytes)")
    if args.preview:
        print(f"preview: {build_preview()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
