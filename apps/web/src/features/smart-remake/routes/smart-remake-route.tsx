import { createFileRoute } from "@tanstack/react-router";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
    ArrowRight,
    CheckCircle2,
    FileImage,
    FileVideo,
    Link2,
    Loader2,
    Play,
    Sparkles,
    Upload,
    Wand2,
    type LucideIcon,
} from "lucide-react";
import { type RefObject, useEffect, useRef, useState } from "react";

import { useApiWorkspace } from "@/shared/hooks/use-workspace";
import {
    compileSmartRemake,
    getSmartRemakeHealth,
    type SmartRemakeCompileResult,
} from "@/shared/api/smart-remake";
import { crawlProductPreview, type ProductCrawlPreview } from "@/shared/api/products";
import { AppShell } from "@/widgets/app-shell/app-shell";
import { Button } from "@/shared/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/ui/card";
import { PageHeader } from "@/shared/ui/page-header";
import { StatusChip } from "@/shared/ui/status-chip";
import { SurfaceCard } from "@/shared/ui/surface-card";
import { Textarea } from "@/shared/ui/textarea";
import { Input } from "@/shared/ui/input";
import { cn } from "@/shared/lib/utils";

export const Route = createFileRoute("/smart-remake")({
    head: () => ({ meta: [{ title: "Smart Remake - Viraldy" }] }),
    component: SmartRemakePage,
});

const MAX_VIDEO_BYTES = 30 * 1024 * 1024;
const MAX_IMAGE_BYTES = 10 * 1024 * 1024;
const ANALYSIS_STEPS = [
    {
        label: "Đang xem nhịp video mẫu",
        detail: "Tìm phần mở đầu, điểm nhấn và cách câu chuyện được kể.",
    },
    {
        label: "Đang chọn những khoảnh khắc đáng nhớ",
        detail: "Giữ lại cảm xúc và nhịp điệu phù hợp nhất từ video của bạn.",
    },
    {
        label: "Đang nhận diện sản phẩm",
        detail: "Ghi nhận các chi tiết để sản phẩm luôn xuất hiện nhất quán.",
    },
    {
        label: "Đang lên ý tưởng cho video mới",
        detail: "Kết hợp sản phẩm của bạn với cảm hứng từ video mẫu.",
    },
    {
        label: "Đang viết kịch bản video mới",
        detail: "Hoàn thiện từng phân đoạn để sẵn sàng cho bước tạo video.",
    },
] as const;
const DEMO_OUTPUT_VIDEO = "/smart-remake/02_After.mp4";
const DEMO_RENDER_DELAY_MS = 20_000;

type CompileAssets = {
    referenceVideo: File;
    productImage?: File;
    productLink?: ProductLinkSelection;
};

type ProductLinkSelection = {
    sourceUrl: string;
    title: string;
    description: string | null;
    imageUrls: string[];
};

type SmartRemakeRenderState = {
    finalVideoUrl: string;
    status: "completed";
};

