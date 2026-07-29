from __future__ import annotations

from viraldy.modules.campaign_packs.requirements import (
    CompiledRequirementsSnapshotV2,
    CompiledRequirementV2,
    compile_campaign_requirements,
    compile_requirements,
    compiled_requirements_to_json,
    parse_compiled_requirements_snapshot,
)

CompiledRequirementV1 = CompiledRequirementV2

__all__ = [
    "CompiledRequirementV1",
    "CompiledRequirementV2",
    "CompiledRequirementsSnapshotV2",
    "compile_campaign_requirements",
    "compile_requirements",
    "compiled_requirements_to_json",
    "parse_compiled_requirements_snapshot",
]
