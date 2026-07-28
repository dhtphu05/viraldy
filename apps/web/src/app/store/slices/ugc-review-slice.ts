import {
    analyzeUgcAsset,
    deriveDecision,
    sparkBlockers,
} from "@/features/ugc-review/lib/mockUgcAnalysis";
import type { UgcAsset } from "@/features/ugc-review/types/ugc";
import type { AppState } from "../store-types";
import type { StoreGet, StoreSet } from "../slice-types";

export function createUgcReviewSlice(set: StoreSet, get: StoreGet): Partial<AppState> {
    return {
        uploadUgc: (input) => {
            const id = `u-${Date.now()}`;
            const now = new Date().toISOString();
            const asset: UgcAsset = {
                reviewState: "new",
                decision: "awaiting-analysis",
                rightsStatus: "not-checked",
                ...input,
                id,
                submittedAt: now,
            } as UgcAsset;
            set((s) => ({
                ugcAssets: [asset, ...s.ugcAssets],
                ugcRights: {
                    ...s.ugcRights,
                    [id]: s.ugcRights[id] ?? {
                        organic: false,
                        sparkAllowed: false,
                        metaAllowed: false,
                        websiteAllowed: false,
                        rawFootage: false,
                        editingAllowed: false,
                        creatorConfirmed: false,
                    },
                },
                ugcActivity: [
                    {
                        id: `ua-${Date.now()}`,
                        assetId: id,
                        kind: "created" as const,
                        detail: `Draft uploaded: ${asset.title}`,
                        at: now,
                    },
                    ...s.ugcActivity,
                ].slice(0, 500),
            }));
            return id;
        },

        startUgcAnalysis: (assetId, totalSteps) =>
            set((s) => ({
                ugcJobs: {
                    ...s.ugcJobs,
                    [assetId]: { step: 0, total: totalSteps, startedAt: Date.now() },
                },
                ugcAssets: s.ugcAssets.map((a) =>
                    a.id === assetId ? { ...a, decision: "processing" } : a,
                ),
            })),

        advanceUgcJob: (assetId) =>
            set((s) => {
                const j = s.ugcJobs[assetId];
                if (!j) return {};
                return {
                    ugcJobs: {
                        ...s.ugcJobs,
                        [assetId]: { ...j, step: Math.min(j.step + 1, j.total) },
                    },
                };
            }),

        completeUgcAnalysis: (assetId) =>
            set((s) => {
                const asset = s.ugcAssets.find((a) => a.id === assetId);
                if (!asset) return {};
                const { analysis, issues } = analyzeUgcAsset(asset);
                const rights = s.ugcRights[assetId] ?? {
                    organic: false,
                    sparkAllowed: false,
                    metaAllowed: false,
                    websiteAllowed: false,
                    rawFootage: false,
                    editingAllowed: false,
                    creatorConfirmed: false,
                };
                const decision = deriveDecision(analysis, rights);
                const { [assetId]: _drop, ...restJobs } = s.ugcJobs;
                void _drop;
                return {
                    ugcAnalyses: { ...s.ugcAnalyses, [assetId]: analysis },
                    ugcIssues: { ...s.ugcIssues, [assetId]: issues },
                    ugcJobs: restJobs,
                    ugcAssets: s.ugcAssets.map((a) =>
                        a.id === assetId
                            ? {
                                  ...a,
                                  decision,
                                  reviewState:
                                      a.reviewState === "new" ? "in-review" : a.reviewState,
                              }
                            : a,
                    ),
                    ugcActivity: [
                        {
                            id: `ua-${Date.now()}`,
                            assetId,
                            kind: "analyzed" as const,
                            detail: `Analysis complete — score ${analysis.score}.`,
                            at: new Date().toISOString(),
                        },
                        ...s.ugcActivity,
                    ].slice(0, 500),
                };
            }),

        failUgcAnalysis: (assetId, reason) =>
            set((s) => {
                const { [assetId]: _drop, ...restJobs } = s.ugcJobs;
                void _drop;
                return {
                    ugcJobs: restJobs,
                    ugcAssets: s.ugcAssets.map((a) =>
                        a.id === assetId ? { ...a, decision: "failed" } : a,
                    ),
                    ugcAnalyses: {
                        ...s.ugcAnalyses,
                        [assetId]: {
                            ...(s.ugcAnalyses[assetId] ?? {
                                assetId,
                                createdAt: new Date().toISOString(),
                                score: 0,
                                confidence: "Low" as const,
                                summary: "Analysis could not complete.",
                                reason: reason ?? "The analyzer could not process this asset.",
                                nextAction:
                                    "Retry, replace the file, or continue with a demo asset.",
                                dimensions: [],
                                packAlignment: [],
                                markers: [],
                                transcript: [],
                                scenes: [],
                                onScreenText: [],
                            }),
                            failed: true,
                            failureReason: reason ?? "Analyzer error",
                        },
                    },
                };
            }),

        retryUgcAnalysis: (assetId) => {
            get().startUgcAnalysis(assetId, 10);
        },

        setUgcDecision: (assetId, decision) =>
            set((s) => ({
                ugcAssets: s.ugcAssets.map((a) => (a.id === assetId ? { ...a, decision } : a)),
            })),

        setUgcReviewState: (assetId, reviewState) =>
            set((s) => ({
                ugcAssets: s.ugcAssets.map((a) => (a.id === assetId ? { ...a, reviewState } : a)),
            })),

        toggleIssueInRevision: (assetId, issueId) =>
            set((s) => ({
                ugcIssues: {
                    ...s.ugcIssues,
                    [assetId]: (s.ugcIssues[assetId] ?? []).map((i) =>
                        i.id === issueId ? { ...i, addedToRevision: !i.addedToRevision } : i,
                    ),
                },
            })),

        reviewIssue: (assetId, issueId) =>
            set((s) => ({
                ugcIssues: {
                    ...s.ugcIssues,
                    [assetId]: (s.ugcIssues[assetId] ?? []).map((i) =>
                        i.id === issueId ? { ...i, reviewed: true } : i,
                    ),
                },
            })),

        dismissIssue: (assetId, issueId, dismissed) =>
            set((s) => ({
                ugcIssues: {
                    ...s.ugcIssues,
                    [assetId]: (s.ugcIssues[assetId] ?? []).map((i) =>
                        i.id === issueId ? { ...i, dismissed } : i,
                    ),
                },
            })),

        setRevisionMessage: (assetId, message) =>
            set((s) => ({
                ugcAssets: s.ugcAssets.map((a) =>
                    a.id === assetId ? { ...a, revisionMessage: message } : a,
                ),
            })),

        markRevisionRequested: (assetId) => {
            const now = new Date().toISOString();
            set((s) => ({
                ugcAssets: s.ugcAssets.map((a) =>
                    a.id === assetId
                        ? { ...a, reviewState: "revision-requested", reviewedAt: now }
                        : a,
                ),
                ugcActivity: [
                    {
                        id: `ua-${Date.now()}`,
                        assetId,
                        kind: "revision-requested" as const,
                        detail: "Revision marked as requested.",
                        at: now,
                    },
                    ...s.ugcActivity,
                ].slice(0, 500),
            }));
        },

        approveUgcOrganic: (assetId, note) => {
            const now = new Date().toISOString();
            set((s) => ({
                ugcAssets: s.ugcAssets.map((a) =>
                    a.id === assetId
                        ? {
                              ...a,
                              decision: "organic-ready",
                              reviewState: "approved",
                              reviewedAt: now,
                              note: note ?? a.note,
                          }
                        : a,
                ),
                ugcActivity: [
                    {
                        id: `ua-${Date.now()}`,
                        assetId,
                        kind: "approved-organic" as const,
                        detail: "Approved for organic publishing.",
                        at: now,
                    },
                    ...s.ugcActivity,
                ].slice(0, 500),
            }));
        },

        markUgcSparkReady: (assetId) => {
            const s = get();
            const rights = s.ugcRights[assetId];
            if (!rights) return { ok: false, blockers: ["Rights not filled in"] };
            const blockers = sparkBlockers(rights);
            if (blockers.length > 0) return { ok: false, blockers };
            const now = new Date().toISOString();
            set((state) => ({
                ugcAssets: state.ugcAssets.map((a) =>
                    a.id === assetId
                        ? {
                              ...a,
                              decision: "spark-ready",
                              reviewState: "approved",
                              rightsStatus: "complete",
                              reviewedAt: now,
                          }
                        : a,
                ),
                ugcActivity: [
                    {
                        id: `ua-${Date.now()}`,
                        assetId,
                        kind: "spark-ready" as const,
                        detail: "Marked Spark-ready.",
                        at: now,
                    },
                    ...state.ugcActivity,
                ].slice(0, 500),
            }));
            return { ok: true };
        },

        rejectUgc: (assetId) => {
            const now = new Date().toISOString();
            set((s) => ({
                ugcAssets: s.ugcAssets.map((a) =>
                    a.id === assetId
                        ? { ...a, decision: "reject", reviewState: "in-review", reviewedAt: now }
                        : a,
                ),
                ugcActivity: [
                    {
                        id: `ua-${Date.now()}`,
                        assetId,
                        kind: "rejected" as const,
                        detail: "Reshoot requested.",
                        at: now,
                    },
                    ...s.ugcActivity,
                ].slice(0, 500),
            }));
        },

        updateUgcRights: (assetId, patch) =>
            set((s) => {
                const prev = s.ugcRights[assetId] ?? {
                    organic: false,
                    sparkAllowed: false,
                    metaAllowed: false,
                    websiteAllowed: false,
                    rawFootage: false,
                    editingAllowed: false,
                    creatorConfirmed: false,
                };
                const next = { ...prev, ...patch };
                const blockers = sparkBlockers(next);
                let rightsStatus: UgcAsset["rightsStatus"] = "not-checked";
                if (next.creatorConfirmed) {
                    if (blockers.length === 0) rightsStatus = "complete";
                    else if (!next.sparkAllowed && next.organic) rightsStatus = "organic-only";
                    else rightsStatus = "spark-required";
                } else if (Object.values(next).some((v) => v)) rightsStatus = "missing";
                return {
                    ugcRights: { ...s.ugcRights, [assetId]: next },
                    ugcAssets: s.ugcAssets.map((a) =>
                        a.id === assetId ? { ...a, rightsStatus } : a,
                    ),
                    ugcActivity: [
                        {
                            id: `ua-${Date.now()}`,
                            assetId,
                            kind: "rights-updated" as const,
                            detail: "Rights fields updated.",
                            at: new Date().toISOString(),
                        },
                        ...s.ugcActivity,
                    ].slice(0, 500),
                };
            }),

        archiveUgc: (assetId) =>
            set((s) => ({
                ugcAssets: s.ugcAssets.map((a) =>
                    a.id === assetId ? { ...a, archived: true, reviewState: "archived" } : a,
                ),
            })),

        deleteLocalUgc: (assetId) =>
            set((s) => ({
                ugcAssets: s.ugcAssets.filter((a) => a.id !== assetId || !a.isLocalUpload),
            })),

        addUgcActivity: (event) =>
            set((s) => ({
                ugcActivity: [
                    {
                        id: `ua-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
                        at: new Date().toISOString(),
                        ...event,
                    },
                    ...s.ugcActivity,
                ].slice(0, 500),
            })),
    };
}
