import type { Recommendation } from "@/shared/types";

export const recommendations: Recommendation[] = [
    {
        id: "r-1",
        kind: "Scale",
        title: "Problem-solution angle with a home-organization creator",
        summary:
            "Pair @tidy.emma's under-cabinet problem-solution format with your top 3 SKUs. Combination outperformed the campaign median by 2.4×.",
        metric: { label: "GMV per sample", value: "$184" },
        confidence: "High",
        reason: "This combination generated 2.4× higher conversion than the campaign median across 14 days.",
        evidence: [
            "3 assets over $150 GMV per sample",
            "Watch-through rate 71% vs 44% median",
            "Comment sentiment: 88% positive",
        ],
    },
    {
        id: "r-2",
        kind: "Fix",
        title: "Beauty Mirror hook is losing viewers in first 3 seconds",
        summary:
            "Rewrite the hook to lead with the problem instead of the product beauty shot. Predicted +32% retention.",
        metric: { label: "Hook retention", value: "38%" },
        confidence: "Medium",
        reason: "3 of 4 assets show >55% drop-off before product reveal.",
        evidence: ["Drop-off cliff at 2.4s across 4 assets", "Median first comment at 8s"],
    },
    {
        id: "r-3",
        kind: "Rehire",
        title: "Rehire @theresa_pets for Q1 Pet Vertical",
        summary:
            "Consistently high GMV per sample across two products. Reply rate <4h and Spark-ready on time.",
        metric: { label: "GMV per sample", value: "$212" },
        confidence: "High",
        reason: "Two consecutive campaigns above the 90th percentile of GMV per sample.",
        evidence: ["Avg GMV per sample: $212", "Spark-ready: 100% on time", "3 assets scaled paid"],
    },
    {
        id: "r-4",
        kind: "Stop testing",
        title: "Stop testing 'reaction' format on Kitchen Organizer",
        summary:
            "Reaction format underperforms problem-solution by 3× on this SKU. Reallocate sample budget.",
        metric: { label: "GMV per sample", value: "$41" },
        confidence: "High",
        reason: "5 reaction-format assets tested, all below the kill threshold.",
        evidence: ["All 5 assets below $60 GMV per sample", "Reallocate ~$900 sample budget"],
    },
];
