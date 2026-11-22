"""原图 / 结果 并排对比预览：同步缩放与平移，像素级查看。"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import QImage, QPainter, QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QGraphicsPixmapItem,
    QGraphicsScene,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from i18n import tr

from core import imageops
from core.runner import Job
from core.tools import Toolchain
from core.util import fmt_bytes
from . import theme
from .widgets import Card


class ZoomView(QGraphicsView):
    zoom_changed = Signal(float)
    view_moved = Signal(int, int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self._item: QGraphicsPixmapItem | None = None
        self.setRenderHints(QPainter.SmoothPixmapTransform | QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setBackgroundBrush(theme.qcolor("#0F1115"))
        self._syncing = False
        self.horizontalScrollBar().valueChanged.connect(self._emit_moved)
        self.verticalScrollBar().valueChanged.connect(self._emit_moved)

    def set_image(self, image: QImage) -> None:
        self._scene.clear()
        self._item = self._scene.addPixmap(QPixmap.fromImage(image))
        self._scene.setSceneRect(self._item.boundingRect())

    def fit(self) -> None:
        if self._item:
            self.resetTransform()
            self.fitInView(self._item, Qt.KeepAspectRatio)
            self.zoom_changed.emit(self.scale_factor())

    def actual_size(self) -> None:
        if self._item:
            self.resetTransform()
            self.zoom_changed.emit(1.0)

    def set_scale(self, scale: float) -> None:
        if not self._item:
            return
        self.resetTransform()
        self.scale(scale, scale)
        self.zoom_changed.emit(scale)

    def scale_factor(self) -> float:
        return self.transform().m11()

    def wheelEvent(self, event):  # noqa: N802
        if not self._item:
            return
        step = 1.25 if event.angleDelta().y() > 0 else 1 / 1.25
        new_scale = self.scale_factor() * step
        if new_scale < 0.02 or new_scale > 40:
            return
        self.scale(step, step)
        self.zoom_changed.emit(self.scale_factor())

    def _emit_moved(self, _=None) -> None:
        if self._syncing:
            return
        self.view_moved.emit(self.horizontalScrollBar().value(), self.verticalScrollBar().value())

    def apply_scroll(self, x: int, y: int) -> None:
        self._syncing = True
        self.horizontalScrollBar().setValue(x)
        self.verticalScrollBar().setValue(y)
        self._syncing = False


class PreviewDialog(QDialog):
    def __init__(self, job: Job, tools: Toolchain, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.job = job
        self.tools = tools
        self.setWindowTitle(tr("预览对比 — {name}", name=job.name))
        self.setMinimumSize(980, 660)
        self.resize(1320, 860)

        self.left = ZoomView()
        self.right = ZoomView()
        self.left.zoom_changed.connect(self._sync_zoom)
        self.left.view_moved.connect(lambda x, y: self.right.apply_scroll(x, y))
        self.right.view_moved.connect(lambda x, y: self.left.apply_scroll(x, y))

        self.title_left, self.meta_left = self._panel_header(tr("原图"), theme.TEXT_MUTED)
        self.title_right, self.meta_right = self._panel_header(tr("结果"), theme.ACCENT)

        left_card = self._panel(self.title_left, self.meta_left, self.left)
        right_card = self._panel(self.title_right, self.meta_right, self.right)

        body = QHBoxLayout()
        body.setSpacing(10)
        body.addWidget(left_card, 1)
        body.addWidget(right_card, 1)

        self.zoom_label = QLabel("100%")
        self.zoom_label.setObjectName("Mono")
        self.zoom_label.setFixedWidth(52)
        self.zoom_label.setAlignment(Qt.AlignCenter)
        btn_fit = QPushButton(tr("适应窗口"))
        btn_actual = QPushButton("1:1")
        btn_out = QPushButton("−")
        btn_in = QPushButton("+")
        btn_close = QPushButton(tr("关闭"))
        btn_close.setProperty("role", "primary")
        for b in (btn_out, btn_in):
            b.setFixedWidth(34)

        footer = QHBoxLayout()
        footer.setSpacing(6)
        footer.addWidget(QLabel(tr("缩放")))
        footer.addWidget(btn_out)
        footer.addWidget(self.zoom_label)
        footer.addWidget(btn_in)
        footer.addSpacing(8)
        footer.addWidget(btn_fit)
        footer.addWidget(btn_actual)
        footer.addStretch(1)
        footer.addWidget(btn_close)

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 12)
        root.setSpacing(10)
        root.addLayout(body, 1)
        root.addLayout(footer)

        btn_fit.clicked.connect(self._fit)
        btn_actual.clicked.connect(self._actual)
        btn_in.clicked.connect(lambda: self._zoom_by(1.25))
        btn_out.clicked.connect(lambda: self._zoom_by(1 / 1.25))
        btn_close.clicked.connect(self.accept)

        self._load()

    # ---------- 构建 ----------
    def _panel_header(self, title: str, color: str) -> tuple[QLabel, QLabel]:
        t = QLabel(title)
        t.setStyleSheet(f"QLabel{{color:{color};font-size:12px;font-weight:600;}}")
        m = QLabel("")
        m.setObjectName("Hint")
        return t, m

    def _panel(self, title: QLabel, meta: QLabel, view: QWidget) -> QWidget:
        card = Card()
        head = QHBoxLayout()
        head.setContentsMargins(2, 0, 2, 0)
        head.addWidget(title)
        head.addSpacing(8)
        head.addWidget(meta)
        head.addStretch(1)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 9, 10, 10)
        layout.setSpacing(7)
        layout.addLayout(head)
        layout.addWidget(view, 1)
        return card

    # ---------- 数据 ----------
    def _load(self) -> None:
        job = self.job
        self.setCursor(Qt.WaitCursor)
        try:
            src_path = imageops.source_preview(job.src, self.tools)
            src_img = QImage(str(src_path))
            if src_img.isNull():
                src_img = QImage(str(job.src))
        except Exception:
            src_img = QImage(str(job.src))
        finally:
            self.setCursor(Qt.ArrowCursor)

        if not src_img.isNull():
            self.left.set_image(src_img)
            self.meta_left.setText(
                f"{src_img.width()} × {src_img.height()} · {fmt_bytes(job.src_size)}"
            )

        dst = job.dst
        if dst and Path(dst).exists():
            self.setCursor(Qt.WaitCursor)
            try:
                shown = imageops.cached_preview(dst, job.codec, self.tools)
                dst_img = QImage(str(shown))
            except Exception as exc:
                dst_img = QImage()
                self.meta_right.setText(tr("无法解码：{reason}", reason=exc))
            finally:
                self.setCursor(Qt.ArrowCursor)
            if not dst_img.isNull():
                self.right.set_image(dst_img)
                parts = [f"{dst_img.width()} × {dst_img.height()}", fmt_bytes(job.out_size)]
                if job.out_size and job.src_size:
                    parts.append(f"{job.out_size / job.src_size * 100:.1f}%")
                if job.s2 is not None:
                    parts.append(f"S2 {job.s2:.2f}")
                self.meta_right.setText(" · ".join(parts))
        else:
            self.meta_right.setText(tr("尚未生成结果"))

        self._fit()

    # ---------- 缩放联动 ----------
    def _fit(self) -> None:
        self.left.fit()
        self.right.fit()
        self._update_zoom_label()

    def _actual(self) -> None:
        self.left.actual_size()
        self.right.actual_size()
        self._update_zoom_label()

    def _zoom_by(self, factor: float) -> None:
        scale = self.left.scale_factor() * factor
        self.left.set_scale(scale)
        self.right.set_scale(scale)
        self._update_zoom_label()

    def _sync_zoom(self, scale: float) -> None:
        if abs(self.right.scale_factor() - scale) > 1e-6:
            self.right.set_scale(scale)
        self._update_zoom_label(scale)

    def _update_zoom_label(self, scale: float | None = None) -> None:
        s = self.left.scale_factor() if scale is None else scale
        self.zoom_label.setText(f"{s * 100:.0f}%")
