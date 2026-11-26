import { Check, Library, Loader2, Search, Video, X } from "lucide-react";
import { useEffect, useId, useRef, useState } from "react";

import { useAppStore } from "@/app/store/app-store";
import {
    getRemakeLibraryVideos,
    isDemoLibraryVideo,
    loadRemakeLibraryVideo,
} from "@/features/smart-remake/lib/remake-library";
import { cn } from "@/shared/lib/utils";
import { Button } from "@/shared/ui/button";
import {
    Dialog,
    DialogClose,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
} from "@/shared/ui/dialog";
import { Input } from "@/shared/ui/input";

export interface RemakeVideoLibraryProps {
    disabled: boolean;
    onVideo: (file: File) => void;
}

export function RemakeVideoLibrary({ disabled, onVideo }: RemakeVideoLibraryProps) {
    const creatives = useAppStore((state) => state.creatives);
    const [open, setOpen] = useState(false);
    const [query, setQuery] = useState("");
    const [showAll, setShowAll] = useState(false);
    const [selectedId, setSelectedId] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [metadata, setMetadata] = useState({ id: "", width: 0, height: 0, duration: 0 });
    const [mediaRatios, setMediaRatios] = useState<Record<string, number>>({});
    const [previewErrorId, setPreviewErrorId] = useState<string | null>(null);
    const download = useRef<AbortController | null>(null);
    const preview = useRef<HTMLElement | null>(null);
    const searchId = useId();
    const matchingVideos = getRemakeLibraryVideos(creatives, query);
    const sourceVideos = matchingVideos.filter((video) => Boolean(video.mediaUrl?.trim()));
    const missingFileCount = matchingVideos.length - sourceVideos.length;
    const videos = showAll ? matchingVideos : sourceVideos;
    const selected = getRemakeLibraryVideos(creatives).find((video) => video.id === selectedId);

    useEffect(
        () => () => {
            download.current?.abort();
            download.current = null;
        },
        [],
    );

    const changeOpen = (nextOpen: boolean) => {
        if (nextOpen && disabled) return;
        if (!nextOpen) {
            download.current?.abort();
            download.current = null;
            setLoading(false);
            setError(null);
        }
        setOpen(nextOpen);
    };

    const applyVideo = async () => {
        if (!selected?.mediaUrl?.trim() || disabled || download.current) return;
        const controller = new AbortController();
        download.current = controller;
        setLoading(true);
        setError(null);
        try {
            const file = await loadRemakeLibraryVideo(selected, controller.signal);
            if (controller.signal.aborted || download.current !== controller) return;
            onVideo(file);
            changeOpen(false);
        } catch (cause) {
            if (!controller.signal.aborted && download.current === controller) {
                setError(
                    cause instanceof Error && !(cause instanceof TypeError)
                        ? cause.message
                        : "Chưa tải được video này. Bạn hãy thử lại hoặc tải file lên.",
                );
            }
        } finally {
            if (download.current === controller) {
                download.current = null;
                setLoading(false);
            }
        }
    };

    const duration =
        selected && metadata.id === selected.id ? metadata.duration : selected?.durationSec;
    const ratioFor = (video: (typeof videos)[number]) => {
        const ratio = video.mediaAspectRatio?.split(":").map(Number);
        return mediaRatios[video.id] ?? (ratio ? ratio[0] / ratio[1] : 9 / 16);
    };
    const selectedRatio = selected ? ratioFor(selected) : 9 / 16;

    return (
        <Dialog open={open} onOpenChange={changeOpen}>
            <DialogTrigger asChild>
                <Button
                    type="button"
                    variant="ghost"
                    className="min-h-11 w-full border-0 bg-surface-soft text-text-primary hover:bg-surface-muted motion-reduce:transform-none"
                    disabled={disabled}
                >
                    <Library aria-hidden="true" />
                    Chọn từ kho video
                </Button>
            </DialogTrigger>
            <DialogContent className="flex max-h-[calc(100dvh-1.5rem)] max-w-5xl flex-col gap-0 overflow-hidden rounded-3xl border-0 p-0 shadow-[0_24px_80px_rgb(0_0_0/0.18)] motion-reduce:animate-none [&>button:last-child]:flex [&>button:last-child]:size-11 [&>button:last-child]:items-center [&>button:last-child]:justify-center [&>button:last-child]:rounded-xl">
                <DialogHeader className="shrink-0 px-5 pb-4 pt-6 pr-20 text-left sm:px-6 sm:pr-20">
                    <DialogTitle>Chọn video mẫu từ kho</DialogTitle>
                    <DialogDescription>
                        Chọn video để xem trước. Chỉ dùng làm mẫu khi bạn bấm “Dùng video này”.
                    </DialogDescription>
                    <p className="text-xs text-text-secondary">Kho lưu trên trình duyệt này</p>
                </DialogHeader>
                <div className="min-h-0 flex-1 overflow-y-auto px-5 pb-5 sm:px-6">
                    <div className="mb-5 space-y-2">
                        <label htmlFor={searchId} className="text-sm font-medium text-text-primary">
                            Tìm trong kho video
                        </label>
                        <div className="relative">
                            <Search
                                className="pointer-events-none absolute left-3 top-3.5 size-4 text-text-tertiary"
                                aria-hidden="true"
                            />
                            <Input
                                id={searchId}
                                value={query}
                                onChange={(event) => setQuery(event.target.value)}
                                placeholder="Tên video, câu mở đầu hoặc từ khóa"
                                className="h-11 border-0 bg-surface-soft pl-10 pr-12 shadow-none"
                            />
                            {query && (
                                <button
                                    type="button"
                                    aria-label="Xóa tìm kiếm"
                                    onClick={() => setQuery("")}
                                    className="absolute right-0 top-0 flex size-11 items-center justify-center rounded-xl text-text-secondary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                                >
                                    <X className="size-4" aria-hidden="true" />
                                </button>
                            )}
                        </div>
                        <div
                            role="group"
                            aria-label="Lọc theo nguồn video"
                            className="flex flex-wrap gap-2 pt-1"
                        >
                            <Button
                                type="button"
                                variant="ghost"
                                aria-pressed={!showAll}
                                className={cn(
                                    "min-h-11 rounded-xl bg-surface-soft text-xs",
                                    !showAll &&
                                        "bg-primary-soft text-primary hover:bg-primary-soft",
                                )}
                                onClick={() => setShowAll(false)}
                            >
                                Có nguồn video
                            </Button>
                            <Button
                                type="button"
                                variant="ghost"
                                aria-pressed={showAll}
                                className={cn(
                                    "min-h-11 rounded-xl bg-surface-soft text-xs",
                                    showAll && "bg-primary-soft text-primary hover:bg-primary-soft",
                                )}
                                onClick={() => setShowAll(true)}
                            >
                                Tất cả
                            </Button>
                        </div>
                    </div>
                    <div className="grid items-start gap-5 md:grid-cols-[minmax(0,1fr)_minmax(230px,320px)]">
                        <div className="order-2 min-w-0 md:order-1">
                            <p role="status" className="mb-3 text-xs text-text-secondary">
                                {sourceVideos.length} có nguồn video · {missingFileCount} chưa có
                                file
                            </p>
                            {videos.length ? (
                                <div
                                    className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-2 lg:grid-cols-3"
                                    aria-label="Video trong kho"
                                >
                                    {videos.map((video) => (
                                        <button
                                            key={video.id}
                                            type="button"
                                            onClick={() => {
                                                setSelectedId(video.id);
                                                setError(null);
                                            }}
                                            disabled={!video.mediaUrl?.trim() || loading}
                                            aria-pressed={selectedId === video.id}
                                            title={video.title}
                                            className={cn(
                                                "flex h-full min-w-0 flex-col items-stretch rounded-2xl bg-surface-soft p-3 text-left transition-[background-color,box-shadow] duration-150 hover:bg-surface-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-60 motion-reduce:transition-none",
                                                selectedId === video.id &&
                                                    "bg-primary-soft ring-2 ring-primary/50",
                                            )}
                                        >
                                            <div className="mb-3 flex h-36 shrink-0 items-center justify-center">
                                                {video.mediaUrl?.trim() ? (
                                                    <video
                                                        src={video.mediaUrl}
                                                        poster={
                                                            video.posterUrl || video.thumbnailUrl
                                                        }
                                                        preload="metadata"
                                                        muted
                                                        playsInline
                                                        aria-hidden="true"
                                                        className="pointer-events-none block h-auto max-h-full w-auto max-w-full rounded-lg object-contain"
                                                        style={{
                                                            aspectRatio: ratioFor(video),
                                                            width: `min(100%, ${144 * ratioFor(video)}px)`,
                                                        }}
                                                        onLoadedMetadata={(event) => {
                                                            const media = event.currentTarget;
                                                            if (
                                                                media.videoWidth &&
                                                                media.videoHeight
                                                            )
                                                                setMediaRatios((current) => ({
                                                                    ...current,
                                                                    [video.id]:
                                                                        media.videoWidth /
                                                                        media.videoHeight,
                                                                }));
                                                        }}
                                                    />
                                                ) : (
                                                    <Video
                                                        className="size-8 text-text-tertiary"
                                                        aria-hidden="true"
                                                    />
                                                )}
                                            </div>
                                            <span className="line-clamp-2 h-10 shrink-0 text-sm font-medium leading-5 text-text-primary [overflow-wrap:anywhere]">
                                                {video.title}
                                            </span>
                                            <span className="mt-1 block h-4 shrink-0 truncate text-xs text-text-secondary">
                                                {video.platform}
                                                {video.durationSec > 0
                                                    ? ` · ${video.durationSec} giây`
                                                    : ""}
                                            </span>
                                            <div className="mt-auto flex h-16 min-w-0 shrink-0 flex-col items-start justify-end gap-1 overflow-hidden">
                                                {isDemoLibraryVideo(video) && (
                                                    <span className="block max-w-full truncate rounded-full bg-surface px-2 py-0.5 text-[11px] text-text-secondary">
                                                        Video minh họa
                                                    </span>
                                                )}
                                                {!video.mediaUrl?.trim() && (
                                                    <span className="block max-w-full truncate text-xs text-text-secondary">
                                                        Chưa có file video
                                                    </span>
                                                )}
                                                {selectedId === video.id && (
                                                    <span className="inline-flex max-w-full items-center gap-1 whitespace-nowrap text-xs font-medium text-primary">
                                                        <Check
                                                            className="size-3.5"
                                                            aria-hidden="true"
                                                        />
                                                        Đang chọn
                                                    </span>
                                                )}
                                            </div>
                                        </button>
                                    ))}
                                </div>
                            ) : (
                                <div className="rounded-2xl bg-surface-soft p-6 text-center">
                                    <Library
                                        className="mx-auto mb-3 size-8 text-text-tertiary"
                                        aria-hidden="true"
                                    />
                                    <p className="text-sm font-medium text-text-primary">
                                        {query
                                            ? missingFileCount > 0
                                                ? "Kết quả này chưa có file video"
                                                : "Chưa tìm thấy video phù hợp"
                                            : missingFileCount > 0
                                              ? "Các mục đã lưu chưa có file video"
                                              : "Kho chưa có video để làm mẫu"}
                                    </p>
                                    <p className="mt-2 text-sm text-text-secondary">
                                        {query
                                            ? missingFileCount > 0
                                                ? "Chọn Tất cả để xem các mục đã lưu, hoặc tìm tên khác."
                                                : "Thử tên khác hoặc xóa tìm kiếm để xem toàn bộ kho."
                                            : missingFileCount > 0
                                              ? "Chọn Tất cả để xem thông tin đã lưu, hoặc tải video từ máy."
                                              : "Bạn có thể quay lại và tải video từ máy lên."}
                                    </p>
                                    {query && (
                                        <Button
                                            type="button"
                                            variant="ghost"
                                            className="mt-3 min-h-11"
                                            onClick={() => setQuery("")}
                                        >
                                            Xóa tìm kiếm
                                        </Button>
                                    )}
                                    <DialogClose asChild>
                                        <Button
                                            type="button"
                                            variant="ghost"
                                            className="mt-3 min-h-11"
                                        >
                                            Quay lại tải video
                                        </Button>
                                    </DialogClose>
                                </div>
                            )}
                        </div>
                        <aside
                            ref={preview}
                            tabIndex={-1}
                            className="order-1 min-w-0 scroll-mt-3 space-y-3 rounded-2xl bg-surface-soft p-4 focus:outline-none focus-visible:ring-2 focus-visible:ring-ring md:order-2 md:sticky md:top-0"
                            aria-label="Video đang chọn"
                        >
                            {selected?.mediaUrl?.trim() ? (
                                <>
                                    <div className="flex min-h-40 items-center justify-center">
                                        <video
                                            key={selected.id}
                                            src={selected.mediaUrl}
                                            poster={selected.posterUrl || selected.thumbnailUrl}
                                            controls
                                            playsInline
                                            preload="metadata"
                                            aria-label={`Xem trước ${selected.title}`}
                                            className="block h-auto max-h-[min(40svh,340px)] w-auto max-w-full rounded-xl bg-black object-contain"
                                            style={{
                                                aspectRatio: selectedRatio,
                                                width: `min(100%, calc(min(40svh, 340px) * ${selectedRatio}))`,
                                            }}
                                            onLoadedMetadata={(event) => {
                                                const media = event.currentTarget;
                                                setPreviewErrorId((current) =>
                                                    current === selected.id ? null : current,
                                                );
                                                if (media.videoWidth && media.videoHeight)
                                                    setMediaRatios((current) => ({
                                                        ...current,
                                                        [selected.id]:
                                                            media.videoWidth / media.videoHeight,
                                                    }));
                                                setMetadata({
                                                    id: selected.id,
                                                    width: media.videoWidth,
                                                    height: media.videoHeight,
                                                    duration: Number.isFinite(media.duration)
                                                        ? media.duration
                                                        : 0,
                                                });
                                            }}
                                            onError={() => setPreviewErrorId(selected.id)}
                                        />
                                    </div>
                                    <h3 className="text-sm font-semibold text-text-primary [overflow-wrap:anywhere]">
                                        {selected.title}
                                    </h3>
                                    <p className="text-xs text-text-secondary">
                                        {selected.platform}
                                        {duration && duration > 0
                                            ? ` · ${Math.round(duration)} giây`
                                            : ""}
                                        {metadata.id === selected.id && metadata.width > 0
                                            ? ` · ${metadata.width} × ${metadata.height}`
                                            : ""}
                                    </p>
                                    {isDemoLibraryVideo(selected) && (
                                        <p className="text-xs text-text-secondary">
                                            Video minh họa trong kho.
                                        </p>
                                    )}
                                    {previewErrorId === selected.id ? (
                                        <p role="status" className="text-xs text-text-secondary">
                                            Chưa phát được bản xem trước. Bạn có thể thử tải video
                                            hoặc chọn video khác.
                                        </p>
                                    ) : (
                                        metadata.id !== selected.id && (
                                            <p
                                                role="status"
                                                className="flex items-center gap-2 text-xs text-text-secondary"
                                            >
                                                <Loader2
                                                    className="size-3.5 animate-spin motion-reduce:animate-none"
                                                    aria-hidden="true"
                                                />
                                                Đang đọc video…
                                            </p>
                                        )
                                    )}
                                </>
                            ) : (
                                <div className="py-8 text-center">
                                    <Video
                                        className="mx-auto mb-3 size-8 text-text-tertiary"
                                        aria-hidden="true"
                                    />
                                    <p className="text-sm text-text-secondary">
                                        Chọn một video để xem trước.
                                    </p>
                                </div>
                            )}
                        </aside>
                    </div>
                </div>
                <div className="shrink-0 space-y-3 bg-surface px-5 pb-[max(1.25rem,env(safe-area-inset-bottom))] pt-4 sm:px-6">
                    <p className="text-xs text-text-secondary">
                        MP4, WebM hoặc MOV · Tối đa 30 MB. File sẽ được kiểm tra khi bạn chọn dùng.
                    </p>
                    {error && (
                        <p
                            role="alert"
                            className="text-sm text-destructive [overflow-wrap:anywhere]"
                        >
                            {error}
                        </p>
                    )}
                    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                        <div className="min-w-0 flex-1 space-y-1">
                            {selected && (
                                <>
                                    <p className="line-clamp-2 text-xs font-medium text-text-primary [overflow-wrap:anywhere]">
                                        Đang chọn: {selected.title}
                                    </p>
                                    <Button
                                        type="button"
                                        variant="ghost"
                                        className="h-auto min-h-11 max-w-full whitespace-normal px-0 text-left text-xs text-primary hover:bg-transparent"
                                        onClick={() => {
                                            preview.current?.focus({ preventScroll: true });
                                            preview.current?.scrollIntoView({
                                                block: "start",
                                                behavior: "auto",
                                            });
                                        }}
                                    >
                                        Xem video đang chọn
                                    </Button>
                                </>
                            )}
                            <p className="text-xs text-text-secondary">
                                {loading
                                    ? "Đang tải file video. Đóng cửa sổ để hủy."
                                    : selected
                                      ? "Video này sẽ thay video mẫu hiện tại. Chưa chạy phân tích."
                                      : "Chọn video có file để tiếp tục."}
                            </p>
                        </div>
                        <div className="flex max-w-full shrink-0 flex-wrap gap-2">
                            <DialogClose asChild>
                                <Button
                                    type="button"
                                    variant="ghost"
                                    className="h-auto min-h-11 max-w-full whitespace-normal"
                                >
                                    Đóng
                                </Button>
                            </DialogClose>
                            <Button
                                type="button"
                                className="h-auto min-h-11 max-w-full flex-1 whitespace-normal bg-[#e00b41] text-white hover:bg-[#c90939] sm:flex-none"
                                disabled={disabled || loading || !selected?.mediaUrl?.trim()}
                                onClick={() => void applyVideo()}
                            >
                                {loading ? (
                                    <Loader2
                                        className="animate-spin motion-reduce:animate-none"
                                        aria-hidden="true"
                                    />
                                ) : (
                                    <Check aria-hidden="true" />
                                )}
                                {loading ? "Đang tải video…" : "Dùng video này"}
                            </Button>
                        </div>
                    </div>
                </div>
            </DialogContent>
        </Dialog>
    );
}
