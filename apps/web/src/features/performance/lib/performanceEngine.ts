import type {
    PerfAsset,
    CampaignPerfSummary,
    Confidence,
    DecisionGroup,
} from "@/features/performance/types/performance";

// ----- Formatting -----
export const fmtMoney = (n: number, digits = 0) =>
    n < 0
        ? `-$${Math.abs(n).toLocaleString("en-US", { maximumFractionDigits: digits })}`
        : `$${n.toLocaleString("en-US", { maximumFractionDigits: digits })}`;

export const fmtPct = (n: number, digits = 1) => `${(n * 100).toFixed(digits)}%`;

export const fmtNum = (n: number) => n.toLocaleString("en-US");

// ----- Derived metrics -----
export function grossProfit(a: PerfAsset): number {
    return Math.round(a.gmv - a.commission - a.cogs - a.adSpend - a.refunds - a.sampleCost);
}

export function roasLabel(a: PerfAsset): string {
    if (a.adSpend <= 0) return "Organic / no paid spend";
    return (a.gmv / a.adSpend).toFixed(2);
}

export function gmvPerSample(a: PerfAsset): number | null {
    if (a.sampleCost <= 0) return null;
    return Math.round(a.gmv / a.sampleCost);
}

// ----- Decision grouping tone -----
export const decisionTone: Record<
    DecisionGroup,
    "ok" | "warn" | "info" | "destructive" | "neutral"
> = {
    Scale: "ok",
    Fix: "warn",
    Rehire: "info",
    Hold: "neutral",
    Stop: "destructive",
    Refresh: "info",
};

// ----- Confidence rules -----
export function computeConfidence(
    sampleSize: number,
    hasCompleteCost: boolean,
    hasComparison: boolean,
): Confidence {
    if (sampleSize < 3 || !hasCompleteCost) return "Low";
    if (sampleSize >= 5 && hasCompleteCost && hasComparison) return "High";
    return "Medium";
}

// ----- Diagnostic heuristics -----
export type Diagnostic = {
    id: string;
    label: string;
    severity: "info" | "warn" | "destructive" | "ok";
    reason: string;
    suggestion: string;
};

export function diagnoseAsset(a: PerfAsset, medianCtr: number, medianOrders: number): Diagnostic[] {
    const out: Diagnostic[] = [];
    const clickRate = a.views > 0 ? a.productClicks / a.views : 0;
    const orderConv = a.productClicks > 0 ? a.orders / a.productClicks : 0;

    if (a.views > 40_000 && clickRate < 0.008) {
        out.push({
            id: "d1",
            label: "High views, low product clicks",
            severity: "warn",
            reason: "Creative curiosity is not translating into product interest.",
            suggestion: "Check product clarity, reveal timing, offer, and creator-product fit.",
        });
    }
    if (a.ctr > medianCtr && a.orders < medianOrders * 0.5 && orderConv < 0.05) {
        out.push({
            id: "d2",
            label: "High CTR, low order conversion",
            severity: "warn",
            reason: "Downstream product-page, price, shipping, reviews, or offer friction.",
            suggestion: "Audit the product page and offer consistency.",
        });
    }
    if (a.watchRate > 0.65 && a.views < 30_000) {
        out.push({
            id: "d3",
            label: "Strong watch rate, weak reach",
            severity: "info",
            reason: "Content resonates but distribution is limited.",
            suggestion:
                "Try controlled Spark distribution or a stronger caption and opening frame.",
        });
    }
    const eff = gmvPerSample(a);
    if (eff !== null && eff >= 100 && a.rightsStatus === "complete") {
        out.push({
            id: "d4",
            label: "High GMV per sample with complete rights",
            severity: "ok",
            reason: "This asset is efficient and paid-ready.",
            suggestion: "Rehire creator and produce controlled variants.",
        });
    }
    if (a.ugcScore >= 78 && a.ctr < medianCtr * 0.6) {
        out.push({
            id: "d5",
            label: "High UGC score, weak CTR",
            severity: "info",
            reason: "Structurally sound, but the angle or offer may not match the buyer.",
            suggestion: "Test a new angle or offer variation with the same creator.",
        });
    }
    if ((a.ctrTrendPct ?? 0) < -0.15 && (a.hookRepeatCount ?? 1) >= 3) {
        out.push({
            id: "d6",
            label: "Declining CTR with repeated hook",
            severity: "warn",
            reason: "CTR is trending down while the hook is repeated across active assets.",
            suggestion: "Refresh hook and first scene before stopping the product.",
        });
    }
    if (grossProfit(a) < 0) {
        out.push({
            id: "d7",
            label: "Negative gross profit",
            severity: "destructive",
            reason: "Costs exceed revenue on this asset.",
            suggestion:
                "Hold or stop scaling until margin, commission, ad spend, or refund issue is resolved.",
        });
    }
    if (a.rightsStatus !== "complete" && a.orders >= 30) {
        out.push({
            id: "d8",
            label: "Organic performance is strong, Spark rights are incomplete",
            severity: "info",
            reason: "Missing Spark authorization is blocking paid amplification.",
            suggestion: "Request authorization before paid amplification.",
        });
    }
    return out;
}

