"""Provider selection. ``mock`` is never silently substituted for ``laya``."""

from __future__ import annotations

from .config import RuntimeConfig
from .model.laya import LayaProvider
from .model.mock import MockProvider


def build_provider(config: RuntimeConfig):
    if config.provider == "mock":
        return MockProvider()
    if config.provider == "laya":
        return LayaProvider(config.laya_settings())
    raise ValueError(f"unknown provider {config.provider!r}; expected 'mock' or 'laya'")
