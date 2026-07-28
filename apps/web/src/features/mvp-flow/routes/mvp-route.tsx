import { createFileRoute } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
    CheckCircle2,
    Clipboard,
    FileVideo,
    Loader2,
    Play,
    RefreshCw,
    Sparkles,
    Upload,
} from "lucide-react";
import { useMemo, useState } from "react";
import type { ComponentType, ReactNode } from "react";
import { toast } from "sonner";

import { AppShell } from "@/widgets/app-shell/app-shell";
import { apiGet, apiPatch, apiPost } from "@/shared/api/client";
import { getJob, type JobResponse } from "@/shared/api/jobs";
import { uploadAsset, type Asset } from "@/shared/api/uploads";
import { Badge } from "@/shared/ui/badge";
import { Button } from "@/shared/ui/button";
import { Progress } from "@/shared/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/shared/ui/tabs";
import { Textarea } from "@/shared/ui/textarea";
import { cn } from "@/shared/lib/utils";

export const Route = createFileRoute("/mvp")({
    head: () => ({ meta: [{ title: "MVP Flow - Viraldy" }] }),
    component: MvpRoute,
});

type Workspace = { id: string; name: string };
type Product = { id: string; name: string; metadata_json: Record<string, unknown> };
type Board = { id: string; name: string };
type Reference = { id: string; title: string; asset_id: string; status: string };
type Dna = {
    id: string;
    analysis_mode: string;
    confidence: string;
    dna_json: Record<string, unknown>;
};
type DimensionResult = { score: number | string; reason?: string };
type Finding = { message?: string; instruction?: string };
type AdaptationConcept = {
    id: string;
    name: string;
    hook: string;
    test_hypothesis: string;
};
type CreativeDnaView = {
    opening?: { hook_text?: string };
    product?: { first_appearance_ms?: number };
    cta?: { cta_type?: string };
    creator?: { delivery_style?: string };
    narrative?: { angle?: string };
    summary?: {
        what_to_keep?: string[];
        what_to_change?: string[];
        what_not_to_copy?: string[];
        test_hypotheses?: string[];
    };
};
type ScoreRun = {
    id: string;
    status: string;
    structural_score: number;
    action_label: string;
    confidence: string;
    analysis_mode: string;
    dimension_scores_json: Record<string, DimensionResult>;
    blockers_json: Finding[];
    fixes_json: Finding[];
};
type Adaptation = {
    id: string;
    result_json: { concepts: AdaptationConcept[] };
    analysis_mode: string;
};
type CampaignPackVersion = {
    id: string;
    version_number: number;
    brief_json: Record<string, unknown>;
};
type CampaignPack = {
    id: string;
    current_version_id: string | null;
    current_version: CampaignPackVersion | null;
};
type PreflightRun = {
    id: string;
    status: string;
    preflight_score: number;
    structural_score: number;
    brief_alignment_score: number;
    action_label: string;
    analysis_mode: string;
    blockers_json: Finding[];
    fixes_json: Finding[];
    revision_message: string;
};

