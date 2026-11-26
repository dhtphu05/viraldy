"""Local restore may bind only to the owned server input digests."""

from __future__ import annotations

import pytest

from viraldy.modules.smart_remake.project_presentation import project_policy_fields


def context(*, character=False):
    roles = ["source", "product", *(["character"] if character else [])]
    return {
        **{f"{role}MediaHash": str(index) * 64 for index, role in enumerate(roles, start=1)},
        "p0": {
            "assets": {
                role: {"storageKey": f"secret/{role}", "mediaHash": str(index) * 64}
                for index, role in enumerate(roles, start=1)
            }
        },
    }


@pytest.mark.parametrize("character", [False, True])
def test_owned_input_hashes_are_projected_without_storage_details(character):
    public = project_policy_fields(context(character=character))
    assert public["inputMediaHashes"] == {
        "source": "1" * 64,
        "product": "2" * 64,
        **({"character": "3" * 64} if character else {}),
    }
    assert "secret/" not in str(public) and "storageKey" not in str(public)


@pytest.mark.parametrize("invalid", [None, "bad-hash", "a" * 63, "A" * 64])
def test_invalid_or_inconsistent_input_hashes_cannot_authorize_restore(invalid):
    value = context()
    value["p0"]["assets"]["source"]["mediaHash"] = invalid
    assert project_policy_fields(value)["inputMediaHashes"] is None
    value = context()
    value["sourceMediaHash"] = "f" * 64
    assert project_policy_fields(value)["inputMediaHashes"] is None


def test_historical_project_without_owned_assets_does_not_invent_hashes():
    assert project_policy_fields({"sourceMediaHash": "1" * 64})["inputMediaHashes"] is None
