from __future__ import annotations

from uuid import NAMESPACE_URL, uuid5

from viraldy.modules.tiktok_scorer.contracts_v2 import (
    SceneInventoryV1,
    TikTokFindingV2,
    TikTokFixActionV1,
    VideoEditOperationV1,
    VideoSceneV1,
)


def compile_fix_actions(
    findings: list[TikTokFindingV2],
    inventory: SceneInventoryV1,
) -> list[TikTokFixActionV1]:
    actions = [
        action
        for finding in findings
        if finding.applicability == "applicable"
        and finding.priority in {"P0", "P1", "P2"}
        and finding.severity != "info"
        for action in [_compile_finding(finding, inventory)]
        if action is not None
    ]
    return sorted(actions, key=lambda action: (_priority_rank(action.priority), action.code))


def _compile_finding(
    finding: TikTokFindingV2,
    inventory: SceneInventoryV1,
) -> TikTokFixActionV1 | None:
    if finding.evidence_status == "insufficient":
        return _request_better_media(finding)
    if finding.requires_seller_truth:
        return _confirm_seller_input(finding)
    if finding.code in {"RIGHTS_STATUS_UNKNOWN", "PAID_USE_RIGHTS_UNKNOWN"}:
        return _confirm_rights(finding)
    if finding.requires_physical_reshoot is True or finding.code in {
        "PRODUCT_MISMATCH",
        "SKU_MISMATCH",
        "PERSONALIZATION_MISMATCH",
        "INCOMPARABLE_BEFORE_AFTER",
    }:
        return _reshoot(finding)
    copy_edit = _verified_copy_edit(finding, inventory)
    if copy_edit is not None:
        return copy_edit
    if "CLAIM" in finding.code or "COPY" in finding.code:
        return _confirm_seller_input(finding)
    disclosure_edit = _verified_disclosure_overlay(finding, inventory)
    if disclosure_edit is not None:
        return disclosure_edit
    if "DISCLOSURE" in finding.code:
        return _confirm_seller_input(finding)
    readable_hold = _verified_readable_hold(finding, inventory)
    if readable_hold is not None:
        return readable_hold
    if finding.observed.get("required_scene_exists") is False:
        return _add_missing_scene(finding)

    reusable_scene = _find_reusable_scene(finding, inventory)
    if reusable_scene is not None and finding.can_be_resolved_by_edit is True:
        return _edit_existing_scene(finding, reusable_scene, inventory)
    if finding.can_be_resolved_by_edit is True:
        return _add_missing_scene(finding)
    return _reshoot(finding)


def _request_better_media(finding: TikTokFindingV2) -> TikTokFixActionV1:
    return _action(
        finding,
        fix_type="request_better_media",
        owner_role="seller",
        instructions=[
            "Re-upload the original file or a clear export that preserves the affected range.",
            "Confirm the new upload is complete and readable before rescoring.",
        ],
        required_inputs=["A complete, unobscured source video"],
        completion_criteria=[
            "The affected range can be decoded and evidence coverage is no longer insufficient."
        ],
        verification_method="Re-run media extraction and confirm sufficient evidence coverage.",
        estimated_effort="low",
    )


def _confirm_seller_input(finding: TikTokFindingV2) -> TikTokFixActionV1:
    required_inputs = [f"Seller-confirmed {key.replace('_', ' ')}" for key in finding.expected]
    if not required_inputs:
        required_inputs = ["Seller-confirmed product or offer truth"]
    return _action(
        finding,
        fix_type="confirm_seller_input",
        owner_role="seller",
        instructions=[
            "Confirm the expected product, offer, shipping, compatibility, or disclosure value.",
            "Apply only the confirmed value to the video copy before rescoring.",
        ],
        required_inputs=required_inputs,
        completion_criteria=[
            "The seller-confirmed value is recorded in immutable Product Context.",
            "Any visible or spoken copy matches that confirmed value.",
        ],
        verification_method="Compare the revision against the confirmed Product Context snapshot.",
        estimated_effort="low",
    )


