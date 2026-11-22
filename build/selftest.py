"""开发期自检：核对命令构造、跑通四个编码器。

样本图片与参考脚本都是可选的，缺了就跳过对应部分：

    python build/selftest.py                        # 用 ./samples 或 IMGPESS_SAMPLES
    python build/selftest.py --samples D:/pics
    python build/selftest.py --one-py ../bench/one.py   # 与参考脚本比对参数
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QCoreApplication  # noqa: E402

from core import imageops, paths  # noqa: E402
from core.encode import build_decode, build_encode  # noqa: E402
from core.params import RunParams  # noqa: E402
from core.tools import load  # noqa: E402
from core.util import cmdline, fmt_bytes  # noqa: E402

SAMPLES = ROOT / "samples"
ONEPY: Path | None = None
ONE_PY_PYTHON = Path(sys.executable)

FILE_SUFFIXES = (".exe", ".jpg", ".jpeg", ".png", ".jxl", ".avif", ".webp")


def win_split(line: str) -> list[str]:
    return [tok.strip('"') for tok in re.findall(r'"[^"]*"|\S+', line)]


def args_only(tokens: list[str]) -> list[str]:
    return [t for t in tokens if not t.lower().endswith(FILE_SUFFIXES)]


def compare_with_onepy(tools) -> None:
    print("\n== 与参考脚本的参数一致性 ==")
    if ONEPY is None or not ONEPY.exists():
        print("  跳过：未指定 --one-py（可选，用 bench/one.py 做参数比对）")
        return
    py = ONE_PY_PYTHON
    cases = [
        ("avif", ["--q", "90", "--tune", "iq", "--depth", "auto", "--speed", "4", "--yuv", "444"]),
        ("jxl", ["--distance", "1.0", "--effort", "7"]),
        ("webp", ["--q", "95", "--preset", "drawing", "--method", "6"]),
        ("png", ["--opt", "4", "--strip", "safe"]),
    ]
    jpg = next(iter(sorted(SAMPLES.glob("*.jpg"))), None)
    png = next(iter(sorted(SAMPLES.glob("*.png"))), None)
    if not jpg or not png:
        print("  跳过：样本不足")
        return
    for codec, extra in cases:
        src = png if codec == "png" else jpg
        ref = subprocess.run(
            [str(py), str(ONEPY), "-c", codec, *extra, "-i", str(src),
             "-o", f"out.{codec}", "--dry-run", "--no-s2"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        line = next((ln for ln in ref.stdout.splitlines() if ".exe" in ln), "")
        if not line:
            print(f"  {codec:5s} one.py 未输出命令：{ref.stdout[-200:]} {ref.stderr[-200:]}")
            continue
        ref_args = args_only(win_split(line.strip())[1:])

        params = RunParams()
        params.codec = codec
        mine = [str(a) for a in build_encode(codec, params, tools, src, Path(f"out.{codec}"))]
        mine_args = args_only(mine[1:])

        ok = ref_args == mine_args
        print(f"  {codec:5s} {'一致' if ok else '不一致'}")
        if not ok:
            print("    one.py:", " ".join(ref_args))
            print("    当前  :", " ".join(mine_args))


def run_all(tools) -> None:
    print("\n== 四编码器实跑（默认参数）==")
    params = RunParams()
    tmp = Path(tempfile.mkdtemp(prefix="imgpress_selftest_"))
    jpg = next(iter(sorted(SAMPLES.glob("*.jpg"))), None) or next(iter(sorted(SAMPLES.glob("*.jpeg"))), None)
    png = next(iter(sorted(SAMPLES.glob("*.png"))), None)
    if not jpg or not png:
        print("测试需要至少一张 jpg 和一张 png，当前目录不满足。")
        return
    cases = [
        ("avif", jpg),
        ("jxl", jpg),
        ("webp", jpg),
        ("png", png),
    ]
    for codec, src in cases:
        params.codec = codec
        dst = tmp / f"{codec}_out.{codec}"
        cmd = build_encode(codec, params, tools, src, dst)
        print("\n  " + cmdline(cmd))
        p = subprocess.run([str(c) for c in cmd], capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        if p.returncode != 0 or not dst.exists():
            tail = ((p.stdout or "") + (p.stderr or "")).strip().splitlines()
            print(f"   失败 rc={p.returncode}: {tail[-1] if tail else '-'}")
            continue
        size = dst.stat().st_size
        src_size = src.stat().st_size
        print(f"   OK  {fmt_bytes(src_size)} → {fmt_bytes(size)}  ({size / src_size * 100:.1f}%)")

        dec = build_decode(codec, tools, dst, tmp / f"{codec}_dec.png")
        if dec:
            subprocess.run([str(c) for c in dec], capture_output=True)
            dec_path = tmp / f"{codec}_dec.png"
            info = imageops.probe_size(dec_path) if dec_path.exists() else None
            print(f"   解码回读: {info}")

    print(f"\n  临时目录（已清理）: {tmp}")
    shutil.rmtree(tmp, ignore_errors=True)


def main() -> int:
    global SAMPLES, ONEPY, ONE_PY_PYTHON
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples", default=os.environ.get("IMGPESS_SAMPLES") or str(ROOT / "samples"))
    ap.add_argument("--one-py", default=os.environ.get("IMGPESS_ONEPY") or None)
    ap.add_argument("--one-py-python", default=os.environ.get("IMGPESS_ONEPY_PYTHON") or None,
                    help="运行 --one-py 的解释器（需要 numpy/Pillow）")
    args = ap.parse_args()
    SAMPLES = Path(args.samples)
    ONEPY = Path(args.one_py) if args.one_py else None
    if args.one_py_python:
        ONE_PY_PYTHON = Path(args.one_py_python)

    app = QCoreApplication(sys.argv)  # noqa: F841
    if not SAMPLES.is_dir():
        print(f"样本目录不存在：{SAMPLES}")
        print("把任意 jpg/png 放进 ./samples，或用 --samples 指定目录。")
        return 1
    tools = load(paths.default_tools_root())
    print("工具链:", tools.root)
    for name in ("cjxl", "djxl", "avifenc", "avifdec", "cwebp", "dwebp", "oxipng", "ssimulacra2"):
        print(f"  {name:12s} {tools.version(name)}")
    compare_with_onepy(tools)
    run_all(tools)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
