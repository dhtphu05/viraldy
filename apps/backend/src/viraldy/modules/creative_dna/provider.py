from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import TypeGuard
from uuid import UUID

from pydantic import BaseModel

from viraldy.modules.ai_gateway.context import (
    EvidenceItemForModelV1,
    ViraldyOperationContextV1,
)
from viraldy.modules.ai_gateway.execution import execute_structured_operation
from viraldy.modules.ai_gateway.operations import AiOperationName
from viraldy.modules.ai_gateway.prompt_packages import get_prompt_package
from viraldy.modules.creative_dna.contracts import CreativeDnaV1
from viraldy.modules.media_analysis.models import EvidenceItemModel
from viraldy.modules.products.contracts import ProductContextV1
from viraldy.platform.config.settings import Settings
from viraldy.shared.errors.base import AppError

_GROUNDED_STATUSES = frozenset({"observed", "inferred", "not_present"})


@dataclass(frozen=True, slots=True)
class CreativeDnaProviderExecution:
    output: CreativeDnaV1
    provider_request_id: str | None
    http_status: int | None
    latency_ms: int | None
    usage_json: dict[str, object]
    repair_attempt_count: int


class LiveCreativeDnaProvider:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def build_with_metadata(
        self,
        *,
        workspace_id: UUID,
        actor_user_id: UUID | None,
        asset_id: UUID,
        asset_version_id: UUID,
        reference_id: UUID | None,
        evidence: list[EvidenceItemModel],
        model_run_id: UUID,
        media_duration_ms: int | None,
        product_context: ProductContextV1 | None,
        product_context_version: int | None,
    ) -> CreativeDnaProviderExecution:
        if self._settings.ai_mode == "fixture":
            raise AppError(
                "CREATIVE_DNA_AI_MODE_INVALID",
                "The AI Creative DNA provider cannot run in fixture mode.",
            )
        prompt = get_prompt_package(AiOperationName.CREATIVE_DNA_BUILD)
        evidence_catalog = build_creative_dna_evidence_catalog(
            evidence,
            workspace_id=workspace_id,
            asset_id=asset_id,
            asset_version_id=asset_version_id,
            media_duration_ms=media_duration_ms,
        )
        context = ViraldyOperationContextV1(
            operation=AiOperationName.CREATIVE_DNA_BUILD,
            request_id=str(model_run_id),
            workspace_id=workspace_id,
            actor_user_id=actor_user_id,
            product_context=product_context,
            product_context_version=product_context_version,
            source_artifact_ids=[asset_id],
            source_version_ids=[asset_version_id],
            evidence_catalog=evidence_catalog,
            operation_payload={
                "asset_id": str(asset_id),
                "asset_version_id": str(asset_version_id),
                "reference_id": str(reference_id) if reference_id else None,
                "media_duration_ms": media_duration_ms,
            },
            schema_version=prompt.output_schema_version,
            prompt_version=prompt.prompt_version,
        )
        validator = build_creative_dna_output_validator(
            evidence,
            media_duration_ms=media_duration_ms,
        )
        result = execute_structured_operation(
            self._settings,
            context,
            CreativeDnaV1,
            output_validator=validator,
        )
        output = normalize_creative_dna_evidence_ids(
            CreativeDnaV1.model_validate(result.parsed_output),
            {item.id for item in evidence},
        )
        validator(output)
        return CreativeDnaProviderExecution(
            output=output,
            provider_request_id=result.provider_request_id,
            http_status=result.http_status,
            latency_ms=result.latency_ms,
            usage_json=result.usage.model_dump(mode="json"),
            repair_attempt_count=result.repair_attempt_count,
        )


