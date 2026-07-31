import { describe, expect, it } from "vitest";

import type { SeedProduct } from "@/features/creative-library/types/creative";
import type { Product } from "@/shared/api/products";
import {
    mergeCatalogProducts,
    productionRunSearchForProduct,
} from "@/features/products/lib/product-catalog";

const demo: SeedProduct = {
    id: "p-1",
    name: "Demo Organizer",
    category: "Home & Kitchen",
    price: 24.9,
    readiness: "Ready",
    fulfillmentRisk: "Low",
    linkedCampaignCount: 1,
    colorSeed: "#ff9a8b",
};

function backendProduct(overrides: Partial<Product> = {}): Product {
    return {
        id: "product-backend-1",
        workspace_id: "workspace-1",
        name: "Observed Product",
        description: "Observed description",
        status: "active",
        market: "VN",
        external_source: "website",
        external_id: null,
        metadata_json: {
            image_url: "https://images.example.test/product.jpg",
        },
        product_context: {
            schema_version: "product_context_v1",
            identity: {
                name: "Observed Product",
                brand: "Observed Brand",
                category: "Electronics",
                market: "VN",
                currency: "VND",
            },
            features: [],
            commercial: {
                price: "299000",
                compare_at_price: "399000",
            },
        },
        context_schema_version: "product_context_v1",
        product_context_version: 1,
        ...overrides,
    };
}

describe("product catalog", () => {
    it("merges backend products with demo products and removes an imported demo duplicate", () => {
        const importedDemo = backendProduct({
            id: "product-imported-demo",
            name: demo.name,
            external_source: "frontend_demo",
            external_id: demo.id,
            metadata_json: { frontend_seed_id: demo.id },
        });

        const catalog = mergeCatalogProducts([demo], [
            importedDemo,
            backendProduct({ id: "product-crawled" }),
        ]);

        expect(catalog).toHaveLength(2);
        expect(catalog.some((product) => product.origin === "demo")).toBe(false);
        expect(catalog.map((product) => product.id)).toEqual([
            "product-imported-demo",
            "product-crawled",
        ]);
    });

    it("maps dynamic backend category and unknown operational states without inventing them", () => {
        const [product] = mergeCatalogProducts([], [backendProduct()]);

        expect(product.category).toBe("Electronics");
        expect(product.brand).toBe("Observed Brand");
        expect(product.price).toBe(299000);
        expect(product.currency).toBe("VND");
        expect(product.readiness).toBe("Unknown");
        expect(product.fulfillmentRisk).toBe("Unknown");
        expect(product.imageUrl).toBe("https://images.example.test/product.jpg");
    });

    it("hands backend products to Production Run by productId and demos by localProductId", () => {
        const [backend] = mergeCatalogProducts([], [backendProduct()]);
        const [local] = mergeCatalogProducts([demo], []);

        expect(productionRunSearchForProduct(backend)).toMatchObject({
            entryType: "product-first",
            productId: "product-backend-1",
        });
        expect(productionRunSearchForProduct(backend).localProductId).toBeUndefined();
        expect(productionRunSearchForProduct(local)).toMatchObject({
            entryType: "product-first",
            localProductId: "p-1",
        });
        expect(productionRunSearchForProduct(local).productId).toBeUndefined();
    });
});
