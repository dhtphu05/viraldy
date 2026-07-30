from __future__ import annotations

from uuid import uuid4

import httpx
import pytest

from viraldy.modules.generation.contracts import GenerationOperation
from viraldy.modules.generation.provider import (
    FixtureGenerationProvider,
    HttpGenerationProvider,
    generation_provider,
)
from viraldy.modules.generation.service import (
    ensure_generation_enabled,
    ensure_generation_rights,
    select_generation_brief,
)
from viraldy.modules.viral_kits.contracts import GenerationBriefV1, GenerationSceneV1
from viraldy.platform.config.settings import Settings
from viraldy.shared.errors.base import AppError


def test_generation_feature_flags_are_disabled_by_default() -> None:
    settings = Settings()

    with pytest.raises(AppError, match="IMAGE_GENERATION_DISABLED"):
        ensure_generation_enabled(settings, GenerationOperation.STORYBOARD_IMAGE_GENERATE)
    with pytest.raises(AppError, match="VIDEO_GENERATION_DISABLED"):
        ensure_generation_enabled(settings, GenerationOperation.CONCEPT_VIDEO_PREVIEW_GENERATE)


def test_generation_brief_selection_is_exact_and_rejects_missing_contract() -> None:
    concept_id = "concept-1"
    brief = _brief(concept_id, "storyboard_preview")

    assert (
        select_generation_brief(
            [brief],
            concept_id,
            GenerationOperation.STORYBOARD_IMAGE_GENERATE,
        )
        is brief
    )

    with pytest.raises(AppError, match="GENERATION_BRIEF_NOT_FOUND"):
        select_generation_brief(
            [brief],
            concept_id,
            GenerationOperation.CONCEPT_VIDEO_PREVIEW_GENERATE,
        )


def test_generation_requires_explicit_rights_confirmation_when_brief_demands_it() -> None:
    brief = _brief("concept-1", "storyboard_preview")

    with pytest.raises(AppError, match="GENERATION_RIGHTS_CONFIRMATION_REQUIRED"):
        ensure_generation_rights(brief, False)

    ensure_generation_rights(brief, True)


def test_fixture_generation_provider_is_deterministic_and_never_returns_signed_urls() -> None:
    run_id = uuid4()
    brief = _brief("concept-1", "storyboard_preview")
    provider = FixtureGenerationProvider()

    first = provider.generate(
        operation=GenerationOperation.STORYBOARD_IMAGE_GENERATE,
        generation_run_id=run_id,
        brief=brief,
    )
    second = provider.generate(
        operation=GenerationOperation.STORYBOARD_IMAGE_GENERATE,
        generation_run_id=run_id,
        brief=brief,
    )

    assert first == second
    assert len(first.artifacts) == len(brief.scenes)
    assert all(artifact.storage_key is None for artifact in first.artifacts)
    assert all("http" not in str(artifact.payload_json) for artifact in first.artifacts)


def test_live_generation_provider_fails_fast_without_qualified_configuration() -> None:
    settings = Settings(
        ai_mode="live",
        image_generation_enabled=True,
        image_generation_model="seedream-model",
    )

    with pytest.raises(AppError, match="GENERATION_PROVIDER_NOT_CONFIGURED"):
        generation_provider(settings, GenerationOperation.STORYBOARD_IMAGE_GENERATE)


def test_live_generation_provider_retries_transient_failure_and_validates_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = _live_settings(ai_max_retries=1)
    provider = HttpGenerationProvider(settings, "seedream-model")
    run_id = uuid4()
    responses = [
        httpx.Response(503, request=httpx.Request("POST", "https://provider.test")),
        httpx.Response(
            200,
            headers={"x-request-id": "provider-request-1"},
            json=_provider_payload(),
            request=httpx.Request("POST", "https://provider.test"),
        ),
    ]
    requests: list[dict[str, object]] = []
    sleeps: list[int] = []

    def fake_post(*args: object, **kwargs: object) -> httpx.Response:
        requests.append({"args": args, "kwargs": kwargs})
        return responses.pop(0)

    monkeypatch.setattr("viraldy.modules.generation.provider.httpx.post", fake_post)
    monkeypatch.setattr("viraldy.modules.generation.provider.time.sleep", sleeps.append)

    result = provider.generate(
        operation=GenerationOperation.STORYBOARD_IMAGE_GENERATE,
        generation_run_id=run_id,
        brief=_brief("concept-1", "storyboard_preview"),
    )

    assert result.attempt_count == 2
    assert result.provider_request_id == "provider-request-1"
    assert result.artifacts[0].storage_key == "generated/storyboard/scene-1.png"
    assert len(requests) == 2
    assert sleeps == [1]
    request_kwargs = requests[0]["kwargs"]
    assert isinstance(request_kwargs, dict)
    assert request_kwargs["headers"] == {"Authorization": "Bearer test-api-key"}
    assert request_kwargs["timeout"] == settings.ai_request_timeout_seconds


