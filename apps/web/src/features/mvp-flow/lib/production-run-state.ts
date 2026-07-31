import type { JobStatus } from "@/shared/api/jobs";

export type ProductionEntryType = "reference-first" | "product-first";
export type ProductionPhaseId = "context" | "decode" | "adapt" | "build" | "review";
export type ProductionPhaseStatus = "complete" | "active" | "locked" | "stale";
export type ProductionOutput =
    "creative-dna" | "pattern-kit" | "viral-kit" | "campaign-pack" | "preflight";

export type ProductionContext = {
    entryType?: ProductionEntryType;
    productId?: string;
    primaryReferenceId?: string;
    objective?: string;
    market?: string;
    buyerPersona?: string;
    buyerPain?: string;
    desiredOutcome?: string;
};

export type ProductionRunProgress = {
    context: ProductionContext;
    dnaId?: string;
    patternKitId?: string;
    viralKitId?: string;
    selectedConceptId?: string;
    conceptConfirmed?: boolean;
    packId?: string;
    preflightRunId?: string;
    staleOutputs?: ProductionOutput[];
};

export type ProductionPhase = {
    id: ProductionPhaseId;
    status: ProductionPhaseStatus;
    active: boolean;
    unlockReason?: string;
};

export type ProductionDependencySnapshot = {
    productId?: string;
    primaryReferenceId?: string;
    supportingReferenceIds?: string[];
    selectedConceptId?: string;
    packVersionId?: string;
    ugcAssetVersionId?: string;
};

const PHASE_IDS: ProductionPhaseId[] = ["context", "decode", "adapt", "build", "review"];

const OUTPUT_ORDER: ProductionOutput[] = [
    "creative-dna",
    "pattern-kit",
    "viral-kit",
    "campaign-pack",
    "preflight",
];

export function missingProductionContext(context: ProductionContext): string[] {
    const required: Array<[keyof ProductionContext, string]> = [
        ["entryType", "Choose how to start"],
        ["productId", "Select a product"],
        ["primaryReferenceId", "Select a primary reference"],
        ["objective", "Set the production objective"],
        ["market", "Set the target market"],
        ["buyerPersona", "Describe the buyer"],
        ["buyerPain", "Describe the buyer problem"],
        ["desiredOutcome", "Describe the desired outcome"],
    ];
    return required.filter(([key]) => !context[key]?.trim()).map(([, label]) => label);
}

export function productionContextReady(context: ProductionContext): boolean {
    return missingProductionContext(context).length === 0;
}

export function deriveProductionRunPhases(progress: ProductionRunProgress): ProductionPhase[] {
    const stale = new Set(progress.staleOutputs ?? []);
    const contextReady = productionContextReady(progress.context);
    const decodeReady =
        Boolean(progress.dnaId && progress.patternKitId) &&
        !stale.has("creative-dna") &&
        !stale.has("pattern-kit");
    const adaptReady =
        Boolean(progress.viralKitId && progress.selectedConceptId && progress.conceptConfirmed) &&
        !stale.has("viral-kit");
    const buildReady = Boolean(progress.packId) && !stale.has("campaign-pack");

    const activeId: ProductionPhaseId = !contextReady
        ? "context"
        : !decodeReady
          ? "decode"
          : !adaptReady
            ? "adapt"
            : !buildReady
              ? "build"
              : "review";

    const activeIndex = PHASE_IDS.indexOf(activeId);
    return PHASE_IDS.map((id, index) => {
        const phaseIsStale =
            (id === "decode" && (stale.has("creative-dna") || stale.has("pattern-kit"))) ||
            (id === "adapt" && stale.has("viral-kit")) ||
            (id === "build" && stale.has("campaign-pack")) ||
            (id === "review" && stale.has("preflight"));
        const active = id === activeId;
        const status: ProductionPhaseStatus = active
            ? phaseIsStale
                ? "stale"
                : "active"
            : index < activeIndex
              ? "complete"
              : "locked";
        return {
            id,
            status,
            active,
            unlockReason: index > activeIndex ? unlockReasonForPhase(id) : undefined,
        };
    });
}

export function highestPriorityUnresolvedPhase(progress: ProductionRunProgress): ProductionPhaseId {
    return deriveProductionRunPhases(progress).find((phase) => phase.active)?.id ?? "context";
}

export function deriveStaleOutputs(
    previous: ProductionDependencySnapshot,
    next: ProductionDependencySnapshot,
): ProductionOutput[] {
    const stale = new Set<ProductionOutput>();
    const addFrom = (output: ProductionOutput) => {
        const start = OUTPUT_ORDER.indexOf(output);
        OUTPUT_ORDER.slice(start).forEach((item) => stale.add(item));
    };

    if (previous.productId !== next.productId) addFrom("pattern-kit");
    if (
        previous.primaryReferenceId !== next.primaryReferenceId ||
        !sameIds(previous.supportingReferenceIds, next.supportingReferenceIds)
    ) {
        addFrom("creative-dna");
    }
    if (previous.selectedConceptId !== next.selectedConceptId) addFrom("campaign-pack");
    if (previous.packVersionId !== next.packVersionId) stale.add("preflight");
    if (previous.ugcAssetVersionId !== next.ugcAssetVersionId) stale.add("preflight");

    return OUTPUT_ORDER.filter((output) => stale.has(output));
}

export function resolveProductionAssetId({
    selectedAssetId,
    uploadedAssetId,
    fixtureAssetId,
    allowFixtureFallback = false,
}: {
    selectedAssetId?: string;
    uploadedAssetId?: string;
    fixtureAssetId?: string;
    allowFixtureFallback?: boolean;
}): string | undefined {
    return (
        selectedAssetId ?? uploadedAssetId ?? (allowFixtureFallback ? fixtureAssetId : undefined)
    );
}

export function successfulJobOutputId(
    job: { status: JobStatus; output_json: Record<string, unknown> | null } | null | undefined,
    outputKey: string,
): string | undefined {
    if (!job || !["succeeded", "completed"].includes(job.status)) return undefined;
    const value = job.output_json?.[outputKey];
    return typeof value === "string" && value.length > 0 ? value : undefined;
}

export function reviewOutcomeReady({
    reviewComplete,
    hardBlockerCount,
}: {
    reviewComplete: boolean;
    hardBlockerCount: number;
}): boolean {
    return reviewComplete && hardBlockerCount === 0;
}

function sameIds(left: string[] = [], right: string[] = []) {
    return (
        left.length === right.length &&
        [...left].sort().every((value, index) => value === [...right].sort()[index])
    );
}

function unlockReasonForPhase(id: ProductionPhaseId) {
    switch (id) {
        case "context":
            return undefined;
        case "decode":
            return "Complete product and reference context first.";
        case "adapt":
            return "Decode the reference pattern first.";
        case "build":
            return "Choose and confirm one product-specific concept first.";
        case "review":
            return "Create the Campaign Pack first.";
    }
}
