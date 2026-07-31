import {
    normalizeTikTokFixList,
    normalizeTikTokScoreComparison,
    normalizeTikTokScoreList,
    normalizeTikTokScoreProfiles,
    normalizeTikTokScoreRun,
} from "@/features/tiktok-scorer/lib/tiktok-score-contract";
import type {
    FixEventType,
    IntendedUse,
    ProfileSelectionMode,
    ScoreMode,
    ScoreProfileCode,
    TikTokFixAction,
    TikTokScoreComparison,
    TikTokScoreList,
    TikTokScoreProfile,
    TikTokScoreRun,
} from "@/features/tiktok-scorer/types";
import { apiGet, apiPost } from "./client";
import type { JobResponse } from "./jobs";

type HistoryQuery = Partial<{
    search: string;
    status: string;
    score_mode: string;
    score_profile: string;
    product_id: string;
    intended_use: string;
    decision: string;
    created_from: string;
    created_to: string;
    limit: number;
    offset: number;
    sort: string;
}>;

export type CreateTikTokScoreInput = {
    assetId?: string | null;
    assetVersionId: string;
    productId: string | null;
    mode: ScoreMode;
    intendedUse: IntendedUse;
    profile: ScoreProfileCode;
    profileSelectionMode: ProfileSelectionMode;
    profileSelectionConfidence: number | null;
    creativeDirectionContextId: string | null;
    idempotencyKey: string;
};

export type CreateTikTokScoreResult = {
    run: TikTokScoreRun;
    job: JobResponse | null;
    jobId: string | null;
    comparisonId: string | null;
};

export type CreativeDirectionSummary = {
    id: string;
    name: string;
    productId: string;
    targetMarket: string | null;
    status: string;
    version: number;
    selectedConceptId: string | null;
};

export function buildTikTokScoreListPath(workspaceId: string, query: HistoryQuery = {}): string {
    const params = new URLSearchParams();
    const entries: Array<[keyof HistoryQuery, string | number | undefined]> = [
        ["search", query.search],
        ["status", query.status],
        ["score_mode", query.score_mode],
        ["score_profile", query.score_profile],
        ["product_id", query.product_id],
        ["intended_use", query.intended_use],
        ["decision", query.decision],
        ["created_from", query.created_from],
        ["created_to", query.created_to],
        ["limit", query.limit],
        ["offset", query.offset],
        ["sort", query.sort],
    ];
    for (const [key, value] of entries) {
        if (value === undefined || value === "" || value === "all") continue;
        params.set(key, String(value));
    }
    const suffix = params.toString();
    return `/workspaces/${segment(workspaceId)}/tiktok-scores${suffix ? `?${suffix}` : ""}`;
}

export function scoreProfilePath(workspaceId: string): string {
    return `/workspaces/${segment(workspaceId)}/tiktok-score-profiles`;
}

export async function listTikTokScores(
    workspaceId: string,
    query: HistoryQuery = {},
): Promise<TikTokScoreList> {
    return normalizeTikTokScoreList(
        await apiGet<unknown>(buildTikTokScoreListPath(workspaceId, query)),
    );
}

export async function getTikTokScore(
    workspaceId: string,
    scoreRunId: string,
): Promise<TikTokScoreRun> {
    const payload = await apiGet<unknown>(
        `/workspaces/${segment(workspaceId)}/tiktok-scores/${segment(scoreRunId)}`,
    );
    return normalizeTikTokScoreRun(payload);
}

export async function createTikTokScore(
    workspaceId: string,
    input: CreateTikTokScoreInput,
): Promise<CreateTikTokScoreResult> {
    const payload = await apiPost<Record<string, unknown>>(
        `/workspaces/${segment(workspaceId)}/tiktok-scores`,
        {
            asset_id: input.assetId ?? undefined,
            asset_version_id: input.assetVersionId,
            product_id: input.productId,
            score_mode: input.mode,
            score_profile: input.profile,
            intended_use: input.intendedUse,
            creative_direction_context_id: input.creativeDirectionContextId,
            profile_selection_mode: input.profileSelectionMode,
            profile_selection_confidence: input.profileSelectionConfidence,
            idempotency_key: input.idempotencyKey,
        },
        { headers: { "Idempotency-Key": input.idempotencyKey } },
    );
    const job = isJob(payload.job) ? payload.job : null;
    return {
        run: normalizeTikTokScoreRun(payload.score_run ?? payload),
        job,
        jobId: stringOrNull(payload.job_id) ?? job?.id ?? null,
        comparisonId:
            stringOrNull(payload.comparison_id) ??
            stringOrNull(asRecord(payload.comparison).id) ??
            null,
    };
}

export async function listTikTokScoreProfiles(workspaceId: string): Promise<TikTokScoreProfile[]> {
    return normalizeTikTokScoreProfiles(await apiGet<unknown>(scoreProfilePath(workspaceId)));
}

export async function listTikTokScoreFixes(
    workspaceId: string,
    scoreRunId: string,
): Promise<TikTokFixAction[]> {
    return normalizeTikTokFixList(
        await apiGet<unknown>(
            `/workspaces/${segment(workspaceId)}/tiktok-scores/${segment(scoreRunId)}/fixes`,
        ),
    );
}

