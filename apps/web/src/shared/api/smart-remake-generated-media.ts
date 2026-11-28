import { apiGet } from "./client";

export function getSmartRemakeGeneratedImageDownload(
    workspaceId: string,
    projectId: string,
    operationId: string,
    requestHash: string,
) {
    const ids = [workspaceId, projectId, operationId, requestHash].map(encodeURIComponent);
    return apiGet<{ url: string; filename: string }>(
        `/workspaces/${ids[0]}/smart-remake/projects/${ids[1]}/generation/${ids[2]}/images/${ids[3]}/download`,
    );
}
