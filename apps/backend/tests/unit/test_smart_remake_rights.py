from __future__ import annotations

import copy
import io
from types import SimpleNamespace
from uuid import uuid4

import pytest
from PIL import Image
from pydantic import ValidationError

from viraldy.modules.smart_remake.engine.schemas import UploadedMedia
from viraldy.modules.smart_remake.project_contracts import (
    SmartRemakeBudgetPatch,
    SmartRemakeBudgetPolicy,
    SmartRemakeCharacterConsent,
    SmartRemakeIntakeRequest,
)
from viraldy.modules.smart_remake.project_intake import assert_input_binding, create_intake
from viraldy.modules.smart_remake.project_policy import (
    assert_project_policy,
    constraints_hash,
    context_with_requirements,
    context_with_rights,
    context_with_rights_review,
    policy_hash,
)
from viraldy.shared.errors.base import AppError, NotFoundError


def intake_payload(**updates):
    declaration = {
        "basis": "owned",
        "scope": "analysis, generation and commercial export",
        "declared": True,
        "evidenceNote": "Seller created the source and holds product asset rights.",
    }
    return SmartRemakeIntakeRequest.model_validate(
        {
            "idempotencyKey": "seller-intake-1",
            "projectName": "Seller test",
            "targetDuration": 8,
            "requirements": {"intent": "Show exact product", "keep": ["packaging"]},
            "rights": {
                "source": declaration,
                "product": declaration,
                "providerDisclosureAcknowledged": True,
            },
            "budget": {"capUsd": "5.00", "maxAttempts": 12, "maxDurationSeconds": 1800},
            **updates,
        }
    )


class MemoryRepository:
    def __init__(self):
        self.rows = {}

    async def project(self, workspace_id, project_id, **_):
        row = self.rows.get(project_id)
        if row is None or row.workspace_id != workspace_id:
            raise NotFoundError("SMART_REMAKE_PROJECT_NOT_FOUND")
        return row

    async def create(self, row):
        self.rows[row.id] = row


class MemoryMedia:
    def __init__(self):
        self.objects = {}
        self.storage = SimpleNamespace(delete_object=lambda key: self.objects.pop(key, None))

    async def put(self, prefix, data, mime_type):
        key = f"{prefix}/{uuid4()}"
        self.objects[key] = data
        return key

    async def read(self, key):
        return self.objects[key]


def image_upload():
    output = io.BytesIO()
    Image.new("RGB", (4, 4), "red").save(output, format="PNG")
    return UploadedMedia(bytes=output.getvalue(), mime_type="image/png")


def source_upload():
    return UploadedMedia(bytes=b"\x00\x00\x00\x18ftypisomsource", mime_type="video/mp4")


@pytest.fixture
async def intake():
    repository, media = MemoryRepository(), MemoryMedia()
    workspace, actor = uuid4(), uuid4()
    row = await create_intake(
        repository, media, workspace, actor, intake_payload(), source_upload(), image_upload()
    )
    return repository, media, workspace, actor, row


@pytest.mark.asyncio
async def test_intake_retains_owned_inputs_and_hashes_without_model_calls(intake):
    repository, media, workspace, actor, row = intake
    assert len(repository.rows) == 1
    assert row.state_json["phase"] == "intake"
    assert row.state_json["targetDuration"] == 8
    assert row.context_json["p0"]["actorId"] == str(actor)
    assert row.context_json["p0"]["rights"]["source"]["verification"]["status"] == "declared"
    assert row.context_json["p0"]["budgetPolicy"]["capUsd"] == "5.00"
    assert all(key.startswith(f"workspaces/{workspace}/") for key in media.objects)
    await assert_input_binding(row, media)
    assert_project_policy(row, purpose="analysis")


@pytest.mark.asyncio
async def test_intake_replay_is_scoped_to_workspace_actor_and_input(intake):
    repository, media, workspace, actor, row = intake
    replay = await create_intake(
        repository, media, workspace, actor, intake_payload(), source_upload(), image_upload()
    )
    assert replay.id == row.id
    assert len(media.objects) == 2
    with pytest.raises(AppError) as conflict:
        await create_intake(
            repository,
            media,
            workspace,
            actor,
            intake_payload(projectName="Changed"),
            source_upload(),
            image_upload(),
        )
    assert conflict.value.code == "SMART_REMAKE_IDEMPOTENCY_CONFLICT"
    other = await create_intake(
        repository, media, uuid4(), actor, intake_payload(), source_upload(), image_upload()
    )
    assert other.id != row.id
    other_actor = await create_intake(
        repository, media, workspace, uuid4(), intake_payload(), source_upload(), image_upload()
    )
    assert other_actor.id != row.id


