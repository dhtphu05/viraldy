import { apiGet, apiPatch, apiPost, apiPostForm, type ApiRequestOptions } from "./client";
import type {
    SmartRemakeRequirements,
    SmartRemakeRights,
    SmartRemakeBudget,
    SmartRemakeInspectionReport,
    SmartRemakeInspectionReview,
    SmartRemakeAssembly,
    SmartRemakeApproval,
    SmartRemakeIntakeMetadata,
    SmartRemakeMutation,
    SmartRemakeInspectSubject,
    SmartRemakeProjectMutationResult,
    RepairIntent,
    SmartRemakeRepairReceipt,
    SmartRemakeAnalysisProgress,
    SmartRemakeGenerationRecovery,
    SmartRemakeGenerationProgress,
    SmartRemakeSourceAudio,
} from "./smart-remake-project-types";
export type * from "./smart-remake-project-types";

export type SmartRemakeHealth = {
    enabled: boolean;
    mode: "fixture" | "live";
    providers: string[];
    flowkitUrlSet: boolean;
    unificallyConfigured: boolean;
    kieConfigured?: boolean;
    openaiImagesConfigured?: boolean;
    kieVideoModel?: string;
    openaiImageModel?: string;
    limits: { referenceVideoBytes: number; productImageBytes: number };
};

export type SmartRemakeSourceSceneMap = {
    fps: 24;
    sourceStartFrame: number;
    sourceFrameCount: number;
    timingMode?: "source_rhythm" | "fit_target";
    scenes: Array<{
        id: string;
        startFrame: number;
        endFrame: number;
        targetDurationFrames: number;
        sourceSceneIndex?: number;
        prompt?: string;
        imagePrompt?: string;
        videoPrompt?: string;
        shotPlan?: Record<string, unknown>;
        thumbnailUrl?: string;
    }>;
};

export type SmartRemakeRenderGroup = {
    id: string;
    renderUnitIds: string[];
    rawDurationFrames: number;
    targetDurationFrames: number;
    segments: Array<{ renderUnitId: string; inFrame: number; outFrame: number }>;
};

export type SmartRemakeRenderPlan = {
    fps: 24;
    provider: "kie";
    groupingPolicy?: "fixed_provider_windows";
    groups?: SmartRemakeRenderGroup[];
    renderGroupBreaks?: number[];
    videoModel?: string;
    imageModel?: string;
    imageQuality?: "low" | "medium" | "high" | "xhigh" | "max";
    imageComplexity?: "low" | "medium" | "high";
    imageSize?: string;
    units: Array<{
        id: string;
        sourceSceneId: string;
        sceneIndex: number;
        sourceStartFrame?: number;
        sourceEndFrame?: number;
        fragmentIndex?: number;
        fragmentCount?: number;
        rawDurationFrames: number;
        targetDurationFrames: number;
        prompt: string;
        imagePrompt: string;
        videoPrompt: string;
    }>;
};

export type SmartRemakeTimeline = {
    fps: 24;
    totalFrames: number;
    items: Array<{
        id: string;
        sourceSceneId: string;
        renderUnitId: string;
        targetStartFrame: number;
        targetDurationFrames: number;
        versionId: string | null;
        inFrame: number;
        outFrame: number;
        reviewed: boolean;
    }>;
};

export type SmartRemakeTimelineSelectionInput = {
    renderUnitId: string;
    versionId: string;
    inFrame: number;
    outFrame: number;
    reviewed: true;
};

export type SmartRemakeCompileResult = {
    success: true;
    schemaVersion?: 1 | 2;
    projectId?: string;
    revision?: number;
    expectationsVersion?: 1;
    expectationsHash?: string;
    sourceSceneMap?: SmartRemakeSourceSceneMap;
    renderPlan?: SmartRemakeRenderPlan;
    draftTimeline?: SmartRemakeTimeline;
    mode: "smart_remake" | "montage";
    renderSubmitted: false;
    inputSummary: { targetDuration: 8 | 16; aspectRatio: "9:16"; language: string | null };
    referenceAnalysis: Record<string, unknown>;
    analyzeOutput: Record<string, unknown>;
    productLock: Record<string, unknown>;
    sceneMap: {
        targetDuration: 8 | 16;
        sceneCount: number;
        scenes: Array<Record<string, unknown>>;
    };
    compiledPrompts: Array<Record<string, unknown>>;
    compilerDiagnostics: Record<string, unknown>;
    diagnostics: Record<string, unknown>;
    versions: Record<string, unknown>;
    warnings: string[];
};

export type SmartRemakeRenderResult = {
    success: true;
    mode: "smart_remake";
    provider: string;
    finalVideoUrl: string;
    targetDuration: 8 | 16;
    sceneCount: number;
    renderSubmitted: boolean;
    status: "completed" | "submitted" | "running";
    warnings: string[];
    projectId?: string;
    videoId?: string;
    sceneIds?: string[];
    repairProject?: SmartRemakeProject;
};

