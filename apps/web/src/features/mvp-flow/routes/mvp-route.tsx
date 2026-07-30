import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
    CheckCircle2,
    Clipboard,
    Info,
    FileVideo,
    Loader2,
    Play,
    RefreshCw,
    Sparkles,
    Upload,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import type { ComponentType, ReactNode } from "react";
import { toast } from "sonner";

import { AppShell } from "@/widgets/app-shell/app-shell";
import { apiGet, apiPost, hasConfiguredApiBaseUrl } from "@/shared/api/client";
import { getJob, type JobResponse } from "@/shared/api/jobs";
import { queryKeys } from "@/shared/api/query-keys";
import { getAiReadiness, type AiReadiness } from "@/shared/api/system";
import { uploadAsset, type Asset } from "@/shared/api/uploads";
import { Badge } from "@/shared/ui/badge";
import { Button } from "@/shared/ui/button";
import { Progress } from "@/shared/ui/progress";
import { StatusChip } from "@/shared/ui/status-chip";
import { Textarea } from "@/shared/ui/textarea";
import { Skeleton } from "@/shared/ui/skeleton";
import { cn } from "@/shared/lib/utils";
import { DisabledActionHint } from "@/shared/ui/disabled-action-hint";
import { formatPercentScore, formatSystemValue, humanizeLabel } from "@/shared/lib/display";
import { AnalysisThinkingSkeleton } from "@/shared/ui/analysis-thinking-skeleton";
import { AnalysisTimelineSvg } from "@/shared/ui/analysis-timeline-svg";

export const Route = createFileRoute("/production")({
    head: () => ({ meta: [{ title: "Production Studio - Viraldy" }] }),
    validateSearch: (search: Record<string, unknown>): MvpSearch => ({
        quickRunId: optionalSearchString(search.quickRunId),
        quickJobId: optionalSearchString(search.quickJobId),
        dnaId: optionalSearchString(search.dnaId),
        dnaJobId: optionalSearchString(search.dnaJobId),
        adaptationId: optionalSearchString(search.adaptationId),
        packId: optionalSearchString(search.packId),
        preflightRunId: optionalSearchString(search.preflightRunId),
        preflightJobId: optionalSearchString(search.preflightJobId),
    }),
    component: ProductionRunRoute,
});

type MvpSearch = {
    quickRunId?: string;
    quickJobId?: string;
    dnaId?: string;
    dnaJobId?: string;
    adaptationId?: string;
    packId?: string;
    preflightRunId?: string;
    preflightJobId?: string;
};

type Workspace = { id: string; name: string };
type Product = { id: string; name: string; metadata_json: Record<string, unknown> };
type Board = { id: string; name: string };
type Reference = { id: string; title: string; asset_id: string; status: string };
type Dna = {
    id: string;
    analysis_mode: string;
    confidence: string;
    schema_version: string;
    dna_json: CreativeDnaV1;
};
type ObservedValue = {
    value: unknown;
    confidence?: number;
    evidence_ids?: string[];
    status?: "observed" | "inferred" | "unknown" | "not_present";
};
type CreativeDnaSection = Record<string, ObservedValue | unknown>;
type CreativeDnaV1 = {
    schema_version?: string;
    opening?: CreativeDnaSection;
    product?: CreativeDnaSection;
    narrative?: CreativeDnaSection;
    demo?: CreativeDnaSection;
    proof?: CreativeDnaSection;
    creator?: CreativeDnaSection;
    editing?: CreativeDnaSection;
    offer?: CreativeDnaSection;
    cta?: CreativeDnaSection;
    platform?: CreativeDnaSection;
    claims?: unknown[];
    risks?: unknown[];
    reusable_mechanisms?: unknown[];
    uncertainties?: string[];
    completeness?: Record<string, boolean>;
    overall_confidence?: string;
};
type ScoreSignal = {
    code: string;
    value: unknown;
    contribution: number;
    confidence: number;
    evidence_ids: string[];
};
type DimensionResult = {
    score: number | string;
    confidence?: string;
    reason?: string;
    signals?: ScoreSignal[];
    missing_signals?: string[];
    evidence_ids?: string[];
};
type Finding = {
    code?: string;
    message?: string;
    instruction?: string;
    why?: string;
    evidence_ids?: string[];
};
type AdaptationConcept = {
    id: string;
    name: string;
    strategic_axis?: string;
    angle?: string;
    buyer_pain?: string;
    desired_outcome?: string;
    creator_persona?: string;
    delivery_style?: string;
    hook_options?: string[];
    demo_mechanism?: string;
    proof_mechanism?: string;
    must_show?: string[];
    test_hypothesis: string;
};
type ScoreRun = {
    id: string;
    status: string;
    schema_version: string;
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
    schema_version: string;
    result_json: { schema_version?: string; concepts: AdaptationConcept[]; guidance?: unknown[] };
    analysis_mode: string;
};
type CampaignPackBrief = {
    schema_version?: string;
    product_snapshot?: Record<string, unknown>;
    objective?: Record<string, unknown>;
    audience?: Record<string, unknown>;
    angle?: Record<string, unknown>;
    must_show?: unknown[];
    cta?: Record<string, unknown>;
    claim_guardrails?: Record<string, unknown>;
};
type CampaignPackVersion = {
    id: string;
    campaign_pack_id: string;
    version_number: number;
    brief_json: CampaignPackBrief;
    brief_schema_version: string;
    product_snapshot_json: Record<string, unknown> | null;
    compiled_requirements_json: Record<string, unknown>;
    requirements_schema_version: string | null;
    change_note: string | null;
    source_adaptation_run_id: string | null;
    source_model_run_id: string | null;
    source_prompt_version: string | null;
    source_schema_version: string | null;
    created_at: string;
};
type CampaignPack = {
    id: string;
    current_version_id: string | null;
    current_version: CampaignPackVersion | null;
};
type PreflightRun = {
    id: string;
    status: string;
    schema_version: string;
    preflight_score: number;
    structural_score: number;
    brief_alignment_score: number;
    action_label: string;
    analysis_mode: string;
    brief_alignment_json: {
        schema_version?: string;
        confidence?: string;
        coverage?: Record<string, unknown>;
        requirements?: RequirementEvaluation[];
    };
    blockers_json: Finding[];
    fixes_json: Finding[];
    revision_message: string;
    requirements_snapshot_json?: Record<string, unknown> | null;
};
type RequirementEvaluation = {
    requirement_id: string;
    status: string;
    score: number;
    confidence: string;
    reason: string;
    expected: Record<string, unknown>;
    observed: Record<string, unknown>;
    evidence_ids: string[];
};
type UploadState = {
    status: "idle" | "uploading" | "completed" | "failed";
    progress: number;
    filename?: string;
    message?: string;
};

