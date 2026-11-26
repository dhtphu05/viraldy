"""A seller attestation covers source/product rights without inventing evidence."""

from __future__ import annotations

import copy
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError

from tests.unit.test_smart_remake_rights import image_upload, intake_payload, source_upload
from viraldy.modules.smart_remake.project_contracts import SmartRemakeRights
from viraldy.modules.smart_remake.project_policy import (
    assert_project_policy,
    context_with_rights,
    policy_hash,
    rights_snapshot,
)
from viraldy.shared.errors.base import AppError

VERSION = "smart-remake-media-rights-v1"
STATEMENT = (
    "Tôi xác nhận sở hữu hoặc có đủ quyền sử dụng video và ảnh đã tải lên để tạo video AI "
    "phục vụ quảng bá sản phẩm. Tôi chịu trách nhiệm về quyền sử dụng các tư liệu này."
)


def attested_rights(**updates):
    return SmartRemakeRights.model_validate(
        {
            "source": {"basis": "attested", "declared": True},
            "product": {"basis": "attested", "declared": True},
            "attestation": {"policyVersion": VERSION, "accepted": True},
            "providerDisclosureAcknowledged": True,
            **updates,
        }
    )


def saved_row(rights=None):
    return SimpleNamespace(
        context_json={
            "p0": {
                "inputHash": "input-manifest",
                "assets": {
                    "source": {"storageKey": "private/source"},
                    "product": {"storageKey": "private/product"},
                },
                "rights": rights_snapshot(rights or attested_rights(), actor_id=uuid4()),
                "budgetPolicy": {
                    "capUsd": "5.00",
                    "maxAttempts": 20,
                    "maxDurationSeconds": 1800,
                },
                "requirements": {"requiresCharacter": False},
            }
        }
    )


@pytest.mark.parametrize("purpose", ["analysis", "generation", "inspection", "export"])
def test_attestation_allows_source_and_product_without_invented_scope_or_evidence(purpose):
    row = saved_row()
    assert_project_policy(row, purpose=purpose)
    for role in ("source", "product"):
        declaration = row.context_json["p0"]["rights"][role]
        assert declaration["basis"] == "attested"
        assert declaration["scope"] == ""
        assert declaration["evidenceNote"] == ""
        assert declaration["verification"]["status"] == "declared"


def test_server_stamps_actor_time_and_canonical_statement_without_claiming_verification():
    actor = uuid4()
    original = attested_rights()
    snapshot = rights_snapshot(original, actor_id=actor)
    attestation = snapshot["attestation"]
    assert attestation["policyVersion"] == VERSION
    assert attestation["acceptedBy"] == str(actor)
    assert attestation["acceptedAt"]
    assert attestation["statement"] == STATEMENT
    assert "verification" not in attestation
    assert "acceptedBy" not in original.model_dump()["attestation"]


def test_unaccepted_attestation_has_no_acceptance_actor_or_time():
    rights = attested_rights(attestation={"policyVersion": VERSION, "accepted": False})
    attestation = rights_snapshot(rights, actor_id=uuid4())["attestation"]
    assert attestation["acceptedBy"] is None
    assert attestation["acceptedAt"] is None


def test_absent_attestation_preserves_legacy_rights_serialization_and_replay_hashes():
    rights = intake_payload().model_dump(mode="json")["rights"]
    assert "attestation" not in rights
    assert rights["character"] is None
    assert rights["characterConsent"] is None


@pytest.mark.parametrize(
    "field,value", [("accepted", "true"), ("accepted", 1), ("revoked", "false")]
)
def test_attestation_does_not_coerce_ambiguous_acceptance(field, value):
    with pytest.raises(ValidationError):
        attested_rights(attestation={"policyVersion": VERSION, "accepted": True, field: value})


@pytest.mark.parametrize("metadata", ["acceptedBy", "acceptedAt", "statement", "verification"])
def test_client_cannot_forge_attestation_receipt(metadata):
    with pytest.raises(ValidationError):
        attested_rights(
            attestation={"policyVersion": VERSION, "accepted": True, metadata: "forged"}
        )


def test_request_rejects_stale_policy_version():
    with pytest.raises(ValidationError, match="smart-remake-media-rights-v1"):
        attested_rights(attestation={"policyVersion": "old-policy-v0", "accepted": True})


