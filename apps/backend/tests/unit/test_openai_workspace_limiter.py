from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from redis.exceptions import RedisError

from viraldy.modules.ai_gateway.workspace_limiter import (
    RedisWorkspaceRequestLimiter,
    WorkspaceConcurrencyBusy,
    WorkspaceLimiterUnavailable,
)


class _FakeRedis:
    def __init__(self, acquire_results: list[int] | None = None) -> None:
        self.acquire_results = list(acquire_results or [1])
        self.eval_calls: list[tuple[object, ...]] = []
        self.released: list[tuple[str, str]] = []
        self.error: RedisError | None = None

    def eval(self, *args: object) -> int:
        if self.error is not None:
            raise self.error
        self.eval_calls.append(args)
        return self.acquire_results.pop(0) if self.acquire_results else 0

    def zrem(self, key: str, token: str) -> int:
        self.released.append((key, token))
        return 1


class _ConcurrentRedis:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._leases: dict[str, set[str]] = {}

    def eval(self, *args: object) -> int:
        key = str(args[2])
        limit = int(args[3])
        token = str(args[5])
        with self._lock:
            leases = self._leases.setdefault(key, set())
            if len(leases) >= limit:
                return 0
            leases.add(token)
            return 1

    def zrem(self, key: str, token: str) -> int:
        with self._lock:
            leases = self._leases.setdefault(key, set())
            removed = token in leases
            leases.discard(token)
            return int(removed)


def test_limiter_acquires_and_releases_workspace_lease() -> None:
    client = _FakeRedis()
    limiter = RedisWorkspaceRequestLimiter(client, poll_interval_seconds=0.01)
    workspace_id = uuid4()

    with limiter.slot(
        workspace_id,
        max_parallel=2,
        wait_timeout_seconds=1,
        lease_seconds=30,
    ):
        assert len(client.eval_calls) == 1

    assert len(client.released) == 1
    assert str(workspace_id) in client.released[0][0]


def test_limiter_times_out_without_oversubscribing_workspace() -> None:
    client = _FakeRedis([0, 0, 0])
    clock_values = iter([0.0, 0.0, 0.2, 0.5])

    limiter = RedisWorkspaceRequestLimiter(
        client,
        poll_interval_seconds=0.2,
        monotonic=lambda: next(clock_values),
        sleep=lambda _seconds: None,
    )

    with pytest.raises(WorkspaceConcurrencyBusy):
        with limiter.slot(
            uuid4(),
            max_parallel=1,
            wait_timeout_seconds=0.5,
            lease_seconds=30,
        ):
            pass

    assert client.released == []


def test_limiter_fails_closed_when_redis_is_unavailable() -> None:
    client = _FakeRedis()
    client.error = RedisError("private redis detail")
    limiter = RedisWorkspaceRequestLimiter(client)

    with pytest.raises(WorkspaceLimiterUnavailable) as exc_info:
        with limiter.slot(
            uuid4(),
            max_parallel=1,
            wait_timeout_seconds=1,
            lease_seconds=30,
        ):
            pass

    assert "private redis detail" not in str(exc_info.value)


def test_limiter_never_exceeds_same_workspace_parallel_limit() -> None:
    limiter = RedisWorkspaceRequestLimiter(
        _ConcurrentRedis(),
        poll_interval_seconds=0.001,
    )
    workspace_id = uuid4()
    release = threading.Event()
    condition = threading.Condition()
    active = 0
    peak = 0

    def run() -> None:
        nonlocal active, peak
        with limiter.slot(
            workspace_id,
            max_parallel=2,
            wait_timeout_seconds=2,
            lease_seconds=30,
        ):
            with condition:
                active += 1
                peak = max(peak, active)
                condition.notify_all()
            release.wait(timeout=2)
            with condition:
                active -= 1
                condition.notify_all()

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(run) for _ in range(3)]
        with condition:
            assert condition.wait_for(lambda: active == 2, timeout=2)
        release.set()
        for future in futures:
            future.result(timeout=2)

    assert peak == 2


def test_limiter_does_not_block_independent_workspaces() -> None:
    limiter = RedisWorkspaceRequestLimiter(
        _ConcurrentRedis(),
        poll_interval_seconds=0.001,
    )
    barrier = threading.Barrier(2)

    def run() -> None:
        with limiter.slot(
            uuid4(),
            max_parallel=1,
            wait_timeout_seconds=1,
            lease_seconds=30,
        ):
            barrier.wait(timeout=1)

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(run) for _ in range(2)]
        for future in futures:
            future.result(timeout=2)


def test_named_slot_serializes_the_same_analysis_claim() -> None:
    limiter = RedisWorkspaceRequestLimiter(
        _ConcurrentRedis(),
        poll_interval_seconds=0.001,
    )
    release = threading.Event()
    entered = threading.Event()

    def first() -> None:
        with limiter.named_slot(
            "media-analysis:workspace:request",
            max_parallel=1,
            wait_timeout_seconds=1,
            lease_seconds=30,
        ):
            entered.set()
            release.wait(timeout=1)

    with ThreadPoolExecutor(max_workers=2) as executor:
        first_future = executor.submit(first)
        assert entered.wait(timeout=1)
        second_future = executor.submit(
            lambda: _enter_named_slot(limiter, "media-analysis:workspace:request")
        )
        assert second_future.done() is False
        release.set()
        first_future.result(timeout=1)
        second_future.result(timeout=1)


def _enter_named_slot(limiter: RedisWorkspaceRequestLimiter, scope: str) -> None:
    with limiter.named_slot(
        scope,
        max_parallel=1,
        wait_timeout_seconds=1,
        lease_seconds=30,
    ):
        pass
