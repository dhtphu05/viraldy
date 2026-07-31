import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { RecommendationGroups } from "./recommendation-groups";
import type { RecommendationGroup, UgcRecommendation } from "../types/ugc-review";

function recommendation(group: RecommendationGroup, title: string): UgcRecommendation {
    return {
        id: `recommendation-${group}`,
        ruleCode: `RULE-${group}`,
        mistakeCode: null,
        group,
        title,
        reason: `${title} because the evidence supports it.`,
        whyItMatters: "It helps the seller make a clear revision decision.",
        owner: group === "confirm" ? "seller" : "editor",
        fixType: group === "confirm" ? "confirm_seller_input" : "edit_existing_footage",
        instructions: ["Follow the evidence-backed change."],
        strengthsToPreserve: ["Keep the natural creator delivery."],
        completionCriteria: ["The requested change is visible."],
        evidence: [],
        confidence: "high",
        affectedUse: null,
    };
}

describe("RecommendationGroups", () => {
    it("renders Fix first, Improve, and Confirm from the live result contract", () => {
        const markup = renderToStaticMarkup(
            createElement(RecommendationGroups, {
                result: {
                    fixFirst: [recommendation("fix_first", "Replace the mismatched product shot")],
                    improvements: [recommendation("improve", "Connect the product earlier")],
                    confirmations: [recommendation("confirm", "Confirm paid-use rights")],
                    policyPackVersion: "domain-expert-v1",
                },
                savedActions: {},
                busyRecommendationId: null,
                onSeek: vi.fn(),
                onAction: vi.fn(),
            }),
        );

        expect(markup).toContain("Fix first");
        expect(markup).toContain("Replace the mismatched product shot");
        expect(markup).toContain("Improve");
        expect(markup).toContain("Connect the product earlier");
        expect(markup).toContain("Confirm");
        expect(markup).toContain("Confirm paid-use rights");
        expect(markup).not.toMatch(/predicted score|score lift/i);
    });
});
