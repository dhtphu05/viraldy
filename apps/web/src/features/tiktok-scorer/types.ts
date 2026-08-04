export type ScoreMode = "quick" | "product_aware" | "usage_aware";
export type IntendedUse =
    "tiktok_organic" | "tiktok_shop_affiliate" | "ugc_paid_candidate" | "spark_candidate";
export type ScoreProfileCode =
    | "general_tiktok_v1"
    | "product_led_demo_v1"
    | "creator_review_v1"
    | "story_led_pov_v1"
    | "tutorial_howto_v1"
    | "unboxing_reaction_v1"
    | "comment_reply_faq_v1"
    | "offer_led_shop_v1";
export type Applicability = "applicable" | "not_applicable" | "unknown";
export type EvidenceStatus = "sufficient" | "partial" | "insufficient";
export type Confidence = "high" | "medium" | "low";
export type CreativeDecision =
    | "request_better_media"
    | "blocked"
    | "revise"
    | "usable_with_improvements"
    | "structurally_ready"
    | "pending";
export type ScoreRunStatus =
    | "uploading"
    | "queued"
    | "extracting_media"
    | "building_evidence"
    | "scoring"
    | "compiling_fixes"
    | "completed"
    | "partial_evidence"
    | "failed"
    | "cancelled"
    | string;

export type ProfileSelectionMode =
    | "user_selected"
    | "model_suggested"
    | "model_suggested_user_confirmed"
    | "inherited"
    | "user_overridden";

export type TikTokProfileSelection = {
    code: ScoreProfileCode;
    label: string;
    selectionMode: ProfileSelectionMode;
    confidence: number | null;
    reason: string | null;
    alternatives: ScoreProfileCode[];
    evidenceIds: string[];
};

export type TikTokDimension = {
    code: string;
    label: string;
    score: number | null;
    applicability: Applicability;
    evidenceStatus: EvidenceStatus;
    confidence: Confidence;
    reason: string;
    positiveSignals: string[];
    missingSignals: string[];
    uncertainty: string[];
    evidenceIds: string[];
    ruleCodes: string[];
};

export type TikTokFinding = {
    id: string;
    code: string;
    ruleCode: string | null;
    ruleClass: string | null;
    sourceDimension: string;
    severity: "hard" | "high" | "medium" | "low" | "info";
    priority: "P0" | "P1" | "P2" | "P3";
    applicability: Applicability;
    evidenceStatus: EvidenceStatus;
    title: string;
    reason: string;
    expected: Record<string, unknown>;
    observed: Record<string, unknown>;
    targetTimeRangeMs: [number, number] | null;
    evidenceIds: string[];
    uncertainty: string[];
    requiresSellerTruth: boolean;
    canBeResolvedByEdit: boolean | null;
    requiresPhysicalReshoot: boolean | null;
};

export type FixEventType =
    | "viewed"
    | "accepted"
    | "rejected"
    | "sent_to_creator"
    | "sent_to_editor"
    | "marked_completed"
    | "verified_after_revision";

export type TikTokVideoOperation = {
    operation: string;
    sourceSceneId: string | null;
    sourceRangeMs: [number, number] | null;
    targetStartMs: number | null;
    targetDurationMs: number | null;
    textValue: string | null;
    evidenceIds: string[];
    feasibility: string;
};

export type FixGroupKey = "edit" | "reshoot" | "seller" | "better_media";

export type TikTokFixAction = {
    id: string;
    code: string;
    sourceFindingId: string;
    sourceFindingCode: string;
    recommendationClass: "required_fix" | "high_priority_improvement";
    basis: string;
    priority: "P0" | "P1" | "P2";
    severity: "hard" | "high" | "medium" | "low";
    sourceDimension: string;
    ownerRole: "seller" | "creator" | "editor" | "compliance_reviewer";
    fixType: string;
    group: FixGroupKey;
    title: string;
    whyItMatters: string;
    expected: Record<string, unknown>;
    observed: Record<string, unknown>;
    evidenceIds: string[];
    targetTimeRangeMs: [number, number] | null;
    operations: TikTokVideoOperation[];
    instructions: string[];
    strengthsToPreserve: string[];
    requiredInputs: string[];
    effort: "low" | "medium" | "high";
    reshootRequired: boolean;
    completionCriteria: string[];
    verificationMethod: string;
    latestEvent: FixEventType | null;
};

export type TikTokStrength = {
    code: string;
    title: string;
    sourceDimension: string;
    evidenceIds: string[];
};

