import type { CampaignPack, StepId } from "@/features/campaigns/types/campaign";

export type StepState = "complete" | "current" | "not-started" | "needs-review" | "locked";

export type StepDef = { id: StepId; label: string; short: string };

export const STEPS: StepDef[] = [
    { id: "product", label: "Product & Goal", short: "Product" },
    { id: "references", label: "References", short: "Refs" },
    { id: "adaptation", label: "Adaptation", short: "Adapt" },
    { id: "angles", label: "Angles", short: "Angles" },
    { id: "hooks", label: "Hooks", short: "Hooks" },
    { id: "script", label: "Script", short: "Script" },
    { id: "storyboard", label: "Storyboard", short: "Scenes" },
    { id: "cta", label: "CTA & Claims", short: "CTA" },
    { id: "deliverables", label: "Deliverables & Rights", short: "Deliver" },
    { id: "review", label: "Review", short: "Review" },
];

export type CampaignPhaseId =
    "context" | "creative-direction" | "creator-execution" | "guardrails" | "review-send";

export type CampaignPhase = {
    id: CampaignPhaseId;
    label: string;
    short: string;
    steps: StepId[];
};

export const CAMPAIGN_PHASES: CampaignPhase[] = [
    {
        id: "context",
        label: "Context",
        short: "Context",
        steps: ["product", "references"],
    },
    {
        id: "creative-direction",
        label: "Creative Direction",
        short: "Direction",
        steps: ["adaptation", "angles", "hooks"],
    },
    {
        id: "creator-execution",
        label: "Creator Execution",
        short: "Execution",
        steps: ["script", "storyboard"],
    },
    {
        id: "guardrails",
        label: "Guardrails",
        short: "Guardrails",
        steps: ["cta", "deliverables"],
    },
    {
        id: "review-send",
        label: "Review & Send",
        short: "Review",
        steps: ["review"],
    },
];

export function phaseForStep(step: StepId): CampaignPhase {
    return CAMPAIGN_PHASES.find((phase) => phase.steps.includes(step)) ?? CAMPAIGN_PHASES[0];
}

export function phaseIsComplete(pack: CampaignPack, phase: CampaignPhase): boolean {
    return phase.steps.every((step) => stepIsComplete(pack, step));
}

export function firstStepForPhase(pack: CampaignPack, phase: CampaignPhase): StepId {
    return phase.steps.find((step) => !stepIsComplete(pack, step)) ?? phase.steps[0];
}

export function stepIsComplete(pack: CampaignPack, id: StepId): boolean {
    switch (id) {
        case "product":
            return !!(
                pack.name &&
                pack.productId &&
                pack.objective &&
                pack.market &&
                pack.platform
            );
        case "references":
            return pack.referenceCreativeIds.length > 0;
        case "adaptation":
            return !!pack.adaptation.adaptedHook && !!pack.adaptation.adaptedAngle;
        case "angles":
            return !!pack.primaryAngleId;
        case "hooks":
            return pack.selectedHookIds.length > 0;
        case "script":
            return pack.script.length >= 4 && pack.script.every((b) => b.text.trim().length > 0);
        case "storyboard":
            return pack.storyboard.length >= 3;
        case "cta":
            return !!pack.cta.primary;
        case "deliverables":
            return pack.deliverables.numberOfVideos > 0 && pack.deliverables.targetDurationSec > 0;
        case "review":
            return pack.status !== "Draft";
    }
}

export function completionPercent(pack: CampaignPack): number {
    const done = STEPS.filter((s) => stepIsComplete(pack, s.id)).length;
    return Math.round((done / STEPS.length) * 100);
}

export type ReadinessState = "Draft" | "Needs review" | "Creator-ready" | "Blocked";

export function readinessState(pack: CampaignPack): { state: ReadinessState; reasons: string[] } {
    const reasons: string[] = [];
    const blocking: StepId[] = [
        "product",
        "references",
        "adaptation",
        "angles",
        "hooks",
        "script",
        "cta",
    ];
    const missing = blocking.filter((s) => !stepIsComplete(pack, s));
    missing.forEach((m) => reasons.push(`Missing: ${STEPS.find((s) => s.id === m)?.label}`));
    const unreviewedWarnings = pack.cta.warnings.filter(
        (w) => !pack.reviewedWarningIds.includes(w.id) && w.risk !== "Low",
    );
    if (unreviewedWarnings.length > 0)
        reasons.push(`${unreviewedWarnings.length} unreviewed claim warning(s)`);

    if (missing.length > 0) return { state: "Blocked", reasons };
    if (unreviewedWarnings.length > 0) return { state: "Needs review", reasons };
    if (!stepIsComplete(pack, "deliverables"))
        return { state: "Needs review", reasons: ["Set deliverables"] };
    return { state: "Creator-ready", reasons: [] };
}
