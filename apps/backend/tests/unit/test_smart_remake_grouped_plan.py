from __future__ import annotations

import copy
import hashlib
from types import SimpleNamespace
from uuid import uuid4

import pytest

from viraldy.modules.smart_remake import timeline_service as service_module
from viraldy.modules.smart_remake.repair_service import RepairService
from viraldy.modules.smart_remake.timeline_planner import build_timeline_plan
from viraldy.shared.errors.base import AppError


def plan_for(lengths, **kwargs):
    cuts = [0]
    for length in lengths:
        cuts.append(cuts[-1] + length * 24)
    return build_timeline_plan(
        target_duration=sum(lengths),
        source_frame_count=720,
        reference_start_frame=24,
        cut_frames=cuts,
        **kwargs,
    )


@pytest.mark.parametrize(
    "lengths,members", [((3, 5, 4, 4), [2, 2]), ((2, 2, 2, 2), [4]), ((5, 5, 6), [1, 1, 1])]
)
def test_groups_pack_adjacent_scenes_without_changing_logical_timing(lengths, members):
    result = plan_for(lengths)
    plan = result["renderPlan"]
    groups = plan["groups"]
    assert [len(group["renderUnitIds"]) for group in groups] == members
    assert [unit_id for group in groups for unit_id in group["renderUnitIds"]] == [
        unit["id"] for unit in plan["units"]
    ]
    assert [item["targetDurationFrames"] for item in result["draftTimeline"]["items"]] == [
        length * 24 for length in lengths
    ]
    for group in groups:
        assert group["rawDurationFrames"] == 192
        assert group["segments"][0]["inFrame"] == 0
        assert group["segments"][-1]["outFrame"] == group["targetDurationFrames"] <= 192
    assert len({group["id"] for group in groups}) == len(groups)


def test_forced_group_break_and_frozen_provider_image_configuration():
    plan = plan_for((2, 6), render_group_breaks=[1], image_quality="medium")["renderPlan"]
    assert len(plan["groups"]) == 2
    assert (plan["videoModel"], plan["imageModel"], plan["imageQuality"], plan["imageSize"]) == (
        "wan/3-0-video",
        "gpt-image-2.6-sunburst",
        "medium",
        "720x1280",
    )
    assert len(plan_for((2, 6))["renderPlan"]["groups"]) == 1


@pytest.mark.parametrize("breaks", [[0], [2], [-1], [True], [1.5], [1, 1], [2, 1], "1"])
def test_invalid_explicit_group_boundaries_are_rejected(breaks):
    with pytest.raises(AppError, match="SMART_REMAKE_RENDER_GROUPS_INVALID"):
        plan_for((2, 6), render_group_breaks=breaks)


@pytest.mark.parametrize("quality", ["ultra", "auto", "", None, True])
def test_image_quality_is_an_explicit_supported_policy(quality):
    with pytest.raises(AppError, match="SMART_REMAKE_RENDER_GROUPS_INVALID"):
        plan_for((2, 6), image_quality=quality)


def test_new_plans_default_to_sunburst_max_quality_and_high_complexity():
    plan = plan_for((2, 6))["renderPlan"]
    assert (plan["imageModel"], plan["imageQuality"], plan["imageComplexity"]) == (
        "gpt-image-2.6-sunburst",
        "max",
        "high",
    )


@pytest.mark.parametrize("quality", ["low", "medium", "high", "xhigh", "max"])
def test_new_plan_quality_can_be_explicitly_frozen_to_a_supported_value(quality):
    assert plan_for((2, 6), image_quality=quality)["renderPlan"]["imageQuality"] == quality


@pytest.mark.parametrize("quality", [None, "low", "medium", "high", "xhigh", "max", " MAX "])
def test_image_quality_environment_defaults_max_and_accepts_supported_values(monkeypatch, quality):
    from viraldy.modules.smart_remake.engine.config import get_openai_image_quality

    if quality is None:
        monkeypatch.delenv("SMART_REMAKE_OPENAI_IMAGE_QUALITY", raising=False)
    else:
        monkeypatch.setenv("SMART_REMAKE_OPENAI_IMAGE_QUALITY", quality)
    assert get_openai_image_quality() == (quality.strip().lower() if quality else "max")


