"""Offline provider constructor seams used by real API and Celery child processes.

Never replace an API route, lifecycle service, project, ledger, storage or media
transform here. The socket guard also makes a missed provider seam fail closed.
"""

from __future__ import annotations

import fcntl
import hashlib
import importlib
import ipaddress
import json
import os
import socket
import sys
from pathlib import Path
from typing import Any
from uuid import uuid4


def local_address(host: str) -> bool:
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def install_network_guard() -> None:
    original_connect = socket.socket.connect
    original_connect_ex = socket.socket.connect_ex
    original_resolve = socket.getaddrinfo

    def check(address: Any) -> None:
        if isinstance(address, tuple) and not local_address(str(address[0])):
            raise RuntimeError("Offline Smart Remake E2E forbids external network connections.")

    def connect(sock: socket.socket, address: Any) -> Any:
        check(address)
        return original_connect(sock, address)

    def connect_ex(sock: socket.socket, address: Any) -> Any:
        check(address)
        return original_connect_ex(sock, address)

    def resolve(host: Any, *args: Any, **kwargs: Any) -> Any:
        if host is not None and not local_address(str(host)):
            raise RuntimeError("Offline Smart Remake E2E forbids external DNS lookup.")
        return original_resolve(host, *args, **kwargs)

    socket.socket.connect = connect
    socket.socket.connect_ex = connect_ex
    socket.getaddrinfo = resolve


def _record(stage: str, **data: Any) -> None:
    target = Path(os.environ["P0_E2E_PROVIDER_LOG"])
    with target.open("a+") as output:
        fcntl.flock(output.fileno(), fcntl.LOCK_EX)
        output.seek(0)
        previous = [json.loads(line) for line in output.read().splitlines()]
        if data.get("attemptId") and any(
            row.get("attemptId") == data["attemptId"] for row in previous
        ):
            raise AssertionError("One paid attempt cannot authorize a repeated provider submission")
        output.write(json.dumps({"stage": stage, "mode": "fixture", **data}) + "\n")
        output.flush()


def _scenario() -> dict[str, Any]:
    return json.loads(Path(os.environ["P0_E2E_SCENARIO"]).read_text())


def _assert_ledger(stage: str, request_hash: str) -> str:
    import psycopg

    url = os.environ["DATABASE_SYNC_URL"].replace("postgresql+psycopg://", "postgresql://")
    with psycopg.connect(url) as connection:
        found = connection.execute(
            "SELECT id FROM smart_remake_attempts WHERE stage = %s AND request_hash = %s "
            "AND status IN ('reserved', 'submitted') ORDER BY created_at DESC LIMIT 1",
            (stage, request_hash),
        ).fetchone()
    if not found:
        raise AssertionError(f"Provider {stage} called without a committed reservation")
    return str(found[0])


def _submitted_provider_bindings(stage: str) -> list[dict[str, Any]]:
    """Read pending operation inputs through their own committed ledger reservation."""
    import psycopg

    url = os.environ["DATABASE_SYNC_URL"].replace("postgresql+psycopg://", "postgresql://")
    with psycopg.connect(url) as connection:
        rows = connection.execute(
            "SELECT a.request_hash, p.context_json, o.result_json, a.id "
            "FROM smart_remake_attempts a "
            "JOIN smart_remake_operations o ON o.id::text = a.metadata_json->>'operationId' "
            "AND o.project_id = a.project_id "
            "JOIN smart_remake_projects p ON p.id = a.project_id "
            "AND p.workspace_id = a.workspace_id "
            "WHERE a.stage = %s AND a.status IN ('reserved', 'submitted') "
            "AND o.status = 'running' ORDER BY a.created_at DESC",
            (stage,),
        ).fetchall()
    return [
        {"requestHash": request_hash, "context": context, "result": result,
         "attemptId": str(attempt_id)}
        for request_hash, context, result, attempt_id in rows
    ]


def _bound_prompt_value(prompt: str, prefix: str, *, last: bool = False) -> str:
    values = [line.removeprefix(prefix).strip()
              for line in prompt.splitlines() if line.startswith(prefix)]
    if not values:
        raise AssertionError("Offline provider request has no canonical expectations binding")
    return values[-1] if last else values[0]


