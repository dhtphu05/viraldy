import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useState, type ReactNode } from "react";
import { AppShell } from "@/widgets/app-shell/app-shell";
import { PageHeader } from "@/shared/ui/page-header";
import { SurfaceCard } from "@/shared/ui/surface-card";
import { Button } from "@/shared/ui/button";
import { Input } from "@/shared/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/shared/ui/select";
import { StatusChip } from "@/shared/ui/status-chip";
import { RightDrawer } from "@/shared/ui/right-drawer";
import { EmptyState } from "@/shared/ui/empty-state";
import { Skeleton } from "@/shared/ui/skeleton";
import { DemoMediaTile } from "@/shared/ui/demo-media-tile";
import { MetricStrip } from "@/shared/ui/metric-strip";
import { hasConfiguredApiBaseUrl } from "@/shared/api/client";
import { queryKeys } from "@/shared/api/query-keys";
import { listProducts, listProductWorkspaces, type Product } from "@/shared/api/products";
import { seedProducts } from "@/features/products/data/products";
import { ImportProductDialog } from "@/features/products/components/import-product-dialog";
import {
    mergeCatalogProducts,
    productionRunSearchForProduct,
    type CatalogProduct,
    type CatalogReadiness,
    type CatalogRisk,
} from "@/features/products/lib/product-catalog";
import { useAllCampaigns, useAppStore } from "@/app/store/app-store";
import { seedCreators } from "@/features/ugc-review/mocks/creators";
import type { CreativeReference } from "@/features/creative-library/types/creative";
import type { UgcAsset } from "@/features/ugc-review/types/ugc";
import {
    ArrowRight,
    Images,
    Megaphone,
    Package,
    Search,
    Sparkles,
    Video,
    type LucideIcon,
} from "lucide-react";

export const Route = createFileRoute("/products")({
    validateSearch: (search: Record<string, unknown>) => ({
        productId: typeof search.productId === "string" ? search.productId : undefined,
    }),
    head: () => ({ meta: [{ title: "Products - Viraldy" }] }),
    component: ProductsPage,
});

const READINESS = ["All", "Ready", "Setup needed", "Out of stock", "Unknown"] as const;
const RISKS = ["All", "Low", "Medium", "High", "Unknown"] as const;