function MvpRoute() {
    const queryClient = useQueryClient();
    const [quickRunId, setQuickRunId] = useState<string | null>(null);
    const [quickJobId, setQuickJobId] = useState<string | null>(null);
    const [dnaId, setDnaId] = useState<string | null>(null);
    const [dnaJobId, setDnaJobId] = useState<string | null>(null);
    const [adaptationId, setAdaptationId] = useState<string | null>(null);
    const [packId, setPackId] = useState<string | null>(null);
    const [preflightRunId, setPreflightRunId] = useState<string | null>(null);
    const [preflightJobId, setPreflightJobId] = useState<string | null>(null);
    const [uploadProgress, setUploadProgress] = useState(0);
    const [briefDraft, setBriefDraft] = useState("");

    const workspaces = useQuery({
        queryKey: ["workspaces"],
        queryFn: () => apiGet<Workspace[]>("/workspaces"),
    });
    const workspaceId = workspaces.data?.[0]?.id;
    const products = useQuery({
        queryKey: ["products", workspaceId],
        queryFn: () => apiGet<Product[]>(`/workspaces/${workspaceId}/products`),
        enabled: !!workspaceId,
    });
    const assets = useQuery({
        queryKey: ["assets", workspaceId],
        queryFn: () => apiGet<Asset[]>(`/workspaces/${workspaceId}/assets`),
        enabled: !!workspaceId,
    });
    const boards = useQuery({
        queryKey: ["boards", workspaceId],
        queryFn: () => apiGet<Board[]>(`/workspaces/${workspaceId}/reference-boards`),
        enabled: !!workspaceId,
    });
    const references = useQuery({
        queryKey: ["references", workspaceId],
        queryFn: () => apiGet<Reference[]>(`/workspaces/${workspaceId}/references`),
        enabled: !!workspaceId,
    });
    const packs = useQuery({
        queryKey: ["packs", workspaceId],
        queryFn: () => apiGet<CampaignPack[]>(`/workspaces/${workspaceId}/campaign-packs`),
        enabled: !!workspaceId,
    });

    const product = products.data?.[0];
    const reference = references.data?.[0];
    const quickAsset = useMemo(
        () =>
            assets.data?.find(
                (asset) => asset.metadata_json.fixture_id === "viraldy-demo-quick-v1",
            ) ?? assets.data?.[0],
        [assets.data],
    );
    const ugcAsset = useMemo(
        () =>
            assets.data?.find(
                (asset) => asset.metadata_json.fixture_id === "viraldy-demo-ugc-fixable-v1",
            ) ?? assets.data?.[0],
        [assets.data],
    );

    const quickJob = useJob(workspaceId, quickJobId);
    const dnaJob = useJob(workspaceId, dnaJobId);
    const preflightJob = useJob(workspaceId, preflightJobId);
    const quickScore = useQuery({
        queryKey: ["quick-score", workspaceId, quickRunId, quickJob.data?.status],
        queryFn: () => apiGet<ScoreRun>(`/workspaces/${workspaceId}/tiktok-scores/${quickRunId}`),
        enabled: !!workspaceId && !!quickRunId,
    });
    const dna = useQuery({
        queryKey: ["dna", workspaceId, dnaId, dnaJob.data?.status],
        queryFn: () => apiGet<Dna>(`/workspaces/${workspaceId}/creative-dna/${dnaId}`),
        enabled: !!workspaceId && !!dnaId,
    });
    const adaptation = useQuery({
        queryKey: ["adaptation", workspaceId, adaptationId],
        queryFn: () => apiGet<Adaptation>(`/workspaces/${workspaceId}/adaptations/${adaptationId}`),
        enabled: !!workspaceId && !!adaptationId,
    });
    const pack = useQuery({
        queryKey: ["pack", workspaceId, packId],
        queryFn: () => apiGet<CampaignPack>(`/workspaces/${workspaceId}/campaign-packs/${packId}`),
        enabled: !!workspaceId && !!packId,
    });
    const preflight = useQuery({
        queryKey: ["preflight", workspaceId, preflightRunId, preflightJob.data?.status],
        queryFn: () =>
            apiGet<PreflightRun>(`/workspaces/${workspaceId}/preflight-runs/${preflightRunId}`),
        enabled: !!workspaceId && !!preflightRunId,
    });

    const runQuick = useMutation({
        mutationFn: async () => {
            const response = await apiPost<{ score_run: ScoreRun; job: JobResponse }>(
                `/workspaces/${workspaceId}/tiktok-scores`,
                {
                    asset_id: quickAsset?.id,
                    product_id: product?.id ?? null,
                    objective: "generic_structure",
                },
            );
            setQuickRunId(response.score_run.id);
            setQuickJobId(response.job.id);
            return response;
        },
        onSuccess: () => toast.success("Quick scorer queued"),
        onError: (error) =>
            toast.error(error instanceof Error ? error.message : "Quick scorer failed"),
    });

    const analyzeReference = useMutation({
        mutationFn: async () => {
            const response = await apiPost<{ reference: Reference; job: JobResponse }>(
                `/workspaces/${workspaceId}/references/${reference?.id}/analyze`,
            );
            setDnaJobId(response.job.id);
            return response;
        },
        onSuccess: () => toast.success("Reference analysis queued"),
    });

    const loadDnaFromJob = async () => {
        const id = String(dnaJob.data?.output_json?.creative_dna_version_id ?? "");
        if (id) setDnaId(id);
    };

    const createAdaptation = useMutation({
        mutationFn: async () =>
            apiPost<Adaptation>(`/workspaces/${workspaceId}/adaptations`, {
                product_id: product?.id,
                creative_dna_version_id: dnaId,
                objective: "tiktok_shop_affiliate_test",
                target_market: "US",
                target_buyer: {
                    persona: "small apartment renter",
                    pain: "limited counter space",
                    desired_outcome: "faster organization",
                },
                constraints: { avoid: ["exact script copy", "unsupported claims"] },
            }),
        onSuccess: (run) => {
            setAdaptationId(run.id);
            toast.success("Adaptation generated");
        },
    });

    const createPack = useMutation({
        mutationFn: async () =>
            apiPost<CampaignPack>(`/workspaces/${workspaceId}/campaign-packs`, {
                adaptation_run_id: adaptationId,
                concept_id: "concept_1",
            }),
        onSuccess: (created) => {
            setPackId(created.id);
            setBriefDraft(JSON.stringify(created.current_version?.brief_json ?? {}, null, 2));
            queryClient.invalidateQueries({ queryKey: ["packs", workspaceId] });
            toast.success("Campaign Pack created");
        },
    });

    const savePackVersion = useMutation({
        mutationFn: async () =>
            apiPost<CampaignPackVersion>(
                `/workspaces/${workspaceId}/campaign-packs/${packId}/versions`,
                {
                    brief_json: JSON.parse(briefDraft),
                    change_note: "Edited in MVP console",
                },
            ),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["pack", workspaceId, packId] });
            toast.success("New Campaign Pack version saved");
        },
    });

    const runPreflight = useMutation({
        mutationFn: async () => {
            const versionId = pack.data?.current_version_id ?? packs.data?.[0]?.current_version_id;
            const response = await apiPost<{ preflight_run: PreflightRun; job: JobResponse }>(
                `/workspaces/${workspaceId}/preflight-runs`,
                { ugc_asset_id: ugcAsset?.id, campaign_pack_version_id: versionId },
            );
            setPreflightRunId(response.preflight_run.id);
            setPreflightJobId(response.job.id);
            return response;
        },
        onSuccess: () => toast.success("UGC Preflight queued"),
    });

    async function handleUpload(file: File | null) {
        if (!file || !workspaceId) return;
        setUploadProgress(0);
        try {
            await uploadAsset(workspaceId, file, product?.id, setUploadProgress);
            await queryClient.invalidateQueries({ queryKey: ["assets", workspaceId] });
            toast.success("Upload completed");
        } catch (error) {
            toast.error(error instanceof Error ? error.message : "Upload failed");
        }
    }

    return (
        <AppShell>
            <div className="flex flex-col gap-5">
                <header className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                    <div>
                        <h1 className="text-2xl font-semibold tracking-tight text-text-primary">
                            MVP Creative Intelligence Flow
                        </h1>
                        <p className="mt-1 max-w-3xl text-sm text-text-secondary">
                            Fixture and live modes are explicit. Scores are structural readiness
                            signals, not reach, sales, or GMV predictions.
                        </p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                        <ModeBadge
                            mode={
                                quickScore.data?.analysis_mode ??
                                dna.data?.analysis_mode ??
                                "fixture"
                            }
                        />
                        <Badge variant="outline">
                            {workspaces.data?.[0]?.name ?? "No workspace"}
                        </Badge>
                    </div>
                </header>

                <section className="grid gap-3 lg:grid-cols-4">
                    <Summary label="Product" value={product?.name ?? "Seed required"} />
                    <Summary label="Board" value={boards.data?.[0]?.name ?? "Seed required"} />
                    <Summary label="Quick asset" value={assetTitle(quickAsset)} />
                    <Summary label="UGC asset" value={assetTitle(ugcAsset)} />
                </section>

                <section className="rounded-md border border-hairline bg-surface p-4">
                    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                        <div>
                            <h2 className="text-sm font-semibold text-text-primary">Upload path</h2>
                            <p className="text-sm text-text-secondary">
                                Upload uses presigned URL. In fixture mode, only seeded demo assets
                                can be analyzed.
                            </p>
                        </div>
                        <label className="inline-flex cursor-pointer items-center gap-2 rounded-md border border-hairline bg-surface px-3 py-2 text-sm font-medium text-text-primary hover:bg-surface-soft">
                            <Upload className="h-4 w-4" />
                            Upload video
                            <input
                                type="file"
                                accept="video/mp4,video/quicktime"
                                className="hidden"
                                onChange={(event) => handleUpload(event.target.files?.[0] ?? null)}
                            />
                        </label>
                    </div>
                    {uploadProgress > 0 && <Progress className="mt-3" value={uploadProgress} />}
                </section>

                <Tabs defaultValue="quick" className="w-full">
                    <TabsList className="flex h-auto flex-wrap justify-start">
                        <TabsTrigger value="quick">Quick Scorer</TabsTrigger>
                        <TabsTrigger value="dna">Reference DNA</TabsTrigger>
                        <TabsTrigger value="adapt">Adaptation</TabsTrigger>
                        <TabsTrigger value="pack">Campaign Pack</TabsTrigger>
                        <TabsTrigger value="preflight">UGC Preflight</TabsTrigger>
                    </TabsList>

                    <TabsContent value="quick">
                        <ActionPanel title="Quick TikTok Scorer" icon={FileVideo}>
                            <Button
                                onClick={() => runQuick.mutate()}
                                disabled={!workspaceId || !quickAsset || runQuick.isPending}
                            >
                                {runQuick.isPending ? (
                                    <Loader2 className="h-4 w-4 animate-spin" />
                                ) : (
                                    <Play className="h-4 w-4" />
                                )}
                                Run score
                            </Button>
                            <JobBlock job={quickJob.data} />
                            {quickScore.data && <ScoreBlock score={quickScore.data} />}
                        </ActionPanel>
                    </TabsContent>

                    <TabsContent value="dna">
                        <ActionPanel title="Reference Board to Creative DNA" icon={Sparkles}>
                            <div className="flex flex-wrap gap-2">
                                <Button
                                    onClick={() => analyzeReference.mutate()}
                                    disabled={!reference || analyzeReference.isPending}
                                >
                                    <Play className="h-4 w-4" />
                                    Analyze reference
                                </Button>
                                <Button
                                    variant="secondary"
                                    onClick={loadDnaFromJob}
                                    disabled={dnaJob.data?.status !== "completed"}
                                >
                                    <RefreshCw className="h-4 w-4" />
                                    Load DNA
                                </Button>
                            </div>
                            <JobBlock job={dnaJob.data} />
                            {dna.data && <DnaBlock dna={dna.data} />}
                        </ActionPanel>
                    </TabsContent>

                    <TabsContent value="adapt">
                        <ActionPanel title="Product Adaptation" icon={Sparkles}>
                            <Button
                                onClick={() => createAdaptation.mutate()}
                                disabled={!dnaId || !product || createAdaptation.isPending}
                            >
                                <Play className="h-4 w-4" />
                                Generate concepts
                            </Button>
                            {adaptation.data && (
                                <ConceptBlock concepts={adaptation.data.result_json.concepts} />
                            )}
                        </ActionPanel>
                    </TabsContent>

                    <TabsContent value="pack">
                        <ActionPanel title="Campaign Pack Editor" icon={Clipboard}>
                            <div className="flex flex-wrap gap-2">
                                <Button
                                    onClick={() => createPack.mutate()}
                                    disabled={!adaptationId || createPack.isPending}
                                >
                                    <Play className="h-4 w-4" />
                                    Create from concept 1
                                </Button>
                                <Button
                                    variant="secondary"
                                    onClick={() => savePackVersion.mutate()}
                                    disabled={!packId || !briefDraft}
                                >
                                    <CheckCircle2 className="h-4 w-4" />
                                    Save new version
                                </Button>
                            </div>
                            {pack.data?.current_version && (
                                <Textarea
                                    className="min-h-[420px] font-mono text-xs"
                                    value={
                                        briefDraft ||
                                        JSON.stringify(
                                            pack.data.current_version.brief_json,
                                            null,
                                            2,
                                        )
                                    }
                                    onChange={(event) => setBriefDraft(event.target.value)}
                                />
                            )}
                        </ActionPanel>
                    </TabsContent>

                    <TabsContent value="preflight">
                        <ActionPanel title="Brief-Aware UGC Preflight" icon={FileVideo}>
                            <Button
                                onClick={() => runPreflight.mutate()}
                                disabled={
                                    !ugcAsset ||
                                    !(
                                        pack.data?.current_version_id ??
                                        packs.data?.[0]?.current_version_id
                                    ) ||
                                    runPreflight.isPending
                                }
                            >
                                <Play className="h-4 w-4" />
                                Run preflight
                            </Button>
                            <JobBlock job={preflightJob.data} />
                            {preflight.data && <PreflightBlock run={preflight.data} />}
                        </ActionPanel>
                    </TabsContent>
                </Tabs>
            </div>
        </AppShell>
    );
}

