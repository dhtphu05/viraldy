export type CreativePlatform = "TikTok" | "Meta" | "YouTube Shorts" | "UGC" | "Other";
export type CreativeAnalysisStatus = "unanalyzed" | "ready" | "processing" | "analyzed" | "failed";

export type CreativeAngle =
    | "Problem–solution"
    | "Before-and-after"
    | "Testimonial"
    | "Gift reaction"
    | "Product demonstration"
    | "Comparison"
    | "Social proof"
    | "Day-in-the-life";

export type ProductCategory =
    "Home & Kitchen" | "Pet" | "Beauty" | "POD Gifts" | "Home Organization";

export type CreativeReference = {
    id: string;
    title: string;
    hookExcerpt: string;
    platform: CreativePlatform;
    durationSec: number;
    mediaKind?: "image" | "video";
    mediaUrl?: string;
    posterUrl?: string;
    thumbnailUrl?: string;
    mediaAspectRatio?: "9:16" | "16:9" | "1:1" | "4:5";
    brandOrCreator: string;
    angle: CreativeAngle;
    category: ProductCategory;
    tags: string[];
    notes?: string;
    boardIds: string[];
    linkedProductId?: string;
    usedInCampaignId?: string;
    analysisStatus: CreativeAnalysisStatus;
    dnaScore?: number; // 0-100, only when analyzed
    savedAt: string;
    analyzedAt?: string;
    thumbSeed: string; // for deterministic gradient
    archived?: boolean;
};

export type CreativeBoard = {
    id: string;
    name: string;
    icon?: string;
    system?: boolean; // system boards cannot be renamed or deleted
    filter?: "all" | "recent" | "unassigned";
};

export type DnaTimelineMarker = {
    id: string;
    at: number; // seconds
    label: string;
    kind: "hook" | "reveal" | "demo" | "proof" | "offer" | "cta" | "risk";
    note: string;
};

export type DnaElement = {
    id: string;
    label: string;
    value: string;
    score?: number; // 0-100
    timestamp?: number;
    tone?: "ok" | "warn" | "info" | "neutral" | "destructive";
};

export type DnaSection = {
    id: "opening" | "product" | "narrative" | "conversion" | "execution";
    title: string;
    elements: DnaElement[];
};

export type DnaEvidence = {
    id: string;
    title: string;
    timestamp?: number;
    detail: string;
    confidence: "Low" | "Medium" | "High";
    action: string;
};

export type KcaItem = { id: string; label: string; detail: string };

export type CreativeAnalysis = {
    creativeId: string;
    decision:
        "Strong reference" | "Useful with adaptation" | "Weak product fit" | "Analyze before use";
    reason: string;
    dnaScore: number;
    confidence: "Low" | "Medium" | "High";
    analysisType: string;
    markers: DnaTimelineMarker[];
    sections: DnaSection[];
    evidence: DnaEvidence[];
    keep: KcaItem[];
    change: KcaItem[];
    avoid: KcaItem[];
    transcript: { at: number; text: string }[];
};

export type SeedProduct = {
    id: string;
    name: string;
    category: ProductCategory;
    price: number;
    readiness: "Ready" | "Setup needed" | "Out of stock";
    fulfillmentRisk: "Low" | "Medium" | "High";
    linkedCampaignCount: number;
    colorSeed: string;
    imageUrl?: string;
    imageAlt?: string;
};

export type CreativeFilterState = {
    platforms: CreativePlatform[];
    status: CreativeAnalysisStatus[];
    categories: ProductCategory[];
    angles: CreativeAngle[];
    linkage: "any" | "linked" | "unlinked";
    usedInCampaign: "any" | "yes" | "no";
    boardId?: string;
};

export const emptyFilterState: CreativeFilterState = {
    platforms: [],
    status: [],
    categories: [],
    angles: [],
    linkage: "any",
    usedInCampaign: "any",
};

export type CreativeSort = "recent-saved" | "recent-analyzed" | "dna-desc" | "duration" | "az";
