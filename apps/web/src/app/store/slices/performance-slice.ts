import type { AppState } from "../store-types";
import type { StoreSet } from "../slice-types";

export function createPerformanceSlice(set: StoreSet): Partial<AppState> {
    return {
        acceptPerfRec: (id) =>
            set((s) => ({
                perfAcceptedRecs: Array.from(new Set([...s.perfAcceptedRecs, id])),
                perfActivity: [
                    {
                        id: `pa-${Date.now()}`,
                        at: new Date().toISOString(),
                        kind: "accepted" as const,
                        detail: `Accepted recommendation ${id}`,
                    },
                    ...s.perfActivity,
                ].slice(0, 500),
            })),
        dismissPerfRec: (id, reason) =>
            set((s) => ({
                perfDismissedRecs: { ...s.perfDismissedRecs, [id]: reason },
                perfActivity: [
                    {
                        id: `pa-${Date.now()}`,
                        at: new Date().toISOString(),
                        kind: "dismissed" as const,
                        detail: `Dismissed: ${reason}`,
                    },
                    ...s.perfActivity,
                ].slice(0, 500),
            })),
        undismissPerfRec: (id) =>
            set((s) => {
                const next = { ...s.perfDismissedRecs };
                delete next[id];
                return { perfDismissedRecs: next };
            }),
        snoozePerfRec: (id, untilISO) =>
            set((s) => ({
                perfSnoozedRecs: { ...s.perfSnoozedRecs, [id]: untilISO },
                perfActivity: [
                    {
                        id: `pa-${Date.now()}`,
                        at: new Date().toISOString(),
                        kind: "snoozed" as const,
                        detail: `Snoozed until ${untilISO.slice(0, 10)}`,
                    },
                    ...s.perfActivity,
                ].slice(0, 500),
            })),
        savePattern: (p) =>
            set((s) => ({
                savedPatterns: [{ ...p, id: `${p.id}-saved-${Date.now()}` }, ...s.savedPatterns],
                perfActivity: [
                    {
                        id: `pa-${Date.now()}`,
                        at: new Date().toISOString(),
                        kind: "pattern-saved" as const,
                        detail: `Saved pattern: ${p.angle}`,
                    },
                    ...s.perfActivity,
                ].slice(0, 500),
            })),
        addVariants: (v) =>
            set((s) => ({
                perfVariants: [...v, ...s.perfVariants],
                perfActivity: [
                    {
                        id: `pa-${Date.now()}`,
                        at: new Date().toISOString(),
                        kind: "variants-generated" as const,
                        detail: `Generated ${v.length} variants`,
                    },
                    ...s.perfActivity,
                ].slice(0, 500),
            })),
        addPerfImport: (b) =>
            set((s) => ({
                perfImports: [b, ...s.perfImports],
                perfActivity: [
                    {
                        id: `pa-${Date.now()}`,
                        at: new Date().toISOString(),
                        kind: "imported" as const,
                        detail: `Imported ${b.rowCount} rows from ${b.source}`,
                    },
                    ...s.perfActivity,
                ].slice(0, 500),
            })),
        addPerfReport: (r) => set((s) => ({ perfReports: [r, ...s.perfReports] })),
        deletePerfReport: (id) =>
            set((s) => ({ perfReports: s.perfReports.filter((r) => r.id !== id) })),
        setPerfFilters: (patch) => set((s) => ({ perfFilters: { ...s.perfFilters, ...patch } })),
        savePerfView: (v) => set((s) => ({ perfSavedViews: [v, ...s.perfSavedViews] })),
        deletePerfView: (id) =>
            set((s) => ({ perfSavedViews: s.perfSavedViews.filter((v) => v.id !== id) })),
        addPerfActivity: (e) =>
            set((s) => ({
                perfActivity: [
                    {
                        id: `pa-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
                        at: new Date().toISOString(),
                        ...e,
                    },
                    ...s.perfActivity,
                ].slice(0, 500),
            })),
        markPerfReviewStarted: (id) =>
            set((s) => ({
                perfReviewStarted: Array.from(new Set([...s.perfReviewStarted, id])),
                perfActivity: [
                    {
                        id: `pa-${Date.now()}`,
                        at: new Date().toISOString(),
                        kind: "review-started" as const,
                        detail: `Started review for ${id}`,
                    },
                    ...s.perfActivity,
                ].slice(0, 500),
            })),
    };
}
