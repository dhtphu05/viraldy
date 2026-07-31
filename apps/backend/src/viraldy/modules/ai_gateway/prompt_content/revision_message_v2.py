# ruff: noqa: E501

from __future__ import annotations

from typing import Final

REVISION_MESSAGE_DEVELOPER_PROMPT_V2: Final = """\
Write a friendly, professional, direct, and respectful creator revision message from the supplied persisted strengths and blockers.

Required behavior:
1. Start with one or two specific strengths worth preserving.
2. Request the minimum set of changes needed.
3. Use concrete scene and timing language.
4. Quote exact supplied disclosure text when required.
5. Avoid blame.
6. Avoid internal jargon such as rubric, blocker class, schema, or confidence score.
7. Do not use vague requests such as "make it more viral", "make it catchier", "make it pop", "improve engagement", or "make the hook stronger".
8. Preserve the creator's voice and current strengths.
9. End with a clear resubmission request.
10. Reference only blockers supplied to this operation.

Do not add new requirements, claims, disclosures, timing facts, or evaluation results. Keep creator-facing language in natural en-US even when the seller-facing locale is vi-VN.\
"""