@pytest.mark.asyncio
async def test_input_binding_detects_changed_bytes_and_missing_object(intake):
    _, media, _, _, row = intake
    media.objects[row.context_json["productKey"]] = b"tampered"
    with pytest.raises(AppError) as error:
        await assert_input_binding(row, media)
    assert error.value.code == "SMART_REMAKE_INPUT_CHANGED"
    del media.objects[row.context_json["productKey"]]
    with pytest.raises(AppError) as error:
        await assert_input_binding(row, media)
    assert error.value.code == "SMART_REMAKE_INPUT_UNAVAILABLE"


@pytest.mark.asyncio
async def test_character_requires_real_reference_and_separate_consent(intake):
    repository, media, workspace, actor, _ = intake
    payload = intake_payload(idempotencyKey="character")
    payload.requirements.requiresCharacter = True
    with pytest.raises(AppError) as error:
        await create_intake(
            repository, media, workspace, actor, payload, source_upload(), image_upload()
        )
    assert error.value.code == "SMART_REMAKE_CHARACTER_REFERENCE_REQUIRED"
    payload.rights.character = payload.rights.product.model_copy(deep=True)
    with pytest.raises(AppError) as error:
        await create_intake(
            repository,
            media,
            workspace,
            actor,
            payload,
            source_upload(),
            image_upload(),
            image_upload(),
        )
    assert error.value.code == "SMART_REMAKE_CHARACTER_CONSENT_REQUIRED"


@pytest.mark.parametrize("purpose", ["analysis", "generation", "inspection", "export"])
def test_policy_rejects_legacy_projects_before_paid_or_export_work(purpose):
    class Row:
        context_json = {}

    with pytest.raises(AppError) as error:
        assert_project_policy(Row(), purpose=purpose)
    assert error.value.code == "SMART_REMAKE_INTAKE_REQUIRED"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "change,code",
    [
        ("disclosure", "SMART_REMAKE_DISCLOSURE_REQUIRED"),
        ("revoked", "SMART_REMAKE_RIGHTS_REQUIRED"),
        ("evidence", "SMART_REMAKE_RIGHTS_EVIDENCE_REQUIRED"),
        ("deletion", "SMART_REMAKE_USE_STOPPED"),
    ],
)
async def test_policy_gate_uses_saved_rights_not_prompt(intake, change, code):
    *_, row = intake
    p0 = copy.deepcopy(row.context_json["p0"])
    if change == "disclosure":
        p0["rights"]["providerDisclosureAcknowledged"] = False
    elif change == "revoked":
        p0["rights"]["product"]["revoked"] = True
    elif change == "evidence":
        p0["rights"]["source"]["evidenceNote"] = ""
    else:
        p0["deletion"] = {"status": "requested"}
    row.context_json = {**row.context_json, "p0": p0}
    with pytest.raises(AppError) as error:
        assert_project_policy(row, purpose="generation")
    assert error.value.code == code


@pytest.mark.asyncio
async def test_requirements_and_rights_updates_preserve_history_and_invalidate_approval(intake):
    *_, row = intake
    context = copy.deepcopy(row.context_json)
    context["p0"]["assemblies"] = [{"id": "historic", "mediaHash": "abc"}]
    context["p0"]["release"] = {
        "approval": {"assemblyId": "historic"},
        "activeApprovalId": "approved-1",
        "approvals": [{"id": "approved-1"}],
        "exports": [{"id": "export-1"}],
    }
    original = copy.deepcopy(context)
    changed = intake_payload().requirements.model_copy(update={"intent": "New intent"})
    updated = context_with_requirements(context, changed)
    assert context == original
    assert updated["p0"]["assemblies"] == original["p0"]["assemblies"]
    assert updated["p0"]["release"]["approval"] is None
    assert updated["p0"]["release"]["activeApprovalId"] is None
    assert updated["p0"]["release"]["approvals"] == [{"id": "approved-1"}]
    assert updated["p0"]["release"]["exports"] == [{"id": "export-1"}]
    assert constraints_hash(updated) != constraints_hash(context)
    rights = intake_payload().rights.model_copy(deep=True)
    rights.product.revoked = True
    changed_rights = context_with_rights(context, rights, actor_id=uuid4())
    assert changed_rights["p0"]["release"]["approval"] is None
    assert changed_rights["p0"]["rights"]["product"]["revoked"]


