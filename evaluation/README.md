# Evaluation

The backend evaluation harness scores captured PatternKit and ViralKit outputs
without invoking an AI provider. Dataset mode is one of `fixture`, `mock`, or
`live`; mode identifies the provenance of the captured candidate.

Run from `apps/backend`:

```bash
uv run python scripts/run_evaluation.py /path/to/dataset.json \
  --output-dir /path/to/reports
```

The command validates `evaluation_dataset_v1` and writes:

- `evaluation-report.json`;
- `evaluation-report.md`.

PatternKit metrics cover schema validity, evidence resolution, source-field and
sequence agreement, applicability, reviewer keep/change/avoid agreement,
cross-category leakage, and unsupported generalization.

ViralKit metrics cover schema validity, product grounding, constraint
preservation, concept diversity, buyer/creator separation, claim/disclosure
preservation, PatternKit traceability, Campaign Pack and Preflight compilation,
and human usefulness.

Judgments are structured labels, booleans, IDs, and reviewer scores. Exact prose
matching is not used as the primary metric. Reports sort cases and JSON keys so
the same dataset produces stable output suitable for versioned comparison.
