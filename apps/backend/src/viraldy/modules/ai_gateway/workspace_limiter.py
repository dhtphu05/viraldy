from __future__ import annotations

import secrets
import time
from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager
from functools import lru_cache
from typing import Protocol, cast
from uuid import UUID

import structlog
from redis import Redis
from redis.exceptions import RedisError

logger = structlog.get_logger(__name__)

_ACQUIRE_SCRIPT = """
local clock = redis.call('TIME')
local now_ms = (clock[1] * 1000) + math.floor(clock[2] / 1000)
redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', now_ms)
if redis.call('ZCARD', KEYS[1]) >= tonumber(ARGV[1]) then
  return 0
end
local expires_at = now_ms + tonumber(ARGV[2])
redis.call('ZADD', KEYS[1], expires_at, ARGV[3])
redis.call('PEXPIRE', KEYS[1], tonumber(ARGV[2]) + 1000)
return 1
"""


class _RedisClient(Protocol):
    def eval(self, script: str, numkeys: int, *keys_and_args: object) -> object: ...

    def zrem(self, name: str, *values: object) -> object: ...


class WorkspaceConcurrencyBusy(RuntimeError):
    def __init__(self) -> None:
        super().__init__("The workspace OpenAI concurrency limit is currently full.")


class WorkspaceLimiterUnavailable(RuntimeError):
    def __init__(self) -> None:
        super().__init__("The OpenAI workspace concurrency guardrail is unavailable.")


class WorkspaceRequestLimiter(Protocol):
    def slot(
        self,
        workspace_id: UUID,
        *,
        max_parallel: int,
        wait_timeout_seconds: float,
        lease_seconds: float,
    ) -> AbstractContextManager[None]: ...


class RedisWorkspaceRequestLimiter:
    def __init__(
        self,
        client: _RedisClient,
        *,
        poll_interval_seconds: float = 0.1,
        monotonic: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._client = client
        self._poll_interval_seconds = poll_interval_seconds
        self._monotonic = monotonic
        self._sleep = sleep

    @contextmanager
    def slot(
        self,
        workspace_id: UUID,
        *,
        max_parallel: int,
        wait_timeout_seconds: float,
        lease_seconds: float,
    ) -> Iterator[None]:
        with self.named_slot(
            f"openai:workspace:{workspace_id}",
            max_parallel=max_parallel,
            wait_timeout_seconds=wait_timeout_seconds,
            lease_seconds=lease_seconds,
        ):
            yield

    @contextmanager
    def named_slot(
        self,
        scope: str,
        *,
        max_parallel: int,
        wait_timeout_seconds: float,
        lease_seconds: float,
    ) -> Iterator[None]:
        key = f"viraldy:{scope}:leases"
        token = secrets.token_urlsafe(24)
        deadline = self._monotonic() + wait_timeout_seconds
        lease_ms = max(1000, round(lease_seconds * 1000))
        acquired = False
        while not acquired:
            try:
                acquired = bool(
                    self._client.eval(
                        _ACQUIRE_SCRIPT,
                        1,
                        key,
                        max_parallel,
                        lease_ms,
                        token,
                    )
                )
            except RedisError as exc:
                raise WorkspaceLimiterUnavailable() from exc
            if acquired:
                break
            remaining = deadline - self._monotonic()
            if remaining <= 0:
                raise WorkspaceConcurrencyBusy()
            self._sleep(min(self._poll_interval_seconds, remaining))

        try:
            yield
        finally:
            try:
                self._client.zrem(key, token)
            except RedisError:
                logger.warning(
                    "distributed_lease_release_failed",
                    scope=scope,
                )


@lru_cache(maxsize=16)
def redis_workspace_request_limiter(redis_url: str) -> RedisWorkspaceRequestLimiter:
    client: Redis = Redis.from_url(
        redis_url,
        decode_responses=True,
        socket_connect_timeout=3,
        socket_timeout=3,
    )
    return RedisWorkspaceRequestLimiter(cast(_RedisClient, client))
