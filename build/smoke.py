"""开发期冒烟测试：起窗口、截一张图、退出。用于检查布局与样式。

    python build/smoke.py [--files a.jpg b.png] [--out shot.png] [--delay 1200]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import Qt, QTimer  # noqa: E402
from PySide6.QtGui import QGuiApplication  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from core import paths  # noqa: E402
from core import settings as settings_mod  # noqa: E402
from core import tools as tools_mod  # noqa: E402
from ui import theme  # noqa: E402
from ui.mainwindow import MainWindow  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--files", nargs="*", default=[])
    ap.add_argument("--out", default="build/shot.png")
    ap.add_argument("--delay", type=int, default=1200)
    ap.add_argument("--size", default="1440x900")
    ap.add_argument("--codec", default=None)
    ap.add_argument("--lang", default=None)
    args = ap.parse_args()

    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    theme.apply(app)
    import i18n

    i18n.install_qt_translator(app)

    if args.lang:
        import i18n

        i18n.set_language(args.lang)

    settings = settings_mod.load()
    if args.codec:
        settings.params.codec = args.codec
    toolchain = tools_mod.load(paths.default_tools_root())
    window = MainWindow(settings, toolchain, args.files)
    w, h = (int(x) for x in args.size.lower().split("x"))
    window.resize(w, h)
    window.show()

    def shot() -> None:
        out = ROOT / args.out
        out.parent.mkdir(parents=True, exist_ok=True)
        window.grab().save(str(out), "PNG")
        print(f"saved {out}")
        app.quit()

    QTimer.singleShot(args.delay, shot)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