function useJob(workspaceId: string | undefined, jobId: string | null) {
    return useQuery({
        queryKey: ["job", workspaceId, jobId],
        queryFn: () => getJob(workspaceId!, jobId!),
        enabled: !!workspaceId && !!jobId,
        refetchInterval: (query) => {
            const status = query.state.data?.status;
            return status && ["completed", "failed", "cancelled"].includes(status) ? false : 1200;
        },
    });
}

function Summary({ label, value }: { label: string; value: string }) {
    return (
        <div className="rounded-md border border-hairline bg-surface p-4">
            <p className="text-xs font-medium uppercase text-text-tertiary">{label}</p>
            <p className="mt-1 truncate text-sm font-semibold text-text-primary">{value}</p>
        </div>
    );
}

function ActionPanel({
    title,
    icon: Icon,
    children,
}: {
    title: string;
    icon: ComponentType<{ className?: string }>;
    children: ReactNode;
}) {
    return (
        <section className="rounded-md border border-hairline bg-surface p-4">
            <div className="mb-4 flex items-center gap-2">
                <Icon className="h-5 w-5 text-primary" />
                <h2 className="text-base font-semibold text-text-primary">{title}</h2>
            </div>
            <div className="flex flex-col gap-4">{children}</div>
        </section>
    );
}

