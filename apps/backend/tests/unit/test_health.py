from __future__ import annotations

from typing import cast

import pytest
from fastapi import Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from viraldy.api.routers import health as health_module
from viraldy.platform.config.settings import Settings
from viraldy.platform.storage.ports import StoragePort


@pytest.mark.asyncio
async def test_dependency_health_reports_required_components_without_error_details(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def ok_postgres(db: AsyncSession) -> bool:
        return True

    async def failed_redis(settings: Settings) -> bool:
        raise RuntimeError("redis://user:secret@internal:6379")

    async def ok_storage(storage: StoragePort) -> bool:
        return True

    async def ok_worker() -> bool:
        return True

    monkeypatch.setattr(health_module, "check_postgres", ok_postgres)
    monkeypatch.setattr(health_module, "check_redis", failed_redis)
    monkeypatch.setattr(health_module, "check_object_storage", ok_storage)
    monkeypatch.setattr(health_module, "check_worker", ok_worker)

    report = await health_module.dependency_health(
        cast(AsyncSession, object()),
        Settings(),
        cast(StoragePort, object()),
    )

    assert report.status == "degraded"
    assert report.checks["api"].status == "ok"
    assert report.checks["postgres"].status == "ok"
    assert report.checks["redis"].status == "error"
    assert report.checks["object_storage"].status == "ok"
    assert report.checks["worker"].status == "ok"
    assert report.checks["ai_provider_configuration"].status == "ok"
    assert "secret" not in report.model_dump_json()
    assert "internal" not in report.model_dump_json()


@pytest.mark.asyncio
async def test_dependency_health_is_ready_when_every_required_check_passes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def always_ok(*args: object) -> bool:
        return True

    monkeypatch.setattr(health_module, "check_postgres", always_ok)
    monkeypatch.setattr(health_module, "check_redis", always_ok)
    monkeypatch.setattr(health_module, "check_object_storage", always_ok)
    monkeypatch.setattr(health_module, "check_worker", always_ok)

    report = await health_module.dependency_health(
        cast(AsyncSession, object()),
        Settings(ai_mode="fixture"),
        cast(StoragePort, object()),
    )

    assert report.status == "ok"
    assert all(check.status == "ok" for check in report.checks.values())


@pytest.mark.asyncio
async def test_readiness_excludes_worker_and_ai_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def always_ok(*args: object) -> bool:
        return True

    async def failed_worker() -> bool:
        raise RuntimeError("worker unavailable")

    monkeypatch.setattr(health_module, "check_postgres", always_ok)
    monkeypatch.setattr(health_module, "check_redis", always_ok)
    monkeypatch.setattr(health_module, "check_object_storage", always_ok)
    monkeypatch.setattr(health_module, "check_worker", failed_worker)

    report = await health_module.readiness_health(
        cast(AsyncSession, object()),
        Settings(ai_mode="live"),
        cast(StoragePort, object()),
    )

    assert report.status == "ok"
    assert set(report.checks) == {"api", "postgres", "redis", "object_storage"}


@pytest.mark.asyncio
async def test_health_routes_keep_readiness_separate_from_full_dependencies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def always_ok(*args: object) -> bool:
        return True

    async def failed_worker() -> bool:
        return False

    monkeypatch.setattr(health_module, "check_postgres", always_ok)
    monkeypatch.setattr(health_module, "check_redis", always_ok)
    monkeypatch.setattr(health_module, "check_object_storage", always_ok)
    monkeypatch.setattr(health_module, "check_worker", failed_worker)
    settings = Settings(ai_mode="live")

    readiness_response = Response()
    readiness = await health_module.ready(
        cast(AsyncSession, object()),
        settings,
        readiness_response,
        "request-ready",
    )
    dependencies_response = Response()
    dependencies = await health_module.dependencies(
        cast(AsyncSession, object()),
        settings,
        dependencies_response,
        "request-dependencies",
    )

    assert readiness_response.status_code == status.HTTP_200_OK
    assert readiness.data["status"] == "ok"
    assert dependencies_response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert dependencies.data["status"] == "degraded"


@pytest.mark.asyncio
async def test_live_health_does_not_call_dependencies() -> None:
    report = health_module.live_health()

    assert report.status == "ok"
    assert set(report.checks) == {"api"}
