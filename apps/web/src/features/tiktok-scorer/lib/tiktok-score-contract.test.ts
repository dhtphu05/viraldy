import { describe, expect, it } from "vitest";

import {
    normalizeTikTokScoreComparison,
    normalizeTikTokScoreList,
    normalizeTikTokScoreRun,
} from "./tiktok-score-contract";

describe("TikTok score contract normalization", () => {
    it("normalizes the canonical V2 result without losing typed evidence or fix fields", () => {
        const run = normalizeTikTokScoreRun({
            id: "score-1",
            workspace_id: "workspace-1",
            asset_id: "asset-1",
            asset_version_id: "version-1",
            product_id: "product-1",
            score_mode: "product_aware",
            intended_use: "tiktok_shop_affiliate",
            status: "partial_evidence",
            current_stage: "completed",
            overall_score: 74,
            overall_confidence: "medium",
            creative_structure_decision: "revise",
            paid_use_rights_status: "pending_confirmation",
            final_paid_readiness: "pending_rights_confirmation",
            profile_selection: {
                profile_code: "product_led_demo_v1",
                selection_mode: "model_suggested_user_confirmed",
                confidence: 0.82,
                alternative_profiles: ["creator_review_v1"],
                evidence_ids: ["evidence-1"],
            },
            scene_inventory: {
                asset_version_id: "version-1",
                duration_ms: 30_000,
                audio_available: false,
                coverage_status: "partial",
                overall_confidence: "medium",
                scenes: [
                    {
                        scene_id: "scene-1",
                        start_ms: 1_000,
                        end_ms: 4_000,
                        summary: "Product close-up",
                        visual_quality: "usable",
                        reusable_for_edit: true,
                        evidence_ids: ["evidence-1"],
                    },
                ],
                product_appearance_ranges: [[1_000, 4_000]],
                cta_ranges: [],
                disclosure_ranges: [],
                evidence_ids: ["evidence-1"],
            },
            dimensions: [
                {
                    code: "offer_clarity",
                    label: "Value & Offer Clarity",
                    score: null,
                    applicability: "unknown",
                    evidence_status: "insufficient",
                    confidence: "low",
                    reason: "Offer context is unavailable.",
                    positive_signals: [],
                    missing_signals: ["Verified offer"],
                    uncertainty: ["No Product Context snapshot"],
                    evidence_ids: [],
                    contributing_rule_codes: [],
                },
            ],
            findings: [
                {
                    id: "finding-1",
                    code: "product_grounding",
                    rule_code: "PROFILE_PRODUCT_GROUNDING",
                    rule_class: "contextual_guideline",
                    source_dimension: "product_visibility",
                    severity: "high",
                    priority: "P1",
                    applicability: "applicable",
                    evidence_status: "sufficient",
                    title: "The product arrives after the opening promise",
                    reason: "This product-led profile needs a clear connection.",
                    expected: { first_product_ms: 1_500 },
                    observed: { first_product_ms: 4_200 },
                    target_time_range_ms: [1_000, 4_000],
                    evidence_ids: ["evidence-1"],
                    uncertainty: [],
                    requires_seller_truth: false,
                    can_be_resolved_by_edit: true,
                    requires_physical_reshoot: false,
                },
            ],
            fix_actions: [
                {
                    id: "fix-1",
                    code: "MOVE_CLOSEUP",
                    source_finding_id: "finding-1",
                    source_finding_code: "product_grounding",
                    recommendation_class: "required_fix",
                    basis: "score_profile",
                    priority: "P1",
                    severity: "high",
                    source_dimension: "product_visibility",
                    owner_role: "editor",
                    fix_type: "trim_or_reorder",
                    title: "Move the existing product close-up earlier",
                    why_it_matters: "Connect the opening promise to the item.",
                    expected: { first_product_ms: 1_500 },
                    observed: { first_product_ms: 4_200 },
                    evidence_ids: ["evidence-1"],
                    target_time_range_ms: [1_000, 4_000],
                    video_operations: [],
                    instructions: ["Move scene 1 before the current setup."],
                    strengths_to_preserve: ["Keep the natural delivery."],
                    required_inputs: [],
                    estimated_effort: "low",
                    reshoot_required: false,
                    completion_criteria: ["Product is grounded during the opening."],
                    verification_method: "Compare product appearance evidence in Draft 2.",
                    latest_event_type: "accepted",
                },
            ],
            strengths: [
                {
                    code: "natural_delivery",
                    title: "Natural creator delivery",
                    source_dimension: "creator_authenticity",
                    evidence_ids: ["evidence-1"],
                },
            ],
            evidence: [
                {
                    id: "evidence-1",
                    source_type: "frame",
                    start_ms: 1_000,
                    end_ms: 4_000,
                    summary: "The product is visible in a close-up.",
                    confidence: "high",
                },
            ],
            playback: { video_url: null, expires_at: null },
            revision_count: 1,
            updated_at: "2026-07-31T01:00:00Z",
        });

        expect(run.score).toBe(74);
        expect(run.profile.code).toBe("product_led_demo_v1");
        expect(run.dimensions[0].score).toBeNull();
        expect(run.dimensions[0].applicability).toBe("unknown");
        expect(run.fixes[0]).toMatchObject({
            id: "fix-1",
            group: "edit",
            latestEvent: "accepted",
            targetTimeRangeMs: [1_000, 4_000],
        });
        expect(run.sceneInventory?.scenes[0].reusableForEdit).toBe(true);
        expect(run.mediaUrl).toBeNull();
        expect(run.partialEvidence).toBe(true);
    });

    it("normalizes the legacy run and keeps missing Product Context checks not evaluated", () => {
        const run = normalizeTikTokScoreRun({
            id: "legacy-score",
            workspace_id: "workspace-1",
            asset_version_id: "version-1",
            status: "completed",
            structural_score: 61,
            confidence: "low",
            action_label: "fix",
            analysis_mode: "fixture",
            dimension_scores_json: {
                offer_clarity: {
                    score: 0,
                    reason: "No offer evidence was available.",
                    evidence_ids: [],
                },
            },
            blockers_json: [],
            fixes_json: [
                {
                    code: "missing_cta",
                    instruction: "Add a clear next step.",
                    why: "The close has no next action.",
                    evidence_ids: [],
                },
            ],
            strengths_json: [],
            created_at: "2026-07-30T01:00:00Z",
        });

        expect(run.score).toBe(61);
        expect(run.decision).toBe("revise");
        expect(run.scoreMode).toBe("quick");
        expect(run.dimensions[0]).toMatchObject({
            code: "offer_clarity",
            label: "Value & Offer Clarity",
            score: null,
            applicability: "not_applicable",
            evidenceStatus: "insufficient",
        });
        expect(run.fixes[0].title).toBe("Add a clear next step.");
    });

    it("merges detail-envelope names and persisted flat profile audit fields", () => {
        const run = normalizeTikTokScoreRun({
            score_run: {
                id: "score-1",
                asset_version_id: "version-1",
                status: "completed",
                score_profile: "creator_review_v1",
                profile_selection_mode: "inherited",
                alternative_profiles_json: ["general_tiktok_v1"],
                profile_evidence_ids_json: ["evidence-1"],
            },
            dimensions: [],
            findings: [],
            fix_actions: [],
            evidence: [],
            asset_name: "Creator demo draft.mp4",
            product_name: "Daily Serum",
        });

        expect(run.assetName).toBe("Creator demo draft.mp4");
        expect(run.productName).toBe("Daily Serum");
        expect(run.profile).toMatchObject({
            code: "creator_review_v1",
            selectionMode: "inherited",
            alternatives: ["general_tiktok_v1"],
            evidenceIds: ["evidence-1"],
        });
    });

    it("accepts array and paginated history envelopes without creating fixture rows", () => {
        expect(normalizeTikTokScoreList([])).toEqual({ items: [], total: 0, limit: 0, offset: 0 });

        const list = normalizeTikTokScoreList({
            items: [{ id: "score-1", status: "queued", asset_version_id: "version-1" }],
            total: 8,
            limit: 20,
            offset: 0,
        });

        expect(list.items).toHaveLength(1);
        expect(list.items[0].status).toBe("queued");
        expect(list.total).toBe(8);
    });

    it("normalizes comparison JSON and preserves like-for-like warnings", () => {
        const comparison = normalizeTikTokScoreComparison({
            id: "comparison-1",
            before_score_run_id: "score-1",
            after_score_run_id: "score-2",
            before_asset_version_id: "version-1",
            after_asset_version_id: "version-2",
            comparison_json: {
                before_score: 58,
                after_score: 76,
                resolved_blockers: [{ code: "claim", title: "Unsupported claim removed" }],
                unresolved_blockers: [],
                new_regressions: [{ code: "cta_zone", title: "CTA moved into the UI zone" }],
                dimension_changes: [
                    {
                        code: "claim_safety",
                        before_score: 42,
                        after_score: 80,
                        before_applicability: "applicable",
                        after_applicability: "applicable",
                    },
                ],
                evidence_before_after: [],
                strengths_preserved: [{ code: "voice", title: "Natural voice" }],
                actions_verified: [
                    {
                        action_id: "fix-1",
                        action_code: "REMOVE_CLAIM",
                        status: "verified",
                        before: { spoken_line: "Guaranteed result" },
                        after: { spoken_line: "How I use it" },
                        reason: "The unsupported line is absent.",
                    },
                ],
                final_next_action: "address_new_regressions",
                like_for_like: false,
                comparison_warning: "The selected score profile changed.",
            },
        });

        expect(comparison.scoreDelta).toBe(18);
        expect(comparison.resolved[0].title).toBe("Unsupported claim removed");
        expect(comparison.regressions[0].title).toBe("CTA moved into the UI zone");
        expect(comparison.actions[0].status).toBe("verified");
        expect(comparison.likeForLike).toBe(false);
        expect(comparison.warning).toContain("profile changed");
    });
});