def _confirm_rights(finding: TikTokFindingV2) -> TikTokFixActionV1:
    return _action(
        finding,
        fix_type="confirm_rights",
        owner_role="seller",
        instructions=["Confirm paid-use rights outside TikTok Scorer before paid use."],
        required_inputs=["External paid-use rights confirmation"],
        completion_criteria=["Paid-use rights are confirmed in the responsible rights workflow."],
        verification_method="Verify the external rights record; do not infer it from the video.",
        estimated_effort="low",
    )


def _reshoot(finding: TikTokFindingV2) -> TikTokFixActionV1:
    return _action(
        finding,
        fix_type="reshoot_scene",
        owner_role="creator",
        instructions=[
            "Capture a new scene that shows the expected physical state in one readable shot.",
            "Keep the product identity, mechanism, or proof visible long enough to verify it.",
            (
                "Replace the conflicting or unverifiable range; do not simulate the missing "
                "proof in copy."
            ),
        ],
        required_inputs=["The verified physical product and the expected state described above"],
        completion_criteria=[
            "The revision visibly matches the expected product truth.",
            "The new scene has persisted evidence and a valid in-duration timestamp.",
        ],
        verification_method=(
            "Compare product identity and physical evidence in the revision against "
            "Product Context."
        ),
        estimated_effort="high",
        reshoot_required=True,
    )


def _add_missing_scene(finding: TikTokFindingV2) -> TikTokFixActionV1:
    return _action(
        finding,
        fix_type="add_missing_scene",
        owner_role="creator",
        instructions=[
            "Capture the missing scene described in Expected.",
            "Show the relevant product, action, or proof without obscuring the evidence.",
            "Insert the verified new scene at the affected narrative step.",
        ],
        required_inputs=["New footage matching the expected scene state"],
        completion_criteria=[
            "A new evidence-linked scene satisfies the expected state in the revision."
        ],
        verification_method="Confirm the required scene exists in the revision scene inventory.",
        estimated_effort="high",
        reshoot_required=True,
    )


def _verified_copy_edit(
    finding: TikTokFindingV2,
    inventory: SceneInventoryV1,
) -> TikTokFixActionV1 | None:
    if "CLAIM" not in finding.code and "COPY" not in finding.code:
        return None
    replacement = _verified_text(
        finding.expected,
        "approved_replacement_text",
        "replacement_text",
    )
    modality = finding.observed.get("modality")
    if replacement is None or modality not in {"overlay", "spoken"}:
        return None
    scene = _find_reusable_scene(finding, inventory)
    if scene is None:
        return None
    operation_name = "replace_overlay" if modality == "overlay" else "replace_spoken_line"
    fix_type = "replace_overlay_copy" if modality == "overlay" else "replace_spoken_line"
    operation = VideoEditOperationV1(
        operation=operation_name,
        source_scene_id=scene.scene_id,
        source_range_ms=(scene.start_ms, scene.end_ms),
        target_start_ms=scene.start_ms,
        target_duration_ms=scene.end_ms - scene.start_ms,
        text_value=replacement,
        evidence_ids=list(finding.evidence_ids),
        feasibility="verified_possible",
    )
    preserve_operations, preserve_strengths = _preserve_operations(scene, inventory)
    return _action(
        finding,
        fix_type=fix_type,
        owner_role="editor",
        instructions=[
            f"Replace the observed {modality} line at {scene.start_ms}–{scene.end_ms}ms.",
            f"Use the verified replacement exactly: {replacement}",
        ],
        required_inputs=[],
        completion_criteria=[
            "The prior claim text is absent from OCR and transcript evidence.",
            "The replacement exactly matches the approved text.",
        ],
        verification_method="Compare revision OCR/ASR evidence with the approved replacement text.",
        estimated_effort="low",
        video_operations=[operation, *preserve_operations],
        strengths_to_preserve=preserve_strengths,
    )


