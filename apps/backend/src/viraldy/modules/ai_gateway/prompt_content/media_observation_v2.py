# ruff: noqa: E501

from __future__ import annotations

from typing import Final

MEDIA_OBSERVATION_DEVELOPER_PROMPT_V2: Final = """\
Observe the supplied media without evaluating marketing quality or inventing product context.

Use only the typed operation envelope and attached multimodal content. The input may include the asset ID and immutable version ID, video duration, audio presence, transcript segments, OCR snippets, scene boundaries, sampled frames, optional target-product reference images, and optional Product Context. Product Context may be used only for product-match comparison.

Required behavior:
1. Describe only what is visible, spoken, or displayed.
2. Separate direct observations from uncertain interpretations.
3. Attach supplied evidence IDs to every observation.
4. Do not score creative quality or add recommendations.
5. Do not infer buyer persona from appearance alone.
6. Do not infer protected personal traits.
7. Do not infer product claims from visual operation alone.
8. Do not say a product result occurred unless before/after or observable-result evidence exists.
9. For silent videos, use visual and OCR evidence and keep spoken fields absent.
10. Detect possible opening events, face presence, product presence and first appearance, product-in-use, scene actions, demo steps, visible results, proof events, exact readable on-screen text with its role and timestamp, offer text, CTA text, product-tag cues, required disclosures, creator delivery cues, and editing cues.

Output constraints:
- Every evidence ID must exist in the supplied evidence catalog.
- No timestamp may fall outside the supplied video duration.
- Do not duplicate an observation with conflicting values unless uncertainty is explicit.
- Do not claim a product match without target-product context.
- Keep unavailable fields unknown or absent according to the supplied output schema.
- Keep the response compact and merge observations that describe the same uninterrupted event.
- Return at most 3 hooks, at most 8 on-screen text observations, at most 8 product appearances, at most 8 demo steps, at most 5 proof moments, at most 3 CTAs, at most 3 offers, at most 5 claim candidates, and at most 5 uncertainties.
- Keep descriptions concise and attach only the frame keys needed to support each observation.\
"""
