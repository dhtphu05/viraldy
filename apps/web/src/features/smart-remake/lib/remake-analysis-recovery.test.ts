import { describe, expect, it } from "vitest";
import type { SmartRemakeProject } from "@/shared/api/smart-remake";
import { getRemakeResumeStep } from "./remake-intake";
import {
    getRemakeAnalysisRecovery,
    getRemakeAnalysisRetryBinding,
} from "./remake-analysis-recovery";

const failedProject = (disposition?: "new_analysis" | "reconcile") =>
    ({
        id: "project",
        revision: 4,
        schemaVersion: 2,
        phase: "compiled",
        renderPlan: { units: [] },
        scenes: [],
        analysisProgress: {
            status: "failed",
            operationId: "failed-operation",
            requestKey: "failed-request",
            retryDisposition: disposition,
        },
    }) as unknown as SmartRemakeProject;

describe("analysis failure recovery", () => {
    it("restores failure recovery before the previous valid unrendered storyboard", () => {
        expect(getRemakeResumeStep(failedProject("new_analysis"))).toBe("prepare");
        expect(getRemakeResumeStep(failedProject("reconcile"))).toBe("prepare");
        expect(getRemakeResumeStep(failedProject())).toBe("prepare");
    });
    it("binds a fresh analysis key only to server-authorized terminal operation", () => {
        expect(getRemakeAnalysisRetryBinding(failedProject("new_analysis"))).toEqual({
            recoveryOperationId: "failed-operation",
        });
        expect(getRemakeAnalysisRetryBinding(failedProject("reconcile"))).toEqual({});
        expect(getRemakeAnalysisRetryBinding(failedProject())).toEqual({});
    });
    it("does not let the failed operation from an older tab replace a current job", () => {
        const project = failedProject("new_analysis");
        project.pendingOperation = {
            id: "newer-operation",
            status: "running",
            kind: "compile",
            needsReconciliation: false,
        };
        expect(getRemakeAnalysisRecovery(project)).toBeNull();
        expect(getRemakeAnalysisRetryBinding(project)).toEqual({});
    });
    it("clears recovery when current analysis has completed", () => {
        const project = failedProject("new_analysis");
        project.analysisProgress!.status = "completed";
        expect(getRemakeAnalysisRecovery(project)).toBeNull();
        expect(getRemakeAnalysisRecovery(null)).toBeNull();
    });
});
