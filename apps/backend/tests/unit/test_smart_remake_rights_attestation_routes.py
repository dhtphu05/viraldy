"""Existing owned-intake routes accept the attestation and reject forged receipts."""

from __future__ import annotations

import json

import pytest

from tests.unit import test_smart_remake_rights_routes as routes
from tests.unit.test_smart_remake_rights import intake_payload
from tests.unit.test_smart_remake_rights_attestation import VERSION, attested_rights
from tests.unit.test_smart_remake_rights_routes import uploads

boundary = routes.boundary


@pytest.mark.asyncio
async def test_attestation_roundtrips_through_existing_intake_and_rights_routes(boundary):
    rights = attested_rights()
    response = await boundary.client.post(
        f"{boundary.base}/projects",
        data={"metadata": intake_payload(rights=rights.model_dump()).model_dump_json()},
        files=uploads(),
    )
    assert response.status_code == 200
    assert boundary.create.await_args.args[4].rights == rights
    response = await boundary.client.patch(
        f"{boundary.base}/projects/{boundary.project}/rights",
        json={"expectedRevision": 1, "idempotencyKey": "attest", "rights": rights.model_dump()},
    )
    assert response.status_code == 200
    assert boundary.patch.await_args.args[3].rights == rights


@pytest.mark.asyncio
@pytest.mark.parametrize("target", ["intake", "patch"])
@pytest.mark.parametrize("invalid", ["stale-version", "forged-receipt"])
async def test_invalid_attestation_fails_before_storage_or_mutation(boundary, target, invalid):
    rights = attested_rights().model_dump()
    if invalid == "stale-version":
        rights["attestation"]["policyVersion"] = "old-rights-v0"
    else:
        rights["attestation"]["acceptedBy"] = "sensitive-forged-actor"
    if target == "intake":
        payload = intake_payload().model_dump()
        payload["rights"] = rights
        response = await boundary.client.post(
            f"{boundary.base}/projects",
            data={"metadata": json.dumps(payload)},
            files=uploads(),
        )
    else:
        response = await boundary.client.patch(
            f"{boundary.base}/projects/{boundary.project}/rights",
            json={"expectedRevision": 1, "idempotencyKey": "invalid", "rights": rights},
        )
    assert response.status_code == 422
    assert "sensitive-forged-actor" not in response.text
    boundary.create.assert_not_awaited()
    boundary.patch.assert_not_awaited()


def test_rejected_and_revoked_attestations_remain_representable_for_saving():
    for attestation in (
        {"policyVersion": VERSION, "accepted": False},
        {"policyVersion": VERSION, "accepted": True, "revoked": True},
    ):
        rights = attested_rights(attestation=attestation)
        assert rights.attestation.accepted == attestation["accepted"]
