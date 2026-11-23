import { apiGet, apiPost } from "@/shared/api/client";

export type TikTokAd = {
    id: string;
    first_shown_date: string | null;
    last_shown_date: string | null;
    status: string | null;
    status_statement: string | null;
    videos: Array<{ url: string | null; media_type: "video" | "image" }>;
    image_urls: string[];
    image_count: number;
    reach: string | null;
    title: string | null;
    external_url: string | null;
    call_to_action: string | null;
    advertising_objective: string | null;
    targeting_info: Record<string, unknown> | null;
    moderation_metadata: Record<string, unknown> | null;
};

export type TikTokAdResult = {
    source_id: string;
    asset_id?: string | null;
    provider_entity_id: string;
    ad: TikTokAd;
    advertiser: {
        business_id: string;
        business_name: string | null;
        country_code: string | null;
        paid_for_by: string | null;
        follower_count: number | null;
        avatar_url: string | null;
        profile_url: string | null;
    } | null;
    market_signal: {
        label: "MARKET_OBSERVED" | "MARKET_PREVALENT" | "PUBLIC_DISTRIBUTION_SIGNAL";
        scope: "public_market";
        limitations: string[];
    };
    intelligence_status?: "NOT_ANALYZED" | "QUEUED" | "PROCESSING" | "PARTIAL" | "READY" | "FAILED";
    media_state?: "METADATA_ONLY" | "DIRECT_STREAM_AVAILABLE" | "AVAILABLE_ON_SAVE" | "READY";
};

export type TikTokAdSearchResponse = {
    results: TikTokAdResult[];
    page: { has_more: boolean; next_cursor: string | null };
};

export type TikTokSearchInput = {
    search_term?: string;
    search_type?: "exact_phrase" | "fuzzy_phrase";
    date_range?: { min: string; max: string };
    country_code?: string;
    max_count?: number;
    cursor?: string;
    reach_range?: { min?: string; max?: string };
};

export type TikTokSaveReferenceInput = {
    board_id: string;
    product_id?: string | null;
    notes?: string | null;
};

export function searchTikTokAds(workspaceId: string, input: TikTokSearchInput) {
    return apiPost<TikTokAdSearchResponse>(
        `/workspaces/${workspaceId}/creative-library/search`,
        input,
    );
}

export type CreativeDirection = {
    id: string;
    adaptation_run_id: string;
    direction_number: number;
    title: string;
    payload: Record<string, unknown>;
    provenance: Record<string, unknown>;
    status: string;
};

export function listCreativeDirections(workspaceId: string, adaptationId: string) {
    return apiGet<CreativeDirection[]>(
        `/workspaces/${workspaceId}/creative-library/adaptations/${adaptationId}/directions`,
    );
}

export function selectCreativeDirection(workspaceId: string, directionId: string) {
    return apiPost<CreativeDirection>(
        `/workspaces/${workspaceId}/creative-library/directions/${directionId}/select`,
        { status: "selected" },
    );
}

export function createBatchReview(
    workspaceId: string,
    input: { objective: string; asset_ids: string[]; product_id?: string | null },
) {
    return apiPost<{ id: string; status: string }>(
        `/workspaces/${workspaceId}/creative-library/batch-reviews`,
        input,
    );
}

export type CreativeFamily = {
    id: string;
    scope: "MARKET" | "WORKSPACE";
    name: string | null;
    family_type: string;
    status: string;
    confidence: number | null;
    representative_asset_id: string | null;
};

export type CreativeFamilyCandidate = {
    id: string;
    scope: "MARKET" | "WORKSPACE";
    asset_a_id: string;
    asset_b_id: string;
    relationship: string;
    candidate_score: number;
    confidence: string;
    signals: Record<string, unknown>;
    reason: string;
    status: string;
};

export function listCreativeFamilies(
    workspaceId: string,
    scope: "MARKET" | "WORKSPACE" = "MARKET",
) {
    return apiGet<CreativeFamily[]>(
        `/workspaces/${workspaceId}/creative-library/families?scope=${scope}`,
    );
}

export function refreshCreativeFamilies(
    workspaceId: string,
    input: { scope: "MARKET" | "WORKSPACE"; asset_ids?: string[] },
) {
    return apiPost<{ candidate_count: number }>(
        `/workspaces/${workspaceId}/creative-library/families/refresh`,
        input,
    );
}

export function listFamilyCandidates(
    workspaceId: string,
    scope: "MARKET" | "WORKSPACE" = "MARKET",
) {
    return apiGet<CreativeFamilyCandidate[]>(
        `/workspaces/${workspaceId}/creative-library/families/candidates?scope=${scope}`,
    );
}

export function getCreativeFamily(workspaceId: string, familyId: string) {
    return apiGet<CreativeFamily & { members: Array<Record<string, unknown>> }>(
        `/workspaces/${workspaceId}/creative-library/families/${familyId}`,
    );
}