export type SmartRemakeSceneVersion = {
    id: string;
    expectationsHash?: string;
    parentVersionId: string | null;
    videoUrl: string;
    prompt: string;
    imagePrompt: string;
    videoPrompt: string;
    source: "generated" | "regenerated";
    createdAt: string;
    usedByRevision?: number | null;
    rawDurationFrames?: number;
    frameCount?: number;
    renderGroupId?: string;
    suggestedInFrame?: number;
    suggestedOutFrame?: number;
    technicalCheck: {
        status: "passed" | "failed" | "needs_review";
        findings: string[];
        checkedAt: string;
        mediaHash: string;
        frameCount?: number;
    };
};

export type SmartRemakeProject = {
    id: string;
    sourceAudio?: SmartRemakeSourceAudio;
    inputMediaHashes?: { source: string; product: string; character?: string | null } | null;
    expectationsVersion?: 1 | null;
    expectationsHash?: string | null;
    revision: number;
    phase?: "intake" | "compiled" | "rendered";
    requirements?: SmartRemakeRequirements;
    rights?: SmartRemakeRights;
    budget?: SmartRemakeBudget;
    constraintsHash?: string;
    inspectionSummary?: {
        reports: SmartRemakeInspectionReport[];
        reviews: SmartRemakeInspectionReview[];
        currentReportIds?: string[];
    };
    assemblies?: {
        records: SmartRemakeAssembly[];
        activeAssemblyId: string | null;
        history?: Array<Record<string, unknown>>;
    };
    release?: {
        activeApprovalId?: string | null;
        approvals?: SmartRemakeApproval[];
        exports?: Array<Record<string, unknown>>;
        invalidationReason?: string;
    };
    deletion?: {
        status: string;
        reason?: string;
        providerDeletion?: string;
        objects?: Array<{ status: string; keyHash: string }>;
        checkedAt?: string;
    } | null;
    characterImageUrl?: string;
    inspectionMedia?: Array<{
        mediaId: string;
        mediaHash: string;
        timebase: "source" | "raw_group" | "scene_local" | "final" | "image";
        frameCount?: number;
        url: string;
        playbackTimebase?: "raw_group";
        playbackMediaId?: string;
        playbackMediaHash?: string;
        sceneId?: string;
        versionId?: string;
        assemblyId?: string;
        reportId?: string;
        contextHash?: string;
        manifestHash?: string;
    }>;
    inspectionMappings?: Array<{
        from: import("./smart-remake-project-types").SmartRemakeInspectionEvidence & {
            inFrame: number;
            outFrame: number;
        };
        to: import("./smart-remake-project-types").SmartRemakeInspectionEvidence & {
            inFrame: number;
            outFrame: number;
        };
        sceneId?: string;
        versionId?: string;
        assemblyId?: string;
        reportId?: string;
        contextHash?: string;
        manifestHash?: string;
    }>;
    status: "draft" | "ready" | "incomplete";
    schemaVersion?: 1 | 2;
    sourceSceneMap?: SmartRemakeSourceSceneMap;
    renderPlan?: SmartRemakeRenderPlan;
    draftTimeline?: SmartRemakeTimeline;
    publishedTimeline?: SmartRemakeTimeline | null;
    sourceVideoUrl?: string;
    finalVideoUrl: string;
    downloadUrl?: string;
    productImageUrl?: string;
    targetDuration: 8 | 16;
    provider: "unifically" | "flowkit" | "kie";
    analysisProgress?: SmartRemakeAnalysisProgress;
    generationRecovery?: SmartRemakeGenerationRecovery;
    generationProgress?: SmartRemakeGenerationProgress;
    pendingOperation?: {
        id: string;
        status: "running";
        needsReconciliation: boolean;
        errorCode?: string | null;
        kind?: string;
        stage?: string;
        progress?: { stage: string; completed?: number; total?: number };
    };
    lastOperation?: {
        id: string;
        status: "failed" | "completed";
        errorCode?: string | null;
        kind?: string;
        needsReconciliation?: boolean;
    };
    scenes: Array<{
        id: string;
        index: number;
        description?: string;
        startSecond: number;
        durationSeconds: number;
        rawDurationFrames?: number;
        activeVersionId: string | null;
        prompt: string;
        imagePrompt: string;
        videoPrompt: string;
        versions: SmartRemakeSceneVersion[];
    }>;
};

export type SmartRemakeOperationResult = {
    project: SmartRemakeProject;
    candidateVersionId?: string;
    operationId: string;
    status: "completed" | "running" | "failed";
};

export type SmartRemakePromptDraft = Pick<
    SmartRemakeSceneVersion,
    "prompt" | "imagePrompt" | "videoPrompt"
