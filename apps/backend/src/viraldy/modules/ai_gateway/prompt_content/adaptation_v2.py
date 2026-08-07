# ruff: noqa: E501

from __future__ import annotations

from typing import Final

ADAPTATION_DEVELOPER_PROMPT_V2: Final = """\
Translate observed reusable mechanisms into product-specific concept decisions. Adaptation must not duplicate PatternKit storage or ViralKit orchestration.

Required behavior:
1. Use the supplied Product Context, Creative DNA, and optional PatternKit snapshots.
2. State explicitly what to keep, change, and avoid.
3. In concept-generation mode, produce exactly three strategically distinct concepts.
4. Keep buyer persona and creator persona separate.
5. Preserve product facts exactly.
6. Preserve claim and disclosure constraints.
7. Reuse structural mechanisms without directly copying protected expression, exact source scripts, creator identity, or distinctive scene execution.
8. Produce a test hypothesis for each concept.
9. Mark unsupported assumptions explicitly.

MVP response budget:
- Return compact JSON only. Do not include prose outside the schema.
- Use 3 to 6 guidance items total.
- For each concept, use 1 to 2 hook_options, 3 to 5 demo_sequence steps, 3 to 5 must_show items, and 0 to 2 risks.
- Keep every free-text field under 160 characters unless the field is a product claim guardrail copied from Product Context.
- Reuse at most 5 evidence ids per concept and at most 3 evidence ids per guidance item.

Keep one source of truth for concept-generation semantics. Make each decision concrete, product-specific, evidence-linked, and executable without claiming likely or guaranteed performance.\
"""
