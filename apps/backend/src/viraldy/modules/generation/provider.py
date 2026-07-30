from __future__ import annotations

import time
from typing import Protocol
from uuid import NAMESPACE_URL, UUID, uuid5

import httpx
from pydantic import ValidationError

from viraldy.modules.generation.contracts import (
    GenerationArtifactV1,
    GenerationOperation,
    GenerationProviderResultV1,
)
from viraldy.modules.viral_kits.public import GenerationBriefV1, GenerationSceneV1
from viraldy.platform.config.settings import Settings
from viraldy.shared.errors.base import AppError


class GenerationProvider(Protocol):
    provider: str
    model: str

    def generate(
        self,
        *,
        operation: GenerationOperation,
        generation_run_id: UUID,
        brief: GenerationBriefV1,
    ) -> GenerationProviderResultV1:
        raise NotImplementedError


class FixtureGenerationProvider:
    def __init__(self, mode: str = "fixture", model: str = "deterministic-generation-v1") -> None:
        self.provider = f"{mode}_fixture"
        self.model = model

    def generate(
        self,
        *,
        operation: GenerationOperation,
        generation_run_id: UUID,
        brief: GenerationBriefV1,
    ) -> GenerationProviderResultV1:
        if operation is GenerationOperation.STORYBOARD_IMAGE_GENERATE:
            artifacts = [
                self._storyboard_artifact(generation_run_id, brief, scene)
                for scene in sorted(brief.scenes, key=lambda item: item.order)
            ]
        else:
            artifacts = [self._video_artifact(generation_run_id, brief)]
        return GenerationProviderResultV1(
            provider=self.provider,
            model=self.model,
            provider_request_id=f"fixture-{generation_run_id}",
            latency_ms=0,
            attempt_count=1,
            artifacts=artifacts,
            usage_json={"fixture": True},
            output_summary={
                "artifact_count": len(artifacts),
                "operation": operation.value,
                "purpose": brief.purpose,
            },
        )

    def _storyboard_artifact(
        self,
        generation_run_id: UUID,
        brief: GenerationBriefV1,
        scene: GenerationSceneV1,
    ) -> GenerationArtifactV1:
        width, height = _dimensions(brief.aspect_ratio)
        return GenerationArtifactV1(
            id=uuid5(NAMESPACE_URL, f"{generation_run_id}:storyboard:{scene.scene_id}"),
            artifact_kind="storyboard_image",
            scene_id=scene.scene_id,
            storage_key=None,
            media_type="application/vnd.viraldy.fixture+json",
            width=width,
            height=height,
            payload_json={
                "fixture": True,
                "scene_order": scene.order,
                "visual_prompt": scene.visual_prompt,
                "camera_direction": scene.camera_direction,
                "product_visibility": scene.product_visibility,
            },
        )

    def _video_artifact(
        self,
        generation_run_id: UUID,
        brief: GenerationBriefV1,
    ) -> GenerationArtifactV1:
        width, height = _dimensions(brief.aspect_ratio)
        return GenerationArtifactV1(
            id=uuid5(NAMESPACE_URL, f"{generation_run_id}:video-preview"),
            artifact_kind="concept_video_preview",
            storage_key=None,
            media_type="application/vnd.viraldy.fixture+json",
            width=width,
            height=height,
            duration_ms=brief.duration_ms,
            payload_json={
                "fixture": True,
                "scene_ids": [scene.scene_id for scene in brief.scenes],
                "audio_direction": brief.audio_direction,
            },
        )


