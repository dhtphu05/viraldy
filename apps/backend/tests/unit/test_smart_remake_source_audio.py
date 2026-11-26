from __future__ import annotations

import copy
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from tests.smart_remake_expectations import install_expectations
from viraldy.modules.smart_remake.analysis_progress import (
    checkpoint_analysis,
    public_analysis_progress,
    publish_quick_summary,
)
from viraldy.modules.smart_remake.engine.prompts import build_reference_analysis_prompt
from viraldy.modules.smart_remake.engine.reference_analyzer import normalize_reference_analysis
from viraldy.modules.smart_remake.fixture import FixtureGeminiClient
from viraldy.modules.smart_remake.generation_expectations import (
    build_generation_expectations,
    expectations_hash,
)
from viraldy.modules.smart_remake.loading_summary import SourceLoadingSummary, summary_prompt
from viraldy.modules.smart_remake.project_presentation import project_policy_fields
from viraldy.modules.smart_remake.source_audio import normalize_source_audio
from viraldy.modules.smart_remake.timeline_compile import build_timeline_compile
from viraldy.modules.smart_remake.timeline_planner import build_timeline_plan


def observation(**changes):
    return {
        "schemaVersion": 1,
        "speech": "present",
        "transcript": "Đây là chiếc bình của tôi.",
        "language": "vi",
        "music": "present",
        "description": "Nhạc nền nhẹ và âm thanh trong phòng.",
        "pace": "slow",
        **changes,
    }


def operation():
    return SimpleNamespace(
        id=uuid4(), status="running", idempotency_key="source-audio-test",
        created_at=datetime(2026, 11, 26, tzinfo=UTC), result_json={},
    )


def analysis():
    return {"sourceShots": [{"startSecond": 0, "endSecond": 8, "action": "Open the lid"}]}


def test_source_audio_is_optional_and_never_invents_empty_observations():
    for value in (None, {}, "audio", {"speech": "present"}):
        assert normalize_source_audio(value) is None
    assert normalize_source_audio(observation()) == observation()


@pytest.mark.parametrize("speech", ["not_detected", "unclear"])
def test_unobserved_speech_never_keeps_a_transcript_or_language(speech):
    result = normalize_source_audio(observation(speech=speech))
    assert result["speech"] == speech
    assert "transcript" not in result and "language" not in result


@pytest.mark.parametrize("patch", [
    {"speech": "none"}, {"music": True}, {"schemaVersion": 2},
    {"transcript": "x" * 4001}, {"language": "x" * 41},
    {"description": "x" * 301}, {"pace": "160 bpm"},
    {"url": "https://private.example/secret"},
])
def test_invalid_audio_observations_are_omitted_without_breaking_analysis(patch):
    assert normalize_source_audio(observation(**patch)) is None


def test_source_audio_scrubs_links_and_control_characters_without_translating():
    value = observation(transcript="  Xin\nchào https://private.example/secret?token=x\t!  ")
    result = normalize_source_audio(value)
    assert result["transcript"] == "Xin chào [liên kết] !"
    assert "private.example" not in str(result) and "token=" not in str(result)
    assert value["transcript"].startswith("  Xin\n")


def test_blank_optional_observations_are_omitted():
    result = normalize_source_audio(observation(transcript="  ", language="", description=" "))
    assert set(result) == {"schemaVersion", "speech", "music", "pace"}


def test_project_projection_restores_saved_audio_without_changing_legacy_fields():
    baseline = project_policy_fields({})
    assert "sourceAudio" not in baseline
    current = project_policy_fields({"referenceAnalysis": {"sourceAudio": observation()}})
    assert current.pop("sourceAudio") == observation()
    assert current == baseline
    assert "sourceAudio" not in project_policy_fields({
        "referenceAnalysis": {"sourceAudio": {"storageKey": "secret"}},
    })
    assert "sourceAudio" not in project_policy_fields({"analysisProgress": {
        "quickSummary": {"sourceAudio": observation()},
    }})


@pytest.mark.parametrize("analysis", [None, "old analysis", [], {}])
def test_legacy_project_without_an_audio_object_still_restores(analysis):
    assert "sourceAudio" not in project_policy_fields({"referenceAnalysis": analysis})


