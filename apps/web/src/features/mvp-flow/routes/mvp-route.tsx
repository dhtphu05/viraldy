import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
    CheckCircle2,
    Clipboard,
    FileVideo,
    Loader2,
    Play,
    RefreshCw,
    Sparkles,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import type { ComponentType, KeyboardEvent, ReactNode } from "react";
import { toast } from "sonner";

import { AppShell } from "@/widgets/app-shell/app-shell";
import { apiGet, apiPost, hasConfiguredApiBaseUrl } from "@/shared/api/client";
import { getJob, type JobResponse } from "@/shared/api/jobs";
import { queryKeys } from "@/shared/api/query-keys";
import { getAiReadiness } from "@/shared/api/system";
import { uploadAsset, type Asset } from "@/shared/api/uploads";
import { Button } from "@/shared/ui/button";
import { StatusChip } from "@/shared/ui/status-chip";
import { Textarea } from "@/shared/ui/textarea";
import { cn } from "@/shared/lib/utils";
import { DisabledActionHint } from "@/shared/ui/disabled-action-hint";
import { formatSystemValue, humanizeLabel } from "@/shared/lib/display";
import { AnalysisTimelineSvg } from "@/shared/ui/analysis-timeline-svg";
import { ActionTray } from "@/shared/ui/action-tray";
import { DecisionHero } from "@/shared/ui/decision-hero";
import { ExpectedObservedTable } from "@/shared/ui/expected-observed-table";
import { Input } from "@/shared/ui/input";
import { ValueReceipt } from "@/shared/ui/value-receipt";
import type { WorkflowRailStep } from "@/shared/ui/workflow-rail";
import { InputStep } from "@/features/mvp-flow/components/input-step";
import { JobProgress } from "@/features/mvp-flow/components/job-progress";
import { ProductionRunHeader } from "@/features/mvp-flow/components/production-run-header";
import { ProductionRunRail } from "@/features/mvp-flow/components/production-run-rail";

