"""Known canonical-frame markers bind retained video; no cross-media clock inference."""

from __future__ import annotations

from collections.abc import Sequence

from .contracts import InspectionSubject, Observation, ObservationAnchor, ResolvedMedia, Timebase


def validate_observation_anchors(
    subject: InspectionSubject,
    media: ResolvedMedia,
    references: Sequence[ResolvedMedia],
    anchors: Sequence[ObservationAnchor],
) -> None:
    by_id = {item.id: item for item in [media, *references]}
    for anchor in anchors:
        asset = media if anchor.mediaId == media.id else by_id.get(anchor.mediaId)
        if asset is None or anchor.mediaHash != asset.mediaHash:
            raise ValueError("An observation anchor must bind existing retained media and hash.")
        if asset.mimeType.startswith("image/") or asset.fps != 24 or asset.frameCount is None:
            raise ValueError("An observation anchor requires canonical 24-fps video media.")
        bounds = subject.range if asset.id == media.id else asset.range
        clock = (
            subject.range.timebase
            if asset.id == media.id and subject.range
            else "source"
            if asset.role == "source"
            else "raw_group"
        )
        if anchor.timebase != clock:
            raise ValueError("An observation anchor uses an unrelated retained media clock.")
        if (
            anchor.frame >= asset.frameCount
            or bounds
            and not (bounds.inFrame <= anchor.frame < bounds.outFrame)
        ):
            raise ValueError("An observation anchor falls outside the retained selected range.")


def mandatory_frames(
    anchors: Sequence[ObservationAnchor],
    media: ResolvedMedia,
    timebase: Timebase,
    start: int,
    end: int,
) -> list[int]:
    return sorted(
        {
            anchor.frame
            for anchor in anchors
            if anchor.mediaId == media.id
            and anchor.mediaHash == media.mediaHash
            and anchor.timebase == timebase
            and start <= anchor.frame < end
        }
    )


def require_observed_anchors(
    anchors: Sequence[ObservationAnchor],
    observations: Sequence[Observation],
    *,
    allow_missing: bool = False,
) -> None:
    observed = {
        (item.mediaId, item.mediaHash, item.timebase, item.inFrame)
        for item in observations
        if item.inFrame is not None and item.outFrame == item.inFrame + 1
    }
    if not allow_missing and any(
        (anchor.mediaId, anchor.mediaHash, anchor.timebase, anchor.frame) not in observed
        for anchor in anchors
    ):
        raise ValueError(
            "Known observation anchors were not observed within the sampling capacity."
        )