class OfflineGeminiClient:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.max_attempts, self.repair_json = 1, False
        self.last_request_id: str | None = None
        self.last_usage = {"inputTokenCount": 21, "outputTokenCount": 17}

    async def generate_json(
        self, *, system_instruction: str, prompt: str, media: list[dict[str, Any]] | None = None
    ) -> Any:
        from viraldy.modules.smart_remake.budgeted_analysis import request_snapshot
        from viraldy.modules.smart_remake.fixture import FixtureGeminiClient
        from viraldy.modules.smart_remake.project_policy import stable_hash

        try:
            inspection_payload = json.loads(prompt)
        except json.JSONDecodeError:
            inspection_payload = {}
        inspection = bool(inspection_payload.get("observations"))
        stage = "inspection" if inspection else "analysis"
        request_hash = stable_hash(request_snapshot(system_instruction, prompt, media))
        attempt_id = _assert_ledger(stage, request_hash)
        self.last_request_id = f"offline-{uuid4()}"
        _record(
            stage,
            attemptId=attempt_id,
            requestHash=request_hash,
            requestId=self.last_request_id,
            inputHashes=[hashlib.sha256(item["bytes"]).hexdigest() for item in media or []],
        )
        if inspection:
            from io import BytesIO

            from PIL import Image

            observations = inspection_payload["observations"]
            if len(observations) != len(media or []):
                raise AssertionError("Inspector attachments must match its observed frame IDs")
            # Cite only observations actually attached to this provider request.
            # Real Inspector still validates hash/range/coverage and applies rules.
            failed = False
            for observation, attachment in zip(observations, media or [], strict=True):
                image_bytes = attachment["bytes"]
                if hashlib.sha256(image_bytes).hexdigest() != observation["imageHash"]:
                    raise AssertionError("Inspector attachment does not match its observation hash")
                if observation["mediaId"] == "subject" and _scenario().get("inspectionFailure"):
                    with Image.open(BytesIO(image_bytes)) as image:
                        red, green, blue = image.convert("RGB").getpixel(
                            (image.width // 2, int(image.height * 0.47))
                        )
                    failed |= blue > red * 1.3 and blue > green * 1.1
            return {
                "findings": [
                    {
                        "requirementId": rule["id"],
                        "status": "failed"
                        if failed and rule["category"] == "product"
                        else "passed",
                        "observed": "Fixture: blue box differs from original orange product."
                        if failed and rule["category"] == "product"
                        else "Offline fixture: original orange product visible in attached frames.",
                        "observationIds": [item["id"] for item in observations],
                    }
                    for rule in inspection_payload["requirements"]
                ]
            }
        return await FixtureGeminiClient().generate_json(
            system_instruction=system_instruction,
            prompt=prompt,
            media=media,
        )


class OfflineImageClient:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        pass

    async def edit(self, **kwargs: Any) -> dict[str, Any]:
        from io import BytesIO

        from PIL import Image

        snapshot = {key: kwargs[key] for key in ("prompt", "model", "quality")}
        snapshot.update(
            size="720x1280",
            expectationsHash=_bound_prompt_value(kwargs["prompt"], "EXPECTATIONS HASH:"),
            openingFrame=json.loads(_bound_prompt_value(
                kwargs["prompt"], "SOURCE OPENING BINDING:",
            ))["openingFrame"],
        )
        conditioning = json.loads(_bound_prompt_value(kwargs["prompt"], "CONDITIONING FRAME:"))
        snapshot["frameRole"] = conditioning.pop("frameRole")
        snapshot["referenceFrame"] = conditioning
        for key in ("product", "layout", "character"):
            if kwargs.get(key) is not None:
                with Image.open(BytesIO(kwargs[key].bytes)) as image:
                    image.verify()
                snapshot[f"{key}Hash"] = hashlib.sha256(kwargs[key].bytes).hexdigest()
        if snapshot["referenceFrame"]["layoutHash"] != snapshot["layoutHash"]:
            raise AssertionError("Offline image layout differs from its source frame binding")
        policy = _bound_prompt_value(kwargs["prompt"], "PRESENTER IDENTITY POLICY:")
        matching = []
        for binding in _submitted_provider_bindings("image"):
            result = binding["result"]
            if result.get("expectationsHash") != snapshot["expectationsHash"]:
                continue
            for intent in result.get("images", {}).values():
                actor = intent.get("presenterIdentity") or {}
                if (
                    intent.get("status") != "submitting"
                    or intent.get("requestHash") != binding["requestHash"]
                    or intent.get("attemptId") != binding["attemptId"]
                    or intent.get("referenceFrame") != snapshot["referenceFrame"]
                    or intent.get("frameRole") != snapshot["frameRole"]
                    or actor.get("policyVersion") != policy
                    or actor.get("productMediaHash") != snapshot["productHash"]
                    or actor.get("sourceMediaHash") != conditioning["sourceMediaHash"]
                    or (actor.get("anchor") and actor["anchor"]["mediaHash"]
                        != snapshot.get("characterHash"))
                ):
                    continue
                bound_snapshot = {**snapshot, "presenterIdentity": actor}
                if "complexity" in intent:
                    bound_snapshot["complexity"] = kwargs["complexity"]
                actual_hash = hashlib.sha256(
                    json.dumps(bound_snapshot, sort_keys=True).encode()
                ).hexdigest()
                if actual_hash == binding["requestHash"]:
                    matching.append((actual_hash, binding["attemptId"]))
        if len(matching) != 1:
            raise AssertionError("Offline image inputs do not match one committed provider attempt")
        request_hash, committed_attempt = matching[0]
        attempt_id = _assert_ledger("image", request_hash)
        if attempt_id != committed_attempt:
            raise AssertionError("Offline image reservation belongs to a different attempt")
        data = Path(os.environ["P0_E2E_MEDIA"], "conditioning.png").read_bytes()
        _record(
            "image",
            attemptId=attempt_id,
            requestHash=request_hash,
            inputHash=hashlib.sha256(kwargs["product"].bytes).hexdigest(),
        )
        return {
            "bytes": data,
            "mimeType": "image/png",
            "mediaHash": hashlib.sha256(data).hexdigest(),
            "model": kwargs.get("model"),
            "usage": {"input_tokens": 21, "output_tokens": 17},
            "requestId": f"offline-{uuid4()}",
        }


class OfflineKieClient:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.uploads: dict[str, dict[str, str]] = {}

    async def upload_file(self, media: Any) -> str:
        media_hash = hashlib.sha256(media.bytes).hexdigest()
        url = f"https://8.8.8.8/offline-{media_hash}.png"
        self.uploads[url] = {"hash": media_hash, "role": media.file_name}
        return url

    async def create_task(self, *, model: str, input_data: dict[str, Any]) -> dict[str, Any]:
        uploads = [self.uploads[url] for url in input_data["image_urls"]]
        matching = []
        for binding in _submitted_provider_bindings("video"):
            context, result = binding["context"], binding["result"]
            for intent in result.get("tasks", {}).values():
                if (
                    intent.get("status") != "submitting"
                    or intent.get("requestHash") != binding["requestHash"]
                    or intent.get("attemptId") != binding["attemptId"]
                    or intent.get("expectationsHash") != result.get("expectationsHash")
                ):
                    continue
                snapshot = {
                    "model": model,
                    "input": {key: value for key, value in input_data.items()
                              if key != "image_urls"},
                    "productHash": context.get("productMediaHash"),
                    "characterHash": context.get("characterMediaHash"),
                    "imageHashes": [item["hash"] for item in uploads],
                    "expectationsHash": result["expectationsHash"],
                    **({"apiContract": intent["apiContract"]} if "apiContract" in intent else {}),
                }
                actual_hash = hashlib.sha256(
                    json.dumps(snapshot, sort_keys=True, default=str).encode()
                ).hexdigest()
                if actual_hash == binding["requestHash"]:
                    matching.append((actual_hash, binding["attemptId"]))
        if len(matching) != 1:
            raise AssertionError("Offline video inputs do not match one committed provider attempt")
        request_hash, committed_attempt = matching[0]
        attempt_id = _assert_ledger("video", request_hash)
        if attempt_id != committed_attempt:
            raise AssertionError("Offline video ledger attempt changed before submission")
        task_id = f"offline-{uuid4()}"
        _record(
            "video",
            attemptId=attempt_id,
            requestHash=request_hash,
            taskId=task_id,
            model=model,
            input=input_data,
            scenario=_scenario().get("name", "pass"),
            repair=_scenario().get("repair", False),
        )
        if _scenario().get("unknownVideoReceipt"):
            raise TimeoutError("Fixture accepted submission but acknowledgement was lost")
        return {"task_id": task_id, "status": "queued"}

    async def get_task(self, task_id: str) -> dict[str, Any]:
        return {
            "task_id": task_id,
            "status": "completed",
            "output": {"video_url": f"https://8.8.8.8/{task_id}.mp4"},
        }

    async def download_file(self, url: str) -> bytes:
        if _scenario().get("downloadFailure"):
            raise TimeoutError("Fixture output unavailable")
        task_id = url.rsplit("/", 1)[-1].removesuffix(".mp4")
        videos = [
            json.loads(line)
            for line in Path(os.environ["P0_E2E_PROVIDER_LOG"]).read_text().splitlines()
            if json.loads(line)["stage"] == "video"
        ]
        record = next(item for item in videos if item["taskId"] == task_id)
        same_case = [item for item in videos if item["scenario"] == record["scenario"]]
        ordinal = same_case.index(record)
        name = (
            "repair"
            if record["repair"]
            else (
                "bad-group"
                if record["scenario"] == "repair" and ordinal == 0
                else f"clip-{ordinal % 2}"
            )
        )
        return Path(os.environ["P0_E2E_MEDIA"], f"{name}.mp4").read_bytes()


def install_provider_seams() -> None:
    if os.environ.get("P0_E2E_OFFLINE") != "1" or os.environ.get("APP_ENV") != "test":
        raise RuntimeError("Offline provider seams require the isolated E2E test environment")
    replacements = {
        "HttpGeminiClient": OfflineGeminiClient,
        "OpenAIImageClient": OfflineImageClient,
        "KieClient": OfflineKieClient,
    }
    # Load normal constructor consumers before replacing their imported aliases.
    for name in (
        "engine.gemini_client",
        "engine.openai_images",
        "engine.kie_client",
        "timeline_compile",
        "budgeted_analysis",
        "image_workflow",
        "kie_workflow",
    ):
        importlib.import_module(f"viraldy.modules.smart_remake.{name}")
    for name, module in tuple(sys.modules.items()):
        if name.startswith("viraldy.modules.smart_remake"):
            for symbol, replacement in replacements.items():
                if hasattr(module, symbol):
                    setattr(module, symbol, replacement)
    install_network_guard()