function SmartRemakePage() {
    const { workspaceId } = useApiWorkspace();
    const health = useQuery({
        queryKey: ["smart-remake", "health", workspaceId],
        queryFn: () => getSmartRemakeHealth(workspaceId!),
        enabled: Boolean(workspaceId),
        staleTime: 60_000,
    });
    const [duration, setDuration] = useState<8 | 16>(8);
    const [language, setLanguage] = useState("");
    const [prompt, setPrompt] = useState("");
    const [description, setDescription] = useState("");
    const [referenceVideo, setReferenceVideo] = useState<File | null>(null);
    const [productImages, setProductImages] = useState<File[]>([]);
    const [productLink, setProductLink] = useState("");
    const [linkedProduct, setLinkedProduct] = useState<ProductLinkSelection | null>(null);
    const [compileResult, setCompileResult] = useState<SmartRemakeCompileResult | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [result, setResult] = useState<SmartRemakeRenderState | null>(null);
    const [analysisStep, setAnalysisStep] = useState(0);
    const [renderProgress, setRenderProgress] = useState(0);
    const referenceVideoElementRef = useRef<HTMLVideoElement>(null);
    const referencePreviewUrl = usePreviewUrl(referenceVideo);
    const uploadedProductPreviewUrls = usePreviewUrls(productImages);
    const productPreviewUrls = linkedProduct?.imageUrls ?? uploadedProductPreviewUrls;
    const productImageCount = productPreviewUrls.length;
    const compile = useMutation({
        mutationFn: ({ referenceVideo, productImage, productLink: linked }: CompileAssets) => {
            if (!workspaceId) throw new Error("Chọn workspace trước khi phân tích video.");
            return compileSmartRemake(workspaceId, {
                targetDuration: duration,
                language,
                prompt,
                description,
                referenceVideo,
                productImage,
                productUrl: linked?.sourceUrl,
                productTitle: linked?.title,
                productDescription: linked?.description ?? undefined,
            });
        },
        onMutate: () => {
            setError(null);
            setResult(null);
            setAnalysisStep(0);
        },
        onSuccess: (data) => setCompileResult(data),
        onError: (cause) =>
            setError(cause instanceof Error ? cause.message : "Smart Remake compile failed."),
    });
    const productLinkPreview = useMutation({
        mutationFn: (url: string) => {
            if (!workspaceId) throw new Error("Chọn workspace trước khi thêm sản phẩm.");
            return crawlProductPreview(workspaceId, url);
        },
        onMutate: () => setError(null),
        onSuccess: (preview) => {
            const selection = productLinkSelection(preview);
            if (!selection.imageUrls.length) {
                setLinkedProduct(null);
                setError(
                    "Link này chưa có ảnh sản phẩm để dùng. Hãy thử link khác hoặc tải ảnh lên nhé.",
                );
                return;
            }
            setProductLink(selection.sourceUrl);
            setLinkedProduct(selection);
            setProductImages([]);
            setCompileResult(null);
            setResult(null);
        },
        onError: () => setError("Chưa thể lấy ảnh từ link sản phẩm này. Hãy thử lại nhé."),
    });

    useEffect(() => {
        if (!compile.isPending) return;
        const timer = window.setInterval(
            () => setAnalysisStep((step) => Math.min(step + 1, ANALYSIS_STEPS.length - 1)),
            4_000,
        );
        return () => window.clearInterval(timer);
    }, [compile.isPending]);

    const render = useMutation({
        mutationFn: () => {
            if (!compileResult) throw new Error("Hãy phân tích video trước khi tạo video mới.");
            return new Promise<void>((resolve) => window.setTimeout(resolve, DEMO_RENDER_DELAY_MS));
        },
        onMutate: () => {
            setError(null);
            setRenderProgress(0);
        },
        onSuccess: () => {
            setRenderProgress(100);
            setResult({
                finalVideoUrl: DEMO_OUTPUT_VIDEO,
                status: "completed",
            });
        },
        onError: (cause) =>
            setError(cause instanceof Error ? cause.message : "Smart Remake render failed."),
    });

    useEffect(() => {
        if (!render.isPending) return;
        const timer = window.setInterval(
            () => setRenderProgress((progress) => Math.min(progress + 5, 95)),
            1_000,
        );
        return () => window.clearInterval(timer);
    }, [render.isPending]);

    const validateFile = (file: File, kind: "video" | "image") => {
        const validType =
            kind === "video"
                ? ["video/mp4", "video/webm", "video/quicktime"].includes(file.type)
                : ["image/jpeg", "image/png", "image/webp"].includes(file.type);
        const max = kind === "video" ? MAX_VIDEO_BYTES : MAX_IMAGE_BYTES;
        if (!validType) {
            setError(
                kind === "video"
                    ? "Video này chưa thể dùng được. Hãy thử chọn video khác nhé."
                    : "Ảnh này chưa thể dùng được. Hãy thử chọn ảnh khác nhé.",
            );
            return false;
        }
        if (file.size > max) {
            setError(
                kind === "video"
                    ? "Video này hơi lớn. Hãy thử một video nhẹ hơn nhé."
                    : "Ảnh này hơi lớn. Hãy thử một ảnh nhẹ hơn nhé.",
            );
            return false;
        }
        return true;
    };

    const chooseReferenceVideo = (file: File | null) => {
        if (!file || compile.isPending) return;
        if (!validateFile(file, "video")) return;
        setError(null);
        setReferenceVideo(file);
        setCompileResult(null);
        setResult(null);
    };

    const chooseProductImages = (files: File[]) => {
        if (!files.length || compile.isPending) return;
        const additions = files
            .filter(
                (file, index, items) =>
                    index ===
                    items.findIndex(
                        (candidate) =>
                            candidate.name === file.name &&
                            candidate.size === file.size &&
                            candidate.lastModified === file.lastModified,
                    ),
            )
            .filter(
                (file) =>
                    !productImages.some(
                        (existing) =>
                            existing.name === file.name &&
                            existing.size === file.size &&
                            existing.lastModified === file.lastModified,
                    ),
            );
        if (!additions.length || !additions.every((file) => validateFile(file, "image"))) return;
        setError(null);
        setProductLink("");
        setLinkedProduct(null);
        setProductImages((current) => [...current, ...additions]);
        setCompileResult(null);
        setResult(null);
    };

    const chooseProductLink = () => {
        const url = productLink.trim();
        if (!url || productLinkPreview.isPending || compile.isPending) return;
        productLinkPreview.mutate(url);
    };

    const syncReferencePlayback = (playing: boolean) => {
        const video = referenceVideoElementRef.current;
        if (!video) return;

        if (!playing) {
            video.pause();
            return;
        }

        video.currentTime = 0;
        void video.play().catch(() => undefined);
    };

    const disabled = !workspaceId || !referenceVideo || !productImageCount || compile.isPending;
    return (
        <AppShell>
            <div className="space-y-6">
                <PageHeader
                    title="Smart Remake"
                    description="Chọn video mẫu và ảnh sản phẩm. Chúng tôi sẽ chuẩn bị kịch bản video mới cho bạn."
                    actions={
                        <StatusChip tone={health.data?.enabled ? "ok" : "warn"} dot>
                            {health.data?.enabled
                                ? `${health.data.mode === "live" ? "Sẵn sàng" : "Chế độ thử"}`
                                : "Đang kiểm tra"}
                        </StatusChip>
                    }
                />

                <SmartRemakeFlow
                    referenceVideo={referenceVideo}
                    productImages={productImages}
                    referencePreviewUrl={referencePreviewUrl}
                    productPreviewUrls={productPreviewUrls}
                    linkedProduct={linkedProduct}
                    productLink={productLink}
                    compileResult={compileResult}
                    result={result}
                    isCompiling={compile.isPending}
                    isRendering={render.isPending}
                    analysisStep={analysisStep}
                    renderProgress={renderProgress}
                    uploadDisabled={compile.isPending}
                    referenceVideoElementRef={referenceVideoElementRef}
                    onReferenceVideoChange={chooseReferenceVideo}
                    onProductImagesChange={chooseProductImages}
                    onProductLinkChange={setProductLink}
                    onProductLinkSubmit={chooseProductLink}
                    isProductLinkLoading={productLinkPreview.isPending}
                    onOutputPlaybackChange={syncReferencePlayback}
                />

                <div className="grid gap-6 xl:grid-cols-[minmax(0,1.1fr)_minmax(360px,0.9fr)]">
                    <Card>
                        <CardHeader>
                            <CardTitle className="flex items-center gap-2">
                                <Wand2 className="size-5 text-primary" />
                                Bạn muốn video mới thế nào?
                            </CardTitle>
                            <CardDescription>
                                Hai mục này là lựa chọn thêm. Bạn có thể để nguyên gợi ý mặc định.
                            </CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-5">
                            <div>
                                <div className="mb-2 text-sm font-medium text-text-primary">
                                    Độ dài video
                                </div>
                                <div
                                    className="grid grid-cols-2 gap-2"
                                    role="radiogroup"
                                    aria-label="Độ dài video"
                                >
                                    {[8, 16].map((value) => (
                                        <button
                                            key={value}
                                            type="button"
                                            role="radio"
                                            aria-checked={duration === value}
                                            onClick={() => {
                                                setDuration(value as 8 | 16);
                                                setCompileResult(null);
                                                setResult(null);
                                            }}
                                            className={cn(
                                                "rounded-lg border px-4 py-3 text-left transition",
                                                duration === value
                                                    ? "border-primary bg-primary/10"
                                                    : "border-control-border bg-surface hover:bg-surface-soft",
                                            )}
                                        >
                                            <div className="font-semibold text-text-primary">
                                                Video {value} giây
                                            </div>
                                            <div className="text-xs text-text-secondary">
                                                {value === 8
                                                    ? "Một mạch nội dung"
                                                    : "Hai phần nội dung"}{" "}
                                            </div>
                                        </button>
                                    ))}
                                </div>
                            </div>
                            <div className="grid gap-4 md:grid-cols-2">
                                <label className="space-y-2 text-sm font-medium text-text-primary">
                                    Ngôn ngữ hiển thị
                                    <input
                                        value={language}
                                        onChange={(event) => setLanguage(event.target.value)}
                                        placeholder="Ví dụ: Tiếng Việt"
                                        className="flex h-10 w-full rounded-[10px] border border-control-border bg-surface px-3 text-sm"
                                    />
                                </label>
                                <label className="space-y-2 text-sm font-medium text-text-primary">
                                    Phong cách bạn muốn
                                    <Textarea
                                        value={prompt}
                                        onChange={(event) => setPrompt(event.target.value)}
                                        placeholder="Mô tả phong cách, nhịp điệu hoặc thông điệp bạn muốn cho video mới"
                                        rows={3}
                                    />
                                </label>
                            </div>
                            <label className="block space-y-2 text-sm font-medium text-text-primary">
                                Những điều phải giữ nguyên
                                <Textarea
                                    value={description}
                                    onChange={(event) => setDescription(event.target.value)}
                                    placeholder="Nêu chi tiết sản phẩm hoặc nhận diện thương hiệu cần giữ nguyên"
                                    rows={4}
                                />
                            </label>
                            {error && (
                                <div
                                    role="alert"
                                    className="rounded-lg border border-destructive/30 bg-destructive-soft px-3 py-2 text-sm text-destructive"
                                >
                                    {error}
                                </div>
                            )}
                            <Button
                                className="w-full"
                                size="lg"
                                disabled={disabled}
                                onClick={() => {
                                    if (referenceVideo && (productImages[0] || linkedProduct)) {
                                        compile.mutate({
                                            referenceVideo,
                                            productImage: productImages[0],
                                            productLink: linkedProduct ?? undefined,
                                        });
                                    }
                                }}
                            >
                                {compile.isPending ? (
                                    <>
                                        <Loader2 className="animate-spin" />
                                        Đang phân tích video…
                                    </>
                                ) : (
                                    <>
                                        <Sparkles />
                                        {compileResult ? "Phân tích lại video" : "Phân tích video"}
                                    </>
                                )}
                            </Button>
                        </CardContent>
                    </Card>

                    <div className="space-y-6">
                        <Card>
                            <CardHeader>
                                <CardTitle>Kịch bản video của bạn</CardTitle>
                                <CardDescription>
                                    {compileResult
                                        ? "Đây là câu chuyện video sẽ kể, trước khi bạn tạo video mới."
                                        : "Sau khi phân tích, bạn sẽ xem và kiểm tra kịch bản trước khi tạo video."}
                                </CardDescription>
                            </CardHeader>
                            <CardContent>
                                {compileResult ? (
                                    <div className="space-y-5">
                                        <CompilePreview result={compileResult} />
                                        <PromptInspector result={compileResult} />
                                    </div>
                                ) : (
                                    <div className="flex min-h-48 flex-col items-center justify-center rounded-lg border border-dashed border-control-border bg-surface-soft text-center text-sm text-text-secondary">
                                        <Sparkles className="mb-3 size-8 text-primary/60" />
                                        <span>
                                            Chọn tư liệu rồi bấm Phân tích video để tạo kịch bản.
                                        </span>
                                    </div>
                                )}
                            </CardContent>
                        </Card>
                        {compileResult && (
                            <Card>
                                <CardHeader>
                                    <CardTitle>Tạo video mới</CardTitle>
                                    <CardDescription>
                                        Khi bạn hài lòng với kịch bản, hãy tạo video hoàn chỉnh.
                                    </CardDescription>
                                </CardHeader>
                                <CardContent className="space-y-4">
                                    <Button
                                        className="w-full"
                                        size="lg"
                                        disabled={render.isPending}
                                        onClick={() => render.mutate()}
                                    >
                                        {render.isPending ? (
                                            <>
                                                <Loader2 className="animate-spin" />
                                                Đang hoàn thiện video… {renderProgress}%
                                            </>
                                        ) : (
                                            <>
                                                <Play />
                                                Tạo video {duration} giây
                                            </>
                                        )}
                                    </Button>
                                    {result && (
                                        <div className="space-y-3 rounded-lg border border-ok/30 bg-ok-soft p-3 text-sm">
                                            <div className="flex items-center gap-2 font-medium text-ok">
                                                <CheckCircle2 className="size-4" />
                                                {result.status === "completed"
                                                    ? "Video đã sẵn sàng"
                                                    : "Đã bắt đầu tạo video"}
                                            </div>
                                            {result.finalVideoUrl && (
                                                <a
                                                    className="text-primary underline"
                                                    href={result.finalVideoUrl}
                                                    target="_blank"
                                                    rel="noreferrer"
                                                >
                                                    Mở video đã tạo
                                                </a>
                                            )}
                                        </div>
                                    )}
                                </CardContent>
                            </Card>
                        )}
                    </div>
                </div>
            </div>
        </AppShell>
    );
}

