import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { AppShell } from "@/widgets/app-shell/app-shell";
import { PageHeader } from "@/shared/ui/page-header";
import { SurfaceCard } from "@/shared/ui/surface-card";
import { MetricCard } from "@/shared/ui/metric-card";
import { DecisionBanner } from "@/shared/ui/decision-banner";
import { RecommendationRow } from "@/shared/ui/recommendation-row";
import { CampaignRow } from "@/shared/ui/campaign-row";
import { RightDrawer } from "@/shared/ui/right-drawer";
import { ProcessingStepper, type Step } from "@/shared/ui/processing-stepper";
import { Button } from "@/shared/ui/button";
import { StatusChip } from "@/shared/ui/status-chip";
import { RelativeTime } from "@/shared/ui/relative-time";
import { AnalyzeCreativeDialog } from "@/features/dashboard/components/analyze-creative-dialog";
import { CreateCampaignDialog } from "@/features/dashboard/components/create-campaign-dialog";
import { overviewMetrics, decisionQueue } from "@/features/dashboard/mocks/dashboard";
import { recommendations as seedRecs } from "@/features/dashboard/mocks/recommendations";
import { activities } from "@/features/dashboard/mocks/activities";
import { useAllCampaigns, useAppStore } from "@/app/store/app-store";
import { useMemo, useState } from "react";
import { toast } from "sonner";
import {
    Sparkles,
    Plus,
    ClipboardCheck,
    MessageSquare,
    FolderKanban,
    ShieldCheck,
    Lightbulb,
    ArrowRight,
    Workflow,
} from "lucide-react";
import type { DecisionItem, Recommendation } from "@/shared/types";

export const Route = createFileRoute("/dashboard")({
    head: () => ({
        meta: [
            { title: "Overview — Viraldy" },
            {
                name: "description",
                content:
                    "Decision Center: pending decisions, business value, and Scale / Fix / Kill / Rehire recommendations.",
            },
        ],
    }),
    component: DashboardPage,
});

const activityIcon = {
    analysis: Sparkles,
    message: MessageSquare,
    pack: FolderKanban,
    asset: ShieldCheck,
    recommendation: Lightbulb,
} as const;