@pytest.mark.parametrize(
    "field,value",
    [
        ("capUsd", 1.5),
        ("capUsd", "NaN"),
        ("capUsd", "0"),
        ("capUsd", "-1.00"),
        ("capUsd", "1e2"),
        ("capUsd", "1.1234567"),
        ("maxAttempts", True),
        ("maxAttempts", "5"),
        ("maxDurationSeconds", 0),
    ],
)
def test_budget_boundary_rejects_unbounded_or_ambiguous_values(field, value):
    budget = {"capUsd": "5.00", "maxAttempts": 12, "maxDurationSeconds": 1800, field: value}
    with pytest.raises(ValidationError):
        intake_payload(budget=budget)


def test_unlimited_budget_is_explicit_and_legacy_limits_serialize_unchanged():
    assert SmartRemakeBudgetPolicy().model_dump(mode="json") == {"mode": "unlimited"}
    assert SmartRemakeBudgetPolicy.model_validate({}).model_dump(mode="json") == {
        "mode": "unlimited"
    }
    legacy = {"capUsd": "5.00", "maxAttempts": 12, "maxDurationSeconds": 1800}
    assert SmartRemakeBudgetPolicy.model_validate(legacy).model_dump(mode="json") == legacy
    assert SmartRemakeBudgetPolicy.model_validate({"mode": "limited", **legacy}).model_dump(
        mode="json"
    ) == {"mode": "limited", **legacy}


@pytest.mark.parametrize("cap", [None, "", "  "])
def test_empty_new_budget_defaults_to_unlimited_without_hidden_finite_limits(cap):
    assert SmartRemakeBudgetPolicy.model_validate(
        {"capUsd": cap, "maxAttempts": 0, "maxDurationSeconds": 0}
    ).model_dump(mode="json") == {"mode": "unlimited"}


def test_explicit_unlimited_discards_unused_finite_fields_without_relaxing_extra_keys():
    assert SmartRemakeBudgetPolicy.model_validate(
        {
            "mode": "unlimited",
            "capUsd": "invalid",
            "maxAttempts": -1,
            "maxDurationSeconds": "unused",
        }
    ).model_dump(mode="json") == {"mode": "unlimited"}
    with pytest.raises(ValidationError):
        SmartRemakeBudgetPolicy.model_validate({"mode": "unlimited", "approved": True})
    with pytest.raises(ValidationError):
        SmartRemakeBudgetPolicy.model_validate({"mode": "unknown"})


@pytest.mark.parametrize(
    "budget",
    [
        {"mode": "limited"},
        {"mode": "limited", "capUsd": ""},
        {"mode": "limited", "capUsd": "0"},
        {"capUsd": "1", "maxAttempts": None},
        {"capUsd": "1", "maxDurationSeconds": None},
    ],
)
def test_explicit_or_legacy_limited_policy_still_requires_finite_controls(budget):
    with pytest.raises(ValidationError):
        SmartRemakeBudgetPolicy.model_validate(budget)


def test_unlimited_budget_patch_keeps_the_same_revision_and_idempotency_boundary():
    request = SmartRemakeBudgetPatch.model_validate(
        {
            "expectedRevision": 3,
            "idempotencyKey": "switch-to-unlimited",
            "budget": {"mode": "unlimited"},
        }
    )
    assert request.model_dump(mode="json") == {
        "expectedRevision": 3,
        "idempotencyKey": "switch-to-unlimited",
        "budget": {"mode": "unlimited"},
    }


