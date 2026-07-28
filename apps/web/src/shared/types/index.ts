export type Workspace = {
    id: string;
    name: string;
    handle: string;
    color: string;
};

export type MetricTone = "neutral" | "ok" | "warn" | "info" | "destructive";

export type Metric = {
    id: string;
    label: string;
    value: string;
    delta?: string;
    deltaTone?: MetricTone;
    hint?: string;
    tone?: MetricTone;
};

export type DecisionSeverity = "info" | "warn" | "destructive" | "ok";

export type DecisionItem = {
    id: string;
    severity: DecisionSeverity;
    title: string;
    description: string;
    object: string;
    objectType: "UGC" | "Asset" | "Campaign" | "Sample";
    urgency: string;
    action: string;
    evidence: string[];
    confidence: "Low" | "Medium" | "High";
    nextAction: string;
    reason: string;
};

export type RecommendationKind = "Scale" | "Fix" | "Rehire" | "Stop testing";

export type Recommendation = {
    id: string;
    kind: RecommendationKind;
    title: string;
    summary: string;
    metric: { label: string; value: string };
    confidence: "Low" | "Medium" | "High";
    reason: string;
    evidence: string[];
};

export type CampaignStatus = "Live" | "Testing" | "Paused" | "Draft";

export type Campaign = {
    id: string;
    name: string;
    product: string;
    status: CampaignStatus;
    activeAssets: number;
    ugcScore: number;
    gmv: number;
    nextAction: string;
};

export type Activity = {
    id: string;
    kind: "analysis" | "message" | "pack" | "asset" | "recommendation";
    title: string;
    subject: string;
    at: string; // ISO date
};