@pytest.mark.parametrize(
    "change,code",
    [
        ("missing", "SMART_REMAKE_RIGHTS_ATTESTATION_REQUIRED"),
        ("unaccepted", "SMART_REMAKE_RIGHTS_ATTESTATION_REQUIRED"),
        ("revoked", "SMART_REMAKE_RIGHTS_ATTESTATION_REQUIRED"),
        ("old-version", "SMART_REMAKE_RIGHTS_POLICY_OUTDATED"),
        ("source-revoked", "SMART_REMAKE_RIGHTS_REQUIRED"),
        ("product-undeclared", "SMART_REMAKE_RIGHTS_REQUIRED"),
        ("no-disclosure", "SMART_REMAKE_DISCLOSURE_REQUIRED"),
    ],
)
def test_saved_attestation_gate_fails_closed(change, code):
    row = saved_row()
    rights = row.context_json["p0"]["rights"]
    if change == "missing":
        rights["attestation"] = None
    elif change == "unaccepted":
        rights["attestation"]["accepted"] = False
    elif change == "revoked":
        rights["attestation"]["revoked"] = True
    elif change == "old-version":
        rights["attestation"]["policyVersion"] = "old-policy-v0"
    elif change == "source-revoked":
        rights["source"]["revoked"] = True
    elif change == "product-undeclared":
        rights["product"]["declared"] = False
    else:
        rights["providerDisclosureAcknowledged"] = False
    with pytest.raises(AppError) as error:
        assert_project_policy(row, purpose="generation")
    assert error.value.code == code


def test_global_attestation_does_not_replace_detailed_character_rights_or_consent():
    rights = attested_rights().model_dump()
    rights["character"] = {"basis": "attested", "declared": True}
    row = saved_row(SmartRemakeRights.model_validate(rights))
    row.context_json["p0"]["assets"]["character"] = {"storageKey": "private/character"}
    row.context_json["p0"]["requirements"]["requiresCharacter"] = True
    with pytest.raises(AppError) as error:
        assert_project_policy(row, purpose="generation")
    assert error.value.code == "SMART_REMAKE_RIGHTS_REQUIRED"
    row.context_json["p0"]["rights"]["character"] = intake_payload().rights.product.model_dump()
    with pytest.raises(AppError) as error:
        assert_project_policy(row, purpose="generation")
    assert error.value.code == "SMART_REMAKE_CHARACTER_CONSENT_REQUIRED"
    row.context_json["p0"]["rights"]["characterConsent"] = {
        "consented": True,
        "scope": "AI advertising",
        "evidenceNote": "Written consent retained.",
        "revoked": False,
    }
    assert_project_policy(row, purpose="generation")


def test_attestation_does_not_replace_evidence_in_detailed_declarations():
    rights = attested_rights().model_dump()
    rights["product"] = intake_payload().rights.product.model_dump()
    rights["product"]["evidenceNote"] = ""
    row = saved_row(SmartRemakeRights.model_validate(rights))
    with pytest.raises(AppError) as error:
        assert_project_policy(row, purpose="analysis")
    assert error.value.code == "SMART_REMAKE_RIGHTS_EVIDENCE_REQUIRED"


def test_rights_update_binds_receipt_and_revocation_invalidates_approval_immutably():
    row = saved_row()
    context = row.context_json
    context["p0"]["release"] = {"approval": {"id": "approved"}, "activeApprovalId": "approved"}
    original = copy.deepcopy(context)
    rights = attested_rights(
        attestation={"policyVersion": VERSION, "accepted": True, "revoked": True}
    )
    actor = uuid4()
    updated = context_with_rights(context, rights, actor_id=actor)
    assert context == original
    assert updated["p0"]["rights"]["attestation"]["acceptedBy"] == str(actor)
    assert updated["p0"]["release"]["approval"] is None
    assert updated["p0"]["release"]["activeApprovalId"] is None
    assert policy_hash(context) != policy_hash(updated)
    row.context_json = updated
    with pytest.raises(AppError) as error:
        assert_project_policy(row, purpose="export")
    assert error.value.code == "SMART_REMAKE_RIGHTS_ATTESTATION_REQUIRED"


@pytest.mark.asyncio
async def test_intake_retains_attestation_against_the_owned_input_manifest():
    from tests.unit.test_smart_remake_rights import MemoryMedia, MemoryRepository
    from viraldy.modules.smart_remake.project_intake import assert_input_binding, create_intake

    actor = uuid4()
    row = await create_intake(
        MemoryRepository(),
        media := MemoryMedia(),
        uuid4(),
        actor,
        intake_payload(rights=attested_rights().model_dump()),
        source_upload(),
        image_upload(),
    )
    assert row.context_json["p0"]["rights"]["attestation"]["acceptedBy"] == str(actor)
    assert row.context_json["p0"]["inputHash"]
    await assert_input_binding(row, media)
    assert_project_policy(row, purpose="analysis")
