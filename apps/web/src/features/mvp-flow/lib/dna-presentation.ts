import { humanizeLabel } from "@/shared/lib/display";

export type DnaInsight = {
    title: string;
    description?: string;
    meta?: string;
    tone: "positive" | "warning" | "neutral";
};

export function toMechanismInsights(value: unknown): DnaInsight[] {
    return records(value).map((item) => ({
        title: humanizeLabel(item.mechanism_type, "Reusable mechanism"),
        description: text(item.description),
        meta: evidenceMeta(item.evidence_ids, "Supported by"),
        tone: "positive",
    }));
}

export function toClaimInsights(value: unknown): DnaInsight[] {
    return records(value).map((item) => {
        const category = humanizeLabel(item.category, "Observed claim");
        const risk = humanizeLabel(item.risk, "Unknown");
        return {
            title: text(item.text) ?? "Observed claim",
            meta: `${category} · ${risk} risk`,
            tone: "neutral",
        };
    });
}

export function toRiskInsights(value: unknown): DnaInsight[] {
    return records(value).map((item) => {
        const priority = `${humanizeLabel(item.severity, "Unknown")} priority`;
        const evidence = evidenceMeta(item.evidence_ids);
        return {
            title: humanizeLabel(item.code, "Review required"),
            description: text(item.message),
            meta: evidence ? `${priority} · ${evidence}` : priority,
            tone: "warning",
        };
    });
}

function records(value: unknown): Array<Record<string, unknown>> {
    return Array.isArray(value)
        ? value.filter(
              (item): item is Record<string, unknown> =>
                  Boolean(item) && typeof item === "object" && !Array.isArray(item),
          )
        : [];
}

function text(value: unknown): string | undefined {
    return typeof value === "string" && value.trim() ? value.trim() : undefined;
}

function evidenceMeta(value: unknown, prefix?: string): string | undefined {
    const count = Array.isArray(value) ? value.length : 0;
    if (!count) return undefined;
    const label = `${count} evidence ${count === 1 ? "item" : "items"}`;
    return prefix ? `${prefix} ${label}` : label;
}
