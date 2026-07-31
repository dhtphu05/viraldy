import type {
    FixGroupKey,
    IntendedUse,
    ScoreMode,
    ScoreProfileCode,
    TikTokFixAction,
    TikTokScoreRun,
} from "../types";

export type HistoryFilters = {
    search: string;
    status: string;
    mode: string;
    profile: string;
    product: string;
    intendedUse: string;
    decision: string;
    date: string;
};

const PROCESSING_STAGES = [
    ["uploading", "Uploading video"],
    ["queued", "Waiting for analysis"],
    ["extracting_media", "Extracting media"],
    ["building_evidence", "Building evidence"],
    ["scoring", "Evaluating structure"],
    ["compiling_fixes", "Compiling fix plan"],
    ["completed", "Analysis ready"],
] as const;

const TERMINAL_STATUSES = new Set([
    "completed",
    "partial_evidence",
    "failed",
    "cancelled",
    "succeeded",
]);

const GROUP_META: Array<{
    key: FixGroupKey;
    title: string;
    description: string;
}> = [
    {
        key: "edit",
        title: "Fix with current footage",
        description: "Start here—the existing video contains what this repair needs.",
    },
    {
        key: "reshoot",
        title: "Needs creator reshoot",
        description: "The required physical scene or proof is not present in this draft.",
    },
    {
        key: "seller",
        title: "Needs seller confirmation",
        description:
            "Confirm product, offer, disclosure, shipping, compatibility, or rights truth.",
    },
    {
        key: "better_media",
        title: "Request better media",
        description: "Evidence quality is too weak for a responsible creative verdict.",
    },
];

export function isTerminalScoreStatus(status: string | null | undefined): boolean {
    return status ? TERMINAL_STATUSES.has(status) : false;
}

export function buildProcessingSteps(stage: string | null | undefined) {
    const normalized = stage === "running" || stage === "processing" ? "extracting_media" : stage;
    const currentIndex = Math.max(
        0,
        PROCESSING_STAGES.findIndex(([key]) => key === normalized),
    );
    const terminal = isTerminalScoreStatus(normalized);
    return PROCESSING_STAGES.map(([key, label], index) => ({
        key,
        label,
        status: (terminal || index < currentIndex
            ? "done"
            : index === currentIndex
              ? "active"
              : "pending") as "done" | "active" | "pending",
    }));
}

export function groupFixActions(actions: TikTokFixAction[]) {
    return GROUP_META.map((group) => ({
        ...group,
        actions: actions
            .filter((action) => action.group === group.key)
            .sort((left, right) => priorityWeight(left.priority) - priorityWeight(right.priority)),
    }));
}

export function filterScoreRuns(
    runs: TikTokScoreRun[],
    filters: HistoryFilters,
    now = new Date(),
): TikTokScoreRun[] {
    const query = filters.search.trim().toLowerCase();
    const earliest = dateFloor(filters.date, now);
    return runs.filter((run) => {
        if (
            query &&
            !`${run.assetName} ${run.productName ?? ""} ${run.profile.code}`
                .toLowerCase()
                .includes(query)
        ) {
            return false;
        }
        if (!matches(filters.status, run.status)) return false;
        if (!matches(filters.mode, run.scoreMode)) return false;
        if (!matches(filters.profile, run.profile.code)) return false;
        if (
            filters.product !== "all" &&
            filters.product !== run.productId &&
            filters.product !== (run.productName ?? "No product")
        ) {
            return false;
        }
        if (!matches(filters.intendedUse, run.intendedUse)) return false;
        if (!matches(filters.decision, run.decision)) return false;
        if (earliest && (!run.updatedAt || new Date(run.updatedAt) < earliest)) return false;
        return true;
    });
}

export function buildHandoffMessage(
    actions: TikTokFixAction[],
    target: "creator" | "editor",
): string {
    const strengths = [...new Set(actions.flatMap((action) => action.strengthsToPreserve))];
    const lines = [`${target === "creator" ? "Creator" : "Editor"} handoff`, ""];
    if (strengths.length) {
        lines.push("Keep these strengths:", ...strengths.map((item) => `- ${item}`), "");
    }
    lines.push("Required changes:");
    for (const action of actions) {
        lines.push(`- ${action.title}`);
        for (const instruction of action.instructions) lines.push(`  ${instruction}`);
        if (action.completionCriteria.length) {
            lines.push(`  Done when: ${action.completionCriteria.join("; ")}`);
        }
    }
    lines.push("", "Please send the revised file back for another structural review.");
    return lines.join("\n");
}

export function safeSeekSeconds(timestampMs: number, durationMs: number | null): number {
    const safeMs = Math.max(
        0,
        durationMs === null ? timestampMs : Math.min(timestampMs, durationMs),
    );
    return safeMs / 1_000;
}

export function validateScoreDraft(input: {
    fileSelected: boolean;
    mode: ScoreMode;
    productId: string | null;
    intendedUse: IntendedUse | "";
    profile: ScoreProfileCode | "";
}): Partial<Record<"file" | "productId" | "intendedUse" | "profile", string>> {
    const errors: Partial<Record<"file" | "productId" | "intendedUse" | "profile", string>> = {};
    if (!input.fileSelected) errors.file = "Choose a video to score.";
    if (input.mode === "product_aware" && !input.productId) {
        errors.productId = "Choose a product for Product-Aware Score.";
    }
    if (!input.intendedUse) errors.intendedUse = "Choose the intended use.";
    if (!input.profile) errors.profile = "Choose a content profile.";
    return errors;
}

export function validateVideoFile(
    file: Pick<File, "name" | "type" | "size">,
    durationSeconds: number | null,
): string | null {
    const allowedTypes = new Set(["video/mp4", "video/quicktime"]);
    if (!allowedTypes.has(file.type)) return "Choose an MP4 or QuickTime video.";
    if (file.size <= 0) return "The selected video is empty.";
    if (file.size > 250 * 1024 * 1024) return "Choose a video no larger than 250 MB.";
    if (durationSeconds !== null && durationSeconds > 180) {
        return "Choose a video that is 3 minutes or shorter.";
    }
    return null;
}

function matches(filter: string, value: string): boolean {
    return filter === "all" || filter === value;
}

function dateFloor(value: string, now: Date): Date | null {
    const days = value === "7d" ? 7 : value === "30d" ? 30 : value === "90d" ? 90 : null;
    if (days === null) return null;
    return new Date(now.getTime() - days * 24 * 60 * 60 * 1_000);
}

function priorityWeight(priority: TikTokFixAction["priority"]): number {
    return priority === "P0" ? 0 : priority === "P1" ? 1 : 2;
}
