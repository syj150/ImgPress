"""工具链定位与版本探测。

工具链目录结构（与 bench 项目一致，扁平化拷贝后同样可用）：
    tools/bin/jxl/cjxl.exe
    tools/bin/avif/avifenc.exe
    tools/bin/webp/cwebp.exe
    tools/bin/oxipng/oxipng.exe
实际扫描为递归按文件名匹配，目录层级可任意。
"""

from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from i18n import tr

TOOL_NAMES = {
    "cjxl": "cjxl.exe",
    "djxl": "djxl.exe",
    "ssimulacra2": "ssimulacra2.exe",
    "cwebp": "cwebp.exe",
    "dwebp": "dwebp.exe",
    "avifenc": "avifenc.exe",
    "avifdec": "avifdec.exe",
    "oxipng": "oxipng.exe",
}

# 每个编码器工作所必需的可执行文件
REQUIRED = {
    "jxl": ("cjxl",),
    "avif": ("avifenc",),
    "webp": ("cwebp",),
    "png": ("oxipng",),
}

_SCAN_CACHE: dict[str, dict[str, Path]] = {}
_VERSION_CACHE: dict[str, str] = {}


def _scan(root: Path) -> dict[str, Path]:
    key = str(root)
    if key in _SCAN_CACHE:
        return _SCAN_CACHE[key]
    wanted = {v.lower(): k for k, v in TOOL_NAMES.items()}
    found: dict[str, Path] = {}
    for dirpath, _dirnames, filenames in os.walk(root):
        for fn in filenames:
            key_name = fn.lower()
            if key_name in wanted and wanted[key_name] not in found:
                found[wanted[key_name]] = Path(dirpath) / fn
        if len(found) == len(wanted):
            break
    _SCAN_CACHE[key] = found
    return found


@dataclass
class Toolchain:
    root: Path
    paths: dict[str, Path] = field(default_factory=dict)

    def get(self, name: str) -> Path | None:
        return self.paths.get(name)

    def has(self, *names: str) -> bool:
        return all(n in self.paths for n in names)

    def missing_for(self, codec: str) -> list[str]:
        return [n for n in REQUIRED.get(codec, ()) if n not in self.paths]

    @property
    def available_codecs(self) -> list[str]:
        return [c for c in ("jxl", "avif", "webp", "png") if not self.missing_for(c)]

    def version(self, name: str) -> str:
        path = self.paths.get(name)
        if not path:
            return tr("未找到")
        key = str(path)
        if key in _VERSION_CACHE:
            return _VERSION_CACHE[key]
        text = _probe_version(path)
        _VERSION_CACHE[key] = text
        return text


def load(root: Path | str | None) -> Toolchain:
    if root is None:
        return Toolchain(Path(""), {})
    root = Path(root)
    if not root.is_dir():
        return Toolchain(root, {})
    return Toolchain(root, _scan(root))


VERSION_FLAGS = {
    "cjxl": "--version",
    "djxl": "--version",
    "avifenc": "--version",
    "avifdec": "--version",
    "cwebp": "-version",
    "dwebp": "-version",
    "oxipng": "--version",
}


def _probe_version(exe: Path) -> str:
    name = exe.stem.lower()
    if name == "ssimulacra2":
        return tr("内置")
    flag = VERSION_FLAGS.get(name)
    if not flag:
        return "—"

    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    try:
        p = subprocess.run(
            [str(exe), flag],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=8,
            creationflags=flags,
        )
    except (OSError, subprocess.SubprocessError):
        return tr("无法执行")

    out = ((p.stdout or "") + (p.stderr or "")).strip()
    if not out:
        return tr("未知")

    if name in ("avifenc", "avifdec"):
        m = re.search(r"Version:\s*([^\s(]+)(?:.*?aom\s*\[enc\]:([\w.\-]+))?", out)
        if m:
            ver, aom = m.group(1), m.group(2)
            return f"{ver} · aom {aom}" if aom else ver
    if name in ("cjxl", "djxl"):
        m = re.search(r"v(\d+\.\d+\.\d+)", out)
        if m:
            return m.group(1)
    if name in ("cwebp", "dwebp"):
        m = re.search(r"^(\d+\.\d+\.\d+)", out.strip())
        if m:
            return m.group(1)
    if name == "oxipng":
        m = re.search(r"(\d+\.\d+\.\d+)", out)
        if m:
            return m.group(1)
    return out.splitlines()[0].strip()[:40]
