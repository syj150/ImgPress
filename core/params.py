"""编码参数模型：完整覆盖 bench/one.py 暴露的每一项参数。

字段语义与 one.py 一一对应，默认值保持一致，便于把命令行习惯直接搬到界面。
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields
from typing import Any

from i18n import tr

CODECS = ("jxl", "avif", "webp", "png")

CODEC_LABEL = {
    "jxl": "JPEG XL",
    "avif": "AVIF",
    "webp": "WebP",
    "png": "PNG 无损",
}

CODEC_ENGINE = {
    "jxl": "libjxl 0.13.0 · cjxl",
    "avif": "libavif 1.4.2 · libaom 3.14.1 · avifenc",
    "webp": "libwebp 1.6.0 · cwebp",
    "png": "oxipng 10.2.1",
}

EXT = {"jxl": "jxl", "avif": "avif", "webp": "webp", "png": "png"}


def codec_label(codec: str) -> str:
    """编码器显示名（按当前语言）。"""
    return tr(CODEC_LABEL.get(codec, codec))

# 各编码器可直接吃进去的输入格式；其余格式需先转 PNG
NATIVE_INPUT = {
    "jxl": {".png", ".jpg", ".jpeg", ".jfif"},
    "avif": {".png", ".jpg", ".jpeg", ".jfif"},
    "webp": {".png", ".jpg", ".jpeg", ".jfif", ".tif", ".tiff"},
    "png": {".png"},
}


@dataclass
class JxlParams:
    distance: float = 1.0
    effort: int = 7
    modular: bool = False
    lossless_jpeg: bool = False
    progressive: bool = False


@dataclass
class AvifParams:
    q: float = 90.0
    tune: str = "iq"
    depth: str = "auto"
    speed: int = 4
    yuv: str = "444"
    lossless: bool = False
    qalpha: float | None = None


@dataclass
class WebpParams:
    q: float = 95.0
    preset: str = "drawing"
    method: int = 6
    sharp_yuv: bool = True
    sns: int | None = None
    filter: int | None = None
    segments: int | None = None
    passes: int | None = None
    lossless: bool = False


@dataclass
class PngParams:
    opt: str = "4"
    strip: str = "safe"
    zopfli: bool = False


@dataclass
class RunParams:
    codec: str = "avif"
    keep_metadata: bool = False
    extra: str = ""
    calc_s2: bool = True
    jxl: JxlParams = field(default_factory=JxlParams)
    avif: AvifParams = field(default_factory=AvifParams)
    webp: WebpParams = field(default_factory=WebpParams)
    png: PngParams = field(default_factory=PngParams)

    # ---------- 序列化 ----------
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "RunParams":
        obj = cls()
        if not isinstance(data, dict):
            return obj
        for f in fields(cls):
            if f.name not in data:
                continue
            value = data[f.name]
            if f.name in ("jxl", "avif", "webp", "png"):
                if isinstance(value, dict):
                    setattr(obj, f.name, _build(getattr(obj, f.name), value))
                continue
            if f.name == "codec":
                if value in CODECS:
                    obj.codec = value
                continue
            coerced = _coerce(getattr(obj, f.name), value)
            if coerced is not _SKIP:
                setattr(obj, f.name, coerced)
        return obj

    # ---------- 便捷访问 ----------
    def sub(self):
        return getattr(self, self.codec)

    def effective_jxl_distance(self) -> float:
        # cjxl 的 JPEG 无损重打包要求 distance 为 0
        return 0.0 if self.jxl.lossless_jpeg else self.jxl.distance

    def effective_avif_depth(self) -> int:
        if self.avif.depth != "auto":
            return int(self.avif.depth)
        return 10 if self.avif.q <= 70 else 8


_SKIP = object()


def _coerce(current: Any, value: Any) -> Any:
    """按当前默认值的类型做最小转换；None 只在字段本身可为空时保留。"""
    if value is None:
        return None if current is None else _SKIP
    if isinstance(current, bool):
        return bool(value)
    if isinstance(current, int):
        try:
            return int(value)
        except (TypeError, ValueError):
            return _SKIP
    if isinstance(current, float):
        try:
            return float(value)
        except (TypeError, ValueError):
            return _SKIP
    if isinstance(current, str):
        return str(value)
    return value


def _build(obj: Any, data: dict[str, Any]):
    for f in fields(obj):
        if f.name not in data:
            continue
        coerced = _coerce(getattr(obj, f.name), data[f.name])
        if coerced is not _SKIP:
            setattr(obj, f.name, coerced)
    return obj


@dataclass
class Notice:
    level: str  # info / warn / error
    text: str


def validate(p: RunParams) -> list[Notice]:
    """返回影响执行的提示。error 会阻止开始，warn 仅提示。"""
    out: list[Notice] = []

    if p.codec == "jxl":
        j = p.jxl
        if j.lossless_jpeg and j.distance != 0:
            out.append(Notice("info", tr("JPEG 无损重打包要求 distance = 0，已按 0 执行。")))
        if j.lossless_jpeg and p.keep_metadata:
            out.append(Notice("warn", tr("JPEG 无损重打包无法剥离元数据，保留元数据开关在此模式下不生效。")))
        if j.modular and j.distance > 0:
            out.append(Notice("info", tr("模块化有损模式易在渐变处出现色带，务必放大检查。")))
        if j.distance == 0 and not j.modular:
            out.append(Notice("info", tr("distance = 0 时 cjxl 自动切到模块化无损。")))
    elif p.codec == "avif":
        a = p.avif
        if a.lossless:
            out.append(Notice("info", tr("AVIF 无损对照片通常比原文件更大，仅归档场景值得。")))
        if not a.lossless and a.q >= 92:
            out.append(Notice("warn", tr("AVIF q ≥ 92 后边际收益急剧下降（q90→92 体积 +29%，S2 仅 +0.7）。")))
        if not a.lossless and a.yuv in ("420", "400"):
            out.append(Notice("warn", tr("yuv {yuv} 会明显损失彩色边缘，彩色线稿不建议。", yuv=a.yuv)))
        if a.qalpha is not None and a.lossless:
            out.append(Notice("info", tr("无损模式下 qalpha 不生效。")))
    elif p.codec == "webp":
        w = p.webp
        if not w.lossless and w.q >= 100:
            out.append(Notice("warn", tr("WebP q = 100 仍是有损，只是最高档。")))
        if w.lossless and p.keep_metadata:
            out.append(Notice("info", tr("WebP 无损 + 保留元数据时，EXIF/XMP 仍不会写入。")))
    else:
        g = p.png
        if not p.keep_metadata and g.strip == "all":
            out.append(Notice("warn", tr("--strip all 会连 ICC 一起删除，广色域图片会出现颜色偏移。")))
        if g.opt == "max" and g.zopfli:
            out.append(Notice("info", "opt = max 叠加 zopfli 会非常慢，收益通常不足 1%。"))
    return out
