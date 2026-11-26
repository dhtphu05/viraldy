import type { SmartRemakeProject } from "@/shared/api/smart-remake";

export function getRemakeAnalysisRecovery(project: SmartRemakeProject | null | undefined) {
    const progress = project?.analysisProgress;
    return progress?.status === "failed" &&
        (!project?.pendingOperation || project.pendingOperation.id === progress.operationId)
        ? progress
        : null;
}

export function getRemakeAnalysisRetryBinding(project: SmartRemakeProject | null | undefined) {
    const progress = getRemakeAnalysisRecovery(project);
    return progress?.retryDisposition === "new_analysis"
        ? { recoveryOperationId: progress.operationId }
        : {};
}
