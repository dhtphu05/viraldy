import type {
    RecommendationGroup,
    RecommendationOwner,
    ReviewConfidence,
    ReviewEvidenceSource,
    ReviewFixType,
    ReviewNextAction,
    UgcRecommendation,
    UgcRecommendationAction,
    UgcReviewContext,
    UgcReviewCreation,
    UgcReviewEvidence,
    UgcReviewResult,
    UgcReviewRevisionCreation,
    UgcReviewStatus,
    UgcReviewStatusValue,
    UgcRevisionComparison,
} from "@/features/ugc-review/types/ugc-review";
import { apiGet, apiPost, apiPostForm } from "./client";

export type CreateUgcReviewInput = Readonly<{
    assetId: string;
    assetVersionId: string;
    context: UgcReviewContext;
}>;

export type UgcAssetPlayback = Readonly<{
    videoUrl: string | null;
    expiresAt: string | null;
}>;

export const UGC_VIDEO_MAX_BYTES = 250 * 1024 * 1024;

export async function createUgcReview(
    workspaceId: string,
    input: CreateUgcReviewInput,
    signal?: AbortSignal,
): Promise<UgcReviewCreation> {
    const form = new FormData();
    appendFormValue(form, "asset_id", input.assetId);
    appendFormValue(form, "asset_version_id", input.assetVersionId);
    appendReviewContext(form, input.context);
    return normalizeUgcReviewCreation(
        await apiPostForm<unknown>(workspacePath(workspaceId), form, { signal }),
    );
}

export async function getUgcReviewStatus(
    workspaceId: string,
    reviewId: string,
    signal?: AbortSignal,
): Promise<UgcReviewStatus> {
    return normalizeUgcReviewStatus(
        await apiGet<unknown>(`${reviewPath(workspaceId, reviewId)}/status`, { signal }),
    );
}

export async function getUgcReviewResult(
    workspaceId: string,
    reviewId: string,
    signal?: AbortSignal,
): Promise<UgcReviewResult> {
    return normalizeUgcReviewResult(
        await apiGet<unknown>(reviewPath(workspaceId, reviewId), { signal }),
    );
}

export async function recordUgcRecommendationAction(
    workspaceId: string,
    reviewId: string,
    recommendationId: string,
    action: UgcRecommendationAction,
    reason?: string,
): Promise<Readonly<Record<string, unknown>>> {
    return asRecord(
        await apiPost<unknown>(
            `${reviewPath(workspaceId, reviewId)}/recommendations/${segment(recommendationId)}/actions`,
            { action, reason: reason?.trim() || undefined },
        ),
    );
}

export async function createUgcReviewRevision(
    workspaceId: string,
    reviewId: string,
    assetVersionId: string,
    signal?: AbortSignal,
): Promise<UgcReviewRevisionCreation> {
    const form = new FormData();
    appendFormValue(form, "asset_version_id", assetVersionId);
    return normalizeUgcReviewRevisionCreation(
        await apiPostForm<unknown>(`${reviewPath(workspaceId, reviewId)}/revisions`, form, {
            signal,
        }),
    );
}

export async function getLatestUgcRevisionComparison(
    workspaceId: string,
    reviewId: string,
): Promise<UgcRevisionComparison> {
    return normalizeUgcRevisionComparison(
        await apiGet<unknown>(`${reviewPath(workspaceId, reviewId)}/comparisons/latest`),
    );
}

export async function getUgcAssetPlayback(
    workspaceId: string,
    assetId: string,
    assetVersionId: string,
): Promise<UgcAssetPlayback> {
    const payload = asRecord(
        await apiGet<unknown>(
            `/workspaces/${segment(workspaceId)}/assets/${segment(assetId)}/versions/${segment(assetVersionId)}/playback`,
        ),
    );
    return {
        videoUrl: optionalString(payload.video_url),
        expiresAt: optionalString(payload.expires_at),
    };
}

export function validateUgcVideo(file: Pick<File, "name" | "type" | "size">): string | null {
    const extension = file.name.toLowerCase().split(".").pop();
    const supportedMime = file.type === "video/mp4" || file.type === "video/quicktime";
    const supportedUnnamedMime = file.type === "" && (extension === "mp4" || extension === "mov");
    if (!supportedMime && !supportedUnnamedMime) {
        return "Choose an MP4 or QuickTime (.mov) video.";
    }
    if (file.size <= 0) return "Choose a video that is not empty.";
    if (file.size > UGC_VIDEO_MAX_BYTES) return "Video must be 250 MB or smaller.";
    return null;
}

