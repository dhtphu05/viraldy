import { seedPacks } from "@/features/campaigns/mocks/campaignPacks";
import { seedAnalyses } from "@/features/creative-library/mocks/creativeAnalyses";
import { seedBoards } from "@/features/creative-library/mocks/creativeBoards";
import { seedCreatives } from "@/features/creative-library/mocks/creatives";
import {
    seedRecommendations,
    seedReports,
    seedPatterns,
} from "@/features/performance/mocks/performanceSeed";
import {
    seedUgcActivity,
    seedUgcAnalyses,
    seedUgcAssets,
    seedUgcIssues,
    seedUgcRights,
} from "@/features/ugc-review/mocks/ugcSeed";
import { workspaces } from "@/shared/mocks/workspaces";
import type { Campaign } from "@/shared/types";
import type { SeedCampaign } from "@/features/campaigns/mocks/campaigns";
import type { ActivityEvent, CampaignDraft } from "@/features/campaigns/types/campaign";
import type {
    CreativeAnalysis,
    CreativeReference,
} from "@/features/creative-library/types/creative";
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
import type {
    UgcActivityEvent,
    UgcAnalysis,
    UgcAsset,
    UgcIssue,
    UgcRights,
} from "@/features/ugc-review/types/ugc";
import type { AdaptationHandoff, DemoImport } from "./store-types";

export const initialAppState = {
    sidebarCollapsed: false,
    currentWorkspaceId: workspaces[0].id,
    dismissedRecommendations: [] as string[],
    acceptedRecommendations: [] as string[],
    demoCampaigns: [] as Campaign[],
    demoImports: [] as DemoImport[],
    boards: seedBoards,
    creatives: seedCreatives,
    analyses: seedAnalyses,
    analysisJobs: {} as Record<string, { step: number; total: number; startedAt: number }>,
    adaptationNotes: {} as Record<string, string[]>,
    lastAdaptation: undefined as AdaptationHandoff | undefined,
    packs: seedPacks,
    localCampaignSummaries: [] as SeedCampaign[],
    campaignActivity: [] as ActivityEvent[],
    packAutosaveAt: {} as Record<string, string>,
    campaignDraft: {} as CampaignDraft,
    ugcAssets: seedUgcAssets as UgcAsset[],
    ugcAnalyses: seedUgcAnalyses as Record<string, UgcAnalysis>,
    ugcIssues: seedUgcIssues as Record<string, UgcIssue[]>,
    ugcRights: seedUgcRights as Record<string, UgcRights>,
    ugcActivity: seedUgcActivity,
    ugcJobs: {} as Record<string, { step: number; total: number; startedAt: number }>,
    perfRecommendations: seedRecommendations as PerfRecommendation[],
    perfAcceptedRecs: [] as string[],
    perfDismissedRecs: {} as Record<string, string>,
    perfSnoozedRecs: {} as Record<string, string>,
    perfReports: seedReports as PerfReport[],
    perfPatterns: seedPatterns as WinningPattern[],
    savedPatterns: [] as WinningPattern[],
    perfVariants: [] as PatternVariant[],
    perfImports: [] as ImportBatch[],
    perfSavedViews: [] as SavedView[],
    perfFilters: { dateRange: "30d", decision: "All", source: "all" } as PerfFilters,
    perfActivity: [] as PerfActivity[],
    perfReviewStarted: [] as string[],
};
