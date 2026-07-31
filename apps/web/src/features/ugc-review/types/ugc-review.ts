export type UgcCommerceDomain =
    "generic" | "tiktok_shop_us" | "pod_personalization" | "dropshipping";

export type UgcIntendedUse =
    "organic" | "affiliate" | "paid_candidate" | "spark_candidate" | "unknown";

export type MaterialConnection = "yes" | "no" | "unknown";
export type ReviewConfidence = "high" | "medium" | "low";
export type RecommendationGroup = "fix_first" | "improve" | "confirm";
export type RecommendationOwner = "seller" | "creator" | "editor";
export type ReviewFixType =
    | "edit_existing_footage"
    | "add_overlay"
    | "replace_copy"
    | "reshoot_scene"
    | "confirm_seller_input"
    | "request_better_media";
export type ReviewNextAction =
    "use_as_is" | "revise" | "reshoot_scene" | "confirm_information" | "request_better_media";
export type ReviewEvidenceSource =
    "video" | "transcript" | "ocr" | "seller_input" | "brief" | "policy";
export type UgcReviewStatusValue = "queued" | "running" | "completed" | "failed";
export type UgcRecommendationAction =
    "accepted" | "ignored" | "not_applicable" | "sent_to_creator" | "marked_completed";

export type UgcReviewContext = Readonly<{
    market?: string;
    platform?: string;
    commerceDomain?: UgcCommerceDomain;
    intendedUse?: UgcIntendedUse;
    productName?: string;
    productCategory?: string;
    exactVariantOrSku?: string;
    productDescription?: string;
    currentOffer?: string;
    verifiedShippingLanguage?: string;
    approvedPersonalization?: string;
    physicalSampleAvailable?: boolean;
    creatorBrief?: string;
    materialConnection?: MaterialConnection;
    sellerNotes?: string;
}>;

export type UgcReviewEvidence = Readonly<{
    id: string;
    source: ReviewEvidenceSource;
    observed: string;
    startMs: number | null;
    endMs: number | null;
    confidence: ReviewConfidence;
}>;

export type UgcRecommendation = Readonly<{
    id: string;
    ruleCode: string | null;
    mistakeCode: string | null;
    group: RecommendationGroup;
    title: string;
    reason: string;
    whyItMatters: string;
    owner: RecommendationOwner;
    fixType: ReviewFixType | null;
    instructions: readonly string[];
    strengthsToPreserve: readonly string[];
    completionCriteria: readonly string[];
    evidence: readonly UgcReviewEvidence[];
    confidence: ReviewConfidence;
    affectedUse: string | null;
}>;

export type UgcReviewResult = Readonly<{
    reviewId: string;
    status: "completed";
    assetId: string;
    assetVersionId: string;
    headline: string;
    summary: string;
    recommendedNextAction: ReviewNextAction;
    overallConfidence: ReviewConfidence;
    strengths: readonly string[];
    fixFirst: readonly UgcRecommendation[];
    improvements: readonly UgcRecommendation[];
    confirmations: readonly UgcRecommendation[];
    message: string;
    policyPackVersion: string;
    provenance: Readonly<Record<string, unknown>>;
    createdAt: string;
}>;

export type UgcReviewCreation = Readonly<{
    reviewId: string;
    status: "queued";
    mode: "ugc_review_v1";
    assetId: string;
    assetVersionId: string;
}>;

export type UgcReviewRevisionCreation = UgcReviewCreation &
    Readonly<{
        parentReviewId: string;
    }>;

export type UgcReviewStatus = Readonly<{
    reviewId: string;
    status: UgcReviewStatusValue;
    progress: number;
    stage: string;
    errorCode: string | null;
    errorMessage: string | null;
}>;

export type UgcRevisionComparison = Readonly<{
    parentReviewId: string;
    revisionReviewId: string;
    summary: string;
    resolved: readonly Readonly<Record<string, unknown>>[];
    stillOpen: readonly Readonly<Record<string, unknown>>[];
    newFindings: readonly Readonly<Record<string, unknown>>[];
    strengthsPreserved: readonly string[];
}>;
