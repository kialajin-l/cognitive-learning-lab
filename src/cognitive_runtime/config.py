"""Runtime configuration.

Credentials are read from the environment only and are never serialised into
config output, so ``doctor`` and run manifests cannot leak a token.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .model.laya import LayaSettings

DEFAULT_DIR = Path(__file__).resolve().parent / "defaults"
DEFAULT_CONFIG_PATH = DEFAULT_DIR / "config.json"
EXAMPLES_DIR = DEFAULT_DIR / "examples"


@dataclass
class RuntimeConfig:
    provider: str = "mock"
    namespace: str = "default"
    store_path: str | None = None
    sources_path: str | None = None
    abstain_threshold: float = 0.5
    max_model_calls: int = 4
    max_wall_seconds: int = 900
    model: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def load(cls, path: str | Path | None = None) -> "RuntimeConfig":
        config_path = Path(path) if path else DEFAULT_CONFIG_PATH
        payload: dict[str, Any] = {}
        if config_path.exists():
            payload = json.loads(config_path.read_text(encoding="utf-8"))
        payload = {key: value for key, value in payload.items() if key in cls.__dataclass_fields__}
        config = cls(**payload)
        env_store = os.environ.get("COGNITIVE_RUNTIME_STORE")
        if env_store:
            config.store_path = env_store
        env_sources = os.environ.get("COGNITIVE_RUNTIME_SOURCES")
        if env_sources:
            config.sources_path = env_sources
        return config

    def resolve_store_path(self, override: str | Path | None = None) -> Path:
        candidate = override or self.store_path
        if candidate is None:
            raise ValueError(
                "no store path: pass --store or set store_path in the config; "
                "the runtime will not silently pick a shared location"
            )
        return Path(candidate).expanduser().resolve()

    def resolve_sources_path(self) -> Path:
        candidate = self.sources_path or (EXAMPLES_DIR / "sources.jsonl")
        return Path(candidate).expanduser().resolve()

    def laya_settings(self) -> LayaSettings:
        settings = LayaSettings.from_config({"model": self.model})
        if self.model.get("local_dir"):
            settings.local_dir = self.model["local_dir"]
        return settings

    def safe_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        model = dict(payload.get("model") or {})
        model.pop("token", None)
        payload["model"] = model
        return payload
