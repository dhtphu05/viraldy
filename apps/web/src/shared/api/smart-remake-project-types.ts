export type SmartRemakeRequirements = {
    intent: string;
    keep: string[];
    replace: string[];
    forbid: string[];
    claims: string[];
    requiresCharacter: boolean;
    characterReferencePolicy?: "product_and_character";
};

export type SmartRemakeRightsDeclaration = {
    basis: "owned" | "licensed" | "permission" | "public_domain" | "attested";
    scope: string;
    declared: boolean;
    evidenceNote: string;
    attribution?: string | null;
    revoked?: boolean;
    verified?: boolean;
    verification?: {
        status?: string;
        reviewedBy?: string | null;
        reviewedAt?: string | null;
        evidenceNote?: string;
    };
};

export type SmartRemakeRights = {
    source: SmartRemakeRightsDeclaration;
    product: SmartRemakeRightsDeclaration;
    character?: SmartRemakeRightsDeclaration | null;
    characterConsent?: {
        consented: boolean;
        scope: string;
        evidenceNote: string;
        revoked?: boolean;
    } | null;
    providerDisclosureAcknowledged: boolean;
    attestation?: {
        policyVersion: "smart-remake-media-rights-v1";
        accepted: boolean;
        revoked?: boolean;
        acceptedBy?: string | null;
        acceptedAt?: string | null;
        statement?: string;
    } | null;
    verification?: {
        status?: string;
        actorId?: string;
        reviewedAt?: string;
        evidenceNote?: string;
    };
};

export type SmartRemakeBudgetPolicy =
    | {
          mode: "unlimited";
          capUsd?: undefined;
          maxAttempts?: undefined;
          maxDurationSeconds?: undefined;
      }
    | { mode?: "limited"; capUsd: string; maxAttempts: number; maxDurationSeconds: number };
export type SmartRemakeBudget = {
    policy: SmartRemakeBudgetPolicy;
    reservedUsd?: string | null;
    actualUsd?: string | null;
    estimatedUsd?: string | null;
    remainingUsd?: string | null;
    attempts?: number;
    unknownCosts?: number;
    costStatus?: "estimated" | "actual" | "unknown";
    attemptsUsed?: number;
    needsReconciliation?: boolean;
    attemptCount?: number;
    unknownAttemptCount?: number;
    knownActualUsd?: string;
    exposureUsd?: string | null;
    knownEstimatedUsd?: string;
    knownExposureUsd?: string;
    unknownEstimateAttemptCount?: number;
    startedAt?: string | null;
    status?: string;
};

export type SmartRemakeInspectionStatus =
    "passed" | "failed" | "needs_review" | "insufficient_evidence";