const scoreMarkers = [
    { id: "score-hook", at: 1.5, label: "Hook read", kind: "hook" },
    { id: "score-reveal", at: 4.5, label: "Product reveal", kind: "reveal" },
    { id: "score-demo", at: 10, label: "Demo clarity", kind: "demo" },
    { id: "score-proof", at: 17, label: "Proof check", kind: "proof" },
    { id: "score-cta", at: 25, label: "CTA check", kind: "cta" },
];

const dnaMarkers = [
    { id: "dna-opening", at: 1, label: "Opening hook", kind: "hook" },
    { id: "dna-product", at: 5, label: "Product role", kind: "reveal" },
    { id: "dna-narrative", at: 11, label: "Story arc", kind: "demo" },
    { id: "dna-proof", at: 18, label: "Proof moment", kind: "proof" },
    { id: "dna-cta", at: 26, label: "CTA pattern", kind: "cta" },
];

const preflightMarkers = [
    { id: "preflight-hook", at: 2, label: "Brief hook", kind: "hook" },
    { id: "preflight-product", at: 7, label: "Must-show product", kind: "reveal" },
    { id: "preflight-demo", at: 13, label: "Demo requirement", kind: "demo" },
    { id: "preflight-risk", at: 20, label: "Claim risk", kind: "risk" },
    { id: "preflight-cta", at: 27, label: "CTA fit", kind: "cta" },
];

function optionalSearchString(value: unknown) {
    return typeof value === "string" && value.length > 0 ? value : undefined;
}

function compactSearch(search: MvpSearch): MvpSearch {
    return Object.fromEntries(
        Object.entries(search).filter(([, value]) => value !== undefined && value !== ""),
    ) as MvpSearch;
}