function ModeBadge({ mode }: { mode: string }) {
    return (
        <Badge className={cn(mode === "fixture" ? "bg-warn-soft text-warn" : "bg-ok-soft text-ok")}>
            {mode.toUpperCase()} MODE
        </Badge>
    );
}

function JobBlock({ job }: { job?: JobResponse }) {
    if (!job) return null;
    return (
        <div className="rounded-md border border-hairline bg-surface-soft p-3">
            <div className="flex items-center justify-between gap-3 text-sm">
                <span className="font-medium text-text-primary">{job.job_type}</span>
                <Badge variant={job.status === "failed" ? "destructive" : "secondary"}>
                    {job.status}
                </Badge>
            </div>
            <Progress className="mt-3" value={job.progress} />
            <p className="mt-2 text-xs text-text-secondary">
                Stage: {job.stage ?? "queued"} {job.error_message ? `- ${job.error_message}` : ""}
            </p>
        </div>
    );
}

function ScoreBlock({ score }: { score: ScoreRun }) {
    return (
        <ResultShell
            title={`${score.structural_score} / 100`}
            subtitle={score.action_label}
            mode={score.analysis_mode}
        >
            <DimensionGrid dimensions={score.dimension_scores_json} />
            <Fixes blockers={score.blockers_json} fixes={score.fixes_json} />
            <p className="text-xs text-text-tertiary">
                This is a structural readiness score, not a guarantee of viral reach, sales, or GMV.
            </p>
        </ResultShell>
    );
}

