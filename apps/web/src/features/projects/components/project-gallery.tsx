import { useState } from "react";
import { ChevronLeft, ChevronRight, Download, Film, Play, RefreshCw } from "lucide-react";

import type { SmartRemakeProjectVideo } from "@/shared/api/smart-remake-library";
import { RemakePlayer } from "@/features/smart-remake/components/remake-player";
import { Button } from "@/shared/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/shared/ui/dialog";
import { EmptyState, LoadingState } from "@/shared/ui/empty-state";
import { SurfaceCard } from "@/shared/ui/surface-card";
import { generationStageLabels } from "@/features/smart-remake/lib/remake-generation-progress";

function projectStage(item: SmartRemakeProjectVideo) {
    const activity = item.activity;
    if (activity?.needsReconciliation) return "Cần kiểm tra trạng thái";
    if (activity?.status === "failed") return "Cần tiếp tục xử lý";
    if (activity?.status === "running") {
        const stages: Record<string, string> = {
            ...generationStageLabels,
            validating_source: "Đang chuẩn bị video mẫu",
            analyzing_source: "Đang phân tích video mẫu",
            resolving_scenes: "Đang phân tích từng cảnh",
            identifying_product: "Đang nhận diện sản phẩm",
            building_storyboard: "Đang soạn kịch bản",
        };
        return stages[activity.stage ?? ""] ?? "Đang xử lý";
    }
    if (item.finalVideoUrl) return "Video hoàn chỉnh";
    if (item.videos.length) return "Có clip để xem";
    return item.phase === "compiled" || activity?.kind === "compile"
        ? "Kịch bản đã sẵn sàng"
        : "Chưa tạo video";
}

export type ProjectGalleryProps = {
    items: SmartRemakeProjectVideo[];
    total: number;
    limit: number;
    offset: number;
    loading: boolean;
    refreshing: boolean;
    error: boolean;
    onRefresh(): void;
    onPageChange(offset: number): void;
};

