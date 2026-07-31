import type { SeedProduct } from "@/features/creative-library/types/creative";
import type { Product } from "@/shared/api/products";

export type CatalogReadiness = SeedProduct["readiness"] | "Unknown";
export type CatalogRisk = SeedProduct["fulfillmentRisk"] | "Unknown";

export type CatalogProduct = {
    id: string;
    origin: "demo" | "backend";
    backendProductId?: string;
    localProductId?: string;
    name: string;
    description?: string;
    brand?: string;
    category: string;
    market: string;
    currency?: string;
    price: number | null;
    compareAtPrice: number | null;
    readiness: CatalogReadiness;
    fulfillmentRisk: CatalogRisk;
    colorSeed: string;
    imageUrl?: string;
    imageAlt?: string;
    sourceUrl?: string;
    sourceType?: string;
    rating?: string;
    reviewsCount?: string;
};

export type ProductProductionSearch = {
    entryType: "product-first";
    productId?: string;
    localProductId?: string;
    objective: "tiktok_shop_affiliate_test";
    market: string;
};

export function mergeCatalogProducts(
    seedProducts: SeedProduct[],
    backendProducts: Product[],
): CatalogProduct[] {
    const importedSeedIds = new Set(
        backendProducts.map(importedSeedId).filter((value): value is string => Boolean(value)),
    );
    const demos = seedProducts
        .filter((product) => !importedSeedIds.has(product.id))
        .map(mapSeedProduct);
    const backend = uniqueById(backendProducts).map(mapBackendProduct);
    return [...demos, ...backend];
}

export function productionRunSearchForProduct(product: CatalogProduct): ProductProductionSearch {
    const base = {
        entryType: "product-first" as const,
        objective: "tiktok_shop_affiliate_test" as const,
        market: observedText(product.market) || "US",
    };
    return product.origin === "backend"
        ? { ...base, productId: product.backendProductId ?? product.id }
        : { ...base, localProductId: product.localProductId ?? product.id };
}

function mapSeedProduct(product: SeedProduct): CatalogProduct {
    return {
        id: product.id,
        origin: "demo",
        localProductId: product.id,
        name: product.name,
        category: product.category,
        market: "US",
        currency: "USD",
        price: product.price,
        compareAtPrice: null,
        readiness: product.readiness,
        fulfillmentRisk: product.fulfillmentRisk,
        colorSeed: product.colorSeed,
        imageUrl: product.imageUrl,
        imageAlt: product.imageAlt,
        sourceType: "demo",
    };
}

function mapBackendProduct(product: Product): CatalogProduct {
    const identity = product.product_context.identity;
    const metadata = product.metadata_json;
    const market = observedText(identity.market) || observedText(product.market) || "Unknown";
    return {
        id: product.id,
        origin: "backend",
        backendProductId: product.id,
        name: observedText(identity.name) || product.name,
        description: observedText(product.description),
        brand: observedText(identity.brand),
        category: observedText(identity.category) || "Unknown",
        market,
        currency: observedText(identity.currency),
        price: numberValue(product.product_context.commercial.price),
        compareAtPrice: numberValue(product.product_context.commercial.compare_at_price),
        readiness: readinessValue(metadata.readiness),
        fulfillmentRisk: riskValue(metadata.fulfillment_risk),
        colorSeed: colorForId(product.id),
        imageUrl:
            observedText(metadata.image_url) || firstString(metadata.screenshots) || undefined,
        imageAlt: `${product.name} product image`,
        sourceUrl: observedText(metadata.source_url),
        sourceType: observedText(product.external_source),
        rating: observedText(metadata.rating),
        reviewsCount: observedText(metadata.reviews_count),
    };
}

function importedSeedId(product: Product): string | undefined {
    const explicit = observedText(product.metadata_json.frontend_seed_id);
    if (explicit) return explicit;
    if (product.external_source === "frontend_demo") {
        return observedText(product.external_id);
    }
    return undefined;
}

function uniqueById(products: Product[]): Product[] {
    const seen = new Set<string>();
    return products.filter((product) => {
        if (seen.has(product.id)) return false;
        seen.add(product.id);
        return true;
    });
}

function readinessValue(value: unknown): CatalogReadiness {
    return value === "Ready" || value === "Setup needed" || value === "Out of stock"
        ? value
        : "Unknown";
}

function riskValue(value: unknown): CatalogRisk {
    return value === "Low" || value === "Medium" || value === "High" ? value : "Unknown";
}

function observedText(value: unknown): string {
    if (typeof value !== "string") return "";
    const text = value.trim();
    return text.toLowerCase() === "unknown" || text.toLowerCase() === "n/a" ? "" : text;
}

function numberValue(value: unknown): number | null {
    if (typeof value === "number") return Number.isFinite(value) ? value : null;
    if (typeof value !== "string" || !value.trim()) return null;
    const result = Number(value);
    return Number.isFinite(result) ? result : null;
}

function firstString(value: unknown): string {
    if (!Array.isArray(value)) return "";
    return observedText(value[0]);
}

function colorForId(id: string): string {
    let hash = 0;
    for (const character of id) {
        hash = (hash * 31 + character.charCodeAt(0)) >>> 0;
    }
    return `hsl(${hash % 360} 58% 76%)`;
}
