"""命令构造：把 RunParams 翻译成 cjxl / avifenc / cwebp / oxipng 的参数序列。

与 bench/one.py 的 build_cmd() 逐项对应，额外补上 -j 1 与 distance 的强制一致。
"""

from __future__ import annotations

import shlex
from pathlib import Path

from .params import EXT, RunParams
from .tools import Toolchain


class ToolMissing(RuntimeError):
    pass


def _extra(text: str) -> list[str]:
    text = (text or "").strip()
    if not text:
        return []
    try:
        return shlex.split(text, posix=True)
    except ValueError:
        return text.split()


def _num(value: float) -> str:
    return f"{value:g}"


def _num_decimal(value: float) -> str:
    """至少保留一位小数，与 cjxl 的习惯写法一致（1.0 而不是 1）。"""
    text = f"{value:.4f}".rstrip("0")
    return text + "0" if text.endswith(".") else text


def _tool(t: Toolchain, name: str) -> str:
    path = t.get(name)
    if not path:
        raise ToolMissing(f"缺少 {name}.exe，请检查工具目录")
    return str(path)


def build_encode(codec: str, p: RunParams, t: Toolchain, src: Path, dst: Path) -> list[str]:
    extra = _extra(p.extra)
    src_s, dst_s = str(src), str(dst)

    if codec == "jxl":
        j = p.jxl
        opts = ["-d", _num_decimal(p.effective_jxl_distance()), "-e", str(j.effort)]
        opts += ["-j", "1" if j.lossless_jpeg else "0"]
        if j.modular:
            opts += ["-m", "1"]
        if j.progressive:
            opts += ["-p"]
        if not p.keep_metadata and not j.lossless_jpeg:
            # cjxl 只能按类型剥离；ICC 不在可剥列表内，会被保留
            opts += ["-x", "strip=exif", "-x", "strip=xmp"]
        return [_tool(t, "cjxl"), src_s, dst_s, *opts, *extra]

    if codec == "avif":
        a = p.avif
        opts = ["--yuv", a.yuv]
        if a.lossless:
            opts += ["-l"]
        else:
            opts += [
                "-q", _num(a.q),
                "-d", str(p.effective_avif_depth()),
                "-s", str(a.speed),
                "-a", f"tune={a.tune}",
            ]
            if a.qalpha is not None:
                opts += ["--qalpha", _num(a.qalpha)]
        if not p.keep_metadata:
            opts += ["--ignore-exif", "--ignore-xmp"]
        return [_tool(t, "avifenc"), *opts, *extra, src_s, dst_s]

    if codec == "webp":
        w = p.webp
        if w.lossless:
            opts = ["-lossless", "-z", "9", "-exact", "-mt"]
        else:
            opts = ["-q", _num(w.q), "-m", str(w.method), "-preset", w.preset]
            if w.sharp_yuv:
                opts.append("-sharp_yuv")
            if w.sns is not None:
                opts += ["-sns", str(w.sns)]
            if w.filter is not None:
                opts += ["-f", str(w.filter)]
            if w.segments is not None:
                opts += ["-segments", str(w.segments)]
            if w.passes is not None:
                opts += ["-pass", str(w.passes)]
        if not p.keep_metadata:
            opts += ["-metadata", "icc"]
        return [_tool(t, "cwebp"), *opts, *extra, src_s, "-o", dst_s]

    if codec == "png":
        g = p.png
        strip = "none" if p.keep_metadata else g.strip
        opts = ["-o", str(g.opt)]
        if strip != "none":
            opts += ["--strip", strip]
        if g.zopfli:
            opts.append("-z")
        return [_tool(t, "oxipng"), *opts, *extra, "--out", dst_s, src_s]

    raise ValueError(f"未知编码器: {codec}")


def build_decode(codec: str, t: Toolchain, src: Path, dst: Path) -> list[str] | None:
    """把编码结果解回 PNG，用于预览与 SSIMULACRA2。"""
    if codec == "jxl":
        return [_tool(t, "djxl"), str(src), str(dst)]
    if codec == "avif":
        return [_tool(t, "avifdec"), "--depth", "8", str(src), str(dst)]
    if codec == "webp":
        return [_tool(t, "dwebp"), str(src), "-o", str(dst)]
    return None


def output_suffix(codec: str) -> str:
    return "." + EXT[codec]


def preview_command(codec: str, p: RunParams, t: Toolchain) -> str:
    """界面上展示的命令预览（用示例文件名，不产生副作用）。"""
    src = Path("input.png") if codec == "png" else Path("input.jpg")
    dst = src.with_suffix(output_suffix(codec))
    try:
        cmd = build_encode(codec, p, t, src, dst)
    except ToolMissing as exc:
        return f"（{exc}）"
    return _readable(cmd, t)


def _readable(cmd: list[str], t: Toolchain) -> str:
    from .util import cmdline

    root = str(t.root) if t.root else ""
    shown: list[str] = []
    for i, part in enumerate(cmd):
        norm = str(part).replace("/", "\\")
        if i == 0:
            shown.append(norm.split("\\")[-1])
        elif root and norm.startswith(root.replace("/", "\\")):
            shown.append(norm[len(root) + 1:])
        else:
            shown.append(norm)
    return cmdline(shown)
