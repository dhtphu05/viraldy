import { afterEach, describe, expect, it, vi } from "vitest";

import {
    createUgcReview,
    createUgcReviewRevision,
    getLatestUgcRevisionComparison,
    getUgcReviewStatus,
    normalizeUgcReviewResult,
    recordUgcRecommendationAction,
    validateUgcVideo,
} from "./ugc-reviews";

afterEach(() => {
    vi.unstubAllGlobals();
});

describe("UGC Review API", () => {
    it("creates a review with immutable asset identifiers and optional context as FormData", async () => {
        const fetchMock = vi.fn().mockResolvedValue(
            envelope({
                review_id: "review-1",
                status: "queued",
                mode: "ugc_review_v1",
                asset_id: "asset-1",
                asset_version_id: "version-1",
            }),
        );
        vi.stubGlobal("fetch", fetchMock);

        const response = await createUgcReview("workspace/one", {
            assetId: "asset-1",
            assetVersionId: "version-1",
            context: {
                commerceDomain: "pod_personalization",
                intendedUse: "spark_candidate",
                productName: "Custom mug",
                physicalSampleAvailable: false,
                sellerNotes: "Keep the creator's opening delivery.",
            },
        });

        expect(response.reviewId).toBe("review-1");
        expect(fetchMock).toHaveBeenCalledOnce();
        const [path, init] = fetchMock.mock.calls[0] as [string, RequestInit];
        expect(path).toBe("/api/backend/workspaces/workspace%2Fone/ugc-reviews");
        expect(init.method).toBe("POST");
        expect(init.headers).toBeUndefined();
        expect(init.body).toBeInstanceOf(FormData);
        const body = init.body as FormData;
        expect(Object.fromEntries(body.entries())).toEqual({
            asset_id: "asset-1",
            asset_version_id: "version-1",
            commerce_domain: "pod_personalization",
            intended_use: "spark_candidate",
            product_name: "Custom mug",
            physical_sample_available: "false",
            seller_notes: "Keep the creator's opening delivery.",
        });
    });

    it("uploads a revision reference without resending the video bytes", async () => {
        const fetchMock = vi.fn().mockResolvedValue(
            envelope({
                review_id: "review-2",
                parent_review_id: "review-1",
                status: "queued",
                mode: "ugc_review_v1",
                asset_id: "asset-1",
                asset_version_id: "version-2",
            }),
        );
        vi.stubGlobal("fetch", fetchMock);

        const response = await createUgcReviewRevision("workspace-1", "review/one", "version-2");

        expect(response.parentReviewId).toBe("review-1");
        expect(response.assetVersionId).toBe("version-2");
        const [path, init] = fetchMock.mock.calls[0] as [string, RequestInit];
        expect(path).toBe("/api/backend/workspaces/workspace-1/ugc-reviews/review%2Fone/revisions");
        expect(Object.fromEntries((init.body as FormData).entries())).toEqual({
            asset_version_id: "version-2",
        });
    });

    it("maps status, persists actions, and reads the latest real comparison", async () => {
        const fetchMock = vi
            .fn()
            .mockResolvedValueOnce(
                envelope({
                    review_id: "review-1",
                    status: "running",
                    progress: 64,
                    stage: "matching_evidence",
                }),
            )
            .mockResolvedValueOnce(
                envelope({
                    review_id: "review-1",
                    recommendation_id: "recommendation-1",
                    action: "marked_completed",
                }),
            )
            .mockResolvedValueOnce(
                envelope({
                    parent_review_id: "review-1",
                    revision_review_id: "review-2",
                    summary: "The product close-up is now clear.",
                    resolved: [{ title: "Show the exact product" }],
                    still_open: [],
                    new_findings: [],
                    strengths_preserved: ["Natural creator delivery"],
                }),
            );
        vi.stubGlobal("fetch", fetchMock);

        const status = await getUgcReviewStatus("workspace-1", "review-1");
        await recordUgcRecommendationAction(
            "workspace-1",
            "review-1",
            "recommendation/one",
            "marked_completed",
        );
        const comparison = await getLatestUgcRevisionComparison("workspace-1", "review-1");

        expect(status).toMatchObject({ status: "running", progress: 64 });
        expect(fetchMock.mock.calls[1]?.[0]).toBe(
            "/api/backend/workspaces/workspace-1/ugc-reviews/review-1/recommendations/recommendation%2Fone/actions",
        );
        expect(fetchMock.mock.calls[1]?.[1]).toMatchObject({
            method: "POST",
            body: JSON.stringify({ action: "marked_completed" }),
        });
        expect(comparison.resolved[0]?.title).toBe("Show the exact product");
        expect(fetchMock.mock.calls[2]?.[0]).toBe(
            "/api/backend/workspaces/workspace-1/ugc-reviews/review-1/comparisons/latest",
        );
    });
});

