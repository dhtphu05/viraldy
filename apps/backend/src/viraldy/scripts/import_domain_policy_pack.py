from __future__ import annotations

import argparse
import json
from collections.abc import Sequence

from viraldy.modules.domain_intelligence.public import PolicyPackImporter


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate and import a Viraldy domain policy pack."
    )
    parser.add_argument("--pack", required=True)
    parser.add_argument("--schema", required=True)
    parser.add_argument("--sources", required=True)
    parser.add_argument("--activate-mvp", action="store_true")
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    if args.validate_only:
        validated = PolicyPackImporter(None).validate(
            pack_path=args.pack,
            schema_path=args.schema,
            sources_path=args.sources,
        )
        print(
            json.dumps(
                {
                    "pack_name": validated.pack_name,
                    "version": validated.version,
                    "content_hash": validated.content_hash,
                    "counts": validated.counts.model_dump(),
                    "status": "valid",
                },
                sort_keys=True,
            )
        )
        return 0

    if args.dry_run:
        summary = PolicyPackImporter(None).import_pack(
            pack_path=args.pack,
            schema_path=args.schema,
            sources_path=args.sources,
            activate_mvp=args.activate_mvp,
            dry_run=True,
        )
    else:
        from viraldy.platform.database.session import SyncSessionFactory

        try:
            with SyncSessionFactory.begin() as session:
                summary = PolicyPackImporter(session).import_pack(
                    pack_path=args.pack,
                    schema_path=args.schema,
                    sources_path=args.sources,
                    activate_mvp=args.activate_mvp,
                )
        except Exception as exc:
            parser.error(f"database import failed: {exc}")
    print(summary.model_dump_json())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
