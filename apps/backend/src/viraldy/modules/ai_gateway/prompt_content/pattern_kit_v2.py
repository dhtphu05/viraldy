# ruff: noqa: E501

from __future__ import annotations

from typing import Final

PATTERN_KIT_DEVELOPER_PROMPT_V2: Final = """\
Extract a reusable, evidence-backed creative mechanism from one or more selected Creative DNA versions. A PatternKit is not an ad template and not a promise of performance.

Use selected Creative DNA snapshots, source evidence, known categories and markets, optional verified performance summaries, and the requested PatternKit scope and name. Return a plain-language name and summary, source count and lineage, sequence beats, opening, product reveal, narrative, demo, proof, creator, editing, offer and CTA patterns, applicability, contraindications, keep/change/avoid instructions, performance-evidence status, confidence, uncertainties, and provenance.

Exact rules:
1. Generalize structure, not exact scripts.
2. Every pattern component must reference source evidence.
3. Do not call a pattern winning when performance evidence is none or insufficient.
4. When sources disagree, record a range, variants, or uncertainty.
5. Make applicability product- and domain-aware.
6. Include TikTok Shop product-demo, POD personalization or gifting, and dropshipping visual-demo applicability only where supported.
7. Record contraindications, including products without observable demos, long-term results, proof that cannot be shown safely, unavailable exact personalization, and unknown shipping claims.
8. Make keep, change, and avoid instructions actionable.
9. Never copy source creator identity, exact hook text, or distinctive visual execution.
10. Treat a performance summary as immutable unless verified records support it.
11. Keep the response compact enough to complete the full schema: return between 4 and 7 sequence beats, at most 2 evidence references per component, at most 3 items in descriptive string lists, at most 2 uncertainties per component, and at most 9 adaptation instructions total.
12. Prefer short, operational phrases over repeated prose. Do not repeat the same evidence summary or rationale across fields.
13. When no verified performance records are supplied, set performance evidence_status to none, asset_count and campaign_count to 0, both date fields to null, metrics to an empty list, and confidence to low. Never infer performance from creative structure.
14. For every evidence reference, copy feature_path exactly from the source's evidence_feature_paths entry for that evidence_id. Never invent, abbreviate, or translate a Creative DNA path.

The result must explain when the mechanism may fit, when it should not be used, its evidence source count, performance-evidence status, confidence, and uncertainty.\
"""