def _verified_disclosure_overlay(
    finding: TikTokFindingV2,
    inventory: SceneInventoryV1,
) -> TikTokFixActionV1 | None:
    if "DISCLOSURE" not in finding.code:
        return None
    disclosure = _verified_text(finding.expected, "approved_disclosure_text")
    time_range = finding.target_time_range_ms
    if disclosure is None or time_range is None:
        return None
    start_ms, end_ms = time_range
    operation = VideoEditOperationV1(
        operation="add_overlay",
        source_scene_id=None,
        source_range_ms=None,
        target_start_ms=start_ms,
        target_duration_ms=end_ms - start_ms,
        text_value=disclosure,
        evidence_ids=list(finding.evidence_ids),
        feasibility="verified_possible",
    )
    return _action(
        finding,
        fix_type="add_overlay",
        owner_role="editor",
        instructions=[
            f"Add the approved disclosure from {start_ms}–{end_ms}ms: {disclosure}",
            "Keep it readable and unobscured for the full evidence-linked range.",
        ],
        required_inputs=[],
        completion_criteria=[
            "OCR evidence contains the exact approved disclosure in the target range.",
            "Safe-zone evidence does not mark the disclosure as obscured.",
        ],
        verification_method=(
            "Verify exact disclosure copy, timestamp, readability, and safe-zone status."
        ),
        estimated_effort="low",
        video_operations=[operation],
    )


def _verified_readable_hold(
    finding: TikTokFindingV2,
    inventory: SceneInventoryV1,
) -> TikTokFixActionV1 | None:
    if not any(token in finding.code for token in ("READABLE", "READABILITY", "HOLD")):
        return None
    duration = finding.expected.get("target_duration_ms")
    if not isinstance(duration, int) or duration <= 0:
        return None
    scene = _find_reusable_scene(finding, inventory)
    if scene is None:
        return None
    operation = VideoEditOperationV1(
        operation="extend_readable_hold",
        source_scene_id=scene.scene_id,
        source_range_ms=(scene.start_ms, scene.end_ms),
        target_start_ms=scene.start_ms,
        target_duration_ms=duration,
        text_value=None,
        evidence_ids=list(finding.evidence_ids),
        feasibility="likely_possible",
    )
    return _action(
        finding,
        fix_type="edit_existing_footage",
        owner_role="editor",
        instructions=[
            f"Hold scene {scene.scene_id} for {duration}ms without obscuring its readable content."
        ],
        required_inputs=[],
        completion_criteria=[f"The evidence-bearing scene remains readable for {duration}ms."],
        verification_method="Measure the revision scene duration and rerun OCR/readability checks.",
        estimated_effort="low",
        video_operations=[operation],
        strengths_to_preserve=[f"Preserve the verified content in scene {scene.scene_id}."],
    )


def _edit_existing_scene(
    finding: TikTokFindingV2,
    scene: VideoSceneV1,
    inventory: SceneInventoryV1,
) -> TikTokFixActionV1:
    target_start_ms = _target_start_for(finding, scene)
    operation = VideoEditOperationV1(
        operation="move_clip",
        source_scene_id=scene.scene_id,
        source_range_ms=(scene.start_ms, scene.end_ms),
        target_start_ms=target_start_ms,
        target_duration_ms=scene.end_ms - scene.start_ms,
        text_value=None,
        evidence_ids=list(scene.evidence_ids),
        feasibility="verified_possible",
    )
    preserve_operations, preserve_strengths = _preserve_operations(scene, inventory)
    return _action(
        finding,
        fix_type="trim_or_reorder",
        owner_role="editor",
        instructions=[
            f"Move the verified scene from {scene.start_ms}–{scene.end_ms}ms "
            f"to start at {target_start_ms}ms.",
            "Preserve the complete readable action within that source scene.",
        ],
        required_inputs=[],
        completion_criteria=[
            f"Scene {scene.scene_id} begins at {target_start_ms}ms in the revision.",
            "The scene remains readable and its evidence-bearing content is not trimmed out.",
        ],
        verification_method=(
            "Match the source scene evidence in the revision and compare its new start timestamp."
        ),
        estimated_effort="low",
        video_operations=[operation, *preserve_operations],
        strengths_to_preserve=[
            f"Preserve the verified content in scene {scene.scene_id}.",
            *preserve_strengths,
        ],
    )


def _preserve_operations(
    edited_scene: VideoSceneV1,
    inventory: SceneInventoryV1,
) -> tuple[list[VideoEditOperationV1], list[str]]:
    preserved = next(
        (
            scene
            for scene in inventory.scenes
            if scene.scene_id != edited_scene.scene_id and scene.reusable_for_edit
        ),
        None,
    )
    if preserved is None:
        return [], []
    operation = VideoEditOperationV1(
        operation="preserve_clip",
        source_scene_id=preserved.scene_id,
        source_range_ms=(preserved.start_ms, preserved.end_ms),
        target_start_ms=preserved.start_ms,
        target_duration_ms=preserved.end_ms - preserved.start_ms,
        text_value=None,
        evidence_ids=list(preserved.evidence_ids),
        feasibility="verified_possible",
    )
    return [operation], [f"Preserve scene {preserved.scene_id} unchanged."]


