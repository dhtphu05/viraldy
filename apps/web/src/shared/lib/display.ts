const ACRONYMS: Record<string, string> = {
    ai: "AI",
    api: "API",
    cta: "CTA",
    dna: "DNA",
    gmv: "GMV",
    id: "ID",
    json: "JSON",
    kpi: "KPI",
    mvp: "Production",
    openai: "OpenAI",
    roi: "ROI",
    sku: "SKU",
    tiktok: "TikTok",
    ugc: "UGC",
    url: "URL",
    us: "US",
    v1: "v1",
    v2: "v2",
};

export function humanizeLabel(value: unknown, fallback = "Not available") {
    if (value === null || value === undefined || value === "") return fallback;
    const raw = String(value).trim();
    if (!raw) return fallback;
    return raw
        .replace(/([a-z0-9])([A-Z])/g, "$1 $2")
        .replace(/[_-]+/g, " ")
        .replace(/\s+/g, " ")
        .trim()
        .split(" ")
        .map((token) => {
            const lower = token.toLowerCase();
            if (ACRONYMS[lower]) return ACRONYMS[lower];
            return lower.charAt(0).toUpperCase() + lower.slice(1);
        })
        .join(" ");
}

export function humanizeSystemText(value: string) {
    return value.replace(/\b[a-z0-9]+(?:_[a-z0-9]+)+\b/gi, (token) =>
        humanizeLabel(token).toLowerCase(),
    );
}

export function formatSystemValue(value: unknown, fallback = "Not available"): string {
    if (value === null || value === undefined || value === "") return fallback;
    if (typeof value === "number" || typeof value === "boolean") return String(value);
    if (typeof value === "string") {
        return shouldHumanize(value) ? humanizeLabel(value, fallback) : value;
    }
    if (Array.isArray(value)) {
        const values = value
            .map((item) => formatSystemValue(item, fallback))
            .filter((item) => item !== fallback);
        return values.length ? values.join(", ") : fallback;
    }
    if (typeof value === "object") {
        const entries = Object.entries(value as Record<string, unknown>).slice(0, 4);
        if (!entries.length) return fallback;
        return entries
            .map(([key, item]) => `${humanizeLabel(key)}: ${formatSystemValue(item, fallback)}`)
            .join(" · ");
    }
    return fallback;
}

export function formatPercentScore(value: number) {
    return `${Math.round(value)} / 100`;
}

function shouldHumanize(value: string) {
    const trimmed = value.trim();
    return /^[a-z0-9_-]+$/i.test(trimmed) && /[_-]/.test(trimmed);
}
