import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useMemo, useState } from "react";
import { AppShell } from "@/widgets/app-shell/app-shell";
import { PageHeader } from "@/shared/ui/page-header";
import { Button } from "@/shared/ui/button";
import { Input } from "@/shared/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/shared/ui/select";
import { StatusChip } from "@/shared/ui/status-chip";
import { EmptyState } from "@/shared/ui/empty-state";
import { Plus, LayoutTemplate, Sparkles, Search } from "lucide-react";
import { useAllCampaigns, useAppStore } from "@/app/store/app-store";
import { CampaignListRow } from "@/features/campaigns/components/campaign-list-row";
import { CampaignTemplatesSheet } from "@/features/campaigns/components/campaign-templates-sheet";
import { CampaignRenameDialog } from "@/features/campaigns/components/campaign-rename-dialog";
import { CampaignDeleteDialog } from "@/features/campaigns/components/campaign-delete-dialog";
import { seedProducts } from "@/features/products/data/products";
import { toast } from "sonner";
import {
    campaignLifecycleLabel,
    selectCampaignReadiness,
} from "@/features/campaigns/lib/campaignReadiness";

export const Route = createFileRoute("/campaigns/")({
    head: () => ({
        meta: [
            { title: "Campaigns — Viraldy" },
            {
                name: "description",
                content: "Turn products and creative references into structured creator campaigns.",
            },
        ],
    }),
    component: CampaignsIndex,
});

const STATUSES = [
    "All",
    "Draft",
    "Ready to review",
    "Creator-ready",
    "Creator production",
    "UGC received",
    "Live",
] as const;

const SORTS = [
    { id: "updated", label: "Recently updated" },
    { id: "created", label: "Recently created" },
    { id: "name", label: "Campaign name" },
    { id: "gmv", label: "Highest GMV" },
] as const;

