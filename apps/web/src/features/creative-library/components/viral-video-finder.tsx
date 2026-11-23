import { useEffect, useRef, useState, type ChangeEvent, type DragEvent } from "react";
import { useNavigate } from "@tanstack/react-router";
import { ArrowRight, ImagePlus, Loader2, Sparkles, Trash2, Upload } from "lucide-react";

import {
    DEMO_SEARCH_DELAY_MS,
    getDemoVideoResults,
    validateProductImages,
    type ViralVideoRecommendation,
} from "@/features/creative-library/lib/viral-video-demo";
import type { CreativeReference } from "@/features/creative-library/types/creative";
import { setSmartRemakeHandoff } from "@/features/smart-remake/lib/smart-remake-handoff";
import { captureVideoPoster } from "@/shared/lib/demo-media";
import { Button } from "@/shared/ui/button";
import { SurfaceCard } from "@/shared/ui/surface-card";
import { cn } from "@/shared/lib/utils";

type UploadedImage = { id: string; file: File; previewUrl: string };

const SEARCH_STEPS = [
    "Đang chuẩn bị ảnh sản phẩm của bạn",
    "Đang tìm các cách giới thiệu sản phẩm thu hút",
    "Đang chọn video mẫu để bạn tham khảo",
] as const;

export function ViralVideoFinder() {
    const navigate = useNavigate();
    const inputRef = useRef<HTMLInputElement>(null);
    const objectUrlsRef = useRef(new Set<string>());
    const [images, setImages] = useState<UploadedImage[]>([]);
    const [results, setResults] = useState<ViralVideoRecommendation[]>([]);
    const [posters, setPosters] = useState<Record<string, string>>({});
    const [searching, setSearching] = useState(false);
    const [searchStep, setSearchStep] = useState(0);
    const [choosingVideoId, setChoosingVideoId] = useState<string | null>(null);
    const [isDragging, setIsDragging] = useState(false);
    const [error, setError] = useState<string | null>(null);

    useEffect(
        () => () => {
            for (const url of objectUrlsRef.current) URL.revokeObjectURL(url);
            objectUrlsRef.current.clear();
        },
        [],
    );

    useEffect(() => {
        if (!results.length) {
            setPosters({});
            return;
        }

        let cancelled = false;
        void Promise.all(
            results.map(async (video) => ({
                id: video.id,
                poster: video.mediaUrl ? await captureVideoPoster(video.mediaUrl) : undefined,
            })),
        ).then((entries) => {
            if (cancelled) return;
            setPosters(
                Object.fromEntries(
                    entries.flatMap(({ id, poster }) => (poster ? [[id, poster]] : [])),
                ),
            );
        });

        return () => {
            cancelled = true;
        };
    }, [results]);

    useEffect(() => {
        if (!images.length) {
            setSearching(false);
            setSearchStep(0);
            setResults([]);
            return;
        }

        setSearching(true);
        setSearchStep(0);
        setResults([]);
        let cancelled = false;
        const stepTimer = window.setInterval(
            () => setSearchStep((step) => Math.min(step + 1, SEARCH_STEPS.length - 1)),
            550,
        );
        const resultTimer = window.setTimeout(() => {
            void getDemoVideoResults().then((videos) => {
                if (cancelled) return;
                setResults(videos);
                setSearching(false);
            });
        }, DEMO_SEARCH_DELAY_MS);

        return () => {
            cancelled = true;
            window.clearInterval(stepTimer);
            window.clearTimeout(resultTimer);
        };
    }, [images]);

    function addImages(files: File[]) {
        if (!files.length) return;
        const validation = validateProductImages(files);
        const accepted = validation.accepted.filter(
            (file) => !images.some((image) => sameFile(image.file, file)),
        );

        if (validation.rejected.length) {
            setError("Một vài ảnh chưa thêm được. Hãy chọn lại ảnh sản phẩm phù hợp nhé.");
        } else {
            setError(null);
        }

        if (!accepted.length) return;
        const additions = accepted.map((file) => {
            const previewUrl = URL.createObjectURL(file);
            objectUrlsRef.current.add(previewUrl);
            return { id: imageId(file), file, previewUrl };
        });
        setImages((current) => [...current, ...additions]);
    }

    function onFileChange(event: ChangeEvent<HTMLInputElement>) {
        addImages(Array.from(event.currentTarget.files ?? []));
        event.currentTarget.value = "";
    }

    function onDrop(event: DragEvent<HTMLDivElement>) {
        event.preventDefault();
        setIsDragging(false);
        addImages(Array.from(event.dataTransfer.files));
    }

    function removeImage(id: string) {
        const removed = images.find((image) => image.id === id);
        if (removed) {
            URL.revokeObjectURL(removed.previewUrl);
            objectUrlsRef.current.delete(removed.previewUrl);
        }
        setImages((current) => current.filter((image) => image.id !== id));
        setError(null);
    }

    async function chooseVideo(video: CreativeReference) {
        if (!video.mediaUrl || choosingVideoId) return;
        setChoosingVideoId(video.id);
        setError(null);

        try {
            const response = await fetch(video.mediaUrl);
            if (!response.ok) throw new Error("Could not load the selected demo video.");
            const blob = await response.blob();
            const filename = video.mediaUrl.split("/").at(-1) ?? `${video.id}.mp4`;
            const referenceVideo = new File([blob], filename, {
                type: blob.type || "video/mp4",
            });
            setSmartRemakeHandoff({
                referenceVideo,
                productImages: images.map((image) => image.file),
            });
            await navigate({ to: "/smart-remake" });
        } catch {
            setChoosingVideoId(null);
            setError("Chưa mở được video mẫu này. Bạn thử chọn một video khác nhé.");
        }
    }

    const imageGridClass =
        images.length === 1
            ? "grid-cols-1"
            : images.length === 2
              ? "grid-cols-2"
              : "grid-cols-2 lg:grid-cols-3";

    return (
        <SurfaceCard padding="lg" className="min-w-0 space-y-5 overflow-hidden">
            <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                        <h2 className="text-base font-semibold text-text-primary">
                            Tìm video viral bằng ảnh sản phẩm
                        </h2>
                        <span className="rounded-full bg-primary/10 px-2 py-1 text-[10px] font-semibold text-primary">
                            DEMO
                        </span>
                    </div>
                    <p className="mt-1 text-sm text-text-secondary">
                        Tải ảnh lên để xem các video mẫu và chọn ý tưởng phù hợp.
                    </p>
                </div>
                {results.length > 0 && !searching && (
                    <span className="shrink-0 rounded-full bg-surface-soft px-2.5 py-1 text-xs text-text-secondary">
                        {results.length} video gợi ý
                    </span>
                )}
            </div>

            <input
                ref={inputRef}
                type="file"
                accept="image/jpeg,image/png,image/webp"
                multiple
                className="sr-only"
                aria-label="Tải ảnh sản phẩm lên"
                onChange={onFileChange}
            />

            {images.length === 0 ? (
                <div
                    onDragEnter={(event) => {
                        event.preventDefault();
                        setIsDragging(true);
                    }}
                    onDragOver={(event) => event.preventDefault()}
                    onDragLeave={(event) => {
                        if (!event.currentTarget.contains(event.relatedTarget as Node | null)) {
                            setIsDragging(false);
                        }
                    }}
                    onDrop={onDrop}
                    className={cn(
                        "rounded-2xl border border-dashed p-6 transition-colors sm:p-8",
                        isDragging
                            ? "border-primary bg-primary/[0.06]"
                            : "border-control-border bg-surface-soft/50",
                    )}
                >
                    <button
                        type="button"
                        onClick={() => inputRef.current?.click()}
                        className="flex min-h-36 w-full flex-col items-center justify-center rounded-xl text-center focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                    >
                        <span className="grid size-12 place-items-center rounded-2xl bg-primary/10 text-primary">
                            <ImagePlus className="size-6" aria-hidden />
                        </span>
                        <span className="mt-3 text-sm font-semibold text-text-primary">
                            Tải ảnh sản phẩm lên
                        </span>
                        <span className="mt-1 text-xs text-text-secondary">
                            Kéo ảnh vào đây hoặc nhấn để chọn
                        </span>
                    </button>
                </div>
            ) : (
                <div className="space-y-3">
                    <div className={cn("grid gap-3", imageGridClass)}>
                        {images.map((image, index) => (
                            <div
                                key={image.id}
                                className="group relative min-w-0 overflow-hidden rounded-xl border border-control-border bg-surface-soft"
                            >
                                <div className="aspect-[4/3] w-full bg-white">
                                    <img
                                        src={image.previewUrl}
                                        alt={`Ảnh sản phẩm ${index + 1}`}
                                        className="h-full w-full object-contain"
                                    />
                                </div>
                                <div className="flex min-w-0 items-center justify-between gap-2 border-t border-control-border/60 bg-surface px-3 py-2">
                                    <span className="min-w-0 truncate text-xs text-text-secondary">
                                        {image.file.name}
                                    </span>
                                    <button
                                        type="button"
                                        onClick={() => removeImage(image.id)}
                                        aria-label={`Xóa ảnh sản phẩm ${index + 1}`}
                                        className="grid size-8 shrink-0 place-items-center rounded-lg text-text-tertiary transition-colors hover:bg-destructive-soft hover:text-destructive focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                                    >
                                        <Trash2 className="size-4" aria-hidden />
                                    </button>
                                </div>
                            </div>
                        ))}
                    </div>
                    <Button
                        type="button"
                        variant="secondary"
                        size="sm"
                        onClick={() => inputRef.current?.click()}
                        className="w-full sm:w-auto"
                    >
                        <Upload className="size-4" />
                        Thêm ảnh sản phẩm
                    </Button>
                </div>
            )}

            {error && (
                <p
                    role="alert"
                    className="rounded-lg bg-destructive-soft px-3 py-2 text-sm text-destructive"
                >
                    {error}
                </p>
            )}

            {searching && (
                <div
                    role="status"
                    aria-live="polite"
                    className="rounded-2xl border border-primary/15 bg-primary/[0.035] p-4 sm:p-5"
                >
                    <div className="flex items-center gap-3">
                        <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-primary/10 text-primary">
                            <Loader2 className="size-5 animate-spin" aria-hidden />
                        </span>
                        <div className="min-w-0">
                            <p className="text-sm font-semibold text-text-primary">
                                {SEARCH_STEPS[searchStep]}
                            </p>
                            <p className="mt-0.5 text-xs text-text-secondary">
                                Sắp xong rồi, đang chuẩn bị video cho bạn.
                            </p>
                        </div>
                    </div>
                    <div className="mt-4 h-1.5 overflow-hidden rounded-full bg-primary/10">
                        <div
                            className="h-full rounded-full bg-primary transition-[width] duration-500"
                            style={{ width: `${((searchStep + 1) / SEARCH_STEPS.length) * 100}%` }}
                        />
                    </div>
                </div>
            )}

            {results.length > 0 && !searching && (
                <section aria-label="Video gợi ý" className="space-y-3">
                    <div className="flex flex-wrap items-end justify-between gap-2">
                        <div>
                            <h3 className="text-sm font-semibold text-text-primary">
                                Xếp hạng video gợi ý
                            </h3>
                            <p className="mt-0.5 text-xs text-text-secondary">
                                Mỗi video có phần xem trước riêng. Các chỉ số là dữ liệu demo để
                                tham khảo, không phải kết quả thực tế từ tài khoản quảng cáo.
                            </p>
                        </div>
                        <span className="text-xs text-text-tertiary">
                            Chọn một video để tiếp tục
                        </span>
                    </div>

                    <div className="grid min-w-0 gap-4 md:grid-cols-2 xl:grid-cols-3">
                        {results.map((video) => (
                            <DemoVideoCard
                                key={video.id}
                                video={video}
                                posterUrl={posters[video.id]}
                                isChoosing={choosingVideoId === video.id}
                                selectionDisabled={choosingVideoId !== null}
                                onChoose={() => void chooseVideo(video)}
                            />
                        ))}
                    </div>
                </section>
            )}
        </SurfaceCard>
    );
}

