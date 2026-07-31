import {
    evaluateCampaignCoherence,
    type CampaignCoherenceContext,
} from "@/features/campaigns/lib/campaignCoherence";
import { STEPS, completionPercent, stepIsComplete } from "@/features/campaigns/lib/campaignSteps";
import type { CampaignPack, StepId } from "@/features/campaigns/types/campaign";

export type CampaignLifecycle =
    | "draft"
    | "ready_for_review"
    | "creator_ready"
    | "sent"
    | "creator_production"
    | "ugc_received"
    | "live";

export type ReadinessIssue = {
    id: string;
    label: string;
    step: StepId;
    kind: "completion" | "coherence" | "claim" | "rights";
};

export type CampaignNextAction = {
    id:
        | "complete_section"
        | "resolve_blocker"
        | "review_warning"
        | "preview_brief"
        | "mark_ready"
        | "copy_brief"
        | "review_ugc"
        | "open_performance";
    label: string;
    step?: StepId;
};

export type CampaignReadiness = {
    lifecycle: CampaignLifecycle;
    completionPercent: number;
    contentComplete: boolean;
    qualityPassed: boolean;
    hardBlockers: ReadinessIssue[];
    warnings: ReadinessIssue[];
    nextAction: CampaignNextAction;
};

export function campaignLifecycleLabel(lifecycle: CampaignLifecycle): string {
    switch (lifecycle) {
        case "draft":
            return "Draft";
        case "ready_for_review":
            return "Ready to review";
        case "creator_ready":
            return "Creator-ready";
        case "sent":
            return "Sent";
        case "creator_production":
            return "Creator production";
        case "ugc_received":
            return "UGC received";
        case "live":
            return "Live";
    }
}

const REQUIRED_STEPS: StepId[] = [
    "product",
    "references",
    "adaptation",
    "angles",
    "hooks",
    "script",
    "storyboard",
    "cta",
    "deliverables",
];

export function selectCampaignReadiness(
    pack: CampaignPack,
    coherenceContext?: CampaignCoherenceContext,
): CampaignReadiness {
    const missingSteps = REQUIRED_STEPS.filter((step) => !stepIsComplete(pack, step));
    const completionBlockers: ReadinessIssue[] = missingSteps.map((step) => ({
        id: `missing-${step}`,
        label: `Complete ${STEPS.find((item) => item.id === step)?.label ?? step}.`,
        step,
        kind: "completion",
    }));
    const coherenceIssues = evaluateCampaignCoherence(pack, coherenceContext);
    const coherenceBlockers: ReadinessIssue[] = coherenceIssues
        .filter((issue) => issue.severity === "blocker")
        .map((issue) => ({
            id: issue.id,
            label: issue.message,
            step: issue.step,
            kind: issue.code === "claim_blocker" ? "claim" : "coherence",
        }));
    const warnings: ReadinessIssue[] = pack.cta.warnings
        .filter(
            (warning) => warning.risk !== "High" && !pack.reviewedWarningIds.includes(warning.id),
        )
        .map((warning) => ({
            id: warning.id,
            label: warning.reason,
            step: "cta",
            kind: "claim",
        }));
    const hardBlockers = [...completionBlockers, ...coherenceBlockers];
    const contentComplete = completionBlockers.length === 0;
    const qualityPassed = coherenceBlockers.length === 0;
    const eligibleForCreator = contentComplete && qualityPassed && hardBlockers.length === 0;
    const lifecycle = deriveLifecycle(pack, eligibleForCreator);

    return {
        lifecycle,
        completionPercent: completionPercent(pack),
        contentComplete,
        qualityPassed,
        hardBlockers,
        warnings,
        nextAction: deriveNextAction(lifecycle, hardBlockers, warnings),
    };
}

export function markCampaignReady(pack: CampaignPack): CampaignPack {
    const readiness = selectCampaignReadiness(pack);
    if (
        !readiness.contentComplete ||
        !readiness.qualityPassed ||
        readiness.hardBlockers.length > 0
    ) {
        return pack;
    }
    return {
        ...pack,
        status: "Ready for creator",
        updatedAt: new Date().toISOString(),
    };
}

function deriveLifecycle(pack: CampaignPack, eligibleForCreator: boolean): CampaignLifecycle {
    switch (pack.status) {
        case "Draft":
            return eligibleForCreator ? "ready_for_review" : "draft";
        case "Ready for creator":
            return eligibleForCreator ? "creator_ready" : "draft";
        case "Creator production":
            return eligibleForCreator ? "creator_production" : "draft";
        case "Awaiting UGC":
            return eligibleForCreator ? "creator_production" : "draft";
        case "Active":
            return eligibleForCreator ? "live" : "draft";
        case "Completed":
            return eligibleForCreator ? "live" : "draft";
        case "Archived":
            return "draft";
    }
}

function deriveNextAction(
    lifecycle: CampaignLifecycle,
    blockers: ReadinessIssue[],
    warnings: ReadinessIssue[],
): CampaignNextAction {
    const firstBlocker = blockers[0];
    if (firstBlocker) {
        return {
            id: firstBlocker.kind === "completion" ? "complete_section" : "resolve_blocker",
            label: firstBlocker.label,
            step: firstBlocker.step,
        };
    }
    if (warnings.length > 0) {
        return {
            id: "review_warning",
            label: `Review ${warnings.length} claim warning${warnings.length === 1 ? "" : "s"}.`,
            step: "cta",
        };
    }
    switch (lifecycle) {
        case "draft":
            return { id: "preview_brief", label: "Preview creator brief", step: "review" };
        case "ready_for_review":
            return { id: "mark_ready", label: "Mark ready for creator", step: "review" };
        case "creator_ready":
        case "sent":
            return { id: "copy_brief", label: "Copy creator brief", step: "review" };
        case "creator_production":
            return { id: "review_ugc", label: "Review creator draft" };
        case "ugc_received":
            return { id: "review_ugc", label: "Review received UGC" };
        case "live":
            return { id: "open_performance", label: "Review performance" };
    }
}
