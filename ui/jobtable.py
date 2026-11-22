"""工作区表格：数据模型、委托、空状态与拖放。"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QObject, Qt, Signal
from PySide6.QtGui import QAction, QColor, QGuiApplication
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMenu,
    QPushButton,
    QStackedLayout,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from i18n import tr

from core import imageops
from core.runner import CANCELED, DONE, FAILED, PENDING, RUNNING, SKIPPED, STATUS_LABEL, Job
from core.util import fmt_bpp, fmt_bytes, fmt_duration
from . import theme
from .widgets import Card

INPUT_EXTS = {".png", ".jpg", ".jpeg", ".jfif", ".webp", ".bmp", ".tif", ".tiff", ".gif", ".avif", ".jxl"}

COL_NAME, COL_STATUS, COL_SIZE, COL_SRC, COL_DST, COL_RATIO, COL_BPP, COL_S2, COL_TIME = range(9)

HEADERS = ["文件", "状态", "尺寸", "原始", "输出", "比例", "bpp", "S2", "耗时"]
WIDTHS = {COL_STATUS: 78, COL_SIZE: 98, COL_SRC: 82, COL_DST: 82, COL_RATIO: 118, COL_BPP: 56, COL_S2: 66, COL_TIME: 74}

STATUS_COLOR = {
    PENDING: theme.TEXT_SOFT,
    RUNNING: theme.ACCENT,
    DONE: theme.OK,
    FAILED: theme.ERR,
    SKIPPED: theme.WARN,
    CANCELED: theme.TEXT_MUTED,
}


class JobModel(QAbstractTableModel):
    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.jobs: list[Job] = []
        self._keys: set[str] = set()
        self._mono = theme.mono_font(9)

    # ---------- Qt 接口 ----------
    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(self.jobs)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(HEADERS)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole):  # noqa: N802
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return tr(HEADERS[section])
        if role == Qt.TextAlignmentRole and orientation == Qt.Horizontal:
            if section == COL_NAME:
                return int(Qt.AlignLeft | Qt.AlignVCenter)
            if section == COL_STATUS:
                return int(Qt.AlignCenter)
            return int(Qt.AlignRight | Qt.AlignVCenter)
        return None

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid() or index.row() >= len(self.jobs):
            return None
        job = self.jobs[index.row()]
        col = index.column()

        if role == Qt.DisplayRole:
            return self._text(job, col)
        if role == Qt.ToolTipRole:
            return self._tooltip(job)
        if role == Qt.TextAlignmentRole:
            if col == COL_STATUS:
                return int(Qt.AlignCenter)
            if col in (COL_NAME,):
                return int(Qt.AlignLeft | Qt.AlignVCenter)
            return int(Qt.AlignRight | Qt.AlignVCenter)
        if role == Qt.ForegroundRole:
            if col == COL_STATUS:
                return QColor(STATUS_COLOR.get(job.status, theme.TEXT))
            if col == COL_RATIO and job.out_size is not None and job.src_size:
                return QColor(theme.OK if job.out_size < job.src_size else theme.WARN)
            if col in (COL_SRC, COL_DST, COL_SIZE, COL_BPP, COL_S2, COL_TIME):
                return QColor(theme.TEXT_MUTED)
            if col == COL_NAME and job.status == FAILED:
                return QColor(theme.ERR)
            return None
        if role == Qt.FontRole and col in (COL_SIZE, COL_SRC, COL_DST, COL_RATIO, COL_BPP, COL_S2, COL_TIME, COL_STATUS):
            return self._mono
        return None

    # ---------- 渲染内容 ----------
    @staticmethod
    def _text(job: Job, col: int) -> str:
        if col == COL_NAME:
            return job.name
        if col == COL_STATUS:
            return tr(STATUS_LABEL.get(job.status, job.status))
        if col == COL_SIZE:
            return job.size_text
        if col == COL_SRC:
            return fmt_bytes(job.src_size)
        if col == COL_DST:
            return fmt_bytes(job.out_size)
        if col == COL_RATIO:
            if job.out_size is None or not job.src_size:
                return "—"
            pct = job.out_size / job.src_size * 100
            delta = pct - 100
            sign = "+" if delta > 0 else "−"
            return f"{pct:.1f}%  ({sign}{abs(delta):.1f}%)"
        if col == COL_BPP:
            return fmt_bpp(job.out_size, job.width, job.height)
        if col == COL_S2:
            return f"{job.s2:.2f}" if job.s2 is not None else "—"
        if col == COL_TIME:
            return fmt_duration(job.elapsed)
        return ""

    @staticmethod
    def _tooltip(job: Job) -> str:
        lines = [tr("源文件：{path}", path=job.src)]
        if job.dst:
            lines.append(tr("输出：{path}", path=job.dst))
        if job.message:
            lines.append(tr("说明：{text}", text=job.message))
        if job.command:
            lines.append("")
            lines.append(job.command)
        return "\n".join(lines)

    # ---------- 数据操作 ----------
    def add_paths(self, paths: list[Path], codec: str) -> tuple[int, int]:
        """返回 (新增条数, 忽略条数)。目录会递归展开。"""
        files: list[Path] = []
        ignored = 0
        for p in paths:
            p = Path(p)
            if p.is_dir():
                for child in sorted(p.rglob("*")):
                    if child.is_file() and child.suffix.lower() in INPUT_EXTS:
                        files.append(child)
            elif p.is_file():
                if p.suffix.lower() in INPUT_EXTS:
                    files.append(p)
                    continue
                ignored += 1
            else:
                ignored += 1

        added = 0
        start = len(self.jobs)
        fresh: list[Job] = []
        for f in files:
            key = str(f.resolve()).lower()
            if key in self._keys:
                continue
            self._keys.add(key)
            size = f.stat().st_size if f.exists() else 0
            size_px = imageops.probe_size(f)
            job = Job(
                src=f,
                codec=codec,
                src_size=size,
                width=size_px[0] if size_px else 0,
                height=size_px[1] if size_px else 0,
            )
            fresh.append(job)
            added += 1
        if fresh:
            self.beginInsertRows(QModelIndex(), start, start + len(fresh) - 1)
            self.jobs.extend(fresh)
            self.endInsertRows()
        return added, ignored

    def remove_rows(self, rows: list[int]) -> None:
        for row in sorted(set(rows), reverse=True):
            if 0 <= row < len(self.jobs):
                self.beginRemoveRows(QModelIndex(), row, row)
                job = self.jobs.pop(row)
                self._keys.discard(str(job.src.resolve()).lower())
                self.endRemoveRows()

    def clear(self) -> None:
        if not self.jobs:
            return
        self.beginResetModel()
        self.jobs.clear()
        self._keys.clear()
        self.endResetModel()

    def reset_status(self, codec: str) -> None:
        for job in self.jobs:
            job.codec = codec
            job.status = PENDING
            job.dst = None
            job.out_size = None
            job.s2 = None
            job.elapsed = None
            job.message = ""
            job.command = ""
        if self.jobs:
            self.dataChanged.emit(self.index(0, 0), self.index(len(self.jobs) - 1, len(HEADERS) - 1))

    def refresh(self, row: int | None = None) -> None:
        if not self.jobs:
            return
        if row is None:
            self.dataChanged.emit(self.index(0, 0), self.index(len(self.jobs) - 1, len(HEADERS) - 1))
        elif 0 <= row < len(self.jobs):
            self.dataChanged.emit(self.index(row, 0), self.index(row, len(HEADERS) - 1))

    def total_bytes(self) -> int:
        return sum(j.src_size for j in self.jobs)


class JobTable(QTableView):
    activated_row = Signal(int)
    rows_removed = Signal(list)
    selection_changed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setShowGrid(False)
        self.setWordWrap(False)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setAlternatingRowColors(True)
        self.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.verticalHeader().setVisible(False)
        self.verticalHeader().setDefaultSectionSize(34)
        self.setTextElideMode(Qt.ElideMiddle)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._menu)
        self.doubleClicked.connect(lambda idx: self.activated_row.emit(idx.row()))
        self.locked = False

    def set_job_model(self, model: JobModel) -> None:
        self.setModel(model)
        header = self.horizontalHeader()
        header.setHighlightSections(False)
        header.setSectionsMovable(False)
        header.setSectionResizeMode(COL_NAME, QHeaderView.Stretch)
        for col, width in WIDTHS.items():
            header.setSectionResizeMode(col, QHeaderView.Fixed)
            self.setColumnWidth(col, width)
        if self.selectionModel():
            self.selectionModel().selectionChanged.connect(lambda *_: self.selection_changed.emit())

    def selected_rows(self) -> list[int]:
        return sorted({i.row() for i in self.selectionModel().selectedRows()}) if self.selectionModel() else []

    def _menu(self, pos) -> None:
        index = self.indexAt(pos)
        rows = self.selected_rows()
        if not rows and index.isValid():
            rows = [index.row()]
        if not rows:
            return
        job = self.model().jobs[rows[0]]
        menu = QMenu(self)

        act_preview = QAction(tr("预览对比"), self)
        act_preview.setEnabled(bool(job.dst and job.dst.exists()) or job.src.exists())
        act_preview.triggered.connect(lambda: self.activated_row.emit(rows[0]))
        menu.addAction(act_preview)
        menu.addSeparator()

        act_src = QAction(tr("打开源文件"), self)
        act_src.triggered.connect(lambda: self._open(job.src))
        menu.addAction(act_src)

        act_dir = QAction(tr("打开所在文件夹"), self)
        act_dir.triggered.connect(lambda: self._reveal(job.dst if job.dst and job.dst.exists() else job.src))
        menu.addAction(act_dir)

        if job.dst and job.dst.exists():
            act_out = QAction(tr("打开输出文件"), self)
            act_out.triggered.connect(lambda: self._open(job.dst))
            menu.addAction(act_out)

        menu.addSeparator()
        act_copy = QAction(tr("复制文件路径"), self)
        act_copy.triggered.connect(lambda: QGuiApplication.clipboard().setText(str(job.src)))
        menu.addAction(act_copy)

        act_remove = QAction(tr("从工作区移除（{count} 项）", count=len(rows)), self)
        act_remove.setEnabled(not self.locked)
        act_remove.triggered.connect(lambda: self.rows_removed.emit(rows))
        menu.addAction(act_remove)
        menu.exec(self.viewport().mapToGlobal(pos))

    @staticmethod
    def _open(path: Path) -> None:
        import os

        if path and Path(path).exists():
            os.startfile(str(path))  # noqa: S606

    @staticmethod
    def _reveal(path: Path) -> None:
        import subprocess

        if path and Path(path).exists():
            subprocess.Popen(["explorer", "/select,", str(path)])

    def keyPressEvent(self, event):  # noqa: N802
        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            rows = self.selected_rows()
            if rows and not self.locked:
                self.rows_removed.emit(rows)
                return
        super().keyPressEvent(event)


class JobPanel(Card):
    files_dropped = Signal(list)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.model = JobModel(self)
        self.table = JobTable(self)
        self.table.set_job_model(self.model)

        self.title = QLabel(tr("工作区"))
        self.title.setObjectName("SectionTitle")
        self.badge = QLabel(tr("0 个文件"))
        self.badge.setObjectName("Badge")
        self.btn_remove = QPushButton(tr("移除选中"))
        self.btn_remove.setProperty("role", "ghost")
        self.btn_clear = QPushButton(tr("清空"))
        self.btn_clear.setProperty("role", "ghost")

        head = QHBoxLayout()
        head.setContentsMargins(14, 12, 14, 8)
        head.setSpacing(8)
        head.addWidget(self.title)
        head.addWidget(self.badge)
        head.addStretch(1)
        head.addWidget(self.btn_remove)
        head.addWidget(self.btn_clear)

        empty = QWidget()
        el = QVBoxLayout(empty)
        el.setContentsMargins(24, 24, 24, 24)
        el.setSpacing(6)
        el.addStretch(1)
        icon = QLabel("+")
        icon.setAlignment(Qt.AlignCenter)
        icon.setStyleSheet(
            "QLabel{font-size:28px;color:#B4BCC8;background:#F7F8FA;border:1px dashed #D0D5DD;"
            "border-radius:14px;}"
        )
        icon.setFixedSize(168, 86)
        icon_wrap = QWidget()
        icon_row = QHBoxLayout(icon_wrap)
        icon_row.setContentsMargins(0, 0, 0, 0)
        icon_row.addStretch(1)
        icon_row.addWidget(icon)
        icon_row.addStretch(1)
        empty_title = QLabel(tr("把图片拖到这里"))
        empty_title.setObjectName("EmptyTitle")
        empty_title.setAlignment(Qt.AlignCenter)
        empty_hint = QLabel(tr("也可以右键图片选择「添加到 ImgPress 工作区」，或点击右上角「添加文件」"))
        empty_hint.setObjectName("EmptyHint")
        empty_hint.setAlignment(Qt.AlignCenter)
        empty_hint.setWordWrap(True)
        el.addWidget(icon_wrap)
        el.addWidget(empty_title)
        el.addWidget(empty_hint)
        el.addStretch(1)

        self.stack = QStackedLayout()
        self.stack.addWidget(empty)
        self.stack.addWidget(self.table)
        self.stack.setContentsMargins(0, 0, 0, 0)

        body = QWidget()
        body.setLayout(self.stack)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addLayout(head)
        root.addWidget(body, 1)

        self.model.rowsInserted.connect(self._sync)
        self.model.rowsRemoved.connect(self._sync)
        self.model.modelReset.connect(self._sync)
        self.model.dataChanged.connect(self._sync)

        self.btn_remove.clicked.connect(lambda: self.table.rows_removed.emit(self.table.selected_rows()))
        self.btn_clear.clicked.connect(self.model.clear)
        self.table.rows_removed.connect(self._remove)
        self.table.selection_changed.connect(self._sync)

        self.setAcceptDrops(True)
        self._locked = False

    def set_locked(self, locked: bool) -> None:
        """编码进行中：禁止移除/清空，但允许继续添加。"""
        self._locked = locked
        self.table.locked = locked
        self._sync()

    def _remove(self, rows: list[int]) -> None:
        self.model.remove_rows(rows)

    def _sync(self, *_) -> None:
        count = len(self.model.jobs)
        total = self.model.total_bytes()
        self.badge.setText(tr("{n} 个文件 · {size}", n=count, size=fmt_bytes(total)) if count else tr("0 个文件"))
        self.stack.setCurrentIndex(1 if count else 0)
        self.btn_remove.setEnabled(bool(self.table.selected_rows()) and not self._locked)
        self.btn_clear.setEnabled(count > 0 and not self._locked)

    # ---------- 拖放 ----------
    def dragEnterEvent(self, event):  # noqa: N802
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):  # noqa: N802
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):  # noqa: N802
        paths = [Path(u.toLocalFile()) for u in event.mimeData().urls() if u.isLocalFile()]
        if paths:
            self.files_dropped.emit(paths)
            event.acceptProposedAction()
