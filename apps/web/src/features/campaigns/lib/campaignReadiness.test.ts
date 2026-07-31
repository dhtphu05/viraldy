import { describe, expect, it } from "vitest";

import { seedPacks } from "@/features/campaigns/mocks/campaignPacks";
import { evaluateCampaignCoherence } from "./campaignCoherence";
import { markCampaignReady, selectCampaignReadiness } from "./campaignReadiness";

function completeDraft() {
    return structuredClone({ ...seedPacks["pack-4"], status: "Draft" as const });
}

describe("Campaign readiness", () => {
    it("does not treat a Draft as creator-ready", () => {
        const readiness = selectCampaignReadiness(completeDraft());
        expect(readiness.lifecycle).toBe("ready_for_review");
        expect(readiness.lifecycle).not.toBe("creator_ready");
    });

    it("blocks complete content that fails coherence", () => {
        const pack = completeDraft();
        pack.script[0] = { ...pack.script[0], text: "Open this kitchen drawer first." };
        const readiness = selectCampaignReadiness(pack, {
            disallowedSourceTerms: ["kitchen drawer"],
        });
        expect(readiness.contentComplete).toBe(true);
        expect(readiness.qualityPassed).toBe(false);
        expect(readiness.lifecycle).toBe("draft");
    });

    it("blocks readiness when one hard blocker remains", () => {
        const pack = completeDraft();
        pack.cta.primary = "";
        const readiness = selectCampaignReadiness(pack);
        expect(readiness.hardBlockers.some((issue) => issue.id === "missing-cta")).toBe(true);
        expect(readiness.lifecycle).toBe("draft");
    });

    it("marks an eligible campaign ready immutably", () => {
        const pack = completeDraft();
        const next = markCampaignReady(pack);
        expect(next).not.toBe(pack);
        expect(next.status).toBe("Ready for creator");
        expect(selectCampaignReadiness(next).lifecycle).toBe("creator_ready");
    });

    it("keeps header, overview, and review consistent through one selector", () => {
        const pack = markCampaignReady(completeDraft());
        const header = selectCampaignReadiness(pack);
        const overview = selectCampaignReadiness(pack);
        const review = selectCampaignReadiness(pack);
        expect([header.lifecycle, overview.lifecycle, review.lifecycle]).toEqual([
            "creator_ready",
            "creator_ready",
            "creator_ready",
        ]);
    });
});

describe("Campaign coherence", () => {
    it("detects product-context leakage", () => {
        const pack = completeDraft();
        pack.script[0] = { ...pack.script[0], text: "Open this kitchen drawer first." };
        expect(
            evaluateCampaignCoherence(pack, { disallowedSourceTerms: ["kitchen drawer"] }).map(
                (issue) => issue.code,
            ),
        ).toContain("product_context_leakage");
    });

    it("detects selected-angle mismatch", () => {
        expect(
            evaluateCampaignCoherence(completeDraft(), {
                selectedAngleTerms: ["medical professional endorsement"],
            }).map((issue) => issue.code),
        ).toContain("selected_angle_mismatch");
    });

    it("detects a missing CTA", () => {
        const pack = completeDraft();
        pack.cta.primary = "";
        expect(evaluateCampaignCoherence(pack).map((issue) => issue.code)).toContain("missing_cta");
    });

    it("detects an unsupported claim", () => {
        const pack = completeDraft();
        pack.script[0] = { ...pack.script[0], text: "This guarantees instant results." };
        expect(
            evaluateCampaignCoherence(pack, { blockedClaimTerms: ["guarantees"] }).map(
                (issue) => issue.code,
            ),
        ).toContain("claim_blocker");
    });

    it("passes correct product-grounded content", () => {
        expect(
            evaluateCampaignCoherence(completeDraft(), {
                selectedAngleTerms: ["one-swipe"],
                disallowedSourceTerms: ["kitchen drawer"],
                blockedClaimTerms: ["guaranteed"],
            }),
        ).toEqual([]);
    });
});
