from __future__ import annotations

from viraldy.api.responses.envelope import failure, success


def test_success_envelope_contract() -> None:
    envelope = success({"ok": True}, "request-id")
    assert envelope.model_dump() == {
        "data": {"ok": True},
        "meta": {"request_id": "request-id", "pagination": None},
        "error": None,
    }


def test_error_envelope_contract() -> None:
    assert failure("ASSET_NOT_FOUND", "Asset was not found.", "request-id") == {
        "data": None,
        "meta": {"request_id": "request-id"},
        "error": {
            "code": "ASSET_NOT_FOUND",
            "message": "Asset was not found.",
            "details": {},
        },
    }
