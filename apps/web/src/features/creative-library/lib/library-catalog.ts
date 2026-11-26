import { seedCreatives } from "../mocks/creatives";
import type { CreativeReference } from "../types/creative";

const illustrationIds = new Set(seedCreatives.map((creative) => creative.id));

function normalizeSearch(value: string) {
    return value
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "")
        .replace(/đ/gi, "d")
        .toLowerCase();
}

export function matchesCreativeQuery(creative: CreativeReference, query: string) {
    const search = normalizeSearch(query.trim());
    return (
        !search ||
        normalizeSearch(
            [
                creative.title,
                creative.hookExcerpt,
                creative.brandOrCreator,
                creative.platform,
                creative.angle,
                creative.category,
                creative.notes ?? "",
                ...creative.tags,
            ].join(" "),
        ).includes(search)
    );
}

// This describes the saved source, not whether that URL still opens or passes validation.
export function getCreativeMediaKind(creative: CreativeReference): "video" | "image" | "reference" {
    if (!creative.mediaUrl?.trim()) return "reference";
    if (creative.mediaKind === "image") return "image";
    if (creative.mediaKind === "video" || (!creative.mediaKind && creative.durationSec > 0))
        return "video";
    return "reference";
}

export function isIllustrativeCreative(creative: CreativeReference) {
    return (
        illustrationIds.has(creative.id) ||
        creative.tags.some((tag) => tag.startsWith("demo")) ||
        /^\/(demo-media|product_ads)\//.test(creative.mediaUrl ?? "") ||
        /^(Demo|Video mẫu)/i.test(creative.brandOrCreator)
    );
}
