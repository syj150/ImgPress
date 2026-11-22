"""图像读取、格式转换、预览缓存。全部基于 Qt，不额外引入 Pillow。"""

from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QImageReader, QPainter

from . import paths
from .encode import build_decode
from .params import NATIVE_INPUT
from .tools import Toolchain

_NO_WINDOW = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0


class ImageError(RuntimeError):
    pass


def probe_size(path: Path) -> tuple[int, int] | None:
    reader = QImageReader(str(path))
    size = reader.size()
    if size.isValid() and size.width() > 0:
        return size.width(), size.height()
    img = QImage(str(path))
    if img.isNull():
        return None
    return img.width(), img.height()


def needs_conversion(src: Path, codec: str) -> bool:
    """该输入格式能否被对应编码器直接读取。"""
    return src.suffix.lower() not in NATIVE_INPUT[codec]


def flatten(img: QImage) -> QImage:
    """透明区域铺白底并转 8bit RGB —— 与 one.py 的 load_rgb 行为一致。"""
    if not img.hasAlphaChannel():
        return img.convertToFormat(QImage.Format_RGB32)
    canvas = QImage(img.size(), QImage.Format_RGB32)
    canvas.fill(Qt.white)
    painter = QPainter(canvas)
    painter.drawImage(0, 0, img)
    painter.end()
    return canvas


def convert_to_png(src: Path, dst: Path, flatten_alpha: bool = False) -> None:
    """用 Qt 把任意可读格式转为 PNG。"""
    img = QImage(str(src))
    if img.isNull():
        raise ImageError(f"无法读取图像：{src.name}")
    if flatten_alpha:
        img = flatten(img)
    if not img.save(str(dst), "PNG"):
        raise ImageError(f"无法写出 PNG：{dst.name}")


def decode_with_cli(codec: str, tools: Toolchain, src: Path, dst: Path) -> None:
    cmd = build_decode(codec, tools, src, dst)
    if not cmd:
        raise ImageError(f"{codec} 不需要解码")
    p = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=_NO_WINDOW,
    )
    if p.returncode != 0 or not dst.exists():
        lines = ((p.stdout or "") + (p.stderr or "")).strip().splitlines()
        raise ImageError(lines[-1] if lines else "解码失败")


def to_reference(src: Path, dst: Path, tools: Toolchain) -> Path:
    """任意输入 → SSIMULACRA2 参考 PNG（铺白底、8bit RGB）。"""
    ext = src.suffix.lower()
    if ext == ".jxl":
        decode_with_cli("jxl", tools, src, dst)
        return dst
    if ext == ".avif":
        decode_with_cli("avif", tools, src, dst)
        return dst
    convert_to_png(src, dst, flatten_alpha=True)
    return dst


# ---------------- 预览缓存 ----------------


def _cache_key(path: Path) -> str:
    st = path.stat()
    raw = f"{path.resolve()}|{st.st_size}|{int(st.st_mtime)}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def cached_preview(path: Path, codec: str, tools: Toolchain) -> Path:
    """把编码结果解码成 PNG 并缓存；同一文件同一时间戳只解一次。"""
    if codec == "png" or path.suffix.lower() == ".png":
        return path
    folder = paths.cache_dir() / "preview"
    folder.mkdir(parents=True, exist_ok=True)
    dst = folder / f"{_cache_key(path)}_{path.stem[:24]}.png"
    if dst.exists() and dst.stat().st_size > 0:
        os.utime(dst, None)
        return dst
    decode_with_cli(codec, tools, path, dst)
    _trim(folder, keep=24)
    return dst


def source_preview(src: Path, tools: Toolchain) -> Path:
    """源文件的预览图（JXL / AVIF 输入需先解码）。"""
    ext = src.suffix.lower()
    if ext in (".jxl", ".avif"):
        return cached_preview(src, "jxl" if ext == ".jxl" else "avif", tools)
    return src


def _trim(folder: Path, keep: int) -> None:
    files = sorted(folder.glob("*.png"), key=lambda p: p.stat().st_mtime, reverse=True)
    for old in files[keep:]:
        try:
            old.unlink()
        except OSError:
            pass