export function normalizeUgcReviewResult(value: unknown): UgcReviewResult {
    const source = asRecord(value);
    return {
        reviewId: requiredString(source.review_id, "review_id"),
        status: literal(source.status, ["completed"] as const, "completed"),
        assetId: requiredString(source.asset_id, "asset_id"),
        assetVersionId: requiredString(source.asset_version_id, "asset_version_id"),
        headline: requiredString(source.headline, "headline"),
        summary: requiredString(source.summary, "summary"),
        recommendedNextAction: literal<ReviewNextAction>(
            source.recommended_next_action,
            ["use_as_is", "revise", "reshoot_scene", "confirm_information", "request_better_media"],
            "revise",
        ),
        overallConfidence: normalizeConfidence(source.overall_confidence),
        strengths: stringList(source.strengths_to_keep),
        fixFirst: recommendationList(source.fix_first, "fix_first"),
        improvements: recommendationList(source.improvements, "improve"),
        confirmations: recommendationList(source.confirmations, "confirm"),
        message: requiredString(source.creator_revision_message, "creator_revision_message"),
        policyPackVersion: requiredString(source.policy_pack_version, "policy_pack_version"),
        provenance: asRecord(source.analysis_provenance),
        createdAt: requiredString(source.created_at, "created_at"),
    };
}

function normalizeUgcReviewCreation(value: unknown): UgcReviewCreation {
    const source = asRecord(value);
    return {
        reviewId: requiredString(source.review_id, "review_id"),
        status: literal(source.status, ["queued"] as const, "queued"),
        mode: literal(source.mode, ["ugc_review_v1"] as const, "ugc_review_v1"),
        assetId: requiredString(source.asset_id, "asset_id"),
        assetVersionId: requiredString(source.asset_version_id, "asset_version_id"),
    };
}

function normalizeUgcReviewRevisionCreation(value: unknown): UgcReviewRevisionCreation {
    const source = asRecord(value);
    return {
        ...normalizeUgcReviewCreation(source),
        parentReviewId: requiredString(source.parent_review_id, "parent_review_id"),
    };
}

function normalizeUgcReviewStatus(value: unknown): UgcReviewStatus {
    const source = asRecord(value);
    return {
        reviewId: requiredString(source.review_id, "review_id"),
        status: literal<UgcReviewStatusValue>(
            source.status,
            ["queued", "running", "completed", "failed"],
            "queued",
        ),
        progress: Math.min(100, Math.max(0, finiteNumber(source.progress) ?? 0)),
        stage: optionalString(source.stage) ?? "Preparing review",
        errorCode: optionalString(source.error_code),
        errorMessage: optionalString(source.error_message),
    };
}

function normalizeUgcRevisionComparison(value: unknown): UgcRevisionComparison {
    const source = asRecord(value);
    return {
        parentReviewId: requiredString(source.parent_review_id, "parent_review_id"),
        revisionReviewId: requiredString(source.revision_review_id, "revision_review_id"),
        summary: requiredString(source.summary, "summary"),
        resolved: recordList(source.resolved),
        stillOpen: recordList(source.still_open),
        newFindings: recordList(source.new_findings),
        strengthsPreserved: stringList(source.strengths_preserved),
    };
}

function recommendationList(value: unknown, group: RecommendationGroup): UgcRecommendation[] {
    if (!Array.isArray(value)) return [];
    return value.map((item) => normalizeRecommendation(item, group));
}

function normalizeRecommendation(value: unknown, group: RecommendationGroup): UgcRecommendation {
    const source = asRecord(value);
    return {
        id: requiredString(source.id, "recommendation.id"),
        ruleCode: optionalString(source.rule_code),
        mistakeCode: optionalString(source.mistake_code),
        group,
        title: requiredString(source.title, "recommendation.title"),
        reason: requiredString(source.reason, "recommendation.reason"),
        whyItMatters: optionalString(source.why_it_matters) ?? "This supports a clearer draft.",
        owner: literal<RecommendationOwner>(
            source.owner ?? source.owner_role,
            ["seller", "creator", "editor"],
            "seller",
        ),
        fixType: normalizeFixType(source.fix_type),
        instructions: stringList(source.instructions),
        strengthsToPreserve: stringList(source.strengths_to_preserve),
        completionCriteria: stringList(source.completion_criteria),
        evidence: evidenceList(source.evidence),
        confidence: normalizeConfidence(source.confidence),
        affectedUse: optionalString(source.affected_use),
    };
}

