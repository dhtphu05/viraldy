import asyncio
import base64
import json
import math
import os
import random
import re
from typing import Any, Protocol

import httpx

from ..provider_execution import ProviderExecutionEvidence, observe_response
from .config import get_gemini_model
from .errors import SmartRemakeError

# Gemini answers 429 for both the per-minute and per-day quota, and 5xx for
# transient capacity problems. Both are worth retrying; a wrong prompt (400) is
# not.
RETRYABLE_STATUS = {429, 500, 502, 503, 504}
GEMINI_MAX_ATTEMPTS = 4


GEMINI_BILLING_HINT = (
    "Rejected for billing reasons (prepaid balance or project quota), not rate limiting. "
    "Top up or switch the project to pay-as-you-go in AI Studio — retrying will not help."
)

_BILLING_MARKERS = (
    "prepayment credits are depleted",
    "billing account",
    "billing is not enabled",
    "quota exceeded for quota metric",
    "exceeded your current quota",
    "free tier",
)


def _is_billing_failure(response: Any) -> bool:
    """Distinguish an empty wallet from a traffic burst; both arrive as 429."""
    try:
        body = response.text or ""
    except Exception:
        return False
    lowered = body.lower()
    return any(marker in lowered for marker in _BILLING_MARKERS)


def _retry_delay_seconds(response: Any, attempt: int) -> float:
    """Honour Retry-After when Gemini sends it, else exponential backoff."""
    header = ""
    try:
        header = (response.headers.get("retry-after") or "").strip()
    except Exception:
        header = ""
    if header:
        try:
            return max(0.0, min(60.0, float(header)))
        except ValueError:
            pass
    # 2s, 4s, 8s (+ jitter) so parallel callers don't retry in lockstep.
    return min(30.0, 2 ** attempt) + random.uniform(0, 0.5)


class SmartRemakeGeminiClient(Protocol):
    async def generate_json(
        self,
        *,
        system_instruction: str,
        prompt: str,
        media: list[dict[str, Any]] | None = None,
    ) -> Any:
        ...


def parse_llm_json(text: str) -> Any:
    raw = _json_candidate(text)
    raw_prefix = raw[:500]
    raw_suffix = raw[-500:] if len(raw) > 500 else raw
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        repaired = _repair_common_json_errors(raw)
        if repaired is not None:
            return repaired
        raise SmartRemakeError(
            f"Failed to parse Gemini JSON: {exc.msg}",
            "SMART_REMAKE_GEMINI_ERROR",
            {"line": exc.lineno, "column": exc.colno, "rawPrefix": raw_prefix, "rawSuffix": raw_suffix},
        ) from exc


def _repair_common_json_errors(raw: str) -> Any | None:
    """Recover only unambiguous comma mistakes from an otherwise JSON response."""
    candidate = re.sub(r",(\s*[}\]])", r"\1", raw)
    for _ in range(8):
        try:
            return json.loads(candidate)
        except json.JSONDecodeError as exc:
            if exc.msg != "Expecting ',' delimiter":
                return None
            position = exc.pos
            if position <= 0 or position >= len(candidate):
                return None
            before = candidate[:position].rstrip()
            after = candidate[position:].lstrip()
            if not before or not after:
                return None
            candidate = f"{before}, {after}"
    return None


def _json_candidate(text: str) -> str:
    raw = text.strip()
    fenced = re.match(r"^```(?:json)?\s*(.*?)\s*```$", raw, re.DOTALL | re.IGNORECASE)
    if fenced:
        raw = fenced.group(1).strip()

    object_start = raw.find("{")
    array_start = raw.find("[")
    starts = [index for index in (object_start, array_start) if index >= 0]
    if not starts:
        return raw
    start = min(starts)
    end_char = "}" if raw[start] == "{" else "]"
    end = raw.rfind(end_char)
    if end > start:
        return raw[start : end + 1].strip()
    return raw[start:].strip()


