from __future__ import annotations

import pytest

from viraldy.modules.smart_remake.engine.prompt_edits import scene_edit_directions


def test_minor_edit_inside_long_single_line_keeps_context_without_full_snapshot() -> None:
    original = (
        "Start " + "reference scene context " * 130 + "OLD ACTION" + " ending scene context" * 130
    )
    current = original.replace("OLD ACTION", "UNIQUE NEW ACTION")
    direction = scene_edit_directions(
        {"promptEdited": True, "videoPrompt": current, "originalVideoPrompt": original}
    )
    assert "UNIQUE NEW ACTION" in direction
    assert len(direction) < 400


def test_all_three_changed_fields_are_included_with_their_roles() -> None:
    scene = {"promptEdited": True}
    for field, marker in [
        ("prompt", "SCENE MARKER"),
        ("imagePrompt", "IMAGE MARKER"),
        ("videoPrompt", "VIDEO MARKER"),
    ]:
        scene[field] = marker
        scene[f"original{field[0].upper()}{field[1:]}"] = "original"
    direction = scene_edit_directions(scene)
    assert all(marker in direction for marker in ["SCENE MARKER", "IMAGE MARKER", "VIDEO MARKER"])


def test_unedited_original_fields_do_not_consume_direction_budget() -> None:
    snapshot = "Compiler instruction " * 400
    direction = scene_edit_directions(
        {"promptEdited": True, "videoPrompt": snapshot, "originalVideoPrompt": snapshot}
    )
    assert direction == ""


def test_extensive_changes_are_rejected_instead_of_silently_truncated() -> None:
    with pytest.raises(Exception, match="focused"):
        scene_edit_directions(
            {
                "promptEdited": True,
                "videoPrompt": "new direction " * 500,
                "originalVideoPrompt": "old direction " * 500,
            }
        )
