export type DecisionKind =
    | "Scale"
    | "Fix creative"
    | "Fix product page"
    | "Fix offer"
    | "Rehire creator"
    | "Test Spark"
    | "Refresh hook"
    | "Hold"
    | "Stop asset"
    | "Stop campaign"
    | "Request more data";

export type DecisionGroup = "Scale" | "Fix" | "Rehire" | "Hold" | "Stop" | "Refresh";

export type Confidence = "Low" | "Medium" | "High";

export type PerfAsset = {
    id: string;
    campaignId: string;
    name: string;
    version: string;
    creatorId: string;
    creator: string;
    product: string;
    angle: string;
    hook: string;
    hookType: string;
    ugcScore: number;
    rightsStatus: "complete" | "organic-only" | "spark-required" | "missing" | "not-checked";
    views: number;
    watchRate: number; // 0..1
    ctr: number; // 0..1
    productClicks: number;
    addToCart: number;
    orders: number;
    gmv: number;
    commission: number;
    sampleCost: number;
    adSpend: number;
    refunds: number;
    cogs: number;
    createdAt: string;
    ageDays: number;
    mediaKind?: "image" | "video";
    mediaUrl?: string;
    posterUrl?: string;
    mediaAspectRatio?: "9:16" | "16:9" | "1:1" | "4:5";
    isImprovedVersion?: boolean;
    fatigueSignal?: "none" | "monitor" | "prepare-refresh" | "high" | "stop-scaling";
    ctrTrendPct?: number; // e.g. -0.28
    hookRepeatCount?: number;
};

export type CampaignPerfSummary = {
    campaignId: string;
    campaignName: string;
    product: string;
    status: "Live" | "Testing" | "Paused" | "Draft";
    activeAssets: number;
    gmv: number;
    grossProfit: number;
    sampleEfficiency: number; // gmv per $1 sample
    adSpend: number;
    roas: number | null;
    orders: number;
    productClicks: number;
    ctr: number;
    watchRate: number;
    refundRate: number;
    rightsReady: number;
    avgUgcScore: number;
    dataQuality: DataQualityStatus;
    primaryDecision: DecisionGroup;
    lastUpdated: string;
};

export type DataQualityStatus =
    "complete" | "partial" | "needs-mapping" | "missing-required" | "duplicate";

export type PerfRecommendation = {
    id: string;
    kind: DecisionKind;
    group: DecisionGroup;
    campaignId: string;
    object: string;
    objectType: "asset" | "campaign" | "creator" | "product-page" | "offer";
    objectId?: string;
    title: string;
    reason: string;
    evidence: string[];
    supportingMetrics: { label: string; value: string }[];
    estimatedImpact: string;
    confidence: Confidence;
    nextAction: string;
    mediaKind?: "image" | "video";
    mediaUrl?: string;
    posterUrl?: string;
    mediaAspectRatio?: "9:16" | "16:9" | "1:1" | "4:5";
    assumptions?: string[];
    missingData?: string[];
    risks?: string[];
    createdAt: string;
};

export type WinningPattern = {
    id: string;
    campaignId: string;
    angle: string;
    hook: string;
    creatorType: string;
    productReveal: string;
    proof: string;
    cta: string;
    signal: string; // e.g. "+42% gross profit vs median"
    confidence: Confidence;
};

export type FatigueAlert = {
    id: string;
    campaignId: string;
    assetId: string;
    assetName: string;
    state: "monitor" | "prepare-refresh" | "high" | "stop-scaling";
    ctrDeclinePct: number;
    reason: string;
    suggestion: string;
};

export type CreatorPerf = {
    creatorId: string;
    handle: string;
    campaigns: number;
    assets: number;
    sampleCost: number;
    gmv: number;
    grossProfit: number;
    gmvPerSample: number;
    avgUgcScore: number;
    rightsReady: number;
    recommendation:
        "Rehire" | "Test another product" | "Affiliate-only" | "Monitor" | "Do not send";
};

export type TrendPoint = {
    date: string; // ISO
    gmv: number;
    grossProfit: number;
    orders: number;
    productClicks: number;
    ctr: number;
    watchRate: number;
    sampleEfficiency: number;
};

export type PerfReport = {
    id: string;
    name: string;
    type:
        | "Weekly Creative Decisions"
        | "Winning Assets"
        | "Creator Rehire"
        | "Sample Efficiency"
        | "Creative Fatigue"
        | "Product Comparison"
        | "Angle Performance"
        | "Spark-ready Assets";
    scope: string;
    dateRange: string;
    lastGenerated: string;
    includedAssets: number;
    status: "Ready" | "Generating" | "Stale";
};

export type PatternVariant = {
    id: string;
    name: string;
    patternId: string;
    keep: string;
    change: string;
    creator: string;
    cta: string;
    priority: "High" | "Medium" | "Low";
    reason: string;
    createdAt: string;
};

export type PerfActivity = {
    id: string;
    at: string;
    kind:
        | "accepted"
        | "dismissed"
        | "snoozed"
        | "imported"
        | "exported"
        | "pattern-saved"
        | "variants-generated"
        | "review-started"
        | "rehire";
    detail: string;
    campaignId?: string;
};

export type SavedView = {
    id: string;
    name: string;
    filters: PerfFilters;
    createdAt: string;
};

export type PerfFilters = {
    dateRange: "7d" | "14d" | "30d" | "90d" | "custom";
    campaignId?: string;
    productId?: string;
    creatorId?: string;
    objective?: string;
    decision?: DecisionGroup | "All";
    source?: "all" | "imported" | "demo";
    search?: string;
};

export type ImportRow = {
    id: string;
    raw: Record<string, string>;
    mappedAssetId?: string;
    status: "matched" | "multiple" | "unmatched" | "ignored" | "duplicate";
};

export type ImportBatch = {
    id: string;
    name: string;
    source: "csv" | "paste" | "demo";
    createdAt: string;
    rowCount: number;
    matched: number;
    unmatched: number;
    duplicates: number;
    missingFields: string[];
};
