import { apiGet, apiPost } from "@/shared/api/client";

export type ProductIdentity = {
    name: string;
    brand?: string | null;
    category: string;
    subcategory?: string | null;
    variant?: string | null;
    market: string;
    currency?: string | null;
};

export type ProductCommercial = {
    price?: string | number | null;
    compare_at_price?: string | number | null;
    discount_text?: string | null;
    bundle_text?: string | null;
    shipping_text?: string | null;
    commission_percent?: string | number | null;
    margin_band?: string;
    offer_notes?: string[];
};

export type ProductContext = {
    schema_version: "product_context_v1";
    identity: ProductIdentity;
    personas?: unknown[];
    benefits?: unknown[];
    features?: Array<{
        id: string;
        label: string;
        description?: string | null;
        visual_demo_possible?: boolean;
        visual_cues?: string[];
    }>;
    commercial: ProductCommercial;
    creative?: Record<string, unknown>;
    personalization?: Record<string, unknown>;
    governance?: Record<string, unknown>;
};

export type CreateProductInput = {
    name: string;
    description?: string | null;
    market?: string | null;
    external_source?: string | null;
    external_id?: string | null;
    metadata_json: Record<string, unknown>;
    product_context: ProductContext;
};

export type Product = {
    id: string;
    workspace_id: string;
    name: string;
    description: string | null;
    status: string;
    market: string | null;
    external_source: string | null;
    external_id: string | null;
    metadata_json: Record<string, unknown>;
    product_context: ProductContext;
    context_schema_version: string;
    product_context_version: number;
};

export type ProductCrawlPreview = {
    source_url: string;
    crawl: Record<string, unknown>;
    product_draft: CreateProductInput;
};

export type ProductWorkspace = {
    id: string;
    name: string;
};

export function listProductWorkspaces() {
    return apiGet<ProductWorkspace[]>("/workspaces");
}

export function listProducts(workspaceId: string) {
    return apiGet<Product[]>(`/workspaces/${workspaceId}/products`);
}

export function crawlProductPreview(workspaceId: string, url: string) {
    return apiPost<ProductCrawlPreview>(
        `/workspaces/${workspaceId}/products/crawl-preview`,
        { url },
    );
}

export function createProduct(workspaceId: string, input: CreateProductInput) {
    return apiPost<Product>(`/workspaces/${workspaceId}/products`, input);
}
