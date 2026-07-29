from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from viraldy.modules.creative_domain.schema_versions import COMPILED_REQUIREMENTS_SCHEMA_VERSION

RequirementSeverity = Literal["hard", "high", "medium", "low"]
ExpectedSemantics = Literal[
    "presence",
    "absence",
    "qualified_presence",
    "timing",
    "type_match",
    "semantic_match",
]


class CompiledRequirementV2(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    requirement_type: str
    source_path: str
    description: str
    severity: RequirementSeverity
    matcher_type: str
    matcher_config: dict[str, object] = Field(default_factory=dict)
    expected_semantics: ExpectedSemantics
    requirement_group_id: str | None = None
    minimum_satisfied: int | None = None


class CompiledRequirementsSnapshotV2(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["compiled_requirements_v2"] = COMPILED_REQUIREMENTS_SCHEMA_VERSION
    requirements: list[CompiledRequirementV2]


def compile_campaign_requirements(brief_json: dict[str, object]) -> list[CompiledRequirementV2]:
    requirements: list[CompiledRequirementV2] = []
    _compile_must_show(brief_json, requirements)
    _compile_hooks(brief_json, requirements)
    _compile_script_beats(brief_json, requirements)
    _compile_storyboard(brief_json, requirements)
    _compile_text_overlays(brief_json, requirements)
    _compile_creator_direction(brief_json, requirements)
    _compile_proof_direction(brief_json, requirements)
    _compile_offer_direction(brief_json, requirements)
    _compile_cta(brief_json, requirements)
    _compile_claim_guardrails(brief_json, requirements)
    _compile_product_snapshot(brief_json, requirements)
    _compile_angle(brief_json, requirements)
    if not requirements:
        requirements.append(
            _requirement(
                id="baseline_product_visibility",
                requirement_type="product",
                source_path="system.baseline_product_visibility",
                description="Product must be visible enough to evaluate the UGC.",
                severity="hard",
                matcher_type="product_visibility",
                matcher_config={},
                expected_semantics="presence",
            )
        )
    return _dedupe_requirements(requirements)


def compile_requirements(brief_json: dict[str, object]) -> list[CompiledRequirementV2]:
    return compile_campaign_requirements(brief_json)


def compiled_requirements_to_json(
    requirements: list[CompiledRequirementV2],
) -> dict[str, object]:
    return CompiledRequirementsSnapshotV2(requirements=requirements).model_dump(mode="json")


def parse_compiled_requirements_snapshot(
    payload: dict[str, object] | None,
) -> list[CompiledRequirementV2]:
    if not payload:
        return []
    raw = payload.get("requirements")
    if not isinstance(raw, list):
        raise ValueError("compiled requirements snapshot must include requirements list")
    if payload.get("schema_version") == COMPILED_REQUIREMENTS_SCHEMA_VERSION:
        return [CompiledRequirementV2.model_validate(item) for item in raw]
    return [_legacy_requirement(item) for item in raw if isinstance(item, dict)]


def _compile_must_show(
    brief_json: dict[str, object], requirements: list[CompiledRequirementV2]
) -> None:
    for index, item in enumerate(_as_list(brief_json.get("must_show")), start=1):
        parsed = _must_show_item(item, index)
        if parsed is None:
            continue
        requirement_type = parsed["requirement_type"]
        description = str(parsed["description"])
        severity = _severity(parsed.get("severity"), "high")
        source_path = str(parsed["source_path"])
        base_id = str(parsed["id"])
        expected_before_ms = parsed.get("expected_before_ms")
        matcher_type = _matcher_for_requirement(requirement_type, description, expected_before_ms)
        semantics = _semantics_for_matcher(matcher_type)
        config: dict[str, object] = {"text": description}
        if isinstance(expected_before_ms, int):
            config["expected_before_ms"] = expected_before_ms
            config["before_ms"] = expected_before_ms
        requirements.append(
            _requirement(
                id=base_id,
                requirement_type=str(requirement_type),
                source_path=source_path,
                description=description,
                severity=severity,
                matcher_type=matcher_type,
                matcher_config=config,
                expected_semantics=semantics,
            )
        )


def _compile_hooks(
    brief_json: dict[str, object],
    requirements: list[CompiledRequirementV2],
) -> None:
    hooks = [item for item in _as_list(brief_json.get("hooks")) if isinstance(item, dict)]
    optional_index = 0
    for index, hook in enumerate(hooks, start=1):
        spoken_text = _clean_text(hook.get("spoken_text"))
        overlay_text = _clean_text(hook.get("overlay_text"))
        opening_visual = _clean_text(hook.get("opening_visual"))
        expected = spoken_text or overlay_text or opening_visual
        if not expected:
            continue
        mandatory = bool(hook.get("mandatory"))
        optional_index += 0 if mandatory else 1
        requirements.append(
            _requirement(
                id=_clean_text(hook.get("id")) or f"hook_{index}",
                requirement_type="hook",
                source_path=f"hooks[{index - 1}]",
                description=f"Opening hook must match: {expected}",
                severity="high" if mandatory else "medium",
                matcher_type="hook_semantic_match",
                matcher_config={
                    "text": expected,
                    "hook_type": _clean_text(hook.get("hook_type")),
                    "target_time_ms": hook.get("target_time_ms")
                    if isinstance(hook.get("target_time_ms"), int)
                    else None,
                },
                expected_semantics="semantic_match",
                requirement_group_id=None if mandatory else "optional_hooks",
                minimum_satisfied=None if mandatory else 1,
            )
        )


def _compile_script_beats(
    brief_json: dict[str, object], requirements: list[CompiledRequirementV2]
) -> None:
    for index, beat in enumerate(_as_list(brief_json.get("script_beats")), start=1):
        if not isinstance(beat, dict) or not bool(beat.get("required")):
            continue
        instruction = _clean_text(beat.get("instruction"))
        if not instruction:
            continue
        beat_type = _clean_text(beat.get("beat_type"))
        matcher = "demo_mechanism_match" if "demo" in beat_type.lower() else "spoken_text_presence"
        requirements.append(
            _requirement(
                id=_clean_text(beat.get("id")) or f"script_beat_{index}",
                requirement_type="demo" if matcher == "demo_mechanism_match" else "script",
                source_path=f"script_beats[{index - 1}]",
                description=instruction,
                severity="high",
                matcher_type=matcher,
                matcher_config={"text": instruction},
                expected_semantics=_semantics_for_matcher(matcher),
            )
        )


def _compile_storyboard(
    brief_json: dict[str, object], requirements: list[CompiledRequirementV2]
) -> None:
    for index, scene in enumerate(_as_list(brief_json.get("storyboard")), start=1):
        if not isinstance(scene, dict) or not bool(scene.get("required")):
            continue
        scene_id = _clean_text(scene.get("id")) or f"storyboard_scene_{index}"
        source_path = f"storyboard[{index - 1}]"
        if bool(scene.get("product_visibility_required")):
            requirements.append(
                _requirement(
                    id=f"{scene_id}_product",
                    requirement_type="product",
                    source_path=source_path,
                    description="Required storyboard scene must show product visibility.",
                    severity="high",
                    matcher_type="product_visibility",
                    matcher_config={"shot_type": _clean_text(scene.get("shot_type"))},
                    expected_semantics="presence",
                )
            )
        overlay = _clean_text(scene.get("overlay_text"))
        if overlay:
            requirements.append(
                _requirement(
                    id=f"{scene_id}_overlay",
                    requirement_type="overlay",
                    source_path=source_path,
                    description=f"Required overlay must appear: {overlay}",
                    severity="high",
                    matcher_type="overlay_text_presence",
                    matcher_config={"text": overlay},
                    expected_semantics="presence",
                )
            )
        spoken = _clean_text(scene.get("spoken_direction"))
        if spoken:
            requirements.append(
                _requirement(
                    id=f"{scene_id}_spoken",
                    requirement_type="spoken",
                    source_path=source_path,
                    description=f"Required spoken direction must appear: {spoken}",
                    severity="high",
                    matcher_type="spoken_text_presence",
                    matcher_config={"text": spoken},
                    expected_semantics="presence",
                )
            )


def _compile_text_overlays(
    brief_json: dict[str, object], requirements: list[CompiledRequirementV2]
) -> None:
    for index, text in enumerate(_list_of_text(brief_json.get("text_overlays")), start=1):
        requirements.append(
            _requirement(
                id=f"text_overlay_{index}",
                requirement_type="overlay",
                source_path=f"text_overlays[{index - 1}]",
                description=f"Required overlay must appear: {text}",
                severity="medium",
                matcher_type="overlay_text_presence",
                matcher_config={"text": text},
                expected_semantics="presence",
            )
        )


def _compile_creator_direction(
    brief_json: dict[str, object], requirements: list[CompiledRequirementV2]
) -> None:
    creator = brief_json.get("creator_direction")
    if not isinstance(creator, dict):
        return
    persona = _clean_text(creator.get("persona"))
    delivery_style = _clean_text(creator.get("delivery_style"))
    if not persona and not delivery_style:
        return
    requirements.append(
        _requirement(
            id="creator_direction_match",
            requirement_type="creator",
            source_path="creator_direction",
            description="Creator direction must match the briefed persona and delivery style.",
            severity="medium",
            matcher_type="creator_style_match",
            matcher_config={"creator_persona": persona, "delivery_style": delivery_style},
            expected_semantics="semantic_match",
        )
    )


def _compile_proof_direction(
    brief_json: dict[str, object], requirements: list[CompiledRequirementV2]
) -> None:
    for index, text in enumerate(_list_of_text(brief_json.get("proof_direction")), start=1):
        requirements.append(
            _requirement(
                id=f"proof_direction_{index}",
                requirement_type="proof",
                source_path=f"proof_direction[{index - 1}]",
                description=f"Proof direction must be observed: {text}",
                severity="medium",
                matcher_type="proof_presence",
                matcher_config={"text": text},
                expected_semantics="presence",
            )
        )


def _compile_offer_direction(
    brief_json: dict[str, object], requirements: list[CompiledRequirementV2]
) -> None:
    offers = _list_of_text(brief_json.get("offer_direction"))
    if not offers:
        return
    requirements.append(
        _requirement(
            id="offer_presence",
            requirement_type="offer",
            source_path="offer_direction",
            description="Offer must be present when configured by the Campaign Pack.",
            severity="high",
            matcher_type="offer_presence",
            matcher_config={},
            expected_semantics="presence",
        )
    )
    for index, text in enumerate(offers, start=1):
        requirements.append(
            _requirement(
                id=f"offer_text_{index}",
                requirement_type="offer",
                source_path=f"offer_direction[{index - 1}]",
                description=f"Offer text must match: {text}",
                severity="medium",
                matcher_type="offer_text_match",
                matcher_config={"text": text},
                expected_semantics="semantic_match",
            )
        )
    requirements.append(
        _requirement(
            id="offer_before_cta",
            requirement_type="offer",
            source_path="offer_direction",
            description="Offer must appear before the CTA.",
            severity="medium",
            matcher_type="offer_before_cta",
            matcher_config={},
            expected_semantics="timing",
        )
    )


def _compile_cta(brief_json: dict[str, object], requirements: list[CompiledRequirementV2]) -> None:
    cta = brief_json.get("cta")
    if not isinstance(cta, dict):
        return
    cta_type = _clean_text(cta.get("cta_type"))
    product_tag_required = bool(cta.get("product_tag_required"))
    required_before_ms = cta.get("required_before_ms")
    severity: RequirementSeverity = "hard" if product_tag_required else "high"
    requirements.append(
        _requirement(
            id="cta_presence",
            requirement_type="cta",
            source_path="cta",
            description="CTA must be present.",
            severity=severity,
            matcher_type="cta_presence",
            matcher_config={},
            expected_semantics="presence",
        )
    )
    if cta_type:
        requirements.append(
            _requirement(
                id="cta_type_match",
                requirement_type="cta",
                source_path="cta.cta_type",
                description=f"CTA type must match {cta_type}.",
                severity=severity,
                matcher_type="cta_type_match",
                matcher_config={"cta_type": cta_type},
                expected_semantics="type_match",
            )
        )
    if product_tag_required:
        requirements.append(
            _requirement(
                id="product_tag_presence",
                requirement_type="cta",
                source_path="cta.product_tag_required",
                description="Product tag must be visible.",
                severity="hard",
                matcher_type="product_tag_presence",
                matcher_config={},
                expected_semantics="presence",
            )
        )
    if isinstance(required_before_ms, int):
        requirements.append(
            _requirement(
                id="cta_timing",
                requirement_type="cta",
                source_path="cta.required_before_ms",
                description=f"CTA must appear before {required_before_ms}ms.",
                severity=severity,
                matcher_type="cta_timing",
                matcher_config={"required_before_ms": required_before_ms},
                expected_semantics="timing",
            )
        )
    spoken = _clean_text(cta.get("spoken"))
    if spoken:
        requirements.append(
            _requirement(
                id="cta_spoken_text",
                requirement_type="cta",
                source_path="cta.spoken",
                description=f"CTA spoken text must match: {spoken}",
                severity="medium",
                matcher_type="spoken_text_presence",
                matcher_config={"text": spoken},
                expected_semantics="presence",
            )
        )
    overlay = _clean_text(cta.get("overlay"))
    if overlay:
        requirements.append(
            _requirement(
                id="cta_overlay_text",
                requirement_type="cta",
                source_path="cta.overlay",
                description=f"CTA overlay text must match: {overlay}",
                severity="medium",
                matcher_type="overlay_text_presence",
                matcher_config={"text": overlay},
                expected_semantics="presence",
            )
        )


def _compile_claim_guardrails(
    brief_json: dict[str, object], requirements: list[CompiledRequirementV2]
) -> None:
    claim_guardrails = brief_json.get("claim_guardrails")
    if isinstance(claim_guardrails, dict):
        for index, claim in enumerate(_list_of_text(claim_guardrails.get("prohibited")), start=1):
            requirements.append(
                _requirement(
                    id=f"prohibited_claim_{index}",
                    requirement_type="claim",
                    source_path=f"claim_guardrails.prohibited[{index - 1}]",
                    description=f"Do not include prohibited claim: {claim}",
                    severity="hard",
                    matcher_type="prohibited_claim_absence",
                    matcher_config={"text": claim},
                    expected_semantics="absence",
                )
            )
        for index, text in enumerate(
            _list_of_text(claim_guardrails.get("required_disclosures")), start=1
        ):
            requirements.append(
                _requirement(
                    id=f"required_disclosure_{index}",
                    requirement_type="claim",
                    source_path=f"claim_guardrails.required_disclosures[{index - 1}]",
                    description=f"Required disclosure must appear: {text}",
                    severity="hard",
                    matcher_type="required_disclosure_presence",
                    matcher_config={"text": text},
                    expected_semantics="presence",
                )
            )
        for index, claim in enumerate(
            _list_of_text(claim_guardrails.get("allowed_with_qualification")), start=1
        ):
            requirements.append(
                _requirement(
                    id=f"qualified_claim_{index}",
                    requirement_type="claim",
                    source_path=f"claim_guardrails.allowed_with_qualification[{index - 1}]",
                    description=f"Allowed claim must be qualified: {claim}",
                    severity="high",
                    matcher_type="allowed_claim_qualification",
                    matcher_config={"claim_text": claim, "qualification_text": claim},
                    expected_semantics="qualified_presence",
                )
            )
    for index, claim in enumerate(_list_of_text(brief_json.get("claims_to_avoid")), start=1):
        requirements.append(
            _requirement(
                id=f"claims_to_avoid_{index}",
                requirement_type="claim",
                source_path=f"claims_to_avoid[{index - 1}]",
                description=f"Do not include prohibited claim: {claim}",
                severity="hard",
                matcher_type="prohibited_claim_absence",
                matcher_config={"text": claim},
                expected_semantics="absence",
            )
        )
    product_snapshot = brief_json.get("product_snapshot")
    governance = product_snapshot.get("governance") if isinstance(product_snapshot, dict) else None
    if not isinstance(governance, dict):
        return
    for rule in _as_list(governance.get("claims")):
        if not isinstance(rule, dict):
            continue
        rule_type = _clean_text(rule.get("rule_type"))
        text = _clean_text(rule.get("text"))
        if not text:
            continue
        if rule_type == "prohibited":
            requirements.append(
                _requirement(
                    id=f"product_prohibited_claim_{_stable_slug(text)}",
                    requirement_type="claim",
                    source_path="product_snapshot.governance.claims",
                    description=f"Do not include prohibited claim: {text}",
                    severity="hard",
                    matcher_type="prohibited_claim_absence",
                    matcher_config={"text": text},
                    expected_semantics="absence",
                )
            )
        elif rule_type == "required_disclosure":
            requirements.append(
                _requirement(
                    id=f"product_required_disclosure_{_stable_slug(text)}",
                    requirement_type="claim",
                    source_path="product_snapshot.governance.claims",
                    description=f"Required disclosure must appear: {text}",
                    severity="hard",
                    matcher_type="required_disclosure_presence",
                    matcher_config={"text": text},
                    expected_semantics="presence",
                )
            )
        elif rule_type == "allowed_with_qualification":
            requirements.append(
                _requirement(
                    id=f"product_qualified_claim_{_stable_slug(text)}",
                    requirement_type="claim",
                    source_path="product_snapshot.governance.claims",
                    description=f"Allowed claim must be qualified: {text}",
                    severity="high",
                    matcher_type="allowed_claim_qualification",
                    matcher_config={
                        "claim_text": text,
                        "qualification_text": _clean_text(rule.get("qualification")),
                    },
                    expected_semantics="qualified_presence",
                )
            )
    for index, text in enumerate(_list_of_text(governance.get("required_disclosures")), start=1):
        requirements.append(
            _requirement(
                id=f"product_required_disclosure_{index}",
                requirement_type="claim",
                source_path=f"product_snapshot.governance.required_disclosures[{index - 1}]",
                description=f"Required disclosure must appear: {text}",
                severity="hard",
                matcher_type="required_disclosure_presence",
                matcher_config={"text": text},
                expected_semantics="presence",
            )
        )


def _compile_product_snapshot(
    brief_json: dict[str, object], requirements: list[CompiledRequirementV2]
) -> None:
    product_snapshot = brief_json.get("product_snapshot")
    if not isinstance(product_snapshot, dict):
        return
    identity = product_snapshot.get("identity")
    product_name = _clean_text(identity.get("name")) if isinstance(identity, dict) else ""
    if product_name:
        requirements.append(
            _requirement(
                id="product_match",
                requirement_type="product",
                source_path="product_snapshot.identity",
                description="Observed product must match the Campaign Pack product snapshot.",
                severity="hard",
                matcher_type="product_match",
                matcher_config={"product_name": product_name},
                expected_semantics="semantic_match",
            )
        )
    requirements.append(
        _requirement(
            id="product_in_use",
            requirement_type="product",
            source_path="product_snapshot",
            description="Product should be shown in use or during a visible demo.",
            severity="medium",
            matcher_type="product_in_use",
            matcher_config={},
            expected_semantics="presence",
        )
    )


def _compile_angle(
    brief_json: dict[str, object], requirements: list[CompiledRequirementV2]
) -> None:
    angle = brief_json.get("angle")
    if not isinstance(angle, dict):
        return
    mechanism = _clean_text(angle.get("mechanism"))
    if mechanism:
        requirements.append(
            _requirement(
                id="angle_mechanism_match",
                requirement_type="demo",
                source_path="angle.mechanism",
                description=f"Demo mechanism must match campaign angle: {mechanism}",
                severity="medium",
                matcher_type="demo_mechanism_match",
                matcher_config={"text": mechanism},
                expected_semantics="semantic_match",
            )
        )


def _must_show_item(item: object, index: int) -> dict[str, object] | None:
    if isinstance(item, dict):
        description = _clean_text(item.get("description"))
        if not description:
            return None
        requirement_type = _requirement_type(item.get("requirement_type"), description)
        return {
            "id": _clean_text(item.get("id")) or f"must_show_{index}",
            "requirement_type": requirement_type,
            "source_path": _clean_text(item.get("source_path")) or f"must_show[{index - 1}]",
            "description": description,
            "severity": _severity(item.get("severity"), "high"),
            "expected_before_ms": item.get("expected_before_ms")
            if isinstance(item.get("expected_before_ms"), int)
            else None,
        }
    description = _clean_text(item)
    if not description:
        return None
    matcher_type = _matcher_for_text(description)
    return {
        "id": f"must_show_{index}",
        "requirement_type": _requirement_type_for_matcher(matcher_type),
        "source_path": f"must_show[{index - 1}]",
        "description": description,
        "severity": "high",
        "expected_before_ms": None,
    }


def _matcher_for_requirement(
    requirement_type: object, description: str, expected_before_ms: object
) -> str:
    type_text = _clean_text(requirement_type)
    if type_text == "product" and isinstance(expected_before_ms, int):
        return "product_visibility_timing"
    return {
        "cta": "cta_presence",
        "demo": "demo_mechanism_match",
        "proof": _proof_matcher(description),
        "product": "product_visibility",
        "claim": "required_disclosure_presence"
        if "disclosure" in description.lower()
        else "prohibited_claim_absence",
        "overlay": "overlay_text_presence",
        "creator": "creator_style_match",
        "offer": "offer_text_match",
    }.get(type_text, _matcher_for_text(description))


def _matcher_for_text(text: str) -> str:
    lowered = text.lower()
    if "cta" in lowered or "shop" in lowered or "tag" in lowered:
        return "cta_presence"
    if "overlay" in lowered or "caption" in lowered or "text" in lowered:
        return "overlay_text_presence"
    if "demo" in lowered or "use" in lowered or "using" in lowered:
        return "demo_mechanism_match"
    if "before" in lowered or "after" in lowered or "result" in lowered or "proof" in lowered:
        return _proof_matcher(text)
    if "offer" in lowered or "discount" in lowered or "price" in lowered:
        return "offer_text_match"
    if "creator" in lowered or "face" in lowered or "voice" in lowered:
        return "creator_style_match"
    if "product" in lowered or "close-up" in lowered or "close up" in lowered:
        return "product_visibility"
    return "hook_semantic_match"


def _proof_matcher(text: str) -> str:
    lowered = text.lower()
    proof_types = {
        "before_after",
        "measurement",
        "testimonial",
        "visual_result",
        "comparison",
        "review",
    }
    return "proof_type_match" if any(item in lowered for item in proof_types) else "proof_presence"


def _semantics_for_matcher(matcher_type: str) -> ExpectedSemantics:
    if matcher_type.endswith("_timing") or matcher_type == "offer_before_cta":
        return "timing"
    if matcher_type.endswith("_type_match"):
        return "type_match"
    if matcher_type == "prohibited_claim_absence":
        return "absence"
    if matcher_type == "allowed_claim_qualification":
        return "qualified_presence"
    if matcher_type in {
        "demo_mechanism_match",
        "hook_semantic_match",
        "creator_style_match",
        "product_match",
        "offer_text_match",
    }:
        return "semantic_match"
    return "presence"


def _requirement_type(value: object, description: str) -> str:
    text = _clean_text(value)
    if text in {
        "product",
        "demo",
        "proof",
        "offer",
        "cta",
        "overlay",
        "creator",
        "scene",
        "claim",
    }:
        return text
    return _requirement_type_for_matcher(_matcher_for_text(description))


def _requirement_type_for_matcher(matcher_type: str) -> str:
    return {
        "cta_presence": "cta",
        "cta_type_match": "cta",
        "cta_timing": "cta",
        "product_tag_presence": "cta",
        "demo_mechanism_match": "demo",
        "demo_presence": "demo",
        "proof_presence": "proof",
        "proof_type_match": "proof",
        "product_visibility": "product",
        "product_visibility_timing": "product",
        "product_match": "product",
        "product_in_use": "product",
        "prohibited_claim_absence": "claim",
        "required_disclosure_presence": "claim",
        "allowed_claim_qualification": "claim",
    }.get(matcher_type, "scene")


def _legacy_requirement(item: dict[str, object]) -> CompiledRequirementV2:
    matcher_type = _clean_text(item.get("matcher_type")) or "hook_semantic_match"
    raw_config = item.get("matcher_config")
    matcher_config = raw_config if isinstance(raw_config, dict) else {}
    return CompiledRequirementV2(
        id=_clean_text(item.get("id")) or "legacy_requirement",
        requirement_type=_clean_text(item.get("requirement_type")) or _requirement_type_for_matcher(
            matcher_type
        ),
        source_path=_clean_text(item.get("source_path")) or "legacy",
        description=_clean_text(item.get("description")) or "Legacy requirement",
        severity=_severity(item.get("severity"), "high"),
        matcher_type="prohibited_claim_absence" if matcher_type == "claim_safety" else matcher_type,
        matcher_config=dict(matcher_config),
        expected_semantics=_semantics_for_matcher(
            "prohibited_claim_absence" if matcher_type == "claim_safety" else matcher_type
        ),
    )


def _requirement(
    *,
    id: str,
    requirement_type: str,
    source_path: str,
    description: str,
    severity: RequirementSeverity,
    matcher_type: str,
    matcher_config: dict[str, object],
    expected_semantics: ExpectedSemantics,
    requirement_group_id: str | None = None,
    minimum_satisfied: int | None = None,
) -> CompiledRequirementV2:
    return CompiledRequirementV2(
        id=id,
        requirement_type=requirement_type,
        source_path=source_path,
        description=description,
        severity=severity,
        matcher_type=matcher_type,
        matcher_config={key: value for key, value in matcher_config.items() if value is not None},
        expected_semantics=expected_semantics,
        requirement_group_id=requirement_group_id,
        minimum_satisfied=minimum_satisfied,
    )


def _dedupe_requirements(
    requirements: list[CompiledRequirementV2],
) -> list[CompiledRequirementV2]:
    deduped: list[CompiledRequirementV2] = []
    seen: set[tuple[str, str, str]] = set()
    used_ids: set[str] = set()
    for requirement in requirements:
        text_key = _clean_text(requirement.matcher_config.get("text") or requirement.description)
        key = (requirement.matcher_type, text_key.lower(), requirement.source_path)
        if key in seen:
            continue
        seen.add(key)
        candidate = requirement
        if candidate.id in used_ids:
            candidate = candidate.model_copy(update={"id": f"{candidate.id}_{len(used_ids) + 1}"})
        used_ids.add(candidate.id)
        deduped.append(candidate)
    return deduped


def _as_list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


def _list_of_text(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [text for item in value if (text := _clean_text(item))]


def _severity(value: object, fallback: RequirementSeverity) -> RequirementSeverity:
    text = _clean_text(value)
    if text in {"hard", "high", "medium", "low"}:
        return text  # type: ignore[return-value]
    return fallback


def _stable_slug(value: str) -> str:
    cleaned = "".join(char if char.isalnum() else "_" for char in value.lower()).strip("_")
    return cleaned[:60] or "rule"


def _clean_text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""