function ProductionRunRoute() {
    const queryClient = useQueryClient();
    const search = Route.useSearch();
    const navigate = useNavigate();
    const quickRunId = search.quickRunId ?? null;
    const quickJobId = search.quickJobId ?? null;
    const dnaId = search.dnaId ?? null;
    const dnaJobId = search.dnaJobId ?? null;
    const adaptationId = search.adaptationId ?? null;
    const packId = search.packId ?? null;
    const preflightRunId = search.preflightRunId ?? null;
    const preflightJobId = search.preflightJobId ?? null;
    const [uploadState, setUploadState] = useState<UploadState>({
        status: "idle",
        progress: 0,
    });
    const [briefDraft, setBriefDraft] = useState("");
    const [draftVersionId, setDraftVersionId] = useState<string | null>(null);
    const backendConfigured = hasConfiguredApiBaseUrl;

    const updateWorkflowSearch = (updates: Partial<MvpSearch>) => {
        void navigate({
            to: "/production",
            replace: true,
            search: compactSearch({ ...search, ...updates }),
        });
    };

    const aiReadiness = useQuery({
        queryKey: queryKeys.system.aiReadiness,
        queryFn: getAiReadiness,
        enabled: backendConfigured,
    });
    const workspaces = useQuery({
        queryKey: queryKeys.workspaces.list,
        queryFn: () => apiGet<Workspace[]>("/workspaces"),
        enabled: backendConfigured,
    });
    const workspaceId = workspaces.data?.[0]?.id;
    const products = useQuery({
        queryKey: queryKeys.products.list(workspaceId),
        queryFn: () => apiGet<Product[]>(`/workspaces/${workspaceId}/products`),
        enabled: !!workspaceId,
    });
    const assets = useQuery({
        queryKey: queryKeys.assets.list(workspaceId),
        queryFn: () => apiGet<Asset[]>(`/workspaces/${workspaceId}/assets`),
        enabled: !!workspaceId,
    });
    const boards = useQuery({
        queryKey: queryKeys.referenceBoards.list(workspaceId),
        queryFn: () => apiGet<Board[]>(`/workspaces/${workspaceId}/reference-boards`),
        enabled: !!workspaceId,
    });
    const references = useQuery({
        queryKey: queryKeys.references.list(workspaceId),
        queryFn: () => apiGet<Reference[]>(`/workspaces/${workspaceId}/references`),
        enabled: !!workspaceId,
    });
    const packs = useQuery({
        queryKey: queryKeys.campaignPacks.list(workspaceId),
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
        queryKey: [
            ...queryKeys.tiktokScores.detail(workspaceId, quickRunId),
            quickJob.data?.status,
        ],
        queryFn: () => apiGet<ScoreRun>(`/workspaces/${workspaceId}/tiktok-scores/${quickRunId}`),
        enabled: !!workspaceId && !!quickRunId,
    });
    const dna = useQuery({
        queryKey: [...queryKeys.creativeDna.detail(workspaceId, dnaId), dnaJob.data?.status],
        queryFn: () => apiGet<Dna>(`/workspaces/${workspaceId}/creative-dna/${dnaId}`),
        enabled: !!workspaceId && !!dnaId,
    });
    const adaptation = useQuery({
        queryKey: queryKeys.adaptations.detail(workspaceId, adaptationId),
        queryFn: () => apiGet<Adaptation>(`/workspaces/${workspaceId}/adaptations/${adaptationId}`),
        enabled: !!workspaceId && !!adaptationId,
    });
    const pack = useQuery({
        queryKey: queryKeys.campaignPacks.detail(workspaceId, packId),
        queryFn: () => apiGet<CampaignPack>(`/workspaces/${workspaceId}/campaign-packs/${packId}`),
        enabled: !!workspaceId && !!packId,
    });
    const packVersions = useQuery({
        queryKey: queryKeys.campaignPacks.versions(workspaceId, packId),
        queryFn: () =>
            apiGet<CampaignPackVersion[]>(
                `/workspaces/${workspaceId}/campaign-packs/${packId}/versions`,
            ),
        enabled: !!workspaceId && !!packId,
    });
    const preflight = useQuery({
        queryKey: [
            ...queryKeys.preflightRuns.detail(workspaceId, preflightRunId),
            preflightJob.data?.status,
        ],
        queryFn: () =>
            apiGet<PreflightRun>(`/workspaces/${workspaceId}/preflight-runs/${preflightRunId}`),
        enabled: !!workspaceId && !!preflightRunId,
    });

    useEffect(() => {
        const version = pack.data?.current_version;
        if (!version || draftVersionId === version.id) return;
        setBriefDraft(JSON.stringify(version.brief_json, null, 2));
        setDraftVersionId(version.id);
    }, [draftVersionId, pack.data?.current_version]);

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
            updateWorkflowSearch({
                quickRunId: response.score_run.id,
                quickJobId: response.job.id,
            });
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
            updateWorkflowSearch({ dnaId: undefined, dnaJobId: response.job.id });
            return response;
        },
        onSuccess: () => toast.success("Reference analysis queued"),
    });

    const loadDnaFromJob = async () => {
        const id = String(dnaJob.data?.output_json?.creative_dna_version_id ?? "");
        if (id) updateWorkflowSearch({ dnaId: id });
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
                constraints: {
                    max_duration_seconds: 30,
                    must_avoid: ["exact script copy", "unsupported claims"],
                    channel_constraints: ["TikTok Shop vertical UGC"],
                },
            }),
        onSuccess: (run) => {
            updateWorkflowSearch({ adaptationId: run.id });
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
            updateWorkflowSearch({ packId: created.id });
            setBriefDraft(JSON.stringify(created.current_version?.brief_json ?? {}, null, 2));
            setDraftVersionId(created.current_version?.id ?? null);
            queryClient.invalidateQueries({
                queryKey: queryKeys.campaignPacks.list(workspaceId),
            });
            toast.success("Campaign Pack created");
        },
    });

    const savePackVersion = useMutation({
        mutationFn: async () => {
            const brief = parseCampaignBriefDraft(briefDraft);
            return apiPost<CampaignPackVersion>(
                `/workspaces/${workspaceId}/campaign-packs/${packId}/versions`,
                {
                    brief,
                    change_note: "Edited in Production Studio",
                },
            );
        },
        onSuccess: () => {
            queryClient.invalidateQueries({
                queryKey: queryKeys.campaignPacks.detail(workspaceId, packId),
            });
            queryClient.invalidateQueries({
                queryKey: queryKeys.campaignPacks.versions(workspaceId, packId),
            });
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
            updateWorkflowSearch({
                preflightRunId: response.preflight_run.id,
                preflightJobId: response.job.id,
            });
            return response;
        },
        onSuccess: () => toast.success("UGC Preflight queued"),
    });

    const quickReason = disabledReason([
        [!workspaceId, "Connect a workspace before scoring a reference."],
        [!quickAsset, "Add a reference video before scoring."],
        [runQuick.isPending, "Reference scoring is already running."],
    ]);
    const referenceReason = disabledReason([
        [!reference, "Add a video to the reference board first."],
        [analyzeReference.isPending, "Reference analysis is already queued."],
    ]);
    const loadDnaReason = disabledReason([
        [
            dnaJob.data?.status !== "completed",
            "Finish reference analysis before loading Creative DNA.",
        ],
    ]);
    const adaptationReason = disabledReason([
        [!dnaId, "Load Creative DNA before generating product concepts."],
        [!product, "Select a product before adapting the concept."],
        [createAdaptation.isPending, "Concept generation is already running."],
    ]);
    const createPackReason = disabledReason([
        [!adaptationId, "Generate at least one concept before creating the brief."],
        [createPack.isPending, "Campaign brief creation is already running."],
    ]);
    const savePackReason = disabledReason([
        [!packId, "Create a campaign brief before saving a new version."],
        [!briefDraft, "Brief JSON is empty."],
    ]);
    const preflightReason = disabledReason([
        [!ugcAsset, "Add a creator video before review."],
        [
            !(pack.data?.current_version_id ?? packs.data?.[0]?.current_version_id),
            "Create or load a campaign brief before reviewing UGC.",
        ],
        [runPreflight.isPending, "Creator video review is already running."],
    ]);
    const workflowLoading =
        backendConfigured &&
        (aiReadiness.isLoading ||
            workspaces.isLoading ||
            products.isLoading ||
            assets.isLoading ||
            boards.isLoading ||
            references.isLoading);

    async function handleUpload(file: File | null) {
        if (!file || !workspaceId) return;
        setUploadState({ status: "uploading", progress: 0, filename: file.name });
        try {
            await uploadAsset(workspaceId, file, product?.id, (progress) =>
                setUploadState({ status: "uploading", progress, filename: file.name }),
            );
            setUploadState({ status: "completed", progress: 100, filename: file.name });
            await queryClient.invalidateQueries({ queryKey: queryKeys.assets.list(workspaceId) });
            toast.success("Upload completed");
        } catch (error) {
            setUploadState({
                status: "failed",
                progress: 0,
                filename: file.name,
                message: error instanceof Error ? error.message : "Upload failed",
            });
            toast.error(error instanceof Error ? error.message : "Upload failed");
        }
    }

    return (
        <AppShell>
            <div className="flex flex-col gap-5">
                <header className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                    <div>
                        <h1 className="text-2xl font-semibold tracking-tight text-text-primary">
                            Production Studio
                        </h1>
                        <p className="mt-1 max-w-3xl text-sm text-text-secondary">
                            Move from reference analysis to campaign brief and creator review in one
                            guided workflow. Demo analysis is clearly labeled until your AI provider
                            is connected.
                        </p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                        <ModeBadge
                            mode={
                                quickScore.data?.analysis_mode ??
                                dna.data?.analysis_mode ??
                                adaptation.data?.analysis_mode ??
                                preflight.data?.analysis_mode ??
                                aiReadiness.data?.mode ??
                                "fixture"
                            }
                        />
                        <ProviderBadge readiness={aiReadiness.data} />
                        <Badge variant="outline">
                            {workspaces.data?.[0]?.name ?? "Workspace unavailable"}
                        </Badge>
                    </div>
                </header>

                <RuntimeState
                    backendConfigured={backendConfigured}
                    loading={workflowLoading}
                    error={
                        backendConfigured
                            ? (aiReadiness.error ??
                              workspaces.error ??
                              products.error ??
                              assets.error ??
                              boards.error ??
                              references.error ??
                              null)
                            : null
                    }
                    readiness={aiReadiness.data}
                />

                <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                    <Summary
                        label="Product"
                        value={
                            product?.name ??
                            (workspaceId ? "No product selected" : "Waiting for workspace")
                        }
                        loading={workflowLoading}
                    />
                    <Summary
                        label="Reference board"
                        value={
                            boards.data?.[0]?.name ??
                            (workspaceId ? "No board selected" : "Waiting for workspace")
                        }
                        loading={workflowLoading}
                    />
                    <Summary
                        label="Reference video"
                        value={assetTitle(
                            quickAsset,
                            workspaceId ? "No video selected" : "Waiting for workspace",
                        )}
                        loading={workflowLoading}
                    />
                    <Summary
                        label="Creator video"
                        value={assetTitle(
                            ugcAsset,
                            workspaceId ? "No video selected" : "Waiting for workspace",
                        )}
                        loading={workflowLoading}
                    />
                </section>

                <WorkflowProgress
                    steps={[
                        {
                            label: "Score reference",
                            state: workflowState(!!quickRunId, quickJob.data),
                            detail: quickScore.data?.action_label
                                ? humanizeLabel(quickScore.data.action_label)
                                : "Check structure",
                        },
                        {
                            label: "Extract Creative DNA",
                            state: workflowState(!!dnaId, dnaJob.data),
                            detail: dna.data?.confidence ?? "Find reusable patterns",
                        },
                        {
                            label: "Adapt to product",
                            state: adaptationId ? "done" : "idle",
                            detail: adaptation.data
                                ? "Concepts ready"
                                : "Generate product concepts",
                        },
                        {
                            label: "Build campaign brief",
                            state: packId ? "done" : "idle",
                            detail: pack.data?.current_version
                                ? "Brief ready to edit"
                                : "Prepare creator guidance",
                        },
                        {
                            label: "Review creator video",
                            state: workflowState(!!preflightRunId, preflightJob.data),
                            detail: preflight.data?.action_label
                                ? humanizeLabel(preflight.data.action_label)
                                : "Check brief alignment",
                        },
                    ]}
                />

                <section className="rounded-md border border-hairline bg-surface p-4">
                    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                        <div>
                            <h2 className="text-sm font-semibold text-text-primary">Add media</h2>
                            <p className="text-sm text-text-secondary">
                                Upload a reference or creator video. Demo mode can analyze the
                                included samples.
                            </p>
                        </div>
                        <label
                            className={cn(
                                "inline-flex shrink-0 items-center gap-2 whitespace-nowrap rounded-md border border-hairline bg-surface px-3 py-2 text-sm font-medium text-text-primary hover:bg-surface-soft",
                                workspaceId
                                    ? "cursor-pointer"
                                    : "cursor-not-allowed opacity-60 hover:bg-surface",
                            )}
                        >
                            <Upload className="h-4 w-4" />
                            Upload video
                            <input
                                type="file"
                                aria-label="Upload video"
                                accept="video/mp4,video/quicktime"
                                className="hidden"
                                disabled={!workspaceId}
                                onChange={(event) => handleUpload(event.target.files?.[0] ?? null)}
                            />
                        </label>
                    </div>
                    {uploadState.status !== "idle" && (
                        <div className="mt-3" role="status" aria-live="polite">
                            <Progress value={uploadState.progress} />
                            <p className="mt-2 text-xs text-text-secondary">
                                Upload {humanizeLabel(uploadState.status)}
                                {uploadState.filename ? `: ${uploadState.filename}` : ""}
                                {uploadState.message ? ` - ${uploadState.message}` : ""}
                            </p>
                        </div>
                    )}
                </section>

                <div className="grid gap-5 xl:grid-cols-[240px_minmax(0,1fr)] xl:items-start">
                    <ProductionRunRail
                        steps={[
                            {
                                id: "quick-score",
                                label: "Score reference",
                                state: workflowState(!!quickRunId, quickJob.data),
                            },
                            {
                                id: "creative-dna",
                                label: "Extract Creative DNA",
                                state: workflowState(!!dnaId, dnaJob.data),
                            },
                            {
                                id: "product-adaptation",
                                label: "Adapt to product",
                                state: adaptationId ? "done" : "idle",
                            },
                            {
                                id: "campaign-brief",
                                label: "Build campaign brief",
                                state: packId ? "done" : "idle",
                            },
                            {
                                id: "ugc-preflight",
                                label: "Review creator video",
                                state: workflowState(!!preflightRunId, preflightJob.data),
                            },
                        ]}
                    />
                    <div className="flex min-w-0 flex-col gap-5">
                        <ActionPanel
                            id="quick-score"
                            eyebrow="Step 1"
                            title="Score reference video"
                            summary="Check whether the hook, proof, pacing, and CTA are strong enough to reuse."
                            icon={FileVideo}
                        >
                            <DisabledActionHint reason={quickReason}>
                                <Button onClick={() => runQuick.mutate()} disabled={!!quickReason}>
                                    {runQuick.isPending ? (
                                        <Loader2 className="h-4 w-4 animate-spin" />
                                    ) : (
                                        <Play className="h-4 w-4" />
                                    )}
                                    Score reference
                                </Button>
                            </DisabledActionHint>
                            <JobBlock job={quickJob.data} />
                            {quickScore.data && <ScoreBlock score={quickScore.data} />}
                        </ActionPanel>

                        <ActionPanel
                            id="creative-dna"
                            eyebrow="Step 2"
                            title="Extract Creative DNA"
                            summary="Extract reusable hooks, proof, pacing, and creator mechanics."
                            icon={Sparkles}
                        >
                            <div className="grid gap-3 sm:grid-cols-2">
                                <DisabledActionHint reason={referenceReason} className="min-w-0">
                                    <Button
                                        onClick={() => analyzeReference.mutate()}
                                        disabled={!!referenceReason}
                                    >
                                        <Play className="h-4 w-4" />
                                        Analyze reference
                                    </Button>
                                </DisabledActionHint>
                                <DisabledActionHint reason={loadDnaReason} className="min-w-0">
                                    <Button
                                        variant="secondary"
                                        onClick={loadDnaFromJob}
                                        disabled={!!loadDnaReason}
                                    >
                                        <RefreshCw className="h-4 w-4" />
                                        Load results
                                    </Button>
                                </DisabledActionHint>
                            </div>
                            <JobBlock job={dnaJob.data} />
                            {dna.data && <DnaBlock dna={dna.data} />}
                        </ActionPanel>

                        <ActionPanel
                            id="product-adaptation"
                            eyebrow="Step 3"
                            title="Adapt concept to product"
                            summary="Turn reference DNA into product-specific creative concepts."
                            icon={Sparkles}
                        >
                            <DisabledActionHint reason={adaptationReason}>
                                <Button
                                    onClick={() => createAdaptation.mutate()}
                                    disabled={!!adaptationReason}
                                >
                                    <Play className="h-4 w-4" />
                                    Generate concepts
                                </Button>
                            </DisabledActionHint>
                            {adaptation.data && (
                                <ConceptBlock concepts={adaptation.data.result_json.concepts} />
                            )}
                        </ActionPanel>

                        <ActionPanel
                            id="campaign-brief"
                            eyebrow="Step 4"
                            title="Build campaign brief"
                            summary="Turn the selected concept into clear, editable guidance for creators."
                            icon={Clipboard}
                        >
                            <div className="grid gap-3 sm:grid-cols-2">
                                <DisabledActionHint reason={createPackReason} className="min-w-0">
                                    <Button
                                        onClick={() => createPack.mutate()}
                                        disabled={!!createPackReason}
                                    >
                                        <Play className="h-4 w-4" />
                                        Create brief
                                    </Button>
                                </DisabledActionHint>
                                <DisabledActionHint reason={savePackReason} className="min-w-0">
                                    <Button
                                        variant="secondary"
                                        onClick={() => savePackVersion.mutate()}
                                        disabled={!!savePackReason}
                                    >
                                        <CheckCircle2 className="h-4 w-4" />
                                        Save version
                                    </Button>
                                </DisabledActionHint>
                            </div>
                            {pack.data?.current_version && (
                                <>
                                    <CampaignBriefPreview
                                        brief={pack.data.current_version.brief_json}
                                    />
                                    <details className="rounded-md border border-hairline bg-surface-soft p-3">
                                        <summary className="cursor-pointer text-sm font-medium text-text-primary">
                                            Advanced brief JSON
                                        </summary>
                                        <Textarea
                                            aria-label="Campaign brief JSON"
                                            className="mt-3 min-h-[300px] font-mono text-xs"
                                            value={briefDraft}
                                            onChange={(event) => setBriefDraft(event.target.value)}
                                        />
                                    </details>
                                </>
                            )}
                            <VersionHistory
                                versions={packVersions.data ?? []}
                                isLoading={packVersions.isLoading}
                            />
                        </ActionPanel>

                        <ActionPanel
                            id="ugc-preflight"
                            eyebrow="Step 5"
                            title="Review creator video"
                            summary="Compare the creator asset against the campaign brief before approval."
                            icon={FileVideo}
                        >
                            <DisabledActionHint reason={preflightReason}>
                                <Button
                                    onClick={() => runPreflight.mutate()}
                                    disabled={!!preflightReason}
                                >
                                    <Play className="h-4 w-4" />
                                    Run UGC review
                                </Button>
                            </DisabledActionHint>
                            <JobBlock job={preflightJob.data} />
                            {preflight.data && <PreflightBlock run={preflight.data} />}
                        </ActionPanel>
                    </div>
                </div>
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

function disabledReason(entries: Array<[boolean, string]>) {
    return entries.find(([blocked]) => blocked)?.[1] ?? null;
}

function workflowState(done: boolean, job?: JobResponse): "done" | "active" | "failed" | "idle" {
    if (done) return "done";
    if (!job) return "idle";
    if (job.status === "failed" || job.status === "cancelled") return "failed";
    if (["queued", "running", "retrying"].includes(job.status)) return "active";
    return "idle";
}

function requirementTone(status: string) {
    const normalized = status.toLowerCase();
    if (normalized.includes("pass") || normalized.includes("met") || normalized.includes("ok")) {
        return "ok" as const;
    }
    if (normalized.includes("fail") || normalized.includes("missing")) {
        return "destructive" as const;
    }
    if (normalized.includes("partial") || normalized.includes("warn")) return "warn" as const;
    return "info" as const;
}

function WorkflowProgress({
    steps,
}: {
    steps: Array<{
        label: string;
        detail: string;
        state: "done" | "active" | "failed" | "idle";
    }>;
}) {
    return (
        <section
            aria-label="Production Studio progress"
            className="rounded-md border border-hairline bg-surface p-3"
        >
            <ol className="grid gap-2 sm:grid-cols-2 xl:grid-cols-5">
                {steps.map((step, index) => (
                    <li
                        key={step.label}
                        className={cn(
                            "min-w-0 rounded-md border px-3 py-2 sm:last:col-span-2 xl:last:col-span-1",
                            step.state === "done" && "border-ok/30 bg-ok-soft",
                            step.state === "active" && "border-primary/30 bg-primary-soft",
                            step.state === "failed" && "border-destructive/30 bg-destructive-soft",
                            step.state === "idle" && "border-hairline bg-surface-soft",
                        )}
                    >
                        <div className="flex items-center gap-2">
                            <span
                                className={cn(
                                    "grid h-5 w-5 shrink-0 place-items-center rounded-full text-[10px] font-semibold tabular",
                                    step.state === "done" && "bg-ok text-ok-foreground",
                                    step.state === "active" && "bg-primary text-primary-foreground",
                                    step.state === "failed" &&
                                        "bg-destructive text-destructive-foreground",
                                    step.state === "idle" && "bg-surface-muted text-text-tertiary",
                                )}
                            >
                                {index + 1}
                            </span>
                            <p className="min-w-0 break-words text-sm font-medium leading-snug text-text-primary">
                                {step.label}
                            </p>
                        </div>
                        <p className="mt-1 break-words text-xs leading-snug text-text-secondary">
                            {step.detail}
                        </p>
                    </li>
                ))}
            </ol>
        </section>
    );
}

function ProductionRunRail({
    steps,
}: {
    steps: Array<{
        id: string;
        label: string;
        state: "done" | "active" | "failed" | "idle";
    }>;
}) {
    const tone = {
        done: "ok",
        active: "info",
        failed: "destructive",
        idle: "neutral",
    } as const;
    return (
        <aside className="rounded-md border border-hairline bg-surface p-3 xl:sticky xl:top-20">
            <div className="mb-3">
                <p className="text-sm font-semibold text-text-primary">Workflow steps</p>
                <p className="mt-0.5 text-xs text-text-secondary">
                    Complete each step in order. Results stay open for review.
                </p>
            </div>
            <ol className="grid gap-2 sm:grid-cols-2 xl:flex xl:flex-col">
                {steps.map((step, index) => (
                    <li key={step.label} className="min-w-0 sm:last:col-span-2 xl:last:col-span-1">
                        <a
                            href={`#${step.id}`}
                            className="grid grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-2 rounded-md px-2 py-2 text-sm transition-colors hover:bg-surface-soft focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                        >
                            <span
                                className={cn(
                                    "grid h-6 w-6 place-items-center rounded-full text-[11px] font-semibold",
                                    step.state === "done" && "bg-ok text-ok-foreground",
                                    step.state === "active" && "bg-primary text-primary-foreground",
                                    step.state === "failed" &&
                                        "bg-destructive text-destructive-foreground",
                                    step.state === "idle" && "bg-surface-muted text-text-tertiary",
                                )}
                            >
                                {index + 1}
                            </span>
                            <span className="min-w-0 break-words font-medium leading-snug text-text-primary">
                                {step.label}
                            </span>
                            <StatusChip tone={tone[step.state]}>
                                {humanizeLabel(step.state)}
                            </StatusChip>
                        </a>
                    </li>
                ))}
            </ol>
        </aside>
    );
}

function Summary({
    label,
    value,
    loading = false,
}: {
    label: string;
    value: string;
    loading?: boolean;
}) {
    return (
        <div className="rounded-md border border-hairline bg-surface p-4">
            <p className="text-xs font-medium uppercase text-text-tertiary">{label}</p>
            {loading ? (
                <Skeleton className="mt-2 h-4 w-3/4" />
            ) : (
                <p className="mt-1 break-words text-sm font-semibold leading-snug text-text-primary">
                    {value}
                </p>
            )}
        </div>
    );
}

function ActionPanel({
    id,
    eyebrow,
    title,
    summary,
    icon: Icon,
    children,
}: {
    id?: string;
    eyebrow?: string;
    title: string;
    summary?: string;
    icon: ComponentType<{ className?: string }>;
    children: ReactNode;
}) {
    return (
        <section id={id} className="scroll-mt-20 rounded-md border border-hairline bg-surface p-4">
            <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                <div className="flex min-w-0 gap-3">
                    <span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-primary-soft text-primary-active">
                        <Icon className="h-4 w-4" />
                    </span>
                    <div className="min-w-0">
                        {eyebrow && (
                            <p className="text-[10px] font-semibold uppercase tracking-wider text-text-tertiary">
                                {eyebrow}
                            </p>
                        )}
                        <h2 className="text-base font-semibold text-text-primary">{title}</h2>
                        {summary && <p className="mt-0.5 text-sm text-text-secondary">{summary}</p>}
                    </div>
                </div>
            </div>
            <div className="flex flex-col gap-4">{children}</div>
        </section>
    );
}

function ModeBadge({ mode }: { mode: string }) {
    const fixture = mode === "fixture";
    return (
        <Badge className={cn(fixture ? "bg-warn-soft text-warn" : "bg-ok-soft text-ok")}>
            {fixture ? "Demo analysis" : `${humanizeLabel(mode)} analysis`}
        </Badge>
    );
}

function ProviderBadge({ readiness }: { readiness?: AiReadiness }) {
    if (!readiness) return <Badge variant="outline">AI provider not connected</Badge>;
    return (
        <Badge variant={readiness.configured ? "secondary" : "outline"}>
            {readiness.configured
                ? `${humanizeLabel(readiness.provider)} ready`
                : "AI provider not connected"}
        </Badge>
    );
}

function RuntimeState({
    backendConfigured,
    loading,
    error,
    readiness,
}: {
    backendConfigured: boolean;
    loading: boolean;
    error: unknown;
    readiness?: AiReadiness;
}) {
    if (!backendConfigured) {
        return (
            <div
                role="status"
                aria-live="polite"
                className="flex flex-col gap-2 rounded-md border border-hairline bg-surface-soft p-3 text-sm text-text-primary lg:flex-row lg:items-center lg:justify-between"
            >
                <div className="flex items-center gap-2">
                    <Info className="h-4 w-4 text-warn" />
                    <span>Workspace data is not connected.</span>
                </div>
                <span className="text-xs text-text-secondary">
                    Connect the backend to use your products and media.
                </span>
            </div>
        );
    }

    if (error) {
        return (
            <div
                role="status"
                aria-live="polite"
                className="rounded-md border border-destructive/30 bg-destructive/10 p-3 text-sm text-text-primary"
            >
                {errorMessage(error)}
            </div>
        );
    }
    if (!loading && readiness?.configured !== false) return null;
    return (
        <div
            role="status"
            aria-live="polite"
            className="flex flex-col gap-2 rounded-md border border-hairline bg-surface-soft p-3 text-sm text-text-primary lg:flex-row lg:items-center lg:justify-between"
        >
            <div className="flex items-center gap-2">
                {loading ? (
                    <Loader2 className="h-4 w-4 animate-spin text-text-secondary" />
                ) : (
                    <Info className="h-4 w-4 text-warn" />
                )}
                <span>
                    {loading ? "Loading workspace..." : "AI analysis is running in demo mode."}
                </span>
            </div>
            {!loading && readiness?.missing.length ? (
                <span className="text-xs text-text-secondary">
                    Missing: {readiness.missing.map((item) => humanizeLabel(item)).join(", ")}
                </span>
            ) : null}
        </div>
    );
}

function JobBlock({ job }: { job?: JobResponse }) {
    if (!job) return null;
    const active = ["queued", "running", "retrying"].includes(job.status);
    const statusTone =
        job.status === "failed" || job.status === "cancelled"
            ? "destructive"
            : job.status === "completed"
              ? "ok"
              : "info";
    return (
        <div
            role="status"
            aria-live="polite"
            className="rounded-md border border-primary/15 bg-primary-soft/35 p-3"
        >
            <div className="flex items-center justify-between gap-3 text-sm">
                <span className="inline-flex items-center gap-2 font-medium text-text-primary">
                    {active && <Loader2 className="h-4 w-4 animate-spin text-text-secondary" />}
                    {humanizeLabel(job.job_type)}
                </span>
                <StatusChip tone={statusTone}>{humanizeLabel(job.status)}</StatusChip>
            </div>
            <Progress className="mt-3" value={job.progress} />
            <p className="mt-2 text-xs text-text-secondary">
                Stage: {humanizeLabel(job.stage ?? "queued")}{" "}
                {job.error_message ? `- ${job.error_message}` : ""}
            </p>
            {job.error_code && (
                <p className="mt-1 text-xs font-medium text-destructive">
                    Error code: {humanizeLabel(job.error_code)}
                </p>
            )}
            {active && (
                <AnalysisThinkingSkeleton
                    compact
                    className="mt-3"
                    title="Backend is analyzing"
                    description="Preparing structured evidence, scores, recommendations, and next-step modules."
                />
            )}
        </div>
    );
}

function ScoreBlock({ score }: { score: ScoreRun }) {
    return (
        <ResultShell
            title={formatPercentScore(score.structural_score)}
            subtitle={humanizeLabel(score.action_label)}
            mode={score.analysis_mode}
            outcome="System score"
        >
            <AnalysisTimelineSvg
                title="Scoring timeline"
                durationSec={30}
                currentTime={30}
                markers={scoreMarkers}
            />
            <DimensionGrid dimensions={score.dimension_scores_json} />
            <SignalBlock dimensions={score.dimension_scores_json} />
            <Fixes blockers={score.blockers_json} fixes={score.fixes_json} />
            <p className="text-xs text-text-tertiary">
                Structural readiness score. This is not a guarantee of viral reach, sales, or GMV.
            </p>
        </ResultShell>
    );
}

function DnaBlock({ dna }: { dna: Dna }) {
    const data = dna.dna_json;
    return (
        <ResultShell
            title={observedText(data.narrative?.angle, "Creative DNA")}
            subtitle={`Confidence: ${formatSystemValue(data.overall_confidence ?? dna.confidence)}`}
            mode={dna.analysis_mode}
            outcome="System extraction"
        >
            <AnalysisTimelineSvg
                title="Extracted Creative DNA timeline"
                durationSec={30}
                currentTime={30}
                markers={dnaMarkers}
            />
            <DimensionGrid
                dimensions={{
                    Hook: { score: "-", reason: observedText(data.opening?.hook_text) },
                    Product: {
                        score: "-",
                        reason: `${observedText(data.product?.first_appearance_ms)}ms first reveal`,
                    },
                    Demo: { score: "-", reason: observedText(data.demo?.demo_type) },
                    Proof: { score: "-", reason: observedText(data.proof?.strongest_proof) },
                    CTA: { score: "-", reason: observedText(data.cta?.cta_types) },
                    Creator: { score: "-", reason: observedText(data.creator?.delivery_style) },
                }}
            />
            <ListBlock title="Reusable mechanisms" items={toTextList(data.reusable_mechanisms)} />
            <ListBlock title="Claims" items={toTextList(data.claims)} />
            <ListBlock title="Risks" items={toTextList(data.risks)} />
            <ListBlock title="Uncertainties" items={data.uncertainties ?? []} />
            <KeyValueBlock title="Completeness" values={data.completeness ?? {}} />
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
                    <p className="mt-1 text-sm text-text-secondary">
                        {concept.hook_options?.[0] ?? concept.angle ?? "No hook option"}
                    </p>
                    <p className="mt-2 text-xs text-text-secondary">
                        {formatSystemValue(concept.strategic_axis, "No strategic axis")} -{" "}
                        {formatSystemValue(concept.delivery_style, "No delivery style")}
                    </p>
                    <ListBlock title="Must show" items={concept.must_show ?? []} compact />
                    <p className="mt-3 text-xs text-text-tertiary">{concept.test_hypothesis}</p>
                </article>
            ))}
        </div>
    );
}

