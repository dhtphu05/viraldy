import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { AppShell } from "@/widgets/app-shell/app-shell";
import { useAppStore } from "@/app/store/app-store";
import { useMemo, useState } from "react";
import {
    Breadcrumb,
    BreadcrumbItem,
    BreadcrumbLink,
    BreadcrumbList,
    BreadcrumbPage,
    BreadcrumbSeparator,
} from "@/shared/ui/breadcrumb";
import { Button } from "@/shared/ui/button";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from "@/shared/ui/dropdown-menu";
import { AnalysisStatusChip } from "@/features/creative-library/components/analysis-status-chip";
import { MediaPlayer } from "@/features/creative-library/components/media-player";
import {
    DecisionSummary,
    DnaElementSections,
    EvidenceList,
    KcaPanel,
    TranscriptList,
    FailedState,
} from "@/features/creative-library/components/dna-sections";
import { AdaptToProductDialog } from "@/features/creative-library/components/adapt-to-product-dialog";
import { AnalyzeDnaDialog } from "@/features/creative-library/components/analyze-dna-dialog";
import { MoveToBoardDialog } from "@/features/creative-library/components/move-to-board-dialog";
import { AnalysisJobsRunner } from "@/features/creative-library/components/analysis-jobs-runner";
import { seedProducts } from "@/features/products/data/products";
import { EmptyState } from "@/shared/ui/empty-state";
import { SurfaceCard } from "@/shared/ui/surface-card";
import { ProcessingStepper, type Step } from "@/shared/ui/processing-stepper";
import { AnalysisThinkingSkeleton } from "@/shared/ui/analysis-thinking-skeleton";
import {
    ArrowLeft,
    ChevronRight,
    FolderInput,
    Megaphone,
    MoreHorizontal,
    Package,
    Sparkles,
} from "lucide-react";
import { analysisSteps } from "@/features/creative-library/lib/mockAnalysis";
import { scrollElementIntoView } from "@/shared/lib/scroll";
import { toast } from "sonner";

export const Route = createFileRoute("/creative-library/$creativeId")({
    head: ({ params }) => ({
        meta: [{ title: `Creative reference — Viraldy` }],
    }),
    component: CreativeDetailPage,
});

