"""A changed wire protocol creates a distinct intent; stored tasks only reconcile."""
import pytest

from tests.unit.test_smart_remake_kie_workflow_unit import workflow as workflow_fixture
from viraldy.modules.smart_remake import kie_workflow as module


@pytest.fixture(name="workflow")
def setup_workflow(monkeypatch):
    return workflow_fixture.__wrapped__(monkeypatch)


@pytest.mark.asyncio
@pytest.mark.parametrize("contract", [None, "veo-native-v1"])
async def test_video_wire_contract_is_bound_before_submission_without_changing_legacy_hash(
    workflow, monkeypatch, contract,
):
    runner, repair, client, row, operation = workflow
    if contract:
        client.api_contract = contract
    reservations = []

    async def reserve(*args, **kwargs):
        reservations.append(kwargs)
        return None, True

    monkeypatch.setattr(module, "reserve_generation_attempt", reserve)
    await runner.execute(row.id, operation.id)
    request = client.submits[0]
    task = operation.result_json["tasks"]["0"]
    legacy = module._fingerprint({
        "model": request["model"],
        "input": {key: value for key, value in request["input_data"].items()
                  if key != "image_urls"},
        "productHash": row.context_json.get("productMediaHash"),
        "characterHash": row.context_json.get("characterMediaHash"),
        "imageHashes": [image["mediaHash"] for image in task["imageReferences"]],
        "expectationsHash": operation.result_json["expectationsHash"],
    })
    if contract:
        assert task["apiContract"] == contract
        assert reservations[0]["profile"]["apiContract"] == contract
        assert task["requestHash"] != legacy
        assert any(saved["tasks"].get("0", {}).get("apiContract") == contract
                   and saved["tasks"]["0"]["status"] == "submitting"
                   for saved in repair.repository.history)
    else:
        assert "apiContract" not in task
        assert task["requestHash"] == legacy
    assert len(client.submits) == 1


@pytest.mark.asyncio
async def test_wire_upgrade_reconciles_retained_task_without_submitting_another_request(workflow):
    runner, repair, client, row, operation = workflow
    client.fail_download = True
    with pytest.raises(RuntimeError):
        await runner.execute(row.id, operation.id)
    client.api_contract = "veo-native-v1"
    client.fail_download = False
    await runner.execute(row.id, operation.id)
    assert len(client.submits) == 1
    assert "apiContract" not in operation.result_json["tasks"]["0"]
