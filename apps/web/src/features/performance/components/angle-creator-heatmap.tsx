import { DemoMediaTile } from "@/shared/ui/demo-media-tile";
import { RightDrawer } from "@/shared/ui/right-drawer";
import { StatusChip } from "@/shared/ui/status-chip";
import { SurfaceCard } from "@/shared/ui/surface-card";
import { fmtMoney, grossProfit } from "@/features/performance/lib/performanceEngine";
import type { PerfAsset } from "@/features/performance/types/performance";
import { cn } from "@/shared/lib/utils";

export type HeatmapSelection = {
    angle: string;
    creator: string;
    assets: PerfAsset[];
    grossProfit: number;
    gmv: number;
    orders: number;
};

export function AngleCreatorHeatmap({
    assets,
    selected,
    onSelect,
}: {
    assets: PerfAsset[];
    selected?: HeatmapSelection | null;
    onSelect: (selection: HeatmapSelection) => void;
}) {
    const angles = Array.from(new Set(assets.map((asset) => asset.angle)));
    const creators = Array.from(new Set(assets.map((asset) => asset.creator)));
    const cells = angles.flatMap((angle) =>
        creators.map((creator) => buildSelection(assets, angle, creator)),
    );
    const maxPositiveProfit = Math.max(1, ...cells.map((cell) => cell.grossProfit));

    return (
        <SurfaceCard padding="none">
            <div className="flex flex-wrap items-start justify-between gap-3 border-b border-hairline px-5 py-3">
                <div>
                    <h3 className="text-sm font-semibold text-text-primary">
                        Angle × creator heatmap
                    </h3>
                    <p className="mt-0.5 text-xs text-text-tertiary">
                        Gross profit by creative pairing
                    </p>
                </div>
                <div className="flex flex-wrap gap-2 text-[10px] text-text-tertiary">
                    <Legend swatch="bg-ok-soft ring-ok/30" label="Strong" />
                    <Legend swatch="bg-info-soft ring-info/30" label="Promising" />
                    <Legend swatch="bg-warn-soft ring-warn/30" label="Watch" />
                    <Legend swatch="bg-destructive-soft ring-destructive/30" label="Losing" />
                </div>
            </div>

            <div className="overflow-x-auto p-4">
                <div
                    className="grid min-w-[620px] gap-1.5"
                    style={{
                        gridTemplateColumns: `minmax(150px, 1.3fr) repeat(${creators.length}, minmax(118px, 1fr))`,
                    }}
                >
                    <div />
                    {creators.map((creator) => (
                        <div
                            key={creator}
                            className="truncate px-2 pb-1 text-center text-[11px] font-medium text-text-secondary"
                            title={creator}
                        >
                            {creator}
                        </div>
                    ))}

                    {angles.map((angle) => (
                        <HeatmapRow
                            key={angle}
                            angle={angle}
                            creators={creators}
                            assets={assets}
                            maxPositiveProfit={maxPositiveProfit}
                            selected={selected}
                            onSelect={onSelect}
                        />
                    ))}
                </div>
            </div>
        </SurfaceCard>
    );
}

function HeatmapRow({
    angle,
    creators,
    assets,
    maxPositiveProfit,
    selected,
    onSelect,
}: {
    angle: string;
    creators: string[];
    assets: PerfAsset[];
    maxPositiveProfit: number;
    selected?: HeatmapSelection | null;
    onSelect: (selection: HeatmapSelection) => void;
}) {
    return (
        <>
            <div className="flex min-h-16 items-center rounded-md bg-surface-soft/60 px-3 text-xs font-medium text-text-primary">
                {angle}
            </div>
            {creators.map((creator) => {
                const cell = buildSelection(assets, angle, creator);
                if (cell.assets.length === 0) {
                    return (
                        <div
                            key={`${angle}-${creator}`}
                            aria-label={`${angle} with ${creator}: no assets`}
                            className="min-h-16 rounded-md border border-dashed border-hairline bg-surface-soft/20"
                        />
                    );
                }

                const active = selected?.angle === cell.angle && selected.creator === cell.creator;
                return (
                    <button
                        key={`${angle}-${creator}`}
                        type="button"
                        onClick={() => onSelect(cell)}
                        aria-label={`${angle} with ${creator}: ${fmtMoney(cell.grossProfit)} gross profit from ${cell.assets.length} asset${cell.assets.length === 1 ? "" : "s"}`}
                        className={cn(
                            "group min-h-16 rounded-md px-3 py-2 text-left ring-1 transition-[transform,box-shadow,background-color] duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                            heatmapTone(cell.grossProfit, maxPositiveProfit),
                            "hover:-translate-y-0.5 hover:shadow-md-card",
                            active && "ring-2 ring-primary",
                        )}
                    >
                        <span className="block tabular text-sm font-semibold text-text-primary">
                            {fmtMoney(cell.grossProfit)}
                        </span>
                        <span className="mt-0.5 block text-[10px] text-text-secondary">
                            {cell.orders} orders · {cell.assets.length} asset
                            {cell.assets.length === 1 ? "" : "s"}
                        </span>
                    </button>
                );
            })}
        </>
    );
}

