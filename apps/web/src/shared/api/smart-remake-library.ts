import { apiGet } from "./client";

export type SmartRemakeSavedVideo = {
    id: string;
    label: string;
    kind: "final" | "clip";
    url: string;
    durationSeconds: number;
};

export type SmartRemakeProjectVideo = {
    id: string;
    projectName: string;
    createdAt: string;
    status: "draft" | "ready" | "incomplete";
    targetDuration: number;
    provider: string;
    finalVideoUrl: string;
    productImageUrl?: string;
    downloadUrl?: string;
    videos: SmartRemakeSavedVideo[];
    phase?: string | null;
    activity?: {
        operationId?: string;
        kind: string;
        status: "not_started" | "running" | "completed" | "failed";
        stage?: string;
        needsReconciliation?: boolean;
        errorCode?: string;
        plannedVideoCount?: number;
        submittedVideoCount?: number | null;
        completedVideoCount?: number;
        completedImageCount?: number;
    };
};

export type SmartRemakeProjectList = {
    items: SmartRemakeProjectVideo[];
    total: number;
    limit: number;
    offset: number;
};

export function listSmartRemakeProjects(
    workspaceId: string,
    {
        limit = 24,
        offset = 0,
        signal,
        includeUnfinished,
    }: { limit?: number; offset?: number; signal?: AbortSignal; includeUnfinished?: boolean } = {},
) {
    const search = new URLSearchParams({ limit: String(limit), offset: String(offset) });
    if (includeUnfinished) search.set("includeUnfinished", "true");
    return apiGet<SmartRemakeProjectList>(
        `/workspaces/${workspaceId}/smart-remake/projects?${search}`,
        { signal },
    );
}