function ProductsPage() {
    const search = Route.useSearch();
    const navigate = useNavigate();
    const campaigns = useAllCampaigns();
    const creatives = useAppStore((s) => s.creatives);
    const ugcAssets = useAppStore((s) => s.ugcAssets);
    const workspaces = useQuery({
        queryKey: queryKeys.workspaces.list,
        queryFn: listProductWorkspaces,
        enabled: hasConfiguredApiBaseUrl,
    });
    const workspaceId = workspaces.data?.[0]?.id;
    const products = useQuery({
        queryKey: queryKeys.products.list(workspaceId),
        queryFn: () => listProducts(workspaceId!),
        enabled: Boolean(workspaceId),
    });
    const catalog = useMemo(
        () => mergeCatalogProducts(seedProducts, products.data ?? []),
        [products.data],
    );
    const categories = useMemo(
        () => ["All", ...new Set(catalog.map((product) => product.category))],
        [catalog],
    );

    const [query, setQuery] = useState("");
    const [category, setCategory] = useState("All");
    const [readiness, setReadiness] = useState<(typeof READINESS)[number]>("All");
    const [risk, setRisk] = useState<(typeof RISKS)[number]>("All");
    const [selectedId, setSelectedId] = useState<string | null>(search.productId ?? null);

    useEffect(() => {
        if (search.productId) {
            setSelectedId(search.productId);
        }
    }, [search.productId]);

    const filtered = useMemo(() => {
        const q = query.trim().toLowerCase();
        return catalog.filter((product) => {
            if (
                q &&
                !`${product.name} ${product.brand ?? ""} ${product.category}`
                    .toLowerCase()
                    .includes(q)
            ) {
                return false;
            }
            if (category !== "All" && product.category !== category) return false;
            if (readiness !== "All" && product.readiness !== readiness) return false;
            if (risk !== "All" && product.fulfillmentRisk !== risk) return false;
            return true;
        });
    }, [catalog, category, query, readiness, risk]);

    const selected = catalog.find((product) => product.id === selectedId) ?? null;
    const hasFilters = Boolean(
        query.trim() || category !== "All" || readiness !== "All" || risk !== "All",
    );
    const catalogLoading =
        hasConfiguredApiBaseUrl &&
        (workspaces.isLoading || (Boolean(workspaceId) && products.isLoading));
    const totalCampaigns = campaigns.filter((campaign) =>
        catalog.some((product) => product.name === campaign.product),
    ).length;
    const readyCount = catalog.filter((product) => product.readiness === "Ready").length;
    const linkedCreativeCount = creatives.filter((creative) => creative.linkedProductId).length;

    const openProduct = (id: string) => {
        setSelectedId(id);
        void navigate({ to: "/products", replace: true, search: { productId: id } });
    };

    const closeProduct = () => {
        setSelectedId(null);
        void navigate({
            to: "/products",
            replace: true,
            search: { productId: undefined },
        });
    };

    const startProductionRun = (product: CatalogProduct) => {
        void navigate({
            to: "/mvp",
            search: productionRunSearchForProduct(product),
        });
    };

    return (
        <AppShell>
            <div className="flex flex-col gap-6">
                <PageHeader
                    title="Products"
                    description="Catalog context for campaign planning, creative reuse, and sample risk."
                    actions={
                        <>
                            <ImportProductDialog
                                workspaceId={workspaceId}
                                onImported={(product: Product) => openProduct(product.id)}
                            />
                            <Button
                                onClick={() => {
                                    const firstReady =
                                        catalog.find((product) => product.readiness === "Ready") ??
                                        catalog[0];
                                    if (firstReady) startProductionRun(firstReady);
                                }}
                                disabled={catalog.length === 0}
                            >
                                <Sparkles className="h-4 w-4" />
                                Start production run
                            </Button>
                        </>
                    }
                />

                <MetricStrip
                    ariaLabel="Product catalog summary"
                    metrics={[
                        {
                            id: "products",
                            label: "Products",
                            value: catalog.length,
                            hint: "Demo + workspace catalog",
                        },
                        {
                            id: "ready",
                            label: "Ready to brief",
                            value: readyCount,
                            hint: "Low-friction starts",
                            tone: "ok",
                        },
                        {
                            id: "signals",
                            label: "Linked signals",
                            value: linkedCreativeCount + totalCampaigns,
                            hint: "Creatives + campaigns",
                            tone: "info",
                        },
                    ]}
                />

                <SurfaceCard padding="sm" className="flex flex-wrap items-center gap-2">
                    {catalogLoading ? (
                        <div
                            role="status"
                            aria-live="polite"
                            aria-busy="true"
                            aria-label="Loading product catalog filters"
                            className="grid w-full gap-2 sm:grid-cols-[minmax(220px,1fr)_170px_160px_140px]"
                        >
                            <Skeleton className="h-10" />
                            <Skeleton className="h-10" />
                            <Skeleton className="h-10" />
                            <Skeleton className="h-10" />
                        </div>
                    ) : (
                        <>
                            <div className="relative min-w-[220px] flex-1">
                                <Search className="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-text-tertiary" />
                                <Input
                                    className="pl-8"
                                    aria-label="Search products"
                                    placeholder="Search products, categories..."
                                    value={query}
                                    onChange={(event) => setQuery(event.target.value)}
                                />
                            </div>
                            <Select
                                value={category}
                                onValueChange={(value) => setCategory(value as typeof category)}
                            >
                                <SelectTrigger
                                    className="w-[170px]"
                                    aria-label="Filter by category"
                                >
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    {categories.map((item) => (
                                        <SelectItem key={item} value={item}>
                                            {item === "All" ? "All categories" : item}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                            <Select
                                value={readiness}
                                onValueChange={(value) => setReadiness(value as typeof readiness)}
                            >
                                <SelectTrigger
                                    className="w-[160px]"
                                    aria-label="Filter by readiness"
                                >
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    {READINESS.map((item) => (
                                        <SelectItem key={item} value={item}>
                                            {item === "All" ? "All readiness" : item}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                            <Select
                                value={risk}
                                onValueChange={(value) => setRisk(value as typeof risk)}
                            >
                                <SelectTrigger
                                    className="w-[140px]"
                                    aria-label="Filter by fulfillment risk"
                                >
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    {RISKS.map((item) => (
                                        <SelectItem key={item} value={item}>
                                            {item === "All" ? "All risks" : `${item} risk`}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                            {hasFilters && (
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => {
                                        setQuery("");
                                        setCategory("All");
                                        setReadiness("All");
                                        setRisk("All");
                                    }}
                                >
                                    Clear filters
                                </Button>
                            )}
                        </>
                    )}
                </SurfaceCard>

                {catalogLoading ? (
                    <ProductCatalogSkeleton />
                ) : filtered.length === 0 ? (
                    <SurfaceCard padding="lg">
                        <EmptyState
                            icon={Package}
                            title={
                                catalog.length
                                    ? "No products match these filters"
                                    : "Build your product catalog"
                            }
                            description={
                                catalog.length
                                    ? "Clear filters or search a broader category to continue campaign planning."
                                    : "Import a public product page to create the context needed for creative adaptation and campaign planning."
                            }
                            action={
                                catalog.length ? (
                                    <Button
                                        variant="secondary"
                                        size="sm"
                                        onClick={() => {
                                            setQuery("");
                                            setCategory("All");
                                            setReadiness("All");
                                            setRisk("All");
                                        }}
                                    >
                                        Clear filters
                                    </Button>
                                ) : (
                                    <ImportProductDialog
                                        workspaceId={workspaceId}
                                        onImported={(product: Product) => openProduct(product.id)}
                                    />
                                )
                            }
                        />
                    </SurfaceCard>
                ) : (
                    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                        {filtered.map((product) => {
                            const linkedCampaigns = campaigns.filter(
                                (campaign) => campaign.product === product.name,
                            );
                            const linkedCreatives = creatives.filter(
                                (creative) =>
                                    creative.linkedProductId === catalogLinkId(product) &&
                                    !creative.archived,
                            );
                            return (
                                <button
                                    key={product.id}
                                    type="button"
                                    onClick={() => openProduct(product.id)}
                                    className="surface-card-interactive inner-top-highlight overflow-hidden text-left focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                                >
                                    <DemoMediaTile
                                        mediaUrl={product.imageUrl}
                                        mediaKind={product.imageUrl ? "image" : undefined}
                                        alt={product.imageAlt}
                                        seed={product.colorSeed}
                                        label={product.category}
                                        badges={[product.readiness]}
                                        aspect="16 / 7"
                                    />
                                    <div className="flex flex-col gap-4 p-4">
                                        <div className="flex items-start justify-between gap-3">
                                            <div className="min-w-0">
                                                <p className="truncate text-sm font-semibold text-text-primary">
                                                    {product.name}
                                                </p>
                                                <p className="mt-0.5 text-xs text-text-secondary">
                                                    {product.category} · {productPrice(product)}
                                                </p>
                                            </div>
                                            <ArrowRight className="mt-0.5 h-4 w-4 shrink-0 text-text-tertiary" />
                                        </div>
                                        <div className="flex flex-wrap gap-2">
                                            <StatusChip tone={readinessTone(product.readiness)} dot>
                                                {product.readiness}
                                            </StatusChip>
                                            <StatusChip tone={riskTone(product.fulfillmentRisk)}>
                                                {product.fulfillmentRisk} risk
                                            </StatusChip>
                                        </div>
                                        <dl className="grid grid-cols-2 gap-3 text-xs">
                                            <div>
                                                <dt className="text-text-tertiary">Campaigns</dt>
                                                <dd className="font-medium text-text-primary">
                                                    {linkedCampaigns.length}
                                                </dd>
                                            </div>
                                            <div>
                                                <dt className="text-text-tertiary">Creatives</dt>
                                                <dd className="font-medium text-text-primary">
                                                    {linkedCreatives.length}
                                                </dd>
                                            </div>
                                        </dl>
                                    </div>
                                </button>
                            );
                        })}
                    </div>
                )}
            </div>

            <ProductDrawer
                product={selected}
                campaigns={campaigns.filter((campaign) => selected?.name === campaign.product)}
                creatives={creatives.filter(
                    (creative) =>
                        selected &&
                        catalogLinkId(selected) === creative.linkedProductId &&
                        !creative.archived,
                )}
                ugcAssets={ugcAssets.filter((asset) => {
                    const campaign = campaigns.find((item) => item.id === asset.campaignId);
                    return selected?.name === campaign?.product && !asset.archived;
                })}
                open={!!selected}
                onOpenChange={(open) => {
                    if (!open) closeProduct();
                }}
                onStartProduction={() => selected && startProductionRun(selected)}
            />
        </AppShell>
    );
}

function ProductCatalogSkeleton() {
    return (
        <div
            role="status"
            aria-live="polite"
            aria-busy="true"
            aria-label="Syncing workspace product catalog"
            className="grid gap-4 md:grid-cols-2 xl:grid-cols-3"
        >
            {Array.from({ length: 6 }).map((_, index) => (
                <div key={index} className="surface-card overflow-hidden">
                    <Skeleton className="aspect-[16/7] rounded-none" />
                    <div className="grid gap-4 p-4">
                        <div className="flex items-start justify-between gap-4">
                            <div className="min-w-0 flex-1">
                                <Skeleton className="h-4 w-3/5" />
                                <Skeleton className="mt-2 h-3 w-2/5" />
                            </div>
                            <Skeleton className="h-4 w-4 rounded-full" />
                        </div>
                        <div className="flex gap-2">
                            <Skeleton className="h-6 w-20 rounded-full" />
                            <Skeleton className="h-6 w-16 rounded-full" />
                        </div>
                        <div className="grid grid-cols-2 gap-3">
                            <Skeleton className="h-9" />
                            <Skeleton className="h-9" />
                        </div>
                    </div>
                </div>
            ))}
        </div>
    );
}

function ProductDrawer({
    product,
    campaigns,
    creatives,
    ugcAssets,
    open,
    onOpenChange,
    onStartProduction,
}: {
    product: CatalogProduct | null;
    campaigns: ReturnType<typeof useAllCampaigns>;
    creatives: CreativeReference[];
    ugcAssets: UgcAsset[];
    open: boolean;
    onOpenChange: (open: boolean) => void;
    onStartProduction: () => void;
}) {
    if (!product) return null;
    const nextAction =
        product.readiness === "Out of stock"
            ? "Resolve inventory before briefing creators."
            : product.fulfillmentRisk === "High"
              ? "Validate fulfillment timing before sample allocation."
              : product.readiness === "Unknown"
                ? "Review the imported product context before briefing creators."
                : creatives.length > 0
                  ? "Start a Production Run from linked creative references."
                  : "Import or link reference creatives before launch.";

    return (
        <RightDrawer
            open={open}
            onOpenChange={onOpenChange}
            title={product.name}
            description={`${product.category} · ${productPrice(product)}`}
            footer={
                <div className="flex items-center justify-between gap-2">
                    <Button variant="ghost" onClick={() => onOpenChange(false)}>
                        Close
                    </Button>
                    <Button onClick={onStartProduction}>
                        <Sparkles className="h-4 w-4" />
                        Start production run
                    </Button>
                </div>
            }
        >
            <div className="flex flex-col gap-5">
                <DemoMediaTile
                    mediaUrl={product.imageUrl}
                    mediaKind={product.imageUrl ? "image" : undefined}
                    alt={product.imageAlt}
                    seed={product.colorSeed}
                    label={product.name}
                    badges={[product.category]}
                    aspect="16 / 8"
                    className="rounded-md"
                />
                <div className="flex flex-wrap gap-2">
                    <StatusChip tone={readinessTone(product.readiness)} dot>
                        {product.readiness}
                    </StatusChip>
                    <StatusChip tone={riskTone(product.fulfillmentRisk)}>
                        {product.fulfillmentRisk} fulfillment risk
                    </StatusChip>
                </div>
                {product.description || product.brand || product.sourceUrl ? (
                    <SurfaceCard padding="sm" className="space-y-2 bg-surface-soft">
                        {product.brand ? (
                            <p className="text-sm text-text-primary">
                                <span className="text-text-tertiary">Brand:</span> {product.brand}
                            </p>
                        ) : null}
                        {product.description ? (
                            <p className="whitespace-pre-wrap text-sm text-text-secondary">
                                {product.description}
                            </p>
                        ) : null}
                        {product.sourceUrl ? (
                            <a
                                href={product.sourceUrl}
                                target="_blank"
                                rel="noreferrer"
                                className="block truncate text-xs text-primary hover:underline"
                            >
                                {product.sourceUrl}
                            </a>
                        ) : null}
                    </SurfaceCard>
                ) : null}
                <SurfaceCard padding="sm" className="bg-surface-soft">
                    <p className="text-xs font-semibold uppercase text-text-tertiary">
                        Suggested next action
                    </p>
                    <p className="mt-1 text-sm text-text-primary">{nextAction}</p>
                </SurfaceCard>
                <Section title="Linked campaigns" icon={Megaphone}>
                    {campaigns.length ? (
                        campaigns.map((campaign) => (
                            <div
                                key={campaign.id}
                                className="flex items-center justify-between gap-3 rounded-md border border-hairline bg-surface px-3 py-2 text-sm"
                            >
                                <div className="min-w-0">
                                    <p className="truncate font-medium text-text-primary">
                                        {campaign.name}
                                    </p>
                                    <p className="text-xs text-text-tertiary">
                                        {campaign.nextAction}
                                    </p>
                                </div>
                                <StatusChip tone={campaign.status === "Live" ? "ok" : "info"}>
                                    {campaign.status}
                                </StatusChip>
                            </div>
                        ))
                    ) : (
                        <p className="text-sm text-text-secondary">
                            No active campaign is linked to this product yet.
                        </p>
                    )}
                </Section>
                <Section title="Linked creatives" icon={Images}>
                    {creatives.length ? (
                        creatives.slice(0, 5).map((creative) => (
                            <div
                                key={creative.id}
                                className="rounded-md border border-hairline bg-surface px-3 py-2 text-sm"
                            >
                                <p className="truncate font-medium text-text-primary">
                                    {creative.title}
                                </p>
                                <p className="text-xs text-text-tertiary">
                                    {creative.angle} · {creative.brandOrCreator}
                                </p>
                            </div>
                        ))
                    ) : (
                        <p className="text-sm text-text-secondary">
                            Link creative references to improve adaptation quality.
                        </p>
                    )}
                </Section>
                <Section title="Linked UGC" icon={Video}>
                    {ugcAssets.length ? (
                        ugcAssets.slice(0, 3).map((asset) => {
                            const creator = seedCreators.find(
                                (item) => item.id === asset.creatorId,
                            );
                            return (
                                <div
                                    key={asset.id}
                                    className="grid grid-cols-[88px_minmax(0,1fr)] gap-3 rounded-md border border-hairline bg-surface p-2.5 text-sm"
                                >
                                    <DemoMediaTile
                                        mediaUrl={asset.mediaUrl}
                                        mediaKind="video"
                                        posterUrl={asset.posterUrl}
                                        seed={asset.thumbSeed}
                                        label={asset.objective}
                                        badges={[`${asset.durationSec}s`]}
                                        aspect={asset.mediaAspectRatio ?? "3 / 2"}
                                        fit={
                                            asset.mediaAspectRatio === "9:16" ? "contain" : "cover"
                                        }
                                        className="rounded-md bg-black"
                                    />
                                    <div className="min-w-0">
                                        <p className="line-clamp-2 font-medium text-text-primary">
                                            {asset.title}
                                        </p>
                                        <p className="mt-0.5 text-xs text-text-tertiary">
                                            {creator?.handle ?? "Creator"} · v
                                            {asset.submissionVersion}
                                        </p>
                                        <StatusChip
                                            tone={asset.decision === "spark-ready" ? "ok" : "info"}
                                        >
                                            {asset.decision.replace(/-/g, " ")}
                                        </StatusChip>
                                    </div>
                                </div>
                            );
                        })
                    ) : (
                        <p className="text-sm text-text-secondary">
                            Upload creator drafts to review product fit and Spark readiness.
                        </p>
                    )}
                </Section>
            </div>
        </RightDrawer>
    );
}

function Section({
    title,
    icon: Icon,
    children,
}: {
    title: string;
    icon: LucideIcon;
    children: ReactNode;
}) {
    return (
        <section>
            <div className="mb-2 flex items-center gap-2">
                <Icon className="h-4 w-4 text-text-tertiary" />
                <h3 className="text-sm font-semibold text-text-primary">{title}</h3>
            </div>
            <div className="space-y-2">{children}</div>
        </section>
    );
}

function readinessTone(readiness: CatalogReadiness) {
    if (readiness === "Ready") return "ok";
    if (readiness === "Setup needed") return "warn";
    if (readiness === "Unknown") return "neutral";
    return "destructive";
}

function riskTone(risk: CatalogRisk) {
    if (risk === "Low") return "ok";
    if (risk === "Medium") return "warn";
    if (risk === "Unknown") return "neutral";
    return "destructive";
}

function catalogLinkId(product: CatalogProduct) {
    return product.localProductId ?? product.id;
}

function productPrice(product: CatalogProduct) {
    if (product.price === null) return "Price unknown";
    const currency = product.currency?.trim().toUpperCase();
    if (currency && /^[A-Z]{3}$/.test(currency)) {
        try {
            return new Intl.NumberFormat(undefined, {
                style: "currency",
                currency,
                maximumFractionDigits: currency === "VND" ? 0 : 2,
            }).format(product.price);
        } catch {
            // Fall through to a currency-neutral value for unknown ISO codes.
        }
    }
    const value = new Intl.NumberFormat(undefined, {
        maximumFractionDigits: 2,
    }).format(product.price);
    return `${value} (currency unknown)`;
}
