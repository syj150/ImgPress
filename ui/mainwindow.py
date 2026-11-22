"""主窗口：工作区 + 参数面板 + 进度与日志。"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize, QThread, Qt, QTimer, Signal
from PySide6.QtGui import QGuiApplication, QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from i18n import tr

from core import paths
from core import tools as tools_mod
from core.params import codec_label, validate
from core.runner import DONE, RUNNING, EncodeWorker, summarize
from core.settings import Settings, save as save_settings
from core.tools import Toolchain
from core.util import fmt_bytes, fmt_duration
from . import icons, theme
from .jobtable import INPUT_EXTS, JobPanel
from .paramspanel import ParamsPanel
from .previewdialog import PreviewDialog
from .settingsdialog import SettingsDialog
from .widgets import Card

FILE_FILTER = f"{tr('图片')} (" + " ".join(f"*{e}" for e in sorted(INPUT_EXTS)) + f");;{tr('所有文件')} (*.*)"


class MainWindow(QMainWindow):
    run_finished = Signal()

    def __init__(self, settings: Settings, tools: Toolchain, initial_files: list[str] | None = None) -> None:
        super().__init__()
        self.settings = settings
        self.tools = tools
        self._thread: QThread | None = None
        self._worker: EncodeWorker | None = None
        self._running = False

        self.setWindowTitle(tr(paths.APP_TITLE))
        self.setMinimumSize(1060, 680)
        self._resize_to_screen()
        icon_path = paths.asset_path("icon.ico")
        if icon_path:
            self.setWindowIcon(QIcon(str(icon_path)))
        self.setAcceptDrops(True)

        self.panel = ParamsPanel(settings.params, tools)
        self.jobs_panel = JobPanel()
        self._build_ui()
        self._restore_geometry()
        self._connect()

        if initial_files:
            self.add_paths([Path(p) for p in initial_files])
        self._update_status()
        self._log(tr("工具链：{path}", path=tools.root if tools.root else tr("未找到")))

    # ---------------- 界面 ----------------
    # 标题栏 + 边框在 Windows 上会额外占用约 32px，窗口尺寸要预留出来，
    # 否则底部的「开始编码」会被任务栏盖住。
    FRAME_H = 44
    FRAME_W = 20

    def _resize_to_screen(self) -> None:
        screen = QGuiApplication.primaryScreen()
        avail = screen.availableGeometry() if screen else None
        width, height = 1360, 880
        if avail:
            width = min(width, avail.width() - self.FRAME_W - 24)
            height = min(height, avail.height() - self.FRAME_H - 16)
        self.resize(max(width, 1060), max(height, 680))

    def _build_ui(self) -> None:
        header = QFrame()
        header.setObjectName("Header")
        header.setFixedHeight(66)

        icon = QLabel()
        png = paths.asset_path("icon.png")
        if png:
            from PySide6.QtGui import QPixmap

            icon.setPixmap(QPixmap(str(png)).scaled(34, 34, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        title = QLabel("ImgPress")
        title.setObjectName("Title")
        subtitle = QLabel(tr("本地图片压缩 · libjxl 0.13.0 · libavif 1.4.2 / libaom 3.14.1 · libwebp 1.6.0"))
        subtitle.setObjectName("Subtitle")

        title_box = QVBoxLayout()
        title_box.setSpacing(1)
        title_box.addWidget(title)
        title_box.addWidget(subtitle)

        self.btn_add = QPushButton(tr("添加文件"))
        self.btn_add.setIcon(icons.make("file_plus"))
        self.btn_add.setToolTip(tr("把图片加入工作区（Ctrl+O）"))

        self.btn_add_folder = QPushButton(tr("添加文件夹"))
        self.btn_add_folder.setIcon(icons.make("folder_plus"))
        self.btn_add_folder.setToolTip(tr("递归添加文件夹里的图片（Ctrl+Shift+O）"))

        self.btn_settings = QPushButton(tr("设置"))
        self.btn_settings.setIcon(icons.make("gear"))
        self.btn_settings.setToolTip(tr("界面语言、工具链目录、右键菜单"))

        for b in (self.btn_add, self.btn_add_folder, self.btn_settings):
            b.setMinimumHeight(32)
            b.setIconSize(QSize(16, 16))

        hlay = QHBoxLayout(header)
        hlay.setContentsMargins(18, 0, 18, 0)
        hlay.setSpacing(10)
        hlay.addWidget(icon)
        hlay.addLayout(title_box)
        hlay.addStretch(1)
        hlay.addWidget(self.btn_add)
        hlay.addWidget(self.btn_add_folder)
        hlay.addSpacing(6)
        hlay.addWidget(self.btn_settings)

        params_card = Card()
        pcl = QVBoxLayout(params_card)
        pcl.setContentsMargins(0, 0, 0, 0)
        pcl.addWidget(self.panel)
        params_card.setMinimumWidth(468)
        self.params_card = params_card

        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setHandleWidth(10)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.addWidget(self.jobs_panel)
        self.splitter.addWidget(params_card)
        self.splitter.setStretchFactor(0, 3)
        self.splitter.setStretchFactor(1, 2)
        if self.settings.splitter:
            self.splitter.setSizes(self.settings.splitter)
        else:
            self.splitter.setSizes([820, 520])

        content = QWidget()
        cl = QVBoxLayout(content)
        cl.setContentsMargins(12, 12, 12, 0)
        cl.addWidget(self.splitter)

        self.log = QPlainTextEdit()
        self.log.setObjectName("Log")
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(4000)
        self.log.setFixedHeight(120)
        self.log.setVisible(self.settings.log_visible)
        log_wrap = QWidget()
        lwl = QVBoxLayout(log_wrap)
        lwl.setContentsMargins(12, 8, 12, 0)
        lwl.addWidget(self.log)
        self.log_wrap = log_wrap

        footer = QFrame()
        footer.setObjectName("Footer")
        footer.setFixedHeight(62)
        self.status_label = QLabel(tr("就绪 · 把图片拖入工作区，或点击「添加文件」"))
        self.status_label.setStyleSheet(f"color:{theme.TEXT};font-size:13px;")
        self.counter_label = QLabel("")
        self.counter_label.setObjectName("Hint")
        self.progress = QProgressBar()
        self.progress.setFixedWidth(200)
        self.progress.setTextVisible(False)
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.progress.setVisible(False)
        self.btn_log = QPushButton(tr("日志"))
        self.btn_log.setProperty("role", "ghost")
        self.btn_reveal = QPushButton(tr("打开输出目录"))
        self.btn_reveal.setProperty("role", "ghost")
        self.btn_reveal.setEnabled(False)
        self.btn_start = QPushButton(tr("开始编码"))
        self.btn_start.setProperty("role", "primary")
        self.btn_start.setMinimumHeight(34)
        self.btn_cancel = QPushButton(tr("取消"))
        self.btn_cancel.setVisible(False)
        self.btn_cancel.setMinimumHeight(34)

        flay = QHBoxLayout(footer)
        flay.setContentsMargins(18, 0, 18, 0)
        flay.setSpacing(10)
        flay.addWidget(self.status_label, 1)
        flay.addWidget(self.counter_label)
        flay.addWidget(self.progress)
        flay.addWidget(self.btn_reveal)
        flay.addWidget(self.btn_log)
        flay.addWidget(self.btn_cancel)
        flay.addWidget(self.btn_start)

        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(header)
        root.addWidget(content, 1)
        root.addWidget(log_wrap)
        root.addWidget(footer)
        self.setCentralWidget(central)

    def _restore_geometry(self) -> None:
        w = self.settings.window
        if not w:
            return
        try:
            screen = QGuiApplication.primaryScreen()
            avail = screen.availableGeometry() if screen else None
            width = int(w.get("w", 1360))
            height = int(w.get("h", 880))
            if avail:
                width = min(width, avail.width() - self.FRAME_W - 24)
                height = min(height, avail.height() - self.FRAME_H - 16)
            self.resize(max(width, 1060), max(height, 680))
            if w.get("x") is not None and w.get("y") is not None and avail:
                x, y = int(w["x"]), int(w["y"])
                # 屏幕或缩放变了时把窗口拉回可视范围，底栏不能落到任务栏下面
                x = max(avail.left(), min(x, avail.right() - width - self.FRAME_W))
                y = max(avail.top(), min(y, avail.bottom() - height - self.FRAME_H))
                self.move(x, y)
            if w.get("max"):
                self.showMaximized()
        except (TypeError, ValueError):
            pass

    def _connect(self) -> None:
        self.btn_add.clicked.connect(self.pick_files)
        self.btn_add_folder.clicked.connect(self.pick_folder)
        self.btn_settings.clicked.connect(self.open_settings)
        self.btn_start.clicked.connect(self.start)
        self.btn_cancel.clicked.connect(self.cancel)
        self.btn_log.clicked.connect(self.toggle_log)
        self.btn_reveal.clicked.connect(self.reveal_output)
        self.jobs_panel.files_dropped.connect(self.add_paths)
        self.jobs_panel.table.activated_row.connect(self.open_preview)
        self.panel.codec_changed.connect(self._on_codec_changed)
        self.panel.params_changed.connect(self._update_status)

        QShortcut(QKeySequence("Ctrl+O"), self, self.pick_files)
        QShortcut(QKeySequence("Ctrl+Shift+O"), self, self.pick_folder)
        QShortcut(QKeySequence("Ctrl+Return"), self, self.start)
        QShortcut(QKeySequence("Ctrl+Enter"), self, self.start)

    # ---------------- 文件 ----------------
    def pick_files(self) -> None:
        start = self.settings.last_dir or str(Path.home())
        files, _ = QFileDialog.getOpenFileNames(self, tr("选择一个或多个图片"), start, FILE_FILTER)
        if files:
            self.settings.last_dir = str(Path(files[0]).parent)
            self.add_paths([Path(f) for f in files])

    def pick_folder(self) -> None:
        start = self.settings.last_dir or str(Path.home())
        folder = QFileDialog.getExistingDirectory(self, tr("选择文件夹（含子目录）"), start)
        if folder:
            self.settings.last_dir = folder
            self.add_paths([Path(folder)])

    def add_paths(self, paths_in: list[Path]) -> None:
        added, ignored = self.jobs_panel.model.add_paths(list(paths_in), self.panel.to_params().codec)
        if added:
            if ignored:
                self._log(
                    tr(
                        "加入工作区：{count} 个文件，忽略 {ignored} 个不支持的文件",
                        count=added,
                        ignored=ignored,
                    )
                )
            else:
                self._log(tr("加入工作区：{count} 个文件", count=added))
        elif ignored:
            self._log(tr("没有可处理的图片（忽略 {ignored} 个文件）", ignored=ignored))
        self._update_status()

    def open_preview(self, row: int) -> None:
        jobs = self.jobs_panel.model.jobs
        if not 0 <= row < len(jobs):
            return
        job = jobs[row]
        if not job.src.exists():
            return
        dialog = PreviewDialog(job, self.tools, self)
        dialog.exec()

    # ---------------- 参数 ----------------
    def _on_codec_changed(self, codec: str) -> None:
        # 不清空上一轮结果：换编码器只是换参数视图，方便对照着调
        self._log(tr("编码器切换为 {codec}", codec=codec_label(codec)))
        if self._has_output():
            self._log(tr("表格里是上一轮的结果，点「开始编码」后才会刷新"))
        self._update_status()

    def open_settings(self) -> None:
        dialog = SettingsDialog(self.settings, self.tools, self)
        dialog.applied.connect(self._apply_settings)
        dialog.exec()

    def _apply_settings(self) -> None:
        self.tools = tools_mod.load(self.settings.tools_root or paths.default_tools_root())
        self.panel.set_tools(self.tools)
        self._log(tr("工具链更新：{path}", path=self.tools.root if self.tools.root else tr("未找到")))
        self._update_status()

    # ---------------- 执行 ----------------
    def start(self) -> None:
        if self._running:
            return
        params = self.panel.to_params()
        jobs = self.jobs_panel.model.jobs
        if not jobs:
            self._log(tr("工作区为空，先添加图片"))
            return

        missing = self.tools.missing_for(params.codec)
        if missing:
            QMessageBox.warning(
                self,
                tr("工具链不完整"),
                tr("缺少 {tools}，请在「设置」里指定工具目录。", tools=", ".join(m + ".exe" for m in missing)),
            )
            return

        errors = [n for n in validate(params) if n.level == "error"]
        if errors:
            QMessageBox.warning(self, tr("参数有误"), errors[0].text)
            return

        self.jobs_panel.model.reset_status(params.codec)
        self._set_running(True)
        self.progress.setRange(0, len(jobs))
        self.progress.setValue(0)
        self.progress.setVisible(True)
        self._log("=" * 60)
        self._log(tr("开始编码 · {codec} · {count} 个文件", codec=codec_label(params.codec), count=len(jobs)))

        # 传副本：编码期间允许继续往工作区加文件，不影响本批
        self._worker = EncodeWorker(list(jobs), params, self.tools, self.settings.policy)
        self._thread = QThread(self)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.job_started.connect(self._on_job_started)
        self._worker.job_finished.connect(self._on_job_finished)
        self._worker.progress.connect(self._on_progress)
        self._worker.log.connect(self._log)
        self._worker.finished.connect(self._on_finished)
        self._worker.finished.connect(self._thread.quit)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.start()

    def cancel(self) -> None:
        if self._worker:
            self.btn_cancel.setEnabled(False)
            self.status_label.setText(tr("正在取消…"))
            self._worker.cancel()

    def _on_job_started(self, row: int) -> None:
        job = self.jobs_panel.model.jobs[row]
        job.status = RUNNING
        self.jobs_panel.model.refresh(row)
        self.status_label.setText(tr("正在编码 · {name}", name=job.name))
        self.jobs_panel.table.scrollTo(self.jobs_panel.model.index(row, 0))

    def _on_job_finished(self, row: int) -> None:
        self.jobs_panel.model.refresh(row)
        self._update_reveal()

    def _on_progress(self, done: int, total: int) -> None:
        self.progress.setValue(done)
        self.counter_label.setText(f"{done}/{total}")

    def _on_finished(self) -> None:
        self._set_running(False)
        self.progress.setVisible(False)
        self.counter_label.setText("")
        self.jobs_panel.model.refresh()
        stats = summarize(self.jobs_panel.model.jobs)
        self._log("-" * 60)
        self._log(
            tr(
                "完成 {done} · 失败 {failed} · 跳过 {skipped} · 原 {src} → 输出 {out} · 节省 {saved} · 用时 {time}",
                done=stats["done"],
                failed=stats["failed"],
                skipped=stats["skipped"],
                src=fmt_bytes(stats["src_bytes"]),
                out=fmt_bytes(stats["out_bytes"]),
                saved=fmt_bytes(stats["saved"]),
                time=fmt_duration(stats["elapsed"]),
            )
        )
        self.settings.params = self.panel.to_params()
        save_settings(self.settings)
        self._update_reveal()
        self._show_summary(stats)
        self.run_finished.emit()

    def _show_summary(self, stats: dict) -> None:
        parts = [tr("完成 {done}", done=stats["done"])]
        if stats["failed"]:
            parts.append(tr("失败 {failed}", failed=stats["failed"]))
        if stats["skipped"]:
            parts.append(tr("跳过 {skipped}", skipped=stats["skipped"]))
        if stats["done"] and stats["src_bytes"]:
            pct = stats["out_bytes"] / stats["src_bytes"] * 100
            parts.append(
                tr(
                    "{src} → {out}（−{percent}%）",
                    src=fmt_bytes(stats["src_bytes"]),
                    out=fmt_bytes(stats["out_bytes"]),
                    percent=f"{100 - pct:.1f}",
                )
            )
        if stats["elapsed"]:
            parts.append(tr("用时 {time}", time=fmt_duration(stats["elapsed"])))
        if stats["s2_avg"] >= 0:
            parts.append(tr("S2 {value}", value=f"{stats['s2_avg']:.2f}"))
        self.status_label.setText(" · ".join(parts))
        color = theme.ERR if stats["failed"] else theme.OK
        self.status_label.setStyleSheet(f"color:{color};font-size:13px;font-weight:600;")
        QTimer.singleShot(9000, self._update_status)

    def _set_running(self, running: bool) -> None:
        self._running = running
        self.btn_start.setVisible(not running)
        self.btn_cancel.setVisible(running)
        self.btn_cancel.setEnabled(running)
        self.btn_settings.setEnabled(not running)
        self.panel.setEnabled(not running)
        self.jobs_panel.set_locked(running)
        self.btn_reveal.setEnabled(not running and self._has_output())

    def _has_output(self) -> bool:
        return any(j.status == DONE and j.dst and j.dst.exists() for j in self.jobs_panel.model.jobs)

    def _update_reveal(self) -> None:
        self.btn_reveal.setEnabled(self._has_output() and not self._running)

    def reveal_output(self) -> None:
        rows = self.jobs_panel.table.selected_rows()
        jobs = self.jobs_panel.model.jobs
        target = None
        if rows:
            job = jobs[rows[0]]
            target = job.dst if job.dst and job.dst.exists() else None
        if target is None:
            for job in jobs:
                if job.dst and job.dst.exists():
                    target = job.dst
                    break
        if target is None:
            return
        import subprocess

        subprocess.Popen(["explorer", "/select,", str(target)])

    # ---------------- 状态与日志 ----------------
    def toggle_log(self) -> None:
        visible = not self.log.isVisible()
        self.log.setVisible(visible)
        self.btn_log.setText(tr("隐藏日志") if visible else tr("日志"))
        self.settings.log_visible = visible

    def _log(self, text: str) -> None:
        self.log.appendPlainText(text)
        bar = self.log.verticalScrollBar()
        bar.setValue(bar.maximum())

    def _update_status(self) -> None:
        if self._running:
            return
        params = self.panel.to_params()
        count = len(self.jobs_panel.model.jobs)
        total = self.jobs_panel.model.total_bytes()

        missing = self.tools.missing_for(params.codec)
        if missing:
            self.status_label.setText(
                tr("缺少 {tools} —— 请在「设置 → 工具链目录」指定正确目录", tools=", ".join(m + ".exe" for m in missing))
            )
            self.status_label.setStyleSheet(f"color:{theme.ERR};font-size:13px;")
            self.btn_start.setEnabled(False)
            return

        engine = codec_label(params.codec)
        if count:
            self.status_label.setText(tr("就绪 · {engine} · {count} 个文件 · {size}", engine=engine, count=count, size=fmt_bytes(total)))
        else:
            self.status_label.setText(tr("就绪 · 把图片拖入工作区，或点击「添加文件」"))
        self.status_label.setStyleSheet(f"color:{theme.TEXT};font-size:13px;")
        self.btn_start.setEnabled(count > 0)

    # ---------------- 事件 ----------------
    def dragEnterEvent(self, event):  # noqa: N802
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):  # noqa: N802
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):  # noqa: N802
        files = [Path(u.toLocalFile()) for u in event.mimeData().urls() if u.isLocalFile()]
        if files:
            self.add_paths(files)
            event.acceptProposedAction()

    def closeEvent(self, event):  # noqa: N802
        if self._running:
            reply = QMessageBox.question(
                self,
                tr("正在编码"),
                tr("编码尚未完成，确定要退出吗？未完成的文件不会保存。"),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                event.ignore()
                return
            if self._worker:
                self._worker.cancel()
        self.settings.params = self.panel.to_params()
        geo = self.geometry()
        self.settings.window = {
            "x": geo.x(),
            "y": geo.y(),
            "w": geo.width(),
            "h": geo.height(),
            "max": self.isMaximized(),
        }
        self.settings.splitter = self.splitter.sizes()
        save_settings(self.settings)
        super().closeEvent(event)
