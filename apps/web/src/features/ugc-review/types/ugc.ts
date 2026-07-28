export type UgcReviewState =
    | "new"
    | "in-review"
    | "revision-requested"
    | "creator-revising"
    | "new-version"
    | "approved"
    | "archived";

export type UgcDecision =
    | "awaiting-analysis"
    | "processing"
    | "failed"
    | "request-revision"
    | "reject"
    | "organic-ready"
    | "small-spark-test"
    | "spark-ready";

export type UgcRightsStatus =
    "not-checked" | "missing" | "organic-only" | "spark-required" | "complete" | "expiring-soon";

export type UgcReviewObjective =
    | "Organic TikTok"
    | "TikTok Shop affiliate"
    | "Spark Ads test"
    | "Paid UGC asset"
    | "Creator deliverable approval";

export type Creator = {
    id: string;
    name: string;
    handle: string;
    avatarSeed: string;
    tone: string;
};

export type UgcDimensionId =
    | "hook"
    | "product-visibility"
    | "demo-clarity"
    | "authenticity"
    | "problem-solution"
    | "offer-clarity"
    | "cta"
    | "pack-alignment"
    | "shop-readiness"
    | "compliance";

export type UgcDimension = {
    id: UgcDimensionId;
    label: string;
    score: number;
    reason: string;
    timestampSec?: number;
    requirement?: string;
    action?: string;
};

export type UgcIssueSeverity = "blocker" | "high" | "improvement" | "positive";

export type UgcIssue = {
    id: string;
    assetId: string;
    severity: UgcIssueSeverity;
    timestampSec: number;
    endSec?: number;
    title: string;
    why: string;
    packRequirement?: string;
    fix: string;
    confidence: "Low" | "Medium" | "High";
    dismissed?: boolean;
    reviewed?: boolean;
    addedToRevision?: boolean;
};

export type UgcTimelineKind =
    "hook" | "reveal" | "demo" | "proof" | "offer" | "cta" | "risk" | "missing";

export type UgcTimelineMarker = {
    id: string;
    kind: UgcTimelineKind;
    timestampSec: number;
    label: string;
    issueId?: string;
};

export type UgcTranscriptSegment = {
    id: string;
    startSec: number;
    endSec: number;
    text: string;
    flags?: Array<"product" | "cta" | "risk" | "offer">;
};

export type UgcScene = {
    id: string;
    number: number;
    startSec: number;
    endSec: number;
    label: string;
    spokenLine: string;
    onScreenText?: string;
    productVisibility: "Prominent" | "Contextual" | "Absent";
    requirementStatus: "Complete" | "Needs revision" | "Missing";
    thumbSeed: string;
};

export type UgcOnScreenText = {
    id: string;
    timestampSec: number;
    text: string;
    role: "hook" | "caption" | "cta" | "offer" | "other";
    riskFlag?: boolean;
    ctaFlag?: boolean;
    offerFlag?: boolean;
};

export type UgcPackAlignmentRow = {
    requirement: string;
    detected: string;
    status: "Complete" | "Needs revision" | "Missing";
    evidence?: string;
    action?: string;
};

export type UgcAnalysis = {
    assetId: string;
    createdAt: string;
    score: number;
    confidence: "Low" | "Medium" | "High";
    summary: string;
    reason: string;
    nextAction: string;
    dimensions: UgcDimension[];
    packAlignment: UgcPackAlignmentRow[];
    markers: UgcTimelineMarker[];
    transcript: UgcTranscriptSegment[];
    scenes: UgcScene[];
    onScreenText: UgcOnScreenText[];
    failed?: boolean;
    failureReason?: string;
};

export type UgcRights = {
    organic: boolean;
    sparkAllowed: boolean;
    metaAllowed: boolean;
    websiteAllowed: boolean;
    rawFootage: boolean;
    editingAllowed: boolean;
    durationDays?: number;
    sparkCode?: string;
    sparkExpiry?: string;
    creatorConfirmed: boolean;
    notes?: string;
};

export type UgcAsset = {
    id: string;
    title: string;
    creatorId: string;
    campaignId?: string;
    packId?: string;
    submissionVersion: number;
    previousVersionId?: string;
    thumbSeed: string;
    mediaUrl?: string; // Object URL when locally uploaded (session-only)
    posterUrl?: string;
    durationSec: number;
    submittedAt: string;
    reviewedAt?: string;
    reviewState: UgcReviewState;
    decision: UgcDecision;
    rightsStatus: UgcRightsStatus;
    objective: UgcReviewObjective;
    note?: string;
    dueDate?: string;
    archived?: boolean;
    isDemo?: boolean;
    isLocalUpload?: boolean;
    revisionMessage?: string;
};

export type UgcActivityEvent = {
    id: string;
    assetId: string;
    kind:
        | "created"
        | "analyzed"
        | "revision-requested"
        | "approved-organic"
        | "spark-ready"
        | "rejected"
        | "rights-updated"
        | "version-added"
        | "archived"
        | "note";
    detail: string;
    at: string;
};
