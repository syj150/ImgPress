"""任务模型与后台执行器。

单个任务的生命周期：准备输入 → 构造命令 → 执行编码 → 统计体积
→（可选）解码并计算 SSIMULACRA2。整批串行执行，编码器自身已多线程。
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from i18n import tr

from . import imageops
from .encode import build_encode, output_suffix
from .params import RunParams
from .tools import Toolchain
from .util import cmdline, fmt_bytes

_NO_WINDOW = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0

# 状态用稳定标识，界面层负责翻译，避免把中文文案写进数据模型
PENDING = "pending"
RUNNING = "running"
DONE = "done"
FAILED = "failed"
SKIPPED = "skipped"
CANCELED = "canceled"

STATUS_LABEL = {
    PENDING: "待处理",
    RUNNING: "编码中",
    DONE: "完成",
    FAILED: "失败",
    SKIPPED: "跳过",
    CANCELED: "已取消",
}


@dataclass
class Job:
    src: Path
    codec: str
    dst: Path | None = None
    status: str = PENDING
    src_size: int = 0
    width: int = 0
    height: int = 0
    out_size: int | None = None
    s2: float | None = None
    elapsed: float | None = None
    message: str = ""
    command: str = ""
    converted: bool = False

    @property
    def name(self) -> str:
        return self.src.name

    @property
    def size_text(self) -> str:
        if self.width and self.height:
            return f"{self.width}×{self.height}"
        return "—"


def resolve_dst(src: Path, codec: str, policy: str, taken: set[str] | None = None) -> Path | None:
    """按重名策略决定输出路径；返回 None 表示按策略跳过。"""
    suffix = output_suffix(codec)
    base = src.with_suffix(suffix)
    if base == src:
        base = src.with_name(f"{src.stem}_compressed{suffix}")
    taken = taken or set()
    key = str(base).lower()
    if not base.exists() and key not in taken:
        return base
    if policy == "overwrite":
        return base
    if policy == "skip":
        return None
    n = 1
    while True:
        cand = base.with_name(f"{base.stem}-{n}{suffix}")
        if not cand.exists() and str(cand).lower() not in taken:
            return cand
        n += 1


class EncodeWorker(QObject):
    job_started = Signal(int)
    job_finished = Signal(int)
    progress = Signal(int, int)
    log = Signal(str)
    finished = Signal()

    def __init__(
        self,
        jobs: list[Job],
        params: RunParams,
        tools: Toolchain,
        policy: str = "overwrite",
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.jobs = jobs
        self.params = params
        self.tools = tools
        self.policy = policy
        self._cancel = False
        self._proc: subprocess.Popen | None = None
        self._tmp: Path | None = None

    # ---------- 控制 ----------
    def cancel(self) -> None:
        self._cancel = True
        proc = self._proc
        if proc and proc.poll() is None:
            try:
                proc.kill()
            except OSError:
                pass

    # ---------- 主流程 ----------
    def run(self) -> None:
        self._tmp = Path(tempfile.mkdtemp(prefix="imgpress_"))
        taken: set[str] = set()
        try:
            total = len(self.jobs)
            for idx, job in enumerate(self.jobs):
                if self._cancel:
                    job.status = CANCELED
                    job.message = tr("已取消")
                    self.job_finished.emit(idx)
                    continue
                self.job_started.emit(idx)
                try:
                    self._run_one(idx, job, taken)
                except Exception as exc:  # 单张失败不应中断整批
                    job.status = FAILED
                    job.message = str(exc)
                    self.log.emit(tr("[失败] {name} — {message}", name=job.src.name, message=exc))
                self.job_finished.emit(idx)
                self.progress.emit(idx + 1, total)
        finally:
            if self._tmp:
                shutil.rmtree(self._tmp, ignore_errors=True)
                self._tmp = None
            self.finished.emit()

    def _run_one(self, idx: int, job: Job, taken: set[str]) -> None:
        t0 = time.perf_counter()
        codec = job.codec

        if codec == "png" and job.src.suffix.lower() != ".png":
            job.status = SKIPPED
            job.message = tr("oxipng 仅支持 PNG 输入")
            self.log.emit(tr("[跳过] {name} — {message}", name=job.src.name, message=job.message))
            return

        dst = resolve_dst(job.src, codec, self.policy, taken)
        if dst is None:
            job.status = SKIPPED
            job.message = tr("输出已存在（按设置跳过）")
            self.log.emit(tr("[跳过] {name} — {message}", name=job.src.name, message=job.message))
            return
        job.dst = dst
        taken.add(str(dst).lower())

        enc_in = self._prepare_input(idx, job)
        cmd = build_encode(codec, self.params, self.tools, enc_in, dst)
        job.command = cmdline(cmd)
        dst.parent.mkdir(parents=True, exist_ok=True)

        self.log.emit(tr("[编码] {name} → {dst}", name=job.src.name, dst=dst.name))
        self.log.emit("       " + job.command)

        code, msg, elapsed = self._exec(cmd)
        job.elapsed = elapsed
        if self._cancel:
            job.status = CANCELED
            job.message = tr("已取消")
            return
        if code != 0 or not dst.exists():
            tail = msg.strip().splitlines()
            job.status = FAILED
            job.message = tail[-1] if tail else tr("退出码 {code}", code=code)
            self.log.emit(tr("[失败] {name} — {message}", name=job.src.name, message=job.message))
            return

        job.out_size = dst.stat().st_size
        job.status = DONE
        if not job.width or not job.height:
            info = imageops.probe_size(dst)
            if not info:
                try:
                    info = imageops.probe_size(imageops.cached_preview(dst, codec, self.tools))
                except Exception:  # noqa: BLE001
                    info = None
            if info:
                job.width, job.height = info
        ratio = job.out_size / job.src_size * 100 if job.src_size else 0
        self.log.emit(
            tr(
                "[完成] {name}  {src} → {out}  {percent}%  {time}s",
                name=job.src.name,
                src=fmt_bytes(job.src_size),
                out=fmt_bytes(job.out_size),
                percent=f"{ratio:.1f}",
                time=f"{elapsed:.1f}",
            )
        )
        taken.add(str(dst).lower())

        if self.params.calc_s2:
            job.s2 = self._compute_s2(job, enc_in)
            if job.s2 is not None:
                self.log.emit("       " + tr("S2 {score}", score=f"{job.s2:.2f}"))

    # ---------- 子步骤 ----------
    def _prepare_input(self, idx: int, job: Job) -> Path:
        """编码器吃不下的格式先转 PNG；JXL/AVIF 走 CLI 解码。"""
        if not imageops.needs_conversion(job.src, job.codec):
            return job.src
        assert self._tmp is not None
        tmp_in = self._tmp / f"in_{idx}.png"
        try:
            imageops.convert_to_png(job.src, tmp_in)
        except imageops.ImageError:
            hint = job.src.suffix.lower().lstrip(".")
            if hint not in ("jxl", "avif"):
                raise
            imageops.decode_with_cli(hint, self.tools, job.src, tmp_in)
        job.converted = True
        self.log.emit("       " + tr("输入格式 {ext} 需先转 PNG（临时文件）", ext=job.src.suffix))
        return tmp_in

    def _compute_s2(self, job: Job, enc_in: Path) -> float | None:
        exe = self.tools.get("ssimulacra2")
        if not exe or not job.dst or self._tmp is None:
            return None
        try:
            ref = self._tmp / f"ref_{job.src.stem[:16]}.png"
            imageops.to_reference(job.src, ref, self.tools)
            dec = imageops.cached_preview(job.dst, job.codec, self.tools)
        except Exception as exc:
            self.log.emit("       " + tr("S2 跳过：{reason}", reason=exc))
            return None
        code, msg, _ = self._exec([str(exe), str(ref), str(dec)], timeout=900)
        if code != 0:
            return None
        nums = re.findall(r"-?\d+(?:\.\d+)?", msg)
        return float(nums[-1]) if nums else None

    def _exec(self, cmd: list[str], timeout: int | None = None) -> tuple[int, str, float]:
        t0 = time.perf_counter()
        try:
            self._proc = subprocess.Popen(
                [str(c) for c in cmd],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=_NO_WINDOW,
            )
        except OSError as exc:
            return 1, str(exc), time.perf_counter() - t0
        try:
            out, _ = self._proc.communicate(timeout=timeout)
            code = self._proc.returncode
        except subprocess.TimeoutExpired:
            self._proc.kill()
            out, _ = self._proc.communicate()
            code = 1
            out = (out or "") + "\n" + tr("超时")
        finally:
            self._proc = None
        return code, out or "", time.perf_counter() - t0


def summarize(jobs: list[Job]) -> dict[str, float | int]:
    done = [j for j in jobs if j.status == DONE]
    failed = [j for j in jobs if j.status == FAILED]
    skipped = [j for j in jobs if j.status == SKIPPED]
    canceled = [j for j in jobs if j.status == CANCELED]
    src_total = sum(j.src_size for j in done)
    out_total = sum(j.out_size or 0 for j in done)
    elapsed = sum(j.elapsed or 0 for j in done)
    return {
        "done": len(done),
        "failed": len(failed),
        "skipped": len(skipped),
        "canceled": len(canceled),
        "src_bytes": src_total,
        "out_bytes": out_total,
        "saved": src_total - out_total,
        "elapsed": elapsed,
        "s2_avg": (
            sum(j.s2 for j in done if j.s2 is not None) / len([j for j in done if j.s2 is not None])
            if any(j.s2 is not None for j in done)
            else -1
        ),
    }
