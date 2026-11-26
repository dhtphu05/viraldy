import { Check, ChevronDown, Link2, Loader2, Plus, Upload, VideoOff, X } from "lucide-react";
import { useEffect, useId, useRef, useState, type DragEvent } from "react";

import { cn } from "@/shared/lib/utils";
import { Button } from "@/shared/ui/button";
import { Input } from "@/shared/ui/input";
import { Textarea } from "@/shared/ui/textarea";
import referenceVideoIllustration from "@/assets/smart-remake/reference-video.webp";
import productReferenceIllustration from "@/assets/smart-remake/product-reference.webp";
import { RemakeVideoLibrary } from "./remake-video-library";
import { RemakeBoundaryControls } from "./remake-source-timeline";
import { RemakeImagePreview } from "./remake-image-preview";
import "./remake-inputs.css";

export interface RemakeInputsProps {
    sourceUrl: string | null;
    sourceName: string | null;
    productUrls: string[];
    primaryIndex: number;
    onPrimaryChange: (index: number) => void;
    onVideo: (file: File) => void;
    onImages: (files: File[]) => void;
    onRemoveImage: (index: number) => void;
    link: string;
    onLinkChange: (value: string) => void;
    onLinkSubmit: () => void;
    isLinkLoading: boolean;
    linkedTitle?: string;
    duration: 8 | 16;
    onDuration: (duration: 8 | 16) => void;
    language: string;
    onLanguage: (value: string) => void;
    description: string;
    onDescription: (value: string) => void;
    brief: string;
    onBrief: (value: string) => void;
    disabled: boolean;
    onSample?: () => void;
    isSample?: boolean;
    timelineStartFrame?: number;
    onTimelineStartFrameChange?: (frame: number) => void;
    onSourceMetadata?: (durationSeconds: number) => void;
    sourceDurationSeconds?: number | null;
    sourceCutFrames?: number[];
    onSourceCutFramesChange?: (cuts: number[]) => void;
    validationErrors?: { video?: string; product?: string };
}

const fieldClass =
    "border-0 bg-surface-soft shadow-none focus-visible:ring-2 focus-visible:ring-ring/60";
const quietButton =
    "min-h-11 border-0 bg-surface-soft shadow-none hover:bg-surface-muted motion-reduce:transform-none";