export type TikTokEvidence = {
    id: string;
    sourceType: string;
    startMs: number | null;
    endMs: number | null;
    summary: string;
    transcript: string | null;
    ocrText: string | null;
    frameUrl: string | null;
    confidence: Confidence | null;
};

export type TikTokScene = {
    id: string;
    startMs: number;
    endMs: number;
    summary: string;
    shotType: string | null;
    productVisible: boolean | null;
    productMatchConfidence: number | null;
    productVisibilityQuality: string | null;
    spokenText: string | null;
    overlayTexts: string[];
    demoStep: string | null;
    proofRole: string | null;
    creatorPresent: boolean | null;
    visualQuality: string;
    continuityGroupId: string | null;
    reusableForEdit: boolean;
    evidenceIds: string[];
};

export type TikTokSceneInventory = {
    assetVersionId: string;
    durationMs: number | null;
    audioAvailable: boolean | null;
    coverageStatus: EvidenceStatus;
    confidence: Confidence;
    scenes: TikTokScene[];
    productRanges: Array<[number, number]>;
    ctaRanges: Array<[number, number]>;
    disclosureRanges: Array<[number, number]>;
    safeZoneObservations: Array<{
        range: [number, number];
        status: string;
        reason: string;
        evidenceIds: string[];
    }>;
    evidenceIds: string[];
};

export type TikTokCreativeUpgrade = {
    id: string;
    title: string;
    whyItFits: string;
    affectsScore: false;
    keep: string[];
    change: string[];
    additionalFootage: string[];
    claimGuardrails: string[];
    expectedLearning: string | null;
};

export type TikTokScoreRun = {
    id: string;
    workspaceId: string | null;
    assetId: string | null;
    assetVersionId: string;
    assetName: string;
    productId: string | null;
    productName: string | null;
    status: ScoreRunStatus;
    currentStage: string;
    jobId: string | null;
    score: number | null;
    confidence: Confidence;
    decision: CreativeDecision;
    paidUseRightsStatus: string;
    finalPaidReadiness: string;
    scoreMode: ScoreMode;
    intendedUse: IntendedUse;
    profile: TikTokProfileSelection;
    dimensions: TikTokDimension[];
    findings: TikTokFinding[];
    fixes: TikTokFixAction[];
    strengths: TikTokStrength[];
    evidence: TikTokEvidence[];
    sceneInventory: TikTokSceneInventory | null;
    optionalUpgrades: TikTokCreativeUpgrade[];
    uncertainty: string[];
    mediaUrl: string | null;
    mediaExpiresAt: string | null;
    partialEvidence: boolean;
    revisionCount: number;
    comparisonIds: string[];
    parentScoreRunId: string | null;
    failureCode: string | null;
    failureMessage: string | null;
    createdAt: string | null;
    updatedAt: string | null;
    completedAt: string | null;
};

export type TikTokScoreList = {
    items: TikTokScoreRun[];
    total: number;
    limit: number;
    offset: number;
};

export type TikTokScoreProfile = {
    code: ScoreProfileCode;
    label: string;
    version: number;
    description: string;
    isDefault: boolean;
    suggested: boolean;
    suggestionConfidence: number | null;
    suggestionReason: string | null;
};

export type TikTokComparisonFinding = {
    code: string;
    title: string;
    beforeEvidenceIds: string[];
    afterEvidenceIds: string[];
};

export type TikTokScoreComparison = {
    id: string;
    beforeScoreRunId: string | null;
    afterScoreRunId: string | null;
    beforeAssetVersionId: string;
    afterAssetVersionId: string;
    beforeScore: number | null;
    afterScore: number | null;
    scoreDelta: number | null;
    status: string;
    resolved: TikTokComparisonFinding[];
    unresolved: TikTokComparisonFinding[];
    regressions: TikTokComparisonFinding[];
    dimensions: Array<{
        code: string;
        beforeScore: number | null;
        afterScore: number | null;
        beforeApplicability: Applicability | null;
        afterApplicability: Applicability | null;
    }>;
    evidence: Array<{
        subjectCode: string;
        beforeEvidenceIds: string[];
        afterEvidenceIds: string[];
    }>;
    strengths: TikTokStrength[];
    actions: Array<{
        actionId: string;
        actionCode: string;
        sourceFindingCode: string;
        status: "verified" | "not_verified" | "not_evaluated";
        before: Record<string, unknown>;
        after: Record<string, unknown>;
        beforeEvidenceIds: string[];
        afterEvidenceIds: string[];
        reason: string;
    }>;
    finalNextAction: string;
    likeForLike: boolean;
    warning: string | null;
};