def test_live_generation_provider_rejects_remote_artifact_urls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = _provider_payload()
    artifacts = payload["artifacts"]
    assert isinstance(artifacts, list)
    artifact = artifacts[0]
    assert isinstance(artifact, dict)
    artifact["storage_key"] = "https://signed.example/generated.png"
    response = httpx.Response(
        200,
        json=payload,
        request=httpx.Request("POST", "https://provider.test"),
    )
    monkeypatch.setattr(
        "viraldy.modules.generation.provider.httpx.post",
        lambda *args, **kwargs: response,
    )
    provider = HttpGenerationProvider(_live_settings(), "seedream-model")

    with pytest.raises(AppError, match="GENERATION_OUTPUT_INVALID"):
        provider.generate(
            operation=GenerationOperation.STORYBOARD_IMAGE_GENERATE,
            generation_run_id=uuid4(),
            brief=_brief("concept-1", "storyboard_preview"),
        )


def test_live_generation_provider_surfaces_rate_limit_after_retry_budget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    response = httpx.Response(
        429,
        request=httpx.Request("POST", "https://provider.test"),
    )
    monkeypatch.setattr(
        "viraldy.modules.generation.provider.httpx.post",
        lambda *args, **kwargs: response,
    )
    provider = HttpGenerationProvider(_live_settings(ai_max_retries=0), "seedream-model")

    with pytest.raises(AppError, match="GENERATION_PROVIDER_RATE_LIMITED"):
        provider.generate(
            operation=GenerationOperation.STORYBOARD_IMAGE_GENERATE,
            generation_run_id=uuid4(),
            brief=_brief("concept-1", "storyboard_preview"),
        )


def _live_settings(*, ai_max_retries: int = 2) -> Settings:
    return Settings(
        ai_mode="live",
        ai_provider="test-provider",
        ai_base_url="https://provider.test/v1",
        ai_api_key="test-api-key",
        image_generation_enabled=True,
        image_generation_model="seedream-model",
        ai_max_retries=ai_max_retries,
    )


def _provider_payload() -> dict[str, object]:
    return {
        "provider": "test-provider",
        "model": "seedream-model",
        "artifacts": [
            {
                "id": str(uuid4()),
                "artifact_kind": "storyboard_image",
                "scene_id": "scene-1",
                "storage_key": "generated/storyboard/scene-1.png",
                "media_type": "image/png",
                "width": 1080,
                "height": 1920,
                "duration_ms": None,
                "payload_json": {"fixture": False},
            }
        ],
        "usage_json": {"images": 1},
        "output_summary": {"artifact_count": 1},
    }


def _brief(
    concept_id: str,
    purpose: str,
) -> GenerationBriefV1:
    return GenerationBriefV1(
        concept_id=concept_id,
        purpose=purpose,
        aspect_ratio="9:16",
        duration_ms=10_000,
        scenes=[
            GenerationSceneV1(
                scene_id="scene-1",
                order=1,
                start_ms=0,
                end_ms=2_000,
                purpose="hook",
                visual_prompt="Show the observable product result.",
                camera_direction="Static close-up.",
                product_visibility="Product visible.",
                creator_direction="Natural delivery.",
            ),
            GenerationSceneV1(
                scene_id="scene-2",
                order=2,
                start_ms=2_000,
                end_ms=6_000,
                purpose="demo",
                visual_prompt="Show the product mechanism.",
                camera_direction="Overhead demo.",
                product_visibility="Product remains visible.",
                creator_direction="Demonstrate one step.",
            ),
        ],
        consistency_constraints=["Keep product identity consistent."],
        negative_constraints=["Do not add unsupported claims."],
        claim_guardrails=["Use only supplied product facts."],
        rights_confirmation_required=True,
    )