export type SmartRemakeInspectionClock = "source" | "raw_group" | "scene_local" | "final" | "image";
export type SmartRemakeInspectionEvidence = {
    mediaId: string;
    mediaHash: string;
    timebase?: Exclude<SmartRemakeInspectionClock, "image"> | null;
    inFrame?: number | null;
    outFrame?: number | null;
    range?: { inFrame: number; outFrame: number } | null;
    assetId?: string | null;
    sampleId?: string | null;
    sceneId?: string | null;
    versionId?: string | null;
    assemblyId?: string | null;
};
export type SmartRemakeInspectionFinding = {
    id: string;
    requirementId: string;
    category: string;
    expected: string;
    observed: string;
    status: SmartRemakeInspectionStatus;
    severity: "info" | "warning" | "error" | "critical";
    evidence: SmartRemakeInspectionEvidence[];
    suggestedAction: string;
    hardBlocking?: boolean;
    blocking?: boolean;
};
export type SmartRemakeInspectionReport = {
    id: string;
    expectationsHash?: string | null;
    schemaVersion: number;
    subject: {
        kind: "image" | "scene" | "assembly";
        projectId: string;
        mediaHash: string;
        mediaId?: string;
        sceneId?: string | null;
        versionId?: string | null;
        assemblyId?: string | null;
        range?: {
            inFrame: number;
            outFrame: number;
            fps?: 24;
            timebase?: "source" | "raw_group" | "scene_local" | "final";
        } | null;
        neighborVersionIds?: string[];
    };
    status: SmartRemakeInspectionStatus;
    checkedAt: string;
    checkerVersion: string;
    rubricVersion: string;
    modelProfile: string | Record<string, unknown>;
    constraintsHash: string;
    manifestHash: string;
    contextHash?: string;
    coverage: Array<{
        requirementId: string;
        status: SmartRemakeInspectionStatus;
        evidence: SmartRemakeInspectionEvidence[];
        sampledFrames: number[];
        unobservedFrames: number;
        limitations: string[];
    }>;
    findings: SmartRemakeInspectionFinding[];
    observations?: Array<
        SmartRemakeInspectionEvidence & { id: string; imageHash: string; mimeType: string }
    >;
    notApplicableRequirements?: Array<{ requirementId: string; reason: string }>;
    stale?: boolean;
};
export type SmartRemakeInspectionReview = {
    reportId: string;
    findingId: string;
    decision: "accept" | "reject";
    reason: string;
    actorId: string;
    reviewedAt: string;
};
export type SmartRemakeAssembly = {
    id: string;
    expectationsHash?: string;
    projectId: string;
    schemaVersion: number;
    parentAssemblyId: string | null;
    restoredFromAssemblyId?: string;
    mediaHash: string;
    manifestHash: string;
    constraintsHash: string;
    contextHash: string;
    revision: number;
    createdAt: string;
    technicalCheck: { status: string; mediaHash: string; frameCount?: number };
    timeline: import("./smart-remake").SmartRemakeTimeline;
};
export type SmartRemakeApproval = {
    id: string;
    expectationsHash?: string;
    status: string;
    assemblyId: string;
    mediaHash: string;
    manifestHash: string;
    constraintsHash: string;
    reportId: string;
    approvedAt: string;
};
export type SmartRemakeIntakeMetadata = {
    idempotencyKey: string;
    projectName: string;
    targetDuration: 8 | 12 | 16;
    requirements: SmartRemakeRequirements;
    rights: SmartRemakeRights;
    budget: SmartRemakeBudgetPolicy;
};
export type SmartRemakeMutation = { expectedRevision: number; idempotencyKey: string };
export type SmartRemakeProjectMutationResult = {
    project?: import("./smart-remake").SmartRemakeProject;
    status?: string;
    operationId?: string;
};
export type SmartRemakeInspectSubject =
    | { kind: "scene"; sceneId: string; versionId: string }
    | { kind: "assembly"; assemblyId: string }
    | { kind: "image"; imageRole: "product" | "character" };

