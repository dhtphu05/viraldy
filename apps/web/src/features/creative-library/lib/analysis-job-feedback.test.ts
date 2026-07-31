import { describe, expect, it } from "vitest";
import { getAnalysisJobFeedback, restoreInterruptedAnalysisStates } from "./analysis-job-feedback";

describe("getAnalysisJobFeedback", () => {
    it("keeps one stable toast id while the job advances", () => {
        const started = getAnalysisJobFeedback("cr-1", "Sofa demo", 0, 7);
        const advanced = getAnalysisJobFeedback("cr-1", "Sofa demo", 2, 7);

        expect(started.id).toBe("creative-analysis-cr-1");
        expect(advanced.id).toBe(started.id);
        expect(started.description).toBe("Preparing creative");
        expect(advanced.description).toBe("Reading on-screen text");
    });

    it("uses a clear completion message", () => {
        expect(getAnalysisJobFeedback("cr-1", "Sofa demo", 7, 7)).toEqual({
            id: "creative-analysis-cr-1",
            title: "Creative DNA ready",
            description: "Sofa demo is ready to review.",
            complete: true,
        });
    });

    it("makes interrupted processing items retryable without changing active jobs", () => {
        const creatives = [
            { id: "stale", analysisStatus: "processing" as const, title: "Stale job" },
            { id: "active", analysisStatus: "processing" as const, title: "Active job" },
            { id: "done", analysisStatus: "analyzed" as const, title: "Finished" },
        ];

        expect(
            restoreInterruptedAnalysisStates(creatives, {
                active: { step: 2, total: 7, startedAt: 1 },
            }),
        ).toEqual([
            { id: "stale", analysisStatus: "ready", title: "Stale job" },
            { id: "active", analysisStatus: "processing", title: "Active job" },
            { id: "done", analysisStatus: "analyzed", title: "Finished" },
        ]);
    });
});
