"""The two provider windows keep the same identity and shared physical directions."""

from __future__ import annotations

import copy

import pytest

from tests.unit.test_smart_remake_presenter_conditioning import (
    image,
    prepare_unit,
    presenter_setup,  # noqa: F401
    setup,  # noqa: F401
)
from viraldy.modules.smart_remake import image_workflow
from viraldy.modules.smart_remake.engine.video_directions import video_brief


@pytest.mark.asyncio
async def test_four_bookends_reuse_one_presenter_when_later_metadata_hides_the_actor(
    presenter_setup, monkeypatch,  # noqa: F811
):
    repair, row, operation, client, _, _, _ = presenter_setup
    opening = image((30, 20), "white")
    ending = image((30, 20), "blue")
    extracted = []

    def extract(data, frame):
        assert data == repair.media.objects["source"]
        extracted.append(frame)
        return ending if frame in {119, 191} else opening

    monkeypatch.setattr(image_workflow, "extract_layout_frame", extract)
    first = await prepare_unit(presenter_setup)
    presenter_bytes = repair.media.objects[first["storageKey"]]
    canonical = copy.deepcopy(row.context_json["presenterIdentityAnchor"])

    # These labels describe shots, and cannot remove an already established identity.
    row.context_json["referenceAnalysis"]["sourceShots"][0]["subjectPresence"] = "hands_only"
    row.context_json["referenceAnalysis"]["sourceShots"][1]["subjectPresence"] = "none"
    bookends = [first]
    for index, role in [(0, "ending"), (1, "opening"), (1, "ending")]:
        bookends.append(await prepare_unit(presenter_setup, index, role))

    assert len(client.calls) == 4
    assert all(call["character"].bytes == presenter_bytes for call in client.calls[1:])
    assert all(
        item["presenterIdentity"]["anchor"]["requestHash"] == first["requestHash"]
        for item in bookends[1:]
    )
    assert row.context_json["presenterIdentityAnchor"] == canonical
    assert bookends[1]["referenceFrame"]["frame"] == 119
    assert bookends[3]["referenceFrame"]["frame"] == 191
    assert set(operation.result_json["images"]) == {"0", "0:ending", "1", "1:ending"}
    assert 119 in extracted and 191 in extracted

    for index, role in [(0, "opening"), (0, "ending"), (1, "opening"), (1, "ending")]:
        await prepare_unit(presenter_setup, index, role)
    assert len(client.calls) == 4


def test_image_and_video_use_the_same_performer_contact_directions():
    from viraldy.modules.smart_remake.engine.performer_continuity import (
        performer_continuity_directions,
    )

    shared = performer_continuity_directions()
    image_prompt = image_workflow._image_prompt(
        {}, {"imagePrompt": "A person holds the upright cup."}, presenter_anchor=True,
    )
    video_prompt = video_brief({}, {}, ending=True)
    assert image_prompt.count(shared) == video_prompt.count(shared) == 1
    assert "release" in shared.lower()
    assert "panel" in shared.lower()
