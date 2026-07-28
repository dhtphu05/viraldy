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

export const useAppStore = create<AppState>()(
    persist(
        (set, get) => ({
            ...initialAppState,
            ...createShellSlice(set),
            ...createDashboardSlice(set),
            ...createCreativeLibrarySlice(set, get),
            ...createCampaignsSlice(set, get),
            ...createUgcReviewSlice(set, get),
            ...createPerformanceSlice(set),
            reset: () => set({ ...initialAppState }),
        }),
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