function CampaignsIndex() {
    const navigate = useNavigate();
    const campaigns = useAllCampaigns();
    const packs = useAppStore((s) => s.packs);
    const duplicate = useAppStore((s) => s.duplicateCampaign);
    const archive = useAppStore((s) => s.archiveCampaign);
    const deleteLocal = useAppStore((s) => s.deleteLocalCampaign);
    const rename = useAppStore((s) => s.renameCampaign);
    const localCampaignSummaries = useAppStore((s) => s.localCampaignSummaries);
    const localSet = useMemo(
        () => new Set(localCampaignSummaries.map((c) => c.id)),
        [localCampaignSummaries],
    );
    const lastAdaptation = useAppStore((s) => s.lastAdaptation);
    const creatives = useAppStore((s) => s.creatives);
    const handoffCreative = lastAdaptation
        ? creatives.find((c) => c.id === lastAdaptation.creativeId)
        : undefined;
    const handoffProduct = lastAdaptation
        ? seedProducts.find((p) => p.id === lastAdaptation.productId)
        : undefined;

    const [q, setQ] = useState("");
    const [status, setStatus] = useState<(typeof STATUSES)[number]>("All");
    const [productId, setProductId] = useState<string>("all");
    const [objective, setObjective] = useState<string>("all");
    const [sort, setSort] = useState<(typeof SORTS)[number]["id"]>("updated");
    const [templatesOpen, setTemplatesOpen] = useState(false);
    const [renameTarget, setRenameTarget] = useState<{ id: string; name: string } | null>(null);
    const [deleteTarget, setDeleteTarget] = useState<{ id: string; name: string } | null>(null);

    const objectives = useMemo(
        () => Array.from(new Set(campaigns.map((c) => c.objective).filter(Boolean))),
        [campaigns],
    );

    const filtered = useMemo(() => {
        let list = campaigns.slice();
        const query = q.trim().toLowerCase();
        if (query) {
            list = list.filter(
                (c) =>
                    c.name.toLowerCase().includes(query) ||
                    c.product.toLowerCase().includes(query) ||
                    (c.objective ?? "").toLowerCase().includes(query),
            );
        }
        if (status !== "All") {
            list = list.filter((campaign) => {
                const pack = campaign.packId ? packs[campaign.packId] : undefined;
                return (
                    pack &&
                    campaignLifecycleLabel(selectCampaignReadiness(pack).lifecycle) === status
                );
            });
        }
        if (productId !== "all") list = list.filter((c) => c.product === productId);
        if (objective !== "all") list = list.filter((c) => c.objective === objective);
        if (sort === "name") list.sort((a, b) => a.name.localeCompare(b.name));
        if (sort === "gmv") list.sort((a, b) => b.gmv - a.gmv);
        if (sort === "updated")
            list.sort(
                (a, b) =>
                    new Date(b.updatedAt ?? 0).getTime() - new Date(a.updatedAt ?? 0).getTime(),
            );
        return list;
    }, [campaigns, packs, q, status, productId, objective, sort]);

    return (
        <AppShell>
            <div className="flex flex-col gap-6">
                <PageHeader
                    title="Campaigns"
                    description="Turn products and creative references into structured creator campaigns."
                    actions={
                        <div className="flex flex-wrap gap-2">
                            <Button variant="secondary" onClick={() => setTemplatesOpen(true)}>
                                <LayoutTemplate className="h-4 w-4" />
                                View templates
                            </Button>
                            <Button onClick={() => navigate({ to: "/campaigns/new" })}>
                                <Plus className="h-4 w-4" />
                                Create campaign
                            </Button>
                        </div>
                    }
                />

                {handoffCreative && handoffProduct && (
                    <div className="flex flex-col gap-3 border-y border-primary/20 bg-primary-softer px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
                        <div className="flex min-w-0 items-center gap-3">
                            <span className="grid h-9 w-9 shrink-0 place-items-center rounded-md bg-primary-soft text-primary">
                                <Sparkles className="h-4 w-4" />
                            </span>
                            <div className="min-w-0">
                                <div className="flex flex-wrap items-center gap-2">
                                    <StatusChip tone="info" dot>
                                        Adaptation queued
                                    </StatusChip>
                                    <p className="truncate text-sm font-medium text-text-primary">
                                        {handoffCreative.title} → {handoffProduct.name}
                                    </p>
                                </div>
                                <p className="mt-0.5 text-xs text-text-secondary">
                                    Continue in a new campaign to keep the reference and product
                                    linked.
                                </p>
                            </div>
                        </div>
                        <Button asChild size="sm" className="w-full sm:w-auto">
                            <Link to="/campaigns/new">Create campaign from this adaptation</Link>
                        </Button>
                    </div>
                )}

                <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-[minmax(220px,1fr)_repeat(4,180px)]">
                    <div className="relative min-w-[220px] flex-1">
                        <Search className="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-text-tertiary" />
                        <Input
                            className="pl-8"
                            placeholder="Search campaigns, products, objectives…"
                            aria-label="Search campaigns, products, and objectives"
                            value={q}
                            onChange={(e) => setQ(e.target.value)}
                        />
                    </div>
                    <Select value={status} onValueChange={(v) => setStatus(v as typeof status)}>
                        <SelectTrigger className="w-full" aria-label="Filter campaigns by status">
                            <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                            {STATUSES.map((s) => (
                                <SelectItem key={s} value={s}>
                                    {s}
                                </SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                    <Select value={productId} onValueChange={setProductId}>
                        <SelectTrigger className="w-full" aria-label="Filter campaigns by product">
                            <SelectValue placeholder="Product" />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="all">All products</SelectItem>
                            {Array.from(new Set(campaigns.map((c) => c.product))).map((p) => (
                                <SelectItem key={p} value={p}>
                                    {p}
                                </SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                    <Select value={objective} onValueChange={setObjective}>
                        <SelectTrigger
                            className="w-full"
                            aria-label="Filter campaigns by objective"
                        >
                            <SelectValue placeholder="Objective" />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="all">All objectives</SelectItem>
                            {objectives.map((o) => (
                                <SelectItem key={o!} value={o!}>
                                    {o}
                                </SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                    <Select value={sort} onValueChange={(v) => setSort(v as typeof sort)}>
                        <SelectTrigger className="w-full" aria-label="Sort campaigns">
                            <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                            {SORTS.map((s) => (
                                <SelectItem key={s.id} value={s.id}>
                                    {s.label}
                                </SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                </div>

                {filtered.length === 0 ? (
                    <div className="border-y border-divider bg-surface p-7">
                        <EmptyState
                            title={
                                q
                                    ? "No campaigns match your search"
                                    : "Create your first creator campaign"
                            }
                            description={
                                q
                                    ? "Try clearing filters or searching a different product."
                                    : "Turn a product and selected creative references into a structured brief, hooks, script, and storyboard."
                            }
                            action={
                                <Button onClick={() => navigate({ to: "/campaigns/new" })}>
                                    <Plus className="h-4 w-4" />
                                    Create campaign
                                </Button>
                            }
                        />
                    </div>
                ) : (
                    <div className="divide-y divide-divider overflow-hidden rounded-md border border-control-border bg-surface">
                        <div className="sticky top-0 z-10 hidden gap-3 bg-surface px-4 py-2 text-[10px] font-semibold uppercase text-text-tertiary md:grid md:grid-cols-[minmax(0,2.4fr)_minmax(0,1fr)_minmax(0,1.4fr)_auto] xl:grid-cols-[minmax(0,2.4fr)_minmax(0,1fr)_120px_120px_minmax(0,1.4fr)_auto]">
                            <span>Campaign</span>
                            <span>Status</span>
                            <span className="hidden xl:block">Angle</span>
                            <span className="hidden xl:block">Refs · hooks</span>
                            <span>Next action</span>
                            <span />
                        </div>
                        {filtered.map((c) => (
                            <CampaignListRow
                                key={c.id}
                                campaign={c}
                                readiness={
                                    c.packId && packs[c.packId]
                                        ? selectCampaignReadiness(packs[c.packId])
                                        : undefined
                                }
                                onRename={() => setRenameTarget({ id: c.id, name: c.name })}
                                onDuplicate={() => {
                                    const newId = duplicate(c.id);
                                    if (newId) {
                                        toast.success("Duplicated to a new draft");
                                        navigate({
                                            to: "/campaigns/$campaignId",
                                            params: { campaignId: newId },
                                        });
                                    }
                                }}
                                onArchive={() => {
                                    archive(c.id);
                                    toast.success("Campaign archived");
                                }}
                                onDelete={
                                    localSet.has(c.id)
                                        ? () => setDeleteTarget({ id: c.id, name: c.name })
                                        : undefined
                                }
                            />
                        ))}
                    </div>
                )}
            </div>

            <CampaignTemplatesSheet open={templatesOpen} onOpenChange={setTemplatesOpen} />
            <CampaignRenameDialog
                open={!!renameTarget}
                currentName={renameTarget?.name ?? ""}
                onOpenChange={(open) => {
                    if (!open) setRenameTarget(null);
                }}
                onRename={(name) => {
                    if (!renameTarget) return;
                    rename(renameTarget.id, name);
                    toast.success("Renamed");
                }}
            />
            <CampaignDeleteDialog
                open={!!deleteTarget}
                campaignName={deleteTarget?.name ?? "This campaign"}
                onOpenChange={(open) => {
                    if (!open) setDeleteTarget(null);
                }}
                onDelete={() => {
                    if (!deleteTarget) return;
                    deleteLocal(deleteTarget.id);
                    setDeleteTarget(null);
                    toast.success("Draft deleted");
                }}
            />
        </AppShell>
    );
}
