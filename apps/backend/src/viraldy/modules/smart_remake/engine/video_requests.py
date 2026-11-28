"""Dispatch a saved video model to its own validated KIE wire contract."""
from __future__ import annotations

from typing import Any

from . import kie_adapter
from .errors import SmartRemakeValidationError
from .kie_adapter import KIE_MODEL
from .wan_video_adapter import WAN_VIDEO_MODEL, build_wan_group_request, validate_wan_video_input


def canonical_video_model(model: str) -> str:
    if model in {KIE_MODEL, "veo3_lite"}:
        return KIE_MODEL
    if model == WAN_VIDEO_MODEL:
        return model
    raise SmartRemakeValidationError("Unsupported saved KIE video model.", "KIE_VALIDATION_FAILED")


def validate_video_input(model: str, data: dict[str, Any]) -> None:
    if canonical_video_model(model) == WAN_VIDEO_MODEL:
        validate_wan_video_input(data)
    else:
        kie_adapter.validate_kie_video_input(data)


def build_group_request(
    *, model: str = KIE_MODEL, audio: bool = False, resolution: str = "720P", **kwargs: Any,
) -> dict[str, Any]:
    if canonical_video_model(model) == WAN_VIDEO_MODEL:
        return build_wan_group_request(audio=audio, resolution=resolution, **kwargs)
    return kie_adapter.build_kie_group_request(**kwargs)