function DnaBlock({ dna }: { dna: Dna }) {
    const data = dna.dna_json as CreativeDnaView;
    return (
        <ResultShell
            title={String(data.narrative?.angle ?? "Creative DNA")}
            subtitle={dna.confidence}
            mode={dna.analysis_mode}
        >
            <DimensionGrid
                dimensions={{
                    Hook: { score: "-", reason: data.opening?.hook_text },
                    Product: {
                        score: "-",
                        reason: `${data.product?.first_appearance_ms}ms first reveal`,
                    },
                    CTA: { score: "-", reason: data.cta?.cta_type },
                    Creator: { score: "-", reason: data.creator?.delivery_style },
                }}
            />
            <ListBlock title="Keep" items={data.summary?.what_to_keep ?? []} />
            <ListBlock title="Change" items={data.summary?.what_to_change ?? []} />
            <ListBlock title="Avoid" items={data.summary?.what_not_to_copy ?? []} />
            <ListBlock title="Hypotheses" items={data.summary?.test_hypotheses ?? []} />
        </ResultShell>
    );
}

function ConceptBlock({ concepts }: { concepts: AdaptationConcept[] }) {
    return (
        <div className="grid gap-3 lg:grid-cols-3">
            {concepts.map((concept) => (
                <article
                    key={concept.id}
                    className="rounded-md border border-hairline bg-surface-soft p-4"
                >
                    <h3 className="font-semibold text-text-primary">{concept.name}</h3>
                    <p className="mt-1 text-sm text-text-secondary">{concept.hook}</p>
                    <p className="mt-3 text-xs text-text-tertiary">{concept.test_hypothesis}</p>
                </article>
            ))}
        </div>
    );
}