function SmartRemakeFlow({
    referenceVideo,
    productImages,
    referencePreviewUrl,
    productPreviewUrls,
    linkedProduct,
    productLink,
    compileResult,
    result,
    isCompiling,
    isRendering,
    analysisStep,
    renderProgress,
    uploadDisabled,
    referenceVideoElementRef,
    onReferenceVideoChange,
    onProductImagesChange,
    onProductLinkChange,
    onProductLinkSubmit,
    isProductLinkLoading,
    onOutputPlaybackChange,
}: {
    referenceVideo: File | null;
    productImages: File[];
    referencePreviewUrl: string | null;
    productPreviewUrls: string[];
    linkedProduct: ProductLinkSelection | null;
    productLink: string;
    compileResult: SmartRemakeCompileResult | null;
    result: SmartRemakeRenderState | null;
    isCompiling: boolean;
    isRendering: boolean;
    analysisStep: number;
    renderProgress: number;
    uploadDisabled: boolean;
    referenceVideoElementRef: RefObject<HTMLVideoElement | null>;
    onReferenceVideoChange: (file: File | null) => void;
    onProductImagesChange: (files: File[]) => void;
    onProductLinkChange: (value: string) => void;
    onProductLinkSubmit: () => void;
    isProductLinkLoading: boolean;
    onOutputPlaybackChange: (playing: boolean) => void;
}) {
    return (
        <Card className="overflow-hidden">
            <CardHeader className="border-b border-control-border bg-surface-soft/50">
                <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="space-y-1">
                        <CardTitle>Video của bạn sẽ được làm mới như thế nào?</CardTitle>
                        <CardDescription>Video mẫu → sản phẩm của bạn → video mới.</CardDescription>
                    </div>
                    <StatusChip tone={result?.status === "completed" ? "ok" : "info"}>
                        {result?.status === "completed"
                            ? "Video sẵn sàng"
                            : compileResult
                              ? "Kịch bản sẵn sàng"
                              : "Chọn nội dung"}
                    </StatusChip>
                </div>
            </CardHeader>
            <CardContent className="p-4 md:p-6">
                <div className="grid items-stretch gap-3 sm:grid-cols-[minmax(0,0.8fr)_auto_minmax(0,1.3fr)_auto_minmax(0,0.8fr)]">
                    <FlowInputSlot
                        label="Video mẫu"
                        icon={FileVideo}
                        file={referenceVideo}
                        accept="video/mp4,video/webm,video/quicktime"
                        description="Tải video mẫu để bắt đầu"
                        previewUrl={referencePreviewUrl}
                        portraitFrame
                        disabled={uploadDisabled}
                        videoElementRef={referenceVideoElementRef}
                        onChange={onReferenceVideoChange}
                    />
                    <FlowArrow />
                    <ProductImagesSlot
                        files={productImages}
                        previewUrls={productPreviewUrls}
                        linkedProduct={linkedProduct}
                        productLink={productLink}
                        disabled={uploadDisabled}
                        onChange={onProductImagesChange}
                        onProductLinkChange={onProductLinkChange}
                        onProductLinkSubmit={onProductLinkSubmit}
                        isProductLinkLoading={isProductLinkLoading}
                    />
                    <FlowArrow />
                    <OutputSlot
                        compileResult={compileResult}
                        isCompiling={isCompiling}
                        isRendering={isRendering}
                        analysisStep={analysisStep}
                        renderProgress={renderProgress}
                        result={result}
                        onPlaybackChange={onOutputPlaybackChange}
                    />
                </div>
                <AnalysisProgress
                    complete={Boolean(compileResult)}
                    isRunning={isCompiling}
                    step={analysisStep}
                />
            </CardContent>
        </Card>
    );
}

