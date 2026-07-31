from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from pydantic import ValidationError

from viraldy.evaluation.qualification import (
    ApplicationQualificationExecutor,
    QualificationExecutor,
    QualificationRequestV1,
    QualificationRunner,
)
from viraldy.evaluation.qualification.catalog import (
    CASE_ALIASES,
    OPERATION_ALIASES,
)
from viraldy.platform.config.settings import Settings


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Qualify Viraldy's OpenAI operation contracts and Golden semantic gates."
        )
    )
    command = parser.add_mutually_exclusive_group(required=True)
    command.add_argument(
        "--check-config",
        action="store_true",
        help="Validate safe provider, model, prompt, and schema configuration.",
    )
    command.add_argument(
        "--operation",
        choices=sorted(OPERATION_ALIASES),
        help="Run one registered operation qualification.",
    )
    command.add_argument(
        "--full-flow",
        action="store_true",
        help="Run the selected Golden case through the qualification flow.",
    )
    case_selection = parser.add_mutually_exclusive_group()
    case_selection.add_argument(
        "--case",
        choices=sorted(CASE_ALIASES),
        help="Golden commercial case to qualify.",
    )
    case_selection.add_argument(
        "--all-cases",
        action="store_true",
        help="Run all authoritative Golden commercial cases.",
    )
    parser.add_argument(
        "--write-report",
        action="store_true",
        help=(
            "Write qualification.json, qualification.md, outputs/, and failures/ "
            "under evaluation/reports/openai/<timestamp>/."
        ),
    )
    parser.add_argument(
        "--application-base-url",
        help=(
            "Run full-flow qualification through an already running Viraldy API, "
            "for example http://127.0.0.1:8001/api/v1."
        ),
    )
    args = parser.parse_args(argv)
    if args.full_flow and args.case is None and not args.all_cases:
        parser.error("--full-flow requires --case or --all-cases")
    if not args.full_flow and (args.case is not None or args.all_cases):
        parser.error("--case and --all-cases require --full-flow")
    if args.application_base_url and not args.full_flow:
        parser.error("--application-base-url requires --full-flow")
    return args


def main(
    argv: Sequence[str] | None = None,
    *,
    settings: Settings | None = None,
    executor: QualificationExecutor | None = None,
    report_root: Path = Path("evaluation/reports/openai"),
) -> int:
    args = parse_args(argv)
    try:
        selected_settings = settings or Settings()
        request = QualificationRequestV1(
            check_config=args.check_config,
            operation=args.operation,
            full_flow=args.full_flow,
            case=args.case,
            all_cases=args.all_cases,
            write_report=args.write_report,
        )
        selected_executor = executor
        if args.application_base_url is not None:
            if selected_executor is not None:
                raise ValueError(
                    "application base URL cannot be combined with an injected executor"
                )
            selected_executor = ApplicationQualificationExecutor(
                settings=selected_settings,
                base_url=args.application_base_url,
            )
        outcome = QualificationRunner(
            settings=selected_settings,
            executor=selected_executor,
            report_root=report_root,
        ).run(request)
    except (ValidationError, ValueError):
        print(
            (
                "OpenAI qualification configuration is invalid. Check AI_MODE, "
                "AI_PROVIDER, OPENAI_API_KEY, and OpenAI model settings."
            ),
            file=sys.stderr,
        )
        return 2

    summary = {
        "run_id": outcome.report.run_id,
        "mode": outcome.report.mode,
        "qualification_state": outcome.report.qualification_state,
        "passed": outcome.report.passed,
        "command": outcome.report.command,
        "sample_size": outcome.report.sample_size,
        "operations": [
            item.operation for item in outcome.report.operation_results
        ],
        "cases": [item.scenario_id for item in outcome.report.case_results],
        "failed_gates": [
            gate.gate
            for gate in (
                *outcome.report.configuration_gates,
                *outcome.report.hard_gates,
                *outcome.report.semantic_gates,
            )
            if not gate.passed
        ],
    }
    if outcome.report_paths is not None:
        summary["report_directory"] = str(outcome.report_paths.root)
        summary["json_report"] = str(outcome.report_paths.json_path)
        summary["markdown_report"] = str(outcome.report_paths.markdown_path)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return outcome.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
