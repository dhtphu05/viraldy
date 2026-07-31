import { describe, expect, it } from "vitest";

import { toClaimInsights, toMechanismInsights, toRiskInsights } from "./dna-presentation";

describe("Creative DNA presentation", () => {
    it("keeps evidence identifiers out of seller-facing mechanism copy", () => {
        const insights = toMechanismInsights([
            {
                mechanism_type: "before_after_reveal",
                description: "Show the unfinished sofa before the fitted cover.",
                evidence_ids: ["554fab02-84d6-418b-a7a3-dc7bdaf161ac"],
            },
        ]);

        expect(insights).toEqual([
            {
                title: "Before After Reveal",
                description: "Show the unfinished sofa before the fitted cover.",
                meta: "Supported by 1 evidence item",
                tone: "positive",
            },
        ]);
        expect(JSON.stringify(insights)).not.toContain("554fab02");
    });

    it("humanizes claim and risk metadata without exposing raw objects", () => {
        expect(
            toClaimInsights([
                {
                    text: "No TikTok Shop tag is visible.",
                    category: "shopability_gap",
                    risk: "medium",
                },
            ]),
        ).toEqual([
            {
                title: "No TikTok Shop tag is visible.",
                meta: "Shopability Gap · Medium risk",
                tone: "neutral",
            },
        ]);

        expect(
            toRiskInsights([
                {
                    code: "NO_SHOP_TAG",
                    severity: "high",
                    message: "Add a product-tag CTA before launch.",
                    evidence_ids: ["private-id"],
                },
            ]),
        ).toEqual([
            {
                title: "No Shop Tag",
                description: "Add a product-tag CTA before launch.",
                meta: "High priority · 1 evidence item",
                tone: "warning",
            },
        ]);
    });
});
