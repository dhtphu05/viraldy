# ruff: noqa: E501

from __future__ import annotations

from typing import Final

CREATIVE_DNA_DEVELOPER_PROMPT_V2: Final = """\
Convert normalized observations into an evidence-grounded description of what one creative does. Creative DNA is an observation artifact, not a winning-pattern claim.

Cover opening, hook, product presence and reveal, demo, proof, narrative, buyer pain represented in the creative, creator delivery, editing and pacing, offer, CTA, TikTok Shop cues, claims and disclosures, risks, reusable mechanisms, uncertainties, completeness, and overall confidence.

Exact rules:
1. Use actual supplied evidence fields and preserve their IDs.
2. Product Context may identify mismatch but may not overwrite observation.
3. Do not fill a missing offer or CTA with expected values from the brief.
4. Preserve multiple observed hook signals; select one primary hook only when evidence supports it.
5. Distinguish demo present, demo mechanism clear, result visible, proof present, and proof verifiable.
6. Distinguish spoken text, overlay text, and inferred intent.
7. Product-tag presence requires explicit evidence.
8. Claims must include source, text, timing, and confidence.
9. Every field marked observed, inferred, or not_present must cite one or more supplied evidence IDs. A not_present status must cite evidence that covers the relevant absence. Unknown fields must use value=null; evidence IDs are optional only for unknown fields.
10. A seller-facing summary must mention the actual product when Product Context exists, but structured observations must not fabricate product use.

Use concrete, product-specific wording in explanation fields. Identify what the creative is doing, what is structurally clear, what is missing or uncertain, what is reusable, and what must not be copied. Do not use generic advice such as "strong hook", "clearer CTA", or "make it more engaging" without evidence-specific detail.

Keep the response compact. Return at most 5 claims, at most 5 risks, at most 5 reusable mechanisms, and at most 5 uncertainties. Merge duplicates and keep each explanation concise.\
"""
