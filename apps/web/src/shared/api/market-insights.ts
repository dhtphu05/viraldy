import { apiGet } from "@/shared/api/client";

export type MarketInsightSnapshot = {
    id: string;
    slug: string;
    snapshot_type: string;
    title: string;
    category: string | null;
    market: string | null;
    date_range: Record<string, string>;
    payload: Record<string, unknown>;
    published_at: string | null;
};

export function getPublicMarketInsight(slug: string) {
    return apiGet<MarketInsightSnapshot>(`/insights/${encodeURIComponent(slug)}`);
}
