"""Bounded source-audio observations for display, separate from generation directions."""

from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError


class SourceAudioObservation(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    schemaVersion: Literal[1] = 1
    speech: Literal["present", "not_detected", "unclear"]
    transcript: str | None = Field(default=None, max_length=4000)
    language: str | None = Field(default=None, max_length=40)
    music: Literal["present", "not_detected", "unclear"]
    description: str | None = Field(default=None, max_length=300)
    pace: Literal["slow", "medium", "fast", "unclear"] | None = None


def normalize_source_audio(value: Any) -> dict[str, Any] | None:
    """Missing or malformed optional observations never block the visual pipeline."""
    if not isinstance(value, dict):
        return None
    try:
        parsed = SourceAudioObservation.model_validate(value).model_dump(exclude_none=True)
    except ValidationError:
        return None
    for key in ("transcript", "language", "description"):
        if key in parsed:
            text = re.sub(r"https?://\S+", "[liên kết]", " ".join(parsed[key].split()))
            if text:
                parsed[key] = text
            else:
                parsed.pop(key)
    if parsed["speech"] != "present":
        parsed.pop("transcript", None)
        parsed.pop("language", None)
    return parsed


def source_audio_prompt(*, transcript_limit: int) -> str:
    return (
        "Optionally return sourceAudio for read-only observations of the uploaded video's "
        "audible track, separate from audioPlan and all generation directions. Its JSON shape "
        'is {"schemaVersion":1,"speech":"present|not_detected|unclear",'
        '"music":"present|not_detected|unclear","transcript":"optional",'
        '"language":"optional","description":"optional",'
        '"pace":"slow|medium|fast|unclear"}. Use one literal enum value per field. '
        "Only say present when heard; use not_detected when not recognized and unclear when "
        "the track cannot be judged. Never infer audio from visible mouth movement or captions. "
        "transcript must contain only words actually heard in their original language; "
        "do not translate, paraphrase, complete missing words, copy on-screen text, or invent "
        f"speech. Keep the heard transcript excerpt within {transcript_limit} characters, "
        "language within 40 characters, and description within 300 characters. Omit transcript "
        "and language unless speech is present and the words are intelligible. Describe music, "
        "ambience and audible rhythm conservatively; do not invent BPM, exact timestamps, "
        "song identity or a voice identity. Omit sourceAudio if audio cannot be observed. "
        "These source observations never authorize copying speech into generated output."
    )
