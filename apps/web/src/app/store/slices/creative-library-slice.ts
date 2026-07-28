import type {
    CreativeBoard,
    CreativeReference,
    CreativeAnalysisStatus,
} from "@/features/creative-library/types/creative";
import type { AppState } from "../store-types";
import type { StoreGet, StoreSet } from "../slice-types";

export function createCreativeLibrarySlice(set: StoreSet, get: StoreGet): Partial<AppState> {
    return {
        createBoard: (name) => {
            const board: CreativeBoard = { id: `b-${Date.now()}`, name, icon: "folder" };
            set((s) => ({ boards: [...s.boards, board] }));
            return board;
        },
        renameBoard: (id, name) =>
            set((s) => ({
                boards: s.boards.map((b) => (b.id === id && !b.system ? { ...b, name } : b)),
            })),
        duplicateBoard: (id) =>
            set((s) => {
                const orig = s.boards.find((b) => b.id === id);
                if (!orig) return {};
                return {
                    boards: [
                        ...s.boards,
                        {
                            ...orig,
                            id: `b-${Date.now()}`,
                            name: `${orig.name} copy`,
                            system: false,
                        },
                    ],
                };
            }),
        deleteBoard: (id) => {
            const s = get();
            const b = s.boards.find((x) => x.id === id);
            if (!b || b.system) return;
            const inUse = s.creatives.some((c) => c.boardIds.includes(id));
            if (inUse) return;
            set({ boards: s.boards.filter((x) => x.id !== id) });
        },

        addCreative: (c) => set((s) => ({ creatives: [c, ...s.creatives] })),
        updateCreative: (id, patch) =>
            set((s) => ({
                creatives: s.creatives.map((c) => (c.id === id ? { ...c, ...patch } : c)),
            })),
        moveCreativeToBoard: (creativeId, boardId) =>
            set((s) => ({
                creatives: s.creatives.map((c) =>
                    c.id === creativeId
                        ? { ...c, boardIds: Array.from(new Set([...c.boardIds, boardId])) }
                        : c,
                ),
            })),
        archiveCreative: (id) =>
            set((s) => ({
                creatives: s.creatives.map((c) => (c.id === id ? { ...c, archived: true } : c)),
            })),
        duplicateCreative: (id) =>
            set((s) => {
                const orig = s.creatives.find((c) => c.id === id);
                if (!orig) return {};
                const copy: CreativeReference = {
                    ...orig,
                    id: `cr-${Date.now()}`,
                    title: `${orig.title} (copy)`,
                    savedAt: new Date().toISOString(),
                    analysisStatus: "unanalyzed" as CreativeAnalysisStatus,
                    dnaScore: undefined,
                    analyzedAt: undefined,
                    usedInCampaignId: undefined,
                };
                return { creatives: [copy, ...s.creatives] };
            }),

        saveAnalysis: (a) =>
            set((s) => {
                const { [a.creativeId]: _drop, ...rest } = s.analysisJobs;
                void _drop;
                return {
                    analyses: { ...s.analyses, [a.creativeId]: a },
                    analysisJobs: rest,
                    creatives: s.creatives.map((c) =>
                        c.id === a.creativeId
                            ? {
                                  ...c,
                                  analysisStatus: "analyzed",
                                  dnaScore: a.dnaScore,
                                  analyzedAt: new Date().toISOString(),
                              }
                            : c,
                    ),
                };
            }),

        startAnalysisJob: (creativeId, total) =>
            set((s) => ({
                analysisJobs: {
                    ...s.analysisJobs,
                    [creativeId]: { step: 0, total, startedAt: Date.now() },
                },
                creatives: s.creatives.map((c) =>
                    c.id === creativeId ? { ...c, analysisStatus: "processing" } : c,
                ),
            })),
        advanceAnalysisJob: (creativeId) =>
            set((s) => {
                const j = s.analysisJobs[creativeId];
                if (!j) return {};
                return {
                    analysisJobs: {
                        ...s.analysisJobs,
                        [creativeId]: { ...j, step: Math.min(j.step + 1, j.total) },
                    },
                };
            }),
        failAnalysisJob: (creativeId) =>
            set((s) => {
                const { [creativeId]: _drop, ...rest } = s.analysisJobs;
                void _drop;
                return {
                    analysisJobs: rest,
                    creatives: s.creatives.map((c) =>
                        c.id === creativeId ? { ...c, analysisStatus: "failed" } : c,
                    ),
                };
            }),
        clearAnalysisJob: (creativeId) =>
            set((s) => {
                const { [creativeId]: _drop, ...rest } = s.analysisJobs;
                void _drop;
                return { analysisJobs: rest };
            }),

        addAdaptationNote: (creativeId, note) =>
            set((s) => ({
                adaptationNotes: {
                    ...s.adaptationNotes,
                    [creativeId]: [...(s.adaptationNotes[creativeId] ?? []), note],
                },
            })),

        setLastAdaptation: (h) => set({ lastAdaptation: h }),
    };
}
