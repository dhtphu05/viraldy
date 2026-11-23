import { useMutation, useQuery } from "@tanstack/react-query";
import { useNavigate } from "@tanstack/react-router";
import { useState, type ReactNode } from "react";
import { Loader2, Search, ShieldCheck } from "lucide-react";

import { Button } from "@/shared/ui/button";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
} from "@/shared/ui/dialog";
import { SurfaceCard } from "@/shared/ui/surface-card";
import {
    analyzeCreativeAsset,
    attachCreativeProduct,
    createBatchReview,
    generateCreativeDirections,
    getTikTokSource,
    getTikTokMediaUrl,
    getCreativeAssetIntelligence,
    saveTikTokReference,
    searchTikTokAds,
    type TikTokAdResult,
} from "@/shared/api/tiktok-commercial-content";
import { apiGet } from "@/shared/api/client";
import { listProducts, type Product } from "@/shared/api/products";
import { toast } from "sonner";

type Board = { id: string; name: string };

function getDefaultTikTokDateRange() {
    const today = new Date();
    const yesterday = new Date(today);
    yesterday.setDate(today.getDate() - 1);
    const formatDate = (value: Date) =>
        [
            value.getFullYear(),
            String(value.getMonth() + 1).padStart(2, "0"),
            String(value.getDate()).padStart(2, "0"),
        ].join("-");
    return {
        min: `${today.getFullYear()}-01-01`,
        max: formatDate(yesterday),
    };
}

