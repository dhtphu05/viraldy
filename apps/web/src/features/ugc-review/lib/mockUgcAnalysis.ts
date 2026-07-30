import type { UgcAsset, UgcAnalysis, UgcIssue, UgcRights } from "@/features/ugc-review/types/ugc";
import { seedUgcAnalyses, seedUgcIssues } from "@/features/ugc-review/mocks/ugcSeed";

export const ugcProcessingSteps: string[] = [
    "Preparing video",
    "Reading Campaign Pack",
    "Transcribing creator audio",
    "Reading on-screen text",
    "Detecting scenes and product visibility",
    "Checking hook, demo, offer and CTA",
    "Comparing video with required scenes",
    "Checking risky claims",
    "Building action recommendation",
    "Generating creator revision message",
];

// Deterministic frontend "analyzer". For seeded demo assets we return a
// pre-authored analysis so scores stay stable. For local uploads we produce
// a coherent "organic-ready" default so buttons remain meaningful.
export function analyzeUgcAsset(asset: UgcAsset): { analysis: UgcAnalysis; issues: UgcIssue[] } {
    // Map local uploads to a "sibling" demo analysis based on title heuristics
    // so users have something to interact with without any randomness.
    const heuristicId = pickTemplateAnalysisId(asset);
    if (heuristicId && seedUgcAnalyses[heuristicId]) {
        const base = seedUgcAnalyses[heuristicId];
        const issues = (seedUgcIssues[heuristicId] ?? []).map((i) => ({
            ...i,
            assetId: asset.id,
            id: `${asset.id}-${i.id}`,
        }));
        const analysis: UgcAnalysis = {
            ...base,
            assetId: asset.id,
            createdAt: new Date().toISOString(),
            markers: base.markers.map((m) => ({
                ...m,
                id: `${asset.id}-${m.id}`,
                issueId: m.issueId ? `${asset.id}-${m.issueId}` : undefined,
            })),
        };
        return { analysis, issues };
    }
    // Neutral fallback
    const analysis: UgcAnalysis = {
        assetId: asset.id,
        createdAt: new Date().toISOString(),
        score: 72,
        confidence: "Medium",
        summary: "Structural review complete.",
        reason: "Hook, demo and CTA are present. Rights fields still need to be filled in.",
        nextAction: "Complete rights fields, then decide organic vs paid.",
        dimensions: [],
        packAlignment: [],
        markers: [],
        transcript: [],
        scenes: [],
        onScreenText: [],
    };
    return { analysis, issues: [] };
}

function pickTemplateAnalysisId(asset: UgcAsset): string | undefined {
    const t = asset.title.toLowerCase();
    if (t.includes("v3") || t.includes("spark")) return "u-3";
    if (t.includes("v2") || t.includes("revision")) return "u-2";
    if (t.includes("dog")) return "u-4";
    if (t.includes("sofa") || t.includes("cover")) return "u-sofa-cover";
    if (t.includes("pet") || t.includes("roller")) return "u-11";
    if (t.includes("mirror") || t.includes("beauty")) return "u-2";
    if (t.includes("claim") || t.includes("aggressive")) return "u-10";
    return "u-1";
}

// Given an analysis + rights, decide the final decision label.
export function deriveDecision(analysis: UgcAnalysis, rights: UgcRights): UgcAsset["decision"] {
    if (analysis.failed) return "failed";
    const compliance = analysis.dimensions.find((d) => d.id === "compliance")?.score ?? 100;
    if (compliance < 40) return "reject";
    if (analysis.score < 55) return "request-revision";
    if (analysis.score < 72) return "request-revision";
    // 72+ candidate
    const hasBlockingIssue = false;
    void hasBlockingIssue;
    const sparkComplete =
        rights.sparkAllowed && !!rights.sparkCode && !!rights.sparkExpiry && !!rights.durationDays;
    if (analysis.score >= 82 && sparkComplete) return "spark-ready";
    if (analysis.score >= 78 && rights.sparkAllowed) return "small-spark-test";
    return "organic-ready";
}

export function sparkBlockers(rights: UgcRights): string[] {
    const out: string[] = [];
    if (!rights.sparkAllowed) out.push("Spark Ads usage not authorized");
    if (!rights.sparkCode) out.push("Spark authorization code missing");
    if (!rights.sparkExpiry) out.push("Spark code expiry missing");
    if (!rights.durationDays) out.push("Paid usage duration missing");
    if (!rights.editingAllowed) out.push("Editing permission missing");
    return out;
}

export function generateRevisionMessage(
    creatorFirstName: string,
    positives: string[],
    fixes: string[],
): string {
    const lines: string[] = [];
    lines.push(`Hi ${creatorFirstName || "there"} — thanks for sending this over.`);
    lines.push("");
    if (positives.length > 0) {
        lines.push(
            positives.length === 1
                ? positives[0]
                : `${positives.slice(0, 2).join(" ")} These are really working.`,
        );
        lines.push("");
    }
    if (fixes.length > 0) {
        lines.push(
            fixes.length === 1
                ? "Could you make this update before the final version?"
                : "Could you make these updates before the final version?",
        );
        fixes.forEach((f, i) => lines.push(`${i + 1}. ${f}`));
        lines.push("");
    }
    lines.push(
        "Please keep your natural delivery and pacing — that's the strongest part of the video.",
    );
    return lines.join("\n");
}