describe("UGC Review contract mapper", () => {
    it("maps the four result sections and provenance without introducing a score", () => {
        const result = normalizeUgcReviewResult({
            review_id: "review-1",
            status: "completed",
            asset_id: "asset-1",
            asset_version_id: "version-1",
            headline: "Strong draft — one scene should be reshot",
            summary: "Keep the creator delivery and replace the unclear product scene.",
            recommended_next_action: "reshoot_scene",
            overall_confidence: "high",
            strengths_to_keep: ["Natural creator delivery"],
            fix_first: [recommendation("fix-1", "fix_first")],
            improvements: [recommendation("improve-1", "improve")],
            confirmations: [recommendation("confirm-1", "confirm")],
            creator_revision_message: "Please keep the opening and reshoot the product close-up.",
            policy_pack_version: "1.0.0",
            analysis_provenance: { media_duration_ms: 18_000, provider: "evidence-pipeline" },
            created_at: "2026-07-31T12:00:00Z",
        });

        expect(result.assetId).toBe("asset-1");
        expect(result.assetVersionId).toBe("version-1");
        expect(result.strengths).toEqual(["Natural creator delivery"]);
        expect(result.fixFirst[0]?.group).toBe("fix_first");
        expect(result.improvements[0]?.group).toBe("improve");
        expect(result.confirmations[0]?.group).toBe("confirm");
        expect(result.message).toContain("reshoot the product close-up");
        expect(result.provenance.media_duration_ms).toBe(18_000);
        expect(result.fixFirst[0]).toMatchObject({
            taskKind: "video_edit_required",
            priority: "fix_before_publish",
            timeRange: { startMs: 2000, endMs: 3500 },
            exactAction: "Film a steady close-up of the exact product.",
            exactCopy: ["Use the seller-approved product name."],
            acceptanceCriteria: ["The exact product is visible and in focus."],
        });
        expect("score" in result).toBe(false);
    });

    it("drops invalid evidence timestamps while keeping an untimestamped evidence item", () => {
        const mapped = normalizeUgcReviewResult({
            review_id: "review-1",
            status: "completed",
            asset_id: "asset-1",
            asset_version_id: "version-1",
            headline: "Review ready",
            summary: "One confirmation is useful.",
            recommended_next_action: "confirm_information",
            overall_confidence: "medium",
            strengths_to_keep: [],
            fix_first: [],
            improvements: [],
            confirmations: [
                {
                    ...recommendation("confirm-1", "confirm"),
                    evidence: [
                        {
                            id: "evidence-1",
                            source: "seller_input",
                            observed: "Shipping statement not supplied",
                            start_ms: -10,
                            end_ms: 500,
                            confidence: "medium",
                        },
                    ],
                },
            ],
            creator_revision_message: "Please confirm the shipping language before publishing.",
            policy_pack_version: "1.0.0",
            analysis_provenance: {},
            created_at: "2026-07-31T12:00:00Z",
        });

        expect(mapped.confirmations[0]?.evidence[0]?.startMs).toBeNull();
        expect(mapped.confirmations[0]?.evidence[0]?.endMs).toBeNull();
    });
});

describe("UGC video validation", () => {
    it("accepts MP4 and QuickTime files up to 250 MB", () => {
        expect(validateUgcVideo({ name: "draft.mp4", type: "video/mp4", size: 1 })).toBeNull();
        expect(
            validateUgcVideo({
                name: "draft.mov",
                type: "video/quicktime",
                size: 250 * 1024 * 1024,
            }),
        ).toBeNull();
    });

    it("rejects unsupported or oversized files with actionable messages", () => {
        expect(validateUgcVideo({ name: "draft.webm", type: "video/webm", size: 1 })).toContain(
            "MP4 or QuickTime",
        );
        expect(
            validateUgcVideo({
                name: "draft.mp4",
                type: "video/mp4",
                size: 250 * 1024 * 1024 + 1,
            }),
        ).toContain("250 MB");
    });
});

function recommendation(id: string, group: "fix_first" | "improve" | "confirm") {
    return {
        id,
        rule_code: "UGC-RULE-1",
        mistake_code: null,
        group,
        title: "Show the exact product clearly",
        reason: "The current product view is too brief to verify.",
        why_it_matters: "A clear view helps the buyer understand the offer.",
        owner: "creator",
        fix_type: "reshoot_scene",
        instructions: ["Film a steady close-up of the exact product."],
        strengths_to_preserve: ["Keep the creator's natural opening."],
        completion_criteria: ["The exact product is visible and in focus."],
        task_kind: "video_edit_required",
        priority: "fix_before_publish",
        time_range: { start_ms: 2_000, end_ms: 3_500 },
        exact_action: "Film a steady close-up of the exact product.",
        exact_copy: ["Use the seller-approved product name."],
        acceptance_criteria: ["The exact product is visible and in focus."],
        evidence: [
            {
                id: `${id}-evidence`,
                source: "video",
                observed: "Product is visible briefly",
                start_ms: 2_000,
                end_ms: 3_500,
                confidence: "high",
            },
        ],
        confidence: "high",
        affected_use: "paid_candidate",
    };
}

function envelope(data: unknown): Response {
    return new Response(
        JSON.stringify({ success: true, data, error: null, request_id: "request-1" }),
        { status: 200, headers: { "Content-Type": "application/json" } },
    );
}