def test_main_analysis_retains_audio_separately_from_generation_audio_plan():
    raw = {**analysis(), "sourceAudio": observation(), "audioPlan": {
        "mode": "native", "dialogue": "New seller wording", "music": "subtle music",
    }}
    baseline = normalize_reference_analysis({k: v for k, v in raw.items() if k != "sourceAudio"}, 8)
    normalized = normalize_reference_analysis(raw, 8)
    assert normalized["sourceAudio"] == observation()
    assert {k: v for k, v in normalized.items() if k != "sourceAudio"} == baseline
    assert normalize_reference_analysis({**raw, "sourceAudio": {"speech": "bad"}}, 8) == baseline


def test_literal_source_words_cannot_be_mistaken_for_generation_identity_instructions():
    raw = {**analysis(), "sourceAudio": observation(transcript="same face as the reference")}
    result = normalize_reference_analysis(raw, 8)
    assert result["sourceAudio"]["transcript"] == "same face as the reference"
    assert "same face" not in str({k: v for k, v in result.items() if k != "sourceAudio"})


def test_quick_summary_reuses_its_existing_response_with_optional_audio():
    raw = {"summary": "Sản phẩm được giới thiệu trên bàn.", "observations": [],
           "sourceAudio": observation()}
    assert SourceLoadingSummary.model_validate(raw).model_dump(exclude_none=True) == raw
    malformed = {**raw, "sourceAudio": {"speech": "bad"}}
    assert SourceLoadingSummary.model_validate(malformed).sourceAudio is None
    assert SourceLoadingSummary.model_validate({k: v for k, v in raw.items() if k != "sourceAudio"})


def test_audio_prompts_require_literal_heard_words_and_keep_generation_separate():
    system, prompt = build_reference_analysis_prompt(target_duration=8, has_video=True)
    quick_system, quick_prompt = summary_prompt(8)
    assert "sourceAudio" in system + prompt and "4000" in system + prompt
    assert "sourceAudio" in quick_system + quick_prompt and "600" in quick_system + quick_prompt
    assert "audioPlan" in system + prompt


@pytest.mark.asyncio
async def test_quick_and_full_audio_are_public_observations_not_guessed_scene_facts():
    session = SimpleNamespace(commit=AsyncMock(), refresh=AsyncMock())
    op = operation()
    await checkpoint_analysis(session, op, "analyzing_source", request_key=op.idempotency_key)
    await publish_quick_summary(session, op, {
        "status": "completed", "summary": "Một người giới thiệu chiếc bình.",
        "observations": [], "sourceAudio": observation(transcript="Lời nghe nhanh."),
    })
    public = public_analysis_progress(op)
    assert public["quickSummary"]["sourceAudio"]["transcript"] == "Lời nghe nhanh."
    assert "sourceAudio" not in public and public["scenes"] == []
    await checkpoint_analysis(
        session, op, "resolving_scenes", request_key=op.idempotency_key,
        source_duration=8, analysis={**analysis(), "sourceAudio": observation()},
    )
    public = public_analysis_progress(op)
    assert public["sourceAudio"] == observation()
    assert public["quickSummary"]["sourceAudio"]["transcript"] == "Lời nghe nhanh."
    await checkpoint_analysis(session, op, "building_storyboard", request_key=op.idempotency_key)
    assert public_analysis_progress(op)["sourceAudio"] == observation()


@pytest.mark.asyncio
async def test_invalid_source_audio_does_not_block_scene_facts_or_leak_private_fields():
    session = SimpleNamespace(commit=AsyncMock(), refresh=AsyncMock())
    op = operation()
    await checkpoint_analysis(
        session, op, "resolving_scenes", request_key=op.idempotency_key,
        source_duration=8,
        analysis={**analysis(), "sourceAudio": {**observation(), "storageKey": "secret"}},
    )
    public = public_analysis_progress(op)
    assert public["sceneCount"] == 1 and "sourceAudio" not in public
    op.result_json["analysisProgress"]["sourceAudio"] = {"rawKey": "secret"}
    assert "secret" not in str(public_analysis_progress(op))