def build_creative_dna_evidence_catalog(
    evidence: list[EvidenceItemModel],
    *,
    workspace_id: UUID,
    asset_id: UUID,
    asset_version_id: UUID,
    media_duration_ms: int | None,
) -> list[EvidenceItemForModelV1]:
    if not evidence:
        raise AppError(
            "CREATIVE_DNA_EVIDENCE_INVALID",
            "Creative DNA requires persisted evidence.",
        )
    catalog: list[EvidenceItemForModelV1] = []
    seen_ids: set[UUID] = set()
    for item in evidence:
        if item.workspace_id != workspace_id or item.asset_version_id != asset_version_id:
            raise AppError(
                "CREATIVE_DNA_EVIDENCE_INVALID",
                "Creative DNA evidence must belong to the requested workspace and asset version.",
            )
        if item.id in seen_ids:
            raise AppError(
                "CREATIVE_DNA_EVIDENCE_INVALID",
                "Creative DNA evidence IDs must be unique.",
            )
        _validate_time_range(item.start_ms, item.end_ms, media_duration_ms)
        seen_ids.add(item.id)
        catalog.append(
            EvidenceItemForModelV1(
                evidence_id=item.id,
                source_artifact_id=asset_id,
                source_version_id=item.asset_version_id,
                evidence_type=item.evidence_type,
                observation_id=item.observation_id,
                start_ms=item.start_ms,
                end_ms=item.end_ms,
                value=dict(item.value_json),
                confidence=float(item.confidence) if item.confidence is not None else None,
                source=item.source,
            )
        )
    return catalog


def build_creative_dna_output_validator(
    evidence: list[EvidenceItemModel],
    *,
    media_duration_ms: int | None,
) -> Callable[[BaseModel], None]:
    allowed_evidence_ids = {item.id for item in evidence}
    allowed_timestamps = _evidence_timestamps(evidence)

    def validate(output: BaseModel) -> None:
        dna = normalize_creative_dna_evidence_ids(
            CreativeDnaV1.model_validate(output),
            allowed_evidence_ids,
        )
        _validate_grounded_collections(dna)
        payload = dna.model_dump(mode="python")
        referenced_ids: set[UUID] = set()
        output_timepoints: set[int] = set()
        output_durations: set[int] = set()
        _collect_output_provenance(
            payload,
            referenced_ids,
            output_timepoints,
            output_durations,
        )
        if not referenced_ids.issubset(allowed_evidence_ids):
            raise ValueError("Creative DNA references evidence outside the supplied catalog.")
        unsupported_timestamps = output_timepoints - allowed_timestamps
        if unsupported_timestamps:
            raise ValueError("Creative DNA contains a timestamp absent from supplied evidence.")
        if media_duration_ms is not None and any(
            timestamp > media_duration_ms for timestamp in output_timepoints
        ):
            raise ValueError("Creative DNA contains a timestamp beyond media duration.")
        if media_duration_ms is not None and any(
            duration > media_duration_ms for duration in output_durations
        ):
            raise ValueError("Creative DNA contains a duration beyond media duration.")

    return validate


def normalize_creative_dna_evidence_ids(
    output: CreativeDnaV1,
    allowed_evidence_ids: set[UUID],
) -> CreativeDnaV1:
    payload = output.model_dump(mode="python")
    _prune_foreign_evidence_ids(payload, allowed_evidence_ids)
    return CreativeDnaV1.model_validate(payload)


def _prune_foreign_evidence_ids(value: object, allowed_evidence_ids: set[UUID]) -> None:
    if isinstance(value, dict):
        raw_ids = value.get("evidence_ids")
        if isinstance(raw_ids, list):
            value["evidence_ids"] = [
                evidence_id
                for evidence_id in raw_ids
                if isinstance(evidence_id, UUID) and evidence_id in allowed_evidence_ids
            ]
        for nested in value.values():
            _prune_foreign_evidence_ids(nested, allowed_evidence_ids)
        return
    if isinstance(value, list):
        for nested in value:
            _prune_foreign_evidence_ids(nested, allowed_evidence_ids)


def _validate_grounded_collections(dna: CreativeDnaV1) -> None:
    has_ungrounded_item = (
        any(not item.evidence_ids for item in dna.claims)
        or any(not item.evidence_ids for item in dna.risks)
        or any(not item.evidence_ids for item in dna.reusable_mechanisms)
    )
    if has_ungrounded_item:
        raise ValueError(
            "Creative DNA claims, risks, and reusable mechanisms require evidence IDs."
        )


