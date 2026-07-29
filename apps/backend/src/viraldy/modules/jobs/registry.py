from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class JobType(StrEnum):
    PROCESS_ASSET = "process_asset"
    ANALYZE_REFERENCE = "analyze_reference"
    SCORE_TIKTOK_ASSET = "score_tiktok_asset"
    RUN_UGC_PREFLIGHT = "run_ugc_preflight"


@dataclass(frozen=True, slots=True)
class JobDefinition:
    job_type: JobType
    queue: str
    max_attempts: int
    soft_timeout_seconds: int
    hard_timeout_seconds: int
    required_stages: tuple[str, ...]
    optional_stages: tuple[str, ...]
    result_subject_type: str


JOB_DEFINITIONS: dict[str, JobDefinition] = {
    JobType.PROCESS_ASSET.value: JobDefinition(
        job_type=JobType.PROCESS_ASSET,
        queue="default",
        max_attempts=3,
        soft_timeout_seconds=240,
        hard_timeout_seconds=300,
        required_stages=("loading_asset", "probing_media", "persisting_results"),
        optional_stages=("extracting_visual_evidence",),
        result_subject_type="asset",
    ),
    JobType.ANALYZE_REFERENCE.value: JobDefinition(
        job_type=JobType.ANALYZE_REFERENCE,
        queue="default",
        max_attempts=3,
        soft_timeout_seconds=300,
        hard_timeout_seconds=360,
        required_stages=("loading_asset", "probing_media", "building_creative_dna"),
        optional_stages=("extracting_visual_evidence",),
        result_subject_type="reference",
    ),
    JobType.SCORE_TIKTOK_ASSET.value: JobDefinition(
        job_type=JobType.SCORE_TIKTOK_ASSET,
        queue="default",
        max_attempts=3,
        soft_timeout_seconds=300,
        hard_timeout_seconds=360,
        required_stages=("loading_asset", "probing_media", "calculating_score"),
        optional_stages=("extracting_visual_evidence",),
        result_subject_type="tiktok_score_run",
    ),
    JobType.RUN_UGC_PREFLIGHT.value: JobDefinition(
        job_type=JobType.RUN_UGC_PREFLIGHT,
        queue="default",
        max_attempts=3,
        soft_timeout_seconds=300,
        hard_timeout_seconds=360,
        required_stages=("loading_asset", "probing_media", "checking_brief_alignment"),
        optional_stages=("extracting_visual_evidence",),
        result_subject_type="preflight_run",
    ),
}


def get_job_definition(job_type: str) -> JobDefinition:
    return JOB_DEFINITIONS[job_type]
