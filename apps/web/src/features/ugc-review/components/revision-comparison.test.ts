import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { RevisionComparison } from "./revision-comparison";

describe("RevisionComparison", () => {
    it("renders the actual comparison groups without a simulated score", () => {
        const markup = renderToStaticMarkup(
            createElement(RevisionComparison, {
                comparison: {
                    parentReviewId: "review-1",
                    revisionReviewId: "review-2",
                    summary: "The product close-up is now clear.",
                    resolved: [{ title: "Exact product is now visible" }],
                    stillOpen: [{ title: "Confirm publish-time disclosure" }],
                    newFindings: [],
                    strengthsPreserved: ["Natural creator delivery"],
                },
            }),
        );

        expect(markup).toContain("Resolved");
        expect(markup).toContain("Still open");
        expect(markup).toContain("New in Draft 2");
        expect(markup).toContain("Strengths preserved");
        expect(markup).not.toMatch(/score|lift/i);
    });
});
