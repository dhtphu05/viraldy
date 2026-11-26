"""Owned recompilation preserves history and terminates failed operations."""

import hashlib
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from viraldy.modules.smart_remake import timeline_compile as module
from viraldy.shared.errors.base import AppError


def compile_arguments():
    return dict(
        session=SimpleNamespace(commit=AsyncMock(), refresh=AsyncMock(),
                                scalars=AsyncMock(return_value=[])),
        settings=SimpleNamespace(ai_mode="live"),
        workspace_id=uuid4(),
        project_id=uuid4(),
        actor_id=uuid4(),
        expected_revision=1,
        idempotency_key="compile-once",
        mode="smart_remake",
        target_duration="8",
        aspect_ratio="9:16",
        language="vi",
        prompt=None,
        description=None,
        product_url=None,
        product_title=None,
        product_description=None,
        reference_video=None,
        product_image=None,
    )


def owned_compile(monkeypatch, *, revision=1, fresh=True, status="running"):
    from viraldy.modules.smart_remake import project_intake, project_policy

    row = SimpleNamespace(
        id=uuid4(),
        state_json={"revision": revision},
        context_json={
            "sourceKey": "source",
            "sourceMimeType": "video/mp4",
            "productKey": "product",
            "productMimeType": "image/png",
            "p0": {
                "targetDuration": 8,
                "requirements": {"intent": "Demo", "forbid": ["unproven claim"]},
            },
        },
    )
    operation = SimpleNamespace(id=uuid4(), status=status, result_json={})
    repo = SimpleNamespace(
        project=AsyncMock(return_value=row),
        start=AsyncMock(return_value=(row, operation, fresh)),
        finish=AsyncMock(),
    )
    monkeypatch.setattr(module, "RepairRepository", lambda _: repo)
    monkeypatch.setattr(
        module,
        "RepairMediaStore",
        lambda _: SimpleNamespace(
            read=AsyncMock(return_value=b"media"), url=AsyncMock(return_value="fresh-url")
        ),
    )
    monkeypatch.setattr(module, "S3StorageAdapter", lambda _: object())
    monkeypatch.setattr(project_intake, "assert_input_binding", AsyncMock())
    monkeypatch.setattr(project_policy, "assert_project_policy", lambda *a, **k: None)
    monkeypatch.setenv("SMART_REMAKE_ENABLED", "true")
    return row, operation, repo


@pytest.fixture(autouse=True)
def retained_opening_frame_bindings(monkeypatch):
    # These orchestration fixtures intentionally contain fake video buffers.
    # Real frame decoding and frame/hash binding have dedicated fidelity tests.
    monkeypatch.setattr(
        module,
        "source_opening_bindings",
        lambda source, scenes: {
            scene["id"]: {
                "sourceMediaHash": hashlib.sha256(source.bytes).hexdigest(),
                "frame": scene.get("startFrame", 0),
                "layoutHash": hashlib.sha256(
                    f"opening:{scene.get('startFrame', 0)}".encode()
                ).hexdigest(),
                "extractorVersion": "source-opening-frame-v1",
            }
            for scene in scenes
        },
    )


@pytest.mark.asyncio
async def test_revision_conflict_finishes_new_compile_without_analysis(monkeypatch):
    _, operation, repo = owned_compile(monkeypatch, revision=2)
    model = AsyncMock(side_effect=AssertionError("Revision rejected before AI"))
    monkeypatch.setattr(module, "analyze_reference_video", model)
    with pytest.raises(AppError, match="changed"):
        await module.compile_timeline_request(**compile_arguments())
    assert repo.finish.await_args.args[0] is operation
    assert repo.finish.await_args.args[1] == "failed"
    model.assert_not_awaited()


@pytest.mark.asyncio
async def test_decode_failure_closes_compile_and_preserves_previous_state(monkeypatch):
    row, operation, repo = owned_compile(monkeypatch)
    row.state_json["finalStorageKey"] = "previous-output"
    monkeypatch.setattr(module, "probe_media_bytes", lambda _: {"hasVideo": False})
    with pytest.raises(AppError):
        await module.compile_timeline_request(**compile_arguments())
    assert repo.finish.await_args.args[0] is operation
    assert repo.finish.await_args.args[1] == "failed"
    assert row.state_json["finalStorageKey"] == "previous-output"