class HttpGenerationProvider:
    def __init__(self, settings: Settings, model: str) -> None:
        if not settings.ai_base_url or not settings.ai_api_key:
            raise AppError(
                "GENERATION_PROVIDER_NOT_CONFIGURED",
                "Live generation requires AI_BASE_URL and AI_API_KEY.",
                status_code=503,
            )
        self.provider = settings.ai_provider
        self.model = model
        self._base_url = settings.ai_base_url.rstrip("/")
        self._api_key = settings.ai_api_key.get_secret_value()
        self._timeout = settings.ai_request_timeout_seconds
        self._max_retries = settings.ai_max_retries

    def generate(
        self,
        *,
        operation: GenerationOperation,
        generation_run_id: UUID,
        brief: GenerationBriefV1,
    ) -> GenerationProviderResultV1:
        started = time.monotonic()
        response, attempt_count = self._request_with_retry(
            operation,
            generation_run_id,
            brief,
        )
        try:
            payload = response.json()
            payload.setdefault("provider", self.provider)
            payload.setdefault("model", self.model)
            payload.setdefault("provider_request_id", response.headers.get("x-request-id"))
            payload.setdefault("latency_ms", int((time.monotonic() - started) * 1000))
            payload.setdefault("attempt_count", attempt_count)
            return GenerationProviderResultV1.model_validate(payload)
        except (ValueError, ValidationError) as exc:
            raise AppError(
                "GENERATION_OUTPUT_INVALID",
                "Generation provider returned invalid output.",
                status_code=502,
            ) from exc

    def _request_with_retry(
        self,
        operation: GenerationOperation,
        generation_run_id: UUID,
        brief: GenerationBriefV1,
    ) -> tuple[httpx.Response, int]:
        for attempt in range(1, self._max_retries + 2):
            try:
                response = httpx.post(
                    f"{self._base_url}/media/generations",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    json={
                        "model": self.model,
                        "operation": operation.value,
                        "generation_run_id": str(generation_run_id),
                        "brief": brief.model_dump(mode="json"),
                    },
                    timeout=self._timeout,
                )
            except httpx.TimeoutException as exc:
                if attempt <= self._max_retries:
                    time.sleep(min(2 ** (attempt - 1), 8))
                    continue
                raise AppError(
                    "GENERATION_PROVIDER_TIMEOUT",
                    "Generation provider timed out.",
                    status_code=504,
                ) from exc
            except httpx.HTTPError as exc:
                raise AppError(
                    "GENERATION_PROVIDER_FAILED",
                    "Generation provider request failed.",
                    status_code=502,
                ) from exc
            if response.status_code in {429, 500, 502, 503, 504}:
                if attempt <= self._max_retries:
                    time.sleep(min(2 ** (attempt - 1), 8))
                    continue
                code = (
                    "GENERATION_PROVIDER_RATE_LIMITED"
                    if response.status_code == 429
                    else "GENERATION_PROVIDER_FAILED"
                )
                raise AppError(
                    code,
                    "Generation provider could not complete the request.",
                    status_code=503 if response.status_code == 429 else 502,
                )
            if response.status_code >= 400:
                raise AppError(
                    "GENERATION_PROVIDER_FAILED",
                    "Generation provider returned an error.",
                    status_code=502,
                )
            return response, attempt
        raise RuntimeError("generation provider retry loop exhausted unexpectedly")


def generation_provider(
    settings: Settings,
    operation: GenerationOperation,
) -> GenerationProvider:
    if settings.ai_mode in {"fixture", "mock"}:
        model = (
            settings.image_generation_model
            if operation is GenerationOperation.STORYBOARD_IMAGE_GENERATE
            else settings.video_generation_model
        )
        return FixtureGenerationProvider(settings.ai_mode, model or "deterministic-generation-v1")
    model = (
        settings.image_generation_model
        if operation is GenerationOperation.STORYBOARD_IMAGE_GENERATE
        else settings.video_generation_model
    )
    if not model:
        raise AppError(
            "GENERATION_PROVIDER_NOT_CONFIGURED",
            "The generation model is not configured.",
            status_code=503,
        )
    return HttpGenerationProvider(settings, model)


def _dimensions(aspect_ratio: str) -> tuple[int, int]:
    if aspect_ratio == "9:16":
        return 1080, 1920
    if aspect_ratio == "16:9":
        return 1920, 1080
    return 1080, 1080
