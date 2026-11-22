"""开发期端到端测试：走完整 GUI 流程编码真实文件，然后截图并退出。

    python build/guirun.py --codec jxl --delay-ms 60000
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import Qt, QTimer  # noqa: E402
from PySide6.QtGui import QGuiApplication  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from core import paths  # noqa: E402
from core import settings as settings_mod  # noqa: E402
from core import tools as tools_mod  # noqa: E402
from core.runner import summarize  # noqa: E402
from core.util import fmt_bytes  # noqa: E402
from ui import theme  # noqa: E402
from ui.mainwindow import MainWindow  # noqa: E402

SAMPLES = Path(os.environ.get("IMGPESS_SAMPLES") or (ROOT / "samples"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--codec", default="avif")
    ap.add_argument("--files", nargs="*", default=["1.jpg", "307__007.png"])
    ap.add_argument("--out", default="build/shot_run.png")
    ap.add_argument("--timeout", type=int, default=180000)
    ap.add_argument("--size", default="1300x780")
    ap.add_argument("--no-s2", action="store_true")
    ap.add_argument("--preview", action="store_true", help="编码结束后打开预览对话框并截图")
    ap.add_argument("--settings", action="store_true", help="只打开设置对话框并截图")
    args = ap.parse_args()

    work = Path(tempfile.mkdtemp(prefix="imgpress_gui_"))
    files = []
    for name in args.files:
        src = SAMPLES / name
        if src.exists():
            dst = work / name
            shutil.copy2(src, dst)
            files.append(dst)

    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    theme.apply(app)

    settings = settings_mod.load()
    settings.params.codec = args.codec
    settings.params.calc_s2 = not args.no_s2
    settings.policy = "overwrite"
    toolchain = tools_mod.load(paths.default_tools_root())

    window = MainWindow(settings, toolchain, [str(f) for f in files])
    w, h = (int(x) for x in args.size.lower().split("x"))
    window.resize(w, h)
    window.show()

    def finish(code: int = 0) -> None:
        stats = summarize(window.jobs_panel.model.jobs)
        print(
            f"[结果] 完成 {stats['done']} 失败 {stats['failed']} 跳过 {stats['skipped']} "
            f"原 {fmt_bytes(stats['src_bytes'])} → {fmt_bytes(stats['out_bytes'])} "
            f"用时 {stats['elapsed']:.1f}s S2avg {stats['s2_avg']}"
        )
        for job in window.jobs_panel.model.jobs:
            print(f"  {job.status:4s} {job.name:18s} {fmt_bytes(job.src_size):>9s} → "
                  f"{fmt_bytes(job.out_size):>9s}  S2={job.s2}  {job.message}")
        window.grab().save(str(ROOT / args.out), "PNG")
        print(f"[截图] {ROOT / args.out}")
        if args.preview:
            from ui.previewdialog import PreviewDialog

            dialog = PreviewDialog(window.jobs_panel.model.jobs[0], window.tools, window)
            dialog.show()
            QApplication.processEvents()
            dialog.grab().save(str(ROOT / "build" / "shot_preview.png"), "PNG")
            print(f"[预览截图] {ROOT / 'build' / 'shot_preview.png'}")
            dialog.close()
        print(f"[输出目录] {work}")
        app.quit()

    def start() -> None:
        if args.settings:
            from ui.settingsdialog import SettingsDialog

            dialog = SettingsDialog(settings, toolchain, window)
            dialog.show()
            QApplication.processEvents()
            dialog.grab().save(str(ROOT / "build" / "shot_settings.png"), "PNG")
            print(f"[设置截图] {ROOT / 'build' / 'shot_settings.png'}")
            dialog.close()
            app.quit()
            return
        window.start()
        if window._worker is None:
            print("[错误] 未启动 worker")
            finish(1)
            return
        window.run_finished.connect(lambda: QTimer.singleShot(200, finish))

    QTimer.singleShot(600, start)
    QTimer.singleShot(args.timeout, lambda: (print("[超时]"), finish(1)))
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