function DashboardPage() {
    const navigate = useNavigate();
    const campaigns = useAllCampaigns();
    const dismissed = useAppStore((s) => s.dismissedRecommendations);
    const accepted = useAppStore((s) => s.acceptedRecommendations);

    const acceptRec = useAppStore((s) => s.acceptRecommendation);

    const [analyzeOpen, setAnalyzeOpen] = useState(false);
    const [createOpen, setCreateOpen] = useState(false);
    const [activeDecision, setActiveDecision] = useState<DecisionItem | null>(null);
    const [evidenceRec, setEvidenceRec] = useState<Recommendation | null>(null);
    const [variantsRec, setVariantsRec] = useState<Recommendation | null>(null);
    const [variantsSteps, setVariantsSteps] = useState<Step[]>([]);

    const visibleRecs = useMemo(
        () => seedRecs.filter((r) => !dismissed.includes(r.id) && !accepted.includes(r.id)),
        [dismissed, accepted],
    );

    async function runVariants(rec: Recommendation) {
        const seq: Step[] = [
            { key: "brief", label: "Drafting creative brief", status: "active" },
            { key: "hooks", label: "Generating 6 hook variants", status: "pending" },
            { key: "match", label: "Matching creators", status: "pending" },
            { key: "pack", label: "Preparing Campaign Pack", status: "pending" },
        ];
        setVariantsRec(rec);
        setVariantsSteps(seq);
        for (let i = 0; i < seq.length; i++) {
            await new Promise((r) => setTimeout(r, 550));
            setVariantsSteps((prev) =>
                prev.map((s, idx) =>
                    idx <= i
                        ? { ...s, status: "done" }
                        : idx === i + 1
                          ? { ...s, status: "active" }
                          : s,
                ),
            );
        }
        await new Promise((r) => setTimeout(r, 300));
        acceptRec(rec.id);
        setVariantsRec(null);
        setVariantsSteps([]);
        toast.success("Variants ready", {
            description: "6 hook variants added to the Campaign Pack.",
        });
    }

    function openDecisionObject(item: DecisionItem) {
        if (item.objectType === "Campaign") {
            const campaign = campaigns.find((c) => c.name === item.object);
            if (campaign) {
                navigate({
                    to: "/campaigns/$campaignId",
                    params: { campaignId: campaign.id },
                });
                return;
            }
            navigate({ to: "/campaigns" });
            return;
        }
        if (item.objectType === "UGC" || item.objectType === "Asset") {
            navigate({ to: "/ugc-review" });
            return;
        }
        navigate({ to: "/campaigns" });
    }

    return (
        <AppShell>
            <div className="flex flex-col gap-8">
                <PageHeader
                    title="Overview"
                    description="Track creative decisions, campaign momentum, and the next actions that can influence GMV."
                    actions={
                        <>
                            <Button variant="secondary" onClick={() => setCreateOpen(true)}>
                                <Plus className="h-4 w-4" />
                                Create campaign
                            </Button>
                            <Button onClick={() => setAnalyzeOpen(true)}>
                                <Sparkles className="h-4 w-4" />
                                Analyze creative
                            </Button>
                        </>
                    }
                />

                {/* Context banner */}
                <SurfaceCard
                    padding="md"
                    className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center"
                >
                    <span className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-primary-soft text-primary-active">
                        <ClipboardCheck className="h-4 w-4" />
                    </span>
                    <div className="min-w-0 flex-1">
                        <p className="text-sm font-semibold text-text-primary">
                            {decisionQueue.length} decisions need your attention today
                        </p>
                        <p className="text-xs text-text-secondary">
                            Estimated GMV opportunity if resolved this week:{" "}
                            <span className="tabular font-medium text-text-primary">$6,200</span>
                        </p>
                    </div>
                    <Button
                        variant="secondary"
                        size="sm"
                        className="shrink-0 self-start sm:self-auto"
                        onClick={() => setActiveDecision(decisionQueue[0])}
                    >
                        Start with the most urgent
                        <ArrowRight className="h-4 w-4" />
                    </Button>
                </SurfaceCard>

                <SurfaceCard
                    padding="md"
                    className="inner-top-highlight flex flex-col gap-4 border-primary/20 bg-primary-soft/30 sm:flex-row sm:items-center sm:justify-between"
                >
                    <div className="flex min-w-0 gap-3">
                        <span className="grid h-10 w-10 shrink-0 place-items-center rounded-lg bg-primary text-primary-foreground">
                            <Workflow className="h-4 w-4" />
                        </span>
                        <div className="min-w-0">
                            <div className="flex flex-wrap items-center gap-2">
                                <p className="text-sm font-semibold text-text-primary">
                                    Production Studio
                                </p>
                                <StatusChip tone="info">Workspace connected</StatusChip>
                                <StatusChip tone="warn">Demo analysis</StatusChip>
                            </div>
                            <p className="mt-1 max-w-2xl text-sm text-text-secondary">
                                Analyze a reference, adapt its Creative DNA, build a campaign brief,
                                and review creator video in one guided workspace.
                            </p>
                        </div>
                    </div>
                    <Button className="shrink-0" onClick={() => navigate({ to: "/production" })}>
                        Open Studio
                        <ArrowRight className="h-4 w-4" />
                    </Button>
                </SurfaceCard>

                {/* Business value — 4 metrics in one row */}
                <section aria-label="Business value">
                    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                        {overviewMetrics.map((m) => (
                            <MetricCard key={m.id} metric={m} />
                        ))}
                    </div>
                </section>

                {/* Needs attention (65%) + Recommended actions (35%) */}
                <div className="grid gap-6 lg:grid-cols-[minmax(0,65fr)_minmax(0,35fr)]">
                    <section className="min-w-0">
                        <div className="mb-3 flex items-center justify-between">
                            <h2 className="text-sm font-semibold uppercase tracking-wide text-text-tertiary">
                                Needs attention
                            </h2>
                            <StatusChip tone="warn">{decisionQueue.length} open</StatusChip>
                        </div>
                        <SurfaceCard padding="none" className="divide-y divide-hairline/50">
                            {decisionQueue.map((item) => (
                                <DecisionBanner
                                    key={item.id}
                                    item={item}
                                    onOpen={() => setActiveDecision(item)}
                                />
                            ))}
                        </SurfaceCard>
                    </section>

                    <section className="min-w-0">
                        <div className="mb-3 flex items-center justify-between">
                            <h2 className="text-sm font-semibold uppercase tracking-wide text-text-tertiary">
                                Recommended actions
                            </h2>
                            <StatusChip tone="info">Scale · Fix · Rehire · Stop</StatusChip>
                        </div>
                        <SurfaceCard padding="none" className="divide-y divide-hairline/50">
                            {visibleRecs.length === 0 ? (
                                <div className="flex flex-col items-center gap-2 px-4 py-8 text-center">
                                    <span className="grid h-10 w-10 place-items-center rounded-full bg-ok-soft text-ok">
                                        <ShieldCheck className="h-5 w-5" />
                                    </span>
                                    <p className="text-sm font-medium text-text-primary">
                                        All caught up
                                    </p>
                                    <p className="text-xs text-text-secondary">
                                        New recommendations appear as performance data arrives.
                                    </p>
                                </div>
                            ) : (
                                visibleRecs.map((rec) => (
                                    <RecommendationRow
                                        key={rec.id}
                                        rec={rec}
                                        onEvidence={() => setEvidenceRec(rec)}
                                        onPrimary={() => runVariants(rec)}
                                    />
                                ))
                            )}
                        </SurfaceCard>
                    </section>
                </div>

                {/* Active campaigns — full width */}
                <section>
                    <div className="mb-3 flex items-end justify-between">
                        <h2 className="text-sm font-semibold uppercase tracking-wide text-text-tertiary">
                            Active campaigns
                        </h2>
                        <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => navigate({ to: "/campaigns" })}
                        >
                            View all
                            <ArrowRight className="h-4 w-4" />
                        </Button>
                    </div>
                    <SurfaceCard padding="none" className="divide-y divide-hairline/50">
                        <div className="hidden grid-cols-[minmax(0,2.4fr)_minmax(0,1fr)_100px_100px_minmax(0,1.4fr)_auto] gap-3 px-4 py-2 text-[10px] font-semibold uppercase tracking-wide text-text-tertiary sm:grid">
                            <span>Campaign</span>
                            <span>Status</span>
                            <span>UGC</span>
                            <span>GMV</span>
                            <span>Next action</span>
                            <span />
                        </div>
                        {campaigns.slice(0, 5).map((c) => (
                            <CampaignRow
                                key={c.id}
                                campaign={c}
                                onClick={() => {
                                    toast("Opening campaign workspace", {
                                        description: `Detailed workspace for “${c.name}” ships in the next phase.`,
                                    });
                                    navigate({ to: "/campaigns" });
                                }}
                            />
                        ))}
                    </SurfaceCard>
                </section>

                {/* Recent activity — secondary */}
                <section aria-label="Recent activity">
                    <div className="mb-3 flex items-center gap-2">
                        <h2 className="text-xs font-semibold uppercase tracking-wide text-text-tertiary">
                            Recent activity
                        </h2>
                        <span className="h-px flex-1 bg-hairline/60" />
                    </div>
                    <ul className="grid gap-x-8 gap-y-1 sm:grid-cols-2">
                        {activities.map((a) => {
                            const Icon = activityIcon[a.kind];
                            return (
                                <li
                                    key={a.id}
                                    className="grid grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-3 py-2"
                                >
                                    <span className="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-surface-soft text-text-secondary">
                                        <Icon className="h-3 w-3" />
                                    </span>
                                    <div className="min-w-0">
                                        <p className="truncate text-xs text-text-primary">
                                            {a.title}
                                        </p>
                                        <p className="truncate text-[11px] text-text-tertiary">
                                            {a.subject}
                                        </p>
                                    </div>
                                    <span className="shrink-0 text-[11px] tabular text-text-tertiary">
                                        <RelativeTime value={a.at} />
                                    </span>
                                </li>
                            );
                        })}
                    </ul>
                </section>
            </div>

            {/* Dialogs */}
            <AnalyzeCreativeDialog open={analyzeOpen} onOpenChange={setAnalyzeOpen} />
            <CreateCampaignDialog open={createOpen} onOpenChange={setCreateOpen} />

            {/* Decision drawer */}
            <RightDrawer
                open={!!activeDecision}
                onOpenChange={(v) => !v && setActiveDecision(null)}
                title={activeDecision?.title ?? ""}
                description={activeDecision?.object}
                footer={
                    activeDecision && (
                        <div className="flex items-center justify-between gap-2">
                            <Button variant="ghost" onClick={() => setActiveDecision(null)}>
                                Dismiss
                            </Button>
                            <Button
                                onClick={() => {
                                    const item = activeDecision;
                                    toast.success("Action queued", {
                                        description: activeDecision.nextAction,
                                        action: {
                                            label: "Undo",
                                            onClick: () => setActiveDecision(item),
                                        },
                                    });
                                    setActiveDecision(null);
                                }}
                            >
                                {activeDecision.action}
                            </Button>
                        </div>
                    )
                }
            >
                {activeDecision && (
                    <div className="flex flex-col gap-5">
                        <div className="flex flex-wrap items-center gap-2">
                            <StatusChip
                                tone={
                                    activeDecision.severity === "destructive"
                                        ? "destructive"
                                        : activeDecision.severity === "warn"
                                          ? "warn"
                                          : activeDecision.severity === "ok"
                                            ? "ok"
                                            : "info"
                                }
                                dot
                            >
                                {activeDecision.urgency}
                            </StatusChip>
                            <StatusChip tone="neutral">
                                Confidence: {activeDecision.confidence}
                            </StatusChip>
                            <StatusChip tone="neutral">{activeDecision.objectType}</StatusChip>
                            <Button
                                size="sm"
                                variant="secondary"
                                onClick={() => {
                                    openDecisionObject(activeDecision);
                                    setActiveDecision(null);
                                }}
                            >
                                Open {activeDecision.objectType.toLowerCase()}
                                <ArrowRight className="h-4 w-4" />
                            </Button>
                        </div>
                        <div>
                            <p className="text-xs font-semibold uppercase tracking-wide text-text-tertiary">
                                Decision
                            </p>
                            <p className="mt-1 text-sm text-text-primary">
                                {activeDecision.description}
                            </p>
                        </div>
                        <div>
                            <p className="text-xs font-semibold uppercase tracking-wide text-text-tertiary">
                                Reason
                            </p>
                            <p className="mt-1 text-sm text-text-secondary">
                                {activeDecision.reason}
                            </p>
                        </div>
                        <div>
                            <p className="text-xs font-semibold uppercase tracking-wide text-text-tertiary">
                                Evidence
                            </p>
                            <ul className="mt-2 flex flex-col gap-2">
                                {activeDecision.evidence.map((e) => (
                                    <li
                                        key={e}
                                        className="rounded-md bg-surface-soft px-3 py-2 text-sm text-text-primary"
                                    >
                                        {e}
                                    </li>
                                ))}
                            </ul>
                        </div>
                        <div>
                            <p className="text-xs font-semibold uppercase tracking-wide text-text-tertiary">
                                Next action
                            </p>
                            <p className="mt-1 text-sm text-text-primary">
                                {activeDecision.nextAction}
                            </p>
                        </div>
                        <div className="rounded-md border border-primary/20 bg-primary-soft/40 p-3">
                            <p className="text-[10px] font-semibold uppercase tracking-wider text-primary">
                                System recommendation
                            </p>
                            <p className="mt-1 text-sm font-medium text-text-primary">
                                {activeDecision.action}
                            </p>
                            <p className="mt-1 text-xs text-text-secondary">
                                {activeDecision.nextAction}
                            </p>
                        </div>
                    </div>
                )}
            </RightDrawer>

            {/* Evidence drawer */}
            <RightDrawer
                open={!!evidenceRec}
                onOpenChange={(v) => !v && setEvidenceRec(null)}
                title={evidenceRec?.title ?? ""}
                description={evidenceRec?.summary}
                footer={
                    evidenceRec && (
                        <div className="flex items-center justify-between gap-2">
                            <Button variant="ghost" onClick={() => setEvidenceRec(null)}>
                                Close
                            </Button>
                            <Button
                                onClick={() => {
                                    const rec = evidenceRec;
                                    setEvidenceRec(null);
                                    if (rec) runVariants(rec);
                                }}
                            >
                                Run this action
                            </Button>
                        </div>
                    )
                }
            >
                {evidenceRec && (
                    <div className="flex flex-col gap-5">
                        <div className="flex flex-wrap gap-2">
                            <StatusChip tone="info">{evidenceRec.kind}</StatusChip>
                            <StatusChip tone="neutral">
                                Confidence: {evidenceRec.confidence}
                            </StatusChip>
                        </div>
                        <div className="rounded-md bg-surface-soft px-3 py-2">
                            <p className="text-[10px] font-semibold uppercase tracking-wider text-text-tertiary">
                                System signal
                            </p>
                            <p className="mt-1 text-xs text-text-secondary">
                                {evidenceRec.metric.label}
                            </p>
                            <p className="tabular text-2xl font-semibold text-text-primary">
                                {evidenceRec.metric.value}
                            </p>
                        </div>
                        <div>
                            <p className="text-xs font-semibold uppercase tracking-wide text-text-tertiary">
                                Why
                            </p>
                            <p className="mt-1 text-sm text-text-secondary">{evidenceRec.reason}</p>
                        </div>
                        <div>
                            <p className="text-xs font-semibold uppercase tracking-wide text-text-tertiary">
                                Evidence
                            </p>
                            <ul className="mt-2 flex flex-col gap-2">
                                {evidenceRec.evidence.map((e) => (
                                    <li
                                        key={e}
                                        className="rounded-md bg-surface-soft px-3 py-2 text-sm text-text-primary"
                                    >
                                        {e}
                                    </li>
                                ))}
                            </ul>
                        </div>
                    </div>
                )}
            </RightDrawer>

            {/* Variants processing dialog */}
            <RightDrawer
                open={!!variantsRec}
                onOpenChange={() => {}}
                title="Creating variants"
                description={variantsRec?.title}
                size="sm"
            >
                <ProcessingStepper steps={variantsSteps} />
            </RightDrawer>
        </AppShell>
    );
}
