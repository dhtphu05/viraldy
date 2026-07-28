import type { CampaignPack } from "@/features/campaigns/types/campaign";
import { generateCreatorBrief } from "@/features/campaigns/lib/mockCampaignAI";
import { seedProducts } from "@/features/products/data/products";

function slugify(s: string) {
    return s
        .toLowerCase()
        .trim()
        .replace(/[^a-z0-9]+/g, "-")
        .replace(/^-+|-+$/g, "")
        .slice(0, 80);
}

export function briefFilename(pack: CampaignPack, ext: "txt" | "json") {
    return `${slugify(pack.name || "campaign")}-creator-brief.${ext}`;
}

export function downloadBlob(filename: string, content: string, mime: string) {
    const blob = new Blob([content], { type: mime });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 500);
}

export function exportBriefText(pack: CampaignPack) {
    const productName = seedProducts.find((p) => p.id === pack.productId)?.name ?? "your product";
    const text = generateCreatorBrief(pack, productName);
    downloadBlob(briefFilename(pack, "txt"), text, "text/plain;charset=utf-8");
}

export function exportBriefJson(pack: CampaignPack) {
    downloadBlob(briefFilename(pack, "json"), JSON.stringify(pack, null, 2), "application/json");
}

export async function copyBriefToClipboard(pack: CampaignPack) {
    const productName = seedProducts.find((p) => p.id === pack.productId)?.name ?? "your product";
    const text = generateCreatorBrief(pack, productName);
    if (!navigator.clipboard) throw new Error("Clipboard unavailable");
    await navigator.clipboard.writeText(text);
}