function PreflightBlock({ run }: { run: PreflightRun }) {
    return (
        <ResultShell
            title={`${run.preflight_score} / 100`}
            subtitle={run.action_label}
            mode={run.analysis_mode}
        >
            <DimensionGrid
                dimensions={{
                    Structural: {
                        score: run.structural_score,
                        reason: "Reused TikTok structure scorer",
                    },
                    Brief: { score: run.brief_alignment_score, reason: "Campaign Pack alignment" },
                }}
            />
            <Fixes blockers={run.blockers_json} fixes={run.fixes_json} />
            <div className="rounded-md bg-info-soft p-3 text-sm text-text-primary">
                {run.revision_message}
            </div>
            <Button
                variant="secondary"
                size="sm"
                onClick={() => navigator.clipboard.writeText(run.revision_message)}
            >
                <Clipboard className="h-4 w-4" />
                Copy revision message
            </Button>
        </ResultShell>
    );
}

function ResultShell({
    title,
    subtitle,
    mode,
    children,
}: {
    title: string;
    subtitle: string;
    mode: string;
    children: ReactNode;
}) {
    return (
        <div className="rounded-md border border-hairline bg-surface p-4">
            <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
                <div>
                    <p className="text-2xl font-semibold text-text-primary">{title}</p>
                    <p className="text-sm text-text-secondary">{subtitle}</p>
                </div>
                <ModeBadge mode={mode} />
            </div>
            <div className="flex flex-col gap-4">{children}</div>
        </div>
    );
}

function DimensionGrid({ dimensions }: { dimensions: Record<string, DimensionResult> }) {
    return (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {Object.entries(dimensions).map(([key, item]) => (
                <div key={key} className="rounded-md border border-hairline bg-surface-soft p-3">
                    <div className="flex items-center justify-between gap-2">
                        <p className="text-sm font-medium text-text-primary">
                            {key.replaceAll("_", " ")}
                        </p>
                        <span className="text-sm font-semibold text-text-primary">
                            {item.score}
                        </span>
                    </div>
                    <p className="mt-1 text-xs text-text-secondary">{item.reason}</p>
                </div>
            ))}
        </div>
    );
}

function Fixes({ blockers, fixes }: { blockers: Finding[]; fixes: Finding[] }) {
    return (
        <div className="grid gap-3 lg:grid-cols-2">
            <ListBlock title="Blockers" items={blockers.map((item) => item.message)} />
            <ListBlock title="Fixes" items={fixes.map((item) => item.instruction)} />
        </div>
    );
}

function ListBlock({ title, items }: { title: string; items: string[] }) {
    return (
        <div className="rounded-md border border-hairline bg-surface-soft p-3">
            <h3 className="text-sm font-semibold text-text-primary">{title}</h3>
            <ul className="mt-2 space-y-1 text-sm text-text-secondary">
                {items.length ? items.map((item) => <li key={item}>{item}</li>) : <li>None</li>}
            </ul>
        </div>
    );
}

function assetTitle(asset: Asset | undefined) {
    return String(asset?.metadata_json.title ?? asset?.id ?? "Seed required");
}
