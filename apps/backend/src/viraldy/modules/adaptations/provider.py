from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from viraldy.modules.adaptations.contracts import AdaptationOutputV2
from viraldy.modules.ai_gateway.public import OpenAICompatibleClient, extract_message_json
from viraldy.platform.config.settings import Settings
from viraldy.shared.errors.base import AppError


class LiveAdaptationProvider:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = OpenAICompatibleClient(settings)

    def generate(
        self,
        product: dict[str, object],
        dna_json: dict[str, object],
        objective: str,
        target_market: str,
        target_buyer: dict[str, object],
        constraints: dict[str, object],
    ) -> AdaptationOutputV2:
        if not self._settings.ai_base_url or not self._settings.ai_text_model:
            raise AppError(
                "AI_PROVIDER_NOT_CONFIGURED",
                "Provider adaptation requires AI_BASE_URL and AI_TEXT_MODEL.",
                status_code=503,
            )
        if self._settings.ai_mode == "live" and not self._settings.ai_api_key:
            raise AppError(
                "AI_PROVIDER_NOT_CONFIGURED",
                "Live adaptation requires AI_API_KEY.",
                status_code=503,
            )
        payload: dict[str, Any] = {
            "model": self._settings.ai_text_model,
            "messages": [
                {
                    "role": "user",
                    "content": (
                        "Adapt this Creative DNA to the product without copying the original. "
                        "Return only JSON matching AdaptationOutputV2. Include schema_version "
                        "adaptation_v2, guidance, exactly three differentiated concepts, and "
                        "uncertainties. Each concept must differ on at least two axes across "
                        "buyer persona/pain, angle, creator style, demo mechanism, proof "
                        "mechanism, offer framing, or opening mechanism. Use only supplied "
                        "Creative DNA evidence IDs when setting source_evidence_ids. "
                        "Do not predict virality, sales, or GMV.\n"
                        f"Product: {product}\n"
                        f"Creative DNA: {dna_json}\n"
                        f"Objective: {objective}\n"
                        f"Target market: {target_market}\n"
                        f"Target buyer: {target_buyer}\n"
                        f"Constraints: {constraints}"
                    ),
                }
            ],
            "response_format": _response_format(self._settings),
        }
        if self._settings.ai_max_output_tokens is not None:
            payload["max_tokens"] = self._settings.ai_max_output_tokens
        raw = extract_message_json(self._client.chat_json(payload))
        return _validate(raw)


def _validate(payload: dict[str, Any]) -> AdaptationOutputV2:
    try:
        return AdaptationOutputV2.model_validate(payload)
    except ValidationError as exc:
        raise AppError(
            "ADAPTATION_OUTPUT_INVALID",
            "Live provider returned invalid adaptation output.",
            details={"errors": exc.errors()},
        ) from exc


def _response_format(settings: Settings) -> dict[str, object]:
    if not settings.ai_supports_json_schema:
        return {"type": "json_object"}
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "AdaptationOutputV2",
            "schema": AdaptationOutputV2.model_json_schema(),
            "strict": True,
        },
    }