function FlowInputSlot({
    label,
    icon: Icon,
    file,
    accept,
    description,
    previewUrl,
    isProduct = false,
    portraitFrame = false,
    disabled = false,
    videoElementRef,
    onChange,
}: {
    label: string;
    icon: LucideIcon;
    file: File | null;
    accept: string;
    description: string;
    previewUrl: string | null;
    isProduct?: boolean;
    portraitFrame?: boolean;
    disabled?: boolean;
    videoElementRef?: RefObject<HTMLVideoElement | null>;
    onChange: (file: File | null) => void;
}) {
    const ref = useRef<HTMLInputElement>(null);
    const isVideo = accept.startsWith("video/");

    return (
        <SurfaceCard
            className={cn("h-full min-w-0", isProduct && "border-primary/35 bg-primary/[0.03]")}
            highlight={isProduct && Boolean(file)}
            padding="sm"
            variant={file ? "raised" : "outlined"}
        >
            <div className="flex h-full min-h-64 flex-col gap-3">
                <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2 text-sm font-medium text-text-primary">
                        <Icon className={cn("size-4", isProduct && "text-primary")} />
                        {label}
                    </div>
                    {file && <StatusChip tone="ok">Đã chọn</StatusChip>}
                </div>
                <div className={cn("flex flex-1", portraitFrame && "mx-auto w-full max-w-40")}>
                    <button
                        type="button"
                        aria-label={`Chọn ${label.toLowerCase()}`}
                        disabled={disabled}
                        onClick={() => ref.current?.click()}
                        className={cn(
                            "group relative flex min-h-40 w-full flex-1 cursor-pointer items-center justify-center overflow-hidden rounded-lg border border-dashed border-control-border bg-surface-soft text-center transition-colors hover:border-primary/60 hover:bg-primary/5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 disabled:cursor-wait disabled:opacity-70",
                            portraitFrame && "aspect-[9/16] min-h-0",
                        )}
                    >
                        {previewUrl ? (
                            isVideo ? (
                                <video
                                    ref={videoElementRef}
                                    aria-hidden="true"
                                    className="size-full object-cover"
                                    autoPlay
                                    loop
                                    muted
                                    playsInline
                                    preload="metadata"
                                    src={previewUrl}
                                />
                            ) : (
                                <img
                                    alt={`${label} preview`}
                                    className="size-full object-cover"
                                    src={previewUrl}
                                />
                            )
                        ) : (
                            <span className="flex flex-col items-center gap-2 px-4">
                                <span className="grid size-10 place-items-center rounded-full bg-surface text-text-secondary shadow-sm">
                                    <Upload className="size-4" aria-hidden="true" />
                                </span>
                                <span className="text-sm font-medium text-text-primary">
                                    {portraitFrame ? "Chọn video" : `Chọn ${label.toLowerCase()}`}
                                </span>
                            </span>
                        )}
                        {previewUrl && !disabled && (
                            <span className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-surface to-transparent px-3 pb-3 pt-8 text-left text-xs font-medium text-text-primary opacity-0 transition-opacity group-hover:opacity-100 group-focus-visible:opacity-100">
                                Thay {label.toLowerCase()}
                            </span>
                        )}
                    </button>
                </div>
                <div className="space-y-1">
                    <p className="truncate text-sm font-medium text-text-primary">
                        {file?.name ?? (isProduct ? "Ảnh sản phẩm của bạn" : "Video mẫu của bạn")}
                    </p>
                    <p className="text-xs text-text-secondary">{description}</p>
                </div>
            </div>
            <input
                ref={ref}
                className="sr-only"
                type="file"
                accept={accept}
                onChange={(event) => onChange(event.target.files?.[0] ?? null)}
            />
        </SurfaceCard>
    );
}

