import { cn } from "@/shared/lib/utils";
import { StatusChip } from "@/shared/ui/status-chip";
import { AnalysisStatusChip } from "./analysis-status-chip";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from "@/shared/ui/dropdown-menu";
import { Button } from "@/shared/ui/button";
import {
    Check,
    MoreHorizontal,
    Sparkles,
    Package,
    FolderInput,
    Copy,
    Archive,
    ArrowRight,
    Play,
} from "lucide-react";
import { formatDuration } from "@/features/creative-library/lib/creative-visuals";
import type { CreativeReference } from "@/features/creative-library/types/creative";
import { DemoMediaTile } from "@/shared/ui/demo-media-tile";

export type CreativeCardAction =
    "open" | "analyze" | "adapt" | "add-to-campaign" | "move-board" | "duplicate" | "archive";

export function CreativeCard({
    creative,
    selected,
    selectable,
    productLabel,
    compact,
    onToggleSelect,
    onAction,
}: {
    creative: CreativeReference;
    selected?: boolean;
    selectable?: boolean;
    productLabel?: string;
    compact?: boolean;
    onToggleSelect?: () => void;
    onAction: (a: CreativeCardAction) => void;
}) {
    const canAnalyze =
        creative.analysisStatus === "ready" ||
        creative.analysisStatus === "unanalyzed" ||
        creative.analysisStatus === "failed";
    const markerTone =
        creative.analysisStatus === "analyzed"
            ? "ok"
            : creative.analysisStatus === "failed"
              ? "destructive"
              : creative.analysisStatus === "processing"
                ? "warn"
                : "info";

    return (
        <div
            className={cn(
                "surface-card-interactive inner-top-highlight group relative flex flex-col overflow-hidden",
                selected && "ring-2 ring-primary/60 bg-primary-softer",
            )}
        >
            {/* Media */}
            <button
                type="button"
                onClick={() => onAction("open")}
                aria-label={`Open ${creative.title}`}
                className="relative block w-full overflow-hidden focus-visible:outline-none"
                style={{ aspectRatio: compact ? "16 / 10" : "4 / 5" }}
            >
                <DemoMediaTile
                    mediaUrl={creative.mediaUrl}
                    mediaKind={creative.mediaKind}
                    posterUrl={creative.posterUrl}
                    alt={creative.title}
                    seed={creative.thumbSeed}
                    label={creative.angle}
                    badges={[
                        creative.platform,
                        formatDuration(creative.durationSec),
                        creative.mediaAspectRatio ?? "demo",
                    ]}
                    score={
                        typeof creative.dnaScore === "number"
                            ? `DNA ${creative.dnaScore}`
                            : undefined
                    }
                    markers={[
                        { at: 8, tone: "info" },
                        { at: 34, tone: markerTone },
                        { at: 62, tone: "ok" },
                        { at: 88, tone: "warn" },
                    ]}
                    aspect={creative.mediaAspectRatio ?? (compact ? "16 / 10" : "4 / 5")}
                    fit={creative.mediaAspectRatio === "9:16" ? "contain" : "cover"}
                    className="absolute inset-0"
                />

                {selectable && (
                    <span
                        onClick={(e) => {
                            e.preventDefault();
                            e.stopPropagation();
                            onToggleSelect?.();
                        }}
                        role="checkbox"
                        aria-checked={!!selected}
                        aria-label={`${selected ? "Deselect" : "Select"} ${creative.title}`}
                        tabIndex={0}
                        onKeyDown={(e) => {
                            if (e.key === " " || e.key === "Enter") {
                                e.preventDefault();
                                onToggleSelect?.();
                            }
                        }}
                        className={cn(
                            "absolute right-2.5 top-2.5 grid h-6 w-6 place-items-center rounded-md border border-white/60 bg-white/30 backdrop-blur-sm transition-all",
                            selected && "border-primary bg-primary text-primary-foreground",
                        )}
                    >
                        {selected && <Check className="h-3.5 w-3.5" />}
                    </span>
                )}

                <span className="absolute bottom-2.5 left-2.5 grid h-9 w-9 place-items-center rounded-full bg-white/85 text-text-primary shadow-md-card opacity-0 transition-opacity duration-200 group-hover:opacity-100">
                    <Play className="h-4 w-4 fill-current" />
                </span>
            </button>

            {/* Body */}
            <div className="flex min-w-0 flex-1 flex-col gap-2 p-3.5">
                <div className="flex items-center gap-2">
                    <AnalysisStatusChip status={creative.analysisStatus} />
                    {creative.usedInCampaignId && (
                        <StatusChip tone="info">Used in campaign</StatusChip>
                    )}
                </div>

                <button
                    type="button"
                    onClick={() => onAction("open")}
                    className="min-w-0 text-left focus-visible:outline-none"
                >
                    <p className="line-clamp-2 text-sm font-semibold leading-snug text-text-primary">
                        {creative.title}
                    </p>
                    <p className="mt-0.5 line-clamp-2 text-xs text-text-secondary">
                        “{creative.hookExcerpt}”
                    </p>
                </button>

                <div className="mt-auto flex items-center justify-between gap-2 pt-1.5 text-[11px] text-text-tertiary">
                    <span className="min-w-0 truncate">
                        <span className="text-text-secondary">{creative.brandOrCreator}</span>
                        <span className="mx-1.5">·</span>
                        <span>{creative.angle}</span>
                    </span>
                </div>

                <div className="flex items-center justify-between gap-2 border-t border-hairline/60 pt-2.5">
                    <span className="min-w-0 truncate text-[11px] text-text-tertiary">
                        {productLabel ? (
                            <span className="inline-flex items-center gap-1 text-text-secondary">
                                <Package className="h-3 w-3" />
                                {productLabel}
                            </span>
                        ) : (
                            "Not linked"
                        )}
                    </span>
                    <div className="flex items-center gap-1">
                        {canAnalyze && (
                            <Button
                                size="sm"
                                variant="secondary"
                                className="h-7 px-2 text-[11px]"
                                onClick={() => onAction("analyze")}
                            >
                                <Sparkles className="h-3 w-3" />
                                Analyze
                            </Button>
                        )}
                        {creative.analysisStatus === "analyzed" && (
                            <Button
                                size="sm"
                                variant="secondary"
                                className="h-7 px-2 text-[11px]"
                                onClick={() => onAction("adapt")}
                            >
                                Adapt
                                <ArrowRight className="h-3 w-3" />
                            </Button>
                        )}
                        <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                                <button
                                    type="button"
                                    aria-label="More actions"
                                    className="inline-flex h-7 w-7 items-center justify-center rounded-md text-text-tertiary transition-colors hover:bg-surface-soft hover:text-text-primary focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                                >
                                    <MoreHorizontal className="h-4 w-4" />
                                </button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end" className="w-52">
                                <DropdownMenuItem onSelect={() => onAction("open")}>
                                    Open analysis
                                </DropdownMenuItem>
                                <DropdownMenuItem onSelect={() => onAction("analyze")}>
                                    <Sparkles className="h-4 w-4" />
                                    Analyze Creative DNA
                                </DropdownMenuItem>
                                <DropdownMenuItem onSelect={() => onAction("adapt")}>
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
            </div>
        </div>
    );
}
