from __future__ import annotations

import asyncio
from typing import Annotated, Any

import redis.asyncio as redis
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from viraldy.api.dependencies.request import get_request_id
from viraldy.api.responses.envelope import Envelope, success
from viraldy.platform.config.settings import Settings, get_settings
from viraldy.platform.database.session import get_async_session

router = APIRouter(tags=["system"])
SettingsDep = Annotated[Settings, Depends(get_settings)]
DbDep = Annotated[AsyncSession, Depends(get_async_session)]


@router.get("/version", response_model=Envelope)
async def version(
    settings: SettingsDep,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    return success(
        {
            "app_name": settings.app_name,
            "app_version": settings.public_version,
            "environment": settings.app_env,
            "git_sha": settings.git_sha,
        },
        request_id,
    )


async def check_postgres(db: AsyncSession) -> bool:
    await asyncio.wait_for(db.execute(text("select 1")), timeout=2)
    return True


async def check_redis(settings: Settings) -> bool:
    client: Any = redis.from_url(  # type: ignore[no-untyped-call]
        settings.redis_url,
        socket_connect_timeout=1,
        socket_timeout=1,
    )
    try:
        await asyncio.wait_for(client.ping(), timeout=2)
        return True
    finally:
        await client.aclose()


async def readiness(db: AsyncSession, settings: Settings) -> dict[str, str]:
    checks: dict[str, str] = {}
    try:
        checks["postgres"] = "ok" if await check_postgres(db) else "error"
    except Exception:
        checks["postgres"] = "error"
    try:
        checks["redis"] = "ok" if await check_redis(settings) else "error"
    except Exception:
        checks["redis"] = "error"
    return checks


@router.get("/ready", response_model=Envelope)
async def ready(
    db: DbDep,
    settings: SettingsDep,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    checks = await readiness(db, settings)
    status = "ok" if all(value == "ok" for value in checks.values()) else "degraded"
    return success({"status": status, "checks": checks}, request_id)
