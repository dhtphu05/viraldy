import type { CampaignPack, StepId } from "@/features/campaigns/types/campaign";

export type CoherenceIssueCode =
    "product_context_leakage" | "selected_angle_mismatch" | "missing_cta" | "claim_blocker";

export type CoherenceIssue = {
    id: string;
    code: CoherenceIssueCode;
    message: string;
    step: StepId;
    severity: "blocker" | "warning";
};

export type CampaignCoherenceContext = {
    productName?: string;
    productCategory?: string;
    disallowedSourceTerms?: string[];
    selectedAngleTerms?: string[];
    blockedClaimTerms?: string[];
};

export function evaluateCampaignCoherence(
    pack: CampaignPack,
    context: CampaignCoherenceContext = {},
): CoherenceIssue[] {
    const content = campaignContent(pack);
    const normalizedContent = normalize(content);
    const issues: CoherenceIssue[] = [];

    for (const term of context.disallowedSourceTerms ?? []) {
        if (containsTerm(normalizedContent, term)) {
            issues.push({
                id: `product-context-${normalizeId(term)}`,
                code: "product_context_leakage",
                message: `Remove source-only context: ${term}.`,
                step: "script",
                severity: "blocker",
            });
        }
    }

    const angleTerms = (context.selectedAngleTerms ?? []).filter((term) => term.trim().length > 2);
    if (
        angleTerms.length > 0 &&
        !angleTerms.some((term) => containsTerm(normalizedContent, term))
    ) {
        issues.push({
            id: "selected-angle-mismatch",
            code: "selected_angle_mismatch",
            message: "The script and storyboard do not reflect the selected angle.",
            step: "script",
            severity: "blocker",
        });
    }

    if (!pack.cta.primary.trim()) {
        issues.push({
            id: "missing-cta",
            code: "missing_cta",
            message: "Add a specific creator CTA.",
            step: "cta",
            severity: "blocker",
        });
    }

    const blockedClaim = (context.blockedClaimTerms ?? []).find((term) =>
        containsTerm(normalizedContent, term),
    );
    if (blockedClaim) {
        issues.push({
            id: `claim-${normalizeId(blockedClaim)}`,
            code: "claim_blocker",
            message: `Remove unsupported claim: ${blockedClaim}.`,
            step: "cta",
            severity: "blocker",
        });
    }

    pack.cta.warnings
        .filter(
            (warning) => warning.risk === "High" && !pack.reviewedWarningIds.includes(warning.id),
        )
        .forEach((warning) => {
            issues.push({
                id: `claim-warning-${warning.id}`,
                code: "claim_blocker",
                message: warning.reason,
                step: "cta",
                severity: "blocker",
            });
        });

    return uniqueIssues(issues);
}

function campaignContent(pack: CampaignPack) {
    return [
        pack.name,
        pack.buyerSegment,
        pack.adaptation.adaptedHook,
        pack.adaptation.adaptedAngle,
        pack.adaptation.adaptedDemo,
        ...pack.script.flatMap((block) => [block.text, block.note ?? ""]),
        ...pack.storyboard.flatMap((scene) => [
            scene.visualDirection,
            scene.spokenLine,
            scene.onScreenText ?? "",
        ]),
        pack.cta.primary,
        pack.cta.offerStatement,
        pack.cta.shipping,
    ].join(" ");
}

function containsTerm(normalizedContent: string, term: string) {
    return normalizedContent.includes(normalize(term));
}

function normalize(value: string) {
    return value
        .toLocaleLowerCase()
        .replace(/[^a-z0-9]+/g, " ")
        .replace(/\s+/g, " ")
        .trim();
}

function normalizeId(value: string) {
    return normalize(value).replace(/\s+/g, "-");
}

function uniqueIssues(issues: CoherenceIssue[]) {
    return [...new Map(issues.map((issue) => [issue.id, issue])).values()];
}
