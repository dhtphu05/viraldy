from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import Annotated, Literal

import redis.asyncio as redis
from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from viraldy.api.dependencies.request import get_request_id
from viraldy.api.responses.envelope import Envelope, success
from viraldy.modules.ai_gateway.readiness import ai_readiness
from viraldy.platform.config.settings import Settings, get_settings
from viraldy.platform.database.session import get_async_session
from viraldy.platform.storage.ports import StoragePort
from viraldy.platform.storage.s3 import S3StorageAdapter

router = APIRouter(prefix="/health", tags=["health"])
SettingsDep = Annotated[Settings, Depends(get_settings)]
DbDep = Annotated[AsyncSession, Depends(get_async_session)]
CheckStatus = Literal["ok", "error"]


class ComponentHealth(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: CheckStatus
    latency_ms: int


class HealthReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["ok", "degraded"]
    checks: dict[str, ComponentHealth]


def live_health() -> HealthReport:
    return HealthReport(
        status="ok",
        checks={"api": ComponentHealth(status="ok", latency_ms=0)},
    )


async def check_postgres(db: AsyncSession) -> bool:
    await asyncio.wait_for(db.execute(text("select 1")), timeout=2)
    return True


async def check_redis(settings: Settings) -> bool:
    client = redis.from_url(  # type: ignore[no-untyped-call]
        settings.redis_url,
        socket_connect_timeout=1,
        socket_timeout=1,
    )
    try:
        await asyncio.wait_for(client.ping(), timeout=2)
        return True
    finally:
        await client.aclose()


async def check_object_storage(storage: StoragePort) -> bool:
    return await asyncio.wait_for(asyncio.to_thread(storage.check_health), timeout=2)


async def check_worker() -> bool:
    def ping() -> bool:
        from viraldy.worker.celery_app import celery_app

        inspector = celery_app.control.inspect(timeout=1)
        responses = inspector.ping() or {}
        return bool(responses)

    return await asyncio.wait_for(asyncio.to_thread(ping), timeout=2)


async def dependency_health(
    db: AsyncSession,
    settings: Settings,
    storage: StoragePort,
) -> HealthReport:
    checks = {
        "api": ComponentHealth(status="ok", latency_ms=0),
        "postgres": await _safe_check(lambda: check_postgres(db)),
        "redis": await _safe_check(lambda: check_redis(settings)),
        "object_storage": await _safe_check(lambda: check_object_storage(storage)),
        "worker": await _safe_check(check_worker),
        "ai_provider_configuration": _configuration_check(settings),
    }
    overall = "ok" if all(check.status == "ok" for check in checks.values()) else "degraded"
    return HealthReport(status=overall, checks=checks)


async def readiness_health(
    db: AsyncSession,
    settings: Settings,
    storage: StoragePort,
) -> HealthReport:
    checks = {
        "api": ComponentHealth(status="ok", latency_ms=0),
        "postgres": await _safe_check(lambda: check_postgres(db)),
        "redis": await _safe_check(lambda: check_redis(settings)),
        "object_storage": await _safe_check(lambda: check_object_storage(storage)),
    }
    overall = "ok" if all(check.status == "ok" for check in checks.values()) else "degraded"
    return HealthReport(status=overall, checks=checks)


async def worker_health() -> HealthReport:
    check = await _safe_check(check_worker)
    return HealthReport(
        status="ok" if check.status == "ok" else "degraded",
        checks={
            "api": ComponentHealth(status="ok", latency_ms=0),
            "worker": check,
        },
    )


async def _safe_check(check: Callable[[], Awaitable[bool]]) -> ComponentHealth:
    started = time.monotonic()
    try:
        healthy = await check()
    except Exception:
        healthy = False
    return ComponentHealth(
        status="ok" if healthy else "error",
        latency_ms=max(0, int((time.monotonic() - started) * 1000)),
    )


def _configuration_check(settings: Settings) -> ComponentHealth:
    return ComponentHealth(
        status="ok" if ai_readiness(settings).configured else "error",
        latency_ms=0,
    )


def _set_status(response: Response, report: HealthReport) -> None:
    response.status_code = (
        status.HTTP_200_OK
        if report.status == "ok"
        else status.HTTP_503_SERVICE_UNAVAILABLE
    )


@router.get("/live", response_model=Envelope)
async def live(request_id: str = Depends(get_request_id)) -> Envelope:
    return success(live_health().model_dump(mode="json"), request_id)


@router.get("/ready", response_model=Envelope)
async def ready(
    db: DbDep,
    settings: SettingsDep,
    response: Response,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    report = await readiness_health(db, settings, S3StorageAdapter(settings))
    _set_status(response, report)
    return success(report.model_dump(mode="json"), request_id)


@router.get("/dependencies", response_model=Envelope)
async def dependencies(
    db: DbDep,
    settings: SettingsDep,
    response: Response,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    report = await dependency_health(db, settings, S3StorageAdapter(settings))
    _set_status(response, report)
    return success(report.model_dump(mode="json"), request_id)


@router.get("/worker", response_model=Envelope)
async def worker(
    response: Response,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    report = await worker_health()
    _set_status(response, report)
    return success(report.model_dump(mode="json"), request_id)
