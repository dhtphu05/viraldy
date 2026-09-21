import { createFileRoute } from "@tanstack/react-router";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
    ArrowRight,
    CheckCircle2,
    FileImage,
    FileVideo,
    Loader2,
    Play,
    Sparkles,
    Upload,
    Wand2,
    type LucideIcon,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { useApiWorkspace } from "@/shared/hooks/use-workspace";
import {
    compileSmartRemake,
    getSmartRemakeHealth,
    renderSmartRemake,
    type SmartRemakeCompileResult,
} from "@/shared/api/smart-remake";
import { AppShell } from "@/widgets/app-shell/app-shell";
import { Button } from "@/shared/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/ui/card";
import { PageHeader } from "@/shared/ui/page-header";
import { StatusChip } from "@/shared/ui/status-chip";
import { SurfaceCard } from "@/shared/ui/surface-card";
import { Textarea } from "@/shared/ui/textarea";
import { cn } from "@/shared/lib/utils";

export const Route = createFileRoute("/smart-remake")({
    head: () => ({ meta: [{ title: "Smart Remake - Viraldy" }] }),
    component: SmartRemakePage,
});

const MAX_VIDEO_BYTES = 30 * 1024 * 1024;
const MAX_IMAGE_BYTES = 10 * 1024 * 1024;
const ANALYSIS_STEPS = [
    "Đang xem video mẫu của bạn",
    "Đang nhận diện sản phẩm",
    "Đang viết kịch bản video mới",
] as const;

type CompileAssets = {
    referenceVideo: File;
    productImage: File;
};