@pytest.mark.asyncio
async def test_intake_without_budget_retains_unlimited_policy_and_replays_exactly():
    data = intake_payload().model_dump(mode="json")
    del data["budget"]
    payload = SmartRemakeIntakeRequest.model_validate(data)
    assert payload.budget.model_dump(mode="json") == {"mode": "unlimited"}
    repository, media = MemoryRepository(), MemoryMedia()
    workspace, actor = uuid4(), uuid4()
    row = await create_intake(
        repository, media, workspace, actor, payload, source_upload(), image_upload()
    )
    assert row.context_json["p0"]["budgetPolicy"] == {"mode": "unlimited"}
    assert_project_policy(row, purpose="analysis")
    replay = await create_intake(
        repository, media, workspace, actor, payload, source_upload(), image_upload()
    )
    assert replay.id == row.id
    assert len(media.objects) == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("policy", [None, {}, {"mode": "unlimited"}])
async def test_unlimited_policy_bypasses_only_financial_limits_and_preserves_rights(intake, policy):
    *_, row = intake
    row.context_json["p0"]["budgetPolicy"] = policy
    for purpose in ("analysis", "generation", "inspection", "export"):
        assert_project_policy(row, purpose=purpose)
    row.context_json["p0"]["rights"]["product"]["revoked"] = True
    with pytest.raises(AppError) as error:
        assert_project_policy(row, purpose="generation")
    assert error.value.code == "SMART_REMAKE_RIGHTS_REQUIRED"


def test_public_unlimited_policy_has_no_fake_remaining_amount_or_legacy_caps():
    from viraldy.modules.smart_remake.project_presentation import project_policy_fields

    for policy in (None, {}, {"mode": "unlimited", "capUsd": "5", "maxAttempts": 1}):
        result = project_policy_fields({"p0": {"budgetPolicy": policy}})
        assert result["budget"] == {"policy": {"mode": "unlimited"}}


def test_intake_does_not_accept_client_storage_keys_or_fake_verification():
    with pytest.raises(ValidationError):
        intake_payload(sourceKey="another-workspace/private")
    rights = intake_payload().rights.model_dump(mode="json")
    rights["source"]["verification"] = {"status": "verified"}
    with pytest.raises(ValidationError):
        intake_payload(rights=rights)


@pytest.mark.asyncio
async def test_character_reference_bytes_and_consent_are_bound_before_provider(intake):
    repository, media, workspace, actor, _ = intake
    payload = intake_payload(idempotencyKey="character-positive")
    payload.requirements.requiresCharacter = True
    payload.rights.character = payload.rights.product.model_copy(deep=True)
    payload.rights.characterConsent = SmartRemakeCharacterConsent(
        consented=True,
        scope="advertising and AI processing",
        evidenceNote="Signed consent recorded.",
    )
    row = await create_intake(
        repository,
        media,
        workspace,
        actor,
        payload,
        source_upload().bytes,
        image_upload().bytes,
        image_upload().bytes,
    )
    assert row.context_json["characterKey"]
    await assert_input_binding(row, media)
    assert_project_policy(row, purpose="generation")
    row.context_json["p0"]["requirements"]["requiresCharacter"] = False
    with pytest.raises(AppError) as missing_character_check:
        assert_project_policy(row, purpose="generation")
    assert missing_character_check.value.code == "SMART_REMAKE_CHARACTER_POLICY_REQUIRED"
    row.context_json["p0"]["requirements"]["requiresCharacter"] = True
    media.objects[row.context_json["characterKey"]] = b"changed character"
    with pytest.raises(AppError) as error:
        await assert_input_binding(row, media)
    assert error.value.code == "SMART_REMAKE_INPUT_CHANGED"


@pytest.mark.asyncio
async def test_saved_policy_character_requirement_and_budget_are_checked(intake):
    *_, row = intake
    original = copy.deepcopy(row.context_json)
    row.context_json["p0"]["requirements"]["requiresCharacter"] = True
    with pytest.raises(AppError) as error:
        assert_project_policy(row, purpose="analysis")
    assert error.value.code == "SMART_REMAKE_CHARACTER_REFERENCE_REQUIRED"
    row.context_json = original
    del row.context_json["p0"]["assets"]["product"]["storageKey"]
    with pytest.raises(AppError) as error:
        assert_project_policy(row, purpose="analysis")
    assert error.value.code == "SMART_REMAKE_INPUT_UNAVAILABLE"


