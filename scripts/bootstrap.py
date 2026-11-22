"""一键安装：Python 环境 + PySide6 + 四个编码器。

设计目标是「任何一台干净的 Windows 机器上，一条命令跑起来」，也方便 AI agent 直接执行：

    python scripts/bootstrap.py --build

它做四件事：
  1. 检查 Python 版本
  2. 建 .venv 并安装 requirements.txt（--build 连打包工具一起装）
  3. 从官方 release 下载 libjxl / libavif / libwebp / oxipng，抽出需要的 exe 到 tools/bin
  4. 逐个执行 --version 验证，打印结果

可重复执行：已存在的依赖和二进制会跳过，加 --force 强制重下。
"""

from __future__ import annotations

import argparse
import hashlib
import os
import platform
import shutil
import ssl
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import zipfile
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
TOOLS_BIN = ROOT / "tools" / "bin"
TOOLS_DL = ROOT / "tools" / "dl"
VENV = ROOT / ".venv"
MIN_PYTHON = (3, 10)


@dataclass
class Component:
    key: str
    title: str
    version: str
    url: str
    exes: list[str]
    note: str = ""
    downloaded: Path | None = field(default=None)


COMPONENTS: list[Component] = [
    Component(
        key="jxl",
        title="libjxl",
        version="0.13.0",
        url="https://github.com/libjxl/libjxl/releases/download/v0.13.0/jxl-x64-windows-static.zip",
        exes=["cjxl.exe", "djxl.exe", "ssimulacra2.exe"],
        note="静态链接，无需额外 DLL",
    ),
    Component(
        key="avif",
        title="libavif",
        version="1.4.2 (libaom 3.14.1)",
        url="https://github.com/AOMediaCodec/libavif/releases/download/v1.4.2/windows-artifacts.zip",
        exes=["avifenc.exe", "avifdec.exe"],
        note="静态构建",
    ),
    Component(
        key="webp",
        title="libwebp",
        version="1.6.0",
        url="https://storage.googleapis.com/downloads.webmproject.org/releases/webp/libwebp-1.6.0-windows-x64.zip",
        exes=["cwebp.exe", "dwebp.exe", "webpinfo.exe"],
    ),
    Component(
        key="oxipng",
        title="oxipng",
        version="10.2.1",
        url="https://github.com/shssoichiro/oxipng/releases/download/v10.2.1/oxipng-10.2.1-x86_64-pc-windows-msvc.zip",
        exes=["oxipng.exe"],
    ),
]

# 这几个工具没有 --version，直接视为安装成功
NO_VERSION = {"ssimulacra2.exe", "webpinfo.exe"}

VERSION_FLAG = {
    "cjxl.exe": "--version",
    "djxl.exe": "--version",
    "avifenc.exe": "--version",
    "avifdec.exe": "--version",
    "cwebp.exe": "-version",
    "dwebp.exe": "-version",
    "oxipng.exe": "--version",
}


# ---------------------------------------------------------------- 输出
class Step:
    def __init__(self, total: int) -> None:
        self.index = 0
        self.total = total

    def __call__(self, text: str) -> None:
        self.index += 1
        print(f"\n[{self.index}/{self.total}] {text}")


def info(text: str) -> None:
    print(f"    {text}")


def warn(text: str) -> None:
    print(f"    ! {text}")


def fail(text: str) -> None:
    print(f"    × {text}")


# ---------------------------------------------------------------- 1. Python
def check_python() -> bool:
    ok = sys.version_info[:2] >= MIN_PYTHON
    info(f"Python {platform.python_version()}  ({sys.executable})")
    if not ok:
        fail(f"需要 Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]} 或更高版本")
    return ok


# ---------------------------------------------------------------- 2. 依赖
def venv_python() -> Path:
    return VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def ensure_venv(use_venv: bool) -> Path:
    if not use_venv:
        info("跳过虚拟环境（--no-venv），直接使用当前解释器")
        return Path(sys.executable)
    if venv_python().exists():
        info(f"复用已有虚拟环境：{VENV}")
        return venv_python()
    info(f"创建虚拟环境：{VENV}")
    subprocess.run([sys.executable, "-m", "venv", str(VENV)], check=True)
    return venv_python()


