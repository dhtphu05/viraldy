"""Persisted compile checkpoints are readable during model work without side effects."""

from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from tests.integration.test_smart_remake_kie_workflow import kie_database_url
from viraldy.modules.identity.models import UserModel
from viraldy.modules.jobs.models import ProcessingJobModel
from viraldy.modules.smart_remake.analysis_progress import checkpoint_analysis
from viraldy.modules.smart_remake.budget_models import SmartRemakeAttemptModel
from viraldy.modules.smart_remake.models import SmartRemakeOperationModel, SmartRemakeProjectModel
from viraldy.modules.smart_remake.repair_repository import RepairRepository
from viraldy.modules.smart_remake.repair_service import RepairService
from viraldy.modules.workspaces.models import WorkspaceModel
from viraldy.shared.errors.base import NotFoundError


@pytest.fixture(scope="module")
def progress_database_url():
    yield from kie_database_url.__wrapped__()


async def test_separate_read_only_sessions_observe_checkpoints_and_terminal_result(
    progress_database_url,
):
    engine = create_async_engine(progress_database_url)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    actor, workspace, project_id = uuid4(), uuid4(), uuid4()
    source_audio = {
        "schemaVersion": 1, "speech": "present", "music": "present",
        "transcript": "Đây là chiếc bình của tôi.", "language": "vi", "pace": "medium",
    }
    try:
        async with sessions() as writer:
            writer.add(
                UserModel(id=actor, external_auth_id=str(actor), email=f"{actor}@progress.test")
            )
            await writer.flush()
            writer.add(
                WorkspaceModel(
                    id=workspace, name="Progress", slug=str(workspace), created_by_user_id=actor
                )
            )
            await writer.flush()
            writer.add(
                SmartRemakeProjectModel(
                    id=project_id,
                    workspace_id=workspace,
                    revision=1,
                    state_json={"provider": "unifically"},
                    context_json={"p0": {}},
                )
            )
            await writer.commit()
            operation = SmartRemakeOperationModel(
                project_id=project_id,
                idempotency_key="compile-current",
                request_hash="a" * 64,
                status="running",
                result_json={"receipt": {"requestId": "retained"}},
            )
            writer.add(operation)
            await writer.commit()

            async def read():
                async with sessions() as reader:
                    await reader.execute(text("SET TRANSACTION READ ONLY"))
                    service = RepairService(RepairRepository(reader), object(), workspace)
                    service.present = AsyncMock(return_value={"id": str(project_id)})
                    return await service.get(project_id)

            await checkpoint_analysis(
                writer,
                operation,
                "analyzing_source",
                request_key="compile-current",
                source_duration=10,
            )
            progress = (await read())["analysisProgress"]
            assert progress["stage"] == "analyzing_source" and progress["scenes"] == []
            await checkpoint_analysis(
                writer,
                operation,
                "identifying_product",
                request_key="compile-current",
                source_duration=10,
                analysis={
                    "sourceShots": [
                        {"startSecond": 0, "endSecond": 10, "action": "Set the product upright"}
                    ],
                    "sourceAudio": source_audio,
                },
            )
            progress = (await read())["analysisProgress"]
            assert (
                progress["sceneCount"] == 1
                and progress["scenes"][0]["action"] == "Set the product upright"
            )
            assert "product" not in progress
            assert progress["sourceAudio"] == source_audio
            await checkpoint_analysis(
                writer,
                operation,
                "completed",
                request_key="compile-current",
                product={"productName": "Orange box", "visualIdentity": {"colors": ["orange"]}},
            )
            await RepairRepository(writer).finish(operation, "completed", operation.result_json)
            progress = (await read())["analysisProgress"]
            assert progress["status"] == progress["stage"] == "completed"
            assert progress["product"] == {"name": "Orange box", "details": ["orange"]}
            assert progress["sourceAudio"] == source_audio
            assert operation.result_json["receipt"] == {"requestId": "retained"}
            async with sessions() as reader:
                with pytest.raises(NotFoundError):
                    await RepairService(RepairRepository(reader), object(), uuid4()).get(project_id)
                assert (
                    await reader.scalar(select(func.count()).select_from(SmartRemakeOperationModel))
                    == 1
                )
                assert (
                    await reader.scalar(select(func.count()).select_from(SmartRemakeAttemptModel))
                    == 0
                )
                assert (
                    await reader.scalar(select(func.count()).select_from(ProcessingJobModel)) == 0
                )
    finally:
        await engine.dispose()