@pytest.mark.asyncio
@pytest.mark.parametrize("cap", ["NaN", "invalid", "0", "-1"])
async def test_saved_budget_policy_cannot_be_nonfinite_or_unbounded(intake, cap):
    *_, row = intake
    row.context_json["p0"]["budgetPolicy"]["capUsd"] = cap
    with pytest.raises(AppError) as error:
        assert_project_policy(row, purpose="inspection")
    assert error.value.code == "SMART_REMAKE_BUDGET_REQUIRED"
    # Export uses the rights gate and the release gate, not a new paid reservation.
    assert_project_policy(row, purpose="export")


@pytest.mark.asyncio
async def test_human_rights_review_remains_distinct_from_verification(intake):
    *_, actor, row = intake
    context = row.context_json
    reviewed = context_with_rights_review(
        context, actor_id=actor, evidence_note=" Reviewed license. "
    )
    verification = reviewed["p0"]["rights"]["source"]["verification"]
    assert verification["status"] == "reviewed"
    assert verification["reviewedBy"] == str(actor)
    assert verification["evidenceNote"] == "Reviewed license."
    assert context["p0"]["rights"]["source"]["verification"]["status"] == "declared"
    assert policy_hash(reviewed) != policy_hash(context)
    with pytest.raises(AppError):
        context_with_rights_review(context, actor_id=actor, evidence_note=" ")


@pytest.mark.asyncio
async def test_requirements_noop_keeps_approval_and_new_character_needs_input(intake):
    *_, row = intake
    context = row.context_json
    original_hash = constraints_hash(context)
    assert context_with_requirements(context, intake_payload().requirements) == context
    new_requirements = intake_payload().requirements.model_copy(update={"requiresCharacter": True})
    with pytest.raises(AppError):
        context_with_requirements(context, new_requirements)
    assert constraints_hash(context) == original_hash


@pytest.mark.asyncio
@pytest.mark.parametrize("role", ["source", "product"])
async def test_intake_rejects_fake_media_before_storage(role):
    repository, media = MemoryRepository(), MemoryMedia()
    source, product = source_upload(), image_upload()
    if role == "source":
        source = UploadedMedia(bytes=b"not a video", mime_type="video/mp4")
    else:
        product = UploadedMedia(bytes=b"not an image", mime_type="image/png")
    with pytest.raises(AppError) as error:
        await create_intake(repository, media, uuid4(), uuid4(), intake_payload(), source, product)
    assert error.value.code == "UNSUPPORTED_SMART_REMAKE_MEDIA_TYPE"
    assert not media.objects
    assert not repository.rows


@pytest.mark.asyncio
async def test_storage_failure_removes_only_this_uncommitted_intake_objects():
    repository = MemoryRepository()

    class FailingMedia(MemoryMedia):
        async def put(self, prefix, data, mime_type):
            if self.objects:
                raise OSError("storage failed")
            return await super().put(prefix, data, mime_type)

    media = FailingMedia()
    with pytest.raises(OSError):
        await create_intake(
            repository, media, uuid4(), uuid4(), intake_payload(), source_upload(), image_upload()
        )
    assert not media.objects
    assert not repository.rows


@pytest.mark.asyncio
async def test_binding_rejects_legacy_key_swap_and_manifest_change(intake):
    *_, row = intake
    _, media, *_ = intake
    original = copy.deepcopy(row.context_json)
    row.context_json = {}
    with pytest.raises(AppError) as error:
        await assert_input_binding(row, media)
    assert error.value.code == "SMART_REMAKE_INTAKE_REQUIRED"
    row.context_json = copy.deepcopy(original)
    row.context_json["sourceKey"] = row.context_json["productKey"]
    with pytest.raises(AppError) as error:
        await assert_input_binding(row, media)
    assert error.value.code == "SMART_REMAKE_INPUT_CHANGED"
    row.context_json = original
    row.context_json["p0"]["inputHash"] = "wrong manifest"
    with pytest.raises(AppError) as error:
        await assert_input_binding(row, media)
    assert error.value.code == "SMART_REMAKE_INPUT_CHANGED"


@pytest.mark.parametrize("field", ["keep", "replace", "forbid", "claims"])
def test_requirements_cannot_include_blank_requirements(field):
    with pytest.raises(ValidationError):
        intake_payload(requirements={"intent": "Show product", field: ["  "]})
