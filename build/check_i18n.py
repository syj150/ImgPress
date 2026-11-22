"""检查英文界面是否还有残留中文（漏翻或 key 不匹配）。

做法：把语言切成 en，构建各个窗口，遍历控件文本与提示，报告仍含中日韩字符的字符串。

    python build/check_i18n.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtGui import QGuiApplication  # noqa: E402
from PySide6.QtWidgets import (  # noqa: E402
    QApplication,
    QCheckBox,
    QComboBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableView,
    QWidget,
)

import i18n  # noqa: E402
from core import paths  # noqa: E402
from core import settings as settings_mod  # noqa: E402
from core import tools as tools_mod  # noqa: E402
from core.params import RunParams  # noqa: E402
from core.runner import Job  # noqa: E402

CJK = re.compile(r"[\u3000-\u303f\u4e00-\u9fff\uff00-\uffef]")

# 语言名按惯例用各自母语显示，不参与检查
ALLOW = {"简体中文", "English", "Follow system (简体中文)"}


def collect(root: QWidget) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []

    def add(kind: str, text: str) -> None:
        if text and text not in ALLOW and CJK.search(text):
            found.append((kind, text.replace("\n", "\\n")[:110]))

    for w in root.findChildren(QWidget):
        add(type(w).__name__, w.toolTip())
        add(f"{type(w).__name__}.windowTitle", w.windowTitle()) if isinstance(w, QWidget) else None
        if isinstance(w, QLabel):
            add("QLabel", w.text())
        elif isinstance(w, QPushButton):
            add("QPushButton", w.text())
        elif isinstance(w, QCheckBox):
            add("QCheckBox", w.text())
        elif isinstance(w, QLineEdit):
            add("QLineEdit.placeholder", w.placeholderText())
        elif isinstance(w, QComboBox):
            for i in range(w.count()):
                add("QComboBox.item", w.itemText(i))
        elif isinstance(w, QTableView) and w.model() is not None:
            model = w.model()
            for c in range(model.columnCount()):
                add("header", str(model.headerData(c, Qt.Horizontal) or ""))
            for r in range(model.rowCount()):
                for c in range(model.columnCount()):
                    add("cell", str(model.data(model.index(r, c), Qt.DisplayRole) or ""))
    return found


def check_runner() -> list[tuple[str, str]]:
    """实跑一次编码，检查日志与任务消息里的文案。"""
    import tempfile

    from PySide6.QtGui import QColor, QImage, QPainter

    from core.params import RunParams
    from core.runner import EncodeWorker, Job
    from core.tools import load

    problems: list[tuple[str, str]] = []
    tmp = Path(tempfile.mkdtemp(prefix="imgpress_i18n_"))
    src = tmp / "sample.png"
    img = QImage(320, 240, QImage.Format_RGB32)
    img.fill(QColor("#3366cc"))
    painter = QPainter(img)
    painter.fillRect(20, 20, 120, 80, QColor("#ffffff"))
    painter.end()
    img.save(str(src), "PNG")

    tools = load(paths.default_tools_root())
    if not tools.paths:
        return problems

    params = RunParams()
    params.codec = "webp"
    params.calc_s2 = False
    jobs = [Job(src=src, codec="webp", src_size=src.stat().st_size)]
    worker = EncodeWorker(jobs, params, tools, policy="overwrite")
    lines: list[str] = []
    worker.log.connect(lines.append)
    worker.run()

    for line in lines + [j.message for j in jobs]:
        if line and CJK.search(line):
            problems.append(("log", line[:110]))

    # 参数校验提示
    from core.params import validate

    combos = [("jxl", "lossless_jpeg"), ("avif", "lossless"), ("webp", "lossless"), ("png", "strip_all")]
    for codec, tweak in combos:
        p = RunParams()
        p.codec = codec
        if tweak == "lossless_jpeg":
            p.jxl.lossless_jpeg = True
        elif tweak == "lossless":
            getattr(p, codec).lossless = True
        elif tweak == "strip_all":
            p.png.strip = "all"
        for notice in validate(p):
            if CJK.search(notice.text):
                problems.append(("notice", notice.text[:110]))

    import shutil

    shutil.rmtree(tmp, ignore_errors=True)
    return problems


def main() -> int:
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)  # noqa: F841
    i18n.set_language("en")

    from ui import theme
    from ui.mainwindow import MainWindow
    from ui.previewdialog import PreviewDialog
    from ui.settingsdialog import SettingsDialog

    theme.apply(app)
    settings = settings_mod.load()
    settings.params = RunParams()
    tools = tools_mod.load(paths.default_tools_root())

    problems: list[tuple[str, str]] = []

    window = MainWindow(settings, tools, [])
    for codec_index in range(4):
        window.panel.tabs.setCurrentIndex(codec_index)
        app.processEvents()
        problems += collect(window)

    # 有任务时的表格/状态文案
    sample = Path(__file__).resolve().parent / "check_i18n.py"
    job = Job(src=sample, codec="avif", src_size=sample.stat().st_size)
    window.jobs_panel.model.jobs.append(job)
    window.jobs_panel.model.reset_status("avif")
    window.jobs_panel.model.refresh()
    window._update_status()
    problems += collect(window)

    problems += collect(SettingsDialog(settings, tools, window))

    job.dst = sample
    problems += collect(PreviewDialog(job, tools, window))
    problems += check_runner()

    seen: set[tuple[str, str]] = set()
    print(f"语言: {i18n.current_language()}  残留中文条目: {len(problems)}\n")
    for kind, text in problems:
        if (kind, text) in seen:
            continue
        seen.add((kind, text))
        print(f"  [{kind}] {text}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