def pip_install(py: Path, requirements: list[Path], proxy: str | None) -> bool:
    cmd = [str(py), "-m", "pip", "install", "--upgrade", "--quiet", "pip"]
    subprocess.run(cmd, check=False)
    args = [str(py), "-m", "pip", "install", "-r", str(requirements[0])]
    if len(requirements) > 1:
        for extra in requirements[1:]:
            args += ["-r", str(extra)]
    if proxy:
        args += ["--proxy", proxy]
    info("$ pip install " + " ".join(a for a in args[4:]))
    result = subprocess.run(args)
    return result.returncode == 0


def verify_pyside(py: Path) -> bool:
    code = "import PySide6; print(PySide6.__version__)"
    result = subprocess.run([str(py), "-c", code], capture_output=True, text=True)
    if result.returncode == 0:
        info(f"PySide6 {result.stdout.strip()} 已就绪")
        return True
    fail("PySide6 导入失败")
    if result.stderr.strip():
        info(result.stderr.strip().splitlines()[-1])
    return False


# ---------------------------------------------------------------- 3. 工具链
def _opener(proxy: str | None, insecure: bool = False):
    handlers: list = []
    if proxy:
        handlers.append(urllib.request.ProxyHandler({"http": proxy, "https": proxy}))
    if insecure:
        handlers.append(urllib.request.HTTPSHandler(context=ssl._create_unverified_context()))
    return urllib.request.build_opener(*handlers)


def download(url: str, dest: Path, proxy: str | None, insecure: bool) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        info(f"已存在，跳过下载：{dest.name} ({dest.stat().st_size / 1048576:.1f} MB)")
        return True

    request = urllib.request.Request(url, headers={"User-Agent": "ImgPress-bootstrap"})
    opener = _opener(proxy, insecure)
    tmp = dest.with_suffix(dest.suffix + ".part")
    try:
        with opener.open(request, timeout=60) as resp:
            total = int(resp.headers.get("Content-Length") or 0)
            size_mb = f"{total / 1048576:.1f} MB" if total else "未知大小"
            info(f"下载 {dest.name}  ({size_mb})")
            done = 0
            last = 0.0
            with tmp.open("wb") as fh:
                while True:
                    chunk = resp.read(256 * 1024)
                    if not chunk:
                        break
                    fh.write(chunk)
                    done += len(chunk)
                    now = time.time()
                    if now - last > 0.4:
                        last = now
                        pct = f"{done / total * 100:5.1f}%" if total else "   "
                        print(f"\r    {pct}  {done / 1048576:.1f} MB", end="", flush=True)
        if total:
            print(f"\r    100.0%  {done / 1048576:.1f} MB")
        print()
        tmp.replace(dest)
        return True
    except urllib.error.HTTPError as exc:
        tmp.unlink(missing_ok=True)
        fail(f"HTTP {exc.code}：{url}")
        info("文件名可能已变更，请到 release 页面确认后改 COMPONENTS 里的 url")
        return False
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        tmp.unlink(missing_ok=True)
        fail(f"下载失败：{exc}")
        info("网络受限时可加 --proxy http://127.0.0.1:<端口> 走本地代理")
        return False


def extract(archive: Path, component: Component) -> bool:
    wanted = {e.lower() for e in component.exes}
    dest = TOOLS_BIN / component.key
    try:
        with zipfile.ZipFile(archive) as zf:
            names = zf.namelist()
            hits: dict[str, str] = {}
            for name in names:
                base = PurePosixPath(name).name.lower()
                if base in wanted and base not in hits:
                    hits[base] = name
            missing = wanted - set(hits)
            if missing:
                fail(f"压缩包里找不到：{', '.join(sorted(missing))}")
                return False

            dest.mkdir(parents=True, exist_ok=True)
            folders = {str(PurePosixPath(p).parent) for p in hits.values()}
            count = 0
            for name in names:
                if name.endswith("/"):
                    continue
                path = PurePosixPath(name)
                same_dir_dll = path.suffix.lower() == ".dll" and str(path.parent) in folders
                if path.name.lower() in wanted or same_dir_dll:
                    (dest / path.name).write_bytes(zf.read(name))
                    count += 1
            info(f"解出 {count} 个文件 → {dest.relative_to(ROOT)}")
            return True
    except zipfile.BadZipFile:
        fail(f"压缩包损坏：{archive.name}")
        return False