async def test_concurrent_optional_and_main_progress_preserve_both_writers(progress_database_url):
    import asyncio

    from viraldy.modules.smart_remake.analysis_progress import publish_quick_summary

    engine = create_async_engine(progress_database_url)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    actor, workspace, project_id = uuid4(), uuid4(), uuid4()
    source_audio = {
        "schemaVersion": 1, "speech": "present", "music": "not_detected",
        "transcript": "Lời thoại từ phân tích đầy đủ.", "language": "vi",
    }
    try:
        async with sessions() as seed:
            seed.add(
                UserModel(id=actor, external_auth_id=str(actor), email=f"{actor}@summary.test")
            )
            await seed.flush()
            seed.add(
                WorkspaceModel(
                    id=workspace, name="Summary", slug=str(workspace), created_by_user_id=actor
                )
            )
            await seed.flush()
            seed.add(
                SmartRemakeProjectModel(
                    id=project_id,
                    workspace_id=workspace,
                    revision=1,
                    state_json={"provider": "kie"},
                    context_json={"p0": {}},
                )
            )
            await seed.commit()
            operation = SmartRemakeOperationModel(
                project_id=project_id,
                idempotency_key="concurrent-current",
                request_hash="b" * 64,
                status="running",
                result_json={},
            )
            seed.add(operation)
            await seed.commit()
            await checkpoint_analysis(
                seed, operation, "analyzing_source", request_key="concurrent-current"
            )
            operation_id = operation.id
        async with sessions() as main, sessions() as preview:
            main_op = await RepairRepository(main).operation(workspace, project_id, operation_id)
            preview_op = await RepairRepository(preview).operation(
                workspace, project_id, operation_id
            )
            await asyncio.gather(
                checkpoint_analysis(
                    main,
                    main_op,
                    "identifying_product",
                    request_key="concurrent-current",
                    analysis={
                        "sourceShots": [{
                            "startSecond": 0, "endSecond": 8, "action": "Open the product lid",
                        }],
                        "sourceAudio": source_audio,
                    },
                    result_updates={"sourceAnalysisCheckpoint": {"private": "retain"}},
                ),
                publish_quick_summary(
                    preview,
                    preview_op,
                    {
                        "status": "completed",
                        "summary": "Một sản phẩm được đặt trên bàn.",
                        "observations": [],
                        "sourceAudio": {**source_audio, "transcript": "Lời nghe nhanh."},
                    },
                ),
            )
            async with sessions() as reader:
                current = await RepairRepository(reader).operation(
                    workspace, project_id, operation_id
                )
                assert current.result_json["sourceAnalysisCheckpoint"] == {"private": "retain"}
                assert current.result_json["analysisProgress"]["stage"] == "identifying_product"
                assert (
                    current.result_json["analysisProgress"]["quickSummary"]["status"] == "completed"
                )
                assert current.result_json["analysisProgress"]["sourceAudio"] == source_audio
                assert current.result_json["analysisProgress"]["quickSummary"]["sourceAudio"][
                    "transcript"
                ] == "Lời nghe nhanh."
            await checkpoint_analysis(
                main,
                main_op,
                "completed",
                request_key="concurrent-current",
                result_updates={"compileResult": {"projectId": str(project_id)}},
            )
            assert not await publish_quick_summary(
                preview, preview_op, {"status": "completed", "summary": "Late overwrite"}
            )
            async with sessions() as reader:
                current = await RepairRepository(reader).operation(
                    workspace, project_id, operation_id
                )
                assert current.status == "completed" and current.result_json["compileResult"][
                    "projectId"
                ] == str(project_id)
                assert (
                    current.result_json["analysisProgress"]["quickSummary"]["summary"]
                    == "Một sản phẩm được đặt trên bàn."
                )
                assert current.result_json["analysisProgress"]["sourceAudio"] == source_audio
    finally:
        await engine.dispose()
