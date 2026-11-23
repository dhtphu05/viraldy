import { describe, expect, it } from "vitest";

import { buildAnalysisProgress } from "./analysis-progress";

describe("TikTok analysis progress", () => {
    it("reports evidence scanning without pretending to know a frame-level position", () => {
        const progress = buildAnalysisProgress("building_evidence", 45, 15_000);

        expect(progress.title).toBe("Reading visual, speech, and text evidence");
        expect(progress.coverageLabel).toBe("Reviewing the full 0:00–0:15 video");
        expect(progress.confirmed.map((item) => item.label)).toContain("Media prepared");
        expect(progress.active.map((item) => item.label)).toEqual([
            "Product visibility",
            "Spoken claims",
            "On-screen text",
            "Demo actions",
        ]);
    });

    it("marks evidence and scene understanding as confirmed after their stages complete", () => {
        const progress = buildAnalysisProgress("scoring", 70, 15_000);

        expect(progress.confirmed.map((item) => item.label)).toEqual(
            expect.arrayContaining([
                "Media prepared",
                "Evidence captured",
                "Scene sequence mapped",
            ]),
        );
        expect(progress.title).toBe("Evaluating creative structure");
    });

    it("clamps the server progress value for accessible progress rendering", () => {
        expect(buildAnalysisProgress("queued", -10, null).percent).toBe(0);
        expect(buildAnalysisProgress("persisting", 120, null).percent).toBe(100);
    });
});
