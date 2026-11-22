"""配置持久化：%LOCALAPPDATA%/ImgPress/config.json"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from i18n import AUTO

from . import paths
from .params import RunParams


@dataclass
class Settings:
    params: RunParams = field(default_factory=RunParams)
    policy: str = "overwrite"  # overwrite | skip | suffix
    language: str = AUTO  # auto | zh_CN | en
    tools_root: str | None = None
    last_dir: str | None = None
    log_visible: bool = False
    window: dict = field(default_factory=dict)
    splitter: list[int] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "params": self.params.to_dict(),
            "policy": self.policy,
            "language": self.language,
            "tools_root": self.tools_root,
            "last_dir": self.last_dir,
            "log_visible": self.log_visible,
            "window": self.window,
            "splitter": self.splitter,
        }

    @classmethod
    def from_dict(cls, data: dict | None) -> "Settings":
        s = cls()
        if not isinstance(data, dict):
            return s
        s.params = RunParams.from_dict(data.get("params"))
        if data.get("policy") in ("overwrite", "skip", "suffix"):
            s.policy = data["policy"]
        if data.get("language"):
            s.language = str(data["language"])
        s.tools_root = data.get("tools_root") or None
        s.last_dir = data.get("last_dir") or None
        s.log_visible = bool(data.get("log_visible", False))
        if isinstance(data.get("window"), dict):
            s.window = data["window"]
        if isinstance(data.get("splitter"), list) and len(data["splitter"]) == 2:
            try:
                s.splitter = [int(x) for x in data["splitter"]]
            except (TypeError, ValueError):
                s.splitter = []
        return s


def load() -> Settings:
    path = paths.config_path()
    try:
        with path.open("r", encoding="utf-8") as fh:
            return Settings.from_dict(json.load(fh))
    except (OSError, ValueError):
        return Settings()


def save(s: Settings) -> None:
    path = paths.config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    try:
        with tmp.open("w", encoding="utf-8") as fh:
            json.dump(s.to_dict(), fh, ensure_ascii=False, indent=2)
        tmp.replace(path)
    except OSError:
        pass
