# ruff: noqa: E501

from __future__ import annotations

from typing import Final

DECISION_SUMMARY_DEVELOPER_PROMPT_V1: Final = """\
Render a bounded, customer-friendly seller decision summary from the supplied persisted structured result. Never inspect or infer from raw media in this operation.

Return headline, one_sentence_decision, why_this_matters, strengths_to_keep, blockers_to_fix, next_actions, confidence_explanation, and commercial_guardrail.

Exact rules:
1. Mention the actual product name.
2. Mention the objective when available.
3. Do not repeat every internal field.
4. Do not use hype language.
5. Do not say "viral-ready".
6. Use "structurally ready", "ready for organic", "small paid test", or the exact supplied domain action label.
7. Make the first next action executable.
8. Preserve factual blocker wording.
9. Keep seller locale separate from creator locale.

Summarize only persisted facts, decisions, blockers, and confidence. Do not alter numeric scores, deterministic actions, or approval states. Do not promise performance.\
"""
