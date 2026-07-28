import type { AppState } from "../store-types";
import type { StoreSet } from "../slice-types";

export function createDashboardSlice(set: StoreSet): Partial<AppState> {
    return {
        dismissRecommendation: (id) =>
            set((s) => ({
                dismissedRecommendations: Array.from(new Set([...s.dismissedRecommendations, id])),
            })),
        acceptRecommendation: (id) =>
            set((s) => ({
                acceptedRecommendations: Array.from(new Set([...s.acceptedRecommendations, id])),
            })),
        addDemoCampaign: (c) => set((s) => ({ demoCampaigns: [c, ...s.demoCampaigns] })),
        addDemoImport: (i) => set((s) => ({ demoImports: [i, ...s.demoImports] })),
    };
}