function ProductImagesSlot({
    files,
    previewUrls,
    linkedProduct,
    productLink,
    disabled,
    onChange,
    onProductLinkChange,
    onProductLinkSubmit,
    isProductLinkLoading,
}: {
    files: File[];
    previewUrls: string[];
    linkedProduct: ProductLinkSelection | null;
    productLink: string;
    disabled: boolean;
    onChange: (files: File[]) => void;
    onProductLinkChange: (value: string) => void;
    onProductLinkSubmit: () => void;
    isProductLinkLoading: boolean;
}) {
    const ref = useRef<HTMLInputElement>(null);
    const imageCount = previewUrls.length;

    return (
        <SurfaceCard
            className="h-full min-w-0 border-primary/35 bg-primary/[0.03]"
            highlight={imageCount > 0}
            padding="sm"
            variant={imageCount ? "raised" : "outlined"}
        >
            <div className="flex h-full min-h-64 flex-col gap-3">
                <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2 text-sm font-medium text-text-primary">
                        <FileImage className="size-4 text-primary" />
                        Ảnh sản phẩm
                    </div>
                    {imageCount > 0 && <StatusChip tone="ok">Đã có {imageCount} ảnh</StatusChip>}
                </div>
                <button
                    type="button"
                    aria-label="Chọn ảnh sản phẩm"
                    disabled={disabled}
                    onClick={() => ref.current?.click()}
                    className={cn(
                        "group grid flex-1 gap-2 rounded-lg border border-dashed border-control-border bg-surface-soft p-2 text-left transition-colors hover:border-primary/60 hover:bg-primary/5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 disabled:cursor-wait disabled:opacity-70",
                        previewUrls.length <= 1
                            ? "grid-cols-1"
                            : previewUrls.length === 2
                              ? "grid-cols-2"
                              : "grid-cols-2 lg:grid-cols-3",
                    )}
                >
                    {previewUrls.length ? (
                        previewUrls.map((imageUrl, index) => (
                            <div
                                className="relative min-h-40 overflow-hidden rounded-md bg-surface"
                                key={imageUrl}
                            >
                                <img
                                    alt={`Ảnh sản phẩm ${index + 1}`}
                                    className="size-full object-cover"
                                    src={imageUrl}
                                />
                                <span className="absolute bottom-2 left-2 rounded bg-surface/90 px-1.5 py-0.5 text-[10px] font-semibold text-text-primary">
                                    Ảnh {index + 1}
                                </span>
                            </div>
                        ))
                    ) : (
                        <span className="col-span-full flex min-h-40 flex-col items-center justify-center gap-2 rounded-md bg-surface px-3 text-center">
                            <span className="grid size-9 place-items-center rounded-full bg-surface-soft text-text-secondary shadow-sm">
                                <Upload className="size-4" aria-hidden="true" />
                            </span>
                            <span className="text-sm font-medium text-text-primary">
                                Tải ảnh sản phẩm
                            </span>
                        </span>
                    )}
                </button>
                <div className="space-y-1">
                    <p className="text-sm font-medium text-text-primary">
                        {linkedProduct
                            ? linkedProduct.title
                            : imageCount
                              ? `${imageCount} ảnh đã chọn`
                              : "Tải ảnh sản phẩm"}
                    </p>
                    <p className="text-xs text-text-secondary">
                        {linkedProduct
                            ? "Ảnh được lấy từ link sản phẩm của bạn."
                            : "Bạn có thể thêm nhiều ảnh cùng lúc."}
                    </p>
                </div>
                <div className="border-t border-control-border pt-3">
                    <p className="mb-2 text-xs font-medium text-text-secondary">
                        Hoặc dán link sản phẩm
                    </p>
                    <div className="flex gap-2">
                        <Input
                            aria-label="Link sản phẩm"
                            type="url"
                            value={productLink}
                            placeholder="Dán link sản phẩm"
                            disabled={disabled || isProductLinkLoading}
                            onChange={(event) => onProductLinkChange(event.target.value)}
                            onKeyDown={(event) => {
                                if (event.key === "Enter") {
                                    event.preventDefault();
                                    onProductLinkSubmit();
                                }
                            }}
                        />
                        <Button
                            type="button"
                            variant="secondary"
                            size="sm"
                            className="shrink-0"
                            disabled={disabled || isProductLinkLoading || !productLink.trim()}
                            onClick={onProductLinkSubmit}
                        >
                            {isProductLinkLoading ? (
                                <Loader2 className="animate-spin" aria-label="Đang lấy ảnh" />
                            ) : (
                                <Link2 />
                            )}
                            {isProductLinkLoading ? "Đang lấy" : "Lấy ảnh"}
                        </Button>
                    </div>
                </div>
            </div>
            <input
                ref={ref}
                className="sr-only"
                type="file"
                accept="image/jpeg,image/png,image/webp"
                multiple
                onChange={(event) => {
                    const selectedFiles = Array.from(event.target.files ?? []);
                    event.currentTarget.value = "";
                    onChange(selectedFiles);
                }}
            />
        </SurfaceCard>
    );
}

