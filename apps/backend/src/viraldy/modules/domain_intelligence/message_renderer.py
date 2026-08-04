from __future__ import annotations

from collections.abc import Sequence

from viraldy.modules.domain_intelligence.schemas import UGCRecommendation


def render_creator_message(
    strengths: Sequence[str],
    fix_first: Sequence[UGCRecommendation],
    improvements: Sequence[UGCRecommendation],
) -> str:
    preserved = strengths[0] if strengths else "the useful creator delivery and unaffected footage"
    preserved_text = _without_leading_keep(preserved)
    opening = (
        f"Please keep {preserved_text[0].lower() + preserved_text[1:]}"
        if preserved_text
        else "Please keep the useful creator delivery and unaffected footage"
    )
    actions: list[str] = []
    for recommendation in [*fix_first, *improvements[:1]]:
        if recommendation.fix_type == "reshoot_scene":
            prefix = "Reshoot only the affected scene:"
        elif recommendation.fix_type in {"replace_copy", "add_overlay", "edit_existing_footage"}:
            prefix = "In the edit:"
        else:
            continue
        instruction = (
            recommendation.instructions[0] if recommendation.instructions else recommendation.title
        )
        actions.append(f"{prefix} {instruction}")
    if not actions:
        actions.append(
            "No reshoot is requested from the current evidence; preserve the approved scope."
        )
    return " ".join([f"{opening}.", *actions])


def _without_leading_keep(value: str) -> str:
    stripped = value.strip()
    lowered = stripped.lower()
    for prefix in ("keep the ", "keep "):
        if lowered.startswith(prefix):
            return stripped[len(prefix) :]
    return stripped
