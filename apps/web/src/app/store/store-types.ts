import type { Campaign } from "@/shared/types";
import type { SeedCampaign } from "@/features/campaigns/mocks/campaigns";
import type {
    CreativeAnalysis,
    CreativeAnalysisStatus,
    CreativeBoard,
    CreativeReference,
} from "@/features/creative-library/types/creative";
import type {
    ActivityEvent,
    CampaignDraft,
    CampaignPack,
    CampaignPackStatus,
} from "@/features/campaigns/types/campaign";
import type {
    UgcActivityEvent,
    UgcAnalysis,
    UgcAsset,
    UgcDecision,
    UgcIssue,
    UgcReviewState,
    UgcRights,
} from "@/features/ugc-review/types/ugc";
import type {
    ImportBatch,
    PatternVariant,
    PerfActivity,
    PerfFilters,
    PerfRecommendation,
    PerfReport,
    SavedView,
    WinningPattern,
} from "@/features/performance/types/performance";

export type DemoImport = {
    id: string;
    name: string;
    source: string;
    createdAt: string;
};

export type AdaptationHandoff = {
    creativeId: string;
    productId: string;
    createdAt: string;
};

export type AppState = {
    // Shell
    sidebarCollapsed: boolean;
    toggleSidebar: () => void;
    setSidebarCollapsed: (v: boolean) => void;

    currentWorkspaceId: string;
    setCurrentWorkspace: (id: string) => void;

    // Dashboard
    dismissedRecommendations: string[];
    acceptedRecommendations: string[];
    dismissRecommendation: (id: string) => void;
    acceptRecommendation: (id: string) => void;

    demoCampaigns: Campaign[];
    addDemoCampaign: (c: Campaign) => void;

    demoImports: DemoImport[];
    addDemoImport: (i: DemoImport) => void;

    // Creative Library
    boards: CreativeBoard[];
    createBoard: (name: string) => CreativeBoard;
    renameBoard: (id: string, name: string) => void;
    duplicateBoard: (id: string) => void;
    deleteBoard: (id: string) => void;

    creatives: CreativeReference[];
    addCreative: (c: CreativeReference) => void;
    updateCreative: (id: string, patch: Partial<CreativeReference>) => void;
    moveCreativeToBoard: (creativeId: string, boardId: string) => void;
    archiveCreative: (id: string) => void;
    duplicateCreative: (id: string) => void;

    analyses: Record<string, CreativeAnalysis>;
    saveAnalysis: (a: CreativeAnalysis) => void;

    analysisJobs: Record<string, { step: number; total: number; startedAt: number }>;
    startAnalysisJob: (creativeId: string, total: number) => void;
    advanceAnalysisJob: (creativeId: string) => void;
    failAnalysisJob: (creativeId: string) => void;
    clearAnalysisJob: (creativeId: string) => void;

    adaptationNotes: Record<string, string[]>;
    addAdaptationNote: (creativeId: string, note: string) => void;

    lastAdaptation?: AdaptationHandoff;
    setLastAdaptation: (h: AdaptationHandoff) => void;

    // Campaigns
    packs: Record<string, CampaignPack>;
    localCampaignSummaries: SeedCampaign[];
    campaignActivity: ActivityEvent[];
    packAutosaveAt: Record<string, string>;
    campaignDraft: CampaignDraft;

    createCampaignPack: (input: {
        campaignId: string;
        packId: string;
        pack: CampaignPack;
        summary: SeedCampaign;
    }) => void;
    updateCampaignPack: (id: string, patch: Partial<CampaignPack>) => void;
    setPackStatus: (id: string, status: CampaignPackStatus) => void;
    duplicateCampaign: (campaignId: string) => string | undefined;
    archiveCampaign: (campaignId: string) => void;
    deleteLocalCampaign: (campaignId: string) => void;
    renameCampaign: (campaignId: string, name: string) => void;
    reviewWarning: (packId: string, warningId: string) => void;
    addActivity: (event: Omit<ActivityEvent, "id" | "at">) => void;
    setDraft: (patch: CampaignDraft) => void;
    clearDraft: () => void;

    // UGC Review
    ugcAssets: UgcAsset[];
    ugcAnalyses: Record<string, UgcAnalysis>;
    ugcIssues: Record<string, UgcIssue[]>;
    ugcRights: Record<string, UgcRights>;
    ugcActivity: UgcActivityEvent[];
    ugcJobs: Record<string, { step: number; total: number; startedAt: number }>;

    uploadUgc: (
        input: Omit<UgcAsset, "id" | "submittedAt" | "reviewState" | "decision" | "rightsStatus"> &
            Partial<Pick<UgcAsset, "reviewState" | "decision" | "rightsStatus">>,
    ) => string;
    startUgcAnalysis: (assetId: string, totalSteps: number) => void;
    advanceUgcJob: (assetId: string) => void;
    completeUgcAnalysis: (assetId: string) => void;
    failUgcAnalysis: (assetId: string, reason?: string) => void;
    retryUgcAnalysis: (assetId: string) => void;
    setUgcDecision: (assetId: string, decision: UgcDecision) => void;
    setUgcReviewState: (assetId: string, reviewState: UgcReviewState) => void;
    toggleIssueInRevision: (assetId: string, issueId: string) => void;
    reviewIssue: (assetId: string, issueId: string) => void;
    dismissIssue: (assetId: string, issueId: string, dismissed: boolean) => void;
    setRevisionMessage: (assetId: string, message: string) => void;
    markRevisionRequested: (assetId: string) => void;
    approveUgcOrganic: (assetId: string, note?: string) => void;
    markUgcSparkReady: (assetId: string) => { ok: true } | { ok: false; blockers: string[] };
    rejectUgc: (assetId: string) => void;
    updateUgcRights: (assetId: string, patch: Partial<UgcRights>) => void;
    archiveUgc: (assetId: string) => void;
    deleteLocalUgc: (assetId: string) => void;
    addUgcActivity: (event: Omit<UgcActivityEvent, "id" | "at">) => void;

    // Performance
    perfRecommendations: PerfRecommendation[];
    perfAcceptedRecs: string[];
    perfDismissedRecs: Record<string, string>; // id -> reason
    perfSnoozedRecs: Record<string, string>; // id -> until ISO
    perfReports: PerfReport[];
    perfPatterns: WinningPattern[];
    savedPatterns: WinningPattern[];
    perfVariants: PatternVariant[];
    perfImports: ImportBatch[];
    perfSavedViews: SavedView[];
    perfFilters: PerfFilters;
    perfActivity: PerfActivity[];
    perfReviewStarted: string[]; // recommendation ids marked review-started

    acceptPerfRec: (id: string) => void;
    dismissPerfRec: (id: string, reason: string) => void;
    undismissPerfRec: (id: string) => void;
    snoozePerfRec: (id: string, untilISO: string) => void;
    savePattern: (p: WinningPattern) => void;
    addVariants: (v: PatternVariant[]) => void;
    addPerfImport: (b: ImportBatch) => void;
    addPerfReport: (r: PerfReport) => void;
    deletePerfReport: (id: string) => void;
    setPerfFilters: (patch: Partial<PerfFilters>) => void;
    savePerfView: (v: SavedView) => void;
    deletePerfView: (id: string) => void;
    addPerfActivity: (e: Omit<PerfActivity, "id" | "at">) => void;
    markPerfReviewStarted: (id: string) => void;
    unacceptPerfRec: (id: string) => void;
    unsnoozePerfRec: (id: string) => void;

    reset: () => void;
};
