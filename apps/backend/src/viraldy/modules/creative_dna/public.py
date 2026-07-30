from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from viraldy.modules.creative_dna.contracts import CreativeDnaV1
from viraldy.modules.creative_dna.repository import CreativeDnaRepository


@dataclass(frozen=True, slots=True)
class CreativeDnaSnapshot:
    creative_dna_version_id: UUID
    asset_version_id: UUID
    dna: CreativeDnaV1
    schema_version: str


def get_creative_dna_v1(payload: dict[str, object]) -> CreativeDnaV1:
    return CreativeDnaV1.model_validate(payload)


__all__ = [
    "CreativeDnaRepository",
    "CreativeDnaSnapshot",
    "CreativeDnaV1",
    "get_creative_dna_v1",
]
