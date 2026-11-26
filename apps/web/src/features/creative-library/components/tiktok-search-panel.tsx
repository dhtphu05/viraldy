import { useMutation, useQuery } from "@tanstack/react-query";
import { useNavigate } from "@tanstack/react-router";
import { useId, useState, type ReactNode } from "react";
import { ChevronDown, Loader2, Search, ShieldCheck } from "lucide-react";

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
    const fieldId = useId();
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
            if (!workspaceId) throw new Error("Chọn workspace trước khi tiếp tục.");
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
            toast.error(
                error instanceof Error ? error.message : "Chưa tìm được video. Bạn hãy thử lại.",
            ),
    });
    const analyze = useMutation({
        mutationFn: async (item: TikTokAdResult) => {
            if (!workspaceId) throw new Error("Chọn workspace trước khi tiếp tục.");
            if (item.media_state === "METADATA_ONLY") {
                throw new Error("Video này mới có thông tin, chưa có file để phân tích.");
            }
            if (item.media_state === "DIRECT_STREAM_AVAILABLE") {
                throw new Error("Lưu tham khảo trước để chuẩn bị file phân tích.");
            }
            if (!boards.data?.[0]) throw new Error("Tạo bộ sưu tập tham khảo trước khi tiếp tục.");
            const saved = await saveTikTokReference(workspaceId, item.source_id, {
                board_id: boards.data[0].id,
            });
            return analyzeCreativeAsset(workspaceId, saved.asset_id);
        },
        onSuccess: () =>
            toast.success("Đã gửi yêu cầu phân tích. Kết quả sẽ cập nhật khi sẵn sàng."),
        onError: (error) =>
            toast.error(
                error instanceof Error
                    ? error.message
                    : "Chưa phân tích được video. Bạn hãy thử lại.",
            ),
    });
    const save = useMutation({
        mutationFn: ({ sourceId }: { sourceId: string }) => {
            if (!workspaceId || !boards.data?.[0])
                throw new Error("Chưa có bộ sưu tập để lưu tham khảo.");
            return saveTikTokReference(workspaceId, sourceId, { board_id: boards.data[0].id });
        },
        onSuccess: () =>
            toast.success("Đã lưu tham khảo. Hệ thống đang chuẩn bị file trong workspace."),
        onError: (error) =>
            toast.error(
                error instanceof Error
                    ? error.message
                    : "Chưa lưu được tham khảo. Bạn hãy thử lại.",
            ),
    });
    const adapt = useMutation({
        mutationFn: async ({ assetId, productId }: { assetId: string; productId: string }) => {
            if (!workspaceId) throw new Error("Chọn workspace trước khi tiếp tục.");
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
                toast.error("Đã tạo gợi ý nhưng chưa mở được kết quả. Bạn hãy thử lại.");
                return;
            }
            toast.success("Đã có 3 hướng video cho sản phẩm của bạn.");
            void navigate({ to: "/creative-directions/$adaptationId", params: { adaptationId } });
        },
        onError: (error) =>
            toast.error(
                error instanceof Error
                    ? error.message
                    : "Chưa tạo được gợi ý cho sản phẩm. Bạn hãy thử lại.",
            ),
    });
    const batch = useMutation({
        mutationFn: async () => {
            if (!workspaceId || !boards.data?.[0])
                throw new Error("Tạo bộ sưu tập tham khảo trước khi tiếp tục.");
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
            toast.error(
                error instanceof Error
                    ? error.message
                    : "Chưa chuẩn bị được nhóm video. Bạn hãy thử lại.",
            ),
    });

    function runSearch() {
        setCursor(undefined);
        search.mutate(undefined);
    }

    return (
        <SurfaceCard
            padding="lg"
            className="min-w-0 overflow-hidden rounded-3xl border-0 bg-surface shadow-sm [&_button]:min-h-11 [&_button]:whitespace-normal"
        >
            <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                    <div className="flex items-center gap-2 text-sm font-semibold text-text-primary">
                        <ShieldCheck className="h-4 w-4 text-primary" />
                        Tìm video trên TikTok
                    </div>
                    <p className="mt-1 text-xs text-text-secondary">
                        Khám phá quảng cáo công khai để tham khảo cách làm video. Dữ liệu này không
                        phản ánh doanh số, ROAS hay dự đoán video sẽ bán tốt.
                    </p>
                    <p className="mt-2 text-xs leading-relaxed text-text-secondary">
                        Video lưu từ TikTok được xử lý trong workspace, chưa đồng bộ vào bộ sưu tập
                        trên trình duyệt này.
                    </p>
                </div>
                <div className="flex shrink-0 whitespace-nowrap rounded-lg bg-surface-soft p-1 text-xs">
                    <button
                        type="button"
                        className={`min-h-11 rounded-lg px-3 py-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${source === "all" ? "bg-primary-soft font-medium text-primary" : "text-text-secondary"}`}
                        aria-pressed={source === "all"}
                        onClick={() => setSource("all")}
                    >
                        Tất cả nguồn
                    </button>
                    <button
                        type="button"
                        className={`min-h-11 rounded-lg px-3 py-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${source === "tiktok" ? "bg-primary-soft font-medium text-primary" : "text-text-secondary"}`}
                        aria-pressed={source === "tiktok"}
                        onClick={() => setSource("tiktok")}
                    >
                        TikTok chính thức
                    </button>
                </div>
            </div>
            {source === "tiktok" && (
                <>
                    <div className="mt-5 grid min-w-0 gap-4 sm:grid-cols-2 xl:grid-cols-4">
                        <div className="space-y-2">
                            <label
                                htmlFor={`${fieldId}-term`}
                                className="text-sm font-medium text-text-primary"
                            >
                                Từ khóa
                            </label>
                            <input
                                id={`${fieldId}-term`}
                                className="h-11 min-w-0 w-full rounded-xl border-0 bg-surface-soft px-3 text-base focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring sm:text-sm"
                                placeholder="Tên sản phẩm hoặc câu mở đầu"
                                value={term}
                                onChange={(event) => setTerm(event.target.value)}
                                maxLength={50}
                            />
                        </div>
                        <div className="space-y-2">
                            <label
                                htmlFor={`${fieldId}-market`}
                                className="text-sm font-medium text-text-primary"
                            >
                                Thị trường · mã quốc gia
                            </label>
                            <input
                                id={`${fieldId}-market`}
                                className="h-11 min-w-0 w-full rounded-xl border-0 bg-surface-soft px-3 text-base uppercase placeholder:normal-case focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring sm:text-sm"
                                placeholder="Ví dụ: DE, FR, GB"
                                title="Hỗ trợ EU/EEA, Anh (GB) và Thụy Sĩ (CH)"
                                value={country}
                                onChange={(event) => setCountry(event.target.value)}
                                maxLength={2}
                                aria-describedby={`${fieldId}-coverage`}
                            />
                        </div>
                        <div className="space-y-2">
                            <label
                                htmlFor={`${fieldId}-from`}
                                className="text-sm font-medium text-text-primary"
                            >
                                Từ ngày
                            </label>
                            <input
                                id={`${fieldId}-from`}
                                className="h-11 min-w-0 w-full rounded-xl border-0 bg-surface-soft px-3 text-base focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring sm:text-sm"
                                type="date"
                                value={minDate}
                                onChange={(event) => setMinDate(event.target.value)}
                            />
                        </div>
                        <div className="space-y-2">
                            <label
                                htmlFor={`${fieldId}-to`}
                                className="text-sm font-medium text-text-primary"
                            >
                                Đến ngày
                            </label>
                            <input
                                id={`${fieldId}-to`}
                                className="h-11 min-w-0 w-full rounded-xl border-0 bg-surface-soft px-3 text-base focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring sm:text-sm"
                                type="date"
                                value={maxDate}
                                onChange={(event) => setMaxDate(event.target.value)}
                            />
                        </div>
                    </div>
                    <p
                        id={`${fieldId}-coverage`}
                        className="mt-3 text-xs leading-relaxed text-text-secondary"
                    >
                        Nguồn này hỗ trợ EU/EEA, Anh (GB) và Thụy Sĩ (CH). Các thị trường khác chưa
                        được hỗ trợ.
                    </p>
                    <details className="group mt-3 rounded-2xl bg-surface-soft px-4">
                        <summary className="flex min-h-11 cursor-pointer items-center rounded-lg text-sm font-medium text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
                            Bộ lọc nâng cao
                            <ChevronDown
                                className="ml-auto size-4 transition-transform group-open:rotate-180 motion-reduce:transition-none"
                                aria-hidden="true"
                            />
                        </summary>
                        <div className="grid gap-4 pb-4 sm:grid-cols-3">
                            <div className="space-y-2">
                                <label
                                    htmlFor={`${fieldId}-match`}
                                    className="text-sm text-text-primary"
                                >
                                    Cách khớp từ khóa
                                </label>
                                <select
                                    id={`${fieldId}-match`}
                                    className="h-11 min-w-0 w-full rounded-xl border-0 bg-surface px-3 text-base focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring sm:text-sm"
                                    value={searchType}
                                    onChange={(event) =>
                                        setSearchType(event.target.value as typeof searchType)
                                    }
                                >
                                    <option value="fuzzy_phrase">Gần đúng</option>
                                    <option value="exact_phrase">Đúng cụm từ</option>
                                </select>
                            </div>
                            <div className="space-y-2">
                                <label
                                    htmlFor={`${fieldId}-min-reach`}
                                    className="text-sm text-text-primary"
                                >
                                    Tiếp cận tối thiểu
                                </label>
                                <input
                                    id={`${fieldId}-min-reach`}
                                    className="h-11 min-w-0 w-full rounded-xl border-0 bg-surface px-3 text-base focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring sm:text-sm"
                                    placeholder="Ví dụ: 10K"
                                    value={minReach}
                                    onChange={(event) =>
                                        setMinReach(event.target.value.toUpperCase())
                                    }
                                />
                            </div>
                            <div className="space-y-2">
                                <label
                                    htmlFor={`${fieldId}-max-reach`}
                                    className="text-sm text-text-primary"
                                >
                                    Tiếp cận tối đa
                                </label>
                                <input
                                    id={`${fieldId}-max-reach`}
                                    className="h-11 min-w-0 w-full rounded-xl border-0 bg-surface px-3 text-base focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring sm:text-sm"
                                    placeholder="Không giới hạn"
                                    value={maxReach}
                                    onChange={(event) =>
                                        setMaxReach(event.target.value.toUpperCase())
                                    }
                                />
                            </div>
                        </div>
                    </details>
                    <div className="mt-4 flex justify-end">
                        <Button
                            className="min-h-11 w-full sm:w-auto"
                            onClick={runSearch}
                            disabled={!workspaceId || !minDate || !maxDate || search.isPending}
                        >
                            {search.isPending ? (
                                <Loader2 className="animate-spin motion-reduce:animate-none" />
                            ) : (
                                <Search />
                            )}
                            {search.isPending ? "Đang tìm video…" : "Tìm video"}
                        </Button>
                    </div>
                    {results.length === 0 && !search.isPending && (
                        <p className="mt-4 text-sm text-text-tertiary">
                            Nhập từ khóa và chọn khoảng ngày để tìm video tham khảo trên TikTok.
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
                                                    playsInline
                                                    controls
                                                    preload="metadata"
                                                    aria-label={`Xem trước video TikTok ${item.ad.id}`}
                                                    className="h-full w-full bg-black object-contain"
                                                />
                                            ) : (
                                                <img
                                                    src={media}
                                                    alt={
                                                        item.ad.title ??
                                                        `Quảng cáo TikTok ${item.ad.id}`
                                                    }
                                                    loading="lazy"
                                                    className="h-full w-full bg-surface-soft object-contain"
                                                />
                                            )
                                        ) : (
                                            <div className="flex h-full items-center justify-center bg-surface-soft px-4 text-center text-xs text-text-tertiary">
                                                {videoCount + imageCount > 0
                                                    ? item.media_state === "METADATA_ONLY"
                                                        ? "Lưu video tham khảo để hệ thống chuẩn bị bản xem trước."
                                                        : "Chưa có bản xem trước"
                                                    : "TikTok chưa cung cấp video hoặc ảnh cho quảng cáo này."}
                                            </div>
                                        )}
                                    </div>
                                    <div className="space-y-2 p-3">
                                        <label className="flex min-h-11 cursor-pointer items-center gap-2 rounded-lg px-1 text-xs text-text-secondary focus-within:ring-2 focus-within:ring-ring">
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
                                            Chọn để xem xét cùng các video khác
                                        </label>
                                        <div className="flex flex-wrap gap-1.5 text-[10px] font-semibold tracking-wide">
                                            <span className="rounded-full bg-primary/10 px-2 py-1 text-primary">
                                                TikTok chính thức
                                            </span>
                                            <span className="rounded-full bg-surface-soft px-2 py-1 text-text-secondary">
                                                Tham khảo thị trường
                                            </span>
                                            <span className="rounded-full bg-surface-soft px-2 py-1 text-text-secondary">
                                                Quảng cáo công khai
                                            </span>
                                        </div>
                                        <p className="line-clamp-2 text-sm font-medium text-text-primary">
                                            {item.ad.title ?? `Quảng cáo TikTok ${item.ad.id}`}
                                        </p>
                                        <p className="text-xs text-text-secondary">
                                            {item.advertiser?.business_name ??
                                                "Chưa có tên nhà quảng cáo"}{" "}
                                            · {item.ad.reach ?? "Chưa có số tiếp cận"}
                                        </p>
                                        <div className="grid grid-cols-2 gap-x-3 gap-y-1 text-[11px] text-text-tertiary">
                                            <CompactMeta
                                                label="Trạng thái"
                                                value={item.ad.status}
                                            />
                                            <CompactMeta
                                                label="Thời gian xuất hiện"
                                                value={formatDateRange(
                                                    item.ad.first_shown_date,
                                                    item.ad.last_shown_date,
                                                )}
                                            />
                                            <CompactMeta
                                                label="Nội dung"
                                                value={`${videoCount} video · ${imageCount} ảnh`}
                                            />
                                            <CompactMeta
                                                label="Phân tích"
                                                value={item.intelligence_status}
                                            />
                                        </div>
                                        <div className="flex flex-wrap gap-2">
                                            <Button
                                                size="sm"
                                                variant="ghost"
                                                onClick={() => setDetailItem(item)}
                                            >
                                                Xem chi tiết
                                            </Button>
                                            {item.asset_id && (
                                                <Button
                                                    size="sm"
                                                    variant="ghost"
                                                    onClick={() => analyze.mutate(item)}
                                                    disabled={
                                                        analyze.isPending ||
                                                        item.media_state === "METADATA_ONLY" ||
                                                        item.media_state ===
                                                            "DIRECT_STREAM_AVAILABLE"
                                                    }
                                                >
                                                    {item.media_state === "METADATA_ONLY"
                                                        ? "Chưa có file"
                                                        : item.media_state ===
                                                            "DIRECT_STREAM_AVAILABLE"
                                                          ? "Lưu để phân tích"
                                                          : "Phân tích cách làm"}
                                                </Button>
                                            )}
                                            {item.asset_id && (
                                                <Button
                                                    size="sm"
                                                    variant="ghost"
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
                                                    Áp dụng cho sản phẩm
                                                </Button>
                                            )}
                                            <Button
                                                size="sm"
                                                onClick={() =>
                                                    save.mutate({ sourceId: item.source_id })
                                                }
                                                disabled={save.isPending || !boards.data?.length}
                                            >
                                                Lưu tham khảo
                                            </Button>
                                        </div>
                                        {adaptAssetId === item.asset_id && (
                                            <div className="mt-2 flex flex-wrap items-center gap-2 rounded-xl bg-surface-soft p-2">
                                                <label
                                                    className="text-xs text-text-secondary"
                                                    htmlFor={`adapt-product-${item.asset_id}`}
                                                >
                                                    Sản phẩm
                                                </label>
                                                <select
                                                    id={`adapt-product-${item.asset_id}`}
                                                    className="h-11 min-w-0 max-w-full rounded-xl border-0 bg-surface px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
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
                                                        ? "Đang tạo gợi ý…"
                                                        : "Tạo 3 hướng video"}
                                                </Button>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                    {selectedSourceIds.size > 0 && (
                        <div className="mt-4 flex flex-wrap items-center justify-between gap-3 rounded-2xl bg-primary-soft p-4">
                            <p className="text-sm text-text-secondary">
                                Đã chọn {selectedSourceIds.size} video. Các video sẽ được lưu tham
                                khảo trong workspace trước khi xem xét.
                            </p>
                            <Button
                                size="sm"
                                onClick={() => batch.mutate()}
                                disabled={batch.isPending || selectedSourceIds.size > 25}
                            >
                                {batch.isPending ? "Đang chuẩn bị…" : "Xem xét các video đã chọn"}
                            </Button>
                        </div>
                    )}
                    {cursor && (
                        <Button
                            className="mt-4"
                            variant="ghost"
                            size="sm"
                            onClick={() => search.mutate(cursor)}
                            disabled={search.isPending}
                        >
                            Xem thêm
                        </Button>
                    )}
                    <Dialog
                        open={Boolean(detailItem)}
                        onOpenChange={(open) => !open && setDetailItem(null)}
                    >
                        <DialogContent className="flex max-h-[calc(100dvh-2rem)] max-w-[min(960px,calc(100vw-2rem))] flex-col gap-0 overflow-hidden border-0 p-0 motion-reduce:animate-none [&>button:last-child]:flex [&>button:last-child]:size-11 [&>button:last-child]:items-center [&>button:last-child]:justify-center [&>button:last-child]:rounded-xl">
                            {detailItem && (
                                <>
                                    <DialogHeader className="shrink-0 bg-surface px-6 pb-4 pt-6 pr-20">
                                        <div className="flex flex-wrap items-start justify-between gap-3">
                                            <div className="min-w-0">
                                                <DialogTitle className="truncate text-xl">
                                                    {detailItem.ad.title ??
                                                        `Quảng cáo TikTok ${detailItem.ad.id}`}
                                                </DialogTitle>
                                                <DialogDescription className="mt-1">
                                                    {detailItem.advertiser?.business_name ??
                                                        "Chưa có tên nhà quảng cáo"}{" "}
                                                    · Video tham khảo từ TikTok chính thức
                                                </DialogDescription>
                                            </div>
                                            <div className="flex shrink-0 flex-wrap gap-1.5 text-[10px] font-semibold tracking-wide">
                                                <span className="rounded-full bg-primary/10 px-2 py-1 text-primary">
                                                    TikTok chính thức
                                                </span>
                                                <span className="rounded-full bg-surface-soft px-2 py-1 text-text-secondary">
                                                    Tham khảo thị trường
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
                <p className="text-text-tertiary">Đang tải thông tin từ TikTok…</p>
            )}
            {detail.isError && (
                <p className="rounded-md bg-amber-500/10 p-2 text-amber-700">
                    Chưa tải được thông tin chi tiết. Bạn đang xem dữ liệu từ kết quả tìm kiếm.
                </p>
            )}
            <DetailSection title="Thông tin từ TikTok">
                <div className="grid gap-x-4 gap-y-2 sm:grid-cols-2">
                    <DetailRow label="Mã quảng cáo" value={data.ad.id} />
                    <DetailRow label="Mã nguồn tham khảo" value={data.source_id} />
                    <DetailRow label="Xuất hiện lần đầu" value={data.ad.first_shown_date} />
                    <DetailRow label="Xuất hiện lần cuối" value={data.ad.last_shown_date} />
                    <DetailRow label="Trạng thái" value={data.ad.status} />
                    <DetailRow label="Mô tả trạng thái" value={data.ad.status_statement} />
                    <DetailRow label="Lượt tiếp cận" value={data.ad.reach} />
                    <DetailRow label="Tình trạng file" value={data.media_state} />
                </div>
            </DetailSection>

            <DetailSection title="Nhà quảng cáo">
                <div className="grid gap-x-4 gap-y-2 sm:grid-cols-2">
                    <DetailRow label="Tên doanh nghiệp" value={data.advertiser?.business_name} />
                    <DetailRow label="Mã doanh nghiệp" value={data.advertiser?.business_id} />
                    <DetailRow label="Quốc gia" value={data.advertiser?.country_code} />
                    <DetailRow label="Bên chi trả" value={data.advertiser?.paid_for_by} />
                    <DetailRow label="Người theo dõi" value={data.advertiser?.follower_count} />
                    <DetailRow label="Link ảnh đại diện" value={data.advertiser?.avatar_url} />
                    <DetailRow label="Link trang cá nhân" value={data.advertiser?.profile_url} />
                </div>
            </DetailSection>

            <DetailSection title="Nội dung quảng cáo">
                <div className="grid gap-x-4 gap-y-2 sm:grid-cols-2">
                    <DetailRow label="Tiêu đề" value={data.ad.title} />
                    <DetailRow label="Lời kêu gọi hành động" value={data.ad.call_to_action} />
                    <DetailRow label="Mục tiêu quảng cáo" value={data.ad.advertising_objective} />
                    <DetailRow label="Số video" value={videoCount} />
                    <DetailRow label="Số ảnh" value={imageCount} />
                    <DetailLink label="Link ngoài" value={data.ad.external_url} />
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
                                            playsInline
                                            preload="metadata"
                                            aria-label={`Video TikTok ${data.ad.id}, phần ${media.index + 1}`}
                                            className="h-full w-full object-contain"
                                        />
                                    ) : (
                                        <img
                                            src={src}
                                            alt={`${data.ad.title ?? `Quảng cáo TikTok ${data.ad.id}`} · ảnh ${media.index + 1}`}
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
                            ? "Media is available after Lưu tham khảo or when direct preview is enabled."
                            : "TikTok chưa cung cấp video hoặc ảnh."}
                    </p>
                )}
            </DetailSection>

            <DetailSection title="Thông tin nhắm mục tiêu và kiểm duyệt">
                <JsonValue label="Nhắm mục tiêu" value={data.ad.targeting_info} />
                <JsonValue label="Kiểm duyệt" value={data.ad.moderation_metadata} />
            </DetailSection>

            <DetailSection title="Phân tích của Viraldy">
                <div className="grid gap-x-4 gap-y-2 sm:grid-cols-2">
                    <DetailRow label="Trạng thái phân tích" value={data.intelligence_status} />
                    <DetailRow
                        label="Số bằng chứng"
                        value={intelligence.data?.analysis.evidence_count}
                    />
                    <DetailRow label="Nhóm nội dung" value={intelligence.data?.families.length} />
                    <DetailRow label="Phạm vi bằng chứng" value="Quan sát thị trường công khai" />
                </div>
            </DetailSection>

            <p className="rounded-xl bg-primary/[0.05] p-3 text-[11px] text-text-tertiary">
                Dữ liệu này giúp tham khảo thị trường, không phản ánh doanh số, ROAS, tỷ lệ chuyển
                đổi hay dự đoán video sẽ bán tốt. Thông tin TikTok chưa cung cấp được để là chưa có
                dữ liệu.
            </p>
        </div>
    );
}

function CompactMeta({ label, value }: { label: string; value: string | null | undefined }) {
    return (
        <span className="truncate">
            <span className="font-medium text-text-secondary">{label}:</span>{" "}
            {value ?? "Chưa có dữ liệu"}
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
                        className="inline-flex min-h-11 items-center rounded-lg px-1 text-primary underline-offset-2 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                    >
                        Mở link ngoài
                    </a>
                ) : (
                    "Chưa có dữ liệu"
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
                {value ? JSON.stringify(value, null, 2) : "Chưa có dữ liệu"}
            </pre>
        </div>
    );
}

function formatDetailValue(value: unknown) {
    if (value === null || value === undefined || value === "") return "Chưa có dữ liệu";
    if (typeof value === "object") return JSON.stringify(value);
    return String(value);
}

function formatDateRange(first: string | null, last: string | null) {
    if (!first && !last) return "Chưa có dữ liệu";
    return `${first ?? "?"} – ${last ?? "?"}`;
}