export function HeatmapAssetDrawer({
    selection,
    onOpenChange,
}: {
    selection: HeatmapSelection | null;
    onOpenChange: (open: boolean) => void;
}) {
    if (!selection) return null;

    return (
        <RightDrawer
            open
            onOpenChange={onOpenChange}
            title={`${selection.angle} × ${selection.creator}`}
            description={`${fmtMoney(selection.grossProfit)} gross profit · ${selection.orders} orders`}
            size="lg"
        >
            <div className="space-y-6">
                <div className="grid grid-cols-3 gap-3 border-b border-hairline pb-5">
                    <Metric label="Assets" value={String(selection.assets.length)} />
                    <Metric label="GMV" value={fmtMoney(selection.gmv)} />
                    <Metric label="Gross profit" value={fmtMoney(selection.grossProfit)} />
                </div>

                <div className="divide-y divide-hairline">
                    {selection.assets.map((asset) => (
                        <article
                            key={asset.id}
                            className="grid gap-4 py-5 first:pt-0 sm:grid-cols-2"
                        >
                            <DemoMediaTile
                                mediaUrl={asset.mediaUrl}
                                mediaKind={asset.mediaKind}
                                posterUrl={asset.posterUrl}
                                seed={asset.id}
                                label={asset.name}
                                badges={[asset.version, asset.mediaAspectRatio ?? "asset"]}
                                aspect="16 / 9"
                                fit={asset.mediaAspectRatio === "9:16" ? "contain" : "cover"}
                                controls={asset.mediaKind === "video"}
                                showPlay={asset.mediaKind !== "video"}
                                className="rounded-md bg-black"
                            />
                            <div className="min-w-0">
                                <div className="flex flex-wrap items-center gap-2">
                                    <StatusChip
                                        tone={grossProfit(asset) >= 0 ? "ok" : "destructive"}
                                    >
                                        {grossProfit(asset) >= 0 ? "Profitable" : "Losing"}
                                    </StatusChip>
                                    <StatusChip tone="neutral">UGC {asset.ugcScore}</StatusChip>
                                </div>
                                <h4 className="mt-3 text-sm font-semibold text-text-primary">
                                    {asset.name}
                                </h4>
                                <p className="mt-1 text-xs text-text-secondary">{asset.hook}</p>
                                <dl className="mt-4 grid grid-cols-2 gap-3 text-xs">
                                    <Metric label="Views" value={asset.views.toLocaleString()} />
                                    <Metric
                                        label="CTR"
                                        value={`${(asset.ctr * 100).toFixed(1)}%`}
                                    />
                                    <Metric label="Orders" value={String(asset.orders)} />
                                    <Metric label="GMV" value={fmtMoney(asset.gmv)} />
                                </dl>
                            </div>
                        </article>
                    ))}
                </div>
            </div>
        </RightDrawer>
    );
}

function buildSelection(assets: PerfAsset[], angle: string, creator: string): HeatmapSelection {
    const matching = assets.filter((asset) => asset.angle === angle && asset.creator === creator);
    return {
        angle,
        creator,
        assets: matching,
        grossProfit: matching.reduce((total, asset) => total + grossProfit(asset), 0),
        gmv: matching.reduce((total, asset) => total + asset.gmv, 0),
        orders: matching.reduce((total, asset) => total + asset.orders, 0),
    };
}

function heatmapTone(value: number, maxPositiveProfit: number) {
    if (value < 0) return "bg-destructive-soft ring-destructive/25";
    const ratio = value / maxPositiveProfit;
    if (ratio >= 0.72) return "bg-ok-soft ring-ok/25";
    if (ratio >= 0.38) return "bg-info-soft ring-info/25";
    return "bg-warn-soft ring-warn/25";
}

function Metric({ label, value }: { label: string; value: string }) {
    return (
        <div className="min-w-0">
            <p className="text-[10px] uppercase tracking-wide text-text-tertiary">{label}</p>
            <p className="mt-0.5 truncate tabular text-sm font-semibold text-text-primary">
                {value}
            </p>
        </div>
    );
}

function Legend({ swatch, label }: { swatch: string; label: string }) {
    return (
        <span className="inline-flex items-center gap-1.5">
            <span className={cn("h-2.5 w-2.5 rounded-[3px] ring-1", swatch)} />
            {label}
        </span>
    );
}
