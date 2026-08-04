export const queryKeys = {
    system: {
        aiReadiness: ["system", "ai-readiness"] as const,
    },
    workspaces: {
        list: ["workspaces"] as const,
    },
    products: {
        list: (workspaceId: string | undefined) => ["products", workspaceId] as const,
    },
    assets: {
        list: (workspaceId: string | undefined) => ["assets", workspaceId] as const,
    },
    referenceBoards: {
        list: (workspaceId: string | undefined) => ["reference-boards", workspaceId] as const,
    },
    references: {
        list: (workspaceId: string | undefined) => ["references", workspaceId] as const,
    },
    jobs: {
        detail: (workspaceId: string | undefined, jobId: string | null) =>
            ["jobs", workspaceId, jobId] as const,
    },
    tiktokScores: {
        list: (workspaceId: string | undefined) => ["tiktok-scores", workspaceId, "list"] as const,
        detail: (workspaceId: string | undefined, scoreRunId: string | null) =>
            ["tiktok-scores", workspaceId, scoreRunId] as const,
        fixes: (workspaceId: string | undefined, scoreRunId: string | null) =>
            ["tiktok-scores", workspaceId, scoreRunId, "fixes"] as const,
        comparison: (
            workspaceId: string | undefined,
            scoreRunId: string | null,
            comparisonId: string | null,
        ) => ["tiktok-scores", workspaceId, scoreRunId, "comparisons", comparisonId] as const,
        profiles: (workspaceId: string | undefined) =>
            ["tiktok-score-profiles", workspaceId] as const,
        playback: (
            workspaceId: string | undefined,
            assetId: string | null,
            assetVersionId: string | null,
        ) => ["asset-playback", workspaceId, assetId, assetVersionId] as const,
    },
    ugcReviews: {
        status: (workspaceId: string | undefined, reviewId: string | null) =>
            ["ugc-reviews", workspaceId, reviewId, "status"] as const,
        detail: (workspaceId: string | undefined, reviewId: string | null) =>
            ["ugc-reviews", workspaceId, reviewId] as const,
        comparison: (workspaceId: string | undefined, reviewId: string | null) =>
            ["ugc-reviews", workspaceId, reviewId, "comparisons", "latest"] as const,
        playback: (
            workspaceId: string | undefined,
            assetId: string | null,
            assetVersionId: string | null,
        ) => ["ugc-review-playback", workspaceId, assetId, assetVersionId] as const,
    },
    creativeDna: {
        detail: (workspaceId: string | undefined, dnaVersionId: string | null) =>
            ["creative-dna", workspaceId, dnaVersionId] as const,
    },
    patternKits: {
        detail: (workspaceId: string | undefined, patternKitId: string | null) =>
            ["pattern-kits", workspaceId, patternKitId] as const,
    },
    viralKits: {
        detail: (workspaceId: string | undefined, viralKitId: string | null) =>
            ["viral-kits", workspaceId, viralKitId] as const,
    },
    adaptations: {
        detail: (workspaceId: string | undefined, adaptationRunId: string | null) =>
            ["adaptations", workspaceId, adaptationRunId] as const,
    },
    campaignPacks: {
        list: (workspaceId: string | undefined) => ["campaign-packs", workspaceId] as const,
        detail: (workspaceId: string | undefined, packId: string | null) =>
            ["campaign-packs", workspaceId, packId] as const,
        versions: (workspaceId: string | undefined, packId: string | null) =>
            ["campaign-packs", workspaceId, packId, "versions"] as const,
    },
    preflightRuns: {
        detail: (workspaceId: string | undefined, preflightRunId: string | null) =>
            ["preflight-runs", workspaceId, preflightRunId] as const,
    },
};