function evidenceList(value: unknown): UgcReviewEvidence[] {
    if (!Array.isArray(value)) return [];
    return value.map((item) => {
        const source = asRecord(item);
        const startMs = nonNegativeNumber(source.start_ms);
        const endMs = nonNegativeNumber(source.end_ms);
        const validRange = startMs !== null && (endMs === null || endMs >= startMs);
        return {
            id: requiredString(source.id, "evidence.id"),
            source: literal<ReviewEvidenceSource>(
                source.source,
                ["video", "transcript", "ocr", "seller_input", "brief", "policy"],
                "video",
            ),
            observed: requiredString(source.observed, "evidence.observed"),
            startMs: validRange ? startMs : null,
            endMs: validRange ? endMs : null,
            confidence: normalizeConfidence(source.confidence),
        };
    });
}

function appendReviewContext(form: FormData, context: UgcReviewContext): void {
    const fields: ReadonlyArray<readonly [string, string | boolean | undefined]> = [
        ["market", context.market],
        ["platform", context.platform],
        ["commerce_domain", context.commerceDomain],
        ["intended_use", context.intendedUse],
        ["product_name", context.productName],
        ["product_category", context.productCategory],
        ["exact_variant_or_sku", context.exactVariantOrSku],
        ["product_description", context.productDescription],
        ["current_offer", context.currentOffer],
        ["verified_shipping_language", context.verifiedShippingLanguage],
        ["approved_personalization", context.approvedPersonalization],
        ["physical_sample_available", context.physicalSampleAvailable],
        ["creator_brief", context.creatorBrief],
        ["material_connection", context.materialConnection],
        ["seller_notes", context.sellerNotes],
    ];
    for (const [key, value] of fields) appendFormValue(form, key, value);
}

function appendFormValue(form: FormData, key: string, value: string | boolean | undefined): void {
    if (value === undefined || (typeof value === "string" && !value.trim())) return;
    form.append(key, String(value));
}

function workspacePath(workspaceId: string): string {
    return `/workspaces/${segment(workspaceId)}/ugc-reviews`;
}

function reviewPath(workspaceId: string, reviewId: string): string {
    return `${workspacePath(workspaceId)}/${segment(reviewId)}`;
}

function segment(value: string): string {
    return encodeURIComponent(value);
}

function asRecord(value: unknown): Record<string, unknown> {
    return value !== null && typeof value === "object" && !Array.isArray(value)
        ? (value as Record<string, unknown>)
        : {};
}

function recordList(value: unknown): Readonly<Record<string, unknown>>[] {
    return Array.isArray(value) ? value.map(asRecord) : [];
}

function stringList(value: unknown): string[] {
    return Array.isArray(value)
        ? value.filter((item): item is string => typeof item === "string" && item.trim().length > 0)
        : [];
}

function requiredString(value: unknown, field: string): string {
    if (typeof value !== "string" || !value.trim()) {
        throw new Error(`UGC Review response is missing ${field}.`);
    }
    return value;
}

function optionalString(value: unknown): string | null {
    return typeof value === "string" && value.trim() ? value : null;
}

function finiteNumber(value: unknown): number | null {
    return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function nonNegativeNumber(value: unknown): number | null {
    const number = finiteNumber(value);
    return number !== null && number >= 0 ? number : null;
}

function literal<T extends string>(value: unknown, values: readonly T[], fallback: T): T {
    return typeof value === "string" && values.includes(value as T) ? (value as T) : fallback;
}

function normalizeConfidence(value: unknown): ReviewConfidence {
    return literal<ReviewConfidence>(value, ["high", "medium", "low"], "low");
}

function normalizeFixType(value: unknown): ReviewFixType | null {
    const values: readonly ReviewFixType[] = [
        "edit_existing_footage",
        "add_overlay",
        "replace_copy",
        "reshoot_scene",
        "confirm_seller_input",
        "request_better_media",
    ];
    return typeof value === "string" && values.includes(value as ReviewFixType)
        ? (value as ReviewFixType)
        : null;
}
