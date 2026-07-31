from __future__ import annotations

from collections.abc import Mapping


def require_openai_live_opt_in(environment: Mapping[str, str]) -> None:
    import pytest

    if not environment.get("OPENAI_API_KEY", "").strip():
        pytest.skip("OPENAI_API_KEY is not configured")
    if environment.get("VIRALDY_RUN_OPENAI_LIVE_TESTS") != "1":
        pytest.skip(
            "set VIRALDY_RUN_OPENAI_LIVE_TESTS=1 to opt in to live OpenAI tests"
        )
