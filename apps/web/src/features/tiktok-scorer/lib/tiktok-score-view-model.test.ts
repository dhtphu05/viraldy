import { describe, expect, it } from "vitest";

import type { TikTokFixAction, TikTokScoreRun } from "../types";
import {
    buildHandoffMessage,
    buildProcessingSteps,
    filterScoreRuns,
    groupFixActions,
    isTerminalScoreStatus,
    safeSeekSeconds,
    validateScoreDraft,
    validateVideoFile,
} from "./tiktok-score-view-model";

const baseFix: TikTokFixAction = {
    id: "fix-1",
    code: "FIX_ONE",
    sourceFindingId: "finding-1",
    sourceFindingCode: "finding_one",
    recommendationClass: "required_fix",
    basis: "video_diagnosis",
    priority: "P1",
    severity: "high",
    sourceDimension: "demo_clarity",
    ownerRole: "editor",
    fixType: "trim_or_reorder",
    group: "edit",
    title: "Move the existing demo earlier",
    whyItMatters: "The viewer needs to see the mechanism.",
    expected: { demo: "visible" },
    observed: { demo: "late" },
    evidenceIds: ["evidence-1"],
    targetTimeRangeMs: [4_000, 7_000],
    operations: [],
    instructions: ["Move the existing demo after the opening line."],
    strengthsToPreserve: ["Keep the natural opening line."],
    requiredInputs: [],
    effort: "low",
    reshootRequired: false,
    completionCriteria: ["The mechanism is visible during the opening."],
    verificationMethod: "Compare demo evidence in the next revision.",
    latestEvent: null,
};

describe("TikTok score view models", () => {
    it("groups fixes by the cheapest valid execution path", () => {
        const groups = groupFixActions([
            baseFix,
            { ...baseFix, id: "fix-2", fixType: "reshoot_scene", group: "reshoot" },
            {
                ...baseFix,
                id: "fix-3",
                fixType: "confirm_seller_input",
                group: "seller",
            },
            {
                ...baseFix,
                id: "fix-4",
                fixType: "request_better_media",
                group: "better_media",
            },
        ]);

        expect(groups.map((group) => [group.key, group.actions.length])).toEqual([
            ["edit", 1],
            ["reshoot", 1],
            ["seller", 1],
            ["better_media", 1],
        ]);
    });

    it("builds stage progress without inventing a percentage", () => {
        const steps = buildProcessingSteps("building_evidence");

        expect(steps.find((step) => step.key === "building_evidence")?.status).toBe("active");
        expect(steps.find((step) => step.key === "scoring")?.status).toBe("pending");
        expect(steps.filter((step) => step.status === "done").length).toBeGreaterThan(0);
    });

    it.each(["completed", "partial_evidence", "failed", "cancelled"])(
        "stops polling terminal status %s",
        (status) => expect(isTerminalScoreStatus(status)).toBe(true),
    );

    it("keeps polling a real queued or processing stage", () => {
        expect(isTerminalScoreStatus("queued")).toBe(false);
        expect(isTerminalScoreStatus("scoring")).toBe(false);
    });

    it("filters history across workspace fields and dates", () => {
        const run = {
            id: "score-1",
            assetName: "Draft 2 coffee demo.mp4",
            productId: "product-1",
            productName: "Travel Brewer",
            status: "completed",
            scoreMode: "product_aware",
            intendedUse: "tiktok_shop_affiliate",
            decision: "revise",
            profile: { code: "product_led_demo_v1" },
            updatedAt: "2026-07-30T01:00:00Z",
        } as TikTokScoreRun;

        expect(
            filterScoreRuns(
                [run],
                {
                    search: "coffee",
                    status: "completed",
                    mode: "product_aware",
                    profile: "product_led_demo_v1",
                    product: "product-1",
                    intendedUse: "tiktok_shop_affiliate",
                    decision: "revise",
                    date: "30d",
                },
                new Date("2026-07-31T01:00:00Z"),
            ),
        ).toEqual([run]);
        expect(
            filterScoreRuns([run], {
                search: "",
                status: "failed",
                mode: "all",
                profile: "all",
                product: "all",
                intendedUse: "all",
                decision: "all",
                date: "all",
            }),
        ).toEqual([]);
    });

    it("builds a handoff only from validated structured actions", () => {
        const message = buildHandoffMessage([baseFix], "editor");

        expect(message).toContain("Move the existing demo earlier");
        expect(message).toContain("Move the existing demo after the opening line.");
        expect(message).toContain("Keep the natural opening line.");
        expect(message).not.toContain("FIX_ONE");
        expect(message).not.toContain("rule");
    });

    it("bounds server-provided timestamp seeking to the known media duration", () => {
        expect(safeSeekSeconds(4_200, 30_000)).toBe(4.2);
        expect(safeSeekSeconds(80_000, 30_000)).toBe(30);
        expect(safeSeekSeconds(-200, null)).toBe(0);
    });

    it("validates only genuinely required score settings", () => {
        expect(
            validateScoreDraft({
                fileSelected: true,
                mode: "quick",
                productId: null,
                intendedUse: "tiktok_organic",
                profile: "general_tiktok_v1",
            }),
        ).toEqual({});
        expect(
            validateScoreDraft({
                fileSelected: true,
                mode: "product_aware",
                productId: null,
                intendedUse: "tiktok_organic",
                profile: "general_tiktok_v1",
            }),
        ).toEqual({ productId: "Choose a product for Product-Aware Score." });
    });

    it("uses backend media limits for local upload feedback", () => {
        expect(validateVideoFile({ name: "draft.mp4", type: "video/mp4", size: 12_000 }, 179)).toBe(
            null,
        );
        expect(
            validateVideoFile({ name: "draft.webm", type: "video/webm", size: 12_000 }, 20),
        ).toContain("MP4 or QuickTime");
        expect(
            validateVideoFile(
                { name: "draft.mov", type: "video/quicktime", size: 251 * 1024 * 1024 },
                20,
            ),
        ).toContain("250 MB");
        expect(
            validateVideoFile({ name: "draft.mp4", type: "video/mp4", size: 12_000 }, 181),
        ).toContain("3 minutes");
    });
});
