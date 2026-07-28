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
import {
    thumbnailGradient,
    formatDuration,
} from "@/features/creative-library/lib/creative-visuals";
import type { CreativeReference } from "@/features/creative-library/types/creative";

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
                <div
                    className="absolute inset-0"
                    style={{ backgroundImage: thumbnailGradient(creative.thumbSeed) }}
                    aria-hidden
                />
                <div
                    aria-hidden
                    className="absolute inset-0 bg-[radial-gradient(circle_at_30%_25%,rgba(255,255,255,0.35),transparent_55%)]"
                />
                <div className="absolute inset-x-0 bottom-0 h-16 bg-gradient-to-t from-black/45 to-transparent" />

                <div className="absolute left-2.5 top-2.5 flex items-center gap-1.5">
                    <span className="rounded-md bg-black/40 px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-white backdrop-blur-sm">
                        {creative.platform}
                    </span>
                    <span className="rounded-md bg-black/40 px-1.5 py-0.5 text-[10px] font-medium text-white backdrop-blur-sm">
                        {formatDuration(creative.durationSec)}
                    </span>
                </div>

                {selectable && (
                    <span
                        onClick={(e) => {
                            e.preventDefault();
                            e.stopPropagation();
                            onToggleSelect?.();
                        }}
                        role="checkbox"
                        aria-checked={!!selected}
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

                {typeof creative.dnaScore === "number" && (
                    <span className="absolute bottom-2.5 right-2.5 rounded-md bg-white/90 px-2 py-0.5 text-[11px] font-semibold tabular text-text-primary shadow-sm-card">
                        DNA {creative.dnaScore}
                    </span>
                )}
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