@pytest.mark.asyncio
async def test_replayed_result_refreshes_owned_thumbnails_without_new_analysis(monkeypatch):
    row, operation, repo = owned_compile(monkeypatch, fresh=False, status="completed")
    row.context_json["sourceThumbnailKeys"] = {"s1": "thumb"}
    operation.result_json = {
        "compileResult": {
            "sourceSceneMap": {"scenes": [{"id": "s1", "thumbnailUrl": "expired-url"}]}
        }
    }
    result = await module.compile_timeline_request(**compile_arguments())
    assert result["sourceSceneMap"]["scenes"][0]["thumbnailUrl"] == "fresh-url"
    repo.finish.assert_not_awaited()


@pytest.mark.asyncio
async def test_initializer_cannot_restore_rights_revoked_during_thumbnail_upload(monkeypatch):
    from viraldy.modules.smart_remake import project_policy
    from viraldy.modules.smart_remake.engine.schemas import UploadedMedia

    original = SimpleNamespace(
        id=uuid4(),
        state_json={"revision": 1},
        context_json={
            "sourceKey": "source",
            "productKey": "product",
            "p0": {"rights": {"revoked": False}},
        },
    )
    latest = SimpleNamespace(
        id=original.id,
        state_json={"revision": 2},
        context_json={
            "sourceKey": "source",
            "productKey": "product",
            "p0": {"rights": {"revoked": True}},
        },
    )
    repo = SimpleNamespace(
        project=AsyncMock(return_value=latest),
        save=AsyncMock(),
        session=SimpleNamespace(commit=AsyncMock(), refresh=AsyncMock()),
    )

    def reject(row, **kwargs):
        if row.context_json["p0"]["rights"]["revoked"]:
            raise AppError("SMART_REMAKE_RIGHTS_REQUIRED", "Rights revoked", 403)

    monkeypatch.setattr(project_policy, "assert_project_policy", reject)
    result = {"sourceSceneMap": {"sourceFrameCount": 192, "scenes": [{"id": "s"}]}}
    media = SimpleNamespace(put=AsyncMock(return_value="owned-thumbnail"))
    with pytest.raises(AppError):
        await module.initialize_timeline_project(
            repository=repo,
            media=media,
            workspace_id=uuid4(),
            compile_result=result,
            source=UploadedMedia(bytes=b"source", mime_type="video/mp4"),
            product=UploadedMedia(bytes=b"product", mime_type="image/png"),
            source_probe={},
            thumbnails=[b"jpeg"],
            existing_project=original,
        )
    assert latest.context_json["p0"]["rights"]["revoked"] is True
    assert original.context_json["p0"]["rights"]["revoked"] is False
    assert repo.project.await_args.kwargs["lock"] is True


@pytest.mark.asyncio
async def test_partial_thumbnail_failure_retains_keys_on_latest_owned_context():
    from viraldy.modules.smart_remake.engine.schemas import UploadedMedia

    row = SimpleNamespace(
        id=uuid4(),
        state_json={"revision": 2},
        context_json={
            "sourceKey": "source",
            "productKey": "product",
            "p0": {"status": "suspended"},
        },
    )
    repo = SimpleNamespace(
        project=AsyncMock(return_value=row),
        session=SimpleNamespace(commit=AsyncMock(), refresh=AsyncMock()),
    )
    media = SimpleNamespace(put=AsyncMock(side_effect=["first-owned-thumb", OSError("storage")]))
    with pytest.raises(AppError) as failed:
        await module.initialize_timeline_project(
            repository=repo,
            media=media,
            workspace_id=uuid4(),
            compile_result={"sourceSceneMap": {"scenes": [{"id": "one"}, {"id": "two"}]}},
            source=UploadedMedia(bytes=b"source", mime_type="video/mp4"),
            product=UploadedMedia(bytes=b"product", mime_type="image/png"),
            source_probe={},
            thumbnails=[b"one", b"two"],
            existing_project=row,
        )
    assert failed.value.code == "SMART_REMAKE_RETENTION_UNAVAILABLE"
    assert row.context_json["p0"]["retainedMediaKeys"] == ["first-owned-thumb"]
    assert row.context_json["p0"]["status"] == "suspended"


