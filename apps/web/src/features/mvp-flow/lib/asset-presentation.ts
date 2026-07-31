import type { Asset } from "@/shared/api/uploads";
import { humanizeLabel } from "@/shared/lib/display";

type PresentableAsset = Pick<Asset, "id" | "asset_type" | "metadata_json">;

export function assetDisplayName(
    asset: PresentableAsset | undefined,
    fallback = "No video selected",
) {
    if (!asset) return fallback;

    for (const key of ["title", "filename", "original_filename", "file_name", "name"]) {
        const value = asset.metadata_json[key];
        if (typeof value === "string" && value.trim()) return value.trim();
    }

    if (asset.asset_type === "ugc") return "UGC video";
    if (asset.asset_type === "reference") return "Reference video";
    if (asset.asset_type === "product_media") return "Product media";
    return `${humanizeLabel(asset.asset_type, "Uploaded")} video`;
}
