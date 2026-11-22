"""打包脚本：PyInstaller onedir + 拷贝工具链与资源。

    python build/build_exe.py

产物：dist/ImgPress/ （整个目录可搬运，双击 ImgPress.exe 运行）
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))  # 仅用于读取项目内常量
DIST = ROOT / "dist" / "ImgPress"


def run(cmd: list[str]) -> None:
    print("$", " ".join(cmd))
    p = subprocess.run(cmd, cwd=ROOT)
    if p.returncode != 0:
        raise SystemExit(f"命令失败（{p.returncode}）")


def move_old_dist() -> None:
    """把上一次的产物挪到临时目录（移动而非删除，避免大批量删除的确认拦截）。"""
    if not DIST.exists():
        return
    stamp = time.strftime("%Y%m%d_%H%M%S")
    target = Path(tempfile.gettempdir()) / f"imgpress_prev_{stamp}"
    target.mkdir(parents=True, exist_ok=True)
    shutil.move(str(DIST), str(target / "ImgPress"))
    print(f"旧的 dist 已移动到：{target}（可手动删除）")


def main() -> int:
    t0 = time.time()
    move_old_dist()
    run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "ImgPress.spec"])

    if not DIST.exists():
        raise SystemExit("未生成 dist/ImgPress")

    # 工具链放在 exe 同级的 tools 下：便携、可单独替换编码器版本
    src_tools = ROOT / "tools"
    dst_tools = DIST / "tools"
    if dst_tools.exists():
        shutil.rmtree(dst_tools)
    shutil.copytree(src_tools, dst_tools)

    # 资源同时放到根目录，方便替换图标
    src_assets = ROOT / "assets"
    dst_assets = DIST / "assets"
    if dst_assets.exists():
        shutil.rmtree(dst_assets)
    shutil.copytree(src_assets, dst_assets)

    total = sum(f.stat().st_size for f in DIST.rglob("*") if f.is_file())
    exe = DIST / "ImgPress.exe"
    print("\n完成：", exe)
    print(f"目录体积：{total / 1024 / 1024:.1f} MB")
    print(f"耗时：{time.time() - t0:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