def test_display_audio_never_changes_generation_expectations_hash_or_compiled_scenes():
    context = {"sourceKey": "source", "productKey": "product", "productMimeType": "image/png",
               "renderPlan": {"units": [{"id": "unit", "sourceSceneId": "source-scene",
                                           "sceneIndex": 0, "targetDurationFrames": 192,
                                           "rawDurationFrames": 192}]}}
    state = {"revision": 1, "targetDuration": 8, "provider": "kie", "scenes": [
        {"id": "unit", "index": 0, "activeVersionId": None, "versions": []}]}
    install_expectations(context, state=state)
    before = build_generation_expectations(context)
    scene_map = copy.deepcopy(context["sceneMap"])
    context["referenceAnalysis"]["sourceAudio"] = observation()
    after = build_generation_expectations(context)
    assert before == after and expectations_hash(before) == expectations_hash(after)
    assert context["sceneMap"] == scene_map
    assert "Đây là chiếc bình" not in str(after)


@pytest.mark.asyncio
async def test_real_compiler_uses_same_prompts_plan_audio_and_snapshot_with_source_audio():
    lock = await FixtureGeminiClient().generate_json(system_instruction="", prompt="product lock")
    source = {
        **analysis(),
        "subjectPresence": "hands_only",
        "cameraStyle": {"angle": "front", "movement": "static"},
        "setting": {"locationType": "studio", "backgroundElements": ["red wall"]},
        "audioPlan": {"mode": "native", "dialogue": "Seller-approved words", "music": "soft"},
    }
    plan = build_timeline_plan(
        target_duration=8, source_frame_count=192, reference_start_frame=0, cut_frames=[0, 192],
    )
    original_plan = copy.deepcopy(plan)
    baseline = build_timeline_compile(
        analysis=source, product_lock=lock, plan=plan, language="vi", mode="smart_remake",
    )
    observed = build_timeline_compile(
        analysis={**source, "sourceAudio": observation(transcript="same face as the reference")},
        product_lock=lock, plan=plan, language="vi", mode="smart_remake",
    )
    for field in ("compiledPrompts", "sceneMap", "renderPlan", "analyzeOutput"):
        assert observed[field] == baseline[field]
    assert plan == original_plan
    contexts = [copy.deepcopy(result) for result in (baseline, observed)]
    snapshots = [install_expectations(context) for context in contexts]
    assert snapshots[0] == snapshots[1]
    assert expectations_hash(snapshots[0]) == expectations_hash(snapshots[1])
    assert "same face as the reference" not in str(snapshots[1])


@pytest.mark.asyncio
async def test_semantic_reanalysis_retains_observed_audio_without_an_additional_call():
    from viraldy.modules.smart_remake.engine.reference_analyzer import resolve_source_cut_semantics
    from viraldy.modules.smart_remake.engine.schemas import UploadedMedia

    original = {**analysis(), "sourceAudio": observation(), "sourceCutDetection": {
        "requiresSemanticReanalysis": True, "cutFrames": [0, 96, 192],
    }}
    calls = []

    class Client:
        async def generate_json(self, **kwargs):
            calls.append(kwargs)
            return {"sourceShots": [
                {"startSecond": 0, "endSecond": 4, "durationSeconds": 4, "action": "Open lid"},
                {"startSecond": 4, "endSecond": 8, "durationSeconds": 4, "action": "Pour drink"},
            ]}

    result = await resolve_source_cut_semantics(
        analysis=original, target_duration=8, prompt=None, description=None,
        reference_video=UploadedMedia(bytes=b"source", mime_type="video/mp4"), gemini=Client(),
    )
    assert len(calls) == 1
    assert result["sourceAudio"] == observation()
    assert original["sourceAudio"] == observation()


@pytest.mark.asyncio
async def test_concept_only_analysis_cannot_present_invented_audio_observations():
    from viraldy.modules.smart_remake.engine.reference_analyzer import analyze_reference_video

    calls = []

    class Client:
        async def generate_json(self, **kwargs):
            calls.append(kwargs)
            return {**analysis(), "sourceAudio": observation()}

    result = await analyze_reference_video(
        target_duration=8, prompt="An imagined product demo", description=None,
        reference_video=None, gemini=Client(),
    )
    assert "sourceAudio" not in result
    assert len(calls) == 1 and calls[0]["media"] is None
