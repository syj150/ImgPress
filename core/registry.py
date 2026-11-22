"""Windows 右键菜单注册（写 HKEY_CURRENT_USER，无需管理员权限）。

注册位置：
  HKCU\\Software\\Classes\\SystemFileAssociations\\.<ext>\\shell\\ImgPress
    (默认)            = 菜单文字
    Icon              = "exe,0"
    MultiSelectModel  = Player      (允许一次多选最多 100 个文件)
    command\\(默认)   = "exe" --add "%1"

说明：Windows 11 把此类经典动词收纳进「显示更多选项」（Shift+F10）菜单，
不在首层右键列表里；这是系统级行为，除非做 MSIX 打包否则无法绕过。
"""

from __future__ import annotations

import sys
from pathlib import Path

from i18n import tr

try:
    import winreg
except ImportError:  # 非 Windows 环境下的降级
    winreg = None  # type: ignore[assignment]

VERB = "ImgPress"
MENU_LABEL_KEY = "添加到 ImgPress 工作区"
EXTS = (
    ".jpg", ".jpeg", ".jfif",
    ".png",
    ".webp",
    ".bmp",
    ".tif", ".tiff",
    ".gif",
    ".avif",
    ".jxl",
)
BASE = r"Software\Classes\SystemFileAssociations"


def _key(ext: str) -> str:
    return f"{BASE}\\{ext}\\shell\\{VERB}"


def launch_command(exe: Path, script: Path | None = None) -> str:
    """注册表里的命令行。开发模式需要显式带上脚本路径。"""
    if script:
        return f'"{exe}" "{script}" --add "%1"'
    return f'"{exe}" --add "%1"'


def install(exe: Path, script: Path | None = None) -> int:
    """写入全部扩展名的菜单项，返回成功条数。"""
    if winreg is None:
        raise RuntimeError("当前系统不支持注册表操作")
    exe = Path(exe)
    icon = exe if not script else Path(script)
    count = 0
    for ext in EXTS:
        try:
            with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, _key(ext), 0, winreg.KEY_WRITE) as k:
                winreg.SetValueEx(k, "", 0, winreg.REG_SZ, tr(MENU_LABEL_KEY))
                winreg.SetValueEx(k, "Icon", 0, winreg.REG_SZ, f"{icon},0")
                winreg.SetValueEx(k, "MultiSelectModel", 0, winreg.REG_SZ, "Player")
            with winreg.CreateKeyEx(
                winreg.HKEY_CURRENT_USER, _key(ext) + r"\command", 0, winreg.KEY_WRITE
            ) as k:
                winreg.SetValueEx(k, "", 0, winreg.REG_SZ, launch_command(exe, script))
            count += 1
        except OSError:
            continue
    return count


def uninstall() -> int:
    if winreg is None:
        raise RuntimeError("当前系统不支持注册表操作")
    count = 0
    for ext in EXTS:
        try:
            _delete_tree(winreg.HKEY_CURRENT_USER, _key(ext))
            count += 1
        except FileNotFoundError:
            count += 1
        except OSError:
            continue
    return count


def _delete_tree(root, path: str) -> None:
    try:
        with winreg.OpenKey(root, path, 0, winreg.KEY_READ | winreg.KEY_WRITE) as k:
            children = []
            i = 0
            while True:
                try:
                    children.append(winreg.EnumKey(k, i))
                except OSError:
                    break
                i += 1
        for child in children:
            _delete_tree(root, path + "\\" + child)
    except FileNotFoundError:
        return
    winreg.DeleteKey(root, path)


def registered_command(ext: str = ".jpg") -> str | None:
    if winreg is None:
        return None
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _key(ext) + r"\command", 0, winreg.KEY_READ) as k:
            value, _ = winreg.QueryValueEx(k, "")
            return value
    except OSError:
        return None


def is_installed() -> bool:
    return all(registered_command(ext) for ext in EXTS)


def current_target() -> str | None:
    """当前注册指向的可执行文件路径（解析引号内的部分）。"""
    cmd = registered_command()
    if not cmd:
        return None
    if cmd.startswith('"'):
        end = cmd.find('"', 1)
        return cmd[1:end] if end > 0 else cmd
    return cmd.split(" ")[0]


def status_text() -> str:
    if winreg is None:
        return tr("仅支持 Windows")
    target = current_target()
    if target and is_installed():
        return tr("已注册 · {path}", path=target)
    if target:
        return tr("部分注册（有扩展名缺失）")
    return tr("未注册")
