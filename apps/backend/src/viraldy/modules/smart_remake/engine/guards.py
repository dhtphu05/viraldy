from collections.abc import Mapping, Sequence
from typing import Any

from .errors import SmartRemakeSecurityError


BANNED_REQUEST_TYPES = {"GENERATE_VIDEO_REFS"}
ALLOWED_REQUEST_TYPES = {
    "GENERATE_IMAGE",
    "EDIT_IMAGE",
    "GENERATE_VIDEO",
    "REGENERATE_VIDEO",
}
FORBIDDEN_REFERENCE_VIDEO_KEYS = {
    "referencevideo",
    "referencevideourl",
    "referencevideopath",
    "referencevideostoragekey",
    "videoreference",
    "sourcereferencevideo",
}


def _normalize_key(key: str) -> str:
    return "".join(ch for ch in key.lower() if ch not in "_- ")


def _find_reference_video_leak(value: Any, seen: set[int]) -> str | None:
    if isinstance(value, Mapping):
        marker = id(value)
        if marker in seen:
            return None
        seen.add(marker)
        for key, nested in value.items():
            if _normalize_key(str(key)) in FORBIDDEN_REFERENCE_VIDEO_KEYS:
                return str(key)
            found = _find_reference_video_leak(nested, seen)
            if found:
                return found
        return None

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        marker = id(value)
        if marker in seen:
            return None
        seen.add(marker)
        for item in value:
            found = _find_reference_video_leak(item, seen)
            if found:
                return found
    return None


def assert_no_reference_video_in_render_payload(payload: Any) -> None:
    leaked_key = _find_reference_video_leak(payload, set())
    if leaked_key:
        raise SmartRemakeSecurityError(
            f"Reference video render input is forbidden in Smart Remake payload: {leaked_key}.",
            "FORBIDDEN_REFERENCE_RENDER_INPUT",
            {"key": leaked_key},
        )


def assert_allowed_request_type(request_type: str) -> None:
    if request_type in BANNED_REQUEST_TYPES or request_type not in ALLOWED_REQUEST_TYPES:
        raise SmartRemakeSecurityError(
            f"Smart Remake request type is not allowlisted: {request_type}.",
            "FORBIDDEN_REFERENCE_RENDER_INPUT",
            {"requestType": request_type},
        )


def assert_allowed_endpoint(pathname: str) -> None:
    segments = [part.strip().lower() for part in pathname.split("?")[0].split("/") if part.strip()]
    if "generate-video-refs" in segments:
        raise SmartRemakeSecurityError(
            f"Smart Remake cannot call forbidden render endpoint: {pathname}.",
            "FORBIDDEN_REFERENCE_RENDER_INPUT",
            {"pathname": pathname},
        )
    if any(left == "flow" and right == "generate" for left, right in zip(segments, segments[1:])):
        raise SmartRemakeSecurityError(
            f"Smart Remake cannot call forbidden render endpoint: {pathname}.",
            "FORBIDDEN_REFERENCE_RENDER_INPUT",
            {"pathname": pathname},
        )