export async function recordTikTokFixAction(
    workspaceId: string,
    scoreRunId: string,
    fixId: string,
    eventType: FixEventType,
    idempotencyKey: string,
): Promise<TikTokFixAction> {
    const payload = await apiPost<Record<string, unknown>>(
        `/workspaces/${segment(workspaceId)}/tiktok-scores/${segment(scoreRunId)}/fixes/${segment(fixId)}/actions`,
        { event_type: eventType, details_json: {}, idempotency_key: idempotencyKey },
        { headers: { "Idempotency-Key": idempotencyKey } },
    );
    return normalizeTikTokFixList([payload.fix_action ?? payload])[0];
}

export async function createTikTokScoreRevision(
    workspaceId: string,
    scoreRunId: string,
    input: {
        assetVersionId: string;
        profile?: ScoreProfileCode;
        profileOverrideReason?: string | null;
        acceptedFixActionIds: string[];
        idempotencyKey: string;
    },
): Promise<CreateTikTokScoreResult> {
    const payload = await apiPost<Record<string, unknown>>(
        `/workspaces/${segment(workspaceId)}/tiktok-scores/${segment(scoreRunId)}/revisions`,
        {
            asset_version_id: input.assetVersionId,
            score_profile: input.profile,
            profile_override_reason: input.profileOverrideReason ?? null,
            accepted_fix_action_ids: input.acceptedFixActionIds,
            idempotency_key: input.idempotencyKey,
        },
        { headers: { "Idempotency-Key": input.idempotencyKey } },
    );
    const job = isJob(payload.job) ? payload.job : null;
    return {
        run: normalizeTikTokScoreRun(payload.score_run ?? payload),
        job,
        jobId: stringOrNull(payload.job_id) ?? job?.id ?? null,
        comparisonId:
            stringOrNull(payload.comparison_id) ??
            stringOrNull(asRecord(payload.comparison).id) ??
            null,
    };
}

export async function getTikTokScoreComparison(
    workspaceId: string,
    scoreRunId: string,
    comparisonId: string,
): Promise<TikTokScoreComparison> {
    return normalizeTikTokScoreComparison(
        await apiGet<unknown>(
            `/workspaces/${segment(workspaceId)}/tiktok-scores/${segment(scoreRunId)}/comparisons/${segment(comparisonId)}`,
        ),
    );
}

export async function getAssetPlayback(
    workspaceId: string,
    assetId: string,
    assetVersionId: string,
): Promise<{ videoUrl: string | null; expiresAt: string | null }> {
    const payload = await apiGet<Record<string, unknown>>(
        `/workspaces/${segment(workspaceId)}/assets/${segment(assetId)}/versions/${segment(assetVersionId)}/playback`,
    );
    return {
        videoUrl: stringOrNull(payload.video_url),
        expiresAt: stringOrNull(payload.expires_at),
    };
}

export async function listCreativeDirections(
    workspaceId: string,
): Promise<CreativeDirectionSummary[]> {
    const payload = await apiGet<unknown[]>(
        `/workspaces/${segment(workspaceId)}/viral-kits?limit=100`,
    );
    return (Array.isArray(payload) ? payload : []).map((item) => {
        const source = asRecord(item);
        return {
            id: String(source.id ?? ""),
            name: String(source.name ?? "Creative Direction"),
            productId: String(source.product_id ?? ""),
            targetMarket: stringOrNull(source.target_market),
            status: String(source.status ?? "unknown"),
            version: Number(source.latest_version ?? 1),
            selectedConceptId: stringOrNull(source.selected_concept_id),
        };
    });
}

export type TikTokScoreEventInput = {
    eventType:
        | "tiktok_scorer_opened"
        | "tiktok_finding_viewed"
        | "tiktok_evidence_opened"
        | "tiktok_comparison_viewed";
    workspaceId: string;
    scoreRunId?: string;
    assetVersionId?: string;
    findingId?: string;
    evidenceId?: string;
    comparisonId?: string;
    mode?: ScoreMode;
    profile?: ScoreProfileCode;
    intendedUse?: IntendedUse;
};

/** Best-effort product analytics. Failure must never block a scorer workflow. */
export async function trackTikTokScoreEvent(input: TikTokScoreEventInput): Promise<void> {
    const body = compact({
        event_type: input.eventType,
        asset_version_id: input.assetVersionId,
        finding_id: input.findingId,
        evidence_id: input.evidenceId,
        comparison_id: input.comparisonId,
        score_mode: input.mode,
        score_profile: input.profile,
        intended_use: input.intendedUse,
    });
    try {
        const path = input.scoreRunId
            ? `/workspaces/${segment(input.workspaceId)}/tiktok-scores/${segment(input.scoreRunId)}/events`
            : `/workspaces/${segment(input.workspaceId)}/tiktok-scores/events`;
        await apiPost(path, body);
    } catch {
        // Analytics is deliberately non-blocking and contains stable identifiers only.
    }
}

function segment(value: string): string {
    return encodeURIComponent(value);
}

function stringOrNull(value: unknown): string | null {
    return typeof value === "string" && value ? value : null;
}

function asRecord(value: unknown): Record<string, unknown> {
    return value !== null && typeof value === "object" && !Array.isArray(value)
        ? (value as Record<string, unknown>)
        : {};
}

function isJob(value: unknown): value is JobResponse {
    const source = asRecord(value);
    return typeof source.id === "string" && typeof source.status === "string";
}

function compact<T extends Record<string, unknown>>(value: T): Record<string, unknown> {
    return Object.fromEntries(Object.entries(value).filter(([, item]) => item !== undefined));
}
