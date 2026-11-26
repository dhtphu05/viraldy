import { useState } from "react";
import {
    Archive,
    ArrowRight,
    Check,
    Copy,
    Film,
    FolderInput,
    MoreHorizontal,
    Package,
    Play,
    Sparkles,
} from "lucide-react";

import {
    getCreativeMediaKind,
    isIllustrativeCreative,
} from "@/features/creative-library/lib/library-catalog";
import { formatDuration } from "@/features/creative-library/lib/creative-visuals";
import type { CreativeReference } from "@/features/creative-library/types/creative";
import { cn } from "@/shared/lib/utils";
import { Button } from "@/shared/ui/button";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from "@/shared/ui/dropdown-menu";
import { SurfaceCard } from "@/shared/ui/surface-card";
import { AnalysisStatusChip } from "./analysis-status-chip";

export type CreativeCardAction =
    | "open"
    | "preview"
    | "remake"
    | "analyze"
    | "adapt"
    | "add-to-campaign"
    | "move-board"
    | "duplicate"
    | "archive";

export function CreativeCard({
    creative,
    selected,
    selectable,
    compact,
    onToggleSelect,
    onAction,
}: {
    creative: CreativeReference;
    selected?: boolean;
    selectable?: boolean;
    compact?: boolean;
    onToggleSelect?: () => void;
    onAction: (a: CreativeCardAction) => void;
}) {
    const [metadata, setMetadata] = useState({ source: "", ratio: 0 });
    const mediaKind = getCreativeMediaKind(creative);
    const hasVideo = mediaKind === "video";
    const canAdapt = creative.analysisStatus === "analyzed";
    const processing = creative.analysisStatus === "processing";
    const savedRatio = creative.mediaAspectRatio?.split(":").map(Number);
    const ratio =
        metadata.source === creative.mediaUrl && metadata.ratio > 0
            ? metadata.ratio
            : savedRatio
              ? savedRatio[0] / savedRatio[1]
              : 9 / 16;
    const imageUrl =
        creative.posterUrl ??
        creative.thumbnailUrl ??
        (mediaKind === "image" ? creative.mediaUrl : undefined);
    const fileLabel = hasVideo
        ? "Có file video"
        : mediaKind === "image"
          ? "Ảnh tham khảo"
          : creative.mediaKind === "video" || creative.durationSec > 0
            ? "Chưa có file video"
            : "Liên kết tham khảo";

    return (
        <SurfaceCard
            padding="none"
            role="article"
            aria-label={creative.title}
            data-selected={selected}
            className={cn(
                "relative flex min-w-0 flex-col overflow-hidden border-0 bg-surface",
                compact && "sm:flex-row",
                selected && "ring-2 ring-primary/50",
            )}
        >
            <button
                type="button"
                onClick={() => onAction(hasVideo ? "preview" : "open")}
                aria-label={`${hasVideo ? "Xem video" : "Mở chi tiết"} ${creative.title}`}
                className={cn(
                    "relative flex h-64 w-full items-center justify-center overflow-hidden bg-surface-soft p-3 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring",
                    !hasVideo && !imageUrl && "h-32",
                    compact && "h-44 sm:h-auto sm:min-h-44 sm:w-40 sm:shrink-0",
                )}
            >
                {hasVideo ? (
                    <video
                        src={creative.mediaUrl}
                        poster={creative.posterUrl ?? creative.thumbnailUrl}
                        muted
                        playsInline
                        preload="metadata"
                        aria-hidden="true"
                        className="block h-auto max-h-60 max-w-full rounded-lg bg-black object-contain"
                        style={{ aspectRatio: ratio, width: `min(100%, ${240 * ratio}px)` }}
                        onLoadedMetadata={(event) => {
                            const media = event.currentTarget;
                            if (media.videoWidth && media.videoHeight)
                                setMetadata({
                                    source: creative.mediaUrl!,
                                    ratio: media.videoWidth / media.videoHeight,
                                });
                        }}
                    />
                ) : imageUrl ? (
                    <img
                        src={imageUrl}
                        alt=""
                        loading="lazy"
                        className="block h-auto max-h-60 max-w-full rounded-lg object-contain"
                    />
                ) : (
                    <span className="flex flex-col items-center gap-2 text-text-tertiary">
                        <Film className="size-8" aria-hidden="true" />
                        <span className="text-xs">Chưa có bản xem trước</span>
                    </span>
                )}
                <span className="pointer-events-none absolute left-3 top-3 rounded-lg bg-surface/95 px-2 py-1 text-[11px] font-medium text-text-secondary">
                    {creative.platform}
                </span>
                {creative.durationSec > 0 && (
                    <span className="pointer-events-none absolute bottom-3 right-3 rounded-lg bg-black/65 px-2 py-1 text-xs tabular-nums text-white">
                        {formatDuration(creative.durationSec)}
                    </span>
                )}
                {hasVideo && (
                    <span className="pointer-events-none absolute bottom-3 left-3 flex min-h-9 items-center gap-1.5 rounded-full bg-surface/95 px-3 text-xs font-medium text-text-primary">
                        <Play className="size-3.5" aria-hidden="true" /> Xem video
                    </span>
                )}
            </button>
            {selectable && (
                <label className="absolute right-1 top-1 z-10 flex size-11 cursor-pointer items-center justify-center">
                    <input
                        type="checkbox"
                        checked={!!selected}
                        onChange={onToggleSelect}
                        aria-label={`${selected ? "Bỏ chọn" : "Chọn"} ${creative.title}`}
                        className="peer sr-only"
                    />
                    <span
                        className={cn(
                            "grid size-7 place-items-center rounded-lg bg-surface text-transparent shadow-sm peer-focus-visible:ring-2 peer-focus-visible:ring-ring peer-focus-visible:ring-offset-2",
                            selected && "bg-primary text-white",
                        )}
                        aria-hidden="true"
                    >
                        <Check className="size-4" />
                    </span>
                </label>
            )}
            <div className="flex min-w-0 flex-1 flex-col gap-3 p-4">
                <div className="flex flex-wrap gap-1.5 text-[11px] text-text-secondary">
                    <span className="rounded-full bg-surface-soft px-2 py-1">{fileLabel}</span>
                    {isIllustrativeCreative(creative) && (
                        <span className="rounded-full bg-surface-soft px-2 py-1">Minh họa</span>
                    )}
                </div>
                <button
                    type="button"
                    onClick={() => onAction("open")}
                    aria-label={`Mở chi tiết ${creative.title}`}
                    className="min-h-11 min-w-0 rounded-lg text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                    <span className="line-clamp-2 text-sm font-semibold leading-snug text-text-primary">
                        {creative.title}
                    </span>
                    {creative.hookExcerpt && (
                        <span className="mt-1.5 block line-clamp-2 text-xs leading-5 text-text-secondary">
                            “{creative.hookExcerpt}”
                        </span>
                    )}
                </button>
                <p className="truncate text-xs text-text-secondary">
                    {creative.brandOrCreator}
                    <span className="mx-1.5 text-text-tertiary">·</span>
                    {creative.angle}
                </p>
                <div className="flex flex-wrap items-center gap-2">
                    <AnalysisStatusChip status={creative.analysisStatus} />
                </div>
                <div className="mt-auto flex items-center justify-between gap-2 pt-1">
                    <Button
                        type="button"
                        variant="ghost"
                        className={cn(
                            "min-h-11 min-w-0 flex-1 whitespace-normal px-3 text-left text-sm leading-5",
                            hasVideo
                                ? "bg-primary-soft text-primary hover:bg-primary-soft"
                                : "bg-surface-soft text-text-primary hover:bg-surface-muted",
                        )}
                        onClick={() => onAction(hasVideo ? "remake" : "open")}
                    >
                        {hasVideo ? (
                            <Sparkles className="size-4 shrink-0" aria-hidden="true" />
                        ) : (
                            <ArrowRight className="size-4 shrink-0" aria-hidden="true" />
                        )}
                        <span>{hasVideo ? "Tạo với Smart Remake" : "Mở chi tiết"}</span>
                    </Button>
                    <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                            <button
                                type="button"
                                aria-label={`Thao tác khác cho ${creative.title}`}
                                className="inline-flex size-11 shrink-0 items-center justify-center rounded-xl text-text-secondary hover:bg-surface-soft focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                            >
                                <MoreHorizontal className="size-4" aria-hidden="true" />
                            </button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end" className="w-60">
                            {hasVideo && (
                                <DropdownMenuItem
                                    className="min-h-11"
                                    onSelect={() => onAction("preview")}
                                >
                                    <Play className="size-4" /> Xem video
                                </DropdownMenuItem>
                            )}
                            <DropdownMenuItem
                                className="min-h-11"
                                onSelect={() => onAction("open")}
                            >
                                Mở chi tiết và phân tích
                            </DropdownMenuItem>
                            <DropdownMenuItem
                                className="min-h-11"
                                onSelect={() => onAction("analyze")}
                                disabled={processing}
                            >
                                <Sparkles className="size-4" />
                                {canAdapt
                                    ? "Phân tích lại cách làm"
                                    : processing
                                      ? "Đang phân tích"
                                      : "Phân tích cách làm"}
                            </DropdownMenuItem>
                            <DropdownMenuItem
                                className="min-h-11"
                                onSelect={() => onAction("adapt")}
                                disabled={!canAdapt}
                            >
                                <Package className="size-4" /> Áp dụng ý tưởng cho sản phẩm
                            </DropdownMenuItem>
                            <DropdownMenuItem
                                className="min-h-11"
                                onSelect={() => onAction("add-to-campaign")}
                            >
                                Thêm vào chiến dịch
                            </DropdownMenuItem>
                            <DropdownMenuSeparator />
                            <DropdownMenuItem
                                className="min-h-11"
                                onSelect={() => onAction("move-board")}
                            >
                                <FolderInput className="size-4" /> Thêm vào bộ sưu tập
                            </DropdownMenuItem>
                            <DropdownMenuItem
                                className="min-h-11"
                                onSelect={() => onAction("duplicate")}
                            >
                                <Copy className="size-4" /> Nhân bản tham khảo
                            </DropdownMenuItem>
                            <DropdownMenuSeparator />
                            <DropdownMenuItem
                                className="min-h-11 text-destructive focus:text-destructive"
                                onSelect={() => onAction("archive")}
                            >
                                <Archive className="size-4" /> Lưu trữ mục này
                            </DropdownMenuItem>
                        </DropdownMenuContent>
                    </DropdownMenu>
                </div>
            </div>
        </SurfaceCard>
    );
}