def tools_ready(component: Component) -> bool:
    dest = TOOLS_BIN / component.key
    return all((dest / e).exists() and (dest / e).stat().st_size > 0 for e in component.exes)


def verify_tools() -> bool:
    ok = True
    for component in COMPONENTS:
        for exe in component.exes:
            path = TOOLS_BIN / component.key / exe
            if not path.exists():
                fail(f"{component.title}: 缺少 {exe}")
                ok = False
                continue
            if exe.lower() in NO_VERSION:
                info(f"{exe:16s} 已安装")
                continue
            flag = VERSION_FLAG.get(exe.lower(), "--version")
            try:
                result = subprocess.run(
                    [str(path), flag],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=15,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                )
                first = ((result.stdout or "") + (result.stderr or "")).strip().splitlines()
                info(f"{exe:16s} {first[0][:60] if first else '无输出'}")
            except (OSError, subprocess.SubprocessError) as exc:
                fail(f"{exe} 无法执行：{exc}")
                ok = False
    return ok


# ---------------------------------------------------------------- 主流程
def main() -> int:
    parser = argparse.ArgumentParser(
        description="ImgPress 一键安装：环境依赖 + 编码器二进制",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="装好后运行：.venv\\Scripts\\python main.py（或 .\\run.bat）",
    )
    parser.add_argument("--build", action="store_true", help="同时安装打包工具（PyInstaller）")
    parser.add_argument("--no-venv", action="store_true", help="不建虚拟环境，装到当前解释器")
    parser.add_argument("--force", action="store_true", help="重新下载编码器")
    parser.add_argument("--proxy", default=os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy"),
                        help="下载用代理，如 http://127.0.0.1:8080")
    parser.add_argument("--skip-tools", action="store_true", help="只装 Python 依赖，不动编码器")
    parser.add_argument("--insecure", action="store_true", help="跳过 TLS 校验（公司代理自签证书时用）")
    args = parser.parse_args()

    print("=" * 62)
    print(" ImgPress 一键安装")
    print("=" * 62)

    steps = 4 if not args.skip_tools else 3
    step = Step(steps)

    step("检查 Python 环境")
    if not check_python():
        return 1
    if os.name != "nt":
        warn("编码器是 Windows 二进制，当前系统只能装 Python 依赖")

    step("安装 Python 依赖")
    py = ensure_venv(not args.no_venv)
    reqs = [ROOT / "requirements.txt"]
    if args.build:
        reqs.append(ROOT / "requirements-build.txt")
    if not pip_install(py, reqs, args.proxy):
        fail("pip 安装失败，请检查网络或代理")
        return 1
    if not verify_pyside(py):
        return 1

    if args.skip_tools:
        finish(py, args)
        return 0

    step("下载并解包编码器（约 40 MB）")
    if os.name != "nt":
        warn("已跳过编码器下载")
    else:
        TOOLS_DL.mkdir(parents=True, exist_ok=True)
        for component in COMPONENTS:
            if not args.force and tools_ready(component):
                info(f"{component.title} {component.version} 已就绪，跳过")
                continue
            archive = TOOLS_DL / f"{component.key}-{component.version.split()[0]}.zip"
            if args.force:
                archive.unlink(missing_ok=True)
            if not download(component.url, archive, args.proxy, args.insecure):
                return 1
            if not extract(archive, component):
                return 1

    step("验证编码器")
    ok = verify_tools() if os.name == "nt" else True
    finish(py, args)
    return 0 if ok else 1


def finish(py: Path, args) -> None:
    print("\n" + "=" * 62)
    if os.name == "nt":
        print(" 完成。启动方式：")
        print(f"   {py} main.py")
        print("   或双击 run.bat")
        print("\n 打包为便携版：")
        print(f"   {py} build/build_exe.py")
    else:
        print(" Python 依赖已就绪；编码器仅 Windows 可用。")
    print("=" * 62)


if __name__ == "__main__":
    raise SystemExit(main())
