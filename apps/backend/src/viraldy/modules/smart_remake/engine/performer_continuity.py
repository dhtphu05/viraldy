"""Shared performer and hand-contact roles for conditioning images and video."""

from __future__ import annotations


def performer_continuity_directions() -> str:
    return (
        "Where a performer is visible, keep the designated target identity and outfit unchanged "
        "across shots and clip joins. Per performer in each panel, two connected arms each end "
        "in one hand. "
        "Assign one hand to support/grip the product and the other to interact; a tabletop can "
        "support its base. Release an old contact before that hand takes a new one; free a "
        "supporting hand before adjusting a lid/straw. For drinking, the support hand brings "
        "the rim/straw to the mouth; the free hand rests unless the action requires adjustment. "
        "Apply roles per performer/panel, not a two-hand limit across a split screen."
    )
