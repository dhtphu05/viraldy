"""Project cards expose observed work without inventing completion or submissions."""

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy.dialects import postgresql

from tests.unit.test_smart_remake_generation_progress import fixture, image, video
from viraldy.modules.smart_remake import project_library as module


def test_project_card_uses_saved_compile_stage_and_keeps_private_payload_out():
    row, operation = fixture()
    operation.idempotency_key = str(uuid4())
    operation.result_json = {
        "kind": "compile",
        "analysisProgress": {
            "schemaVersion": 1,
            "stage": "identifying_product",
            "startedAt": operation.created_at.isoformat(),
            "updatedAt": operation.created_at.isoformat(),
            "scenes": [],
        },
        "providerPayload": {"private": "not a card field"},
    }
    activity = module._project_activity(row, [operation], [])
    assert activity["stage"] == "identifying_product"
    assert activity["kind"] == "compile"
    assert activity["status"] == "running"
    assert "providerPayload" not in activity and "plannedVideoCount" not in activity


@pytest.mark.parametrize("completed", [False, True])
def test_project_card_counts_provider_windows_and_verified_clips(completed):
    row, operation = fixture()
    image(row, operation, 0)
    image(row, operation, 1)
    operation.result_json["referencePreparation"] = "direct"
    attempt = video(row, operation, status="completed" if completed else "submitted")
    group = operation.result_json["renderPlan"]["groups"][0]
    if completed:
        for scene in row.state_json["scenes"]:
            if scene["id"] in group["renderUnitIds"]:
                scene["versions"] = [
                    {
                        "technicalCheck": {"status": "passed"},
                        "expectationsHash": operation.result_json["expectationsHash"],
                        "providerMetadata": {
                            "providerRequestId": attempt.provider_task_id,
                            "renderGroupId": group["id"],
                        },
                    }
                ]
    activity = module._project_activity(row, [operation], [attempt])
    assert activity["plannedVideoCount"] == 2
    assert activity["submittedVideoCount"] == 1
    assert activity["completedVideoCount"] == int(completed)
    assert activity["completedImageCount"] == 2
    assert activity["stage"] == ("completed" if completed else "generating")


@pytest.mark.parametrize("proof", [False, True])
def test_project_card_keeps_uncertain_submission_distinct_from_zero(proof):
    row, operation = fixture()
    attempt = video(row, operation, proof=proof)
    activity = module._project_activity(row, [operation], [attempt])
    assert activity["submittedVideoCount"] == (1 if proof else None)
    assert activity["completedVideoCount"] == 0


@pytest.mark.parametrize(
    "code,visible",
    [
        ("OPENAI_IMAGE_CREDITS_EXHAUSTED", True),
        ("https://provider.test/private?key=secret", False),
        ("X" * 121, False),
    ],
)
def test_project_card_failure_exposes_only_a_bounded_error_identifier(code, visible):
    row, operation = fixture()
    operation.status = "failed"
    operation.result_json.update(errorCode=code, needsReconciliation=True)
    activity = module._project_activity(row, [operation], [])
    assert activity["status"] == "failed"
    assert activity["needsReconciliation"] is True
    assert ("errorCode" in activity) is visible
    assert activity["completedVideoCount"] == 0


@pytest.mark.asyncio
async def test_activity_batch_reads_only_selected_projects_and_workspace_attempts(monkeypatch):
    row, operation = fixture()
    other, other_operation = fixture()
    other.workspace_id = row.workspace_id
    attempt = video(row, operation)
    statements = []

    async def execute(statement):
        statements.append(statement)
        values = [operation, other_operation] if len(statements) == 1 else [attempt]
        return SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: values))

    db = SimpleNamespace(execute=AsyncMock(side_effect=execute), commit=AsyncMock())
    monkeypatch.setattr(
        module, "service_for", lambda *args: pytest.fail("No service on activity read")
    )
    result = await module._project_activities(db, row.workspace_id, [row, other])
    assert result[row.id]["submittedVideoCount"] == 1
    assert result[other.id]["submittedVideoCount"] == 0
    assert set(result) == {row.id, other.id}
    assert len(statements) == 2
    operation_sql, attempt_sql = [
        statement.compile(dialect=postgresql.dialect()) for statement in statements
    ]
    assert str(operation_sql).count("SELECT") == 1
    assert operation_sql.params["project_id_1"] == [row.id, other.id]
    assert attempt_sql.params["project_id_1"] == [row.id, other.id]
    assert attempt_sql.params["workspace_id_1"] == row.workspace_id
    db.commit.assert_not_awaited()
