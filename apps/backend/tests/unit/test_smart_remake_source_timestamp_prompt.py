import json

from viraldy.modules.smart_remake.engine.prompts import build_reference_analysis_prompt


def test_source_analysis_requires_elapsed_seconds_instead_of_timecode_fractions():
    system, prompt = build_reference_analysis_prompt(target_duration=22.75, has_video=True)

    assert "numeric elapsed seconds" in system
    assert "1 second = 1.0" in system
    assert "12 seconds = 12.0" in system
    assert "22.75 seconds = 22.75" in system
    assert "MM.SS" in system and "normalized 0-1" in system
    assert "contiguous coverage from 0 to the actual full visual source end" in prompt
    assert "durationSeconds = endSecond - startSecond" in prompt
    assert "motionBeats use the same absolute source clock" in prompt


def test_supplemental_intervals_include_exact_numeric_seconds_for_every_frame_range():
    cuts = [0, 192, 273, 384, 546]
    _, prompt = build_reference_analysis_prompt(
        target_duration=22.75,
        has_video=True,
        source_cut_frames=cuts,
    )

    interval_line = next(
        line
        for line in prompt.splitlines()
        if line.startswith("Required source interval timestamps in numeric seconds: ")
    )
    intervals = json.loads(interval_line.split(": ", 1)[1])
    assert intervals == [
        {"startSecond": 0.0, "endSecond": 8.0, "durationSeconds": 8.0},
        {"startSecond": 8.0, "endSecond": 11.375, "durationSeconds": 3.375},
        {"startSecond": 11.375, "endSecond": 16.0, "durationSeconds": 4.625},
        {"startSecond": 16.0, "endSecond": 22.75, "durationSeconds": 6.75},
    ]
    assert "exactly one sourceShot per adjacent frame range" in prompt
    assert "A provider boundary is not a new visual scene or a camera cut" in prompt


def test_output_target_does_not_truncate_the_initial_source_analysis_clock():
    _, prompt = build_reference_analysis_prompt(target_duration=8, has_video=True)

    assert "Analyze the full uploaded reference video from beginning to end" in prompt
    assert "contiguous coverage from 0 to the actual full visual source end" in prompt
    assert "Required source interval timestamps" not in prompt