type SmartRemakeRenderState = {
    finalVideoUrl: string;
    status: string;
    warnings: string[];
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
    const [language, setLanguage] = useState("Vietnamese");
    const [prompt, setPrompt] = useState(
        "Giữ năng lượng và nhịp dựng của video mẫu, nhưng làm nổi bật sản phẩm của tôi ngay từ đầu.",
    );
    const [description, setDescription] = useState(
        "Giữ đúng màu sắc, logo, hình dáng và cách sử dụng thực tế của sản phẩm.",
    );
    const [referenceVideo, setReferenceVideo] = useState<File | null>(null);
    const [productImage, setProductImage] = useState<File | null>(null);
    const [compileResult, setCompileResult] = useState<SmartRemakeCompileResult | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [result, setResult] = useState<SmartRemakeRenderState | null>(null);
    const [analysisStep, setAnalysisStep] = useState(0);
    const referencePreviewUrl = usePreviewUrl(referenceVideo);
    const productPreviewUrl = usePreviewUrl(productImage);

    const compile = useMutation({
        mutationFn: ({ referenceVideo, productImage }: CompileAssets) => {
            if (!workspaceId) throw new Error("Chọn workspace trước khi phân tích video.");
            return compileSmartRemake(workspaceId, {
                targetDuration: duration,
                language,
                prompt,
                description,
                referenceVideo,
                productImage,
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

    useEffect(() => {
        if (!compile.isPending) return;
        const timer = window.setInterval(
            () => setAnalysisStep((step) => Math.min(step + 1, ANALYSIS_STEPS.length - 1)),
            12_000,
        );
        return () => window.clearInterval(timer);
    }, [compile.isPending]);
    const render = useMutation({
        mutationFn: () => {
            if (!workspaceId || !compileResult || !productImage)
                throw new Error("Compile a remake before rendering.");
            return renderSmartRemake(workspaceId, {
                compileResult,
                productImage,
                provider: health.data?.mode === "fixture" ? "fixture" : "unifically",
                projectName: `Smart Remake ${duration}s`,
            });
        },
        onMutate: () => {
            setError(null);
        },
        onSuccess: (data) =>
            setResult({
                finalVideoUrl: data.finalVideoUrl,
                status: data.status,
                warnings: data.warnings,
            }),
        onError: (cause) =>
            setError(cause instanceof Error ? cause.message : "Smart Remake render failed."),
    });

    const chooseFile = (file: File | null, kind: "video" | "image") => {
        if (!file || compile.isPending) return;
        const validType =
            kind === "video"
                ? ["video/mp4", "video/webm", "video/quicktime"].includes(file.type)
                : ["image/jpeg", "image/png", "image/webp"].includes(file.type);
        const max = kind === "video" ? MAX_VIDEO_BYTES : MAX_IMAGE_BYTES;
        if (!validType) {
            setError(`Unsupported ${kind} file type.`);
            return;
        }
        if (file.size > max) {
            setError(`${kind === "video" ? "Reference video" : "Product image"} is too large.`);
            return;
        }
        setError(null);
        const nextReferenceVideo = kind === "video" ? file : referenceVideo;
        const nextProductImage = kind === "image" ? file : productImage;
        setReferenceVideo(nextReferenceVideo);
        setProductImage(nextProductImage);
        setCompileResult(null);
        setResult(null);
        if (nextReferenceVideo && nextProductImage) {
            compile.mutate({
                referenceVideo: nextReferenceVideo,
                productImage: nextProductImage,
            });
        }
    };

    const disabled = !workspaceId || !referenceVideo || !productImage || compile.isPending;
    return (
        <AppShell>
            <div className="space-y-6">
                <PageHeader
                    title="Smart Remake"
                    description="Chọn video dọc và ảnh sản phẩm. Chúng tôi sẽ tự tạo kịch bản 8 hoặc 16 giây cho bạn."
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
                    referencePreviewUrl={referencePreviewUrl}
                    productImage={productImage}
                    productPreviewUrl={productPreviewUrl}
                    compileResult={compileResult}
                    result={result}
                    isCompiling={compile.isPending}
                    isRendering={render.isPending}
                    analysisStep={analysisStep}
                    uploadDisabled={compile.isPending}
                    onReferenceVideoChange={(file) => chooseFile(file, "video")}
                    onProductImageChange={(file) => chooseFile(file, "image")}
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
                                                · Dọc 9:16
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
                                        className="flex h-10 w-full rounded-[10px] border border-control-border bg-surface px-3 text-sm"
                                    />
                                </label>
                                <label className="space-y-2 text-sm font-medium text-text-primary">
                                    Phong cách bạn muốn
                                    <Textarea
                                        value={prompt}
                                        onChange={(event) => setPrompt(event.target.value)}
                                        rows={3}
                                    />
                                </label>
                            </div>
                            <label className="block space-y-2 text-sm font-medium text-text-primary">
                                Những điều phải giữ nguyên
                                <Textarea
                                    value={description}
                                    onChange={(event) => setDescription(event.target.value)}
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
                                    if (referenceVideo && productImage) {
                                        compile.mutate({ referenceVideo, productImage });
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
                                        {compileResult
                                            ? "Phân tích lại video"
                                            : "Tự động phân tích sau khi chọn đủ hai file"}
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
                                        : "Kịch bản sẽ tự xuất hiện sau khi bạn chọn đủ video và ảnh."}
                                </CardDescription>
                            </CardHeader>
                            <CardContent>
                                {compileResult ? (
                                    <CompilePreview result={compileResult} />
                                ) : (
                                    <div className="flex min-h-48 flex-col items-center justify-center rounded-lg border border-dashed border-control-border bg-surface-soft text-center text-sm text-text-secondary">
                                        <Sparkles className="mb-3 size-8 text-primary/60" />
                                        <span>Chọn video dọc và ảnh sản phẩm để bắt đầu.</span>
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
                                                Đang gửi yêu cầu tạo video…
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
                                            {result.warnings.map((warning) => (
                                                <p key={warning} className="text-text-secondary">
                                                    {warning}
                                                </p>
                                            ))}
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
    referencePreviewUrl,
    productImage,
    productPreviewUrl,
    compileResult,
    result,
    isCompiling,
    isRendering,
    analysisStep,
    uploadDisabled,
    onReferenceVideoChange,
    onProductImageChange,
}: {
    referenceVideo: File | null;
    referencePreviewUrl: string | null;
    productImage: File | null;
    productPreviewUrl: string | null;
    compileResult: SmartRemakeCompileResult | null;
    result: SmartRemakeRenderState | null;
    isCompiling: boolean;
    isRendering: boolean;
    analysisStep: number;
    uploadDisabled: boolean;
    onReferenceVideoChange: (file: File | null) => void;
    onProductImageChange: (file: File | null) => void;
}) {
    return (
        <Card className="overflow-hidden">
            <CardHeader className="border-b border-control-border bg-surface-soft/50">
                <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="space-y-1">
                        <CardTitle>Video của bạn sẽ được làm mới như thế nào?</CardTitle>
                        <CardDescription>
                            Video mẫu → sản phẩm của bạn → video mới, luôn ở định dạng dọc 9:16.
                        </CardDescription>
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
                <div className="grid items-stretch gap-3 md:grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)_auto_minmax(0,1fr)]">
                    <FlowInputSlot
                        label="Reference video"
                        icon={FileVideo}
                        file={referenceVideo}
                        accept="video/mp4,video/webm,video/quicktime"
                        description="MP4, MOV, or WebM · up to 30 MB"
                        previewUrl={referencePreviewUrl}
                        portraitFrame
                        disabled={uploadDisabled}
                        onChange={onReferenceVideoChange}
                    />
                    <FlowArrow />
                    <FlowInputSlot
                        label="Product image"
                        icon={FileImage}
                        file={productImage}
                        accept="image/jpeg,image/png,image/webp"
                        description="JPG, PNG, or WebP · up to 10 MB"
                        previewUrl={productPreviewUrl}
                        isProduct
                        disabled={uploadDisabled}
                        onChange={onProductImageChange}
                    />
                    <FlowArrow />
                    <OutputSlot
                        compileResult={compileResult}
                        isCompiling={isCompiling}
                        isRendering={isRendering}
                        analysisStep={analysisStep}
                        result={result}
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
    onChange: (file: File | null) => void;
}) {
    const ref = useRef<HTMLInputElement>(null);
    const isVideo = accept.startsWith("video/");

    return (
        <SurfaceCard
            className={cn("h-full", isProduct && "border-primary/35 bg-primary/[0.03]")}
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
                                    aria-hidden="true"
                                    className="size-full object-cover"
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
                                    {portraitFrame
                                        ? "Chọn video dọc"
                                        : `Chọn ${label.toLowerCase()}`}
                                </span>
                            </span>
                        )}
                        {previewUrl && !disabled && (
                            <span className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-surface to-transparent px-3 pb-3 pt-8 text-left text-xs font-medium text-text-primary opacity-0 transition-opacity group-hover:opacity-100 group-focus-visible:opacity-100">
                                Thay {label.toLowerCase()}
                            </span>
                        )}
                        {portraitFrame && (
                            <span className="absolute right-2 top-2 rounded-md bg-surface/90 px-2 py-1 text-[10px] font-semibold text-text-primary shadow-sm">
                                9:16
                            </span>
                        )}
                    </button>
                </div>
                <div className="space-y-1">
                    <p className="truncate text-sm font-medium text-text-primary">
                        {file?.name ?? (isProduct ? "Ảnh sản phẩm của bạn" : "Video dọc làm mẫu")}
                    </p>
                    <p className="text-xs text-text-secondary">
                        {portraitFrame ? "Chỉ nhận video dọc 9:16 · " : ""}
                        {description}
                    </p>
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

function FlowArrow() {
    return (
        <div className="flex items-center justify-center" aria-hidden="true">
            <div className="grid size-9 rotate-90 place-items-center rounded-full border border-control-border bg-surface text-primary shadow-sm md:rotate-0">
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
}: {
    compileResult: SmartRemakeCompileResult | null;
    result: SmartRemakeRenderState | null;
    isCompiling: boolean;
    isRendering: boolean;
    analysisStep: number;
}) {
    const completedVideo = result?.status === "completed" ? result.finalVideoUrl : null;
    const statusLabel = isRendering
        ? "Đang tạo video mới"
        : isCompiling
          ? ANALYSIS_STEPS[analysisStep]
          : completedVideo
            ? "Video đã tạo"
            : compileResult
              ? "Sẵn sàng tạo video"
              : "Đợi video và ảnh";

    return (
        <SurfaceCard
            className="h-full"
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
                            playsInline
                            preload="metadata"
                            src={completedVideo}
                        />
                    ) : isCompiling || isRendering ? (
                        <Loader2
                            className="size-7 animate-spin text-primary"
                            aria-label={statusLabel}
                        />
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
                        {compileResult
                            ? `${compileResult.sceneMap.sceneCount === 1 ? "Một phần nội dung" : "Hai phần nội dung"} · ${compileResult.inputSummary.targetDuration} giây`
                            : "Sau khi chọn đủ video và ảnh, chúng tôi sẽ tự bắt đầu."}
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

    const activeStep = complete ? ANALYSIS_STEPS.length : step;
    return (
        <div
            className="mt-5 rounded-lg border border-control-border bg-surface-soft p-4"
            aria-live="polite"
        >
            <div className="mb-3 flex items-center justify-between gap-3">
                <p className="text-sm font-medium text-text-primary">
                    {complete ? "Kịch bản đã sẵn sàng" : "Đang chuẩn bị video của bạn"}
                </p>
                <span className="text-xs text-text-secondary">
                    {complete ? "Hoàn tất" : "Thường mất 2–5 phút"}
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
            <ol className="grid gap-2 sm:grid-cols-3">
                {ANALYSIS_STEPS.map((label, index) => {
                    const done = complete || index < step;
                    const current = !complete && index === step;
                    return (
                        <li className="flex items-center gap-2 text-sm" key={label}>
                            <span
                                className={cn(
                                    "grid size-5 shrink-0 place-items-center rounded-full border text-[10px] font-semibold",
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
                            <span
                                className={cn(
                                    done || current ? "text-text-primary" : "text-text-secondary",
                                )}
                            >
                                {label}
                            </span>
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
