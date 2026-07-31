# ruff: noqa: E501

from __future__ import annotations

from typing import Final

VIRAL_KIT_DEVELOPER_PROMPT_V2: Final = """\
Compile the immutable Product Context, selected PatternKit versions, campaign objective, and seller constraints into a product-specific creative experiment package. A ViralKit is a test-ready hypothesis package, not a guarantee of virality.

Use the supplied Product Context snapshot, PatternKit snapshots, pattern-match scores and reasons, objective, platform, target market, buyer persona selection, creator and commercial constraints, claim governance, disclosures, and seller creative constraints.

Return exactly three concepts. Every pair must differ on at least two meaningful axes among buyer context, hook mechanism, narrative structure, creator persona, delivery style, demo mechanism, proof mechanism, emotional driver, and offer framing. Wording changes alone do not count.

Each concept must include its ID and customer-friendly name, one-sentence idea, selected buyer persona, buyer pain, desired outcome, hook mechanism and original hook direction, opening visual, audience context, creator persona and delivery style, narrative progression, demo and proof mechanisms, product reveal guidance, offer framing, CTA strategy, product-tag requirement, must-show elements, claims to avoid, required disclosures, creative risks, test hypothesis, primary decision criterion, pattern source links, evidence links, and confidence.

Domain rules:
- TikTok Shop US concepts must use the actual product mechanism, buyer use context, offer, product-tag requirement, CTA type, shipping constraints, and claim governance.
- POD concepts must preserve the actual recipient, occasion, personalization field, variant or design detail, reveal moment, ordering instructions, and production or delivery constraints.
- Dropshipping concepts must preserve the observable mechanism, supported use case, compatibility boundaries, trust mechanism, shipping constraint, and claim restrictions.

Include a test matrix stating what remains fixed, what changes by concept, the primary seller decision signal, minimum execution requirements, and main confounders. Never invent performance targets. Do not return generic concepts that could be reused unchanged for an unrelated product.\
"""
