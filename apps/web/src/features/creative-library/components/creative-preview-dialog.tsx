import { useNavigate } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";
import { ArrowRight, Film, Loader2, X } from "lucide-react";

import {
    getCreativeMediaKind,
    isIllustrativeCreative,
} from "@/features/creative-library/lib/library-catalog";
import { formatDuration } from "@/features/creative-library/lib/creative-visuals";
import type { CreativeReference } from "@/features/creative-library/types/creative";
import { loadRemakeLibraryVideo } from "@/features/smart-remake/lib/remake-library";
import {
    clearSmartRemakeHandoff,
    setSmartRemakeHandoff,
    type SmartRemakeHandoff,
} from "@/features/smart-remake/lib/smart-remake-handoff";
import { Button } from "@/shared/ui/button";
import {
    Dialog,
    DialogClose,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
} from "@/shared/ui/dialog";

export interface CreativePreviewDialogProps {
    creative: CreativeReference | null;
    onOpenChange(open: boolean): void;
}
export function CreativePreviewDialog(props: CreativePreviewDialogProps) {
    return <PreviewSession key={props.creative?.id ?? "closed"} {...props} />;
}
function PreviewSession({ creative, onOpenChange }: CreativePreviewDialogProps) {
    const navigate = useNavigate();
    const request = useRef<AbortController | null>(null);
    const opening = useRef(false);
    const returnFocus = useRef<HTMLElement | null>(
        typeof document !== "undefined" && document.activeElement instanceof HTMLElement
            ? document.activeElement
            : null,
    );
    const [phase, setPhase] = useState<"idle" | "download" | "opening">("idle");
    const loading = phase !== "idle";
    const [error, setError] = useState<string | null>(null);
    const [previewFailed, setPreviewFailed] = useState(false);
    const [metadata, setMetadata] = useState({ width: 0, height: 0, duration: 0 });
    const hasVideo = Boolean(creative && getCreativeMediaKind(creative) === "video");
    const savedRatio = creative?.mediaAspectRatio?.split(":").map(Number);
    const ratio =
        metadata.width && metadata.height
            ? metadata.width / metadata.height
            : savedRatio
              ? savedRatio[0] / savedRatio[1]
              : 9 / 16;
    useEffect(
        () => () => {
            request.current?.abort();
            request.current = null;
        },
        [],
    );
    function changeOpen(open: boolean) {
        if (!open && opening.current) return;
        if (!open) {
            request.current?.abort();
            request.current = null;
            setPhase("idle");
            setError(null);
        }
        onOpenChange(open);
    }
    async function confirmVideo() {
        if (!creative || !hasVideo || request.current) return;
        const controller = new AbortController();
        request.current = controller;
        setPhase("download");
        setError(null);
        try {
            const file = await loadRemakeLibraryVideo(creative, controller.signal);
            if (controller.signal.aborted || request.current !== controller) return;
            opening.current = true;
            setPhase("opening");
            const handoff: SmartRemakeHandoff = { referenceVideo: file, productImages: [] };
            setSmartRemakeHandoff(handoff);
            try {
                await navigate({ to: "/smart-remake" });
            } catch (cause) {
                clearSmartRemakeHandoff(handoff);
                throw cause;
            } finally {
                opening.current = false;
            }
            if (!controller.signal.aborted && request.current === controller) changeOpen(false);
        } catch (cause) {
            if (!controller.signal.aborted && request.current === controller)
                setError(
                    cause instanceof Error && !(cause instanceof TypeError)
                        ? cause.message
                        : "Chưa mở được video này. Hãy thử lại hoặc chọn video khác.",
                );
        } finally {
            if (request.current === controller) {
                request.current = null;
                setPhase("idle");
            }
        }
    }
    return (
        <Dialog open={Boolean(creative)} onOpenChange={changeOpen}>
            <DialogContent
                className="flex max-h-[calc(100dvh-1.5rem)] max-w-4xl flex-col gap-0 overflow-hidden rounded-3xl border-0 p-0 [&>button:last-child]:hidden"
                onEscapeKeyDown={(event) => {
                    if (opening.current) event.preventDefault();
                }}
                onInteractOutside={(event) => {
                    if (opening.current) event.preventDefault();
                }}
                onCloseAutoFocus={(event) => {
                    if (!returnFocus.current?.isConnected) return;
                    event.preventDefault();
                    returnFocus.current.focus({ preventScroll: true });
                }}
            >
                <Button
                    type="button"
                    variant="ghost"
                    aria-label="Đóng xem video"
                    className="absolute right-4 top-4 size-11 shrink-0 rounded-xl px-0"
                    disabled={phase === "opening"}
                    onClick={() => changeOpen(false)}
                >
                    <X className="size-4" aria-hidden="true" />
                </Button>
                <DialogHeader className="shrink-0 px-5 pb-4 pt-6 pr-20 text-left sm:px-6 sm:pr-20">
                    <DialogTitle>Xem video mẫu</DialogTitle>
                    <DialogDescription>
                        {creative?.title ?? "Chọn video trong kho để xem."}
                    </DialogDescription>
                </DialogHeader>
                <div className="min-h-0 flex-1 overflow-y-auto px-5 pb-5 sm:px-6">
                    <div className="grid items-start gap-5 md:grid-cols-[minmax(0,1fr)_240px]">
                        <div className="min-w-0 space-y-3">
                            <div className="flex min-h-44 items-center justify-center rounded-2xl bg-surface-soft p-3">
                                {hasVideo && creative?.mediaUrl ? (
                                    <video
                                        src={creative.mediaUrl}
                                        poster={creative.posterUrl ?? creative.thumbnailUrl}
                                        controls
                                        playsInline
                                        preload="metadata"
                                        aria-label={`Xem video ${creative.title}`}
                                        className="block h-auto max-h-[min(56svh,560px)] max-w-full rounded-xl bg-black object-contain"
                                        style={{
                                            aspectRatio: ratio,
                                            width: `min(100%, calc(min(56svh, 560px) * ${ratio}))`,
                                        }}
                                        onLoadedMetadata={(event) => {
                                            const media = event.currentTarget;
                                            if (media.videoWidth && media.videoHeight)
                                                setMetadata({
                                                    width: media.videoWidth,
                                                    height: media.videoHeight,
                                                    duration: Number.isFinite(media.duration)
                                                        ? media.duration
                                                        : 0,
                                                });
                                        }}
                                        onError={() => setPreviewFailed(true)}
                                    />
                                ) : (
                                    <div className="py-8 text-center text-sm text-text-secondary">
                                        <Film
                                            className="mx-auto mb-3 size-8 text-text-tertiary"
                                            aria-hidden="true"
                                        />
                                        Chưa có file video để xem.
                                    </div>
                                )}
                            </div>
                            {hasVideo && (
                                <p className="text-xs leading-relaxed text-text-secondary">
                                    Bấm Phát trên video để xem và nghe âm thanh. Video không tự
                                    phát.
                                </p>
                            )}
                            {previewFailed && (
                                <p role="status" className="text-sm text-text-secondary">
                                    Chưa phát được bản xem trước. Bạn có thể thử dùng file hoặc chọn
                                    video khác.
                                </p>
                            )}
                        </div>
                        <aside className="space-y-4 rounded-2xl bg-surface-soft p-4">
                            <div className="flex flex-wrap gap-2 text-xs text-text-secondary">
                                <span className="rounded-full bg-surface px-2 py-1">
                                    {creative?.platform}
                                </span>
                                {creative && isIllustrativeCreative(creative) && (
                                    <span className="rounded-full bg-surface px-2 py-1">
                                        Minh họa
                                    </span>
                                )}
                            </div>
                            <div>
                                <h3 className="text-xs font-medium text-text-secondary">
                                    Câu mở đầu
                                </h3>
                                <p className="mt-1 text-sm leading-relaxed text-text-primary">
                                    {creative?.hookExcerpt || "Chưa có mô tả câu mở đầu."}
                                </p>
                            </div>
                            <dl className="space-y-3 text-xs text-text-secondary">
                                <div>
                                    <dt className="font-medium">Nguồn lưu</dt>
                                    <dd className="mt-1">Lưu trên trình duyệt này</dd>
                                </div>
                                <div>
                                    <dt className="font-medium">Thời lượng</dt>
                                    <dd className="mt-1">
                                        {metadata.duration || creative?.durationSec
                                            ? formatDuration(
                                                  metadata.duration || creative!.durationSec,
                                              )
                                            : "Chưa có thông tin"}
                                        {metadata.width > 0 &&
                                            ` · ${metadata.width} × ${metadata.height}`}
                                    </dd>
                                </div>
                            </dl>
                            <p className="text-xs leading-relaxed text-text-secondary">
                                Smart Remake dùng video này làm mẫu. Bạn sẽ thêm sản phẩm và kiểm
                                tra kịch bản trước khi tạo video mới.
                            </p>
                        </aside>
                    </div>
                </div>
                <div className="shrink-0 space-y-3 bg-surface px-5 pb-[max(1.25rem,env(safe-area-inset-bottom))] pt-4 sm:px-6">
                    {error && (
                        <p role="alert" className="text-sm text-destructive">
                            {error}
                        </p>
                    )}
                    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                        <p role="status" className="text-xs leading-relaxed text-text-secondary">
                            {phase === "opening"
                                ? "Đang mở Smart Remake…"
                                : phase === "download"
                                  ? "Đang chuẩn bị file. Đóng cửa sổ để hủy."
                                  : "Chỉ chuyển video mẫu sang Smart Remake. Chưa chạy phân tích hoặc tạo video."}
                        </p>
                        <div className="flex shrink-0 gap-2">
                            <DialogClose asChild>
                                <Button
                                    type="button"
                                    variant="ghost"
                                    className="min-h-11"
                                    disabled={phase === "opening"}
                                >
                                    Đóng
                                </Button>
                            </DialogClose>
                            <Button
                                type="button"
                                aria-label="Dùng video làm mẫu trong Smart Remake"
                                className="min-h-11 flex-1 bg-[#e00b41] text-sm text-white hover:bg-[#c90939] sm:flex-none"
                                disabled={!hasVideo || loading}
                                onClick={() => void confirmVideo()}
                            >
                                {loading ? (
                                    <Loader2
                                        className="size-4 motion-safe:animate-spin"
                                        aria-hidden="true"
                                    />
                                ) : (
                                    <ArrowRight className="size-4" aria-hidden="true" />
                                )}
                                {phase === "opening" ? "Đang mở…" : "Dùng video này"}
                            </Button>
                        </div>
                    </div>
                </div>
            </DialogContent>
        </Dialog>
    );
}
