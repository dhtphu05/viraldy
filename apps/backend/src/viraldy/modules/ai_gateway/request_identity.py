from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence


def stable_json_hash(value: object) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def structured_input_hash(
    *,
    context_json: str,
    runtime_examples_json: str | None,
    images: Sequence[Mapping[str, str]],
) -> str:
    return stable_json_hash(
        {
            "context_sha256": _text_hash(context_json),
            "runtime_examples_sha256": (
                _text_hash(runtime_examples_json)
                if runtime_examples_json is not None
                else None
            ),
            "images": [dict(image) for image in images],
        }
    )


def structured_request_hash(
    *,
    operation: str,
    model: str,
    prompt_version: str | None,
    schema_version: str,
    input_hash: str,
) -> str:
    return stable_json_hash(
        {
            "operation": operation,
            "model": model,
            "prompt_version": prompt_version,
            "schema_version": schema_version,
            "input_hash": input_hash,
        }
    )


def _text_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
