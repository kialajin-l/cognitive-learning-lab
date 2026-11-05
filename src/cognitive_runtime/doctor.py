"""Environment diagnostics: what is present, what is missing, what would be trusted."""

from __future__ import annotations

import importlib.util
import platform
import sys
from pathlib import Path
from typing import Any

from . import __version__
from .config import RuntimeConfig
from .memory.store import MemoryStore
from .model.laya import LayaProvider, ModelIntegrityError, ModelUnavailable
from .sources import SourceRegistry


def diagnose(config: RuntimeConfig, *, store_path: str | Path | None = None) -> dict[str, Any]:
    report: dict[str, Any] = {
        "package_version": __version__,
        "python": {"version": platform.python_version(), "executable": sys.executable, "meets_minimum": sys.version_info >= (3, 10)},
        "provider": config.provider,
        "dependencies": {},
        "model": {},
        "store": {},
        "sources": {},
        "blockers": [],
    }

    for module in ("laya", "huggingface_hub", "jsonschema"):
        report["dependencies"][module] = {"installed": importlib.util.find_spec(module) is not None}

    if config.provider == "laya":
        provider = LayaProvider(config.laya_settings())
        try:
            provider.verify_integrity()
            report["model"] = provider.identity()
        except (ModelIntegrityError, ModelUnavailable) as exc:
            report["model"] = {**provider.identity(), "status": "unavailable", "detail": str(exc)[:400]}
            report["blockers"].append("model_unavailable_or_unverified")
    else:
        report["model"] = {"status": "not_required", "note": "provider=mock; mock output is never model evidence"}

    try:
        resolved = config.resolve_store_path(store_path)
    except ValueError as exc:
        report["store"] = {"status": "unconfigured", "detail": str(exc)}
        report["blockers"].append("store_unconfigured")
        return report

    if resolved.exists():
        store = MemoryStore(resolved, namespace=config.namespace)
        report["store"] = {"status": "present", **store.stats()}
    else:
        report["store"] = {"status": "absent", "path": str(resolved), "writable_parent": resolved.parent.exists()}

    sources = config.resolve_sources_path()
    registry = SourceRegistry(sources)
    report["sources"] = {"path": str(sources), "exists": sources.exists(), "refs": len(registry.refs())}
    if not sources.exists():
        report["blockers"].append("source_registry_missing")
    return report
