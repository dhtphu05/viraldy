from __future__ import annotations

from viraldy.modules.deletion.contracts import DeletionResourceType

RESOURCE_TABLES: dict[DeletionResourceType, str] = {
    DeletionResourceType.WORKSPACE: "workspaces",
    DeletionResourceType.PRODUCT: "products",
    DeletionResourceType.ASSET: "assets",
    DeletionResourceType.REFERENCE: "references",
    DeletionResourceType.CREATIVE_DNA: "creative_dna_versions",
    DeletionResourceType.PATTERN_KIT: "pattern_kits",
    DeletionResourceType.VIRAL_KIT: "viral_kits",
    DeletionResourceType.CAMPAIGN_PACK: "campaign_packs",
}

# Child-first order. The two current-version cycles are nulled before this order runs.
DELETION_ORDER: tuple[str, ...] = (
    "generation_artifacts",
    "preflight_runs",
    "recommendation_actions",
    "viral_kit_campaign_pack_links",
    "viral_kit_concept_actions",
    "viral_kit_pattern_links",
    "pattern_kit_evidence_links",
    "pattern_kit_sources",
    "pattern_kit_actions",
    "feedback_items",
    "product_events",
    "tiktok_score_runs",
    "campaign_pack_versions",
    "generation_runs",
    "campaign_packs",
    "adaptation_runs",
    "viral_kit_versions",
    "viral_kits",
    "pattern_kit_versions",
    "pattern_kits",
    "creative_dna_versions",
    "references",
    "reference_boards",
    "media_artifacts",
    "evidence_items",
    "asset_versions",
    "assets",
    "recommendations",
    "ai_model_runs",
    "processing_job_events",
    "processing_jobs",
    "products",
    "workspace_members",
    "workspaces",
)

TRACE_SUBJECT_ALIASES: dict[DeletionResourceType, frozenset[str]] = {
    DeletionResourceType.WORKSPACE: frozenset({"workspace"}),
    DeletionResourceType.PRODUCT: frozenset({"product"}),
    DeletionResourceType.ASSET: frozenset({"asset", "media_analysis"}),
    DeletionResourceType.REFERENCE: frozenset({"reference"}),
    DeletionResourceType.CREATIVE_DNA: frozenset(
        {"creative_dna", "creative_dna_version"}
    ),
    DeletionResourceType.PATTERN_KIT: frozenset(
        {"pattern_kit", "pattern_kit_version"}
    ),
    DeletionResourceType.VIRAL_KIT: frozenset({"viral_kit", "viral_kit_version"}),
    DeletionResourceType.CAMPAIGN_PACK: frozenset(
        {"campaign_pack", "campaign_pack_version"}
    ),
}

TABLE_SUBJECT_ALIASES: dict[str, frozenset[str]] = {
    "products": frozenset({"product"}),
    "assets": frozenset({"asset", "media_analysis"}),
    "references": frozenset({"reference"}),
    "creative_dna_versions": frozenset({"creative_dna", "creative_dna_version"}),
    "pattern_kits": frozenset({"pattern_kit"}),
    "pattern_kit_versions": frozenset({"pattern_kit_version"}),
    "viral_kits": frozenset({"viral_kit"}),
    "viral_kit_versions": frozenset({"viral_kit_version"}),
    "campaign_packs": frozenset({"campaign_pack"}),
    "campaign_pack_versions": frozenset({"campaign_pack_version"}),
    "generation_runs": frozenset({"generation_run"}),
    "preflight_runs": frozenset({"preflight", "preflight_run"}),
    "tiktok_score_runs": frozenset({"tiktok_score", "tiktok_score_run"}),
}


def subject_aliases(resource_type: DeletionResourceType) -> frozenset[str]:
    return TRACE_SUBJECT_ALIASES[resource_type]