@pytest.mark.asyncio
async def test_recompile_keeps_unassembled_candidates_and_same_input_objects(monkeypatch):
    from viraldy.modules.smart_remake import project_policy
    from viraldy.modules.smart_remake.engine.schemas import UploadedMedia
    from viraldy.modules.smart_remake.fixture import FixtureGeminiClient
    from viraldy.modules.smart_remake.timeline_planner import build_timeline_plan

    client = FixtureGeminiClient()
    result = module.build_timeline_compile(
        analysis=await client.generate_json(system_instruction="", prompt="8 seconds"),
        product_lock=await client.generate_json(system_instruction="", prompt="product lock"),
        plan=build_timeline_plan(
            target_duration=8, source_frame_count=192, reference_start_frame=0, cut_frames=[0, 192]
        ),
        language="vi",
        mode="smart_remake",
    )
    candidate = {
        "id": "unaccepted",
        "storageKey": "old-clip",
        "mediaHash": "exact-hash",
        "prompt": "saved prompt",
        "providerMetadata": {"providerRequestId": "receipt"},
    }
    row = SimpleNamespace(
        id=uuid4(),
        state_json={
            "revision": 5,
            "scenes": [{"id": "old-scene", "versions": [candidate]}],
            "finalStorageKey": "old-final",
        },
        context_json={
            "sourceKey": "owned-source",
            "productKey": "owned-product",
            "projectName": "Seller name",
            "sourceThumbnailKeys": {"old": "old-thumb"},
            "p0": {"release": {"activeApprovalId": "approval"}},
        },
    )

    async def save(current, state):
        current.state_json, current.revision = state, state["revision"]

    repo = SimpleNamespace(project=AsyncMock(return_value=row), save=save)
    media = SimpleNamespace(put=AsyncMock(return_value="new-thumb"))
    compile_operation_id = uuid4()
    monkeypatch.setattr(project_policy, "assert_project_policy", lambda *a, **k: None)
    updated = await module.initialize_timeline_project(
        repository=repo,
        media=media,
        workspace_id=uuid4(),
        compile_result=result,
        source=UploadedMedia(bytes=b"source", mime_type="video/mp4"),
        product=UploadedMedia(bytes=b"product", mime_type="image/png"),
        source_probe={},
        thumbnails=[b"jpeg"],
        existing_project=row,
        expected_revision=5,
        compile_operation_id=compile_operation_id,
    )
    assert updated is row
    assert row.revision == 6 and row.state_json["phase"] == "compiled"
    assert row.context_json["sourceKey"] == "owned-source"
    assert row.context_json["productKey"] == "owned-product"
    assert row.context_json["projectName"] == "Seller name"
    assert row.context_json["p0"]["planHistory"][0]["stateSnapshot"]["scenes"][0]["versions"] == [
        candidate
    ]
    assert row.context_json["p0"]["release"]["activeApprovalId"] is None
    assert row.context_json["p0"]["runtime"]["compileOperationId"] == str(compile_operation_id)
    assert row.state_json["finalStorageKey"] == "old-final"
    media.put.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["fixture", "mock"])
async def test_owned_fixture_compile_never_instantiates_paid_analysis(monkeypatch, mode):
    from viraldy.modules.smart_remake import budgeted_analysis

    row, _, _ = owned_compile(monkeypatch)
    args = compile_arguments()
    args["settings"] = SimpleNamespace(ai_mode=mode)
    args["session"] = SimpleNamespace(commit=AsyncMock(), refresh=AsyncMock(),
                                     scalars=AsyncMock(return_value=[]))
    monkeypatch.setattr(
        module, "probe_media_bytes", lambda _: {"hasVideo": True, "durationSeconds": 8}
    )
    monkeypatch.setattr(module, "measure_video_frames", lambda _: 192)
    monkeypatch.setattr(module, "extract_source_excerpt", lambda source, **k: source)
    monkeypatch.setattr(module, "extract_timeline_thumbnails", lambda *a: [])
    monkeypatch.setattr(module, "enrich_reference_analysis_with_detected_cuts", lambda a, b: a)

    def no_paid_client(*args, **kwargs):
        raise AssertionError("Fixture mode must not instantiate a paid analysis client")

    monkeypatch.setattr(budgeted_analysis, "LedgerGeminiClient", no_paid_client)

    async def initialized(**kwargs):
        row.revision = 2
        row.context_json["sourceThumbnailKeys"] = {}
        row.context_json["expectationsHash"] = "a" * 64
        return row

    monkeypatch.setattr(module, "initialize_timeline_project", initialized)
    result = await module.compile_timeline_request(**args)
    assert result["revision"] == 2
    assert result["projectId"] == str(row.id)