function DemoVideoCard({
    video,
    posterUrl,
    isChoosing,
    selectionDisabled,
    onChoose,
}: {
    video: ViralVideoRecommendation;
    posterUrl?: string;
    isChoosing: boolean;
    selectionDisabled: boolean;
    onChoose: () => void;
}) {
    return (
        <article className="flex min-w-0 flex-col overflow-hidden rounded-2xl border border-control-border bg-surface">
            <div className="relative mx-auto aspect-[9/16] w-full max-w-[280px] overflow-hidden bg-black">
                <video
                    src={video.mediaUrl}
                    poster={posterUrl ?? video.posterUrl ?? video.thumbnailUrl}
                    controls
                    playsInline
                    preload="metadata"
                    aria-label={`Xem trước: ${video.title}`}
                    className="h-full w-full object-cover"
                />
                <span className="absolute left-3 top-3 rounded-full bg-black/75 px-2.5 py-1 text-xs font-semibold text-white">
                    Hạng {video.rank}
                </span>
            </div>
            <div className="flex min-w-0 flex-1 flex-col p-3.5">
                <div className="flex flex-wrap items-center gap-1.5 text-[11px] text-text-tertiary">
                    <span className="rounded-full bg-surface-soft px-2 py-0.5 font-medium text-text-secondary">
                        {video.platform}
                    </span>
                    <span>{formatDuration(video.durationSec)}</span>
                    {video.angle && <span>· {video.angle}</span>}
                </div>
                <p className="mt-1 truncate font-mono text-[10px] text-text-tertiary">
                    {video.fileName}
                </p>
                <h4 className="mt-2 line-clamp-2 text-sm font-semibold leading-snug text-text-primary">
                    {video.title}
                </h4>
                <p className="mt-1 line-clamp-2 text-xs leading-5 text-text-secondary">
                    “{video.hookExcerpt}”
                </p>
                <p className="mt-2 truncate text-[11px] text-text-tertiary">
                    {video.brandOrCreator}
                </p>
                <div className="mt-3 rounded-xl border border-control-border bg-surface-soft p-2.5">
                    <p className="mb-2 text-[10px] font-medium text-text-tertiary">
                        Chỉ số demo · tham khảo
                    </p>
                    <div className="grid grid-cols-2 gap-2">
                        <FeaturedMetric
                            label="Doanh thu"
                            value={formatCurrency(video.metrics.revenue)}
                        />
                        <FeaturedMetric label="ROAS" value={`${video.metrics.roas.toFixed(1)}×`} />
                    </div>
                    <div className="mt-3 grid grid-cols-3 gap-x-2 gap-y-3 border-t border-control-border pt-3">
                        <MockMetric
                            label="Chi tiêu"
                            value={formatCurrency(video.metrics.adSpend)}
                        />
                        <MockMetric
                            label="Lượt xem"
                            value={formatCompact(video.metrics.videoViews)}
                        />
                        <MockMetric
                            label="Hiển thị"
                            value={formatCompact(video.metrics.impressions)}
                        />
                        <MockMetric label="Lượt thích" value={formatCompact(video.metrics.likes)} />
                        <MockMetric
                            label="Bình luận"
                            value={formatCompact(video.metrics.comments)}
                        />
                        <MockMetric label="Chia sẻ" value={formatCompact(video.metrics.shares)} />
                        <MockMetric label="Lượt nhấp" value={formatCompact(video.metrics.clicks)} />
                        <MockMetric label="Đơn hàng" value={formatCompact(video.metrics.orders)} />
                        <MockMetric label="CPC" value={formatCurrency(video.metrics.cpc)} />
                        <MockMetric label="CPA" value={formatCurrency(video.metrics.cpa)} />
                        <MockMetric label="CTR" value={`${video.metrics.ctr.toFixed(1)}%`} />
                        <MockMetric label="CVR" value={`${video.metrics.cvr.toFixed(1)}%`} />
                    </div>
                </div>
                <Button
                    type="button"
                    onClick={onChoose}
                    disabled={selectionDisabled}
                    className="mt-4 w-full"
                    size="sm"
                >
                    {isChoosing ? (
                        <>
                            <Loader2 className="size-4 animate-spin" />
                            Đang mở Smart Remake…
                        </>
                    ) : selectionDisabled ? (
                        "Đang chuẩn bị…"
                    ) : (
                        <>
                            <Sparkles className="size-4" />
                            Dùng video này
                            <ArrowRight className="ml-auto size-4" />
                        </>
                    )}
                </Button>
            </div>
        </article>
    );
}

