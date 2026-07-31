# ruff: noqa: E501

from __future__ import annotations

from typing import Final

CONCEPT_VIDEO_PREVIEW_DEVELOPER_PROMPT_V1: Final = """\
Generate a short concept-video preview for the selected ViralKit concept and Campaign Pack direction using only supplied assets, product references, scene requirements, rights constraints, and claim governance.

Preserve the approved product identity, variant, personalization, mechanism, sequence, disclosure, and CTA direction. Keep buyer persona distinct from creator persona. Do not invent product results, compatibility, offer, shipping, scarcity, creator facts, rights, or platform approval. Do not copy exact source scripts, creator identity, slogans, visual identity, or distinctive source execution.

The preview communicates the production concept; it is not observed evidence, a finished creator submission, or proof of performance. Keep any unsupported detail neutral and avoid depicting a result that the supplied proof plan does not support.\
"""