function PreflightBlock({ run }: { run: PreflightRun }) {
    return (
        <ResultShell
            title={formatPercentScore(run.preflight_score)}
            subtitle={humanizeLabel(run.action_label)}
            mode={run.analysis_mode}
            outcome="System decision"
        >
            <AnalysisTimelineSvg
                title="Preflight evidence timeline"
                durationSec={30}
                currentTime={30}
                markers={preflightMarkers}
            />
            <DimensionGrid
                dimensions={{
                    Structural: {
                        score: run.structural_score,
                        reason: "Reused TikTok structure scorer",
                    },
                    Brief: {
                        score: run.brief_alignment_score,
                        reason: "Campaign Pack alignment",
                    },
                }}
            />
            <RequirementCoverage run={run} />
            <Fixes blockers={run.blockers_json} fixes={run.fixes_json} />
            <div className="rounded-md bg-info-soft p-3 text-sm text-text-primary">
                {run.revision_message}
            </div>
            <div className="rounded-md border border-hairline bg-surface-soft p-3 text-sm text-text-primary">
                Spark or paid usage remains pending until creator rights and authorization are
                confirmed.
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

function CampaignBriefPreview({ brief }: { brief: CampaignPackBrief }) {
    const productName =
        getRecordValue(brief.product_snapshot, "name") ??
        getRecordValue(brief.product_snapshot, "product_name");
    return (
        <div className="rounded-md border border-primary/15 bg-primary-soft/30 p-4">
            <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                <div>
                    <p className="text-[10px] font-semibold uppercase tracking-wider text-primary">
                        Generated campaign brief
                    </p>
                    <h3 className="mt-1 text-base font-semibold text-text-primary">
                        {formatSystemValue(productName, "Campaign Pack")}
                    </h3>
                </div>
                <StatusChip tone="ok" dot>
                    Ready to review
                </StatusChip>
            </div>
            <div className="grid gap-3 md:grid-cols-2">
                <BriefField title="Objective" value={brief.objective} />
                <BriefField title="Audience" value={brief.audience} />
                <BriefField title="Angle" value={brief.angle} />
                <BriefField title="CTA" value={brief.cta} />
            </div>
            <div className="mt-3 grid gap-3 md:grid-cols-2">
                <ListBlock
                    title="Must show"
                    items={(brief.must_show ?? []).map((item) => formatBriefRequirement(item))}
                    compact
                />
                <BriefField title="Claim guardrails" value={brief.claim_guardrails} />
            </div>
        </div>
    );
}

function BriefField({ title, value }: { title: string; value: unknown }) {
    return (
        <div className="rounded-md border border-hairline bg-surface p-3">
            <p className="text-xs font-semibold uppercase tracking-wide text-text-tertiary">
                {title}
            </p>
            <p className="mt-1 text-sm text-text-primary">{formatSystemValue(value)}</p>
        </div>
    );
}

function formatBriefRequirement(value: unknown) {
    const description =
        getRecordValue(value, "description") ??
        getRecordValue(value, "label") ??
        getRecordValue(value, "name");
    const requirementType = getRecordValue(value, "requirement_type");
    const severity = getRecordValue(value, "severity");
    if (!description) return formatSystemValue(value);
    return [
        formatSystemValue(description),
        requirementType ? `Type: ${formatSystemValue(requirementType)}` : null,
        severity ? `Severity: ${formatSystemValue(severity)}` : null,
    ]
        .filter(Boolean)
        .join(" · ");
}

function getRecordValue(value: unknown, key: string) {
    if (!value || typeof value !== "object" || Array.isArray(value)) return undefined;
    return (value as Record<string, unknown>)[key];
}

function VersionHistory({
    versions,
    isLoading,
}: {
    versions: CampaignPackVersion[];
    isLoading: boolean;
}) {
    if (isLoading) {
        return (
            <div className="rounded-md border border-hairline bg-surface-soft p-3 text-sm text-text-secondary">
                Loading version history...
            </div>
        );
    }
    return (
        <div className="rounded-md border border-hairline bg-surface-soft p-3">
            <h3 className="text-sm font-semibold text-text-primary">Version history</h3>
            <div className="mt-3 space-y-2">
                {versions.length ? (
                    versions.map((version) => (
                        <div
                            key={version.id}
                            className="flex flex-col gap-1 rounded-md border border-hairline bg-surface p-3 text-sm sm:flex-row sm:items-center sm:justify-between"
                        >
                            <div>
                                <p className="font-medium text-text-primary">
                                    Version {version.version_number}
                                </p>
                                <p className="text-xs text-text-secondary">
                                    {version.change_note ?? "Initial generated brief"}
                                </p>
                            </div>
                            <div className="text-xs text-text-tertiary">
                                {version.source_model_run_id
                                    ? `Model run ${version.source_model_run_id.slice(0, 8)}`
                                    : "Fixture/manual provenance"}
                            </div>
                        </div>
                    ))
                ) : (
                    <p className="text-sm text-text-secondary">No saved versions yet.</p>
                )}
            </div>
        </div>
    );
}

function ResultShell({
    title,
    subtitle,
    mode,
    outcome = "System response",
    children,
}: {
    title: string;
    subtitle: string;
    mode: string;
    outcome?: string;
    children: ReactNode;
}) {
    return (
        <div className="rounded-md border border-hairline bg-surface p-4">
            <div className="mb-4 flex flex-wrap items-center justify-between gap-2 rounded-md border border-primary/20 bg-primary-soft/45 p-4">
                <div>
                    <p className="text-[10px] font-semibold uppercase tracking-wider text-primary">
                        {outcome}
                    </p>
                    <p className="mt-1 text-2xl font-semibold text-text-primary">{title}</p>
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
                            {humanizeLabel(key)}
                        </p>
                        <span className="text-sm font-semibold text-text-primary">
                            {formatSystemValue(item.score)}
                        </span>
                    </div>
                    {typeof item.score === "number" && (
                        <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-surface-muted">
                            <div
                                className={cn(
                                    "h-full rounded-full",
                                    item.score >= 80
                                        ? "bg-ok"
                                        : item.score >= 60
                                          ? "bg-warn"
                                          : "bg-destructive",
                                )}
                                style={{ width: `${Math.max(0, Math.min(100, item.score))}%` }}
                            />
                        </div>
                    )}
                    <p className="mt-1 text-xs text-text-secondary">
                        {formatSystemValue(item.reason)}
                    </p>
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

function SignalBlock({ dimensions }: { dimensions: Record<string, DimensionResult> }) {
    const rows = Object.entries(dimensions).flatMap(([dimension, item]) =>
        (item.signals ?? []).map((signal) => ({ dimension, signal })),
    );
    return (
        <div className="rounded-md border border-hairline bg-surface-soft p-3">
            <h3 className="text-sm font-semibold text-text-primary">Signals</h3>
            <div className="mt-2 grid gap-2 md:grid-cols-2">
                {rows.length ? (
                    rows.slice(0, 12).map(({ dimension, signal }) => (
                        <div
                            key={`${dimension}-${signal.code}`}
                            className="rounded-md border border-hairline bg-surface p-2 text-xs"
                        >
                            <div className="flex items-center justify-between gap-2">
                                <span className="font-medium text-text-primary">
                                    {humanizeLabel(signal.code)}
                                </span>
                                <span className="text-text-secondary">{signal.contribution}</span>
                            </div>
                            <p className="mt-1 text-text-tertiary">
                                {humanizeLabel(dimension)} - {formatSystemValue(signal.value)}
                            </p>
                        </div>
                    ))
                ) : (
                    <p className="text-sm text-text-secondary">No signals returned.</p>
                )}
            </div>
        </div>
    );
}

function RequirementCoverage({ run }: { run: PreflightRun }) {
    const requirements = run.brief_alignment_json.requirements ?? [];
    return (
        <div className="rounded-md border border-hairline bg-surface-soft p-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
                <h3 className="text-sm font-semibold text-text-primary">Requirement coverage</h3>
                <span className="text-xs text-text-secondary">
                    {formatSystemValue(run.brief_alignment_json.coverage ?? {})}
                </span>
            </div>
            <div className="mt-3 grid gap-2">
                {requirements.length ? (
                    requirements.map((requirement) => (
                        <div
                            key={requirement.requirement_id}
                            className="rounded-md border border-hairline bg-surface p-3 text-sm"
                        >
                            <div className="flex flex-wrap items-center justify-between gap-2">
                                <span className="font-medium text-text-primary">
                                    {humanizeLabel(requirement.requirement_id)}
                                </span>
                                <StatusChip tone={requirementTone(requirement.status)}>
                                    {humanizeLabel(requirement.status)} · {requirement.score}
                                </StatusChip>
                            </div>
                            <p className="mt-1 text-xs text-text-secondary">{requirement.reason}</p>
                            <p className="mt-2 text-xs text-text-tertiary">
                                Expected: {formatSystemValue(requirement.expected)}
                            </p>
                            <p className="mt-1 text-xs text-text-tertiary">
                                Observed: {formatSystemValue(requirement.observed)}
                            </p>
                        </div>
                    ))
                ) : (
                    <p className="text-sm text-text-secondary">No requirements returned.</p>
                )}
            </div>
        </div>
    );
}

function KeyValueBlock({ title, values }: { title: string; values: Record<string, unknown> }) {
    return (
        <div className="rounded-md border border-hairline bg-surface-soft p-3">
            <h3 className="text-sm font-semibold text-text-primary">{title}</h3>
            <div className="mt-2 grid gap-1 text-sm text-text-secondary">
                {Object.entries(values).length ? (
                    Object.entries(values).map(([key, value]) => (
                        <div key={key} className="flex justify-between gap-3">
                            <span>{humanizeLabel(key)}</span>
                            <span>{formatSystemValue(value)}</span>
                        </div>
                    ))
                ) : (
                    <span>None</span>
                )}
            </div>
        </div>
    );
}

function ListBlock({
    title,
    items,
    compact = false,
}: {
    title: string;
    items: Array<string | undefined>;
    compact?: boolean;
}) {
    return (
        <div
            className={cn(
                "rounded-md border border-hairline bg-surface-soft",
                compact ? "p-2" : "p-3",
            )}
        >
            <h3 className="text-sm font-semibold text-text-primary">{title}</h3>
            <ul className="mt-2 space-y-1 text-sm text-text-secondary">
                {items.filter(Boolean).length ? (
                    items.filter(Boolean).map((item) => <li key={item}>{item}</li>)
                ) : (
                    <li>None</li>
                )}
            </ul>
        </div>
    );
}

function observedText(value: unknown, fallback = "unknown") {
    if (isObservedValue(value)) return stringify(value.value, fallback);
    return stringify(value, fallback);
}

function toTextList(value: unknown): string[] {
    if (!Array.isArray(value)) return [];
    return value.map((item) => stringify(item)).filter((item) => item !== "unknown");
}

function isObservedValue(value: unknown): value is ObservedValue {
    return Boolean(value && typeof value === "object" && "value" in value);
}

function stringify(value: unknown, fallback = "unknown"): string {
    return formatSystemValue(value, fallback);
}

function assetTitle(asset: Asset | undefined, fallback = "No video selected") {
    return String(asset?.metadata_json.title ?? asset?.id ?? fallback);
}

function parseCampaignBriefDraft(value: string): CampaignPackBrief {
    let parsed: unknown;
    try {
        parsed = JSON.parse(value);
    } catch {
        throw new Error("Campaign Pack brief must be valid JSON.");
    }
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
        throw new Error("Campaign Pack brief must be an object.");
    }
    const brief = parsed as CampaignPackBrief;
    if (brief.schema_version !== "campaign_pack_brief_v1") {
        throw new Error("Campaign Pack brief must use campaign_pack_brief_v1.");
    }
    if (!brief.product_snapshot || !brief.objective || !brief.audience || !brief.angle) {
        throw new Error("Campaign Pack brief is missing product/objective/audience/angle.");
    }
    if (!Array.isArray(brief.must_show)) {
        throw new Error("Campaign Pack brief must include must_show requirements.");
    }
    if (!brief.cta || !brief.claim_guardrails) {
        throw new Error("Campaign Pack brief is missing CTA or claim guardrails.");
    }
    return brief;
}

function errorMessage(error: unknown) {
    if (error instanceof Error) return error.message;
    return "Backend workflow state could not be loaded.";
}
