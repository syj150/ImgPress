"""路径解析：程序目录、用户数据目录、工具链目录。"""

from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "ImgPress"
APP_TITLE = "ImgPress 图片压缩器"
APP_VERSION = "1.0.0"
PROJECT_URL = "https://github.com/syj150/ImgPress"
LICENSE_NAME = "MIT"


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def app_dir() -> Path:
    """exe 所在目录（打包后）或项目根目录（开发时）。"""
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def bundle_dir() -> Path:
    """PyInstaller 临时解包目录，开发时等于 app_dir。"""
    return Path(getattr(sys, "_MEIPASS", app_dir()))


def data_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    p = Path(base) / APP_NAME
    p.mkdir(parents=True, exist_ok=True)
    return p


def cache_dir() -> Path:
    p = data_dir() / "cache"
    p.mkdir(parents=True, exist_ok=True)
    return p


def config_path() -> Path:
    return data_dir() / "config.json"


def default_tools_root() -> Path | None:
    """工具链根目录，优先程序目录下的 tools/bin（便携、可替换版本）。"""
    candidates = [
        app_dir() / "tools" / "bin",
        bundle_dir() / "tools" / "bin",
        app_dir().parent / "tools" / "bin",
    ]
    for cand in candidates:
        if cand.is_dir():
            return cand
    return None


def asset_path(name: str) -> Path | None:
    """资源文件：优先程序目录（便于替换），其次打包内部目录。"""
    for base in (app_dir(), bundle_dir()):
        candidate = base / "assets" / name
        if candidate.exists():
            return candidate
    return None


def exe_path() -> Path:
    """当前可执行文件：打包后是 ImgPress.exe，开发时是 python.exe。"""
    return Path(sys.executable).resolve()
