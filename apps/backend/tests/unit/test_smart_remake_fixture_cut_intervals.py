from __future__ import annotations

import pytest

from viraldy.modules.smart_remake.engine.reference_analyzer import (
    analyze_reference_video,
    resolve_source_cut_semantics,
    validate_source_analysis,
)
from viraldy.modules.smart_remake.engine.schemas import UploadedMedia
from viraldy.modules.smart_remake.fixture import FixtureGeminiClient


@pytest.mark.asyncio
async def test_fixture_recovers_all_measured_intervals_beyond_four_canned_beats():
    """The bottle demo has seven measured intervals inside two render scenes."""
    client = FixtureGeminiClient()
    reference = UploadedMedia(bytes=b"owned fixture source", mime_type="video/mp4")
    original = await analyze_reference_video(
        target_duration=8, prompt=None, description=None,
        reference_video=reference, gemini=client,
    )
    cuts = [0, 50, 77, 96, 123, 149, 174, 192]
    result = await resolve_source_cut_semantics(
        analysis={**original, "sourceCutDetection": {
            "requiresSemanticReanalysis": True, "cutFrames": cuts,
        }},
        target_duration=8, prompt=None, description=None,
        reference_video=reference, gemini=client,
        requested_cut_frames=[0, 96, 192],
    )
    assert [(round(shot["startSecond"] * 24), round(shot["endSecond"] * 24))
            for shot in result["sourceShots"]] == list(zip(cuts, cuts[1:], strict=False))
    validate_source_analysis(result, target_duration=8)
    assert result["sourceCutDetection"]["requiresSemanticReanalysis"] is False
