"""Saved policy gates; prompt text and client assertions never become verified rights."""

from __future__ import annotations

import copy
import hashlib
import json
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Literal
from uuid import UUID

from viraldy.shared.errors.base import AppError

from .project_contracts import SmartRemakeRequirements, SmartRemakeRights
from .rights_policy import RIGHTS_POLICY_STATEMENT, RIGHTS_POLICY_VERSION

Purpose = Literal["analysis", "generation", "inspection", "export"]


def stable_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


def constraints_hash(context: dict[str, Any]) -> str:
    p0 = context.get("p0", {})
    return stable_hash(
        {
            "requirements": p0.get("requirements"),
            "assets": {
                role: asset.get("mediaHash") for role, asset in p0.get("assets", {}).items()
            },
            **(
                {
                    "additionalProductReferences": [
                        asset.get("mediaHash") for asset in p0["additionalProductReferences"]
                    ]
                }
                if p0.get("additionalProductReferences")
                else {}
            ),
            "targetDuration": p0.get("targetDuration"),
            "referencePolicy": (
                "product-views-and-character-v1"
                if p0.get("additionalProductReferences")
                else "product-and-character-max-three-v1"
            ),
            "expectationsHash": context.get("expectationsHash"),
            "expectationsVersion": (context.get("generationExpectations") or {}).get("version"),
            "generationFacts": {
                key: context.get(key)
                for key in (
                    "productLock",
                    "sceneMap",
                    "sourceSceneMap",
                    "renderPlan",
                    "sourceOpeningFrames",
                    "generationExpectations",
                )
            },
        }
    )


def policy_hash(context: dict[str, Any]) -> str:
    return stable_hash({"rights": context.get("p0", {}).get("rights"), "policyVersion": "p0-v1"})


def assert_project_policy(row: Any, *, purpose: Purpose) -> None:
    """Fail closed before providers/export, including legacy projects without owned intake."""
    p0 = row.context_json.get("p0")
    if not p0 or not p0.get("inputHash"):
        raise AppError(
            "SMART_REMAKE_INTAKE_REQUIRED", "Create an owned intake before continuing.", 403
        )
    if p0.get("status") in {"suspended", "deleted"} or (
        p0.get("deletion", {}).get("status") not in (None, "cancelled")
    ):
        raise AppError(
            "SMART_REMAKE_USE_STOPPED", "This project's assets are no longer in use.", 403
        )
    rights = p0.get("rights", {})
    if rights.get("providerDisclosureAcknowledged") is not True:
        raise AppError(
            "SMART_REMAKE_DISCLOSURE_REQUIRED", "Acknowledge AI provider processing first.", 403
        )
    assets = p0.get("assets", {})
    if "character" in assets and not p0.get("requirements", {}).get("requiresCharacter"):
        raise AppError(
            "SMART_REMAKE_CHARACTER_POLICY_REQUIRED",
            "Confirm character matching before using the uploaded character reference.",
            403,
        )
    for role in ("source", "product"):
        if not assets.get(role, {}).get("storageKey"):
            raise AppError("SMART_REMAKE_INPUT_UNAVAILABLE", "Owned input media is missing.", 409)
    if p0.get("requirements", {}).get("requiresCharacter") and "character" not in assets:
        raise AppError(
            "SMART_REMAKE_CHARACTER_REFERENCE_REQUIRED",
            "Upload the required character reference.",
            403,
        )
    for role in assets:
        declaration = rights.get(role) or {}
        if declaration.get("basis") == "attested" and role in ("source", "product"):
            if declaration.get("declared") is not True or declaration.get("revoked"):
                raise AppError(
                    "SMART_REMAKE_RIGHTS_REQUIRED", f"Valid {role} rights are required.", 403
                )
            assert_rights_attestation(rights)
            continue
        if (
            declaration.get("declared") is not True
            or declaration.get("revoked")
            or not declaration.get("scope", "").strip()
            or declaration.get("basis") not in ("owned", "licensed", "permission", "public_domain")
        ):
            raise AppError(
                "SMART_REMAKE_RIGHTS_REQUIRED", f"Valid {role} rights are required.", 403
            )
        if not declaration.get("evidenceNote", "").strip():
            raise AppError(
                "SMART_REMAKE_RIGHTS_EVIDENCE_REQUIRED",
                f"Record the evidence supporting {role} rights before continuing.",
                403,
            )
    if "character" in assets:
        assert_character_consent(rights)
    budget = p0.get("budgetPolicy") or {}
    if purpose != "export" and budget and budget.get("mode") != "unlimited":
        try:
            cap = Decimal(budget.get("capUsd", "0"))
            valid = cap.is_finite() and cap > 0
        except (InvalidOperation, TypeError, ValueError):
            valid = False
        if not valid or not budget.get("maxAttempts") or not budget.get("maxDurationSeconds"):
            raise AppError(
                "SMART_REMAKE_BUDGET_REQUIRED", "Set a finite budget before AI calls.", 403
            )


