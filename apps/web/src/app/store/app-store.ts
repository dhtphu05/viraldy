import { create } from "zustand";
import { persist } from "zustand/middleware";
import {
    campaigns as seedCampaigns,
    type SeedCampaign,
} from "@/features/campaigns/mocks/campaigns";
import { initialAppState } from "./initial-state";
import { createCampaignsSlice } from "./slices/campaigns-slice";
import { createCreativeLibrarySlice } from "./slices/creative-library-slice";
import { createDashboardSlice } from "./slices/dashboard-slice";
import { createPerformanceSlice } from "./slices/performance-slice";
import { createShellSlice } from "./slices/shell-slice";
import { createUgcReviewSlice } from "./slices/ugc-review-slice";
import type { AppState } from "./store-types";
import { restoreInterruptedAnalysisStates } from "@/features/creative-library/lib/analysis-job-feedback";

function mergeSeededList<T extends { id: string }>(seeded: T[], persisted?: T[]) {
    if (!persisted) return seeded;
    const ids = new Set(persisted.map((item) => item.id));
    return [...persisted, ...seeded.filter((item) => !ids.has(item.id))];
}

function mergePersistedState(persisted: unknown, current: AppState): AppState {
    const state = (persisted ?? {}) as Partial<AppState>;
    const analysisJobs = state.analysisJobs ?? current.analysisJobs;
    const creatives = restoreInterruptedAnalysisStates(
        mergeSeededList(current.creatives, state.creatives),
        analysisJobs,
    );
    return {
        ...current,
        ...state,
        analysisJobs,
        boards: mergeSeededList(current.boards, state.boards),
        creatives,
        analyses: { ...current.analyses, ...(state.analyses ?? {}) },
        packs: { ...current.packs, ...(state.packs ?? {}) },
        ugcAssets: mergeSeededList(current.ugcAssets, state.ugcAssets),
        ugcAnalyses: { ...current.ugcAnalyses, ...(state.ugcAnalyses ?? {}) },
        ugcIssues: { ...current.ugcIssues, ...(state.ugcIssues ?? {}) },
        ugcRights: { ...current.ugcRights, ...(state.ugcRights ?? {}) },
        perfRecommendations: mergeSeededList(
            current.perfRecommendations,
            state.perfRecommendations,
        ),
    };
}

export const useAppStore = create<AppState>()(
    persist(
        (set, get) =>
            ({
                ...initialAppState,
                ...createShellSlice(set),
                ...createDashboardSlice(set),
                ...createCreativeLibrarySlice(set, get),
                ...createCampaignsSlice(set, get),
                ...createUgcReviewSlice(set, get),
                ...createPerformanceSlice(set),
                reset: () => set({ ...initialAppState }),
            }) as AppState,
        {
            name: "viraldy-app",
            storage:
                typeof window === "undefined"
                    ? undefined
                    : {
                          getItem: (name) => {
                              const v = window.localStorage.getItem(name);
                              return v ? JSON.parse(v) : null;
                          },
                          setItem: (name, value) =>
                              window.localStorage.setItem(name, JSON.stringify(value)),
                          removeItem: (name) => window.localStorage.removeItem(name),
                      },
            merge: mergePersistedState,
        },
    ),
);

export function useAllCampaigns(): SeedCampaign[] {
    const local = useAppStore((s) => s.localCampaignSummaries);
    const packs = useAppStore((s) => s.packs);
    // Sync seed summaries with any pack status overrides (e.g., archive).
    const seeds: SeedCampaign[] = seedCampaigns.map((c) => {
        if (!c.packId) return c;
        const p = packs[c.packId];
        if (!p) return c;
        return {
            ...c,
            name: p.name,
            packStatus: p.status,
            objective: p.objective,
            market: p.market,
            platform: p.platform,
            referenceCount: p.referenceCreativeIds.length,
            hookCount: p.selectedHookIds.length,
            deliverables: p.deliverables.numberOfVideos,
        };
    });
    return [...local, ...seeds];
}