@pytest.mark.parametrize("quality", ["ultra", "auto", ""])
def test_image_quality_environment_rejects_unknown_levels(monkeypatch, quality):
    from viraldy.modules.smart_remake.engine.config import get_openai_image_quality
    from viraldy.modules.smart_remake.engine.errors import SmartRemakeValidationError

    monkeypatch.setenv("SMART_REMAKE_OPENAI_IMAGE_QUALITY", quality)
    with pytest.raises(SmartRemakeValidationError):
        get_openai_image_quality()


def grouped_project():
    plan = plan_for((3, 5, 4, 4))
    scenes = [
        {**unit, "index": index, "versions": [], "activeVersionId": None}
        for index, unit in enumerate(plan["renderPlan"]["units"])
    ]
    state = dict(
        schemaVersion=2,
        revision=1,
        targetDuration=16,
        provider="kie",
        scenes=scenes,
        finalStorageKey="published-before",
        **copy.deepcopy(plan),
    )
    return SimpleNamespace(
        id=uuid4(),
        workspace_id=uuid4(),
        revision=1,
        state_json=state,
        context_json=dict(schemaVersion=2, audioRequired=False, **copy.deepcopy(plan)),
    )


@pytest.mark.parametrize(
    "damage",
    [
        "duplicate",
        "missing",
        "order",
        "range",
        "duration",
        "gap",
        "model",
        "image-model",
        "image-quality",
        "empty",
        "boolean",
    ],
)
def test_saved_group_manifest_rejects_invalid_or_rebound_groups(damage):
    row = grouped_project()
    plan = row.state_json["renderPlan"]
    groups = plan["groups"]
    group = groups[0]
    if damage == "duplicate":
        groups[1]["renderUnitIds"][0] = group["renderUnitIds"][0]
    elif damage == "missing":
        group["renderUnitIds"].pop()
        group["segments"].pop()
    elif damage == "order":
        group["renderUnitIds"].reverse()
    elif damage == "range":
        group["targetDurationFrames"] = 193
    elif damage == "duration":
        group["segments"][0]["outFrame"] -= 1
    elif damage == "gap":
        group["segments"][1]["inFrame"] += 1
    elif damage == "model":
        plan["videoModel"] = "veo3_fast"
    elif damage == "image-model":
        plan["imageModel"] = "gpt-image-2.5-sunburst"
    elif damage == "image-quality":
        plan["imageQuality"] = "ultra"
    elif damage == "empty":
        plan["groups"] = []
    else:
        group["segments"][0]["inFrame"] = False
    row.context_json["renderPlan"] = copy.deepcopy(plan)
    with pytest.raises(AppError, match="SMART_REMAKE_TIMELINE_INVALID"):
        service_module.validate_manifest(row)


def test_legacy_saved_v2_without_groups_remains_valid():
    row = grouped_project()
    for plan in (row.state_json["renderPlan"], row.context_json["renderPlan"]):
        for field in (
            "groups",
            "videoModel",
            "videoResolution",
            "imageModel",
            "imageQuality",
            "imageComplexity",
            "imageSize",
        ):
            plan.pop(field)
    service_module.validate_manifest(row)


@pytest.mark.parametrize("quality", ["low", "medium", "high", "xhigh", "max"])
def test_existing_flare_plan_without_complexity_remains_frozen_and_valid(quality):
    row = grouped_project()
    for plan in (row.state_json["renderPlan"], row.context_json["renderPlan"]):
        plan.update(imageModel="gpt-image-2.6-flare", imageQuality=quality)
        plan.pop("imageComplexity", None)
    original = copy.deepcopy(row.context_json["renderPlan"])
    service_module.validate_manifest(row)
    assert row.context_json["renderPlan"] == row.state_json["renderPlan"] == original


@pytest.mark.parametrize("complexity", [None, "xhigh", "max", "unknown", 1, True])
def test_sunburst_saved_plan_requires_explicit_supported_complexity(complexity):
    row = grouped_project()
    for plan in (row.state_json["renderPlan"], row.context_json["renderPlan"]):
        if complexity is None:
            plan.pop("imageComplexity", None)
        else:
            plan["imageComplexity"] = complexity
    with pytest.raises(AppError, match="SMART_REMAKE_TIMELINE_INVALID"):
        service_module.validate_manifest(row)