def assert_rights_attestation(rights: dict[str, Any]) -> None:
    attestation = rights.get("attestation") or {}
    if attestation and attestation.get("policyVersion") != RIGHTS_POLICY_VERSION:
        raise AppError(
            "SMART_REMAKE_RIGHTS_POLICY_OUTDATED",
            "Read and accept the current media rights policy before continuing.",
            403,
        )
    if attestation.get("accepted") is not True or attestation.get("revoked"):
        raise AppError(
            "SMART_REMAKE_RIGHTS_ATTESTATION_REQUIRED",
            "Confirm your rights to use the uploaded video and product image.",
            403,
        )


def assert_character_consent(rights: dict[str, Any]) -> None:
    consent = rights.get("characterConsent") or {}
    if (
        consent.get("consented") is not True
        or consent.get("revoked")
        or not consent.get("scope", "").strip()
        or not consent.get("evidenceNote", "").strip()
    ):
        raise AppError(
            "SMART_REMAKE_CHARACTER_CONSENT_REQUIRED",
            "Record the character's consent and supporting evidence for this use.",
            403,
        )


def rights_snapshot(rights: SmartRemakeRights, *, actor_id: UUID) -> dict[str, Any]:
    saved = rights.model_dump(mode="json")
    now = datetime.now(UTC).isoformat()
    if saved.get("attestation"):
        accepted = rights.attestation is not None and rights.attestation.accepted
        saved["attestation"] = {
            **saved["attestation"],
            "acceptedBy": str(actor_id) if accepted else None,
            "acceptedAt": now if accepted else None,
            "statement": RIGHTS_POLICY_STATEMENT,
        }
    for role in ("source", "product", "character"):
        declaration = saved.get(role)
        if declaration:
            saved[role] = {
                **declaration,
                "declaredBy": str(actor_id),
                "declaredAt": now,
                "verification": {"status": "declared", "reviewedBy": None, "reviewedAt": None},
            }
    if saved.get("characterConsent"):
        saved["characterConsent"] = {
            **saved["characterConsent"],
            "declaredBy": str(actor_id),
            "declaredAt": now,
        }
    return saved


def invalidate_context(context: dict[str, Any], *, reason: str) -> dict[str, Any]:
    updated = copy.deepcopy(context)
    p0 = updated.setdefault("p0", {})
    release = p0.setdefault("release", {})
    release["approval"] = None
    release["activeApprovalId"] = None
    release["staleReason"] = reason
    p0["inspectionSummary"] = {"status": "stale", "reason": reason}
    return updated


def context_with_requirements(
    context: dict[str, Any], requirements: SmartRemakeRequirements
) -> dict[str, Any]:
    snapshot = requirements.model_dump(mode="json")
    if snapshot == context.get("p0", {}).get("requirements"):
        return copy.deepcopy(context)
    if requirements.requiresCharacter and not context.get("p0", {}).get("assets", {}).get(
        "character"
    ):
        raise AppError(
            "SMART_REMAKE_CHARACTER_REFERENCE_REQUIRED",
            "Upload the required character reference.",
            403,
        )
    updated = invalidate_context(context, reason="requirements_changed")
    updated["expectationsStale"] = True
    updated["p0"]["requirements"] = snapshot
    updated["p0"]["constraintsHash"] = constraints_hash(updated)
    return updated


def context_with_rights(
    context: dict[str, Any], rights: SmartRemakeRights, *, actor_id: UUID
) -> dict[str, Any]:
    updated = invalidate_context(context, reason="rights_changed")
    updated["p0"]["rights"] = rights_snapshot(rights, actor_id=actor_id)
    return updated


def context_with_rights_review(
    context: dict[str, Any], *, actor_id: UUID, evidence_note: str
) -> dict[str, Any]:
    """Record a human review without claiming independently verified legal ownership."""
    if not evidence_note.strip():
        raise AppError(
            "SMART_REMAKE_RIGHTS_EVIDENCE_REQUIRED", "A review needs supporting evidence."
        )
    updated = invalidate_context(context, reason="rights_reviewed")
    now = datetime.now(UTC).isoformat()
    rights = updated["p0"].get("rights", {})
    for role in updated["p0"].get("assets", {}):
        if rights.get(role):
            rights[role]["verification"] = {
                "status": "reviewed",
                "reviewedBy": str(actor_id),
                "reviewedAt": now,
                "evidenceNote": evidence_note.strip(),
            }
    return updated
