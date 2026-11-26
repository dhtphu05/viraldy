"""Disposable real infrastructure for offline P0 browser acceptance.

Run with RUN_P0_SMART_REMAKE_BROWSER=1. Every service uses new containers/ports;
no existing local database, bucket or queue is reused. Child logs and Playwright
artifacts live under pytest's temporary root and are retained on failure.
"""

from __future__ import annotations

import contextlib
import json
import os
import secrets
import shutil
import socket
import subprocess
import sys
import time
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import boto3
import httpx
from testcontainers.core.container import DockerContainer
from testcontainers.postgres import PostgresContainer

from tests.e2e.smart_remake_media import generate_media

BACKEND = Path(__file__).resolve().parents[2]
WEB = BACKEND.parent / "web"


def child_environment() -> dict[str, str]:
    """Do not copy seller credentials, database settings or a user's .env."""
    allowed = ("PATH", "HOME", "TMPDIR", "LANG", "LC_ALL", "SYSTEMROOT")
    return {name: os.environ[name] for name in allowed if name in os.environ}


def _port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


@dataclass
class SmartRemakeBrowserStack:
    root: Path
    environment: dict[str, str] = field(default_factory=child_environment)
    processes: dict[str, subprocess.Popen[Any]] = field(default_factory=dict)
    base_url: str = ""
    api_url: str = ""
    media: dict[str, Path] = field(default_factory=dict)

    def spawn(self, name: str, command: list[str], cwd: Path) -> None:
        with (self.root / f"{name}.log").open("ab") as log:
            self.processes[name] = subprocess.Popen(  # noqa: S603 - fixed child commands only
                command,
                cwd=cwd,
                env=self.environment,
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )

    def stop(self, name: str) -> None:
        import signal

        process = self.processes.pop(name, None)
        if process is None:
            return
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            return
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            pass
        # The pnpm parent may exit before Vite children. Kill by process group
        # regardless of the leader's exit status, then reap the leader.
        with contextlib.suppress(ProcessLookupError):
            os.killpg(process.pid, signal.SIGKILL)
        process.wait(timeout=10)

    def start_worker(self) -> None:
        self.spawn(
            "worker",
            [sys.executable, "-m", "tests.e2e.smart_remake_server", "worker"],
            self.root,
        )

    def scenario(self, **values: Any) -> None:
        target = self.root / "scenario.json"
        current = json.loads(target.read_text()) if target.exists() else {}
        # Atomic replace lets API/worker readers observe complete fixture state.
        temporary = target.with_suffix(".next")
        temporary.write_text(json.dumps({**current, **values}))
        temporary.replace(target)

    def calls(self, stage: str | None = None) -> list[dict[str, Any]]:
        path = self.root / "provider-calls.jsonl"
        rows = [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []
        return [row for row in rows if stage is None or row["stage"] == stage]

    def wait_http(self, name: str, url: str, timeout: int = 60) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            process = self.processes[name]
            if process.poll() is not None:
                raise AssertionError(f"{name} exited; inspect {self.root / (name + '.log')}")
            try:
                if httpx.get(url, timeout=2).status_code < 500:
                    return
            except httpx.HTTPError:
                pass
            time.sleep(0.25)
        raise AssertionError(f"{name} failed readiness; inspect {self.root / (name + '.log')}")


@contextlib.contextmanager
def isolated_stack(root: Path) -> Iterator[SmartRemakeBrowserStack]:
    """No service URL overrides: stack ownership is a mandatory safety boundary."""
    root.mkdir(parents=True, exist_ok=True)
    stack = SmartRemakeBrowserStack(root)
    stack.media = generate_media(root / "media")
    stack.scenario(name="pass")
    api_port, web_port = _port(), _port()
    stack.api_url, stack.base_url = f"http://127.0.0.1:{api_port}", f"http://127.0.0.1:{web_port}"
    with contextlib.ExitStack() as resources:
        minio_password = secrets.token_urlsafe(32)
        postgres_container = PostgresContainer(
            "postgres:16.6-alpine",
            username="p0offline",
            password=secrets.token_urlsafe(32),
            dbname="p0offline",
        )
        redis_container = DockerContainer("redis:7.4-alpine")
        minio_container = (
            DockerContainer("minio/minio:RELEASE.2024-12-18T13-15-44Z")
            .with_env("MINIO_ROOT_USER", "p0offline")
            .with_env("MINIO_ROOT_PASSWORD", minio_password)
            .with_command("server /data")
        )
        # Docker SDK tuples bind an ephemeral host port to this interface only.
        for container, port in (
            (postgres_container, 5432),
            (redis_container, 6379),
            (minio_container, 9000),
        ):
            container.ports[port] = ("127.0.0.1", None)
        postgres = resources.enter_context(postgres_container)
        redis = resources.enter_context(redis_container)
        minio = resources.enter_context(minio_container)
        sync = postgres.get_connection_url().replace("postgresql+psycopg2", "postgresql+psycopg")
        redis_url = f"redis://127.0.0.1:{redis.get_exposed_port(6379)}"
        s3_url = f"http://127.0.0.1:{minio.get_exposed_port(9000)}"
        stack.environment.update(
            {
                "PYTHONPATH": os.pathsep.join((str(BACKEND / "src"), str(BACKEND))),
                "APP_ENV": "test",
                "AUTH_MODE": "password",
                "AUTH_DISABLED": "false",
                "AUTH_JWT_SECRET": secrets.token_urlsafe(48),
                "AUTH_PROXY_SECRET": secrets.token_urlsafe(48),
                "AUTH_PUBLIC_ORIGIN": stack.base_url,
                "VITE_API_BASE_URL": f"{stack.api_url}/api/v1",
                "DATABASE_URL": sync.replace("postgresql+psycopg", "postgresql+asyncpg"),
                "DATABASE_SYNC_URL": sync,
                "REDIS_URL": f"{redis_url}/0",
                "CELERY_BROKER_URL": f"{redis_url}/1",
                "CELERY_RESULT_BACKEND": f"{redis_url}/2",
                "S3_ENDPOINT_URL": s3_url,
                "S3_BUCKET": "p0-offline-browser",
                "S3_ACCESS_KEY_ID": "p0offline",
                "S3_SECRET_ACCESS_KEY": minio_password,
                "AWS_EC2_METADATA_DISABLED": "true",
                "AI_MODE": "live",
                "AI_PROVIDER": "openai_compatible",
                "SMART_REMAKE_ENABLED": "true",
                "OPENAI_API_KEY": "offline-constructor-seam-only",
                "KIE_API_KEY": "offline-constructor-seam-only",
                "GEMINI_API_KEY": "offline-constructor-seam-only",
                "SMART_REMAKE_P0_MAX_ANALYSIS_USD": "0.01",
                "SMART_REMAKE_P0_MAX_IMAGE_USD": "0.01",
                "SMART_REMAKE_P0_MAX_VIDEO_USD": "0.01",
                "SMART_REMAKE_P0_MAX_INSPECTION_USD": "0.01",
                "P0_E2E_OFFLINE": "1",
                "P0_E2E_MEDIA": str(root / "media"),
                "P0_E2E_SCENARIO": str(root / "scenario.json"),
                "P0_E2E_PROVIDER_LOG": str(root / "provider-calls.jsonl"),
                "BACKEND_CORS_ORIGINS": json.dumps([stack.base_url]),
                "PUBLIC_BASE_URL": stack.api_url,
                "KIE_POLL_INTERVAL_SECONDS": "0.01",
            }
        )
        client = boto3.client(
            "s3",
            endpoint_url=s3_url,
            aws_access_key_id="p0offline",
            aws_secret_access_key=minio_password,
            region_name="us-east-1",
        )
        deadline = time.monotonic() + 30
        while True:
            try:
                client.create_bucket(Bucket="p0-offline-browser")
                break
            except Exception:
                if time.monotonic() >= deadline:
                    raise
                time.sleep(0.25)
        # Absolute paths keep migrations working from a directory with no .env.
        config = root / "alembic.ini"
        config.write_text(
            (BACKEND / "alembic.ini")
            .read_text()
            .replace("script_location = alembic", f"script_location = {BACKEND / 'alembic'}")
            .replace("prepend_sys_path = src", f"prepend_sys_path = {BACKEND / 'src'}")
        )
        with (root / "migration.log").open("wb") as log:
            subprocess.run(  # noqa: S603 - fixed migration command and pytest-owned config
                [sys.executable, "-m", "alembic", "-c", str(config), "upgrade", "head"],
                cwd=root,
                env=stack.environment,
                check=True,
                stdout=log,
                stderr=subprocess.STDOUT,
                timeout=60,
            )
        try:
            stack.spawn(
                "api",
                [sys.executable, "-m", "tests.e2e.smart_remake_server", "api", str(api_port)],
                root,
            )
            stack.wait_http("api", f"{stack.api_url}/health/live")
            stack.start_worker()
            pnpm = shutil.which("pnpm")
            if pnpm is None:
                raise AssertionError("pnpm is required for the real frontend server")
            stack.spawn("web", [pnpm, "dev", "--host", "127.0.0.1", "--port", str(web_port)], WEB)
            stack.wait_http("web", f"{stack.base_url}/login")
            yield stack
        finally:
            errors = []
            for name in tuple(stack.processes):
                try:
                    stack.stop(name)
                except Exception as exc:
                    errors.append(exc)
            if errors:
                raise ExceptionGroup("P0 browser process cleanup failed", errors)
