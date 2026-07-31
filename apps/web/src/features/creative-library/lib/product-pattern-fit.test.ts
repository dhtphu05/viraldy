import { describe, expect, it } from "vitest";

import { evaluateProductPatternFit, rankProductsByPatternFit } from "./product-pattern-fit";

const creative = {
    category: "Home & Kitchen" as const,
    angle: "Product demonstration" as const,
};

describe("product pattern fit", () => {
    it("recommends a ready product in the same category", () => {
        const fit = evaluateProductPatternFit(creative, {
            id: "p-1",
            name: "Sofa Cover",
            category: "Home & Kitchen",
            readiness: "Ready",
            fulfillmentRisk: "Low",
            linkedCampaignCount: 1,
        });

        expect(fit.level).toBe("recommended");
        expect(fit.reasons).toContain("Same Home & Kitchen buying context");
    });

    it("marks an out-of-stock cross-category product as low fit", () => {
        const fit = evaluateProductPatternFit(creative, {
            id: "p-2",
            name: "Gift Sign",
            category: "POD Gifts",
            readiness: "Out of stock",
            fulfillmentRisk: "High",
            linkedCampaignCount: 0,
        });

        expect(fit.level).toBe("low");
        expect(fit.risk).toContain("not ready");
    });

    it("ranks recommended products before possible and low-fit products", () => {
        const ranked = rankProductsByPatternFit(creative, [
            {
                id: "low",
                name: "Gift Sign",
                category: "POD Gifts",
                readiness: "Out of stock",
                fulfillmentRisk: "High",
                linkedCampaignCount: 0,
            },
            {
                id: "high",
                name: "Sofa Cover",
                category: "Home & Kitchen",
                readiness: "Ready",
                fulfillmentRisk: "Low",
                linkedCampaignCount: 1,
            },
        ]);

        expect(ranked.map((item) => item.product.id)).toEqual(["high", "low"]);
    });

    it("prioritizes the product already linked to the source creative", () => {
        const ranked = rankProductsByPatternFit({ ...creative, linkedProductId: "linked" }, [
            {
                id: "other",
                name: "Organizer",
                category: "Home & Kitchen",
                readiness: "Ready",
                fulfillmentRisk: "Low",
                linkedCampaignCount: 2,
            },
            {
                id: "linked",
                name: "Sofa Cover",
                category: "Home & Kitchen",
                readiness: "Ready",
                fulfillmentRisk: "Low",
                linkedCampaignCount: 1,
            },
        ]);

        expect(ranked[0]?.product.id).toBe("linked");
        expect(ranked[0]?.fit.reasons).toContain("Already linked to this source creative");
    });
});