export function TikTokSearchPanel({ workspaceId }: { workspaceId: string | undefined }) {
    const navigate = useNavigate();
    const defaultDateRange = getDefaultTikTokDateRange();
    const [source, setSource] = useState<"all" | "tiktok">("tiktok");
    const [term, setTerm] = useState("");
    const [searchType, setSearchType] = useState<"exact_phrase" | "fuzzy_phrase">("fuzzy_phrase");
    const [country, setCountry] = useState("");
    const [minDate, setMinDate] = useState(defaultDateRange.min);
    const [maxDate, setMaxDate] = useState(defaultDateRange.max);
    const [minReach, setMinReach] = useState("");
    const [maxReach, setMaxReach] = useState("");
    const [cursor, setCursor] = useState<string | undefined>();
    const [results, setResults] = useState<TikTokAdResult[]>([]);
    const [detailItem, setDetailItem] = useState<TikTokAdResult | null>(null);
    const [adaptAssetId, setAdaptAssetId] = useState<string | null>(null);
    const [adaptProductId, setAdaptProductId] = useState<string>("");
    const [selectedSourceIds, setSelectedSourceIds] = useState<Set<string>>(new Set());

    const boards = useQuery({
        queryKey: ["reference-boards", workspaceId],
        queryFn: () => apiGet<Board[]>(`/workspaces/${workspaceId}/reference-boards`),
        enabled: Boolean(workspaceId),
        staleTime: 60_000,
    });
    const products = useQuery({
        queryKey: ["products", workspaceId, "market-adaptation"],
        queryFn: () => listProducts(workspaceId!),
        enabled: Boolean(workspaceId),
        staleTime: 60_000,
    });
    const search = useMutation({
        mutationFn: (requestCursor?: string) => {
            if (!workspaceId) throw new Error("Choose a workspace first.");
            return searchTikTokAds(workspaceId, {
                search_term: term.trim() || undefined,
                search_type: searchType,
                country_code: country.trim().toUpperCase() || undefined,
                date_range: minDate && maxDate ? { min: minDate, max: maxDate } : undefined,
                max_count: 20,
                reach_range:
                    minReach || maxReach
                        ? { min: minReach || undefined, max: maxReach || undefined }
                        : undefined,
                cursor: requestCursor,
            });
        },
        onSuccess: (data, requestCursor) => {
            setResults((previous) =>
                requestCursor ? [...previous, ...data.results] : data.results,
            );
            setCursor(data.page.next_cursor ?? undefined);
        },
        onError: (error) =>
            toast.error(error instanceof Error ? error.message : "TikTok search failed"),
    });
    const analyze = useMutation({
        mutationFn: async (item: TikTokAdResult) => {
            if (!workspaceId) throw new Error("Choose a workspace first.");
            if (item.media_state === "METADATA_ONLY") {
                throw new Error(
                    "Media analysis is unavailable while this result is metadata-only.",
                );
            }
            if (item.media_state === "DIRECT_STREAM_AVAILABLE") {
                throw new Error("Save this reference first to persist media before analysis.");
            }
            if (!boards.data?.[0]) throw new Error("Save a reference board first.");
            const saved = await saveTikTokReference(workspaceId, item.source_id, {
                board_id: boards.data[0].id,
            });
            return analyzeCreativeAsset(workspaceId, saved.asset_id);
        },
        onSuccess: () =>
            toast.success("Analysis queued. The evidence state will update when ready."),
        onError: (error) => toast.error(error instanceof Error ? error.message : "Analysis failed"),
    });
    const save = useMutation({
        mutationFn: ({ sourceId }: { sourceId: string }) => {
            if (!workspaceId || !boards.data?.[0])
                throw new Error("No reference board is available.");
            return saveTikTokReference(workspaceId, sourceId, { board_id: boards.data[0].id });
        },
        onSuccess: () => toast.success("Reference saved; media import is processing."),
        onError: (error) =>
            toast.error(error instanceof Error ? error.message : "Reference save failed"),
    });
    const adapt = useMutation({
        mutationFn: async ({ assetId, productId }: { assetId: string; productId: string }) => {
            if (!workspaceId) throw new Error("Choose a workspace first.");
            const product = products.data?.find((item) => item.id === productId);
            await attachCreativeProduct(workspaceId, assetId, productId);
            return generateCreativeDirections(workspaceId, assetId, {
                product_id: productId,
                objective: "tiktok_shop_affiliate_test",
                target_market: product?.product_context.identity.market ?? product?.market ?? "US",
            });
        },
        onSuccess: (result) => {
            const adaptationId = String(result.id ?? result.adaptation_id ?? "");
            if (!adaptationId) {
                toast.error("Directions were created but the adaptation ID was missing.");
                return;
            }
            toast.success("Three product-specific directions are ready.");
            void navigate({ to: "/creative-directions/$adaptationId", params: { adaptationId } });
        },
        onError: (error) =>
            toast.error(error instanceof Error ? error.message : "Adaptation failed"),
    });
    const batch = useMutation({
        mutationFn: async () => {
            if (!workspaceId || !boards.data?.[0]) throw new Error("Save a reference board first.");
            const selected = results.filter((item) => selectedSourceIds.has(item.source_id));
            const saved = [] as Array<{ asset_id: string }>;
            for (const item of selected) {
                const result = await saveTikTokReference(workspaceId, item.source_id, {
                    board_id: boards.data[0].id,
                });
                saved.push({ asset_id: result.asset_id });
            }
            return createBatchReview(workspaceId, {
                objective: "tiktok_shop_affiliate_test",
                asset_ids: saved.map((item) => item.asset_id),
            });
        },
        onSuccess: (data) => {
            setSelectedSourceIds(new Set());
            void navigate({ to: "/batch-reviews/$batchId", params: { batchId: data.id } });
        },
        onError: (error) =>
            toast.error(error instanceof Error ? error.message : "Batch creation failed"),
    });

    function runSearch() {
        setCursor(undefined);
        search.mutate(undefined);
    }

    return (
        <SurfaceCard padding="lg" className="min-w-0 overflow-hidden bg-primary/[0.03] shadow-sm">
            <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                    <div className="flex items-center gap-2 text-sm font-semibold text-text-primary">
                        <ShieldCheck className="h-4 w-4 text-primary" />
                        Public commercial signals
                    </div>
                    <p className="mt-1 text-xs text-text-secondary">
                        Official TikTok data. This is not seller sales performance, GMV, ROAS, or a
                        winner prediction.
                    </p>
                </div>
                <div className="flex shrink-0 whitespace-nowrap rounded-lg bg-surface-soft p-1 text-xs">
                    <button
                        type="button"
                        className="rounded-md px-2 py-1 text-text-tertiary"
                        onClick={() => setSource("all")}
                    >
                        All sources
                    </button>
                    <button
                        type="button"
                        className="rounded-md bg-surface-soft px-2 py-1 font-medium text-text-primary"
                        onClick={() => setSource("tiktok")}
                    >
                        TikTok Official
                    </button>
                </div>
            </div>
            {source === "tiktok" && (
                <>
                    <div className="mt-4 grid min-w-0 gap-3 sm:grid-cols-2 xl:grid-cols-4">
                        <input
                            className="h-9 min-w-0 w-full rounded-lg border border-control-border bg-surface px-3 text-sm"
                            placeholder="Search ad title or phrase"
                            value={term}
                            onChange={(event) => setTerm(event.target.value)}
                            maxLength={50}
                        />
                        <select
                            className="h-9 min-w-0 w-full rounded-lg border border-control-border bg-surface px-2 text-sm"
                            value={searchType}
                            onChange={(event) =>
                                setSearchType(event.target.value as typeof searchType)
                            }
                        >
                            <option value="fuzzy_phrase">Fuzzy</option>
                            <option value="exact_phrase">Exact</option>
                        </select>
                        <input
                            className="h-9 min-w-0 w-full rounded-lg border border-control-border bg-surface px-3 text-sm uppercase"
                            placeholder="Country (EU/EEA)"
                            title="TikTok Commercial Content supports EU/EEA, GB, and CH country filters"
                            value={country}
                            onChange={(event) => setCountry(event.target.value)}
                            maxLength={2}
                        />
                        <input
                            className="h-9 min-w-0 w-full rounded-lg border border-control-border bg-surface px-3 text-sm"
                            type="date"
                            value={minDate}
                            onChange={(event) => setMinDate(event.target.value)}
                        />
                        <input
                            className="h-9 min-w-0 w-full rounded-lg border border-control-border bg-surface px-3 text-sm"
                            type="date"
                            value={maxDate}
                            onChange={(event) => setMaxDate(event.target.value)}
                        />
                        <input
                            className="h-9 min-w-0 w-full rounded-lg border border-control-border bg-surface px-2 text-sm"
                            placeholder="Min reach (e.g. 10K)"
                            value={minReach}
                            onChange={(event) => setMinReach(event.target.value.toUpperCase())}
                        />
                        <input
                            className="h-9 min-w-0 w-full rounded-lg border border-control-border bg-surface px-2 text-sm"
                            placeholder="Max reach"
                            value={maxReach}
                            onChange={(event) => setMaxReach(event.target.value.toUpperCase())}
                        />
                        <Button
                            size="sm"
                            className="w-full"
                            onClick={runSearch}
                            disabled={!workspaceId || !minDate || !maxDate || search.isPending}
                        >
                            {search.isPending ? <Loader2 className="animate-spin" /> : <Search />}
                            Search
                        </Button>
                    </div>
                    <p className="mt-2 text-[11px] text-text-tertiary">
                        Official country coverage: EU/EEA, GB, and CH. Unsupported markets are
                        rejected before a provider request.
                    </p>
                    {results.length === 0 && !search.isPending && (
                        <p className="mt-4 text-sm text-text-tertiary">
                            Search official public commercial content to add market references.
                        </p>
                    )}
                    <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                        {results.map((item) => {
                            const videoCount = item.ad.videos.length;
                            const imageCount = item.ad.image_count ?? item.ad.image_urls.length;
                            const canPreview =
                                item.media_state === "DIRECT_STREAM_AVAILABLE" ||
                                item.media_state === "READY";
                            const media =
                                canPreview && (videoCount > 0 || imageCount > 0)
                                    ? getTikTokMediaUrl(workspaceId!, item.source_id)
                                    : undefined;
                            return (
                                <div
                                    key={item.source_id}
                                    className="overflow-hidden rounded-2xl bg-surface shadow-sm"
                                >
                                    <div className="mx-auto aspect-[9/16] w-full max-w-[300px] overflow-hidden bg-black">
                                        {media ? (
                                            videoCount > 0 ? (
                                                <video
                                                    src={media}
                                                    muted
                                                    autoPlay
                                                    loop
                                                    playsInline
                                                    controls
                                                    preload="auto"
                                                    aria-label={`TikTok ad ${item.ad.id} video preview`}
                                                    className="h-full w-full bg-black object-contain"
                                                />
                                            ) : (
                                                <img
                                                    src={media}
                                                    alt={item.ad.title ?? `TikTok ad ${item.ad.id}`}
                                                    loading="lazy"
                                                    className="h-full w-full bg-surface-soft object-contain"
                                                />
                                            )
                                        ) : (
                                            <div className="flex h-full items-center justify-center bg-surface-soft px-4 text-center text-xs text-text-tertiary">
                                                {videoCount + imageCount > 0
                                                    ? item.media_state === "METADATA_ONLY"
                                                        ? "Media preview unavailable until this reference is saved."
                                                        : "Media preview unavailable"
                                                    : "TikTok did not return media for this ad."}
                                            </div>
                                        )}
                                    </div>
                                    <div className="space-y-2 p-3">
                                        <label className="flex items-center gap-2 text-xs text-text-secondary">
                                            <input
                                                type="checkbox"
                                                checked={selectedSourceIds.has(item.source_id)}
                                                onChange={() =>
                                                    setSelectedSourceIds((previous) => {
                                                        const next = new Set(previous);
                                                        if (next.has(item.source_id))
                                                            next.delete(item.source_id);
                                                        else next.add(item.source_id);
                                                        return next;
                                                    })
                                                }
                                            />
                                            Include in batch review
                                        </label>
                                        <div className="flex flex-wrap gap-1.5 text-[10px] font-semibold tracking-wide">
                                            <span className="rounded-full bg-primary/10 px-2 py-1 text-primary">
                                                TIKTOK OFFICIAL
                                            </span>
                                            <span className="rounded-full bg-surface-soft px-2 py-1 text-text-secondary">
                                                MARKET SIGNAL
                                            </span>
                                            <span className="rounded-full bg-surface-soft px-2 py-1 text-text-secondary">
                                                PUBLIC COMMERCIAL DATA
                                            </span>
                                        </div>
                                        <p className="line-clamp-2 text-sm font-medium text-text-primary">
                                            {item.ad.title ?? `TikTok ad ${item.ad.id}`}
                                        </p>
                                        <p className="text-xs text-text-secondary">
                                            {item.advertiser?.business_name ??
                                                "Advertiser unavailable"}{" "}
                                            · {item.ad.reach ?? "Reach unavailable"}
                                        </p>
                                        <div className="grid grid-cols-2 gap-x-3 gap-y-1 text-[11px] text-text-tertiary">
                                            <CompactMeta label="Status" value={item.ad.status} />
                                            <CompactMeta
                                                label="Shown"
                                                value={formatDateRange(
                                                    item.ad.first_shown_date,
                                                    item.ad.last_shown_date,
                                                )}
                                            />
                                            <CompactMeta
                                                label="Media"
                                                value={`${videoCount} video · ${imageCount} image`}
                                            />
                                            <CompactMeta
                                                label="Analysis"
                                                value={item.intelligence_status}
                                            />
                                        </div>
                                        <div className="flex gap-2">
                                            <Button
                                                size="sm"
                                                variant="secondary"
                                                onClick={() => setDetailItem(item)}
                                            >
                                                View details
                                            </Button>
                                            {item.asset_id && (
                                                <Button
                                                    size="sm"
                                                    variant="secondary"
                                                    onClick={() => analyze.mutate(item)}
                                                    disabled={
                                                        analyze.isPending ||
                                                        item.media_state === "METADATA_ONLY" ||
                                                        item.media_state ===
                                                            "DIRECT_STREAM_AVAILABLE"
                                                    }
                                                >
                                                    {item.media_state === "METADATA_ONLY"
                                                        ? "Media unavailable"
                                                        : item.media_state ===
                                                            "DIRECT_STREAM_AVAILABLE"
                                                          ? "Save to analyze"
                                                          : "Analyze pattern"}
                                                </Button>
                                            )}
                                            {item.asset_id && (
                                                <Button
                                                    size="sm"
                                                    variant="secondary"
                                                    onClick={() => {
                                                        setAdaptAssetId(
                                                            adaptAssetId === item.asset_id
                                                                ? null
                                                                : item.asset_id!,
                                                        );
                                                        setAdaptProductId(
                                                            products.data?.[0]?.id ?? "",
                                                        );
                                                    }}
                                                    disabled={!products.data?.length}
                                                >
                                                    Adapt to my product
                                                </Button>
                                            )}
                                            <Button
                                                size="sm"
                                                onClick={() =>
                                                    save.mutate({ sourceId: item.source_id })
                                                }
                                                disabled={save.isPending || !boards.data?.length}
                                            >
                                                Save reference
                                            </Button>
                                        </div>
                                        {adaptAssetId === item.asset_id && (
                                            <div className="mt-2 flex flex-wrap items-center gap-2 rounded-xl bg-surface-soft p-2">
                                                <label
                                                    className="text-xs text-text-secondary"
                                                    htmlFor={`adapt-product-${item.asset_id}`}
                                                >
                                                    Product
                                                </label>
                                                <select
                                                    id={`adapt-product-${item.asset_id}`}
                                                    className="h-8 min-w-48 rounded-md border border-control-border bg-surface px-2 text-xs"
                                                    value={adaptProductId}
                                                    onChange={(event) =>
                                                        setAdaptProductId(event.target.value)
                                                    }
                                                >
                                                    {products.data?.map((product: Product) => (
                                                        <option key={product.id} value={product.id}>
                                                            {product.name}
                                                        </option>
                                                    ))}
                                                </select>
                                                <Button
                                                    size="sm"
                                                    onClick={() =>
                                                        adapt.mutate({
                                                            assetId: item.asset_id!,
                                                            productId: adaptProductId,
                                                        })
                                                    }
                                                    disabled={!adaptProductId || adapt.isPending}
                                                >
                                                    {adapt.isPending
                                                        ? "Generating…"
                                                        : "Generate 3 directions"}
                                                </Button>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                    {selectedSourceIds.size > 0 && (
                        <div className="mt-4 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-primary/20 bg-primary/[0.04] p-3">
                            <p className="text-sm text-text-secondary">
                                {selectedSourceIds.size} public creatives selected. They will be
                                saved as workspace references before review.
                            </p>
                            <Button
                                size="sm"
                                onClick={() => batch.mutate()}
                                disabled={batch.isPending || selectedSourceIds.size > 25}
                            >
                                {batch.isPending ? "Preparing batch…" : "Review selected batch"}
                            </Button>
                        </div>
                    )}
                    {cursor && (
                        <Button
                            className="mt-4"
                            variant="secondary"
                            size="sm"
                            onClick={() => search.mutate(cursor)}
                            disabled={search.isPending}
                        >
                            Load more
                        </Button>
                    )}
                    <Dialog
                        open={Boolean(detailItem)}
                        onOpenChange={(open) => !open && setDetailItem(null)}
                    >
                        <DialogContent className="flex max-h-[calc(100dvh-2rem)] max-w-[min(960px,calc(100vw-2rem))] flex-col gap-0 overflow-hidden border-0 p-0">
                            {detailItem && (
                                <>
                                    <DialogHeader className="shrink-0 border-b border-control-border/60 bg-surface px-6 pb-4 pt-6 pr-12">
                                        <div className="flex flex-wrap items-start justify-between gap-3">
                                            <div className="min-w-0">
                                                <DialogTitle className="truncate text-xl">
                                                    {detailItem.ad.title ??
                                                        `TikTok ad ${detailItem.ad.id}`}
                                                </DialogTitle>
                                                <DialogDescription className="mt-1">
                                                    {detailItem.advertiser?.business_name ??
                                                        "Advertiser unavailable"}{" "}
                                                    · Official TikTok market reference
                                                </DialogDescription>
                                            </div>
                                            <div className="flex shrink-0 flex-wrap gap-1.5 text-[10px] font-semibold tracking-wide">
                                                <span className="rounded-full bg-primary/10 px-2 py-1 text-primary">
                                                    TIKTOK OFFICIAL
                                                </span>
                                                <span className="rounded-full bg-surface-soft px-2 py-1 text-text-secondary">
                                                    MARKET SIGNAL
                                                </span>
                                            </div>
                                        </div>
                                    </DialogHeader>
                                    <div className="min-h-0 overflow-y-auto px-6 pb-6 pt-2">
                                        <TikTokDetails
                                            workspaceId={workspaceId}
                                            item={detailItem}
                                            inModal
                                        />
                                    </div>
                                </>
                            )}
                        </DialogContent>
                    </Dialog>
                </>
            )}
        </SurfaceCard>
    );
}

function TikTokDetails({
    workspaceId,
    item,
    inModal = false,
}: {
    workspaceId: string | undefined;
    item: TikTokAdResult;
    inModal?: boolean;
}) {
    const detail = useQuery({
        queryKey: ["tiktok-source", workspaceId, item.source_id],
        queryFn: () => getTikTokSource(workspaceId!, item.source_id),
        enabled: Boolean(workspaceId),
        staleTime: 300_000,
    });
    const intelligence = useQuery({
        queryKey: ["tiktok-asset-intelligence", workspaceId, item.asset_id],
        queryFn: () => getCreativeAssetIntelligence(workspaceId!, item.asset_id!),
        enabled: Boolean(
            workspaceId &&
            item.asset_id &&
            item.intelligence_status &&
            item.intelligence_status !== "NOT_ANALYZED",
        ),
        staleTime: 60_000,
    });
    const data = detail.data ?? item;
    const videoCount = data.ad.videos.length;
    const imageCount = data.ad.image_count ?? data.ad.image_urls.length;
    const mediaCount = videoCount + imageCount;
    const mediaPreviewEnabled =
        data.media_state === "DIRECT_STREAM_AVAILABLE" || data.media_state === "READY";
    const mediaItems = Array.from({ length: mediaCount }, (_, index) => ({
        index,
        type: index < videoCount ? ("video" as const) : ("image" as const),
    }));
    return (
        <div
            className={
                inModal
                    ? "space-y-3 text-xs text-text-secondary"
                    : "mt-3 space-y-3 text-xs text-text-secondary"
            }
        >
            {detail.isPending && (
                <p className="text-text-tertiary">Loading official TikTok details…</p>
            )}
            {detail.isError && (
                <p className="rounded-md bg-amber-500/10 p-2 text-amber-700">
                    Official detail is temporarily unavailable; showing the search response.
                </p>
            )}
            <DetailSection title="Official TikTok metadata">
                <div className="grid gap-x-4 gap-y-2 sm:grid-cols-2">
                    <DetailRow label="Ad ID" value={data.ad.id} />
                    <DetailRow label="Source record" value={data.source_id} />
                    <DetailRow label="First shown" value={data.ad.first_shown_date} />
                    <DetailRow label="Last shown" value={data.ad.last_shown_date} />
                    <DetailRow label="Status" value={data.ad.status} />
                    <DetailRow label="Status statement" value={data.ad.status_statement} />
                    <DetailRow label="Reach" value={data.ad.reach} />
                    <DetailRow label="Media state" value={data.media_state} />
                </div>
            </DetailSection>

            <DetailSection title="Advertiser">
                <div className="grid gap-x-4 gap-y-2 sm:grid-cols-2">
                    <DetailRow label="Business name" value={data.advertiser?.business_name} />
                    <DetailRow label="Business ID" value={data.advertiser?.business_id} />
                    <DetailRow label="Country" value={data.advertiser?.country_code} />
                    <DetailRow label="Paid for by" value={data.advertiser?.paid_for_by} />
                    <DetailRow label="Follower count" value={data.advertiser?.follower_count} />
                    <DetailRow label="Avatar URL" value={data.advertiser?.avatar_url} />
                    <DetailRow label="Profile URL" value={data.advertiser?.profile_url} />
                </div>
            </DetailSection>

            <DetailSection title="Creative and media">
                <div className="grid gap-x-4 gap-y-2 sm:grid-cols-2">
                    <DetailRow label="Title" value={data.ad.title} />
                    <DetailRow label="Call to action" value={data.ad.call_to_action} />
                    <DetailRow
                        label="Advertising objective"
                        value={data.ad.advertising_objective}
                    />
                    <DetailRow label="Video count" value={videoCount} />
                    <DetailRow label="Image count" value={imageCount} />
                    <DetailLink label="External URL" value={data.ad.external_url} />
                </div>
                {mediaItems.length > 0 && mediaPreviewEnabled ? (
                    <div className="mt-3 grid gap-3 sm:grid-cols-2">
                        {mediaItems.map((media) => {
                            const src = getTikTokMediaUrl(
                                workspaceId!,
                                data.source_id,
                                media.index,
                            );
                            return (
                                <div
                                    key={src}
                                    className="aspect-[9/16] w-full max-w-[260px] overflow-hidden rounded-md bg-black"
                                >
                                    {media.type === "video" ? (
                                        <video
                                            src={src}
                                            controls
                                            muted
                                            autoPlay
                                            loop
                                            playsInline
                                            preload="auto"
                                            aria-label={`TikTok ad ${data.ad.id} video ${media.index + 1}`}
                                            className="h-full w-full object-contain"
                                        />
                                    ) : (
                                        <img
                                            src={src}
                                            alt={`${data.ad.title ?? `TikTok ad ${data.ad.id}`} image ${media.index + 1}`}
                                            loading="lazy"
                                            className="h-full w-full bg-surface-soft object-contain"
                                        />
                                    )}
                                </div>
                            );
                        })}
                    </div>
                ) : (
                    <p className="mt-2 rounded-md bg-surface-soft p-2 text-text-tertiary">
                        {mediaCount > 0
                            ? "Media is available after Save reference or when direct preview is enabled."
                            : "No video or image media was returned by TikTok."}
                    </p>
                )}
            </DetailSection>

            <DetailSection title="Targeting and moderation metadata">
                <JsonValue label="Targeting" value={data.ad.targeting_info} />
                <JsonValue label="Moderation" value={data.ad.moderation_metadata} />
            </DetailSection>

            <DetailSection title="Viraldy intelligence">
                <div className="grid gap-x-4 gap-y-2 sm:grid-cols-2">
                    <DetailRow label="Intelligence state" value={data.intelligence_status} />
                    <DetailRow
                        label="Evidence count"
                        value={intelligence.data?.analysis.evidence_count}
                    />
                    <DetailRow
                        label="Creative families"
                        value={intelligence.data?.families.length}
                    />
                    <DetailRow label="Evidence scope" value="Public market observation" />
                </div>
            </DetailSection>

            <p className="rounded-xl bg-primary/[0.05] p-3 text-[11px] text-text-tertiary">
                Platform metadata is a public market signal, not seller sales performance, GMV,
                ROAS, conversion, or a winner prediction. Missing TikTok values remain unavailable.
            </p>
        </div>
    );
}

function CompactMeta({ label, value }: { label: string; value: string | null | undefined }) {
    return (
        <span className="truncate">
            <span className="font-medium text-text-secondary">{label}:</span>{" "}
            {value ?? "Unavailable"}
        </span>
    );
}

function DetailSection({ title, children }: { title: string; children: ReactNode }) {
    return (
        <section className="rounded-xl bg-surface-soft/70 p-4">
            <h4 className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-text-primary">
                {title}
            </h4>
            {children}
        </section>
    );
}

function DetailRow({ label, value }: { label: string; value: unknown }) {
    return (
        <div className="min-w-0">
            <dt className="text-[10px] uppercase tracking-wide text-text-tertiary">{label}</dt>
            <dd className="break-words text-text-primary">{formatDetailValue(value)}</dd>
        </div>
    );
}

function DetailLink({ label, value }: { label: string; value: string | null | undefined }) {
    return (
        <div className="min-w-0">
            <dt className="text-[10px] uppercase tracking-wide text-text-tertiary">{label}</dt>
            <dd className="truncate text-text-primary">
                {value ? (
                    <a
                        href={value}
                        target="_blank"
                        rel="noreferrer"
                        className="text-primary underline-offset-2 hover:underline"
                    >
                        Open external link
                    </a>
                ) : (
                    "Unavailable"
                )}
            </dd>
        </div>
    );
}

function JsonValue({
    label,
    value,
}: {
    label: string;
    value: Record<string, unknown> | null | undefined;
}) {
    return (
        <div className="mb-2 last:mb-0">
            <p className="text-[10px] uppercase tracking-wide text-text-tertiary">{label}</p>
            <pre className="mt-1 max-h-32 overflow-auto whitespace-pre-wrap break-words rounded-md bg-surface p-2 text-[11px] text-text-primary">
                {value ? JSON.stringify(value, null, 2) : "Unavailable"}
            </pre>
        </div>
    );
}

function formatDetailValue(value: unknown) {
    if (value === null || value === undefined || value === "") return "Unavailable";
    if (typeof value === "object") return JSON.stringify(value);
    return String(value);
}

function formatDateRange(first: string | null, last: string | null) {
    if (!first && !last) return "Unavailable";
    return `${first ?? "?"} – ${last ?? "?"}`;
}