export type BatchReview = {
    id: string;
    objective: string;
    status: string;
    summary: Record<string, unknown>;
    items: Array<{
        id: string;
        asset_id: string;
        status: string;
        decision: string | null;
        recommended_action: string | null;
        priority: string | null;
        primary_reason: string | null;
        evidence_ids: string[];
    }>;
};

export function getBatchReview(workspaceId: string, batchId: string) {
    return apiGet<BatchReview>(
        `/workspaces/${workspaceId}/creative-library/batch-reviews/${batchId}`,
    );
}

export function startBatchReview(workspaceId: string, batchId: string) {
    return apiPost<BatchReview>(
        `/workspaces/${workspaceId}/creative-library/batch-reviews/${batchId}/start`,
        undefined,
    );
}

export function respondToBatchItem(
    workspaceId: string,
    itemId: string,
    input: {
        response: "accepted" | "rejected" | "modified" | "ignored";
        action: "TEST" | "FIX" | "RESHOOT" | "SKIP" | "INSUFFICIENT_EVIDENCE";
        feedback?: string;
    },
) {
    return apiPost<{ id: string; action: string; response: string }>(
        `/workspaces/${workspaceId}/creative-library/batch-review-items/${itemId}/response`,
        input,
    );
}

export function getTikTokSource(workspaceId: string, sourceId: string) {
    return apiGet<TikTokAdResult>(
        `/workspaces/${workspaceId}/creative-library/sources/${sourceId}`,
    );
}

export function getTikTokMediaUrl(workspaceId: string, sourceId: string, mediaIndex = 0) {
    const suffix = mediaIndex > 0 ? `?media_index=${mediaIndex}` : "";
    return `/api/backend/workspaces/${workspaceId}/creative-library/sources/${sourceId}/media${suffix}`;
}

export type CreativeAssetIntelligence = {
    asset: Record<string, unknown>;
    version: {
        id: string;
        validation_status: string;
        detected_mime_type: string | null;
        duration_ms: number | null;
    } | null;
    source: {
        provider: string;
        entity_type: string;
        entity_id: string;
        source_url: string | null;
        metadata: Record<string, unknown>;
    } | null;
    analysis: {
        status: string;
        evidence_count: number;
        evidence: Array<{
            id: string;
            evidence_type: string;
            source_type: string | null;
            evidence_scope: string;
            value: unknown;
            start_ms: number | null;
            end_ms: number | null;
            confidence: string | null;
            provider: string | null;
            observed_at: string | null;
        }>;
    };
    families: CreativeFamily[];
    market_signal_only: boolean;
};

export function getCreativeAssetIntelligence(workspaceId: string, assetId: string) {
    return apiGet<CreativeAssetIntelligence>(
        `/workspaces/${workspaceId}/creative-library/assets/${assetId}/intelligence`,
    );
}

export type MarketPatternSummary = {
    id: string;
    evidence_level:
        "OBSERVED" | "MARKET_OBSERVED" | "MARKET_PREVALENT" | "PUBLIC_DISTRIBUTION_SIGNAL";
    sample_size: number;
    comparable_sample_size: number | null;
    market: string | null;
    category: string | null;
    date_min: string | null;
    date_max: string | null;
    confidence: string;
    recency: string | null;
    limitations: string[];
    metric_summary: Record<string, unknown> | null;
};

export function listMarketPatterns(
    workspaceId: string,
    input?: { market?: string; category?: string },
) {
    const query = new URLSearchParams();
    if (input?.market) query.set("market", input.market);
    if (input?.category) query.set("category", input.category);
    return apiGet<MarketPatternSummary[]>(
        `/workspaces/${workspaceId}/creative-library/patterns/summary?${query.toString()}`,
    );
}

export function saveTikTokReference(
    workspaceId: string,
    sourceId: string,
    input: TikTokSaveReferenceInput,
) {
    return apiPost<{
        reference_id: string;
        asset_id: string;
        asset_version_id: string;
        status: string;
    }>(`/workspaces/${workspaceId}/creative-library/sources/${sourceId}/save-reference`, input);
}

export function analyzeCreativeAsset(workspaceId: string, assetId: string) {
    return apiPost<Record<string, unknown>>(
        `/workspaces/${workspaceId}/creative-library/assets/${assetId}/analyze`,
        undefined,
    );
}

export function attachCreativeProduct(
    workspaceId: string,
    assetId: string,
    productId: string | null,
) {
    return apiPost<Record<string, unknown>>(
        `/workspaces/${workspaceId}/creative-library/assets/${assetId}/attach-product`,
        { product_id: productId },
    );
}

export function generateCreativeDirections(
    workspaceId: string,
    assetId: string,
    input: {
        product_id: string;
        objective: string;
        target_market: string;
        target_buyer?: Record<string, unknown>;
        constraints?: Record<string, unknown>;
    },
) {
    return apiPost<Record<string, unknown>>(
        `/workspaces/${workspaceId}/creative-library/assets/${assetId}/generate-directions`,
        input,
    );
}