@pytest.mark.parametrize("complexity", ["low", "medium", "high"])
def test_complexity_policy_is_validated_independently_of_quality(complexity):
    row = grouped_project()
    for plan in (row.state_json["renderPlan"], row.context_json["renderPlan"]):
        plan.update(imageQuality="high", imageComplexity=complexity)
    service_module.validate_manifest(row)


@pytest.mark.parametrize(
    "field,value",
    [("imageModel", "gpt-image-2.6-flare"), ("imageComplexity", "low"), ("imageQuality", "medium")],
)
def test_saved_image_policy_cannot_change_in_only_one_manifest_copy(field, value):
    row = grouped_project()
    row.state_json["renderPlan"][field] = value
    with pytest.raises(AppError, match="SMART_REMAKE_TIMELINE_INVALID"):
        service_module.validate_manifest(row)


class Repository:
    def __init__(self, row):
        self.row, self.writes = row, 0

    async def project(self, wid, pid, **kwargs):
        assert (wid, pid) == (self.row.workspace_id, self.row.id)
        return self.row

    async def save(self, row, state):
        self.writes += 1
        assert all(state["scenes"][index]["versions"] for index in (0, 1))
        row.state_json = copy.deepcopy(state)
        row.revision = state["revision"]

    async def complete(self, row, state, operation, result):
        row.state_json = copy.deepcopy(state)


class Media:
    def __init__(self):
        self.puts = 0

    async def put(self, prefix, data, mime):
        self.puts += 1
        return "shared-clip-key"


@pytest.fixture
def grouped_runtime(monkeypatch):
    row = grouped_project()
    repository, media = Repository(row), Media()
    repair = RepairService(repository, media, row.workspace_id)

    def version(data, key, prompts, parent, metadata, **kwargs):
        return dict(
            id=str(uuid4()),
            storageKey=key,
            mediaHash=hashlib.sha256(data).hexdigest(),
            providerMetadata=metadata,
            technicalCheck={"status": "passed"},
            parentVersionId=parent,
            usedByRevision=None,
        )

    monkeypatch.setattr(service_module, "_new_version", version)
    monkeypatch.setattr(service_module, "probe_timeline_media", lambda _: {"frameCount": 192})
    return row, repair, repository, media


@pytest.mark.asyncio
async def test_group_clip_is_retained_once_and_all_scene_bindings_commit_together(grouped_runtime):
    row, repair, repository, media = grouped_runtime
    group = row.state_json["renderPlan"]["groups"][0]
    metadata = {"provider": "kie", "providerRequestId": "paid-task"}
    await service_module.retain_timeline_group_clip(repair, row, group, b"clip", metadata)
    versions = [scene["versions"][0] for scene in row.state_json["scenes"][:2]]
    assert versions[0]["id"] != versions[1]["id"]
    assert versions[0]["storageKey"] == versions[1]["storageKey"] == "shared-clip-key"
    assert versions[0]["mediaHash"] == versions[1]["mediaHash"]
    assert [version["providerMetadata"]["suggestedInFrame"] for version in versions] == [0, 72]
    assert [version["providerMetadata"]["suggestedOutFrame"] for version in versions] == [72, 192]
    items = row.state_json["draftTimeline"]["items"]
    assert [(item["inFrame"], item["outFrame"], item["reviewed"]) for item in items[:2]] == [
        (0, 72, False),
        (72, 192, False),
    ]
    assert all(not item["versionId"] for item in items[2:])
    assert row.state_json["finalStorageKey"] == "published-before"
    assert (media.puts, repository.writes, row.revision) == (1, 1, 2)
    await service_module.retain_timeline_group_clip(repair, row, group, b"clip", metadata)
    assert (media.puts, repository.writes, row.revision) == (1, 1, 2)


@pytest.mark.asyncio
async def test_retry_repairs_partial_group_binding_without_overwriting_reviewed_scene(
    grouped_runtime,
):
    row, repair, repository, media = grouped_runtime
    group = row.state_json["renderPlan"]["groups"][0]
    metadata = {"provider": "kie", "providerRequestId": "paid-task"}
    await service_module.retain_timeline_group_clip(repair, row, group, b"clip", metadata)
    first = copy.deepcopy(row.state_json["scenes"][0]["versions"][0])
    row.state_json["scenes"][1]["versions"] = []
    row.state_json["scenes"][1]["activeVersionId"] = None
    row.state_json["draftTimeline"]["items"][0]["reviewed"] = True
    await service_module.retain_timeline_group_clip(repair, row, group, b"clip", metadata)
    assert row.state_json["scenes"][0]["versions"] == [first]
    assert row.state_json["draftTimeline"]["items"][0]["reviewed"] is True
    assert len(row.state_json["scenes"][1]["versions"]) == 1
    assert media.puts == 1


