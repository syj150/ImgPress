"""通用小工具：格式化、命令行拼装。"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def fmt_bytes(n: int | float | None) -> str:
    if n is None:
        return "—"
    n = float(n)
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            if unit == "B":
                return f"{n:.0f} {unit}"
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} GB"


def fmt_ratio(out_size: int | None, src_size: int | None) -> str:
    if not out_size or not src_size:
        return "—"
    pct = out_size / src_size * 100
    delta = pct - 100
    sign = "+" if delta > 0 else "−"
    return f"{pct:.1f}% ({sign}{abs(delta):.1f}%)"


def fmt_bpp(out_size: int | None, w: int | None, h: int | None) -> str:
    if not out_size or not w or not h:
        return "—"
    return f"{out_size * 8 / (w * h):.2f}"


def fmt_duration(seconds: float | None) -> str:
    if seconds is None:
        return "—"
    if seconds < 1:
        return f"{seconds * 1000:.0f} ms"
    if seconds < 60:
        return f"{seconds:.1f} s"
    m, s = divmod(int(round(seconds)), 60)
    if m < 60:
        return f"{m}m {s:02d}s"
    h, m = divmod(m, 60)
    return f"{h}h {m:02d}m"


def cmdline(cmd: list[str]) -> str:
    """人类可读的命令行（Windows 引号规则）。"""
    return subprocess.list2cmdline([str(c) for c in cmd])


def exe_suffix() -> str:
    return ".exe" if sys.platform == "win32" else ""


def human_path(p: Path | str) -> str:
    return str(p)


def strip_ext(name: str) -> str:
    return Path(name).stem


def short_path(p: Path, limit: int = 52) -> str:
    s = str(p)
    if len(s) <= limit:
        return s
    return "…" + s[-(limit - 1):]


def parse_number(text: str) -> float | None:
    try:
        return float(text.strip())
    except (ValueError, AttributeError):
        return None
