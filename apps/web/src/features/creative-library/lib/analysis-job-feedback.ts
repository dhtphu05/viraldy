import { analysisSteps } from "./mockAnalysis";
import type { CreativeAnalysisStatus } from "@/features/creative-library/types/creative";

type AnalysisJobMap = Record<string, { step: number; total: number; startedAt: number }>;

export function restoreInterruptedAnalysisStates<
    T extends { id: string; analysisStatus: CreativeAnalysisStatus },
>(
    creatives: T[],
    jobs: AnalysisJobMap,
): Array<Omit<T, "analysisStatus"> & { analysisStatus: CreativeAnalysisStatus }> {
    return creatives.map((creative) =>
        creative.analysisStatus === "processing" && !jobs[creative.id]
            ? { ...creative, analysisStatus: "ready" }
            : creative,
    );
}

export function getAnalysisJobFeedback(
    creativeId: string,
    creativeTitle: string,
    step: number,
    total: number,
) {
    const id = `creative-analysis-${creativeId}`;
    if (step >= total) {
        return {
            id,
            title: "Creative DNA ready",
            description: `${creativeTitle} is ready to review.`,
            complete: true,
        } as const;
    }

    return {
        id,
        title: "Analyzing Creative DNA",
        description: analysisSteps[Math.min(step, analysisSteps.length - 1)]?.label ?? "Analyzing",
        complete: false,
    } as const;
}
