"""ImgPress 入口。

用法：
    ImgPress.exe                       直接打开主界面
    ImgPress.exe --add "a.jpg" "b.png" 打开主界面并把文件加入工作区（右键菜单即用此形式）
    ImgPress.exe --install-menu        注册右键菜单（写 HKCU）
    ImgPress.exe --uninstall-menu      移除右键菜单
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import QApplication

import i18n
from i18n import tr

from core import paths, registry
from core import settings as settings_mod
from core import tools as tools_mod
from ui import theme
from ui.mainwindow import MainWindow

SERVER_NAME = "ImgPress-single-instance-v1"
MUTEX_NAME = "Local\\ImgPress-single-instance-mutex-v1"
CONNECT_BACKOFF = (0.15, 0.25, 0.4, 0.6, 0.8, 1.0, 1.2)


def acquire_instance_lock() -> tuple[object | None, bool]:
    """用命名互斥量判定是否已有实例；返回 (句柄, 是否已存在)。

    右键多选会并发拉起多个进程，只靠 QLocalServer 判定会出现竞态，
    所以先用内核对象做串行化。
    """
    if os.name != "nt":
        return None, False
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.CreateMutexW(None, False, MUTEX_NAME)
        already = kernel32.GetLastError() == 183  # ERROR_ALREADY_EXISTS
        return handle, already
    except Exception:  # noqa: BLE001
        return None, False


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=True, description=tr("ImgPress 图片压缩器"))
    parser.add_argument("--add", nargs="*", action="append", default=[], help=tr("加入工作区的文件"))
    parser.add_argument("--install-menu", action="store_true", help=tr("注册右键菜单"))
    parser.add_argument("--uninstall-menu", action="store_true", help=tr("移除右键菜单"))
    parser.add_argument("--diagnose", action="store_true", help=tr("打印环境诊断信息"))
    parser.add_argument("files", nargs="*", help=tr("直接拖到 exe 上的文件"))
    args, _unknown = parser.parse_known_args(argv)
    files: list[str] = []
    for group in args.add:
        files.extend(group)
    files.extend(args.files)
    cleaned = [f for f in files if f and not f.startswith("-")]
    args.all_files = [f for f in cleaned if Path(f).exists()]
    return args


def launch_spec() -> tuple[Path, Path | None]:
    if paths.is_frozen():
        return Path(sys.executable), None
    exe = Path(sys.executable).with_name("pythonw.exe")
    if not exe.exists():
        exe = Path(sys.executable)
    return exe, paths.app_dir() / "main.py"


def send_to_running(files: list[str]) -> bool:
    """已有实例在运行时，把文件转发过去。"""
    socket = QLocalSocket()
    socket.connectToServer(SERVER_NAME)
    if not socket.waitForConnected(300):
        return False
    payload = json.dumps({"files": files}, ensure_ascii=False).encode("utf-8")
    socket.write(payload)
    socket.flush()
    socket.waitForBytesWritten(800)
    socket.disconnectFromServer()
    return True


class SingleInstanceServer:
    def __init__(self, window: MainWindow) -> None:
        self.window = window
        self.server = QLocalServer(window)
        if not self.server.listen(SERVER_NAME):
            # 上次异常退出可能留下残留套接字
            QLocalServer.removeServer(SERVER_NAME)
            self.server.listen(SERVER_NAME)
        self.server.newConnection.connect(self._on_connection)

    def _on_connection(self) -> None:
        conn = self.server.nextPendingConnection()
        if not conn:
            return
        conn.readyRead.connect(lambda: self._read(conn))
        conn.disconnected.connect(conn.deleteLater)

    def _read(self, conn: QLocalSocket) -> None:
        data = bytes(conn.readAll())
        if not data:
            return
        try:
            payload = json.loads(data.decode("utf-8"))
            files = payload.get("files") or []
        except (ValueError, UnicodeDecodeError):
            return
        if files:
            self.window.add_paths([Path(f) for f in files])
        self.window.setWindowState(self.window.windowState() & ~Qt.WindowMinimized)
        self.window.show()
        self.window.raise_()
        self.window.activateWindow()


def set_app_id() -> None:
    if os.name != "nt":
        return
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("ImgPress.ImageCompressor.1")
    except Exception:  # noqa: BLE001
        pass


def diagnose() -> None:
    """打印环境信息，便于在 issue 里定位问题（不启动界面）。"""
    from core import settings as settings_mod
    from core import tools as tools_mod

    settings = settings_mod.load()
    root = Path(settings.tools_root) if settings.tools_root else paths.default_tools_root()
    toolchain = tools_mod.load(root)

    print(f"ImgPress {paths.APP_VERSION}")
    print(f"frozen          : {paths.is_frozen()}")
    print(f"app dir         : {paths.app_dir()}")
    print(f"data dir        : {paths.data_dir()}")
    print(f"tools root      : {toolchain.root or '未找到'}")
    print(f"language        : {i18n.current_language()} (setting: {settings.language})")
    try:
        from PySide6.QtCore import QLibraryInfo

        trans = Path(QLibraryInfo.path(QLibraryInfo.TranslationsPath))
        print(f"qt translations : {trans}  ({'ok' if (trans / 'qtbase_zh_CN.qm').exists() else 'missing'})")
    except Exception as exc:  # noqa: BLE001
        print(f"qt translations : {exc}")
    for name in ("cjxl", "djxl", "avifenc", "avifdec", "cwebp", "dwebp", "oxipng", "ssimulacra2"):
        path = toolchain.get(name)
        mark = "ok " if path else "-- "
        print(f"  {mark}{name:14s} {toolchain.version(name) if path else '未找到'}")


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    settings = settings_mod.load()
    i18n.set_language(settings.language)
    args = parse_args(argv)

    if args.install_menu:
        exe, script = launch_spec()
        count = registry.install(exe, script)
        print(f"registered {count} extensions -> {registry.launch_command(exe, script)}")
        return 0 if count else 1

    if args.uninstall_menu:
        count = registry.uninstall()
        print(f"removed {count} extensions")
        return 0

    if args.diagnose:
        diagnose()
        return 0

    set_app_id()
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    app.setApplicationName("ImgPress")
    i18n.install_qt_translator(app)
    app.setApplicationDisplayName(tr(paths.APP_TITLE))
    icon_path = paths.asset_path("icon.ico")
    if icon_path:
        app.setWindowIcon(QIcon(str(icon_path)))
    theme.apply(app)

    _mutex, already_running = acquire_instance_lock()
    if already_running:
        # 主实例可能还在初始化（PyInstaller 解包需要时间），重试投递
        deadline = sum(CONNECT_BACKOFF)
        waited = 0.0
        for delay in CONNECT_BACKOFF:
            if send_to_running(args.all_files):
                return 0
            time.sleep(delay)
            waited += delay
            if waited >= deadline:
                break
        # 连不上说明主实例已无响应，按新实例继续
    elif send_to_running(args.all_files):
        return 0

    root = Path(settings.tools_root) if settings.tools_root else paths.default_tools_root()
    toolchain = tools_mod.load(root)
    window = MainWindow(settings, toolchain, args.all_files)
    server = SingleInstanceServer(window)  # noqa: F841  保活
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