>;

export function getSmartRemakeHealth(workspaceId: string) {
    return apiGet<SmartRemakeHealth>(`/workspaces/${workspaceId}/smart-remake/health`);
}

export function compileSmartRemake(
    workspaceId: string,
    input: {
        targetDuration: 8 | 16;
        language: string;
        prompt: string;
        description: string;
        referenceVideo?: File;
        projectId?: string;
        expectedRevision?: number;
        idempotencyKey?: string;
        productImage?: File;
        productUrl?: string;
        productTitle?: string;
        productDescription?: string;
        timelineMode?: "reference";
        analysisScope?: "excerpt" | "full_source";
        referenceStartFrame?: number;
        sourceCutFrames?: number[];
        renderGroupBreaks?: number[];
    },
) {
    const body = new FormData();
    body.set("mode", "smart_remake");
    body.set("targetDuration", String(input.targetDuration));
    body.set("aspectRatio", "9:16");
    body.set("language", input.language);
    body.set("prompt", input.prompt);
    body.set("description", input.description);
    if (input.referenceVideo) body.set("referenceVideo", input.referenceVideo);
    if (input.projectId) body.set("projectId", input.projectId);
    if (input.expectedRevision !== undefined)
        body.set("expectedRevision", String(input.expectedRevision));
    if (input.idempotencyKey) body.set("idempotencyKey", input.idempotencyKey);
    if (input.timelineMode) body.set("timelineMode", input.timelineMode);
    if (input.analysisScope) body.set("analysisScope", input.analysisScope);
    if (input.referenceStartFrame !== undefined)
        body.set("referenceStartFrame", String(input.referenceStartFrame));
    if (input.sourceCutFrames) body.set("sourceCutFrames", JSON.stringify(input.sourceCutFrames));
    if (input.renderGroupBreaks)
        body.set("renderGroupBreaks", JSON.stringify(input.renderGroupBreaks));
    if (input.productImage) body.set("productImage", input.productImage);
    if (input.productUrl) body.set("productUrl", input.productUrl);
    if (input.productTitle) body.set("productTitle", input.productTitle);
    if (input.productDescription) body.set("productDescription", input.productDescription);
    return apiPostForm<SmartRemakeCompileResult>(
        `/workspaces/${workspaceId}/smart-remake/compile`,
        body,
    );
}

export function renderSmartRemake(
    workspaceId: string,
    input: {
        compileResult: SmartRemakeCompileResult;
        productImage?: File;
        productUrl?: string;
        provider: "fixture" | "flowkit" | "unifically" | "kie";
        projectName: string;
        idempotencyKey?: string;
        projectId?: string;
        expectedRevision?: number;
    },
) {
    const body = new FormData();
    body.set("compileResult", JSON.stringify(input.compileResult));
    if (input.productImage) body.set("productImage", input.productImage);
    if (input.productUrl) body.set("productUrl", input.productUrl);
    body.set("provider", input.provider);
    body.set("projectName", input.projectName);
    if (input.idempotencyKey) body.set("idempotencyKey", input.idempotencyKey);
    if (input.projectId) body.set("projectId", input.projectId);
    if (input.expectedRevision !== undefined)
        body.set("expectedRevision", String(input.expectedRevision));
    body.set("audioRequired", "false");
    return apiPostForm<SmartRemakeRenderResult>(
        `/workspaces/${workspaceId}/smart-remake/render`,
        body,
    );
}

export function getSmartRemakeProject(
    workspaceId: string,
    projectId: string,
    options?: ApiRequestOptions,
) {
    return apiGet<SmartRemakeProject>(
        `/workspaces/${workspaceId}/smart-remake/projects/${projectId}`,
        options,
    );
}

export function getSmartRemakeRepairReceipt(
    workspaceId: string,
    projectId: string,
    requestKey: string,
) {
    return apiGet<{ receipt: SmartRemakeRepairReceipt | null }>(
        `/workspaces/${workspaceId}/smart-remake/projects/${projectId}/repair-receipts?requestKey=${encodeURIComponent(requestKey)}`,
    );
}

export function repairSmartRemakeScene(
    workspaceId: string,
    projectId: string,
    sceneId: string,
    input: (SmartRemakePromptDraft | { repairIntent: RepairIntent }) & {
        baseVersionId: string | null;
        expectedRevision: number;
        idempotencyKey: string;
    },
) {
    return apiPost<SmartRemakeOperationResult>(
        `/workspaces/${workspaceId}/smart-remake/projects/${projectId}/scenes/${sceneId}/repairs`,
        input,
    );
}

export function acceptSmartRemakeVersion(
    workspaceId: string,
    projectId: string,
    input: {
        sceneId: string;
        versionId: string;
        expectedRevision: number;
        idempotencyKey: string;
    },
) {
    return apiPost<SmartRemakeOperationResult>(
        `/workspaces/${workspaceId}/smart-remake/projects/${projectId}/accept`,
        input,
    );
}