export type SmartRemakePreflightAction = "analyze" | "reanalyze" | "render" | "repair" | "inspect";
export type RepairIntent = {
    schemaVersion: 1;
    issues: Array<"product_fidelity" | "action" | "presentation" | "alternate_take">;
    instruction: string;
    advancedEdits?: { prompt?: string; imagePrompt?: string; videoPrompt?: string };
};
export type SmartRemakeRepairReceipt = {
    operationId: string;
    sceneId: string | null;
    baseVersionId: string | null;
    candidateVersionId: string | null;
    status: string;
    errorCode?: string | null;
    needsReconciliation: boolean;
    normalizationReason?: string | null;
};
export type SmartRemakePreflightRequest = {
    action: SmartRemakePreflightAction;
    projectId?: string;
    expectedRevision?: number;
    targetDuration?: 8 | 12 | 16;
    referenceStartFrame?: number;
    analysisScope?: "excerpt" | "full_source";
    sourceDurationSeconds?: number;
    budgetMode?: "unlimited" | "limited";
    requiresCharacter?: boolean;
    sceneId?: string;
    baseVersionId?: string | null;
    repairIntent?: RepairIntent;
    subject?: SmartRemakeInspectSubject;
};
export type SmartRemakePreflight = {
    action: SmartRemakePreflightAction;
    projectId?: string | null;
    revision?: number | null;
    contextHash: string;
    mode: string;
    scope: {
        targetDuration: 8 | 12 | 16;
        sceneCount: number;
        groupCount: number;
        imageCount: number;
        sourceStartFrame?: number;
        sourceEndFrame?: number;
        analysisScope?: "excerpt" | "full_source";
        sceneId?: string | null;
        baseVersionId?: string | null;
    };
    calls: { analysis: number; image: number; video: number; inspection: number; total: number };
    budget: null | {
        knownActualUsd: string;
        reservedUsd: string | null;
        exposureUsd: string | null;
        additionalReservationUsd: string | null;
        minimumCapUsd: string | null;
        minimumMaxAttempts: number | null;
        minimumDurationSeconds: number | null;
        unknownCostAttempts?: number;
        recommended: SmartRemakeBudgetPolicy;
    };
    blockers: Array<{
        code: string;
        message: string;
        action?: "refresh" | "reconcile" | "new_project" | "configure" | null;
    }>;
};
export interface SmartRemakeSourceAudio {
    schemaVersion: 1;
    speech: "present" | "not_detected" | "unclear";
    transcript?: string;
    language?: string;
    music: "present" | "not_detected" | "unclear";
    description?: string;
    pace?: "slow" | "medium" | "fast" | "unclear";
}

export interface SmartRemakeAnalysisProgress {
    schemaVersion: 1;
    operationId: string;
    requestKey: string;
    status: "running" | "completed" | "failed";
    retryDisposition?: "new_analysis" | "reconcile";
    stage:
        | "validating_source"
        | "analyzing_source"
        | "resolving_scenes"
        | "identifying_product"
        | "building_storyboard"
        | "completed"
        | "failed";
    startedAt: string;
    updatedAt: string;
    sourceDurationSeconds?: number;
    sourceAudio?: SmartRemakeSourceAudio;
    preliminaryObservations?: Array<{ label: string; detail: string }>;
    quickSummary?: {
        status: "pending" | "completed" | "unavailable";
        reason?: "timeout" | "invalid_response" | "unavailable";
        summary?: string;
        observations?: Array<{ label: string; detail: string }>;
        sourceAudio?: SmartRemakeSourceAudio;
    };
    sceneCount?: number;
    scenes: Array<{
        index: number;
        startSecond: number;
        endSecond: number;
        action: string;
        camera?: string;
        transition?: string;
    }>;
    product?: { name: string; details: string[] };
    errorCode?: string;
}

export interface SmartRemakeGenerationRecovery {
    kind: "retry_initial_render";
    stage: "image";
    errorCode: string;
    requestKey: string;
    providerErrorCode?: string;
    httpStatus?: number;
    retryAfterSeconds?: number;
}

export type SmartRemakeGenerationStage =
    | "queued"
    | "preparing_image"
    | "checking_image"
    | "submitting_video"
    | "generating"
    | "checking"
    | "completed"
    | "blocked"
    | "unknown";

export type SmartRemakeProviderError = {
    httpStatus?: number;
    providerCode?: string | number;
    providerMessage?: string;
};

export type SmartRemakeConditioningImage = {
    renderUnitId: string;
    url: string;
    requestHash?: string;
    frameRole?: "opening" | "ending";
};

export type SmartRemakeKieRequest = {
    model: string;
    prompt: string;
    requestHash: string;
};

export type SmartRemakeGenerationProgress = {
    operationId: string;
    status: "running" | "completed" | "failed";
    startedAt: string;
    updatedAt: string;
    groups: Array<{
        groupId: string;
        stage: SmartRemakeGenerationStage;
        videoSubmitted: boolean | null;
        conditioningImageUrl?: string;
        conditioningImages?: SmartRemakeConditioningImage[];
        kieRequest?: SmartRemakeKieRequest;
        videoUrl?: string;
        errorCode?: string;
        providerError?: SmartRemakeProviderError;
        providerTaskId?: string;
        inspectionReportId?: string;
    }>;
};
