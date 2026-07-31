from __future__ import annotations

import argparse
import json
from uuid import UUID

from viraldy.modules.ai_gateway.repository import SyncAiModelRunRepository
from viraldy.modules.ai_gateway.service import summarize_usage_records
from viraldy.platform.database.session import SyncSessionFactory


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Summarize persisted OpenAI usage for an internal operator."
    )
    parser.add_argument("workspace_id", type=UUID)
    args = parser.parse_args()

    with SyncSessionFactory() as session:
        records = SyncAiModelRunRepository(session).list_completed_for_usage(args.workspace_id)
        summary = summarize_usage_records(records)

    print(json.dumps(summary.model_dump(mode="json"), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