export function ProjectGallery({
    items,
    total,
    limit,
    offset,
    loading,
    refreshing,
    error,
    onRefresh,
    onPageChange,
}: ProjectGalleryProps) {
    const [selectedId, setSelectedId] = useState<string | null>(null);
    const [selectedVideoId, setSelectedVideoId] = useState<string | null>(null);
    const selected = error ? undefined : items.find((item) => item.id === selectedId);
    const selectedVideo =
        selected?.videos.find((video) => video.id === selectedVideoId) ?? selected?.videos[0];

    if (loading) return <LoadingState label="Đang tải video đã lưu" />;
    if (error)
        return (
            <SurfaceCard role="alert">
                <EmptyState
                    icon={Film}
                    title="Chưa tải được video"
                    description="Bạn thử tải lại danh sách video đã lưu nhé."
                    action={<Button onClick={onRefresh}>Thử lại</Button>}
                />
            </SurfaceCard>
        );

    return (
        <div className="flex flex-col gap-5">
            <div className="flex items-center justify-between gap-3">
                <p className="text-sm text-text-secondary">{total} project đã lưu</p>
                <Button variant="outline" onClick={onRefresh} disabled={refreshing}>
                    <RefreshCw className={refreshing ? "animate-spin" : undefined} aria-hidden />
                    Làm mới
                </Button>
            </div>

            {items.length === 0 ? (
                <SurfaceCard>
                    <EmptyState
                        icon={Film}
                        title="Chưa có dự án"
                        description="Dự án Smart Remake sẽ xuất hiện khi bạn bắt đầu tạo kịch bản hoặc video."
                    />
                </SurfaceCard>
            ) : (
                <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-3">
                    {items.map((item) => {
                        const final = item.videos.find((video) => video.kind === "final");
                        const clipCount = item.videos.filter(
                            (video) => video.kind === "clip",
                        ).length;
                        return (
                            <SurfaceCard key={item.id} padding="none" className="overflow-hidden">
                                <article aria-labelledby={`project-video-${item.id}`}>
                                    <button
                                        type="button"
                                        disabled={item.videos.length === 0}
                                        onClick={() => {
                                            setSelectedVideoId(null);
                                            setSelectedId(item.id);
                                        }}
                                        aria-label={
                                            item.videos.length
                                                ? `Xem video ${item.projectName}`
                                                : `Ảnh sản phẩm ${item.projectName}`
                                        }
                                        className="group relative flex aspect-video w-full items-center justify-center overflow-hidden bg-surface-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring"
                                    >
                                        {item.productImageUrl ? (
                                            <img
                                                src={item.productImageUrl}
                                                alt=""
                                                loading="lazy"
                                                className="h-full w-full object-contain"
                                            />
                                        ) : (
                                            <Film
                                                className="h-12 w-12 text-text-tertiary"
                                                aria-hidden
                                            />
                                        )}
                                        {item.videos.length > 0 && (
                                            <span className="absolute grid h-12 w-12 place-items-center rounded-full bg-surface/95 text-primary shadow-sm transition-transform group-hover:scale-105 motion-reduce:transition-none">
                                                <Play
                                                    className="h-5 w-5 fill-current"
                                                    aria-hidden
                                                />
                                            </span>
                                        )}
                                        <span className="absolute bottom-3 right-3 rounded-md bg-surface/95 px-2 py-1 text-xs font-medium text-text-primary">
                                            {final
                                                ? `${final.durationSeconds} giây`
                                                : item.videos.length
                                                  ? `${clipCount} clip`
                                                  : `${item.targetDuration} giây đầu ra`}
                                        </span>
                                    </button>
                                    <div className="flex flex-col gap-3 p-4">
                                        <div className="min-w-0">
                                            <h2
                                                id={`project-video-${item.id}`}
                                                className="truncate font-semibold text-text-primary"
                                                title={item.projectName}
                                            >
                                                {item.projectName}
                                            </h2>
                                            <time
                                                dateTime={item.createdAt}
                                                className="mt-1 block text-xs text-text-secondary"
                                            >
                                                {new Date(item.createdAt).toLocaleString("vi-VN", {
                                                    dateStyle: "medium",
                                                    timeStyle: "short",
                                                    timeZone: "Asia/Ho_Chi_Minh",
                                                })}
                                            </time>
                                        </div>
                                        {item.activity && (
                                            <p
                                                className="text-sm font-medium text-primary"
                                                role="status"
                                            >
                                                {projectStage(item)}
                                            </p>
                                        )}
                                        <p className="text-xs text-text-secondary">
                                            {item.activity?.plannedVideoCount != null
                                                ? item.activity.submittedVideoCount == null
                                                    ? "Chưa xác nhận số lượt KIE đã gửi"
                                                    : `${item.activity.completedImageCount ?? 0} ảnh đã tạo · ${item.activity.submittedVideoCount}/${item.activity.plannedVideoCount} lượt KIE đã gửi`
                                                : final
                                                  ? `Video hoàn chỉnh${clipCount ? ` · ${clipCount} clip đã tạo` : ""}`
                                                  : item.videos.length
                                                    ? `${clipCount} clip đã tạo`
                                                    : "Mở dự án để xem tư liệu và tiến độ."}
                                        </p>
                                        <Button asChild className="w-full">
                                            <a
                                                href={`/smart-remake?projectId=${encodeURIComponent(item.id)}`}
                                                aria-label={`Mở dự án ${item.projectName}`}
                                            >
                                                Mở dự án
                                            </a>
                                        </Button>
                                        {item.downloadUrl ? (
                                            <Button asChild variant="outline" className="w-full">
                                                <a
                                                    href={item.downloadUrl}
                                                    download={`${item.projectName}.mp4`}
                                                    target="_blank"
                                                    rel="noreferrer"
                                                    aria-label={`Tải video ${item.projectName}`}
                                                >
                                                    <Download aria-hidden /> Tải video
                                                </a>
                                            </Button>
                                        ) : (
                                            <p className="text-xs text-text-tertiary">
                                                Bản xem trước
                                            </p>
                                        )}
                                    </div>
                                </article>
                            </SurfaceCard>
                        );
                    })}
                </div>
            )}

            {total > limit && (
                <nav
                    aria-label="Phân trang video"
                    className="flex items-center justify-center gap-3"
                >
                    <Button
                        variant="outline"
                        size="icon"
                        aria-label="Trang trước"
                        disabled={offset === 0 || refreshing}
                        onClick={() => onPageChange(Math.max(0, offset - limit))}
                    >
                        <ChevronLeft aria-hidden />
                    </Button>
                    <p className="text-sm text-text-secondary">
                        Trang {Math.floor(offset / limit) + 1} / {Math.ceil(total / limit)}
                    </p>
                    <Button
                        variant="outline"
                        size="icon"
                        aria-label="Trang sau"
                        disabled={offset + limit >= total || refreshing}
                        onClick={() => onPageChange(offset + limit)}
                    >
                        <ChevronRight aria-hidden />
                    </Button>
                </nav>
            )}

            <Dialog
                open={Boolean(selectedVideo)}
                onOpenChange={(open) => !open && setSelectedId(null)}
            >
                {selected && selectedVideo && (
                    <DialogContent className="max-w-3xl">
                        <DialogTitle className="pr-6">{selected.projectName}</DialogTitle>
                        <DialogDescription>
                            {selectedVideo.label} · {selectedVideo.durationSeconds} giây
                        </DialogDescription>
                        {!selected.videos.some((video) => video.kind === "final") && (
                            <p className="text-sm text-text-secondary">
                                Chưa ghép thành video hoàn chỉnh
                            </p>
                        )}
                        {selected.videos.length > 1 && (
                            <div
                                role="group"
                                aria-label="Video đã lưu"
                                className="flex flex-wrap gap-2"
                            >
                                {selected.videos.map((video) => (
                                    <Button
                                        key={video.id}
                                        variant={
                                            video.id === selectedVideo.id ? "default" : "outline"
                                        }
                                        aria-pressed={video.id === selectedVideo.id}
                                        onClick={() => setSelectedVideoId(video.id)}
                                    >
                                        {video.label} · {video.durationSeconds} giây
                                    </Button>
                                ))}
                            </div>
                        )}
                        <RemakePlayer
                            url={selectedVideo.url}
                            poster={selected.productImageUrl}
                            scope={null}
                            versionLabel={selectedVideo.label}
                        />
                    </DialogContent>
                )}
            </Dialog>
        </div>
    );
}
