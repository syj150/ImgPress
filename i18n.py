"""界面文案国际化。

约定：**中文原文即 key**。中文界面下 `tr()` 直接返回原文，零开销、零偏差；
其他语言在 `_EN` 表里按中文原文查表。新增文案时写 `tr("中文")` 即可，
需要英文时再往表里补一条，缺失会回退成中文（测试时一眼能看出来）。

带变量的文案用 `{}` 占位：`tr("完成 {done} · 失败 {failed}", done=2, failed=0)`。
表示数量的文案，英文表里可写成二元组 `("{n} file", "{n} files")`，按 `n` 自动选单复数。
"""

from __future__ import annotations

import os
from pathlib import Path

# 语言代码 -> 显示名（显示名本身不翻译）
LANGUAGES: dict[str, str] = {
    "zh_CN": "简体中文",
    "en": "English",
}

AUTO = "auto"

_lang = "zh_CN"

# 英文表：key 为界面上的中文原文
_EN: dict[str, str | tuple[str, str]] = {
    # ---------- 通用 ----------
    "图片": "Images",
    "所有文件": "All files",
    "复制": "Copy",
    "已复制": "Copied",
    "默认": "Default",
    "未找到": "Not found",
    "无法执行": "Cannot run",
    "未知": "Unknown",
    "内置": "Bundled",
    "取消": "Cancel",
    "保存": "Save",
    "关闭": "Close",
    "浏览…": "Browse…",
    "默认值": "default",

    # ---------- 主窗口 ----------
    "ImgPress 图片压缩器": "ImgPress Image Compressor",
    "本地图片压缩 · libjxl 0.13.0 · libavif 1.4.2 / libaom 3.14.1 · libwebp 1.6.0":
        "Local image compression · libjxl 0.13.0 · libavif 1.4.2 / libaom 3.14.1 · libwebp 1.6.0",
    "添加文件": "Add files",
    "添加文件夹": "Add folder",
    "设置": "Settings",
    "开始编码": "Start",
    "日志": "Log",
    "隐藏日志": "Hide log",
    "打开输出目录": "Open output folder",
    "就绪 · 把图片拖入工作区，或点击「添加文件」": 'Ready · drop images into the workspace, or click "Add files"',
    "就绪 · {engine} · {count} 个文件 · {size}":
        ("Ready · {engine} · {count} file · {size}", "Ready · {engine} · {count} files · {size}"),
    "正在编码 · {name}": "Encoding · {name}",
    "正在取消…": "Cancelling…",
    "缺少 {tools} —— 请在「设置 → 工具链目录」指定正确目录":
        "{tools} missing — set the correct folder in Settings → Toolchain",
    "工作区为空，先添加图片": "Workspace is empty — add images first",
    "选择一个或多个图片": "Select one or more images",
    "选择文件夹（含子目录）": "Select a folder (including subfolders)",
    "正在编码": "Encoding in progress",
    "编码尚未完成，确定要退出吗？未完成的文件不会保存。":
        "Encoding is not finished. Quit anyway? Unfinished files will not be saved.",
    "工具链不完整": "Incomplete toolchain",
    "缺少 {tools}，请在「设置」里指定工具目录。":
        "{tools} missing. Set the toolchain folder in Settings.",
    "参数有误": "Invalid parameters",
    "加入工作区：{count} 个文件":
        ("Added {count} file to the workspace", "Added {count} files to the workspace"),
    "加入工作区：{count} 个文件，忽略 {ignored} 个不支持的文件":
        ("Added {count} file, ignored {ignored} unsupported files",
         "Added {count} files, ignored {ignored} unsupported files"),
    "没有可处理的图片（忽略 {ignored} 个文件）":
        "No processable images found ({ignored} files ignored)",
    "编码器切换为 {codec}": "Encoder switched to {codec}",
    "表格里是上一轮的结果，点「开始编码」后才会刷新":
        "The table still shows the previous run — press Start to refresh it.",
    "工具链更新：{path}": "Toolchain updated: {path}",
    "工具链：{path}": "Toolchain: {path}",
    "开始编码 · {codec} · {count} 个文件": "Encoding · {codec} · {count} files",
    "完成 {done} · 失败 {failed} · 跳过 {skipped} · 原 {src} → 输出 {out} · 节省 {saved} · 用时 {time}":
        "Done {done} · Failed {failed} · Skipped {skipped} · {src} → {out} · saved {saved} · {time}",
    "完成 {done}": "Done {done}",
    "失败 {failed}": "Failed {failed}",
    "跳过 {skipped}": "Skipped {skipped}",
    "{src} → {out}（−{percent}%）": "{src} → {out} (−{percent}%)",
    "用时 {time}": "{time}",
    "S2 {value}": "S2 {value}",
    "「{name}」已存在（按设置跳过）": '"{name}" already exists (skipped by setting)',
    "正在编码 · {done}/{total}": "Encoding · {done}/{total}",

    # ---------- 工作区表格 ----------
    "工作区": "Workspace",
    "文件": "File",
    "状态": "Status",
    "尺寸": "Size",
    "原始": "Original",
    "输出": "Output",
    "比例": "Ratio",
    "耗时": "Time",
    "移除选中": "Remove",
    "清空": "Clear",
    "0 个文件": "No files",
    "{n} 个文件 · {size}": ("{n} file · {size}", "{n} files · {size}"),
    "把图片拖到这里": "Drop images here",
    "也可以右键图片选择「添加到 ImgPress 工作区」，或点击右上角「添加文件」":
        'You can also right-click images and choose "Add to ImgPress workspace", or click "Add files".',
    "预览对比": "Compare preview",
    "打开源文件": "Open source file",
    "打开所在文件夹": "Show in folder",
    "打开输出文件": "Open output file",
    "复制文件路径": "Copy file path",
    "从工作区移除（{count} 项）": "Remove from workspace ({count})",
    "待处理": "Pending",
    "编码中": "Encoding",
    "完成": "Done",
    "失败": "Failed",
    "跳过": "Skipped",
    "已取消": "Canceled",
    "源文件：{path}": "Source: {path}",
    "输出：{path}": "Output: {path}",
    "说明：{text}": "Note: {text}",

    # ---------- 参数面板 ----------
    "编码参数": "Encoding parameters",
    "保留 EXIF / XMP": "Keep EXIF / XMP",
    "计算 SSIMULACRA2": "Compute SSIMULACRA2",
    "额外参数": "Extra args",
    "留空不传，例如 --gaborish=0": "Empty = no extra args, e.g. --gaborish=0",
    "将执行的命令": "Command to run",
    "质量 q": "Quality q",
    "位深": "Bit depth",
    "色度抽样": "Chroma subsampling",
    "优化级别": "Optimize level",
    "元数据清理": "Metadata strip",
    "强制模块化": "Force modular",
    "JPEG 无损重打包（-j 1）": "Lossless JPEG repack (-j 1)",
    "渐进式（-p）": "Progressive (-p)",
    "无损（-l）": "Lossless (-l)",
    "无损（-lossless -z 9 -exact）": "Lossless (-lossless -z 9 -exact)",
    "Zopfli 重压（-z）": "Zopfli (-z)",
    "oxipng 只处理 PNG 输入；其它格式会跳过。整个过程无画质损失。":
        "oxipng only accepts PNG input; other formats are skipped. No quality loss.",
    "留空跟随主质量": "follows quality",
    "跟随主质量": "follow q",
    "JPEG XL": "JPEG XL",
    "AVIF": "AVIF",
    "WebP": "WebP",
    "PNG 无损": "PNG lossless",
    "等 {count} 条提示": "and {count} more hints",

    # ---------- 参数提示（参数手册要点） ----------
    "Butteraugli 距离（JND），描述目标失真程度而非压缩率。\n"
    "0 = 数学无损（强制模块化）；0.5 近无损（S2 86–92）；1.0 官方视觉无损（S2 84–90）；\n"
    "2.0 良好网页质量；3.0 中等；>4 明显失真。漫画网点这类高频内容 -d 1.0 实测只有 84 左右。":
        "Butteraugli distance (JND): the target distortion, not the compression ratio.\n"
        "0 = mathematically lossless (forces modular); 0.5 near-lossless (S2 86–92); 1.0 visually lossless (S2 84–90);\n"
        "2.0 good web quality; 3.0 medium; >4 clearly degraded. High-frequency content such as manga screentone measured only ~84 at -d 1.0.",
    "编码搜索强度 1–10。不改变质量目标，只决定为达到目标愿意花多少计算。\n"
    "同 -d 下 e7→e10 通常再小 3%–8%，画质基本不变，时间超线性增长。批量筛 7，终稿 9–10。":
        "Encoder search effort, 1–10. Does not change the quality target, only how much compute is spent reaching it.\n"
        "At the same -d, e7→e10 typically saves another 3%–8% at unchanged quality, with superlinear time. Use 7 for triage, 9–10 for finals.",
    "强制模块化模式（预测器 + 调色板 + squeeze）。平涂、UI、线稿有损下可能比 VarDCT 小 20% 以上；\n"
    "照片通常更差，且没有 DCT 的平滑过渡，渐变处容易出现色带。":
        "Force modular mode (predictor + palette + squeeze). On flat art, UI and line art it can be >20% smaller than VarDCT in lossy mode;\n"
        "on photos it is usually worse, and without DCT smoothing, gradients tend to band.",
    "对 JPEG 输入启用 -j 1，把原始 JPEG 码流原样装进 JXL 容器（jbrd），不重新编码像素。\n"
    "体积约降 20%、画质零损失、可逐字节还原原 JPEG。要求 distance = 0；产物需 djxl 才能还原。":
        "Enable -j 1 for JPEG input: the original JPEG bitstream is stored verbatim inside the JXL container (jbrd), no re-encoding.\n"
        "About 20% smaller, zero quality loss, byte-exact JPEG recovery. Requires distance = 0; only djxl can restore it.",
    "渐进/响应式解码，体积 +1%–3%，画质不变。网络首屏更快，本地文件无意义。":
        "Progressive / responsive decoding, +1%–3% size, no quality change. Faster first paint over the network, pointless for local files.",
    "0–100，内部映射到 AV1 量化器，不是线性百分比。高段边际收益急剧下降：\n"
    "q90→q92 体积 +29%、S2 只 +0.7。拐点在 88–90。":
        "0–100, mapped internally to the AV1 quantizer — not a linear percentage. Returns collapse at the top end:\n"
        "q90→q92 costs +29% size for +0.7 S2. The knee is at 88–90.",
    "RD 优化时偏向哪种失真度量。\n"
    "iq = 感知向，同 q 下明显更小（实测省 11%–27%），纹理略平滑；\n"
    "ssim = 保局部对比与结构，体积更大；psnr = 像素误差，感知上通常不是最优。":
        "Which distortion metric the RD optimization favors.\n"
        "iq = perceptual, clearly smaller at the same q (measured 11%–27% savings), slightly smoother textures;\n"
        "ssim = preserves local contrast and structure, larger files; psnr = pixel error, usually not perceptually optimal.",
    "输出位深。影响不是单调的，交叉点在 q ≈ 70：\n"
    "q ≤ 70 用 10bit 反而更小（−0.4% ~ −1.6%）且色度台阶细 4 倍；\n"
    "q ≥ 80 用 8bit（10bit 体积 +3%–15%）。auto 按 q 自动选择。":
        "Output bit depth. The effect is not monotonic; it crosses over around q ≈ 70:\n"
        "at q ≤ 70, 10-bit is actually smaller (−0.4% to −1.6%) with 4× finer chroma steps;\n"
        "at q ≥ 80 use 8-bit (10-bit costs +3%–15%). auto picks by q.",
    "编码速度档 0–10，越小越慢、搜索越充分。6→4 约省 2%，4→2 再约 2%，\n"
    "低于 2 收益递减且极慢。它改变 RD 决策质量，因此同 q 下体积与画质都会轻微变化。":
        "Encoder speed 0–10: lower is slower and more thorough. 6→4 saves about 2%, 4→2 another 2%,\n"
        "below 2 returns diminish and it gets very slow. It changes RD decision quality, so both size and quality shift slightly at the same q.",
    "色度抽样。444 完整色度，彩色线稿必须用；\n"
    "420 省约 6.7% 但 S2 掉约 6，红线/蓝线交界会渗色；400 灰度可省约 25%；422 少用。":
        "Chroma subsampling. 444 keeps full chroma and is mandatory for colored line art;\n"
        "420 saves ~6.7% but drops ~6 S2 and bleeds at red/blue edges; 400 (grayscale) saves ~25%; 422 is rarely useful.",
    "alpha 通道单独质量。过低会出现锯齿/半透明脏边，过高显著增体积。留空跟随主质量。":
        "Separate quality for the alpha channel. Too low gives jagged or dirty semi-transparent edges; too high inflates size. Empty = follow the main quality.",
    "有损质量 0–100。100 仍然是有损，只是最高档。\n"
    "q95→q92 体积 −21%、S2 −0.7；q90 以下掉得更快。WebP 的 S2 上限普遍 82–85，是格式瓶颈。":
        "Lossy quality 0–100. 100 is still lossy, just the top step.\n"
        "q95→q92 is −21% size for −0.7 S2; below q90 quality falls faster. WebP tops out around S2 82–85 — a format limit.",
    "一组内部参数预设（滤波强度、SNS、预处理），±1%–3% 体积。\n"
    "drawing 适合线稿/漫画，photo 自然图像，icon 小图标，text 文字截图。":
        "A bundle of internal presets (filter strength, SNS, preprocessing), ±1%–3% size.\n"
        "drawing for line art/manga, photo for natural images, icon for small icons, text for screenshots of text.",
    "压缩搜索方法 0–6，越大越慢越充分。6→4 省时间但体积 +2%–5%。通常直接用 6。":
        "Compression search method 0–6: higher is slower and more thorough. 6→4 saves time but costs +2%–5% size. Usually just use 6.",
    "使用更锐利的 RGB→YUV420 转换，仅对 4:2:0 有损有效，可减轻彩色边缘发虚。":
        "Sharper RGB→YUV420 conversion. Only affects lossy 4:2:0, and reduces color bleeding at edges.",
    "空间噪声整形 0–100。数值高会保留更多纹理/噪点；插画 80 左右可保住颗粒感，平涂可低一些。":
        "Spatial noise shaping 0–100. Higher keeps more texture/grain; ~80 preserves grain in illustrations, lower for flat art.",
    "环路滤波强度 0–100。高值平滑块边界，低值保锐度但块效应更明显。线稿可试 0–20，照片 20–40。":
        "Loop filter strength 0–100. Higher smooths block edges; lower keeps sharpness but shows blocking. Try 0–20 for line art, 20–40 for photos.",
    "量化分段数（1–4）与分析遍数（1–10）。提高会略小略慢，实测整体约 1% 收益，投入产出比很低。":
        "Quantizer segments (1–4) and analysis passes (1–10). Raising them is slightly smaller and slower; measured about 1% total gain — poor return.",
    "优化级别 0–6 或 max，尝试更多滤波/压缩组合，纯无损。−o 4 → max 通常只多 0.2 个百分点却慢 5 倍。":
        "Optimization level 0–6 or max: tries more filter/compression combinations, fully lossless. -o 4 → max usually gains 0.2 points for 5× the time.",
    "元数据清理。safe 只删不影响渲染的块并保留 ICC/sRGB/pHYs；\n"
    "all 删所有非关键块（会连 ICC 一起删，广色域图片会偏色）；none 全保留。":
        "Metadata stripping. safe removes only chunks that do not affect rendering and keeps ICC/sRGB/pHYs;\n"
        "all removes every non-critical chunk (including ICC — wide-gamut images will shift); none keeps everything.",
    "用 Zopfli 重压 deflate，比 zlib 小 3%–8%，慢 10–100 倍，仍然无损。":
        "Recompress deflate with Zopfli: 3%–8% smaller than zlib, 10–100× slower, still lossless.",
    "默认只保留 ICC，剥离 EXIF/XMP：\n"
    "AVIF  --ignore-exif --ignore-xmp\nJXL   -x strip=exif -x strip=xmp\n"
    "WebP  -metadata icc\nPNG   --strip safe\n实测对体积影响通常小于 0.5%。":
        "By default only ICC is kept; EXIF/XMP are stripped:\n"
        "AVIF  --ignore-exif --ignore-xmp\nJXL   -x strip=exif -x strip=xmp\n"
        "WebP  -metadata icc\nPNG   --strip safe\nMeasured size impact is usually under 0.5%.",
    "SSIMULACRA2：100 = 与原始不可区分，90 = 1:1 视觉无损，85 = 闪烁测试不可辨，\n"
    "80 = 高质量，70 = 中等。它对平滑有偏好，只适合筛查，最终仍要看 200% 裁切。\n"
    "开启后每张图会多一次解码 + 评分，批量处理会明显变慢。":
        "SSIMULACRA2: 100 = indistinguishable, 90 = visually lossless at 1:1, 85 = invisible in flicker tests,\n"
        "80 = high quality, 70 = medium. It favors smoothness, so treat it as a filter; inspect 200% crops for the final call.\n"
        "Enabling it adds a decode plus a scoring pass per image, noticeably slower in batch.",
    "原样透传给编码器，用于脚本未单独列出的高级项。示例：\n"
    "JXL   --gaborish=0 --epf=1 --faster_decoding=2\n"
    "AVIF  -a sharpness=4 -a aq-mode=1\n"
    "参数含义见参数手册第 2、3 节的「未暴露高级项」。":
        "Passed through to the encoder verbatim, for advanced options not exposed above. Examples:\n"
        "JXL   --gaborish=0 --epf=1 --faster_decoding=2\n"
        "AVIF  -a sharpness=4 -a aq-mode=1\n"
        "See sections 2 and 3 of the parameter manual for the full list.",

    # ---------- 参数校验提示 ----------
    "JPEG 无损重打包要求 distance = 0，已按 0 执行。":
        "Lossless JPEG repack requires distance = 0; running with 0.",
    "JPEG 无损重打包无法剥离元数据，保留元数据开关在此模式下不生效。":
        "Lossless JPEG repack cannot strip metadata; the metadata switch has no effect here.",
    "模块化有损模式易在渐变处出现色带，务必放大检查。":
        "Modular lossy mode tends to band in gradients — zoom in to check.",
    "distance = 0 时 cjxl 自动切到模块化无损。":
        "At distance = 0, cjxl switches to modular lossless automatically.",
    "AVIF 无损对照片通常比原文件更大，仅归档场景值得。":
        "Lossless AVIF is usually larger than the source photo; only worth it for archiving.",
    "AVIF 无损对照片通常比原文件更大，只有归档/法证场景值得。":
        "Lossless AVIF is usually larger than the source photo; only worth it for archiving or forensics.",
    "VP8L 无损。平涂插画上常比 PNG 小，但通常大于 JXL 无损。":
        "VP8L lossless. Often smaller than PNG on flat artwork, but usually larger than lossless JXL.",
    "切换后需要重启程序才会生效。": "Takes effect after restarting the app.",
    "AVIF q ≥ 92 后边际收益急剧下降（q90→92 体积 +29%，S2 仅 +0.7）。":
        "AVIF returns collapse above q 92 (q90→92: +29% size, +0.7 S2).",
    "yuv {yuv} 会明显损失彩色边缘，彩色线稿不建议。":
        "yuv {yuv} visibly damages colored edges — not advised for colored line art.",
    "无损模式下 qalpha 不生效。": "qalpha has no effect in lossless mode.",
    "WebP q = 100 仍是有损，只是最高档。":
        "WebP q = 100 is still lossy — just the top step.",
    "WebP 无损 + 保留元数据时，EXIF/XMP 仍不会写入。":
        "With lossless WebP, EXIF/XMP are not written even when metadata is kept.",
    "--strip all 会连 ICC 一起删除，广色域图片会出现颜色偏移。":
        "--strip all also removes ICC; wide-gamut images will shift color.",

    # ---------- 编码器日志 ----------
    "[编码] {name} → {dst}": "[encode] {name} → {dst}",
    "[完成] {name}  {src} → {out}  {percent}%  {time}s":
        "[done] {name}  {src} → {out}  {percent}%  {time}s",
    "[失败] {name} — {message}": "[failed] {name} — {message}",
    "[跳过] {name} — {message}": "[skipped] {name} — {message}",
    "S2 {score}": "S2 {score}",
    "S2 跳过：{reason}": "S2 skipped: {reason}",
    "退出码 {code}": "exit code {code}",
    "输入格式 {ext} 需先转 PNG（临时文件）":
        "Input format {ext} is converted to a temporary PNG first",
    "oxipng 仅支持 PNG 输入": "oxipng only accepts PNG input",
    "输出已存在（按设置跳过）": "Output already exists (skipped by setting)",
    "已取消": "Canceled",
    "超时": "timed out",
    "{time}s": "{time}s",

    # ---------- 设置 ----------
    "工具链目录": "Toolchain folder",
    "存放 cjxl / avifenc / cwebp / oxipng 的目录，程序会递归查找这些 exe。默认使用程序目录下的 tools\\bin。":
        "Folder containing cjxl / avifenc / cwebp / oxipng. The app searches it recursively. Defaults to tools\\bin next to the executable.",
    "恢复默认": "Reset",
    "重新检测": "Re-scan",
    "输出": "Output",
    "输出位置": "Location",
    "与源文件同目录（原名 + 新扩展名）": "Same folder as the source (original name + new extension)",
    "重名处理": "On collision",
    "覆盖同名文件": "Overwrite",
    "跳过已存在的输出": "Skip existing",
    "自动加序号（-1、-2…）": "Auto-number (-1, -2…)",
    "原文件始终保留；输出文件名与源文件同名时按此规则处理。":
        "The source file is always kept; this rule applies when the output name already exists.",
    "右键菜单": "Context menu",
    "注册右键菜单": "Register context menu",
    "移除": "Remove",
    "注册写入 HKEY_CURRENT_USER，不需要管理员权限；覆盖 jpg/png/webp/bmp/tif/gif/avif/jxl 等扩展名，"
    "支持一次选中多个文件批量加入工作区。Windows 11 会把此类菜单收纳到「显示更多选项」中。":
        "Registration writes to HKEY_CURRENT_USER and needs no admin rights. Covers jpg/png/webp/bmp/tif/gif/avif/jxl and supports multi-select. "
        "Windows 11 tucks these entries under \"Show more options\".",
    "关于": "About",
    "以 MIT 许可证开源，欢迎 issue 与 PR。":
        "Open source under the MIT License — issues and pull requests are welcome.",
    "把图片加入工作区（Ctrl+O）": "Add images to the workspace (Ctrl+O)",
    "递归添加文件夹里的图片（Ctrl+Shift+O）": "Add every image inside a folder, recursively (Ctrl+Shift+O)",
    "界面语言、工具链目录、右键菜单": "Language, toolchain folder, context menu",
    "「?」里的 S2 与体积为单张样本实测值，不同图片差异很大，仅作方向参考。":
        "S2 and size figures in the \"?\" notes come from one test image; results vary per image — use them as a rough guide.",
    "ImgPress {version} · 本地离线运行，不上传任何图片":
        "ImgPress {version} · fully offline, no image ever leaves your machine",
    "JPEG XL 编码": "JPEG XL encode",
    "JXL 解码": "JXL decode",
    "AVIF 编码": "AVIF encode",
    "AVIF 解码": "AVIF decode",
    "WebP 编码": "WebP encode",
    "WebP 解码": "WebP decode",
    "PNG 优化": "PNG optimize",
    "质量评分": "Quality metric",
    "工具目录无效：四个编码器都不可用，无法开始压缩。":
        "Invalid toolchain folder: no encoder is available, compression cannot start.",
    "界面语言": "Language",
    "跟随系统": "Follow system",
    "语言": "Language",
    "语言已切换，重启后生效。现在重启吗？":
        "Language changed. It takes effect after a restart. Restart now?",
    "未指定，使用程序目录下的 tools\\bin": "Not set — using tools\\bin next to the executable",
    "已注册 · {path}": "Registered · {path}",
    "部分注册（有扩展名缺失）": "Partially registered (some extensions missing)",
    "未注册": "Not registered",
    "仅支持 Windows": "Windows only",
    "注册失败": "Registration failed",
    "未能写入注册表，请检查权限或安全软件拦截。":
        "Could not write to the registry. Check permissions or security software.",

    # ---------- 预览 ----------
    "预览对比 — {name}": "Compare — {name}",
    "原图": "Original",
    "结果": "Result",
    "缩放": "Zoom",
    "适应窗口": "Fit",
    "尚未生成结果": "No result yet",
    "无法解码：{reason}": "Decode failed: {reason}",

    # ---------- 右键菜单项 ----------
    "添加到 ImgPress 工作区": "Add to ImgPress workspace",

    # ---------- 命令行 ----------
    "ImgPress 图片压缩器": "ImgPress image compressor",
    "加入工作区的文件": "files to add to the workspace",
    "注册右键菜单": "register the context menu",
    "移除右键菜单": "remove the context menu",
    "直接拖到 exe 上的文件": "files dropped onto the executable",
}


