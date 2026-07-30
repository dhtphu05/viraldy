import { useRef } from "react";
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
    "open" | "analyze" | "adapt" | "add-to-campaign" | "move-board" | "duplicate" | "archive";

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
    const videoRef = useRef<HTMLVideoElement>(null);
    const canAdapt = creative.analysisStatus === "analyzed";
    const isProcessing = creative.analysisStatus === "processing";
    const hasVideo = creative.mediaKind === "video" && !!creative.mediaUrl;
    const imageUrl =
        creative.posterUrl ??
        creative.thumbnailUrl ??
        (creative.mediaKind === "image" ? creative.mediaUrl : undefined);

    function setPreview(active: boolean) {
        const video = videoRef.current;
        if (!video) return;
        if (active) {
            void video.play().catch(() => undefined);
            return;
        }
        video.pause();
    }

    const contextualAction = canAdapt
        ? { label: "Adapt pattern", action: "adapt" as const, icon: ArrowRight }
        : isProcessing
          ? { label: "View progress", action: "open" as const, icon: ArrowRight }
          : { label: "Analyze DNA", action: "analyze" as const, icon: Sparkles };
    const ContextualIcon = contextualAction.icon;

    return (
        <SurfaceCard
            variant="interactive"
            padding="none"
            data-selected={selected}
            role="article"
            aria-label={creative.title}
            className="group relative flex min-w-0 flex-col overflow-hidden"
            onMouseEnter={() => setPreview(true)}
            onMouseLeave={() => setPreview(false)}
            onFocusCapture={() => setPreview(true)}
            onBlurCapture={(event) => {
                if (!event.currentTarget.contains(event.relatedTarget)) setPreview(false);
            }}
        >
            <button
                type="button"
                onClick={() => onAction("open")}
                aria-label={`Open ${creative.title}`}
                className="relative block w-full overflow-hidden bg-surface-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring"
                style={{ aspectRatio: compact ? "16 / 10" : "4 / 5" }}
            >
                {hasVideo ? (
                    <video
                        ref={videoRef}
                        src={creative.mediaUrl}
                        poster={creative.posterUrl ?? creative.thumbnailUrl}
                        muted
                        loop
                        playsInline
                        preload="metadata"
                        aria-hidden
                        className={cn(
                            "absolute inset-0 h-full w-full bg-black",
                            creative.mediaAspectRatio === "9:16"
                                ? "object-contain"
                                : "object-cover",
                        )}
                    />
                ) : imageUrl ? (
                    <img
                        src={imageUrl}
                        alt=""
                        loading="lazy"
                        className={cn(
                            "absolute inset-0 h-full w-full bg-surface-muted",
                            creative.mediaAspectRatio === "9:16"
                                ? "object-contain"
                                : "object-cover",
                        )}
                    />
                ) : (
                    <span className="absolute inset-0 grid place-items-center bg-surface-muted text-text-tertiary">
                        <span className="flex flex-col items-center gap-2">
                            <span className="grid h-12 w-12 place-items-center rounded-full bg-surface">
                                <Film className="h-5 w-5" aria-hidden />
                            </span>
                            <span className="text-xs font-medium">{creative.platform}</span>
                        </span>
                    </span>
                )}

                <span className="pointer-events-none absolute left-2.5 top-2.5 flex flex-wrap items-center gap-1.5">
                    <span className="rounded-md bg-black/55 px-1.5 py-0.5 text-[10px] font-medium uppercase text-white">
                        {creative.platform}
                    </span>
                    <span className="rounded-md bg-black/55 px-1.5 py-0.5 text-[10px] font-medium tabular text-white">
                        {formatDuration(creative.durationSec)}
                    </span>
                </span>

                {hasVideo && (
                    <span className="pointer-events-none absolute bottom-2.5 left-2.5 grid h-9 w-9 place-items-center rounded-full bg-white/90 text-text-primary opacity-100 shadow-soft-card transition-opacity sm:opacity-0 sm:group-hover:opacity-100 sm:group-focus-within:opacity-100">
                        <Play className="h-4 w-4 fill-current" aria-hidden />
                    </span>
                )}
            </button>

            {selectable && (
                <label className="absolute right-2.5 top-2.5 z-10 cursor-pointer">
                    <input
                        type="checkbox"
                        checked={!!selected}
                        onChange={onToggleSelect}
                        aria-label={`${selected ? "Deselect" : "Select"} ${creative.title}`}
                        className="peer sr-only"
                    />
                    <span
                        className={cn(
                            "grid h-7 w-7 place-items-center rounded-md border border-white/70 bg-white/90 text-transparent shadow-soft-card transition-colors peer-focus-visible:ring-2 peer-focus-visible:ring-ring peer-focus-visible:ring-offset-2",
                            selected && "border-primary bg-primary text-primary-foreground",
                        )}
                        aria-hidden
                    >
                        <Check className="h-4 w-4" />
                    </span>
                </label>
            )}

            <div className="flex min-w-0 flex-1 flex-col p-3.5">
                <AnalysisStatusChip status={creative.analysisStatus} />

                <button
                    type="button"
                    onClick={() => onAction("open")}
                    className="mt-2 min-w-0 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                    <span className="line-clamp-2 text-sm font-semibold leading-snug text-text-primary">
                        {creative.title}
                    </span>
                    <span className="mt-1 block line-clamp-2 text-xs leading-5 text-text-secondary">
                        “{creative.hookExcerpt}”
                    </span>
                </button>

                <p className="mt-3 min-w-0 truncate text-[11px] text-text-tertiary">
                    <span className="text-text-secondary">{creative.brandOrCreator}</span>
                    <span className="mx-1.5">·</span>
                    <span>{creative.angle}</span>
                </p>

                <div className="mt-auto flex items-center justify-between gap-2 border-t border-divider pt-2.5">
                    <Button
                        size="sm"
                        variant="ghost"
                        className="h-8 min-w-0 px-2 text-[11px] text-primary-active"
                        onClick={() => onAction(contextualAction.action)}
                    >
                        <ContextualIcon className="h-3.5 w-3.5" />
                        <span className="truncate">{contextualAction.label}</span>
                    </Button>

                    <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                            <button
                                type="button"
                                aria-label={`More actions for ${creative.title}`}
                                className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-text-tertiary transition-colors hover:bg-surface-soft hover:text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                            >
                                <MoreHorizontal className="h-4 w-4" />
                            </button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end" className="w-52">
                            <DropdownMenuItem onSelect={() => onAction("open")}>
                                Open analysis
                            </DropdownMenuItem>
                            <DropdownMenuItem
                                onSelect={() => onAction("analyze")}
                                disabled={isProcessing}
                            >
                                <Sparkles className="h-4 w-4" />
                                {canAdapt ? "Re-analyze Creative DNA" : "Analyze Creative DNA"}
                            </DropdownMenuItem>
                            <DropdownMenuItem
                                onSelect={() => onAction("adapt")}
                                disabled={!canAdapt}
                            >
                                <Package className="h-4 w-4" />
                                Adapt to product
                            </DropdownMenuItem>
                            <DropdownMenuItem onSelect={() => onAction("add-to-campaign")}>
                                Add to campaign
                            </DropdownMenuItem>
                            <DropdownMenuSeparator />
                            <DropdownMenuItem onSelect={() => onAction("move-board")}>
                                <FolderInput className="h-4 w-4" />
                                Move to board
                            </DropdownMenuItem>
                            <DropdownMenuItem onSelect={() => onAction("duplicate")}>
                                <Copy className="h-4 w-4" />
                                Duplicate reference
                            </DropdownMenuItem>
                            <DropdownMenuSeparator />
                            <DropdownMenuItem
                                onSelect={() => onAction("archive")}
                                className="text-destructive focus:text-destructive"
                            >
                                <Archive className="h-4 w-4" />
                                Archive
                            </DropdownMenuItem>
                        </DropdownMenuContent>
                    </DropdownMenu>
                </div>
            </div>
        </SurfaceCard>
    );
}
