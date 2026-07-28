import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useMemo, useState } from "react";
import { AppShell } from "@/widgets/app-shell/app-shell";
import { PageHeader } from "@/shared/ui/page-header";
import { SurfaceCard } from "@/shared/ui/surface-card";
import { Button } from "@/shared/ui/button";
import { Input } from "@/shared/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/shared/ui/select";
import { StatusChip } from "@/shared/ui/status-chip";
import { EmptyState } from "@/shared/ui/empty-state";
import { Plus, LayoutTemplate, Sparkles, Search } from "lucide-react";
import { useAllCampaigns, useAppStore } from "@/app/store/app-store";
import { CampaignListRow } from "@/features/campaigns/components/campaign-list-row";
import { CampaignTemplatesSheet } from "@/features/campaigns/components/campaign-templates-sheet";
import { seedProducts } from "@/features/products/data/products";
import { toast } from "sonner";
import type { CampaignPackStatus } from "@/features/campaigns/types/campaign";

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

const STATUSES: (CampaignPackStatus | "All")[] = [
    "All",
    "Draft",
    "Ready for creator",
    "Creator production",
    "Awaiting UGC",
    "Active",
    "Completed",
    "Archived",
];

const SORTS = [
    { id: "updated", label: "Recently updated" },
    { id: "created", label: "Recently created" },
    { id: "name", label: "Campaign name" },
    { id: "gmv", label: "Highest GMV" },
] as const;

function CampaignsIndex() {
    const navigate = useNavigate();
    const campaigns = useAllCampaigns();
    const duplicate = useAppStore((s) => s.duplicateCampaign);
    const archive = useAppStore((s) => s.archiveCampaign);
    const deleteLocal = useAppStore((s) => s.deleteLocalCampaign);
    const rename = useAppStore((s) => s.renameCampaign);
    const setPackStatus = useAppStore((s) => s.setPackStatus);
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
        if (status !== "All") list = list.filter((c) => (c.packStatus ?? "Draft") === status);
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
    }, [campaigns, q, status, productId, objective, sort]);

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
                    <SurfaceCard
                        padding="md"
                        className="flex flex-wrap items-center justify-between gap-3"
                    >
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
                        <Button asChild size="sm">
                            <Link to="/campaigns/new">Continue in new campaign</Link>
                        </Button>
                    </SurfaceCard>
                )}

                <SurfaceCard padding="sm" className="flex flex-wrap items-center gap-2">
                    <div className="relative min-w-[220px] flex-1">
                        <Search className="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-text-tertiary" />
                        <Input
                            className="pl-8"
                            placeholder="Search campaigns, products, objectives…"
                            value={q}
                            onChange={(e) => setQ(e.target.value)}
                        />
                    </div>
                    <Select value={status} onValueChange={(v) => setStatus(v as typeof status)}>
                        <SelectTrigger className="w-[170px]">
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
                        <SelectTrigger className="w-[180px]">
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
                        <SelectTrigger className="w-[180px]">
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
                        <SelectTrigger className="w-[180px]">
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
                </SurfaceCard>

                {filtered.length === 0 ? (
                    <SurfaceCard padding="lg">
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
                    </SurfaceCard>
                ) : (
                    <SurfaceCard padding="none" className="divide-y divide-hairline/70">
                        <div className="hidden grid-cols-[minmax(0,2.4fr)_minmax(0,1fr)_120px_120px_minmax(0,1.4fr)_auto] gap-3 px-4 py-2 text-[10px] font-semibold uppercase tracking-wide text-text-tertiary sm:grid">
                            <span>Campaign</span>
                            <span>Status</span>
                            <span>Angle</span>
                            <span>Refs · hooks</span>
                            <span>Next action</span>
                            <span />
                        </div>
                        {filtered.map((c) => (
                            <CampaignListRow
                                key={c.id}
                                campaign={c}
                                onRename={() => {
                                    const name = window.prompt("Rename campaign", c.name);
                                    if (name && name.trim()) {
                                        rename(c.id, name.trim());
                                        toast.success("Renamed");
                                    }
                                }}
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
                                onChangeStatus={() => {
                                    const next: CampaignPackStatus =
                                        (c.packStatus ?? "Draft") === "Draft"
                                            ? "Ready for creator"
                                            : "Draft";
                                    if (c.packId) {
                                        setPackStatus(c.packId, next);
                                        toast.success(`Status: ${next}`);
                                    }
                                }}
                                onArchive={() => {
                                    archive(c.id);
                                    toast.success("Campaign archived");
                                }}
                                onDelete={
                                    localSet.has(c.id)
                                        ? () => {
                                              if (
                                                  window.confirm(
                                                      "Delete this local draft? This cannot be undone.",
                                                  )
                                              ) {
                                                  deleteLocal(c.id);
                                                  toast.success("Draft deleted");
                                              }
                                          }
                                        : undefined
                                }
                            />
                        ))}
                    </SurfaceCard>
                )}
            </div>

            <CampaignTemplatesSheet open={templatesOpen} onOpenChange={setTemplatesOpen} />
        </AppShell>
    );
}
