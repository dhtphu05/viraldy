from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class JobType(StrEnum):
    MEDIA_ANALYSIS = "media_analysis"
    CREATIVE_DNA_BUILD = "creative_dna_build"
    TIKTOK_SCORE_RUN = "tiktok_score_run"
    PREFLIGHT_RUN = "preflight_run"
    PATTERN_KIT_EXTRACT = "pattern_kit_extract"
    VIRAL_KIT_COMPOSE = "viral_kit_compose"
    CAMPAIGN_PACK_GENERATE = "campaign_pack_generate"
    STORYBOARD_GENERATE = "storyboard_generate"
    CONCEPT_VIDEO_GENERATE = "concept_video_generate"
    RETENTION_CLEANUP = "retention_cleanup"


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
    JobType.MEDIA_ANALYSIS.value: JobDefinition(
        job_type=JobType.MEDIA_ANALYSIS,
        queue="default",
        max_attempts=3,
        soft_timeout_seconds=240,
        hard_timeout_seconds=300,
        required_stages=("loading_asset", "probing_media", "persisting_results"),
        optional_stages=("extracting_visual_evidence",),
        result_subject_type="asset",
    ),
    JobType.CREATIVE_DNA_BUILD.value: JobDefinition(
        job_type=JobType.CREATIVE_DNA_BUILD,
        queue="default",
        max_attempts=3,
        soft_timeout_seconds=300,
        hard_timeout_seconds=360,
        required_stages=("loading_asset", "probing_media", "building_creative_dna"),
        optional_stages=("extracting_visual_evidence",),
        result_subject_type="reference",
    ),
    JobType.TIKTOK_SCORE_RUN.value: JobDefinition(
        job_type=JobType.TIKTOK_SCORE_RUN,
        queue="default",
        max_attempts=3,
        soft_timeout_seconds=300,
        hard_timeout_seconds=360,
        required_stages=("loading_asset", "probing_media", "calculating_score"),
        optional_stages=("extracting_visual_evidence",),
        result_subject_type="tiktok_score_run",
    ),
    JobType.PREFLIGHT_RUN.value: JobDefinition(
        job_type=JobType.PREFLIGHT_RUN,
        queue="default",
        max_attempts=3,
        soft_timeout_seconds=300,
        hard_timeout_seconds=360,
        required_stages=("loading_asset", "probing_media", "checking_brief_alignment"),
        optional_stages=("extracting_visual_evidence",),
        result_subject_type="preflight_run",
    ),
}


def _workflow_definition(
    job_type: JobType,
    *,
    queue: str = "default",
    max_attempts: int = 3,
    timeout_seconds: int = 360,
    required_stages: tuple[str, ...] = (
        "loading_sources",
        "running_operation",
        "persisting_results",
    ),
    result_subject_type: str,
) -> JobDefinition:
    return JobDefinition(
        job_type=job_type,
        queue=queue,
        max_attempts=max_attempts,
        soft_timeout_seconds=timeout_seconds - 60,
        hard_timeout_seconds=timeout_seconds,
        required_stages=required_stages,
        optional_stages=(),
        result_subject_type=result_subject_type,
    )


JOB_DEFINITIONS.update(
    {
        JobType.PATTERN_KIT_EXTRACT.value: _workflow_definition(
            JobType.PATTERN_KIT_EXTRACT,
            result_subject_type="pattern_kit_version",
        ),
        JobType.VIRAL_KIT_COMPOSE.value: _workflow_definition(
            JobType.VIRAL_KIT_COMPOSE,
            result_subject_type="viral_kit_version",
        ),
        JobType.CAMPAIGN_PACK_GENERATE.value: _workflow_definition(
            JobType.CAMPAIGN_PACK_GENERATE,
            result_subject_type="campaign_pack_version",
        ),
        JobType.STORYBOARD_GENERATE.value: _workflow_definition(
            JobType.STORYBOARD_GENERATE,
            timeout_seconds=420,
            result_subject_type="generation_run",
        ),
        JobType.CONCEPT_VIDEO_GENERATE.value: _workflow_definition(
            JobType.CONCEPT_VIDEO_GENERATE,
            timeout_seconds=900,
            result_subject_type="generation_run",
        ),
        JobType.RETENTION_CLEANUP.value: _workflow_definition(
            JobType.RETENTION_CLEANUP,
            queue="maintenance",
            max_attempts=1,
            required_stages=("selecting_expired_records", "deleting_objects", "persisting_results"),
            result_subject_type="retention_run",
        ),
    }
)

LEGACY_JOB_TYPE_ALIASES: dict[str, str] = {
    "process_asset": JobType.MEDIA_ANALYSIS.value,
    "analyze_reference": JobType.CREATIVE_DNA_BUILD.value,
    "score_tiktok_asset": JobType.TIKTOK_SCORE_RUN.value,
    "run_ugc_preflight": JobType.PREFLIGHT_RUN.value,
}


def normalize_job_type(job_type: str) -> str:
    return LEGACY_JOB_TYPE_ALIASES.get(job_type, job_type)


def equivalent_job_types(job_type: str) -> tuple[str, ...]:
    normalized = normalize_job_type(job_type)
    legacy = tuple(
        alias for alias, canonical in LEGACY_JOB_TYPE_ALIASES.items() if canonical == normalized
    )
    return (normalized, *legacy)


def get_job_definition(job_type: str) -> JobDefinition:
    return JOB_DEFINITIONS[normalize_job_type(job_type)]