export function RemakeInputs(props: RemakeInputsProps) {
    const videoInput = useRef<HTMLInputElement>(null);
    const imageInput = useRef<HTMLInputElement>(null);
    const id = useId();
    const [dragging, setDragging] = useState<"video" | "image" | null>(null);
    const [videoMetadata, setVideoMetadata] = useState({ url: "", ratio: 9 / 16 });
    const [videoPreview, setVideoPreview] = useState<{
        url: string;
        status: "ready" | "error";
    } | null>(null);
    const [sourceDuration, setSourceDuration] = useState<{ url: string; seconds: number } | null>(
        null,
    );
    const busy = props.disabled || props.isLinkLoading;
    const primaryUrl = props.productUrls[props.primaryIndex] ?? props.productUrls[0];
    const ratio = videoMetadata.url === props.sourceUrl ? videoMetadata.ratio : 9 / 16;
    const videoStatus = videoPreview?.url === props.sourceUrl ? videoPreview.status : "loading";
    const measuredSourceDuration =
        sourceDuration?.url === props.sourceUrl
            ? sourceDuration.seconds
            : (props.sourceDurationSeconds ?? null);

    useEffect(() => {
        if (!props.sourceUrl || videoStatus !== "loading") return;
        const url = props.sourceUrl;
        const timeout = window.setTimeout(() => setVideoPreview({ url, status: "error" }), 15000);
        return () => window.clearTimeout(timeout);
    }, [props.sourceUrl, videoStatus]);

    const drop = (event: DragEvent, kind: "video" | "image") => {
        event.preventDefault();
        setDragging(null);
        if (busy) return;
        const files = Array.from(event.dataTransfer.files);
        if (kind === "video" && files[0]) props.onVideo(files[0]);
        if (kind === "image" && files.length) props.onImages(files);
    };

    return (
        <div className="mx-auto w-full max-w-4xl space-y-6">
            <div className="grid items-stretch gap-5 sm:grid-cols-2">
                <section
                    data-interactive={!busy}
                    data-dragging={dragging === "video"}
                    aria-labelledby={`${id}-video-title`}
                    aria-describedby={
                        props.validationErrors?.video ? `${id}-video-error` : undefined
                    }
                    className={cn(
                        "remake-input-card min-w-0 rounded-3xl bg-surface p-5 shadow-[0_8px_32px_rgb(0_0_0/0.035)] transition-[background-color,box-shadow] duration-150 motion-reduce:transition-none",
                        dragging === "video" && "bg-primary-soft ring-2 ring-primary/40",
                    )}
                    onDragOver={(event) => {
                        event.preventDefault();
                        if (!busy) setDragging("video");
                    }}
                    onDragLeave={(event) => {
                        if (!event.currentTarget.contains(event.relatedTarget as Node | null))
                            setDragging(null);
                    }}
                    onDrop={(event) => drop(event, "video")}
                >
                    <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
                        <h2 id={`${id}-video-title`} className="font-semibold text-text-primary">
                            Video mẫu
                        </h2>
                        <span className="inline-flex items-center gap-1.5 rounded-full bg-surface-soft px-2.5 py-1 text-xs text-text-secondary">
                            {props.isSample ? (
                                "Minh họa"
                            ) : props.sourceUrl ? (
                                <>
                                    <Check className="size-3.5" aria-hidden="true" /> Đã thêm
                                </>
                            ) : (
                                "Chưa chọn"
                            )}
                        </span>
                    </div>
                    {props.validationErrors?.video && (
                        <p
                            id={`${id}-video-error`}
                            role="alert"
                            className="mb-3 text-sm text-destructive"
                        >
                            {props.validationErrors.video}
                        </p>
                    )}
                    <div
                        className={cn(
                            "flex min-h-[min(42svh,320px)] items-center justify-center rounded-2xl p-3",
                            props.sourceUrl
                                ? "remake-source-stage"
                                : "remake-input-empty bg-surface-soft",
                        )}
                    >
                        {props.sourceUrl ? (
                            <>
                                <video
                                    key={props.sourceUrl}
                                    src={props.sourceUrl}
                                    controls
                                    playsInline
                                    preload="metadata"
                                    aria-label="Xem video mẫu"
                                    className="remake-source-stage__video block h-auto max-h-[min(42svh,320px)] max-w-full rounded-xl bg-black object-contain"
                                    style={{
                                        aspectRatio: ratio,
                                        width: `min(100%, calc(min(42svh, 320px) * ${ratio}))`,
                                        opacity: videoStatus === "ready" ? 1 : 0,
                                        visibility: videoStatus === "ready" ? "visible" : "hidden",
                                    }}
                                    onLoadedMetadata={(event) => {
                                        const media = event.currentTarget;
                                        setVideoPreview({ url: props.sourceUrl!, status: "ready" });
                                        if (Number.isFinite(media.duration) && media.duration > 0) {
                                            setSourceDuration({
                                                url: props.sourceUrl!,
                                                seconds: media.duration,
                                            });
                                            props.onSourceMetadata?.(media.duration);
                                        }
                                        if (media.videoWidth && media.videoHeight)
                                            setVideoMetadata({
                                                url: props.sourceUrl!,
                                                ratio: media.videoWidth / media.videoHeight,
                                            });
                                    }}
                                    onError={() =>
                                        setVideoPreview({ url: props.sourceUrl!, status: "error" })
                                    }
                                />
                                {videoStatus !== "ready" && (
                                    <div
                                        className="remake-source-stage__feedback"
                                        role={videoStatus === "error" ? "alert" : "status"}
                                    >
                                        {videoStatus === "error" ? (
                                            <VideoOff className="size-6" aria-hidden="true" />
                                        ) : (
                                            <Loader2
                                                className="size-6 animate-spin motion-reduce:animate-none"
                                                aria-hidden="true"
                                            />
                                        )}
                                        <p>
                                            {videoStatus === "error"
                                                ? "Chưa mở được video. Chọn lại file hoặc thử video khác nhé."
                                                : "Đang mở video mẫu…"}
                                        </p>
                                    </div>
                                )}
                            </>
                        ) : (
                            <div className="relative space-y-3 px-4 py-5 text-center">
                                <img
                                    src={referenceVideoIllustration}
                                    alt=""
                                    width={192}
                                    height={128}
                                    draggable={false}
                                    className="remake-input-illustration mx-auto h-28 w-48 max-w-full object-contain sm:h-32"
                                    aria-hidden="true"
                                />
                                <p className="text-sm text-text-secondary">
                                    Chọn video có cách quay
                                    <br />
                                    hoặc mở đầu bạn thích.
                                </p>
                                <p className="text-xs text-text-tertiary">
                                    Kéo video vào đây hoặc chọn file bên dưới
                                </p>
                            </div>
                        )}
                    </div>
                    {props.sourceUrl && (
                        <div className="mt-4 space-y-2 rounded-2xl bg-surface-soft/70 p-4">
                            <h3 className="text-sm font-medium text-text-primary">
                                Phân tích toàn bộ video
                            </h3>
                            <p className="text-xs tabular-nums text-text-secondary">
                                {measuredSourceDuration !== null &&
                                Number.isFinite(measuredSourceDuration) &&
                                measuredSourceDuration > 0
                                    ? `${Number(measuredSourceDuration.toFixed(3)).toLocaleString("vi-VN")} giây tư liệu`
                                    : videoStatus === "error"
                                      ? "Chưa đọc được thời lượng video mẫu"
                                      : "Đang đọc thời lượng video mẫu…"}
                            </p>
                            <p className="text-xs leading-relaxed text-text-secondary">
                                AI phân tích tất cả cảnh trong video mẫu, rồi phân bổ thời lượng cho
                                kịch bản {props.duration} giây của bạn.
                            </p>
                        </div>
                    )}
                    {props.sourceUrl && props.sourceCutFrames && props.onSourceCutFramesChange && (
                        <div className="mt-4 space-y-3">
                            <h3 className="text-sm font-semibold text-text-primary">
                                Nhịp cắt của video mẫu
                            </h3>
                            <p className="text-xs leading-relaxed text-text-secondary">
                                Giữ các mốc AI đã nhận diện hoặc điều chỉnh nếu cần. Hệ thống sẽ tự
                                chia lượt tạo video theo kịch bản.
                            </p>
                            <RemakeBoundaryControls
                                sourceCutFrames={props.sourceCutFrames}
                                totalFrames={
                                    measuredSourceDuration !== null
                                        ? Math.round(measuredSourceDuration * 24)
                                        : (props.sourceCutFrames.at(-1) ?? 0)
                                }
                                onCutsChange={props.onSourceCutFramesChange}
                                disabled={busy}
                            />
                        </div>
                    )}
                    <p
                        className="mt-3 min-h-5 truncate text-xs text-text-secondary"
                        title={props.sourceName ?? undefined}
                    >
                        {props.sourceName ?? "MP4, WebM hoặc MOV · Tối đa 30 MB"}
                    </p>
                    <input
                        ref={videoInput}
                        type="file"
                        accept="video/mp4,video/webm,video/quicktime"
                        className="hidden"
                        aria-label="Chọn file video mẫu"
                        aria-invalid={Boolean(props.validationErrors?.video)}
                        aria-describedby={
                            props.validationErrors?.video ? `${id}-video-error` : undefined
                        }
                        disabled={busy}
                        onChange={(event) => {
                            const file = event.currentTarget.files?.[0];
                            if (file) props.onVideo(file);
                            event.currentTarget.value = "";
                        }}
                    />
                    <div className="mt-3 grid gap-2">
                        <Button
                            type="button"
                            variant="ghost"
                            className={cn(quietButton, "w-full")}
                            disabled={busy}
                            onClick={() => videoInput.current?.click()}
                            aria-describedby={
                                props.validationErrors?.video ? `${id}-video-error` : undefined
                            }
                        >
                            <Upload aria-hidden="true" />
                            {props.sourceUrl ? "Chọn video khác" : "Chọn video từ máy"}
                        </Button>
                        <RemakeVideoLibrary disabled={busy} onVideo={props.onVideo} />
                    </div>
                </section>

                <section
                    data-interactive={!busy}
                    data-dragging={dragging === "image"}
                    aria-labelledby={`${id}-product-title`}
                    aria-describedby={
                        props.validationErrors?.product ? `${id}-product-error` : undefined
                    }
                    className={cn(
                        "remake-input-card min-w-0 rounded-3xl bg-surface p-5 shadow-[0_8px_32px_rgb(0_0_0/0.035)] transition-[background-color,box-shadow] duration-150 motion-reduce:transition-none",
                        dragging === "image" && "bg-primary-soft ring-2 ring-primary/40",
                    )}
                    onDragOver={(event) => {
                        event.preventDefault();
                        if (!busy) setDragging("image");
                    }}
                    onDragLeave={(event) => {
                        if (!event.currentTarget.contains(event.relatedTarget as Node | null))
                            setDragging(null);
                    }}
                    onDrop={(event) => drop(event, "image")}
                >
                    <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
                        <h2 id={`${id}-product-title`} className="font-semibold text-text-primary">
                            Sản phẩm của bạn
                        </h2>
                        <span className="rounded-full bg-surface-soft px-2.5 py-1 text-xs text-text-secondary">
                            {props.isSample ? "Minh họa" : primaryUrl ? "Ảnh chính" : "Chưa chọn"}
                        </span>
                    </div>
                    {props.validationErrors?.product && (
                        <p
                            id={`${id}-product-error`}
                            role="alert"
                            className="mb-3 text-sm text-destructive"
                        >
                            {props.validationErrors.product}
                        </p>
                    )}
                    <div
                        className={cn(
                            "flex min-h-[min(42svh,320px)] items-center justify-center rounded-2xl bg-surface-soft",
                            primaryUrl ? "remake-product-stage" : "remake-input-empty p-3",
                        )}
                    >
                        {primaryUrl ? (
                            <RemakeImagePreview
                                src={primaryUrl}
                                alt={props.linkedTitle || "Ảnh sản phẩm đang dùng làm tham chiếu"}
                                enlarge
                                disabled={busy}
                            />
                        ) : (
                            <div className="relative space-y-3 px-4 py-5 text-center">
                                <img
                                    src={productReferenceIllustration}
                                    alt=""
                                    width={192}
                                    height={128}
                                    draggable={false}
                                    className="remake-input-illustration mx-auto h-28 w-48 max-w-full object-contain sm:h-32"
                                    aria-hidden="true"
                                />
                                <p className="text-sm text-text-secondary">
                                    Chọn ảnh rõ nhất của đúng
                                    <br />
                                    sản phẩm bạn đang bán.
                                </p>
                                <p className="text-xs text-text-tertiary">
                                    JPG, PNG hoặc WebP · Tối đa 10 MB/ảnh
                                </p>
                            </div>
                        )}
                    </div>
                    <p className="mt-3 min-h-5 truncate text-xs text-text-secondary">
                        {props.linkedTitle ||
                            (primaryUrl
                                ? "AI dùng ảnh chính này làm tham chiếu."
                                : "Có thể thêm nhiều ảnh và chọn một ảnh chính.")}
                    </p>
                    <input
                        ref={imageInput}
                        type="file"
                        accept="image/jpeg,image/png,image/webp"
                        multiple
                        className="hidden"
                        aria-label="Chọn ảnh sản phẩm"
                        aria-invalid={Boolean(props.validationErrors?.product)}
                        aria-describedby={
                            props.validationErrors?.product ? `${id}-product-error` : undefined
                        }
                        disabled={busy}
                        onChange={(event) => {
                            props.onImages(Array.from(event.currentTarget.files ?? []));
                            event.currentTarget.value = "";
                        }}
                    />
                    <Button
                        type="button"
                        variant="ghost"
                        className={cn(quietButton, "mt-3 w-full")}
                        disabled={busy}
                        onClick={() => imageInput.current?.click()}
                        aria-describedby={
                            props.validationErrors?.product ? `${id}-product-error` : undefined
                        }
                    >
                        <Plus aria-hidden="true" />
                        Thêm ảnh sản phẩm
                    </Button>
                    {props.productUrls.length > 0 && (
                        <div
                            className="remake-product-gallery mt-4 flex flex-wrap gap-3"
                            aria-label="Các ảnh sản phẩm"
                        >
                            {props.productUrls.map((url, index) => (
                                <div key={`${url}-${index}`} className="w-20 space-y-1">
                                    <button
                                        type="button"
                                        className={cn(
                                            "relative flex h-20 w-20 items-center justify-center overflow-hidden rounded-xl bg-surface-soft transition-[background-color,box-shadow] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50 motion-reduce:transition-none",
                                            index === props.primaryIndex &&
                                                "bg-primary-soft ring-2 ring-primary/50",
                                        )}
                                        aria-label={`Dùng ảnh ${index + 1} làm ảnh chính`}
                                        aria-pressed={index === props.primaryIndex}
                                        disabled={busy}
                                        onClick={() => props.onPrimaryChange(index)}
                                    >
                                        <RemakeImagePreview
                                            src={url}
                                            alt={`Ảnh sản phẩm ${index + 1}`}
                                            compact
                                        />
                                        {index === props.primaryIndex && (
                                            <span
                                                className="remake-product-gallery__selected"
                                                aria-hidden="true"
                                            >
                                                <Check className="size-3" />
                                            </span>
                                        )}
                                    </button>
                                    <button
                                        type="button"
                                        disabled={busy}
                                        onClick={() => props.onRemoveImage(index)}
                                        className="flex min-h-11 w-full items-center justify-center gap-1 rounded-lg text-xs text-text-secondary hover:bg-surface-soft focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50"
                                        aria-label={`Xóa ảnh sản phẩm ${index + 1}`}
                                    >
                                        <X className="size-3" aria-hidden="true" />
                                        Xóa
                                    </button>
                                </div>
                            ))}
                        </div>
                    )}
                    <details className="mt-4 text-sm">
                        <summary className="flex min-h-11 cursor-pointer list-none items-center gap-2 rounded-lg text-text-secondary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
                            <Link2 className="size-4" aria-hidden="true" />
                            Dán link sản phẩm
                            <ChevronDown className="ml-auto size-4" aria-hidden="true" />
                        </summary>
                        <div className="mt-2 space-y-2">
                            <label htmlFor={`${id}-link`} className="text-xs text-text-secondary">
                                Link trang sản phẩm
                            </label>
                            <Input
                                id={`${id}-link`}
                                type="url"
                                value={props.link}
                                onChange={(event) => props.onLinkChange(event.target.value)}
                                placeholder="https://..."
                                disabled={busy}
                                className={fieldClass}
                            />
                            <Button
                                type="button"
                                variant="ghost"
                                className={cn(quietButton, "w-full")}
                                disabled={busy || !props.link.trim()}
                                onClick={props.onLinkSubmit}
                            >
                                {props.isLinkLoading ? (
                                    <Loader2
                                        className="animate-spin motion-reduce:animate-none"
                                        aria-hidden="true"
                                    />
                                ) : (
                                    <Link2 aria-hidden="true" />
                                )}
                                {props.isLinkLoading ? "Đang lấy ảnh…" : "Lấy ảnh từ link"}
                            </Button>
                        </div>
                    </details>
                </section>
            </div>

            <div className="rounded-3xl bg-surface p-5 sm:p-6">
                <div className="grid gap-5 sm:grid-cols-2">
                    <fieldset disabled={busy} className="space-y-2">
                        <legend className="mb-2 text-sm font-medium text-text-primary">
                            Thời lượng video đầu ra
                        </legend>
                        <div className="flex gap-2">
                            {([8, 16] as const).map((duration) => (
                                <Button
                                    key={duration}
                                    type="button"
                                    variant="ghost"
                                    className={cn(
                                        quietButton,
                                        "flex-1",
                                        props.duration === duration &&
                                            "bg-primary-soft text-primary hover:bg-primary-soft",
                                    )}
                                    aria-pressed={props.duration === duration}
                                    onClick={() => props.onDuration(duration)}
                                >
                                    {duration} giây
                                </Button>
                            ))}
                        </div>
                        <p className="text-xs text-text-secondary">
                            Video dọc 9:16 · Phân bổ lại thời lượng cho đủ các cảnh
                        </p>
                    </fieldset>
                    <div className="space-y-2">
                        <label
                            htmlFor={`${id}-language`}
                            className="text-sm font-medium text-text-primary"
                        >
                            Ngôn ngữ
                        </label>
                        <Input
                            id={`${id}-language`}
                            value={props.language}
                            onChange={(event) => props.onLanguage(event.target.value)}
                            placeholder="Ví dụ: Tiếng Việt"
                            disabled={busy}
                            className={cn(fieldClass, "h-11")}
                        />
                        <p className="text-xs text-text-secondary">
                            Để trống để dùng ngôn ngữ từ video mẫu.
                        </p>
                    </div>
                </div>
                <details className="mt-5">
                    <summary className="flex min-h-11 cursor-pointer list-none items-center gap-2 rounded-lg text-sm font-medium text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
                        Thêm yêu cầu của bạn{" "}
                        <span className="text-xs font-normal text-text-secondary">
                            Không bắt buộc
                        </span>
                        <ChevronDown className="ml-auto size-4" aria-hidden="true" />
                    </summary>
                    <div className="mt-3 grid gap-4 sm:grid-cols-2">
                        <div className="space-y-2">
                            <label
                                htmlFor={`${id}-description`}
                                className="text-sm text-text-primary"
                            >
                                Thông tin sản phẩm
                            </label>
                            <Textarea
                                id={`${id}-description`}
                                value={props.description}
                                onChange={(event) => props.onDescription(event.target.value)}
                                placeholder="Ví dụ: Bình hồng, nắp trắng, có tay cầm."
                                disabled={busy}
                                className={cn(fieldClass, "min-h-28")}
                            />
                        </div>
                        <div className="space-y-2">
                            <label htmlFor={`${id}-brief`} className="text-sm text-text-primary">
                                Bạn muốn video thể hiện điều gì?
                            </label>
                            <Textarea
                                id={`${id}-brief`}
                                value={props.brief}
                                onChange={(event) => props.onBrief(event.target.value)}
                                placeholder="Ví dụ: Cho thấy cách mở nắp ngay đầu video."
                                disabled={busy}
                                className={cn(fieldClass, "min-h-28")}
                            />
                        </div>
                    </div>
                </details>
            </div>
            {props.onSample && (
                <div className="text-center">
                    <Button
                        type="button"
                        variant="ghost"
                        className="min-h-11 text-text-secondary"
                        disabled={busy}
                        onClick={props.onSample}
                    >
                        Thử với tư liệu minh họa
                    </Button>
                </div>
            )}
        </div>
    );
}