def available_languages() -> list[tuple[str, str]]:
    """[(code, 显示名), ...]，首项为「跟随系统」。"""
    return [(AUTO, "跟随系统（{name}）")] + list(LANGUAGES.items())


def detect_system_language() -> str:
    """系统界面语言 → 支持的语言代码。

    注意用 uiLanguages() 而不是 name()：后者是区域格式（例如 zh 系统可能返回 en_US），
    前者才是界面语言的有序列表。
    """
    tags: list[str] = []
    try:
        from PySide6.QtCore import QLocale

        tags = list(QLocale.system().uiLanguages())
    except Exception:  # noqa: BLE001
        pass
    tags.append(os.environ.get("LANG", ""))

    for tag in tags:
        low = str(tag).lower()
        if low.startswith("zh"):
            return "zh_CN"
        if low.startswith("en"):
            return "en"
    return "en"


def resolve(code: str | None) -> str:
    if not code or code == AUTO:
        return detect_system_language()
    return code if code in LANGUAGES else detect_system_language()


def set_language(code: str | None) -> str:
    global _lang
    _lang = resolve(code)
    return _lang


def current_language() -> str:
    return _lang


def current_language_name() -> str:
    return LANGUAGES.get(_lang, _lang)


def tr(text: str, **kwargs) -> str:
    """取当前语言的文案；中文下直接返回原文。"""
    out: str | tuple[str, str] = text
    if _lang != "zh_CN":
        out = _EN.get(text, text)

    if isinstance(out, tuple):
        n = kwargs.get("n", kwargs.get("count", 0))
        out = out[0] if n == 1 else out[1]

    if kwargs:
        try:
            return out.format(**kwargs)
        except (KeyError, IndexError):
            return out
    return out


def install_qt_translator(app) -> None:
    """加载 Qt 自带控件文案（文件对话框按钮、标准消息框等）。"""
    if _lang == "en":
        return
    try:
        from PySide6.QtCore import QLibraryInfo, QTranslator
    except Exception:  # noqa: BLE001
        return

    folder = Path(QLibraryInfo.path(QLibraryInfo.TranslationsPath))
    for name in (f"qtbase_{_lang}", "qtbase_zh_CN"):
        path = folder / f"{name}.qm"
        if not path.exists():
            continue
        translator = QTranslator(app)
        if translator.load(str(path)):
            app.installTranslator(translator)
            return