export const Route = createFileRoute("/mvp")({
    head: () => ({ meta: [{ title: "Production Run - Viraldy" }] }),
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
    const [selectedConceptId, setSelectedConceptId] = useState("concept_1");
    const [revisionDraft, setRevisionDraft] = useState("");
    const [revisionSaved, setRevisionSaved] = useState(false);
    const [revisionRunId, setRevisionRunId] = useState<string | null>(null);
    const backendConfigured = hasConfiguredApiBaseUrl;

    const updateWorkflowSearch = (updates: Partial<MvpSearch>) => {
        void navigate({
            to: "/mvp",
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

    useEffect(() => {
        if (!preflight.data || preflight.data.id === revisionRunId) return;
        setRevisionDraft(preflight.data.revision_message);
        setRevisionSaved(false);
        setRevisionRunId(preflight.data.id);
    }, [preflight.data, revisionRunId]);

    useEffect(() => {
        const concepts = adaptation.data?.result_json.concepts;
        if (!concepts?.length || concepts.some((concept) => concept.id === selectedConceptId))
            return;
        setSelectedConceptId(concepts[0].id);
    }, [adaptation.data, selectedConceptId]);

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
        onError: (error) =>
            toast.error(error instanceof Error ? error.message : "Reference analysis failed"),
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
            setSelectedConceptId(run.result_json.concepts[0]?.id ?? "concept_1");
            toast.success("Adaptation generated");
        },
        onError: (error) =>
            toast.error(
                error instanceof Error ? error.message : "Adaptation could not be generated",
            ),
    });

    const createPack = useMutation({
        mutationFn: async () =>
            apiPost<CampaignPack>(`/workspaces/${workspaceId}/campaign-packs`, {
                adaptation_run_id: adaptationId,
                concept_id: selectedConceptId,
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
        onError: (error) =>
            toast.error(
                error instanceof Error ? error.message : "Campaign Pack could not be created",
            ),
    });

    const savePackVersion = useMutation({
        mutationFn: async () => {
            const brief = parseCampaignBriefDraft(briefDraft);
            return apiPost<CampaignPackVersion>(
                `/workspaces/${workspaceId}/campaign-packs/${packId}/versions`,
                {
                    brief,
                    change_note: "Edited in Production Run",
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
        onError: (error) =>
            toast.error(
                error instanceof Error ? error.message : "Campaign Pack could not be saved",
            ),
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
        onError: (error) =>
            toast.error(error instanceof Error ? error.message : "UGC Preflight could not start"),
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
            !["succeeded", "completed"].includes(dnaJob.data?.status ?? ""),
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
    const briefDraftError = briefDraft ? campaignBriefDraftError(briefDraft) : null;
    const savePackReason = disabledReason([
        [!packId, "Create a campaign brief before saving a new version."],
        [!briefDraft, "Brief JSON is empty."],
        [Boolean(briefDraftError), briefDraftError ?? "Campaign Pack brief is invalid."],
        [savePackVersion.isPending, "A new Campaign Pack version is already being saved."],
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
    const runtimeError = backendConfigured
        ? (aiReadiness.error ??
          workspaces.error ??
          products.error ??
          assets.error ??
          boards.error ??
          references.error ??
          null)
        : null;
    const inputItems = [
        {
            label: "Product",
            value: product?.name ?? (workspaceId ? "No product selected" : "Waiting for workspace"),
            complete: Boolean(product),
        },
        {
            label: "Reference board",
            value:
                boards.data?.[0]?.name ??
                (workspaceId ? "No board selected" : "Waiting for workspace"),
            complete: Boolean(boards.data?.[0]),
        },
        {
            label: "Winning reference",
            value: reference?.title ?? "No reference selected",
            complete: Boolean(reference),
        },
        {
            label: "Quick reference asset",
            value: assetTitle(
                quickAsset,
                workspaceId ? "No video selected" : "Waiting for workspace",
            ),
            complete: Boolean(quickAsset),
        },
        {
            label: "Creator video",
            value: assetTitle(
                ugcAsset,
                workspaceId ? "No video selected" : "Waiting for workspace",
            ),
            complete: Boolean(ugcAsset),
        },
    ];
    const missingRequirements = inputItems
        .filter((item) => !item.complete)
        .map((item) => item.label.toLowerCase());
    const inputComplete = missingRequirements.length === 0;
    const dnaComplete = Boolean(dnaId && dna.data);
    const adaptationComplete = Boolean(adaptationId && adaptation.data);
    const packComplete = Boolean(packId && pack.data?.current_version);
    const preflightComplete = Boolean(preflightRunId && preflight.data);
    const ready = isPreflightReady(preflight.data);
    const workflowSteps: WorkflowRailStep[] = [
        {
            id: "input",
            label: "Input",
            state: inputComplete ? "complete" : "current",
            description: inputComplete ? "Production context ready" : "Complete required inputs",
            onSelect: () => scrollToStep("input"),
        },
        {
            id: "creative-dna",
            label: "Creative DNA",
            state: dnaComplete
                ? "complete"
                : dnaJob.data?.status === "failed"
                  ? "blocked"
                  : inputComplete
                    ? "current"
                    : "future",
            description: dnaComplete ? "Reusable pattern extracted" : "Analyze the reference",
            blockedReason: dnaJob.data?.error_message ?? undefined,
            onSelect: () => scrollToStep("creative-dna"),
        },
        {
            id: "product-adaptation",
            label: "Adaptation",
            state: adaptationComplete
                ? "complete"
                : dnaComplete
                  ? "current"
                  : dnaJob.data?.status === "failed"
                    ? "blocked"
                    : "future",
            description: adaptationComplete ? "Product concepts ready" : "Adapt the source pattern",
            onSelect: () => scrollToStep("product-adaptation"),
        },
        {
            id: "campaign-brief",
            label: "Campaign Pack",
            state: packComplete ? "complete" : adaptationComplete ? "current" : "future",
            description: packComplete ? "Current version available" : "Build creator guidance",
            onSelect: () => scrollToStep("campaign-brief"),
        },
        {
            id: "ugc-preflight",
            label: "UGC Preflight",
            state: preflightComplete
                ? "complete"
                : preflightJob.data?.status === "failed"
                  ? "blocked"
                  : packComplete
                    ? "current"
                    : "future",
            description: preflightComplete ? "Creator video reviewed" : "Validate brief alignment",
            blockedReason: preflightJob.data?.error_message ?? undefined,
            onSelect: () => scrollToStep("ugc-preflight"),
        },
        {
            id: "ready",
            label: "Ready",
            state: ready ? "complete" : preflightComplete ? "current" : "future",
            description: ready ? "Production Run complete" : "Resolve review blockers",
            onSelect: () => scrollToStep("ready"),
        },
    ];

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
                <ProductionRunHeader
                    backendConfigured={backendConfigured}
                    loading={workflowLoading}
                    error={runtimeError}
                    readiness={aiReadiness.data}
                    workspaceName={workspaces.data?.[0]?.name}
                />

                <div className="grid gap-5 xl:grid-cols-[240px_minmax(0,1fr)] xl:items-start">
                    <ProductionRunRail steps={workflowSteps} />
                    <div className="flex min-w-0 flex-col gap-5">
                        <InputStep
                            items={inputItems}
                            loading={workflowLoading}
                            uploadDisabled={!workspaceId}
                            uploadState={uploadState}
                            onUpload={handleUpload}
                            missingRequirements={missingRequirements}
                            quickCheck={
                                <div className="flex flex-col gap-4">
                                    <div className="flex flex-wrap items-center gap-2">
                                        <DisabledActionHint reason={quickReason}>
                                            <Button
                                                onClick={() => runQuick.mutate()}
                                                disabled={!!quickReason}
                                            >
                                                {runQuick.isPending ? (
                                                    <Loader2 className="h-4 w-4 animate-spin" />
                                                ) : (
                                                    <Play className="h-4 w-4" />
                                                )}
                                                Score reference
                                            </Button>
                                        </DisabledActionHint>
                                        <p className="text-xs text-text-secondary">
                                            Optional. Checks structure without replacing Creative
                                            DNA analysis.
                                        </p>
                                    </div>
                                    <JobProgress job={quickJob.data} />
                                    {quickScore.isError && (
                                        <WorkflowError
                                            title="Quick score could not be loaded"
                                            error={quickScore.error}
                                            onRetry={() => void quickScore.refetch()}
                                        />
                                    )}
                                    {quickScore.data?.status === "completed" && (
                                        <ScoreBlock score={quickScore.data} />
                                    )}
                                </div>
                            }
                        />

                        <ActionPanel
                            id="creative-dna"
                            eyebrow="Creative DNA"
                            title="Extract reusable creative mechanics"
                            summary="Analyze the winning reference for hooks, proof, pacing, and creator patterns."
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
                            <JobProgress
                                job={dnaJob.data}
                                recoveryAction={
                                    <Button
                                        size="sm"
                                        variant="secondary"
                                        onClick={() => analyzeReference.mutate()}
                                        disabled={analyzeReference.isPending}
                                    >
                                        Retry analysis
                                    </Button>
                                }
                            />
                            {dna.isError && (
                                <WorkflowError
                                    title="Creative DNA could not be loaded"
                                    error={dna.error}
                                    onRetry={() => void dna.refetch()}
                                />
                            )}
                            {dna.data && <DnaBlock dna={dna.data} />}
                        </ActionPanel>

                        <ActionPanel
                            id="product-adaptation"
                            eyebrow="Adaptation"
                            title="Adapt the pattern to this product"
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
                            {adaptation.isError && (
                                <WorkflowError
                                    title="Adaptation could not be loaded"
                                    error={adaptation.error}
                                    onRetry={() => void adaptation.refetch()}
                                />
                            )}
                            {adaptation.data && (
                                <ConceptBlock
                                    concepts={adaptation.data.result_json.concepts}
                                    selectedId={selectedConceptId}
                                    onSelect={setSelectedConceptId}
                                />
                            )}
                        </ActionPanel>

                        <ActionPanel
                            id="campaign-brief"
                            eyebrow="Campaign Pack"
                            title="Build creator-ready guidance"
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
                            </div>
                            {pack.isError && (
                                <WorkflowError
                                    title="Campaign Pack could not be loaded"
                                    error={pack.error}
                                    onRetry={() => void pack.refetch()}
                                />
                            )}
                            {pack.data?.current_version && (
                                <>
                                    <CampaignBriefEditor
                                        value={briefDraft}
                                        onChange={setBriefDraft}
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
                                        {briefDraftError && (
                                            <p
                                                className="mt-2 text-xs font-medium text-destructive"
                                                role="alert"
                                            >
                                                {briefDraftError}
                                            </p>
                                        )}
                                    </details>
                                    <ActionTray
                                        context={
                                            <span>
                                                Current version{" "}
                                                <strong className="text-text-primary">
                                                    {pack.data.current_version.version_number}
                                                </strong>{" "}
                                                · Save edits as a new immutable version.
                                            </span>
                                        }
                                        primaryAction={
                                            <DisabledActionHint reason={savePackReason}>
                                                <Button
                                                    onClick={() => savePackVersion.mutate()}
                                                    disabled={!!savePackReason}
                                                >
                                                    <CheckCircle2 className="h-4 w-4" />
                                                    Save new version
                                                </Button>
                                            </DisabledActionHint>
                                        }
                                    />
                                </>
                            )}
                            <VersionHistory
                                versions={packVersions.data ?? []}
                                isLoading={packVersions.isLoading}
                            />
                        </ActionPanel>

                        <ActionPanel
                            id="ugc-preflight"
                            eyebrow="UGC Preflight"
                            title="Validate the creator video"
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
                            <JobProgress
                                job={preflightJob.data}
                                recoveryAction={
                                    <Button
                                        size="sm"
                                        variant="secondary"
                                        onClick={() => runPreflight.mutate()}
                                        disabled={runPreflight.isPending}
                                    >
                                        Retry review
                                    </Button>
                                }
                            />
                            {preflight.isError && (
                                <WorkflowError
                                    title="UGC Preflight result could not be loaded"
                                    error={preflight.error}
                                    onRetry={() => void preflight.refetch()}
                                />
                            )}
                            {preflight.data?.status === "completed" && (
                                <PreflightBlock
                                    run={preflight.data}
                                    revisionDraft={revisionDraft}
                                    revisionSaved={revisionSaved}
                                    onRevisionChange={(value) => {
                                        setRevisionDraft(value);
                                        setRevisionSaved(false);
                                    }}
                                    onRevisionSave={() => {
                                        setRevisionSaved(true);
                                        toast.success("Revision message saved locally");
                                    }}
                                />
                            )}
                        </ActionPanel>

                        <section id="ready" className="scroll-mt-20">
                            {ready ? (
                                <ValueReceipt
                                    title="Production Run complete"
                                    description="The campaign guidance and creator video are ready for the next operating step."
                                    items={[
                                        "Creative DNA analyzed",
                                        "One adaptation selected",
                                        "Campaign Pack version saved",
                                        "UGC Preflight completed without blockers",
                                    ]}
                                    action={
                                        <Button
                                            size="sm"
                                            onClick={() => scrollToStep("campaign-brief")}
                                        >
                                            Open Campaign Pack
                                        </Button>
                                    }
                                />
                            ) : (
                                <div className="rounded-2xl bg-surface px-5 py-4 shadow-soft-card">
                                    <p className="text-sm font-semibold text-text-primary">
                                        Ready checkpoint
                                    </p>
                                    <p className="mt-1 text-sm text-text-secondary">
                                        {preflightComplete
                                            ? `${preflight.data?.blockers_json.length ?? 0} blockers remain before this run is ready.`
                                            : "Complete UGC Preflight to confirm production readiness."}
                                    </p>
                                </div>
                            )}
                        </section>
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
            return status && ["succeeded", "completed", "failed", "cancelled"].includes(status)
                ? false
                : 1200;
        },
    });
}

function disabledReason(entries: Array<[boolean, string]>) {
    return entries.find(([blocked]) => blocked)?.[1] ?? null;
}

function scrollToStep(id: string) {
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
}

function decisionTone(actionLabel: string, blockerCount: number) {
    const normalized = actionLabel.toLowerCase();
    if (normalized.includes("reject")) return "destructive" as const;
    if (
        blockerCount > 0 ||
        normalized.includes("revise") ||
        normalized.includes("hold") ||
        normalized.includes("fix")
    ) {
        return "warn" as const;
    }
    if (
        normalized.includes("ready") ||
        normalized.includes("approve") ||
        normalized.includes("pass")
    ) {
        return "ok" as const;
    }
    return "info" as const;
}

function isPreflightReady(run?: PreflightRun) {
    if (!run || run.status !== "completed" || run.blockers_json.length > 0) return false;
    const action = run.action_label.toLowerCase();
    return !["revise", "reject", "hold", "block"].some((label) => action.includes(label));
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
        <section
            id={id}
            className="scroll-mt-20 rounded-2xl bg-surface p-5 shadow-soft-card sm:p-6"
        >
            <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                <div className="flex min-w-0 gap-3">
                    <span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-primary-soft text-primary-active">
                        <Icon className="h-4 w-4" />
                    </span>
                    <div className="min-w-0">
                        {eyebrow && (
                            <p className="text-[10px] font-semibold uppercase text-text-tertiary">
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

function WorkflowError({
    title,
    error,
    onRetry,
}: {
    title: string;
    error: unknown;
    onRetry: () => void;
}) {
    return (
        <div
            role="alert"
            className="flex flex-col gap-3 rounded-2xl bg-destructive-soft p-4 sm:flex-row sm:items-center sm:justify-between"
        >
            <div>
                <p className="text-sm font-semibold text-destructive">{title}</p>
                <p className="mt-1 text-xs text-text-secondary">
                    {error instanceof Error
                        ? error.message
                        : "The backend response was unavailable. Retry the current step."}
                </p>
            </div>
            <Button size="sm" variant="secondary" onClick={onRetry}>
                Retry
            </Button>
        </div>
    );
}

function ScoreBlock({ score }: { score: ScoreRun }) {
    const reason =
        score.blockers_json[0]?.message ??
        score.fixes_json[0]?.why ??
        score.fixes_json[0]?.instruction ??
        "The structure check is complete. Review the evidence before reusing this pattern.";
    return (
        <div className="flex flex-col gap-4">
            <DecisionHero
                eyebrow="Quick check decision"
                actionLabel={humanizeLabel(score.action_label)}
                reason={reason}
                score={score.structural_score}
                confidence={score.confidence}
                blockerCount={score.blockers_json.length}
                effort={`${humanizeLabel(score.analysis_mode)} analysis`}
                statusTone={decisionTone(score.action_label, score.blockers_json.length)}
                primaryAction={
                    <Button size="sm" onClick={() => scrollToStep("creative-dna")}>
                        Analyze Creative DNA
                    </Button>
                }
                secondaryAction={
                    <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => scrollToStep("quick-score-evidence")}
                    >
                        Review evidence
                    </Button>
                }
            />
            <div id="quick-score-evidence" className="scroll-mt-20 space-y-4">
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
                    Structural readiness score. This is not a guarantee of viral reach, sales, or
                    GMV.
                </p>
            </div>
        </div>
    );
}

function DnaBlock({ dna }: { dna: Dna }) {
    const data = dna.dna_json;
    return (
        <div className="flex flex-col gap-4">
            <DecisionHero
                eyebrow="Creative DNA extracted"
                actionLabel={observedText(data.narrative?.angle, "Reusable pattern ready")}
                reason={
                    <>
                        Opening: {observedText(data.opening?.hook_text)}. Strongest proof:{" "}
                        {observedText(data.proof?.strongest_proof)}.
                    </>
                }
                confidence={formatSystemValue(data.overall_confidence ?? dna.confidence)}
                effort={`${humanizeLabel(dna.analysis_mode)} analysis`}
                statusTone="info"
                primaryAction={
                    <Button size="sm" onClick={() => scrollToStep("product-adaptation")}>
                        Adapt to product
                    </Button>
                }
                secondaryAction={
                    <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => scrollToStep("dna-evidence")}
                    >
                        Review evidence
                    </Button>
                }
            />
            <AnalysisTimelineSvg
                title="Extracted Creative DNA timeline"
                durationSec={30}
                currentTime={30}
                markers={dnaMarkers}
            />
            <div id="dna-evidence" className="scroll-mt-20">
                <p className="mb-3 text-sm font-semibold text-text-primary">Creative DNA ribbon</p>
                <div className="grid overflow-hidden rounded-2xl bg-surface-soft sm:grid-cols-2 lg:grid-cols-5">
                    <DnaRibbonItem label="Opening" value={observedText(data.opening?.hook_text)} />
                    <DnaRibbonItem
                        label="Product"
                        value={`${observedText(data.product?.first_appearance_ms)}ms reveal`}
                    />
                    <DnaRibbonItem
                        label="Narrative"
                        value={observedText(data.narrative?.structure)}
                    />
                    <DnaRibbonItem label="Demo" value={observedText(data.demo?.demo_type)} />
                    <DnaRibbonItem
                        label="Proof"
                        value={observedText(data.proof?.strongest_proof)}
                    />
                    <DnaRibbonItem
                        label="Creator"
                        value={observedText(data.creator?.delivery_style)}
                    />
                    <DnaRibbonItem label="Editing" value={observedText(data.editing?.pacing)} />
                    <DnaRibbonItem label="Offer" value={observedText(data.offer?.offer_types)} />
                    <DnaRibbonItem label="CTA" value={observedText(data.cta?.cta_types)} />
                    <DnaRibbonItem label="Platform" value={observedText(data.platform?.format)} />
                </div>
            </div>
            <div className="grid gap-3 lg:grid-cols-2">
                <ListBlock
                    title="Reusable mechanisms"
                    items={toTextList(data.reusable_mechanisms)}
                />
                <ListBlock title="Claims" items={toTextList(data.claims)} />
                <ListBlock title="Risks" items={toTextList(data.risks)} />
                <ListBlock title="Uncertainties" items={data.uncertainties ?? []} />
            </div>
            <KeyValueBlock title="Completeness" values={data.completeness ?? {}} />
            <details className="rounded-2xl bg-surface-soft p-4">
                <summary className="cursor-pointer text-sm font-medium text-text-primary">
                    Advanced data
                </summary>
                <pre className="mt-3 max-h-96 overflow-auto whitespace-pre-wrap break-words text-xs text-text-secondary">
                    {JSON.stringify(data, null, 2)}
                </pre>
            </details>
        </div>
    );
}

function DnaRibbonItem({ label, value }: { label: string; value: string }) {
    return (
        <div className="min-w-0 border-b border-divider p-3 last:border-b-0 sm:border-r lg:[&:nth-child(5n)]:border-r-0">
            <p className="text-[10px] font-semibold uppercase text-text-tertiary">{label}</p>
            <p className="mt-1 line-clamp-2 break-words text-sm text-text-primary">{value}</p>
        </div>
    );
}

function ConceptBlock({
    concepts,
    selectedId,
    onSelect,
}: {
    concepts: AdaptationConcept[];
    selectedId: string;
    onSelect: (id: string) => void;
}) {
    function handleConceptKeyDown(event: KeyboardEvent<HTMLButtonElement>, index: number) {
        const isPrevious = event.key === "ArrowLeft" || event.key === "ArrowUp";
        const isNext = event.key === "ArrowRight" || event.key === "ArrowDown";
        if (!isPrevious && !isNext && event.key !== "Home" && event.key !== "End") return;

        event.preventDefault();
        const nextIndex =
            event.key === "Home"
                ? 0
                : event.key === "End"
                  ? concepts.length - 1
                  : isPrevious
                    ? (index - 1 + concepts.length) % concepts.length
                    : (index + 1) % concepts.length;
        onSelect(concepts[nextIndex].id);
        const radios =
            event.currentTarget.parentElement?.querySelectorAll<HTMLButtonElement>(
                '[role="radio"]',
            );
        radios?.[nextIndex]?.focus();
    }

    return (
        <div>
            <div
                className="grid gap-3 lg:grid-cols-3"
                role="radiogroup"
                aria-label="Adaptation concepts"
            >
                {concepts.map((concept, index) => {
                    const selected = concept.id === selectedId;
                    return (
                        <button
                            key={concept.id}
                            type="button"
                            role="radio"
                            aria-checked={selected}
                            tabIndex={selected ? 0 : -1}
                            onClick={() => onSelect(concept.id)}
                            onKeyDown={(event) => handleConceptKeyDown(event, index)}
                            className={cn(
                                "min-w-0 rounded-2xl bg-surface-soft p-4 text-left transition-[box-shadow,background-color,transform] duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                                selected
                                    ? "bg-primary-soft/55 shadow-[inset_0_0_0_2px_var(--primary)]"
                                    : "hover:-translate-y-0.5 hover:bg-surface-muted",
                            )}
                        >
                            <div className="flex items-start justify-between gap-3">
                                <h3 className="font-semibold text-text-primary">{concept.name}</h3>
                                {selected && <StatusChip tone="info">Selected</StatusChip>}
                            </div>
                            <p className="mt-2 text-sm leading-5 text-text-secondary">
                                {concept.hook_options?.[0] ?? concept.angle ?? "No hook option"}
                            </p>
                            <dl className="mt-4 space-y-2 text-xs">
                                <ConceptField
                                    label="Strategic axis"
                                    value={concept.strategic_axis}
                                />
                                <ConceptField label="Buyer pain" value={concept.buyer_pain} />
                                <ConceptField
                                    label="Desired outcome"
                                    value={concept.desired_outcome}
                                />
                                <ConceptField
                                    label="Creator"
                                    value={
                                        concept.creator_persona && concept.delivery_style
                                            ? `${concept.creator_persona} · ${concept.delivery_style}`
                                            : (concept.creator_persona ?? concept.delivery_style)
                                    }
                                />
                                <ConceptField label="Demo" value={concept.demo_mechanism} />
                                <ConceptField label="Proof" value={concept.proof_mechanism} />
                            </dl>
                            <p className="mt-4 text-xs leading-5 text-text-tertiary">
                                {concept.test_hypothesis}
                            </p>
                        </button>
                    );
                })}
            </div>
            <p className="mt-3 text-xs text-text-secondary">
                The selected concept becomes the source for Campaign Pack creation.
            </p>
        </div>
    );
}

function ConceptField({ label, value }: { label: string; value?: string }) {
    return (
        <div className="grid grid-cols-[92px_minmax(0,1fr)] gap-2">
            <dt className="text-text-tertiary">{label}</dt>
            <dd className="break-words text-text-primary">
                {formatSystemValue(value, "Not specified")}
            </dd>
        </div>
    );
}

function PreflightBlock({
    run,
    revisionDraft,
    revisionSaved,
    onRevisionChange,
    onRevisionSave,
}: {
    run: PreflightRun;
    revisionDraft: string;
    revisionSaved: boolean;
    onRevisionChange: (value: string) => void;
    onRevisionSave: () => void;
}) {
    const requirements = run.brief_alignment_json.requirements ?? [];
    const reason =
        run.blockers_json[0]?.message ??
        run.fixes_json[0]?.why ??
        run.fixes_json[0]?.instruction ??
        "The creator video has been compared with the current Campaign Pack.";
    return (
        <div className="flex flex-col gap-4">
            <DecisionHero
                eyebrow="UGC Preflight decision"
                actionLabel={humanizeLabel(run.action_label)}
                reason={reason}
                score={run.preflight_score}
                confidence={run.brief_alignment_json.confidence}
                blockerCount={run.blockers_json.length}
                effort={`${humanizeLabel(run.analysis_mode)} analysis`}
                statusTone={decisionTone(run.action_label, run.blockers_json.length)}
                primaryAction={
                    run.blockers_json.length ? (
                        <Button size="sm" onClick={() => scrollToStep("preflight-revision")}>
                            Review required fixes
                        </Button>
                    ) : (
                        <Button size="sm" onClick={() => scrollToStep("ready")}>
                            Continue to Ready
                        </Button>
                    )
                }
                secondaryAction={
                    <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => scrollToStep("preflight-evidence")}
                    >
                        Review evidence
                    </Button>
                }
            />
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
            <div id="preflight-evidence" className="scroll-mt-20">
                <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                    <h3 className="text-sm font-semibold text-text-primary">
                        Expected vs observed
                    </h3>
                    <span className="text-xs text-text-secondary">
                        {formatSystemValue(run.brief_alignment_json.coverage ?? {})}
                    </span>
                </div>
                <ExpectedObservedTable
                    rows={requirements.map((requirement) => ({
                        id: requirement.requirement_id,
                        requirement: (
                            <div>
                                <p className="font-medium">
                                    {humanizeLabel(requirement.requirement_id)}
                                </p>
                                <p className="mt-1 text-xs text-text-secondary">
                                    {formatSystemValue(requirement.expected)}
                                </p>
                            </div>
                        ),
                        observed: (
                            <div>
                                <p>{formatSystemValue(requirement.observed)}</p>
                                <p className="mt-1 text-xs text-text-secondary">
                                    {requirement.reason}
                                </p>
                            </div>
                        ),
                        status: requirement.status,
                        confidence: requirement.confidence,
                        evidence: requirement.evidence_ids.length
                            ? `${requirement.evidence_ids.length} evidence ${
                                  requirement.evidence_ids.length === 1 ? "item" : "items"
                              }`
                            : "No evidence linked",
                    }))}
                />
            </div>
            <Fixes blockers={run.blockers_json} fixes={run.fixes_json} />
            <div id="preflight-revision" className="scroll-mt-20 rounded-2xl bg-info-soft p-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                    <div>
                        <h3 className="text-sm font-semibold text-text-primary">
                            Creator revision message
                        </h3>
                        <p className="mt-1 text-xs text-text-secondary">
                            Edit the message before sharing it with the creator.
                        </p>
                    </div>
                    <StatusChip tone={revisionSaved ? "ok" : "neutral"}>
                        {revisionSaved ? "Saved locally" : "Unsaved"}
                    </StatusChip>
                </div>
                <Textarea
                    aria-label="Creator revision message"
                    className="mt-3 min-h-28 bg-surface"
                    value={revisionDraft}
                    onChange={(event) => onRevisionChange(event.target.value)}
                />
                <div className="mt-3 flex flex-wrap gap-2">
                    <Button size="sm" onClick={onRevisionSave}>
                        Save message
                    </Button>
                    <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => {
                            void navigator.clipboard.writeText(revisionDraft);
                            toast.success("Revision message copied");
                        }}
                    >
                        <Clipboard className="h-4 w-4" />
                        Copy message
                    </Button>
                </div>
            </div>
            <div className="rounded-2xl bg-surface-soft p-3 text-sm text-text-primary">
                Spark or paid usage remains pending until creator rights and authorization are
                confirmed.
            </div>
        </div>
    );
}

function CampaignBriefEditor({
    value,
    onChange,
}: {
    value: string;
    onChange: (value: string) => void;
}) {
    let brief: CampaignPackBrief;
    try {
        brief = JSON.parse(value) as CampaignPackBrief;
    } catch {
        return (
            <div className="rounded-2xl bg-destructive-soft p-4 text-sm text-destructive">
                Restore valid JSON in Advanced JSON to continue editing the Campaign Pack.
            </div>
        );
    }

    const identity = getRecordValue(brief.product_snapshot, "identity");
    const productName =
        getRecordValue(identity, "name") ??
        getRecordValue(brief.product_snapshot, "name") ??
        getRecordValue(brief.product_snapshot, "product_name");

    function updateField(section: keyof CampaignPackBrief, field: string, nextValue: string) {
        const currentSection = brief[section];
        const nextSection =
            currentSection && typeof currentSection === "object" && !Array.isArray(currentSection)
                ? { ...(currentSection as Record<string, unknown>), [field]: nextValue }
                : { [field]: nextValue };
        onChange(JSON.stringify({ ...brief, [section]: nextSection }, null, 2));
    }

    return (
        <div className="rounded-2xl bg-primary-soft/35 p-4 sm:p-5">
            <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                <div>
                    <p className="text-[10px] font-semibold uppercase text-primary">
                        Structured Campaign Pack
                    </p>
                    <h3 className="mt-1 text-base font-semibold text-text-primary">
                        {formatSystemValue(productName, "Campaign Pack")}
                    </h3>
                </div>
                <StatusChip tone="ok" dot>
                    Ready to review
                </StatusChip>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
                <BriefEditField
                    label="Objective"
                    value={getRecordValue(brief.objective, "objective_type")}
                    onChange={(nextValue) => updateField("objective", "objective_type", nextValue)}
                />
                <BriefEditField
                    label="Primary action"
                    value={getRecordValue(brief.objective, "primary_action")}
                    onChange={(nextValue) => updateField("objective", "primary_action", nextValue)}
                />
                <BriefEditField
                    label="Audience"
                    value={getRecordValue(brief.audience, "persona_label")}
                    onChange={(nextValue) => updateField("audience", "persona_label", nextValue)}
                />
                <BriefEditField
                    label="Awareness stage"
                    value={getRecordValue(brief.audience, "awareness_stage")}
                    onChange={(nextValue) => updateField("audience", "awareness_stage", nextValue)}
                />
                <BriefEditField
                    label="Angle"
                    value={getRecordValue(brief.angle, "name")}
                    onChange={(nextValue) => updateField("angle", "name", nextValue)}
                />
                <BriefEditField
                    label="Promise"
                    value={getRecordValue(brief.angle, "promise")}
                    onChange={(nextValue) => updateField("angle", "promise", nextValue)}
                />
                <BriefEditField
                    label="Mechanism"
                    value={getRecordValue(brief.angle, "mechanism")}
                    onChange={(nextValue) => updateField("angle", "mechanism", nextValue)}
                />
                <BriefEditField
                    label="Emotional driver"
                    value={getRecordValue(brief.angle, "emotional_driver")}
                    onChange={(nextValue) => updateField("angle", "emotional_driver", nextValue)}
                />
                <BriefEditField
                    label="CTA spoken"
                    value={getRecordValue(brief.cta, "spoken")}
                    onChange={(nextValue) => updateField("cta", "spoken", nextValue)}
                />
                <BriefEditField
                    label="CTA overlay"
                    value={getRecordValue(brief.cta, "overlay")}
                    onChange={(nextValue) => updateField("cta", "overlay", nextValue)}
                />
            </div>

            <div className="mt-5 grid gap-4 md:grid-cols-2">
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

function BriefEditField({
    label,
    value,
    onChange,
}: {
    label: string;
    value: unknown;
    onChange: (value: string) => void;
}) {
    return (
        <label className="grid gap-1.5 text-xs font-medium text-text-secondary">
            {label}
            <Input
                value={formatSystemValue(value, "")}
                onChange={(event) => onChange(event.target.value)}
            />
        </label>
    );
}

function BriefField({ title, value }: { title: string; value: unknown }) {
    return (
        <div className="rounded-md border border-hairline bg-surface p-3">
            <p className="text-xs font-semibold uppercase text-text-tertiary">{title}</p>
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

function campaignBriefDraftError(value: string) {
    try {
        parseCampaignBriefDraft(value);
        return null;
    } catch (error) {
        return error instanceof Error ? error.message : "Campaign Pack brief is invalid.";
    }
}
