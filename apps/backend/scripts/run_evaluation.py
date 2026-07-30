from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from viraldy.evaluation.contracts import EvaluationDatasetV1
from viraldy.evaluation.harness import evaluate_dataset
from viraldy.evaluation.reporting import write_reports


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate captured PatternKit and ViralKit JSON without provider calls."
    )
    parser.add_argument("dataset", type=Path, help="Path to an evaluation dataset JSON file.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Directory for evaluation-report.json and evaluation-report.md.",
    )
    args = parser.parse_args(argv)

    payload = json.loads(args.dataset.read_text(encoding="utf-8"))
    dataset = EvaluationDatasetV1.model_validate(payload)
    json_path, markdown_path = write_reports(evaluate_dataset(dataset), args.output_dir)
    print(json_path)
    print(markdown_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