def _verified_text(values: dict[str, object], *keys: str) -> str | None:
    for key in keys:
        value = values.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _action(
    finding: TikTokFindingV2,
    *,
    fix_type: str,
    owner_role: str,
    instructions: list[str],
    required_inputs: list[str],
    completion_criteria: list[str],
    verification_method: str,
    estimated_effort: str,
    reshoot_required: bool = False,
    video_operations: list[VideoEditOperationV1] | None = None,
    strengths_to_preserve: list[str] | None = None,
) -> TikTokFixActionV1:
    return TikTokFixActionV1(
        id=uuid5(NAMESPACE_URL, f"viraldy:tiktok-fix:{finding.id}"),
        code=f"FIX_{finding.code}",
        source_finding_id=finding.id,
        source_finding_code=finding.code,
        recommendation_class=(
            "required_fix" if finding.priority in {"P0", "P1"} else "high_priority_improvement"
        ),
        basis=_basis(finding),
        priority=finding.priority,
        severity=finding.severity,
        source_dimension=finding.source_dimension,
        owner_role=owner_role,
        fix_type=fix_type,
        title=_action_title(finding, fix_type),
        why_it_matters=finding.reason,
        expected=dict(finding.expected),
        observed=dict(finding.observed),
        evidence_ids=list(finding.evidence_ids),
        target_time_range_ms=finding.target_time_range_ms,
        video_operations=video_operations or [],
        instructions=instructions,
        strengths_to_preserve=strengths_to_preserve or [],
        required_inputs=required_inputs,
        estimated_effort=estimated_effort,
        reshoot_required=reshoot_required,
        completion_criteria=completion_criteria,
        verification_method=verification_method,
    )


def _find_reusable_scene(
    finding: TikTokFindingV2,
    inventory: SceneInventoryV1,
) -> VideoSceneV1 | None:
    finding_evidence = set(finding.evidence_ids)
    candidates = [
        scene
        for scene in inventory.scenes
        if scene.reusable_for_edit and finding_evidence.intersection(scene.evidence_ids)
    ]
    if finding.source_dimension == "product_visibility":
        candidates = [scene for scene in candidates if scene.product_visible is True]
    if finding.target_time_range_ms is not None:
        start_ms, end_ms = finding.target_time_range_ms
        overlapping = [
            scene for scene in candidates if scene.start_ms < end_ms and scene.end_ms > start_ms
        ]
        if overlapping:
            candidates = overlapping
    return min(candidates, key=lambda scene: scene.start_ms) if candidates else None


def _target_start_for(finding: TikTokFindingV2, scene: VideoSceneV1) -> int:
    expected_start = finding.expected.get("target_start_ms")
    if isinstance(expected_start, int) and expected_start >= 0:
        return expected_start
    if finding.code == "PROFILE_PRODUCT_GROUNDING_LATE":
        return 0
    return scene.start_ms


def _basis(finding: TikTokFindingV2) -> str:
    return {
        "official_hard_rule": "official_rule",
        "product_governance_rule": "product_governance",
        "operational_hard_constraint": "operational_constraint",
        "contextual_guideline": "score_profile",
        "directional_pattern": "contextual_guideline",
        "seller_preference": "video_diagnosis",
    }[finding.rule_class]


def _action_title(finding: TikTokFindingV2, fix_type: str) -> str:
    prefix = {
        "request_better_media": "Upload clearer source media for",
        "confirm_seller_input": "Confirm seller input for",
        "confirm_rights": "Confirm rights for",
        "reshoot_scene": "Reshoot the scene for",
        "add_missing_scene": "Add the missing scene for",
        "trim_or_reorder": "Reorder existing footage for",
    }.get(fix_type, "Resolve")
    return f"{prefix} {finding.title.lower()}"


def _priority_rank(priority: str) -> int:
    return {"P0": 0, "P1": 1, "P2": 2}[priority]


__all__ = ["compile_fix_actions"]