class HttpGeminiClient:
    def __init__(
        self, *, max_attempts: int = GEMINI_MAX_ATTEMPTS, repair_json: bool = True,
        max_output_tokens: int = 16384, timeout_seconds: float | None = None,
        thinking_budget: int | None = None,
    ) -> None:
        if type(max_output_tokens) is not int or max_output_tokens <= 0:
            raise ValueError("Gemini output token limit must be a positive integer.")
        if timeout_seconds is not None and (
            not math.isfinite(timeout_seconds) or timeout_seconds <= 0
        ):
            raise ValueError("Gemini timeout must be a positive number of seconds.")
        if thinking_budget is not None and (
            type(thinking_budget) is not int or thinking_budget < 0
        ):
            raise ValueError("Gemini thinking budget must be a nonnegative integer.")
        self.max_attempts = max(1, min(max_attempts, GEMINI_MAX_ATTEMPTS))
        self.repair_json = repair_json
        self.max_output_tokens = max_output_tokens
        self.timeout_seconds = timeout_seconds
        self.thinking_budget = thinking_budget
        self.last_usage: dict[str, Any] = {}
        self.last_request_id: str | None = None
        self.last_execution_evidence: ProviderExecutionEvidence | None = None
        self.last_finish_reason: str | None = None

    async def generate_json(
        self,
        *,
        system_instruction: str,
        prompt: str,
        media: list[dict[str, Any]] | None = None,
    ) -> Any:
        self.last_usage, self.last_request_id, self.last_execution_evidence = {}, None, None
        self.last_finish_reason = None
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise SmartRemakeError("GEMINI_API_KEY is not configured.", "SMART_REMAKE_GEMINI_ERROR")

        request = self._request_text(
            api_key=api_key,
            system_instruction=system_instruction,
            prompt=prompt,
            media=media,
        )
        if self.timeout_seconds is None:
            text = await request
        else:
            try:
                async with asyncio.timeout(self.timeout_seconds):
                    text = await request
            except TimeoutError as exc:
                raise SmartRemakeError(
                    f"Gemini request timed out after {self.timeout_seconds:g} seconds.",
                    "SMART_REMAKE_GEMINI_ERROR",
                ) from exc
        try:
            return parse_llm_json(text)
        except SmartRemakeError as first_error:
            if not self.repair_json:
                raise
            retry_prompt = (
                f"{prompt}\n\n"
                "The previous response was invalid JSON and could not be parsed. "
                "Return the same schema again as strict JSON only. "
                "Use double quotes for every string, escape quotes inside strings, "
                "include commas between every object property and array item, and do not include markdown.\n"
                f"Parser error: {first_error}\n"
                f"Invalid response excerpt:\n{_json_candidate(text)[:6000]}"
            )
            retry_text = await self._request_text(
                api_key=api_key,
                system_instruction=system_instruction,
                prompt=retry_prompt,
                media=media,
            )
            return parse_llm_json(retry_text)

    async def _request_text(
        self,
        *,
        api_key: str,
        system_instruction: str,
        prompt: str,
        media: list[dict[str, Any]] | None = None,
    ) -> str:
        model = get_gemini_model()
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        parts: list[dict[str, Any]] = [{"text": prompt}]
        for item in media or []:
            parts.append(
                {
                    "inline_data": {
                        "mime_type": item["mime_type"],
                        "data": base64.b64encode(item["bytes"]).decode("ascii"),
                    }
                }
            )

        body = {
            "system_instruction": {"parts": [{"text": system_instruction}]},
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.1,
                "maxOutputTokens": self.max_output_tokens,
                **({"thinkingConfig": {"thinkingBudget": self.thinking_budget}}
                   if self.thinking_budget is not None else {}),
            },
        }

        try:
            timeout_seconds = min(
                300.0,
                max(5.0, float(os.getenv("SMART_REMAKE_GEMINI_TIMEOUT_SECONDS", "120"))),
            )
        except (TypeError, ValueError):
            timeout_seconds = 120.0
        if self.timeout_seconds is not None:
            timeout_seconds = self.timeout_seconds

        response = None
        for attempt in range(1, self.max_attempts + 1):
            self.last_execution_evidence = None
            try:
                async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                    response = await client.post(url, params={"key": api_key}, json=body)
                    self.last_execution_evidence = observe_response(
                        response, provider="google", model=model,
                        operation="google.generate_content", owned_transport=True,
                    )
            except httpx.TimeoutException as exc:
                raise SmartRemakeError(
                    f"Gemini request timed out after {timeout_seconds:.0f} seconds.",
                    "SMART_REMAKE_GEMINI_ERROR",
                ) from exc
            except httpx.HTTPError as exc:
                raise SmartRemakeError(
                    "Gemini network request failed.", "SMART_REMAKE_GEMINI_ERROR"
                ) from exc

            if response.status_code not in RETRYABLE_STATUS or attempt == self.max_attempts:
                break

            if _is_billing_failure(response):
                # 429 covers both "too fast" and "out of credits". The second
                # returns the same answer forever, so retrying only delays the
                # real error by half a minute.
                print("[Gemini] " + GEMINI_BILLING_HINT)
                break

            # 429 here is usually the per-minute quota, not the daily one: a
            # batch of variants fires several calls at once and trips it. Wait
            # out the window instead of failing the whole batch.
            delay = _retry_delay_seconds(response, attempt)
            print(
                f"[Gemini] HTTP {response.status_code} on attempt {attempt}/{GEMINI_MAX_ATTEMPTS}, "
                f"retrying in {delay:.1f}s"
            )
            await asyncio.sleep(delay)

        if response is None or response.status_code >= 400:
            status = response.status_code if response is not None else 0
            detail = ""
            if status == 429:
                detail = (
                    f" {GEMINI_BILLING_HINT}"
                    if response is not None and _is_billing_failure(response)
                    else " Rate limit hit after retrying — reduce concurrency or raise the quota."
                )
            raise SmartRemakeError(
                f"Gemini request failed with status {status}.{detail}",
                "SMART_REMAKE_GEMINI_ERROR",
            )
        payload = response.json()
        usage = payload.get("usageMetadata")
        self.last_usage = {
            key: value for key, value in (usage or {}).items()
            if isinstance(key, str) and type(value) in {int, float}
        } if isinstance(usage, dict) else {}
        request_id = payload.get("responseId")
        self.last_request_id = request_id[:256] if isinstance(request_id, str) else None
        candidates = payload.get("candidates")
        if not isinstance(candidates, list) or not candidates:
            raise SmartRemakeError("Gemini returned no JSON text.", "SMART_REMAKE_GEMINI_ERROR")
        reason = candidates[0].get("finishReason")
        if isinstance(reason, str) and reason in {"STOP", "MAX_TOKENS"}:
            self.last_finish_reason = reason
        if self.last_finish_reason == "MAX_TOKENS":
            raise SmartRemakeError(
                "Gemini reached its output limit before completing the response.",
                "SMART_REMAKE_GEMINI_OUTPUT_TRUNCATED",
            )
        parts = candidates[0].get("content", {}).get("parts", [])
        text = next(
            (part.get("text") for part in parts if isinstance(part, dict) and part.get("text") and not part.get("thought")),
            None,
        )
        if not isinstance(text, str):
            raise SmartRemakeError("Gemini returned no JSON text.", "SMART_REMAKE_GEMINI_ERROR")
        return text