def _collect_output_provenance(
    value: object,
    evidence_ids: set[UUID],
    timepoints: set[int],
    durations: set[int],
) -> None:
    if isinstance(value, Mapping):
        raw_ids = value.get("evidence_ids")
        parsed_ids = _parse_evidence_ids(raw_ids)
        evidence_ids.update(parsed_ids)
        status = value.get("status")
        if status in _GROUNDED_STATUSES and not parsed_ids:
            raise ValueError(f"Creative DNA {status} values require evidence IDs.")
        if status == "unknown" and value.get("value") is not None:
            raise ValueError("Creative DNA unknown values must have a null value.")
        for key, nested in value.items():
            if _is_timestamp_key(str(key)):
                timestamp_value = (
                    nested.get("value") if isinstance(nested, Mapping) else nested
                )
                _collect_non_negative_time_value(
                    str(key),
                    timestamp_value,
                    timepoints=timepoints,
                    durations=durations,
                )
            _collect_output_provenance(
                nested,
                evidence_ids,
                timepoints,
                durations,
            )
        return
    if isinstance(value, list):
        for nested in value:
            _collect_output_provenance(
                nested,
                evidence_ids,
                timepoints,
                durations,
            )


def _parse_evidence_ids(value: object) -> set[UUID]:
    if not isinstance(value, list):
        return set()
    parsed: set[UUID] = set()
    for raw_id in value:
        try:
            parsed.add(UUID(str(raw_id)))
        except ValueError as exc:
            raise ValueError("Creative DNA contains an invalid evidence ID.") from exc
    return parsed


def _evidence_timestamps(evidence: list[EvidenceItemModel]) -> set[int]:
    timestamps: set[int] = set()
    for item in evidence:
        if item.start_ms is not None:
            timestamps.add(item.start_ms)
        if item.end_ms is not None:
            timestamps.add(item.end_ms)
        _collect_evidence_timestamps(item.value_json, timestamps)
    return timestamps


def _collect_evidence_timestamps(value: object, timestamps: set[int]) -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if _is_timestamp_key(str(key)) and _is_non_negative_int(nested):
                timestamps.add(int(nested))
            _collect_evidence_timestamps(nested, timestamps)
        return
    if isinstance(value, list):
        for nested in value:
            _collect_evidence_timestamps(nested, timestamps)


def _validate_time_range(
    start_ms: int | None,
    end_ms: int | None,
    media_duration_ms: int | None,
) -> None:
    if start_ms is not None and start_ms < 0:
        raise AppError("CREATIVE_DNA_EVIDENCE_INVALID", "Evidence start_ms cannot be negative.")
    if end_ms is not None and end_ms < 0:
        raise AppError("CREATIVE_DNA_EVIDENCE_INVALID", "Evidence end_ms cannot be negative.")
    if start_ms is not None and end_ms is not None and end_ms < start_ms:
        raise AppError(
            "CREATIVE_DNA_EVIDENCE_INVALID",
            "Evidence end_ms cannot be before start_ms.",
        )
    if media_duration_ms is not None and any(
        timestamp is not None and timestamp > media_duration_ms
        for timestamp in (start_ms, end_ms)
    ):
        raise AppError(
            "CREATIVE_DNA_EVIDENCE_INVALID",
            "Evidence timestamp cannot exceed media duration.",
        )


def _is_timestamp_key(key: str) -> bool:
    return key == "timestamp_ms" or key.endswith("_ms")


def _collect_non_negative_time_value(
    key: str,
    value: object,
    *,
    timepoints: set[int],
    durations: set[int],
) -> None:
    if value is None:
        return
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError("Creative DNA time values must be non-negative integers.")
    if key in {"total_visible_ms", "average_shot_duration_ms"}:
        durations.add(value)
        return
    timepoints.add(value)


def _is_non_negative_int(value: object) -> TypeGuard[int]:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0