function MockMetric({ label, value }: { label: string; value: string }) {
    return (
        <div className="min-w-0">
            <p className="text-[10px] text-text-tertiary">{label}</p>
            <p className="mt-0.5 truncate text-xs font-semibold tabular-nums text-text-primary">
                {value}
            </p>
        </div>
    );
}

function FeaturedMetric({ label, value }: { label: string; value: string }) {
    return (
        <div className="min-w-0 rounded-lg bg-surface px-2.5 py-2">
            <p className="text-[10px] text-text-tertiary">{label}</p>
            <p className="mt-1 truncate text-base font-semibold tabular-nums text-text-primary">
                {value}
            </p>
        </div>
    );
}

function sameFile(left: File, right: File) {
    return (
        left.name === right.name &&
        left.size === right.size &&
        left.lastModified === right.lastModified
    );
}

function imageId(file: File) {
    return `${file.name}:${file.size}:${file.lastModified}`;
}

function formatDuration(seconds: number) {
    return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
}

function formatCompact(value: number) {
    return new Intl.NumberFormat("vi-VN", {
        notation: "compact",
        maximumFractionDigits: 1,
    }).format(value);
}

function formatCurrency(value: number) {
    const formatted =
        value >= 1_000_000
            ? formatCompact(value)
            : new Intl.NumberFormat("vi-VN", { maximumFractionDigits: 0 }).format(value);
    return `${formatted} ₫`;
}