function FlowArrow() {
    return (
        <div className="flex items-center justify-center" aria-hidden="true">
            <div className="grid size-9 rotate-90 place-items-center rounded-full border border-control-border bg-surface text-primary shadow-sm sm:rotate-0">
                <ArrowRight className="size-4" />
            </div>
        </div>
    );
}

function OutputSlot({
    compileResult,
    result,
    isCompiling,
    isRendering,
    analysisStep,
    renderProgress,
    onPlaybackChange,
}: {
    compileResult: SmartRemakeCompileResult | null;
    result: SmartRemakeRenderState | null;
    isCompiling: boolean;
    isRendering: boolean;
    analysisStep: number;
    renderProgress: number;
    onPlaybackChange: (playing: boolean) => void;
}) {
    const completedVideo = result?.status === "completed" ? result.finalVideoUrl : null;
    const currentAnalysis = ANALYSIS_STEPS[analysisStep];
    const analysisProgress = Math.round(((analysisStep + 1) / ANALYSIS_STEPS.length) * 100);
    const statusLabel = isRendering
        ? `Đang hoàn thiện video · ${renderProgress}%`
        : isCompiling
          ? currentAnalysis.label
          : completedVideo
            ? "Video đã tạo"
            : compileResult
              ? "Sẵn sàng tạo video"
              : "Đợi video và ảnh";

    return (
        <SurfaceCard
            className="h-full min-w-0"
            padding="sm"
            variant={completedVideo ? "raised" : "outlined"}
        >
            <div className="flex h-full min-h-64 flex-col gap-3">
                <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2 text-sm font-medium text-text-primary">
                        <Sparkles className="size-4 text-primary" aria-hidden="true" />
                        Video mới
                    </div>
                    {completedVideo && <StatusChip tone="ok">Sẵn sàng</StatusChip>}
                </div>
                <div className="mx-auto flex aspect-[9/16] w-full max-w-40 items-center justify-center overflow-hidden rounded-lg border border-dashed border-control-border bg-surface-soft">
                    {completedVideo ? (
                        <video
                            className="size-full object-cover"
                            controls
                            onEnded={() => onPlaybackChange(false)}
                            onPause={() => onPlaybackChange(false)}
                            onPlay={() => onPlaybackChange(true)}
                            playsInline
                            preload="metadata"
                            src={completedVideo}
                        />
                    ) : isRendering ? (
                        <div className="flex w-full flex-col items-center gap-3 px-4 text-center">
                            <Loader2
                                className="size-7 animate-spin text-primary"
                                aria-label={statusLabel}
                            />
                            <div>
                                <p className="text-sm font-medium text-text-primary">
                                    Đang hoàn thiện video
                                </p>
                                <p className="mt-1 text-xs text-text-secondary">
                                    {renderProgress}% · chỉ còn một chút nữa
                                </p>
                            </div>
                            <div
                                aria-label="Tiến độ tạo video"
                                aria-valuemax={100}
                                aria-valuemin={0}
                                aria-valuenow={renderProgress}
                                className="h-1.5 w-full overflow-hidden rounded-full bg-control-border"
                                role="progressbar"
                            >
                                <div
                                    className="h-full rounded-full bg-primary transition-[width] duration-500"
                                    style={{ width: `${renderProgress}%` }}
                                />
                            </div>
                        </div>
                    ) : isCompiling ? (
                        <div
                            className="flex w-full flex-col items-center gap-3 px-4 text-center"
                            aria-live="polite"
                        >
                            <span className="grid size-10 place-items-center rounded-full bg-primary/10 text-primary">
                                <Sparkles className="size-5 animate-pulse" aria-hidden="true" />
                            </span>
                            <div>
                                <p className="text-sm font-medium text-text-primary">
                                    {currentAnalysis.label}
                                </p>
                                <p className="mt-1 text-xs leading-5 text-text-secondary">
                                    {currentAnalysis.detail}
                                </p>
                            </div>
                            <div
                                aria-label="Tiến độ phân tích"
                                aria-valuemax={100}
                                aria-valuemin={0}
                                aria-valuenow={analysisProgress}
                                className="h-1.5 w-full overflow-hidden rounded-full bg-control-border"
                                role="progressbar"
                            >
                                <div
                                    className="h-full rounded-full bg-primary transition-[width] duration-500"
                                    style={{ width: `${analysisProgress}%` }}
                                />
                            </div>
                        </div>
                    ) : (
                        <div className="flex flex-col items-center gap-2 px-5 text-center">
                            <span className="grid size-10 place-items-center rounded-full bg-surface text-primary shadow-sm">
                                <Wand2 className="size-4" aria-hidden="true" />
                            </span>
                            <span className="text-sm font-medium text-text-primary">
                                Video mới sẽ xuất hiện ở đây
                            </span>
                        </div>
                    )}
                </div>
                <div className="space-y-1">
                    <p className="text-sm font-medium text-text-primary">{statusLabel}</p>
                    <p className="text-xs text-text-secondary">
                        {isCompiling
                            ? "Đang biến tư liệu bạn chọn thành kịch bản có thể xem trước."
                            : compileResult
                              ? `${compileResult.sceneMap.sceneCount === 1 ? "Một phần nội dung" : "Hai phần nội dung"} · ${compileResult.inputSummary.targetDuration} giây`
                              : "Chọn tư liệu, sau đó bấm Phân tích video để tiếp tục."}
                    </p>
                </div>
            </div>
        </SurfaceCard>
    );
}

