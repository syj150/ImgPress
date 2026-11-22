"""编码参数面板：四个编码器分页 + 通用项 + 实时命令预览。

参数说明文字取自 bench/参数手册.md，悬停「?」即可查看。
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QGuiApplication, QIntValidator, QDoubleValidator
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from i18n import tr

from core import encode
from core.params import CODECS, CODEC_ENGINE, RunParams, codec_label, validate
from core.tools import Toolchain
from . import theme
from .widgets import Check, Combo, DSpin, InfoDot, Spin, field_label, hint_label, section_label

TIPS = {
    "jxl.d": "Butteraugli 距离（JND），描述目标失真程度而非压缩率。\n"
             "0 = 数学无损（强制模块化）；0.5 近无损（S2 86–92）；1.0 官方视觉无损（S2 84–90）；\n"
             "2.0 良好网页质量；3.0 中等；>4 明显失真。漫画网点这类高频内容 -d 1.0 实测只有 84 左右。",
    "jxl.e": "编码搜索强度 1–10。不改变质量目标，只决定为达到目标愿意花多少计算。\n"
             "同 -d 下 e7→e10 通常再小 3%–8%，画质基本不变，时间超线性增长。批量筛 7，终稿 9–10。",
    "jxl.m": "强制模块化模式（预测器 + 调色板 + squeeze）。平涂、UI、线稿有损下可能比 VarDCT 小 20% 以上；\n"
             "照片通常更差，且没有 DCT 的平滑过渡，渐变处容易出现色带。",
    "jxl.j": "对 JPEG 输入启用 -j 1，把原始 JPEG 码流原样装进 JXL 容器（jbrd），不重新编码像素。\n"
             "体积约降 20%、画质零损失、可逐字节还原原 JPEG。要求 distance = 0；产物需 djxl 才能还原。",
    "jxl.p": "渐进/响应式解码，体积 +1%–3%，画质不变。网络首屏更快，本地文件无意义。",
    "avif.q": "0–100，内部映射到 AV1 量化器，不是线性百分比。高段边际收益急剧下降：\n"
              "q90→q92 体积 +29%、S2 只 +0.7。拐点在 88–90。",
    "avif.tune": "RD 优化时偏向哪种失真度量。\n"
                 "iq = 感知向，同 q 下明显更小（实测省 11%–27%），纹理略平滑；\n"
                 "ssim = 保局部对比与结构，体积更大；psnr = 像素误差，感知上通常不是最优。",
    "avif.depth": "输出位深。影响不是单调的，交叉点在 q ≈ 70：\n"
                  "q ≤ 70 用 10bit 反而更小（−0.4% ~ −1.6%）且色度台阶细 4 倍；\n"
                  "q ≥ 80 用 8bit（10bit 体积 +3%–15%）。auto 按 q 自动选择。",
    "avif.speed": "编码速度档 0–10，越小越慢、搜索越充分。6→4 约省 2%，4→2 再约 2%，\n"
                  "低于 2 收益递减且极慢。它改变 RD 决策质量，因此同 q 下体积与画质都会轻微变化。",
    "avif.yuv": "色度抽样。444 完整色度，彩色线稿必须用；\n"
                "420 省约 6.7% 但 S2 掉约 6，红线/蓝线交界会渗色；400 灰度可省约 25%；422 少用。",
    "avif.qalpha": "alpha 通道单独质量。过低会出现锯齿/半透明脏边，过高显著增体积。留空跟随主质量。",
    "webp.q": "有损质量 0–100。100 仍然是有损，只是最高档。\n"
              "q95→q92 体积 −21%、S2 −0.7；q90 以下掉得更快。WebP 的 S2 上限普遍 82–85，是格式瓶颈。",
    "webp.preset": "一组内部参数预设（滤波强度、SNS、预处理），±1%–3% 体积。\n"
                   "drawing 适合线稿/漫画，photo 自然图像，icon 小图标，text 文字截图。",
    "webp.m": "压缩搜索方法 0–6，越大越慢越充分。6→4 省时间但体积 +2%–5%。通常直接用 6。",
    "webp.sharp": "使用更锐利的 RGB→YUV420 转换，仅对 4:2:0 有损有效，可减轻彩色边缘发虚。",
    "webp.sns": "空间噪声整形 0–100。数值高会保留更多纹理/噪点；插画 80 左右可保住颗粒感，平涂可低一些。",
    "webp.filter": "环路滤波强度 0–100。高值平滑块边界，低值保锐度但块效应更明显。线稿可试 0–20，照片 20–40。",
    "webp.seg": "量化分段数（1–4）与分析遍数（1–10）。提高会略小略慢，实测整体约 1% 收益，投入产出比很低。",
    "png.opt": "优化级别 0–6 或 max，尝试更多滤波/压缩组合，纯无损。−o 4 → max 通常只多 0.2 个百分点却慢 5 倍。",
    "png.strip": "元数据清理。safe 只删不影响渲染的块并保留 ICC/sRGB/pHYs；\n"
                 "all 删所有非关键块（会连 ICC 一起删，广色域图片会偏色）；none 全保留。",
    "png.z": "用 Zopfli 重压 deflate，比 zlib 小 3%–8%，慢 10–100 倍，仍然无损。",
    "common.meta": "默认只保留 ICC，剥离 EXIF/XMP：\n"
                   "AVIF  --ignore-exif --ignore-xmp\nJXL   -x strip=exif -x strip=xmp\n"
                   "WebP  -metadata icc\nPNG   --strip safe\n实测对体积影响通常小于 0.5%。",
    "common.s2": "SSIMULACRA2：100 = 与原始不可区分，90 = 1:1 视觉无损，85 = 闪烁测试不可辨，\n"
                 "80 = 高质量，70 = 中等。它对平滑有偏好，只适合筛查，最终仍要看 200% 裁切。\n"
                 "开启后每张图会多一次解码 + 评分，批量处理会明显变慢。",
    "common.extra": "原样透传给编码器，用于脚本未单独列出的高级项。示例：\n"
                    "JXL   --gaborish=0 --epf=1 --faster_decoding=2\n"
                    "AVIF  -a sharpness=4 -a aq-mode=1\n"
                    "参数含义见参数手册第 2、3 节的「未暴露高级项」。",
}


class OptEdit(QLineEdit):
    """可选数值：留空表示使用编码器默认值。"""

    def __init__(self, integer: bool = True, lo: float = 0, hi: float = 100, placeholder: str | None = None, width: int = 96, parent=None) -> None:
        super().__init__(parent)
        self.setPlaceholderText(placeholder or tr("默认"))
        self.setValidator(QIntValidator(int(lo), int(hi), self) if integer else QDoubleValidator(lo, hi, 2, self))
        self.setFixedWidth(width)

    def value(self, integer: bool = True):
        text = self.text().strip()
        if not text:
            return None
        try:
            return int(text) if integer else float(text)
        except ValueError:
            return None

    def set_value(self, value) -> None:
        self.setText("" if value is None else f"{value:g}")


class ParamsPanel(QWidget):
    params_changed = Signal()
    codec_changed = Signal(str)

    def __init__(self, params: RunParams, tools: Toolchain, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._params = params
        self._tools = tools
        self._loading = False

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setUsesScrollButtons(False)
        self.tabs.setMinimumHeight(132)
        self.tabs.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        for codec in CODECS:
            self.tabs.addTab(self._wrap(self._build_page(codec)), codec_label(codec))

        self.engine_label = QLabel("")
        self.engine_label.setObjectName("Hint")

        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        title_row.addWidget(section_label(tr("编码参数")))
        title_row.addStretch(1)
        title_row.addWidget(self.engine_label)

        # 通用项
        self.chk_meta = Check(tr("保留 EXIF / XMP"), tr(TIPS["common.meta"]))
        self.chk_s2 = Check(tr("计算 SSIMULACRA2"), tr(TIPS["common.s2"]))
        self.edit_extra = QLineEdit()
        self.edit_extra.setPlaceholderText(tr("留空不传，例如 --gaborish=0"))
        self.edit_extra.setToolTip(tr(TIPS["common.extra"]))

        meta_row = QHBoxLayout()
        meta_row.setSpacing(18)
        meta_row.addWidget(self.chk_meta)
        meta_row.addWidget(self.chk_s2)
        meta_row.addStretch(1)

        extra_row = QHBoxLayout()
        extra_row.setSpacing(6)
        extra_row.addWidget(field_label(tr("额外参数"), tr(TIPS["common.extra"])))
        extra_row.addWidget(self.edit_extra, 1)
        extra_row.addWidget(InfoDot(tr(TIPS["common.extra"])))

        self.micro_hint = QLabel(
            tr("「?」里的 S2 与体积为单张样本实测值，不同图片差异很大，仅作方向参考。")
        )
        self.micro_hint.setObjectName("MicroHint")
        self.micro_hint.setWordWrap(True)

        self.notice = QLabel("")
        self.notice.setWordWrap(True)
        self.notice.setObjectName("Hint")
        self.notice.setStyleSheet("QLabel{color:%s;font-size:12px;}" % theme.WARN)
        self.notice.setVisible(False)

        # 命令预览
        self.cmd_label = QLabel("")
        self.cmd_label.setObjectName("Mono")
        self.cmd_label.setWordWrap(True)
        self.cmd_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.cmd_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        cmd_box = QWidget()
        cmd_box.setStyleSheet(
            "QWidget{background:#F9FAFB;border:1px solid #EDF0F3;border-radius:7px;}"
        )
        cb = QVBoxLayout(cmd_box)
        cb.setContentsMargins(10, 8, 10, 8)
        cb.setSpacing(4)
        cmd_head = QHBoxLayout()
        cmd_head.setContentsMargins(0, 0, 0, 0)
        head_label = QLabel(tr("将执行的命令"))
        head_label.setObjectName("Hint")
        self.btn_copy = QPushButton(tr("复制"))
        self.btn_copy.setProperty("role", "ghost")
        self.btn_copy.clicked.connect(self._copy_cmd)
        cmd_head.addWidget(head_label)
        cmd_head.addStretch(1)
        cmd_head.addWidget(self.btn_copy)
        cb.addLayout(cmd_head)
        cb.addWidget(self.cmd_label)

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 12)
        root.setSpacing(9)
        root.addLayout(title_row)
        root.addWidget(self.tabs)
        root.addWidget(self.notice)
        root.addWidget(self._divider())
        root.addLayout(meta_row)
        root.addLayout(extra_row)
        root.addWidget(self.micro_hint)
        root.addWidget(self._divider())
        root.addWidget(cmd_box)
        root.addStretch(1)

        self._wire()
        self.from_params(params)

    # ---------------- 构建 ----------------
    def _divider(self) -> QWidget:
        line = QWidget()
        line.setFixedHeight(1)
        line.setStyleSheet("background:#EFF1F4;")
        return line

    def _grid(self) -> tuple[QWidget, QGridLayout]:
        page = QWidget()
        grid = QGridLayout(page)
        grid.setContentsMargins(2, 8, 2, 4)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)
        grid.setColumnMinimumWidth(0, 78)
        grid.setColumnStretch(1, 1)
        return page, grid

    def _wrap(self, content: QWidget) -> QWidget:
        """每个分页内部单独滚动，保证通用项与命令预览始终可见。"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setMinimumHeight(104)
        scroll.setWidget(content)
        return scroll

    def _add(self, grid: QGridLayout, row: int, text: str, widget: QWidget, tip: str = "") -> QWidget:
        tip = tr(tip) if tip else ""
        label = field_label(text, tip)
        if tip:
            label.setCursor(Qt.WhatsThisCursor)
        grid.addWidget(label, row, 0, Qt.AlignLeft | Qt.AlignVCenter)
        holder = QWidget()
        h = QHBoxLayout(holder)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(6)
        h.addWidget(widget, 0)
        if tip:
            h.addWidget(InfoDot(tip), 0)
        h.addStretch(1)
        grid.addWidget(holder, row, 1)
        return label

    def _build_page(self, codec: str) -> QWidget:
        page, grid = self._grid()

        if codec == "jxl":
            self.j_distance = DSpin()
            self.j_distance.setRange(0.0, 25.0)
            self.j_distance.setSingleStep(0.1)
            self.j_distance.setDecimals(2)
            self.j_distance.setFixedWidth(110)
            self.j_effort = Spin()
            self.j_effort.setRange(1, 10)
            self.j_effort.setFixedWidth(110)
            self.j_modular = Check(tr("强制模块化"), tr(TIPS["jxl.m"]))
            self.j_lossless_jpeg = Check(tr("JPEG 无损重打包（-j 1）"), tr(TIPS["jxl.j"]))
            self.j_progressive = Check(tr("渐进式（-p）"), tr(TIPS["jxl.p"]))
            self._add(grid, 0, "distance", self.j_distance, TIPS["jxl.d"])
            self._add(grid, 1, "effort", self.j_effort, TIPS["jxl.e"])
            grid.addWidget(self.j_modular, 2, 1)
            grid.addWidget(self.j_lossless_jpeg, 3, 1)
            grid.addWidget(self.j_progressive, 4, 1)
            grid.setRowStretch(5, 1)

        elif codec == "avif":
            self.a_q = DSpin()
            self.a_q.setRange(0.0, 100.0)
            self.a_q.setSingleStep(0.5)
            self.a_q.setDecimals(1)
            self.a_q.setFixedWidth(110)
            self.a_tune = Combo()
            self.a_tune.addItems(["iq", "ssim", "psnr"])
            self.a_tune.setFixedWidth(110)
            self.a_depth = Combo()
            self.a_depth.addItems(["auto", "8", "10", "12"])
            self.a_depth.setFixedWidth(110)
            self.a_speed = Spin()
            self.a_speed.setRange(0, 10)
            self.a_speed.setFixedWidth(110)
            self.a_yuv = Combo()
            self.a_yuv.addItems(["444", "422", "420", "400"])
            self.a_yuv.setFixedWidth(110)
            self.a_qalpha = OptEdit(integer=False, lo=0, hi=100, placeholder=tr("跟随主质量"), width=112)
            self.a_lossless = Check(tr("无损（-l）"), tr("AVIF 无损对照片通常比原文件更大，只有归档/法证场景值得。"))
            self._add(grid, 0, tr("质量 q"), self.a_q, TIPS["avif.q"])
            self._add(grid, 1, "tune", self.a_tune, TIPS["avif.tune"])
            self._add(grid, 2, tr("位深"), self.a_depth, TIPS["avif.depth"])
            self._add(grid, 3, "speed", self.a_speed, TIPS["avif.speed"])
            self._add(grid, 4, tr("色度抽样"), self.a_yuv, TIPS["avif.yuv"])
            self._add(grid, 5, "qalpha", self.a_qalpha, TIPS["avif.qalpha"])
            grid.addWidget(self.a_lossless, 6, 1)
            grid.setRowStretch(7, 1)

        elif codec == "webp":
            self.w_q = DSpin()
            self.w_q.setRange(0.0, 100.0)
            self.w_q.setSingleStep(1.0)
            self.w_q.setDecimals(1)
            self.w_q.setFixedWidth(110)
            self.w_preset = Combo()
            self.w_preset.addItems(["default", "photo", "picture", "drawing", "icon", "text"])
            self.w_preset.setFixedWidth(110)
            self.w_method = Spin()
            self.w_method.setRange(0, 6)
            self.w_method.setFixedWidth(110)
            self.w_sharp = Check("sharp_yuv", tr(TIPS["webp.sharp"]))
            self.w_sns = OptEdit(integer=True, lo=0, hi=100)
            self.w_filter = OptEdit(integer=True, lo=0, hi=100)
            self.w_segments = OptEdit(integer=True, lo=1, hi=4, placeholder="1–4")
            self.w_pass = OptEdit(integer=True, lo=1, hi=10, placeholder="1–10")
            self.w_lossless = Check(tr("无损（-lossless -z 9 -exact）"), tr("VP8L 无损。平涂插画上常比 PNG 小，但通常大于 JXL 无损。"))
            self._add(grid, 0, tr("质量 q"), self.w_q, TIPS["webp.q"])
            self._add(grid, 1, "preset", self.w_preset, TIPS["webp.preset"])
            self._add(grid, 2, "method", self.w_method, TIPS["webp.m"])
            self._add(grid, 3, "sns", self.w_sns, TIPS["webp.sns"])
            self._add(grid, 4, "filter", self.w_filter, TIPS["webp.filter"])
            self._add(grid, 5, "segments", self.w_segments, TIPS["webp.seg"])
            self._add(grid, 6, "pass", self.w_pass, TIPS["webp.seg"])
            grid.addWidget(self.w_sharp, 7, 1)
            grid.addWidget(self.w_lossless, 8, 1)
            grid.setRowStretch(9, 1)

        else:  # png
            self.p_opt = Combo()
            self.p_opt.addItems(["0", "1", "2", "3", "4", "5", "6", "max"])
            self.p_opt.setFixedWidth(110)
            self.p_strip = Combo()
            self.p_strip.addItems(["safe", "all", "none"])
            self.p_strip.setFixedWidth(110)
            self.p_zopfli = Check(tr("Zopfli 重压（-z）"), tr(TIPS["png.z"]))
            self._add(grid, 0, tr("优化级别"), self.p_opt, TIPS["png.opt"])
            self._add(grid, 1, tr("元数据清理"), self.p_strip, TIPS["png.strip"])
            grid.addWidget(self.p_zopfli, 2, 1)
            note = hint_label(tr("oxipng 只处理 PNG 输入；其它格式会跳过。整个过程无画质损失。"))
            grid.addWidget(note, 3, 1)
            grid.setRowStretch(4, 1)

        return page

    # ---------------- 事件 ----------------
    def _wire(self) -> None:
        self.tabs.currentChanged.connect(self._on_tab)
        for w in (self.j_distance, self.j_effort, self.a_q, self.a_speed, self.w_q, self.w_method):
            w.valueChanged.connect(self._changed)
        for w in (self.a_tune, self.a_depth, self.a_yuv, self.w_preset, self.p_opt, self.p_strip):
            w.currentIndexChanged.connect(self._changed)
        for w in (self.j_modular, self.j_lossless_jpeg, self.j_progressive, self.a_lossless,
                  self.w_sharp, self.w_lossless, self.p_zopfli, self.chk_meta, self.chk_s2):
            w.toggled.connect(self._changed)
        for w in (self.a_qalpha, self.w_sns, self.w_filter, self.w_segments, self.w_pass, self.edit_extra):
            w.textChanged.connect(self._changed)

    def _on_tab(self, index: int) -> None:
        codec = CODECS[index]
        self._params.codec = codec
        self.engine_label.setText(CODEC_ENGINE[codec])
        self._apply_interlocks()
        self.codec_changed.emit(codec)
        self._changed()

    def _apply_interlocks(self) -> None:
        jl = self.j_lossless_jpeg.isChecked()
        self.j_distance.setEnabled(not jl)
        self.j_modular.setEnabled(not jl)
        self.j_progressive.setEnabled(not jl)

        al = self.a_lossless.isChecked()
        for w in (self.a_q, self.a_tune, self.a_depth, self.a_qalpha):
            w.setEnabled(not al)

        wl = self.w_lossless.isChecked()
        for w in (self.w_q, self.w_preset, self.w_method, self.w_sharp, self.w_sns,
                  self.w_filter, self.w_segments, self.w_pass):
            w.setEnabled(not wl)

    def _changed(self) -> None:
        if self._loading:
            return
        self.to_params()
        self._apply_interlocks()
        self.refresh_preview()
        self.params_changed.emit()

    # ---------------- 读写 ----------------
    def to_params(self) -> RunParams:
        p = self._params
        p.codec = CODECS[self.tabs.currentIndex()]
        p.keep_metadata = self.chk_meta.isChecked()
        p.calc_s2 = self.chk_s2.isChecked()
        p.extra = self.edit_extra.text().strip()

        p.jxl.distance = round(self.j_distance.value(), 2)
        p.jxl.effort = self.j_effort.value()
        p.jxl.modular = self.j_modular.isChecked()
        p.jxl.lossless_jpeg = self.j_lossless_jpeg.isChecked()
        p.jxl.progressive = self.j_progressive.isChecked()

        p.avif.q = round(self.a_q.value(), 1)
        p.avif.tune = self.a_tune.currentText()
        p.avif.depth = self.a_depth.currentText()
        p.avif.speed = self.a_speed.value()
        p.avif.yuv = self.a_yuv.currentText()
        p.avif.qalpha = self.a_qalpha.value(integer=False)
        p.avif.lossless = self.a_lossless.isChecked()

        p.webp.q = round(self.w_q.value(), 1)
        p.webp.preset = self.w_preset.currentText()
        p.webp.method = self.w_method.value()
        p.webp.sharp_yuv = self.w_sharp.isChecked()
        p.webp.sns = self.w_sns.value(integer=True)
        p.webp.filter = self.w_filter.value(integer=True)
        p.webp.segments = self.w_segments.value(integer=True)
        p.webp.passes = self.w_pass.value(integer=True)
        p.webp.lossless = self.w_lossless.isChecked()

        p.png.opt = self.p_opt.currentText()
        p.png.strip = self.p_strip.currentText()
        p.png.zopfli = self.p_zopfli.isChecked()
        return p

    def from_params(self, p: RunParams) -> None:
        self._loading = True
        self._params = p
        self.tabs.setCurrentIndex(CODECS.index(p.codec) if p.codec in CODECS else 0)
        self.chk_meta.setChecked(p.keep_metadata)
        self.chk_s2.setChecked(p.calc_s2)
        self.edit_extra.setText(p.extra)

        self.j_distance.setValue(p.jxl.distance)
        self.j_effort.setValue(p.jxl.effort)
        self.j_modular.setChecked(p.jxl.modular)
        self.j_lossless_jpeg.setChecked(p.jxl.lossless_jpeg)
        self.j_progressive.setChecked(p.jxl.progressive)

        self.a_q.setValue(p.avif.q)
        self._set_combo(self.a_tune, p.avif.tune)
        self._set_combo(self.a_depth, p.avif.depth)
        self.a_speed.setValue(p.avif.speed)
        self._set_combo(self.a_yuv, p.avif.yuv)
        self.a_qalpha.set_value(p.avif.qalpha)
        self.a_lossless.setChecked(p.avif.lossless)

        self.w_q.setValue(p.webp.q)
        self._set_combo(self.w_preset, p.webp.preset)
        self.w_method.setValue(p.webp.method)
        self.w_sharp.setChecked(p.webp.sharp_yuv)
        self.w_sns.set_value(p.webp.sns)
        self.w_filter.set_value(p.webp.filter)
        self.w_segments.set_value(p.webp.segments)
        self.w_pass.set_value(p.webp.passes)
        self.w_lossless.setChecked(p.webp.lossless)

        self._set_combo(self.p_opt, p.png.opt)
        self._set_combo(self.p_strip, p.png.strip)
        self.p_zopfli.setChecked(p.png.zopfli)

        self.engine_label.setText(CODEC_ENGINE[p.codec])
        self._loading = False
        self._apply_interlocks()
        self.refresh_preview()

    @staticmethod
    def _set_combo(combo: QComboBox, text: str) -> None:
        idx = combo.findText(text)
        if idx >= 0:
            combo.setCurrentIndex(idx)

    # ---------------- 预览 ----------------
    def set_tools(self, tools: Toolchain) -> None:
        self._tools = tools
        self.refresh_preview()

    def refresh_preview(self) -> None:
        p = self._params
        self.cmd_label.setText(encode.preview_command(p.codec, p, self._tools))
        notices = validate(p)
        warn = [n for n in notices if n.level == "warn"]
        info = [n for n in notices if n.level == "info"]
        chosen = warn or info
        if chosen:
            suffix = " " + tr("等 {count} 条提示", count=len(chosen) - 1) if len(chosen) > 1 else ""
            self.notice.setText("· " + chosen[0].text + suffix)
            self.notice.setVisible(True)
            self.notice.setStyleSheet(
                "QLabel{color:%s;font-size:12px;}" % (theme.WARN if warn else theme.TEXT_MUTED)
            )
        else:
            self.notice.setVisible(False)

    def _copy_cmd(self) -> None:
        QGuiApplication.clipboard().setText(self.cmd_label.text())
        self.btn_copy.setText(tr("已复制"))
        from PySide6.QtCore import QTimer

        QTimer.singleShot(1200, lambda: self.btn_copy.setText(tr("复制")))
