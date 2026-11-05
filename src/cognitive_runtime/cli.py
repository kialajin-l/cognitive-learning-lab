"""Command line entry point.

Exit codes: 0 = ran and produced a typed result (answered or abstained are both
normal); 2 = bad input, unconfigured store or forbidden fields; 3 = runtime
failure the caller should treat as not-run.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .config import RuntimeConfig
from .doctor import diagnose
from .memory.store import MemoryStore
from .pipeline import ProviderUnavailable, RequestError, run_request
from .sanitize import ForbiddenInput
from .sources import SourceRegistry, verify_record

EXIT_OK = 0
EXIT_INPUT = 2
EXIT_RUNTIME = 3


def _emit(payload: Any) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cognitive-runtime", description="Frozen model + external memory + typed judgment runtime.")
    parser.add_argument("--config", default=None, help="path to a JSON config file")
    sub = parser.add_subparsers(dest="command", required=True)

    doctor = sub.add_parser("doctor", help="report environment, model and store readiness")
    doctor.add_argument("--store", default=None)

    infer = sub.add_parser("infer", help="run one request through the full chain")
    infer.add_argument("--input", required=True, help="JSON request file")
    infer.add_argument("--store", default=None)
    infer.add_argument("--namespace", default=None)
    infer.add_argument("--provider", default=None, choices=["mock", "laya"])

    memory = sub.add_parser("memory", help="inspect or maintain a store")
    memory_sub = memory.add_subparsers(dest="memory_command", required=True)

    inspect = memory_sub.add_parser("inspect", help="list records with trust state")
    inspect.add_argument("--store", required=True)
    inspect.add_argument("--entity", default=None)

    seed = memory_sub.add_parser("seed", help="append candidate records from a JSONL file")
    seed.add_argument("--store", required=True)
    seed.add_argument("--input", required=True)

    verify = memory_sub.add_parser("verify", help="verify and promote candidates")
    verify.add_argument("--store", required=True)

    show = memory_sub.add_parser("show", help="print store statistics and integrity")
    show.add_argument("--store", required=True)

    for command in (inspect, seed, verify, show):
        command.add_argument("--namespace", default=None)

    clear = memory_sub.add_parser("clear", help="delete rows from an explicitly named store")
    clear.add_argument("--store", required=True)
    clear.add_argument("--namespace", default=None)
    clear.add_argument("--yes", action="store_true", help="required confirmation of the exact store path")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = RuntimeConfig.load(args.config)
    if getattr(args, "provider", None):
        config.provider = args.provider
    if getattr(args, "namespace", None):
        config.namespace = args.namespace

    try:
        if args.command == "doctor":
            _emit(diagnose(config, store_path=args.store))
            return EXIT_OK

        if args.command == "infer":
            if args.store:
                config.store_path = args.store
            request = json.loads(Path(args.input).expanduser().read_text(encoding="utf-8"))
            result = run_request(request, config)
            _emit(result)
            return EXIT_OK

        if args.command == "memory":
            return _memory(args, config)
    except ProviderUnavailable as exc:
        _emit(
            {
                "status": "provider_error",
                "run_id": exc.run_id,
                "detail": str(exc),
                "raw_proposal": exc.proposal.as_dict(),
                "note": "no usable proposal, so this run is not-run: the chain did not abstain, it did not execute",
            }
        )
        return EXIT_RUNTIME
    except (ForbiddenInput, RequestError, ValueError, FileNotFoundError) as exc:
        _emit({"status": "input_error", "detail": str(exc)})
        return EXIT_INPUT
    except Exception as exc:  # surfaced as not-run rather than pretending a result
        _emit({"status": "runtime_error", "detail": f"{type(exc).__name__}: {exc}"})
        return EXIT_RUNTIME
    return EXIT_INPUT


def _memory(args: argparse.Namespace, config: RuntimeConfig) -> int:
    store = MemoryStore(config.resolve_store_path(args.store), namespace=config.namespace)

    if args.memory_command == "inspect":
        records = store.find(args.entity) if args.entity else [store.get(mid) for mid in store.ids()]
        _emit({"store": str(store.path), "namespace": config.namespace, "records": [record.as_dict() for record in records if record]})
        return EXIT_OK

    if args.memory_command == "show":
        _emit({"stats": store.stats(), "integrity": store.integrity_check()})
        return EXIT_OK

    if args.memory_command == "seed":
        path = Path(args.input).expanduser()
        written = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            payload = json.loads(line)
            record = store.append(
                entity=payload["entity"],
                content=payload["content"],
                source=payload.get("source", "local-seed"),
                source_ref=payload.get("source_ref", "local-seed"),
            )
            written.append(record.memory_id)
        _emit({"status": "seeded", "written": written, "note": "seeded records are candidates and unverified"})
        return EXIT_OK

    if args.memory_command == "verify":
        registry = SourceRegistry(config.resolve_sources_path())
        outcomes = []
        for memory_id in store.ids():
            record = store.get(memory_id)
            if record is None:
                continue
            result = verify_record(record, registry)
            store.set_verification(memory_id, status=result.status, detail=result.detail)
            entry = {"memory_id": memory_id, **result.as_dict(), "promoted": False}
            if result.status == "pass":
                try:
                    store.promote(memory_id)
                    entry["promoted"] = True
                except Exception as exc:
                    entry["promotion_error"] = str(exc)
            outcomes.append(entry)
        _emit({"status": "verified", "outcomes": outcomes})
        return EXIT_OK

    if args.memory_command == "clear":
        if not args.yes:
            _emit({"status": "refused", "detail": "clear requires --yes naming the same store you passed to --store"})
            return EXIT_INPUT
        removed = store.clear(confirm_path=args.store)
        _emit({"status": "cleared", "records_removed": removed, "store": str(store.path)})
        return EXIT_OK

    return EXIT_INPUT
