import { describe, expect, it } from "vitest";

import { createCampaignHandoff } from "./campaign-handoff";
import type { ViralConcept } from "@/features/mvp-flow/intelligence-types";

const concept: ViralConcept = {
    id: "concept-1",
    name: "Living-room reset",
    strategic_axis: "visible transformation",
    diversity_axes: [],
    buyer_persona_label: "Pet owners",
    buyer_pain: "A couch covered in pet hair",
    desired_outcome: "A clean couch in one pass",
    creative_angle: "Before-and-after",
    hook: {
        hook_type: "problem_first",
        spoken_text: "Watch this couch change in one pass.",
        overlay_text: "One-pass couch reset",
        opening_visual: "Show the hair-covered couch.",
        target_time_ms: 0,
        product_present: true,
    },
    opening_visual: "Show the hair-covered couch.",
    narrative_structure: "Problem, demo, proof, CTA",
    creator_persona: "Pet owner",
    delivery_style: "Natural",
    demo_mechanism: "One visible swipe across the couch",
    proof_mechanism: "Show the collected hair and clean fabric",
    offer_framing: null,
    cta_strategy: "Use the TikTok Shop product tag",
    must_show: [
        {
            id: "proof",
            instruction: "Show the collected pet hair",
            severity: "hard",
            expected_before_ms: 9000,
        },
    ],
    claims_to_avoid: ["Guaranteed results"],
    required_disclosures: [],
    test_hypothesis: "Visible proof will increase product clicks.",
    expected_learning: "Whether one-pass proof is persuasive.",
    risks: [],
    confidence: "high",
};

describe("Campaign handoff", () => {
    it("creates a directly openable campaign grounded in the confirmed concept", () => {
        const result = createCampaignHandoff({
            backendPackId: "backend-pack-1",
            product: {
                id: "backend-product-1",
                name: "Pet Hair Removal Roller",
                frontendSeedId: "p-4",
            },
            concept,
            referenceCreativeId: "cr-4",
            objective: "tiktok_shop_affiliate_test",
            market: "US",
            now: "2026-07-31T00:00:00.000Z",
        });

        expect(result.campaignId).toBe("campaign-backend-pack-1");
        expect(result.pack.productId).toBe("p-4");
        expect(result.pack.primaryAngleId).toBe("concept-1");
        expect(
            result.pack.storyboard.some((scene) =>
                scene.visualDirection.includes("collected pet hair"),
            ),
        ).toBe(true);
        expect(result.summary.packId).toBe(result.packId);
    });
});