function AnalysisProgress({
    complete,
    isRunning,
    step,
}: {
    complete: boolean;
    isRunning: boolean;
    step: number;
}) {
    if (!isRunning && !complete) return null;

    const currentStep = ANALYSIS_STEPS[Math.min(step, ANALYSIS_STEPS.length - 1)];
    const activeStep = complete ? ANALYSIS_STEPS.length : step + 1;
    return (
        <div
            className="mt-5 rounded-lg border border-control-border bg-surface-soft p-4"
            aria-live="polite"
        >
            <div className="mb-3 flex items-center justify-between gap-3">
                <div>
                    <p className="text-sm font-medium text-text-primary">
                        {complete ? "Kịch bản đã sẵn sàng" : currentStep.label}
                    </p>
                    {!complete && (
                        <p className="mt-1 text-xs text-text-secondary">{currentStep.detail}</p>
                    )}
                </div>
                <span className="text-xs text-text-secondary">
                    {complete ? "Hoàn tất" : `Bước ${activeStep}/${ANALYSIS_STEPS.length}`}
                </span>
            </div>
            <div
                aria-label="Tiến độ phân tích video"
                aria-valuemax={ANALYSIS_STEPS.length}
                aria-valuemin={0}
                aria-valuenow={activeStep}
                className="mb-4 h-2 overflow-hidden rounded-full bg-control-border"
                role="progressbar"
            >
                <div
                    className="h-full rounded-full bg-primary transition-[width] duration-500"
                    style={{
                        width: `${Math.max(12, (activeStep / ANALYSIS_STEPS.length) * 100)}%`,
                    }}
                />
            </div>
            <ol className="grid gap-2 sm:grid-cols-2 xl:grid-cols-5">
                {ANALYSIS_STEPS.map((item, index) => {
                    const done = complete || index < step;
                    const current = !complete && index === step;
                    return (
                        <li
                            className={cn(
                                "rounded-lg border p-3 transition-colors",
                                done
                                    ? "border-primary/25 bg-primary/5"
                                    : current
                                      ? "border-primary/50 bg-surface"
                                      : "border-control-border bg-surface",
                            )}
                            key={item.label}
                        >
                            <span
                                className={cn(
                                    "mb-2 grid size-5 shrink-0 place-items-center rounded-full border text-[10px] font-semibold",
                                    done
                                        ? "border-primary bg-primary text-primary-foreground"
                                        : current
                                          ? "border-primary text-primary"
                                          : "border-control-border text-text-secondary",
                                )}
                            >
                                {done ? (
                                    <CheckCircle2 className="size-3" aria-hidden="true" />
                                ) : (
                                    index + 1
                                )}
                            </span>
                            <p
                                className={cn(
                                    "text-sm font-medium leading-5",
                                    done || current ? "text-text-primary" : "text-text-secondary",
                                )}
                            >
                                {item.label}
                            </p>
                            <p className="mt-1 text-xs leading-5 text-text-secondary">
                                {item.detail}
                            </p>
                        </li>
                    );
                })}
            </ol>
        </div>
    );
}

function usePreviewUrl(file: File | null) {
    const [previewUrl, setPreviewUrl] = useState<string | null>(null);

    useEffect(() => {
        if (!file) {
            setPreviewUrl(null);
            return;
        }

        const objectUrl = URL.createObjectURL(file);
        setPreviewUrl(objectUrl);
        return () => URL.revokeObjectURL(objectUrl);
    }, [file]);

    return previewUrl;
}

function usePreviewUrls(files: File[]) {
    const [previewUrls, setPreviewUrls] = useState<string[]>([]);

    useEffect(() => {
        const objectUrls = files.map((file) => URL.createObjectURL(file));
        setPreviewUrls(objectUrls);
        return () => objectUrls.forEach((url) => URL.revokeObjectURL(url));
    }, [files]);

    return previewUrls;
}

function CompilePreview({ result }: { result: SmartRemakeCompileResult }) {
    const lock = result.productLock;
    return (
        <div className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
                <div className="rounded-lg bg-surface-soft p-3">
                    <div className="text-xs text-text-secondary">Sản phẩm chính</div>
                    <div className="mt-1 font-medium text-text-primary">
                        {String(lock.productName ?? "Sản phẩm của bạn")}
                    </div>
                </div>
                <div className="rounded-lg bg-surface-soft p-3">
                    <div className="text-xs text-text-secondary">Thời lượng</div>
                    <div className="mt-1 font-medium text-text-primary">
                        {result.inputSummary.targetDuration} giây
                    </div>
                </div>
            </div>
            <div className="space-y-3">
                {result.sceneMap.scenes.map((scene, index) => (
                    <StoryCard
                        key={String(scene.sceneId ?? index)}
                        scene={scene}
                        sceneIndex={index}
                    />
                ))}
            </div>
        </div>
    );
}