function CreativeDetailPage() {
    const { creativeId } = Route.useParams();
    const creatives = useAppStore((s) => s.creatives);
    const analyses = useAppStore((s) => s.analyses);
    const boards = useAppStore((s) => s.boards);
    const jobs = useAppStore((s) => s.analysisJobs);
    const startAnalysisJob = useAppStore((s) => s.startAnalysisJob);
    const addAdaptationNote = useAppStore((s) => s.addAdaptationNote);
    const adaptationNotes = useAppStore((s) => s.adaptationNotes);
    const campaignDraft = useAppStore((s) => s.campaignDraft);
    const setDraft = useAppStore((s) => s.setDraft);
    const navigate = useNavigate();

    const creative = creatives.find((c) => c.id === creativeId);
    const analysis = creative ? analyses[creative.id] : undefined;
    const job = creative ? jobs[creative.id] : undefined;

    const [t, setT] = useState(0);
    const [activeMarker, setActiveMarker] = useState<string | undefined>();
    const [usefulIds, setUsefulIds] = useState<string[]>([]);
    const [adaptOpen, setAdaptOpen] = useState(false);
    const [analyzeOpen, setAnalyzeOpen] = useState(false);
    const [moveOpen, setMoveOpen] = useState(false);

    const linkedProduct = useMemo(
        () =>
            creative?.linkedProductId
                ? seedProducts.find((p) => p.id === creative.linkedProductId)
                : undefined,
        [creative],
    );
    const boardNames = useMemo(
        () =>
            creative
                ? boards
                      .filter((b) => creative.boardIds.includes(b.id))
                      .map((b) => b.name)
                      .join(", ")
                : "",
        [creative, boards],
    );

    if (!creative) {
        return (
            <AppShell>
                <SurfaceCard padding="lg">
                    <EmptyState
                        title="Creative not found"
                        description="This reference may have been archived or removed."
                        action={
                            <Button asChild variant="secondary" size="sm">
                                <Link to="/creative-library" search={{ import: undefined }}>
                                    <ArrowLeft className="h-4 w-4" />
                                    Back to library
                                </Link>
                            </Button>
                        }
                    />
                </SurfaceCard>
            </AppShell>
        );
    }

    function handleJump(time: number) {
        setT(time);
        if (analysis) {
            const m = analysis.markers.find((mk) => Math.abs(mk.at - time) < 0.6);
            if (m) {
                setActiveMarker(m.id);
                const el = document.getElementById(`marker-evidence-${m.kind}`);
                scrollElementIntoView(el, { block: "nearest" });
            }
        }
    }

    function handleMarkerClick(id: string) {
        setActiveMarker(id);
        const m = analysis?.markers.find((x) => x.id === id);
        if (m) {
            const ev = analysis?.evidence.find(
                (e) => e.timestamp && Math.abs(e.timestamp - m.at) < 1.5,
            );
            if (ev) {
                scrollElementIntoView(document.getElementById(`evidence-${ev.id}`), {
                    block: "nearest",
                });
            }
        }
    }

    function retryAnalysis() {
        startAnalysisJob(creative!.id, analysisSteps.length);
        toast("Retrying analysis");
    }

    function addToCampaign() {
        setDraft({
            referenceCreativeIds: Array.from(
                new Set([...(campaignDraft.referenceCreativeIds ?? []), creative!.id]),
            ),
        });
        toast.success("Creative added to draft", {
            description: "Opening the campaign draft.",
        });
        void navigate({ to: "/campaigns/new" });
    }

    function reviewEvidence() {
        const firstEvidenceId = analysis?.evidence[0]?.id;
        scrollElementIntoView(
            document.getElementById(
                firstEvidenceId ? `evidence-${firstEvidenceId}` : "creative-evidence",
            ),
            { block: "start" },
        );
    }

    const notes = adaptationNotes[creative.id] ?? [];

    // Processing / not-analyzed shells
    const stepper: Step[] = job
        ? analysisSteps.map((s, i) => ({
              key: s.key,
              label: s.label,
              status: i < job.step ? "done" : i === job.step ? "active" : "pending",
          }))
        : [];

    return (
        <AppShell>
            <AnalysisJobsRunner />
            <div className="flex flex-col gap-6">
                {/* Header */}
                <div className="flex flex-col gap-4">
                    <Breadcrumb>
                        <BreadcrumbList>
                            <BreadcrumbItem>
                                <BreadcrumbLink asChild>
                                    <Link to="/creative-library" search={{ import: undefined }}>
                                        Creative Library
                                    </Link>
                                </BreadcrumbLink>
                            </BreadcrumbItem>
                            <BreadcrumbSeparator />
                            <BreadcrumbItem>
                                <BreadcrumbPage className="max-w-[260px] truncate sm:max-w-md">
                                    {creative.title}
                                </BreadcrumbPage>
                            </BreadcrumbItem>
                        </BreadcrumbList>
                    </Breadcrumb>

                    <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-end sm:justify-between sm:gap-4">
                        <div className="min-w-0">
                            <h1 className="break-words text-2xl font-semibold text-text-primary sm:text-[26px]">
                                {creative.title}
                            </h1>
                            <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-text-secondary">
                                <span>{creative.platform}</span>
                                <span>·</span>
                                <span>{creative.brandOrCreator}</span>
                                <span>·</span>
                                <span>{boardNames || "Unassigned"}</span>
                                <AnalysisStatusChip status={creative.analysisStatus} />
                            </div>
                        </div>
                        <div className="flex shrink-0 flex-wrap items-center gap-2">
                            {creative.analysisStatus === "analyzed" ? (
                                <Button onClick={() => setAdaptOpen(true)}>
                                    <Package className="h-4 w-4" />
                                    Adapt to product
                                </Button>
                            ) : (
                                <Button onClick={() => setAnalyzeOpen(true)}>
                                    <Sparkles className="h-4 w-4" />
                                    Analyze Creative DNA
                                </Button>
                            )}
                            <DropdownMenu>
                                <DropdownMenuTrigger asChild>
                                    <Button
                                        variant="secondary"
                                        size="icon"
                                        aria-label="More actions"
                                    >
                                        <MoreHorizontal className="h-4 w-4" />
                                    </Button>
                                </DropdownMenuTrigger>
                                <DropdownMenuContent align="end" className="w-52">
                                    <DropdownMenuItem onSelect={addToCampaign}>
                                        <Megaphone className="h-4 w-4" />
                                        Add to campaign
                                    </DropdownMenuItem>
                                    <DropdownMenuItem onSelect={() => setMoveOpen(true)}>
                                        <FolderInput className="h-4 w-4" />
                                        Move to board
                                    </DropdownMenuItem>
                                    <DropdownMenuItem onSelect={() => setAnalyzeOpen(true)}>
                                        <Sparkles className="h-4 w-4" />
                                        {creative.analysisStatus === "analyzed"
                                            ? "Re-analyze"
                                            : "Analyze Creative DNA"}
                                    </DropdownMenuItem>
                                    <DropdownMenuSeparator />
                                    <DropdownMenuItem asChild>
                                        <Link to="/creative-library" search={{ import: undefined }}>
                                            Back to library
                                        </Link>
                                    </DropdownMenuItem>
                                </DropdownMenuContent>
                            </DropdownMenu>
                        </div>
                    </div>
                </div>

                {/* Layout */}
                <div className="grid min-w-0 gap-6 lg:grid-cols-12">
                    {/* Main */}
                    <div className="flex min-w-0 flex-col gap-4 lg:col-span-7">
                        <MediaPlayer
                            creative={creative}
                            markers={analysis?.markers ?? []}
                            currentTime={t}
                            onTimeChange={setT}
                            activeMarkerId={activeMarker}
                            onMarkerClick={handleMarkerClick}
                        />

                        {creative.analysisStatus === "failed" && (
                            <FailedState onRetry={retryAnalysis} />
                        )}

                        {creative.analysisStatus === "processing" && (
                            <SurfaceCard padding="lg" className="flex flex-col gap-4">
                                <div>
                                    <p className="text-sm font-medium text-text-primary">
                                        Analyzing Creative DNA…
                                    </p>
                                    <p className="mt-0.5 text-xs text-text-secondary">
                                        We'll open the full breakdown when it's ready.
                                    </p>
                                </div>
                                <ProcessingStepper steps={stepper} />
                                <AnalysisThinkingSkeleton
                                    compact
                                    title="Preparing Creative DNA modules"
                                    description="The breakdown will show analyzed moments, evidence, transcript, Keep/Change/Avoid, and adaptation notes."
                                />
                            </SurfaceCard>
                        )}

                        {(creative.analysisStatus === "unanalyzed" ||
                            creative.analysisStatus === "ready") && (
                            <SurfaceCard padding="lg">
                                <div className="grid gap-4 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
                                    <EmptyState
                                        icon={Sparkles}
                                        title="Not analyzed yet"
                                        description="Run Creative DNA analysis to see the hook, product reveal, evidence, and adaptation notes."
                                        action={
                                            <Button size="sm" onClick={() => setAnalyzeOpen(true)}>
                                                <Sparkles className="h-4 w-4" />
                                                Analyze Creative DNA
                                            </Button>
                                        }
                                    />
                                    <AnalysisThinkingSkeleton
                                        compact
                                        title="Modules after analysis"
                                        description="Timeline, transcript, evidence, and product adaptation guidance appear here."
                                    />
                                </div>
                            </SurfaceCard>
                        )}

                        {analysis && creative.analysisStatus === "analyzed" && (
                            <>
                                <DnaElementSections analysis={analysis} onJumpTo={handleJump} />
                                <TranscriptList items={analysis.transcript} onJump={handleJump} />
                            </>
                        )}
                    </div>

                    {/* Right panel */}
                    <div className="flex min-w-0 flex-col gap-4 lg:col-span-5">
                        {analysis && creative.analysisStatus === "analyzed" ? (
                            <>
                                <DecisionSummary
                                    analysis={analysis}
                                    onAdapt={() => setAdaptOpen(true)}
                                    onReviewEvidence={reviewEvidence}
                                    linked={linkedProduct?.name}
                                />
                                <div id="creative-evidence" className="scroll-mt-4">
                                    <EvidenceList
                                        evidence={analysis.evidence}
                                        activeId={
                                            activeMarker
                                                ? analysis.evidence.find((e) => {
                                                      const m = analysis.markers.find(
                                                          (mk) => mk.id === activeMarker,
                                                      );
                                                      return (
                                                          m &&
                                                          e.timestamp &&
                                                          Math.abs(e.timestamp - m.at) < 1.5
                                                      );
                                                  })?.id
                                                : undefined
                                        }
                                        onJump={handleJump}
                                        onMarkUseful={(id) =>
                                            setUsefulIds((prev) =>
                                                prev.includes(id)
                                                    ? prev.filter((x) => x !== id)
                                                    : [...prev, id],
                                            )
                                        }
                                        onAddNote={(e) => {
                                            addAdaptationNote(
                                                creative.id,
                                                `${e.title}: ${e.action}`,
                                            );
                                            toast.success("Added to adaptation notes");
                                        }}
                                        usefulIds={usefulIds}
                                    />
                                </div>
                                <KcaPanel
                                    keep={analysis.keep}
                                    change={analysis.change}
                                    avoid={analysis.avoid}
                                />
                                {notes.length > 0 && (
                                    <SurfaceCard padding="md">
                                        <p className="text-[10px] font-semibold uppercase text-text-tertiary">
                                            Adaptation notes
                                        </p>
                                        <ul className="mt-2 flex flex-col divide-y divide-divider text-sm text-text-primary">
                                            {notes.map((n, i) => (
                                                <li
                                                    key={i}
                                                    className="flex items-start gap-2 py-2.5 text-xs"
                                                >
                                                    <ChevronRight className="mt-0.5 h-3 w-3 shrink-0 text-text-tertiary" />
                                                    <span>{n}</span>
                                                </li>
                                            ))}
                                        </ul>
                                    </SurfaceCard>
                                )}
                            </>
                        ) : (
                            <SurfaceCard padding="lg">
                                <p className="text-[10px] font-semibold uppercase text-text-tertiary">
                                    Intelligence
                                </p>
                                <p className="mt-2 text-sm text-text-secondary">
                                    Decision, evidence, and adaptation notes appear here once
                                    analysis completes.
                                </p>
                            </SurfaceCard>
                        )}
                    </div>
                </div>
            </div>

            {adaptOpen && (
                <AdaptToProductDialog
                    open={adaptOpen}
                    onOpenChange={setAdaptOpen}
                    creativeId={creative.id}
                    creativeTitle={creative.title}
                />
            )}
            <AnalyzeDnaDialog
                open={analyzeOpen}
                onOpenChange={setAnalyzeOpen}
                creativeIds={[creative.id]}
            />
            <MoveToBoardDialog
                open={moveOpen}
                onOpenChange={setMoveOpen}
                creativeId={creative.id}
            />
        </AppShell>
    );
}