@pytest.mark.asyncio
async def test_group_retention_rejects_rebound_media_or_unsaved_group(grouped_runtime):
    row, repair, _, _ = grouped_runtime
    group = row.state_json["renderPlan"]["groups"][0]
    metadata = {"provider": "kie", "providerRequestId": "paid-task"}
    await service_module.retain_timeline_group_clip(repair, row, group, b"clip", metadata)
    with pytest.raises(AppError, match="SMART_REMAKE_MEDIA_CHANGED"):
        await service_module.retain_timeline_group_clip(repair, row, group, b"changed", metadata)
    with pytest.raises(AppError, match="SMART_REMAKE_TIMELINE_INVALID"):
        await service_module.retain_timeline_group_clip(
            repair, row, {**group, "id": str(uuid4())}, b"clip", metadata
        )


@pytest.mark.asyncio
async def test_accept_uses_candidate_suggested_range_and_only_resets_that_scene(grouped_runtime):
    row, repair, _, _ = grouped_runtime
    scene = row.state_json["scenes"][1]
    version = dict(
        id=str(uuid4()),
        frameCount=192,
        providerMetadata={"suggestedInFrame": 72, "suggestedOutFrame": 192},
    )
    row.state_json["draftTimeline"]["items"][0]["reviewed"] = True
    await service_module.accept_timeline_version(
        repair, row, row.state_json, SimpleNamespace(), scene, version
    )
    first, second = row.state_json["draftTimeline"]["items"][:2]
    assert first["reviewed"] is True
    assert (second["inFrame"], second["outFrame"], second["reviewed"]) == (72, 192, False)
    assert second["versionId"] == version["id"]


@pytest.mark.asyncio
async def test_group_binding_failure_never_commits_only_one_member(grouped_runtime, monkeypatch):
    row, repair, repository, _ = grouped_runtime
    group = row.state_json["renderPlan"]["groups"][0]
    original = service_module._new_version
    calls = []

    def fail_second(*args, **kwargs):
        calls.append(args)
        if len(calls) == 2:
            raise RuntimeError("inspection unavailable")
        return original(*args, **kwargs)

    monkeypatch.setattr(service_module, "_new_version", fail_second)
    with pytest.raises(RuntimeError, match="inspection unavailable"):
        await service_module.retain_timeline_group_clip(
            repair, row, group, b"clip", {"providerRequestId": "paid-task"}
        )
    assert repository.writes == 0
    assert all(not scene["versions"] for scene in row.state_json["scenes"])
    assert row.state_json["revision"] == 1


@pytest.mark.asyncio
async def test_short_group_clip_never_fills_missing_scene_frames(grouped_runtime, monkeypatch):
    row, repair, _, _ = grouped_runtime
    group = row.state_json["renderPlan"]["groups"][0]
    monkeypatch.setattr(service_module, "probe_timeline_media", lambda _: {"frameCount": 180})
    await service_module.retain_timeline_group_clip(
        repair, row, group, b"clip", {"providerRequestId": "paid-task"}
    )
    first, second = row.state_json["scenes"][:2]
    assert first["activeVersionId"]
    assert second["activeVersionId"] is None
    assert second["versions"][0]["technicalCheck"]["status"] == "failed"
    assert row.state_json["draftTimeline"]["items"][1]["versionId"] is None


@pytest.mark.asyncio
async def test_accepted_version_top_level_bounds_override_legacy_metadata(grouped_runtime):
    row, repair, _, _ = grouped_runtime
    scene = row.state_json["scenes"][1]
    version = dict(
        id=str(uuid4()),
        frameCount=192,
        suggestedInFrame=24,
        suggestedOutFrame=144,
        providerMetadata={"suggestedInFrame": 72, "suggestedOutFrame": 192},
    )
    await service_module.accept_timeline_version(
        repair, row, row.state_json, SimpleNamespace(), scene, version
    )
    item = row.state_json["draftTimeline"]["items"][1]
    assert (item["inFrame"], item["outFrame"], item["reviewed"]) == (24, 144, False)
