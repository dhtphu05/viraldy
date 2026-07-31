# ruff: noqa: E501

from __future__ import annotations

from typing import Final

CAMPAIGN_PACK_DEVELOPER_PROMPT_V2: Final = """\
Create a creator-production brief from the selected ViralKit concept. A Creative Campaign Pack is not a TikTok Ads or Meta Ads campaign object.

Return typed fields for the objective, product snapshot, selected concept snapshot, target buyer, creator direction, hero angle, hook options, spoken hook directions, overlay directions, script beats, storyboard scenes, must-show requirements, product visibility timing, demo requirements, proof requirements, offer requirements, CTA requirements, product-tag requirement, allowed and prohibited claims, claims requiring qualification, required disclosures, shipping language, rights notes, raw-footage request, revision checklist, and compiled requirement snapshot.

Exact rules:
1. Do not copy a source ad script.
2. Do not convert every spoken hook into a required overlay.
3. Treat spoken text and overlay text as independent fields.
4. Make required scenes testable by Preflight.
5. Give every hard requirement a requirement class, expected value, severity, source path, and rationale.
6. Preserve exact required disclosure text supplied by Product Context.
7. Do not invent price, discount, delivery, stock, or compatibility.
8. Preserve creator authenticity; do not over-script every sentence.
9. Creator-facing language defaults to natural en-US.
10. Seller-facing explanation follows the workspace locale.

Keep creator direction concise enough to use on a phone. Do not expose internal score weights, schema IDs, or provider details in creator-facing fields.\
"""