// ----- Simple CSV parser -----
export function parseCsv(text: string): { headers: string[]; rows: Record<string, string>[] } {
    const lines = text
        .replace(/\r/g, "")
        .split("\n")
        .filter((l) => l.trim().length > 0);
    if (lines.length === 0) return { headers: [], rows: [] };
    const headers = splitCsvLine(lines[0]);
    const rows = lines.slice(1).map((line) => {
        const cells = splitCsvLine(line);
        const obj: Record<string, string> = {};
        headers.forEach((h, i) => (obj[h.trim()] = (cells[i] ?? "").trim()));
        return obj;
    });
    return { headers: headers.map((h) => h.trim()), rows };
}

function splitCsvLine(line: string): string[] {
    const out: string[] = [];
    let cur = "";
    let inQuotes = false;
    for (let i = 0; i < line.length; i++) {
        const c = line[i];
        if (c === '"') {
            if (inQuotes && line[i + 1] === '"') {
                cur += '"';
                i++;
            } else inQuotes = !inQuotes;
        } else if (c === "," && !inQuotes) {
            out.push(cur);
            cur = "";
        } else cur += c;
    }
    out.push(cur);
    return out;
}

export const canonicalFields = [
    "date",
    "campaign_id",
    "campaign_name",
    "asset_id",
    "asset_name",
    "creator",
    "product",
    "views",
    "watch_rate",
    "ctr",
    "product_clicks",
    "add_to_cart",
    "orders",
    "gmv",
    "commission",
    "sample_cost",
    "ad_spend",
    "refunds",
    "gross_profit",
] as const;

export const requiredFields = ["asset_name", "gmv", "orders"] as const;

// ----- Export helpers -----
export function downloadBlob(filename: string, content: string, type = "text/plain") {
    const blob = new Blob([content], { type });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 0);
}

export function tableToCsv(
    rows: Record<string, string | number | null>[],
    columns: string[],
): string {
    const head = columns.join(",");
    const body = rows.map((r) => columns.map((c) => escapeCsv(r[c] ?? "")).join(",")).join("\n");
    return `${head}\n${body}`;
}

function escapeCsv(v: string | number | null): string {
    const s = String(v ?? "");
    if (s.includes(",") || s.includes('"') || s.includes("\n")) {
        return `"${s.replace(/"/g, '""')}"`;
    }
    return s;
}

// ----- Campaign-level derivations -----
export function bestOnAttention(assets: PerfAsset[]) {
    return [...assets].sort((a, b) => b.views - a.views)[0];
}
export function bestOnConversion(assets: PerfAsset[]) {
    return [...assets].sort(
        (a, b) => b.orders / Math.max(1, b.productClicks) - a.orders / Math.max(1, a.productClicks),
    )[0];
}
export function bestOnProfit(assets: PerfAsset[]) {
    return [...assets].sort((a, b) => grossProfit(b) - grossProfit(a))[0];
}
export function bestOnSampleEfficiency(assets: PerfAsset[]) {
    return [...assets].sort((a, b) => (gmvPerSample(b) ?? 0) - (gmvPerSample(a) ?? 0))[0];
}
export function bestPaidReady(assets: PerfAsset[]) {
    return [...assets]
        .filter((a) => a.rightsStatus === "complete")
        .sort((a, b) => grossProfit(b) - grossProfit(a))[0];
}

// ----- Pattern generation for variants -----
export type GeneratedVariant = {
    id: string;
    name: string;
    keep: string;
    change: string;
    creator: string;
    cta: string;
    priority: "High" | "Medium" | "Low";
    reason: string;
};

export function generateVariants(
    patternAngle: string,
    patternHook: string,
    product: string,
): GeneratedVariant[] {
    const t = Date.now();
    return [
        {
            id: `v-${t}-1`,
            name: "Variant A — new visual interrupt",
            keep: `${patternAngle} structure and early product reveal`,
            change: "Open with a drawer-level visual interruption",
            creator: "Small-space apartment creator",
            cta: `Tap the product link to see ${product} sizes.`,
            priority: "High",
            reason: "Same structure, new hook signal for algorithmic distribution",
        },
        {
            id: `v-${t}-2`,
            name: "Variant B — proof-first",
            keep: patternAngle,
            change: `Replace opening line with before-and-after in first 1 second`,
            creator: "First-time buyer creator",
            cta: `See the exact ${product} in the caption.`,
            priority: "Medium",
            reason: "Lead with proof to compress attention loop",
        },
        {
            id: `v-${t}-3`,
            name: "Variant C — identity hook",
            keep: `${patternAngle} pacing`,
            change: `New hook: "If you're the person who ${patternHook.toLowerCase().includes("kitchen") ? "reorganizes your kitchen weekly" : "notices small daily annoyances"}..."`,
            creator: "Everyday household creator",
            cta: "Tap the product tag to try it.",
            priority: "Medium",
            reason: "Test identity framing with same structural pattern",
        },
    ];
}