@pytest.mark.asyncio
@pytest.mark.parametrize("offset", [0, 288])
async def test_compile_commits_observed_progress_before_each_model_await(monkeypatch, offset):
    import copy

    from viraldy.modules.smart_remake.analysis_progress import public_analysis_progress
    from viraldy.modules.smart_remake.fixture import FixtureGeminiClient

    row, operation, repo = owned_compile(monkeypatch)
    args = compile_arguments()
    args["analysis_scope"] = "excerpt" if offset else "full_source"
    args["reference_start_frame"] = offset
    operation.idempotency_key = args["idempotency_key"]
    commits = []

    async def committed():
        commits.append(copy.deepcopy(operation.result_json))

    args["session"] = SimpleNamespace(commit=committed, refresh=AsyncMock(),
                                     scalars=AsyncMock(return_value=[]))
    args["settings"] = SimpleNamespace(ai_mode="fixture")
    monkeypatch.setattr(
        module,
        "probe_media_bytes",
        lambda _: {"hasVideo": True, "durationSeconds": 20 if offset else 8},
    )
    monkeypatch.setattr(
        module, "measure_video_frames", lambda data: 480 if offset and data == b"media" else 192
    )
    monkeypatch.setattr(
        module,
        "extract_source_excerpt",
        lambda *a, **k: module.UploadedMedia(bytes=b"excerpt", mime_type="video/mp4"),
    )
    monkeypatch.setattr(module, "extract_timeline_thumbnails", lambda *a: [])
    monkeypatch.setattr(module, "enrich_reference_analysis_with_detected_cuts", lambda a, b: a)
    source = {
        "sourceShots": [
            {
                "startSecond": 0,
                "endSecond": 8,
                "action": "Place the bottle on the table",
                "physicalAction": {"movement": "lower bottle"},
            }
        ]
    }

    async def analyze(**kwargs):
        progress = public_analysis_progress(operation)
        assert commits[-1]["kind"] == "compile"
        assert progress["stage"] == "analyzing_source" and progress["scenes"] == []
        assert progress["sourceDurationSeconds"] == (20 if offset else 8)
        assert "product" not in progress
        return source

    async def product(**kwargs):
        progress = public_analysis_progress(operation)
        assert commits[-1]["analysisProgress"]["stage"] == "identifying_product"
        if offset:
            assert "sceneCount" not in progress and progress["scenes"] == []
        else:
            assert progress["sceneCount"] == 1
            assert progress["scenes"][0]["action"] == "Place the bottle on the table"
        assert "product" not in progress
        return await FixtureGeminiClient().generate_json(
            system_instruction="", prompt="product lock"
        )

    async def initialized(**kwargs):
        progress = public_analysis_progress(operation)
        assert commits[-1]["analysisProgress"]["stage"] == "building_storyboard"
        assert progress["product"]["name"] == "Target Product"
        row.revision = 2
        row.context_json.update(sourceThumbnailKeys={}, expectationsHash="a" * 64)
        return row

    monkeypatch.setattr(module, "analyze_reference_video", analyze)
    monkeypatch.setattr(module, "generate_product_lock", product)
    monkeypatch.setattr(module, "initialize_timeline_project", initialized)
    await module.compile_timeline_request(**args)
    result = repo.finish.await_args.args[2]
    assert result["analysisProgress"]["stage"] == "completed"
    assert result["analysisProgress"]["requestKey"] == args["idempotency_key"]
    assert "compileResult" in result
    assert ("sourceAnalysisCheckpoint" in result) is not bool(offset)