export function saveSmartRemakeTimeline(
    workspaceId: string,
    projectId: string,
    input: {
        expectedRevision: number;
        idempotencyKey: string;
        items: SmartRemakeTimelineSelectionInput[];
    },
) {
    return apiPatch<SmartRemakeOperationResult>(
        `/workspaces/${workspaceId}/smart-remake/projects/${projectId}/timeline`,
        input,
    );
}

export function publishSmartRemakeTimeline(
    workspaceId: string,
    projectId: string,
    input: { expectedRevision: number; idempotencyKey: string },
) {
    return apiPost<SmartRemakeOperationResult>(
        `/workspaces/${workspaceId}/smart-remake/projects/${projectId}/publish`,
        input,
    );
}

export function createSmartRemakeProject(
    workspaceId: string,
    input: {
        metadata: SmartRemakeIntakeMetadata;
        referenceVideo: File;
        productImage: File;
        characterImage?: File;
    },
) {
    const body = new FormData();
    body.set("metadata", JSON.stringify(input.metadata));
    body.set("referenceVideo", input.referenceVideo);
    body.set("productImage", input.productImage);
    if (input.characterImage) body.set("characterImage", input.characterImage);
    return apiPostForm<{ project: SmartRemakeProject }>(
        `/workspaces/${workspaceId}/smart-remake/projects`,
        body,
    );
}

export function updateSmartRemakeContext(
    workspaceId: string,
    projectId: string,
    field: "requirements" | "rights" | "budget",
    input: SmartRemakeMutation & Record<string, unknown>,
) {
    return apiPatch<{ project: SmartRemakeProject }>(
        `/workspaces/${workspaceId}/smart-remake/projects/${projectId}/${field}`,
        input,
    );
}

export function inspectSmartRemakeSubject(
    workspaceId: string,
    projectId: string,
    input: SmartRemakeMutation & { subject: SmartRemakeInspectSubject },
) {
    return apiPost<SmartRemakeOperationResult>(
        `/workspaces/${workspaceId}/smart-remake/projects/${projectId}/inspections`,
        input,
    );
}

export function reviewSmartRemakeFinding(
    workspaceId: string,
    projectId: string,
    input: SmartRemakeMutation & {
        reportId: string;
        findingId: string;
        decision: "accept" | "reject";
        reason: string;
    },
) {
    return apiPost<SmartRemakeOperationResult>(
        `/workspaces/${workspaceId}/smart-remake/projects/${projectId}/inspection-reviews`,
        input,
    );
}

export function approveSmartRemakeAssembly(
    workspaceId: string,
    projectId: string,
    input: SmartRemakeMutation & { assemblyId: string; reportId: string },
) {
    return apiPost<SmartRemakeProjectMutationResult>(
        `/workspaces/${workspaceId}/smart-remake/projects/${projectId}/approvals`,
        input,
    );
}

export function exportSmartRemakeAssembly(
    workspaceId: string,
    projectId: string,
    input: SmartRemakeMutation & { assemblyId: string; approvalId: string },
) {
    return apiPost<{
        project?: SmartRemakeProject;
        downloadUrl: string;
        assemblyId: string;
        exportMediaHash: string;
        sourceMediaHash: string;
    }>(`/workspaces/${workspaceId}/smart-remake/projects/${projectId}/exports`, input);
}

export function restoreSmartRemakeAssembly(
    workspaceId: string,
    projectId: string,
    input: SmartRemakeMutation & { assemblyId: string },
) {
    return apiPost<SmartRemakeProjectMutationResult>(
        `/workspaces/${workspaceId}/smart-remake/projects/${projectId}/restore`,
        input,
    );
}

export function deleteSmartRemakeProject(
    workspaceId: string,
    projectId: string,
    input: SmartRemakeMutation & { reason: string },
) {
    return apiPost<SmartRemakeProjectMutationResult>(
        `/workspaces/${workspaceId}/smart-remake/projects/${projectId}/deletions`,
        input,
    );
}

export function reviewSmartRemakeRights(
    workspaceId: string,
    projectId: string,
    input: SmartRemakeMutation & { evidenceNote: string },
) {
    return apiPost<SmartRemakeProjectMutationResult>(
        `/workspaces/${workspaceId}/smart-remake/projects/${projectId}/rights/reviews`,
        input,
    );
}

/** Read-only cost and scope preview; this request never uploads media or starts AI work. */
export function getSmartRemakePreflight(
    workspaceId: string,
    input: import("./smart-remake-project-types").SmartRemakePreflightRequest,
) {
    return apiPost<import("./smart-remake-project-types").SmartRemakePreflight>(
        `/workspaces/${workspaceId}/smart-remake/preflight`,
        input,
    );
}
