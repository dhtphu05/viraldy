from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from decimal import Decimal
from pathlib import Path

from .capture import capture_provenance, redact_private_values
from .contracts import EvidenceBundle, RuntimeCaptureContext
from .corpus import build_dev_corpus, build_pilot_inputs
from .replay import blind_assignments, guard_live_pilot, replay_bundle, validate_bundle
from .reporting import write_reports
from .runtime_adapter import capture_runtime_provenance


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Smart Remake captured evidence; no provider calls."
    )
    commands = parser.add_subparsers(dest="command", required=True)
    corpus = commands.add_parser("dev-corpus", help="Generate self-authored offline fixtures.")
    corpus.add_argument("--output-dir", type=Path, required=True)
    pilot_inputs = commands.add_parser(
        "prepare-pilot-inputs", help="Fresh authored inputs; no calls."
    )
    pilot_inputs.add_argument("--output-dir", type=Path, required=True)
    for name in ("validate", "capture", "replay", "report", "blind", "pilot-check"):
        command = commands.add_parser(name)
        command.add_argument("bundle", type=Path)
        if name in {"replay", "report"}:
            command.add_argument("--output-dir", type=Path, required=True)
        if name == "capture":
            command.add_argument("--provenance", type=Path, required=True)
            command.add_argument("--output", type=Path, required=True)
            command.add_argument(
                "--context", type=Path, help="Manifest context for A's public runtime projection."
            )
        if name == "blind":
            command.add_argument("--seed", required=True)
            command.add_argument("--output", type=Path, required=True)
        if name == "pilot-check":
            command.add_argument("--cap-usd", type=Decimal)
            command.add_argument("--authorized", action="store_true")
    args = parser.parse_args(argv)
    if args.command in {"dev-corpus", "prepare-pilot-inputs"}:
        builder = build_dev_corpus if args.command == "dev-corpus" else build_pilot_inputs
        builder(args.output_dir)
        print(args.output_dir / "bundle.json")
        return 0
    bundle = EvidenceBundle.model_validate_json(args.bundle.read_text(encoding="utf-8"))
    root = args.bundle.parent
    validate_bundle(bundle, root)
    if args.command == "capture":
        payload = json.loads(args.provenance.read_text(encoding="utf-8"))
        if args.context:
            context = RuntimeCaptureContext.model_validate_json(args.context.read_text())
            captures = [capture_runtime_provenance(payload, bundle, context)]
        else:
            captures = capture_provenance(payload)
        bundle = bundle.model_copy(
            update={"captures": [*bundle.captures, *captures], "pilot_preparation": None}
        )
        validate_bundle(bundle, root)
        if args.output.resolve().parent != root.resolve():
            raise ValueError("captured bundle must remain beside its relative artifacts")
        _write_new(args.output, bundle.model_dump(mode="json"))
    elif args.command in {"replay", "report"}:
        for path in write_reports(replay_bundle(bundle, root), args.output_dir):
            print(path)
    elif args.command == "blind":
        assignments = blind_assignments(bundle, seed=args.seed)
        _write_new(
            args.output, {"schema_version": "smart_remake_blinding_v1", "assignments": assignments}
        )
    elif args.command == "pilot-check":
        guard_live_pilot(
            bundle.protocol, bundle.cases, cap_usd=args.cap_usd, authorized=args.authorized
        )
        if bundle.mode != "live":
            raise ValueError(
                "pilot requires live rights-backed inputs; fixture bundle is offline only"
            )
        print(
            "Preflight passed; no provider called. Run only through the budgeted application API."
        )
    else:
        print(f"Validated {bundle.bundle_id}: {bundle.mode}; {len(bundle.captures)} captures")
    return 0


def _write_new(path: Path, payload: object) -> None:
    with path.open("x", encoding="utf-8") as stream:
        json.dump(redact_private_values(payload), stream, sort_keys=True, indent=2)
        stream.write("\n")
