from __future__ import annotations

from viraldy.modules.media_analysis.json_safety import sanitize_postgres_json


def test_sanitize_postgres_json_removes_null_characters_recursively() -> None:
    payload = {
        "spoken_text": "\x00measure before ordering",
        "nested": [{"overlay_text": "fit\x00 check"}, {"safe": "line\nbreak"}],
        "count": 1,
    }

    assert sanitize_postgres_json(payload) == {
        "spoken_text": "measure before ordering",
        "nested": [{"overlay_text": "fit check"}, {"safe": "line\nbreak"}],
        "count": 1,
    }
