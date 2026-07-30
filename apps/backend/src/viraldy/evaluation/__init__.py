"""Deterministic evaluation harness for captured PatternKit and ViralKit outputs."""

from viraldy.evaluation.contracts import EvaluationDatasetV1, EvaluationReportV1
from viraldy.evaluation.harness import evaluate_dataset

__all__ = ["EvaluationDatasetV1", "EvaluationReportV1", "evaluate_dataset"]
