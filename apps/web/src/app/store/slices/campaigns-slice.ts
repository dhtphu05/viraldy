import { campaigns as seedCampaigns } from "@/features/campaigns/mocks/campaigns";
import type { CampaignPack } from "@/features/campaigns/types/campaign";
import type { AppState } from "../store-types";
import type { StoreGet, StoreSet } from "../slice-types";

export function createCampaignsSlice(set: StoreSet, get: StoreGet): Partial<AppState> {
    return {
        createCampaignPack: ({ campaignId, packId, pack, summary }) =>
            set((s) => ({
                packs: { ...s.packs, [packId]: pack },
                localCampaignSummaries: [
                    { ...summary, id: campaignId, packId },
                    ...s.localCampaignSummaries,
                ],
                packAutosaveAt: { ...s.packAutosaveAt, [packId]: new Date().toISOString() },
                campaignActivity: [
                    {
                        id: `ev-${Date.now()}`,
                        campaignId,
                        kind: "created",
                        detail: `Campaign draft created: ${pack.name}`,
                        at: new Date().toISOString(),
                    },
                    ...s.campaignActivity,
                ],
            })),

        updateCampaignPack: (id, patch) =>
            set((s) => {
                const prev = s.packs[id];
                if (!prev) return {};
                const next: CampaignPack = {
                    ...prev,
                    ...patch,
                    updatedAt: new Date().toISOString(),
                };
                const summary = s.localCampaignSummaries.find((c) => c.packId === id);
                const seed = seedCampaigns.find((c) => c.packId === id);
                const nextSummaries = summary
                    ? s.localCampaignSummaries.map((c) =>
                          c.packId === id
                              ? {
                                    ...c,
                                    name: next.name,
                                    objective: next.objective,
                                    market: next.market,
                                    platform: next.platform,
                                    packStatus: next.status,
                                    referenceCount: next.referenceCreativeIds.length,
                                    hookCount: next.selectedHookIds.length,
                                    deliverables: next.deliverables.numberOfVideos,
                                    primaryAngle:
                                        next.angleOptions.find((a) => a.id === next.primaryAngleId)
                                            ?.name ?? c.primaryAngle,
                                    updatedAt: next.updatedAt,
                                }
                              : c,
                      )
                    : s.localCampaignSummaries;
                void seed;
                return {
                    packs: { ...s.packs, [id]: next },
                    localCampaignSummaries: nextSummaries,
                    packAutosaveAt: { ...s.packAutosaveAt, [id]: new Date().toISOString() },
                };
            }),

        setPackStatus: (id, status) => {
            const prev = get().packs[id];
            if (!prev) return;
            get().updateCampaignPack(id, { status });
            get().addActivity({
                campaignId:
                    get().localCampaignSummaries.find((c) => c.packId === id)?.id ??
                    seedCampaigns.find((c) => c.packId === id)?.id ??
                    id,
                kind: status === "Ready for creator" ? "marked-ready" : "note",
                detail: `Status changed to ${status}`,
            });
        },

        duplicateCampaign: (campaignId) => {
            const s = get();
            const summary =
                s.localCampaignSummaries.find((c) => c.id === campaignId) ??
                seedCampaigns.find((c) => c.id === campaignId);
            if (!summary?.packId) return undefined;
            const pack = s.packs[summary.packId];
            if (!pack) return undefined;
            const newPackId = `pack-${Date.now()}`;
            const newCampaignId = `c-${Date.now()}`;
            const now = new Date().toISOString();
            const copy: CampaignPack = {
                ...pack,
                id: newPackId,
                name: `${pack.name} (copy)`,
                status: "Draft",
                createdAt: now,
                updatedAt: now,
                savedAt: now,
            };
            set((state) => ({
                packs: { ...state.packs, [newPackId]: copy },
                localCampaignSummaries: [
                    {
                        ...summary,
                        id: newCampaignId,
                        packId: newPackId,
                        name: copy.name,
                        status: "Draft",
                        packStatus: "Draft",
                        updatedAt: now,
                    },
                    ...state.localCampaignSummaries,
                ],
                campaignActivity: [
                    {
                        id: `ev-${Date.now()}`,
                        campaignId: newCampaignId,
                        kind: "created",
                        detail: `Duplicated from ${pack.name}`,
                        at: now,
                    },
                    ...state.campaignActivity,
                ],
            }));
            return newCampaignId;
        },

        archiveCampaign: (campaignId) =>
            set((s) => {
                const local = s.localCampaignSummaries.find((c) => c.id === campaignId);
                const packId =
                    local?.packId ?? seedCampaigns.find((c) => c.id === campaignId)?.packId;
                const nextPacks = { ...s.packs };
                if (packId && nextPacks[packId]) {
                    nextPacks[packId] = {
                        ...nextPacks[packId],
                        status: "Archived",
                        archived: true,
                    };
                }
                return {
                    packs: nextPacks,
                    localCampaignSummaries: s.localCampaignSummaries.map((c) =>
                        c.id === campaignId ? { ...c, packStatus: "Archived" } : c,
                    ),
                };
            }),

        deleteLocalCampaign: (campaignId) =>
            set((s) => {
                const summary = s.localCampaignSummaries.find((c) => c.id === campaignId);
                const nextPacks = { ...s.packs };
                if (summary?.packId) delete nextPacks[summary.packId];
                return {
                    packs: nextPacks,
                    localCampaignSummaries: s.localCampaignSummaries.filter(
                        (c) => c.id !== campaignId,
                    ),
                };
            }),

        renameCampaign: (campaignId, name) =>
            set((s) => {
                const summary = s.localCampaignSummaries.find((c) => c.id === campaignId);
                const packId =
                    summary?.packId ?? seedCampaigns.find((c) => c.id === campaignId)?.packId;
                const nextPacks = { ...s.packs };
                if (packId && nextPacks[packId]) {
                    nextPacks[packId] = { ...nextPacks[packId], name };
                }
                return {
                    packs: nextPacks,
                    localCampaignSummaries: s.localCampaignSummaries.map((c) =>
                        c.id === campaignId ? { ...c, name } : c,
                    ),
                };
            }),

        reviewWarning: (packId, warningId) =>
            set((s) => {
                const p = s.packs[packId];
                if (!p) return {};
                return {
                    packs: {
                        ...s.packs,
                        [packId]: {
                            ...p,
                            reviewedWarningIds: Array.from(
                                new Set([...p.reviewedWarningIds, warningId]),
                            ),
                        },
                    },
                };
            }),

        addActivity: (event) =>
            set((s) => ({
                campaignActivity: [
                    {
                        id: `ev-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
                        at: new Date().toISOString(),
                        ...event,
                    },
                    ...s.campaignActivity,
                ].slice(0, 500),
            })),

        setDraft: (patch) => set((s) => ({ campaignDraft: { ...s.campaignDraft, ...patch } })),
        clearDraft: () => set({ campaignDraft: {} }),
    };
}
