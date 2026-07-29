from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, ValidationError, model_validator

from viraldy.modules.ai_gateway.public import OpenAICompatibleClient, extract_message_json
from viraldy.platform.config.settings import Settings
from viraldy.shared.errors.base import AppError


class AdaptationGuidanceItem(BaseModel):
    element: str
    reason: str
    evidence_ids: list[str] = Field(default_factory=list)


class AdaptationConcept(BaseModel):
    id: str
    name: str
    angle: str
    buyer_persona: str
    creator_persona: str
    hook: str
    opening_visual: str
    demo_sequence: list[str] = Field(min_length=3)
    proof: str
    cta: str
    risks: list[dict[str, object]] = Field(default_factory=list)
    test_hypothesis: str


class AdaptationOutput(BaseModel):
    keep: list[AdaptationGuidanceItem]
    change: list[AdaptationGuidanceItem]
    avoid: list[AdaptationGuidanceItem]
    concepts: list[AdaptationConcept]

    @model_validator(mode="after")
    def validate_concept_count(self) -> AdaptationOutput:
        if len(self.concepts) != 3:
            raise ValueError("Adaptation output must include exactly three concepts.")
        return self


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
    ) -> AdaptationOutput:
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
                        "Return only JSON with keep, change, avoid, and exactly three "
                        "differentiated concepts. Each concept must differ on persona, pain, "
                        "mechanism, proof, creator style, or offer framing. "
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
            "response_format": {"type": "json_object"},
        }
        if self._settings.ai_max_output_tokens is not None:
            payload["max_tokens"] = self._settings.ai_max_output_tokens
        raw = extract_message_json(self._client.chat_json(payload))
        return _validate(raw)


def _validate(payload: dict[str, Any]) -> AdaptationOutput:
    try:
        return AdaptationOutput.model_validate(payload)
    except ValidationError as exc:
        raise AppError(
            "ADAPTATION_OUTPUT_INVALID",
            "Live provider returned invalid adaptation output.",
            details={"errors": exc.errors()},
        ) from exc
