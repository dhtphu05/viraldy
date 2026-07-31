import type { CreativeAngle, ProductCategory } from "@/features/creative-library/types/creative";

export type CampaignObjective =
    | "Organic Product Test"
    | "TikTok Shop Affiliate"
    | "UGC Paid Asset"
    | "Spark Ads Test"
    | "POD Gift Campaign"
    | "Dropshipping Product Demo";

export type CampaignPlatform =
    "TikTok Shop" | "TikTok Organic" | "TikTok Spark Ads" | "Meta UGC Ads";

export type CampaignMarket = "US" | "UK" | "CA" | "AU" | "DE";

export type CreatorTone =
    "Natural" | "Energetic" | "Conversational" | "Expert" | "Emotional" | "Minimal / Raw UGC";

export type CreatorType =
    "Micro creator" | "Mid-tier creator" | "UGC-only" | "Product expert" | "Lifestyle";

export type CampaignPackStatus =
    | "Draft"
    | "Ready for creator"
    | "Creator production"
    | "Awaiting UGC"
    | "Active"
    | "Completed"
    | "Archived";

export type StepId =
    | "product"
    | "references"
    | "adaptation"
    | "angles"
    | "hooks"
    | "script"
    | "storyboard"
    | "cta"
    | "deliverables"
    | "review";

export type HookType =
    | "Problem-first"
    | "Curiosity"
    | "Product reveal"
    | "Social proof"
    | "Comparison"
    | "Emotional identity"
    | "Gift reaction";

export type StructuralFit = "Strong fit" | "Good test" | "Experimental" | "Needs product proof";

export type AngleConcept = {
    id: string;
    name: string;
    buyerProblem: string;
    emotionalTrigger: string;
    creatorPersona: string;
    productProof: string;
    recommendedFormat: string;
    fit: StructuralFit;
    reason: string;
    referenceCreativeId?: string;
    archived?: boolean;
    manual?: boolean;
};

export type Hook = {
    id: string;
    text: string;
    type: HookType;
    sourceAngleId?: string;
    creatorStyle: string;
    fit: StructuralFit;
    riskFlag?: string;
    locked?: boolean;
    manual?: boolean;
};

export type ScriptBlockKind =
    | "Hook"
    | "Buyer Problem"
    | "Product Introduction"
    | "Demo"
    | "Proof"
    | "Benefits"
    | "Offer"
    | "CTA";

export type ScriptBlock = {
    id: string;
    kind: ScriptBlockKind;
    text: string;
    note?: string;
    locked?: boolean;
};

export type StoryboardScene = {
    id: string;
    label: string;
    durationRange: string;
    visualDirection: string;
    spokenLine: string;
    onScreenText?: string;
    productVisibility: "Prominent" | "Contextual" | "Absent";
    framing: string;
    requiredAsset?: string;
    referenceCreativeId?: string;
    mustShow?: boolean;
    optional?: boolean;
};

export type ClaimWarning = {
    id: string;
    phrase: string;
    risk: "Low" | "Medium" | "High";
    reason: string;
    reviewed?: boolean;
};

export type UsageRights = {
    tiktokOrganic: boolean;
    tiktokSpark: boolean;
    metaAds: boolean;
    website: boolean;
    email: boolean;
    editingAllowed: boolean;
    rawFootageIncluded: boolean;
    usageDurationDays: number;
    creatorAttribution: boolean;
};

export type SparkAuth = {
    required: boolean;
    durationDays: number;
    requestTiming: string;
};

export type Deliverables = {
    numberOfVideos: number;
    rawFootageRequired: boolean;
    aspectRatio: "9:16" | "1:1" | "4:5" | "16:9";
    targetDurationSec: number;
    captionRequired: boolean;
    productTagRequired: boolean;
    revisionRounds: number;
    dueDate?: string;
};

export type ActivityEvent = {
    id: string;
    campaignId: string;
    kind:
        | "created"
        | "product-selected"
        | "reference-added"
        | "angle-changed"
        | "hook-selected"
        | "script-updated"
        | "scene-regenerated"
        | "marked-ready"
        | "brief-copied"
        | "exported"
        | "adaptation-regenerated"
        | "note";
    detail: string;
    at: string;
};

export type CampaignPack = {
    id: string;
    name: string;
    status: CampaignPackStatus;
    objective: CampaignObjective;
    market: CampaignMarket;
    platform: CampaignPlatform;
    productId?: string;
    buyerSegment: string;
    language: string;
    creatorType: CreatorType;
    creatorTone: CreatorTone;

    referenceCreativeIds: string[];

    adaptation: {
        sourceHook: string;
        sourceAngle: string;
        sourceDemo: string;
        adaptedHook: string;
        adaptedAngle: string;
        adaptedDemo: string;
        whyChanged: string;
        keep: string[];
        change: string[];
        avoid: string[];
        notes: string;
        locked?: boolean;
    };

    angleOptions: AngleConcept[];
    primaryAngleId?: string;
    secondaryAngleIds: string[];

    hookOptions: Hook[];
    selectedHookIds: string[];

    script: ScriptBlock[];

    storyboard: StoryboardScene[];

    cta: {
        primary: string;
        productTagInstruction: string;
        offerStatement: string;
        coupon: string;
        shipping: string;
        claimsAllowed: string[];
        claimsToAvoid: string[];
        productLimitations: string;
        complianceNotes: string;
        warnings: ClaimWarning[];
    };

    deliverables: Deliverables;
    rights: UsageRights;
    spark: SparkAuth;

    reviewedWarningIds: string[];

    createdAt: string;
    updatedAt: string;
    savedAt?: string;
    archived?: boolean;
};

export type CampaignTemplate = {
    id: string;
    name: string;
    description: string;
    objective: CampaignObjective;
    platform: CampaignPlatform;
    creatorType: CreatorType;
    creatorTone: CreatorTone;
    suggestedAspectRatio: Deliverables["aspectRatio"];
    suggestedDurationSec: number;
};

export type CampaignDraft = Partial<
    Pick<
        CampaignPack,
        | "name"
        | "objective"
        | "market"
        | "platform"
        | "productId"
        | "buyerSegment"
        | "language"
        | "creatorType"
        | "creatorTone"
        | "referenceCreativeIds"
    >
> & { templateId?: string };