function PromptInspector({ result }: { result: SmartRemakeCompileResult }) {
    return (
        <div className="space-y-4 border-t border-control-border pt-5">
            <div>
                <p className="text-sm font-semibold text-text-primary">Prompt gốc (raw)</p>
                <p className="mt-1 text-xs text-text-secondary">
                    Nội dung nguyên bản mà hệ thống đã tạo cho từng phần video.
                </p>
            </div>
            <div className="space-y-3">
                {result.compiledPrompts.map((compiledPrompt, index) => (
                    <div className="space-y-2" key={index}>
                        <p className="text-xs font-medium text-text-secondary">
                            Prompt phần {index + 1}
                        </p>
                        <pre className="max-h-80 overflow-auto whitespace-pre-wrap break-words rounded-lg border border-control-border bg-surface-soft p-3 font-mono text-xs leading-5 text-text-primary">
                            {rawPromptFromCompiled(compiledPrompt)}
                        </pre>
                    </div>
                ))}
            </div>
            <div className="space-y-2">
                <p className="text-sm font-semibold text-text-primary">JSON đầy đủ</p>
                <pre className="max-h-[32rem] overflow-auto whitespace-pre-wrap break-words rounded-lg border border-control-border bg-surface-soft p-3 font-mono text-xs leading-5 text-text-primary">
                    {JSON.stringify(result, null, 2)}
                </pre>
            </div>
        </div>
    );
}

function rawPromptFromCompiled(compiledPrompt: Record<string, unknown>) {
    const promptKeys = ["prompt", "videoPrompt", "imagePrompt", "negativePrompt", "rawPrompt"];
    const sections = promptKeys.flatMap((key) => {
        const value = compiledPrompt[key];
        return typeof value === "string" && value.trim() ? [`${key}:\n${value.trim()}`] : [];
    });

    return sections.length ? sections.join("\n\n") : JSON.stringify(compiledPrompt, null, 2);
}

function StoryCard({ scene, sceneIndex }: { scene: Record<string, unknown>; sceneIndex: number }) {
    const story = storyFromScene(scene);
    return (
        <div className="rounded-lg border border-control-border p-4">
            <div className="mb-4 flex items-center justify-between gap-3">
                <p className="font-medium text-text-primary">Phần {sceneIndex + 1}</p>
                <StatusChip tone="info">{story.duration} giây</StatusChip>
            </div>
            <div className="space-y-3">
                {story.beats.map((beat) => (
                    <div className="grid grid-cols-[88px_minmax(0,1fr)] gap-3" key={beat.label}>
                        <span className="text-xs font-medium text-primary">{beat.label}</span>
                        <p className="text-sm leading-6 text-text-primary">{beat.text}</p>
                    </div>
                ))}
            </div>
            {story.onScreenText ? (
                <div className="mt-4 rounded-md bg-surface-soft px-3 py-2 text-sm text-text-secondary">
                    <span className="font-medium text-text-primary">
                        Thông điệp trên màn hình:{" "}
                    </span>
                    {story.onScreenText}
                </div>
            ) : null}
        </div>
    );
}

function storyFromScene(scene: Record<string, unknown>) {
    const shotPlan = recordValue(scene.shotPlan);
    const shots = Array.isArray(shotPlan?.shots)
        ? shotPlan.shots
              .map(recordValue)
              .filter((shot): shot is Record<string, unknown> => Boolean(shot))
        : [];
    const actionFor = (roles: string[], fallback: string) => {
        const shot = roles
            .map((role) => shots.find((item) => String(item.role ?? "") === role))
            .find(Boolean);
        return readableText(shot?.action, fallback);
    };
    const duration = Number(shotPlan?.targetDuration ?? 8);

    return {
        duration: Number.isFinite(duration) ? duration : 8,
        beats: [
            {
                label: "Mở đầu",
                text: actionFor(
                    ["hook", "setup"],
                    "Mở ngay bằng khoảnh khắc khiến người xem chú ý đến sản phẩm.",
                ),
            },
            {
                label: "Điểm nổi bật",
                text: actionFor(
                    ["demonstration", "action", "feature", "proof"],
                    "Cho sản phẩm vào tình huống sử dụng thực tế và làm rõ lợi ích chính.",
                ),
            },
            {
                label: "Kết thúc",
                text: actionFor(
                    ["result", "payoff", "cta"],
                    "Khép lại bằng kết quả rõ ràng và hình ảnh sản phẩm dễ nhớ.",
                ),
            },
        ],
        onScreenText: readableText(scene.textOverlay, ""),
    };
}

function recordValue(value: unknown): Record<string, unknown> | null {
    return value && typeof value === "object" && !Array.isArray(value)
        ? (value as Record<string, unknown>)
        : null;
}

function readableText(value: unknown, fallback: string) {
    if (typeof value !== "string" || !value.trim()) return fallback;
    const normalized = value.replace(/\s+/g, " ").trim();
    return normalized.length > 220 ? `${normalized.slice(0, 217).trimEnd()}…` : normalized;
}

function productLinkSelection(preview: ProductCrawlPreview): ProductLinkSelection {
    const metadata = preview.product_draft.metadata_json;
    const imageUrls = [
        metadata.image_url,
        preview.crawl.image,
        ...stringValues(metadata.screenshots),
        ...stringValues(metadata.buyer_images),
    ].filter((value, index, values): value is string => {
        if (typeof value !== "string" || !isPublicImageUrl(value)) return false;
        return values.indexOf(value) === index;
    });

    return {
        sourceUrl: preview.source_url,
        title: preview.product_draft.name,
        description: preview.product_draft.description ?? null,
        imageUrls,
    };
}

function stringValues(value: unknown): string[] {
    return Array.isArray(value)
        ? value.filter((item): item is string => typeof item === "string")
        : [];
}

function isPublicImageUrl(value: string): boolean {
    try {
        const url = new URL(value);
        return url.protocol === "https:" || url.protocol === "http:";
    } catch {
        return false;
    }
}
