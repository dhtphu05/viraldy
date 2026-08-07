import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
    AlertTriangle,
    CheckCircle2,
    Clipboard,
    Download,
    FileVideo,
    Library,
    Loader2,
    PackageOpen,
    Play,
    Sparkles,
} from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import type { ComponentType, ReactNode } from "react";
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
import { formatSystemValue, humanizeLabel, humanizeSystemText } from "@/shared/lib/display";
import { scrollElementIntoView } from "@/shared/lib/scroll";
import { ActionTray } from "@/shared/ui/action-tray";
import { DecisionHero } from "@/shared/ui/decision-hero";
import { ExpectedObservedTable } from "@/shared/ui/expected-observed-table";
import { Input } from "@/shared/ui/input";
import { ValueReceipt } from "@/shared/ui/value-receipt";
import { AnalysisThinkingSkeleton } from "@/shared/ui/analysis-thinking-skeleton";
import { EmptyState } from "@/shared/ui/empty-state";
import { Skeleton } from "@/shared/ui/skeleton";
import type { WorkflowRailStep } from "@/shared/ui/workflow-rail";
import { JobProgress } from "@/features/mvp-flow/components/job-progress";
import { PatternKitResult } from "@/features/mvp-flow/components/pattern-kit-result";
import { ProductionRunHeader } from "@/features/mvp-flow/components/production-run-header";
import { ProductionRunRail } from "@/features/mvp-flow/components/production-run-rail";
import { ViralKitResult } from "@/features/mvp-flow/components/viral-kit-result";
import { seedProducts } from "@/features/products/data/products";
import { useAppStore } from "@/app/store/app-store";
import {
    deriveProductionRunPhases,
    missingProductionContext,
    resolveProductionAssetId,
    successfulJobOutputId,
    type ProductionEntryType,
    type ProductionPhaseId,
} from "@/features/mvp-flow/lib/production-run-state";
import {
    demoCreativeSourceUrl,
    findImportedProduct,
    findImportedReference,
} from "@/features/mvp-flow/lib/production-run-handoff";
import { createCampaignHandoff } from "@/features/mvp-flow/lib/campaign-handoff";
import { assetDisplayName } from "@/features/mvp-flow/lib/asset-presentation";
import {
    toClaimInsights,
    toMechanismInsights,
    toRiskInsights,
    type DnaInsight,
} from "@/features/mvp-flow/lib/dna-presentation";
import type { SeedProduct } from "@/features/creative-library/types/creative";
import type {
    PatternKitDetail,
    PreflightPresentation,
    ViralKitDetail,
} from "@/features/mvp-flow/intelligence-types";

export const Route = createFileRoute("/mvp")({
    head: () => ({ meta: [{ title: "Production Run - Viraldy" }] }),
    validateSearch: (search: Record<string, unknown>): MvpSearch => ({
        quickRunId: optionalSearchString(search.quickRunId),
        quickJobId: optionalSearchString(search.quickJobId),
        dnaId: optionalSearchString(search.dnaId),
        dnaJobId: optionalSearchString(search.dnaJobId),
        patternKitId: optionalSearchString(search.patternKitId),
        viralKitId: optionalSearchString(search.viralKitId),
        adaptationId: optionalSearchString(search.adaptationId),
        packId: optionalSearchString(search.packId),
        campaignId: optionalSearchString(search.campaignId),
        preflightRunId: optionalSearchString(search.preflightRunId),
        preflightJobId: optionalSearchString(search.preflightJobId),
        entryType: productionEntryType(search.entryType),
        productId: optionalSearchString(search.productId),
        localProductId: optionalSearchString(search.localProductId),
        primaryReferenceId: optionalSearchString(search.primaryReferenceId),
        sourceCreativeId: optionalSearchString(search.sourceCreativeId),
        quickAssetId: optionalSearchString(search.quickAssetId),
        ugcAssetId: optionalSearchString(search.ugcAssetId),
        objective: optionalSearchString(search.objective),
        market: optionalSearchString(search.market),
        buyerPersona: optionalSearchString(search.buyerPersona),
        buyerPain: optionalSearchString(search.buyerPain),
        desiredOutcome: optionalSearchString(search.desiredOutcome),
        selectedConceptId: optionalSearchString(search.selectedConceptId),
        conceptConfirmed: optionalSearchString(search.conceptConfirmed),
    }),
    component: ProductionRunRoute,
});

type MvpSearch = {
    quickRunId?: string;
    quickJobId?: string;
    dnaId?: string;
    dnaJobId?: string;
    patternKitId?: string;
    viralKitId?: string;
    adaptationId?: string;
    packId?: string;
    campaignId?: string;
    preflightRunId?: string;
    preflightJobId?: string;
    entryType?: ProductionEntryType;
    productId?: string;
    localProductId?: string;
    primaryReferenceId?: string;
    sourceCreativeId?: string;
    quickAssetId?: string;
    ugcAssetId?: string;
    objective?: string;
    market?: string;
    buyerPersona?: string;
    buyerPain?: string;
    desiredOutcome?: string;
    selectedConceptId?: string;
    conceptConfirmed?: string;
};

type Workspace = { id: string; name: string };
type Product = {
    id: string;
    name: string;
    market: string | null;
    external_source: string | null;
    external_id: string | null;
    metadata_json: Record<string, unknown>;
    product_context_version: number;
    product_context: {
        identity?: { name?: string; category?: string; market?: string };
        personas?: Array<{ id: string; label: string }>;
        creative?: { creator_personas?: string[] };
        commercial?: { product_tag_required?: boolean; offer?: unknown };
    };
};
type Board = { id: string; name: string };
type Reference = {
    id: string;
    title: string;
    asset_id: string;
    status: string;
    source_url?: string | null;
};
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
type ViralKitCampaignPackResponse = {
    concept_id: string;
    campaign_pack_id: string;
    campaign_pack_version_id: string;
    campaign_pack: CampaignPack;
};
type CampaignPackExport = {
    filename: string;
    content_type: string;
    content: string;
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
    seller_summary_json?: PreflightPresentation["seller_summary"] | null;
    creator_revision_json?: PreflightPresentation["creator_revision"];
    presentation_source_json?: PreflightPresentation["sources"];
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
const activeJobToastIds = new Set<string>();

function optionalSearchString(value: unknown) {
    return typeof value === "string" && value.length > 0 ? value : undefined;
}

function productionEntryType(value: unknown): ProductionEntryType | undefined {
    return value === "reference-first" || value === "product-first" ? value : undefined;
}

function compactSearch(search: MvpSearch): MvpSearch {
    return Object.fromEntries(
        Object.entries(search).filter(([, value]) => value !== undefined && value !== ""),
    ) as MvpSearch;
}

function hasText(value: string | undefined) {
    return Boolean(value?.trim());
}

function defaultBuyerPersona(product: Product | undefined) {
    return product?.product_context.personas?.[0]?.id;
}

function buyerPersonaLabel(product: Product | undefined, buyerPersona: string | undefined) {
    if (!buyerPersona) return "target buyer";
    return (
        product?.product_context.personas?.find((persona) => persona.id === buyerPersona)?.label ??
        buyerPersona
    );
}

function defaultBuyerPain(product: Product | undefined, buyerPersona: string | undefined) {
    const productName = product?.name ?? "this product";
    const persona = buyerPersonaLabel(product, buyerPersona);
    return `${persona} needs a clearer reason to trust and choose ${productName} quickly.`;
}

function defaultDesiredOutcome(product: Product | undefined, buyerPersona: string | undefined) {
    const productName = product?.name ?? "this product";
    const persona = buyerPersonaLabel(product, buyerPersona);
    return `${persona} understands why ${productName} is relevant and feels ready to take the next step.`;
}

function productionContextAutofill(
    product: Product | undefined,
    current: Pick<MvpSearch, "buyerPersona" | "buyerPain" | "desiredOutcome">,
): Pick<MvpSearch, "buyerPersona" | "buyerPain" | "desiredOutcome"> {
    const buyerPersona = hasText(current.buyerPersona)
        ? current.buyerPersona
        : defaultBuyerPersona(product);
    return {
        buyerPersona,
        buyerPain: hasText(current.buyerPain)
            ? current.buyerPain
            : defaultBuyerPain(product, buyerPersona),
        desiredOutcome: hasText(current.desiredOutcome)
            ? current.desiredOutcome
            : defaultDesiredOutcome(product, buyerPersona),
    };
}

function ProductionRunRoute() {
    const queryClient = useQueryClient();
    const search = Route.useSearch();
    const navigate = useNavigate();
    const quickRunId = search.quickRunId ?? null;
    const quickJobId = search.quickJobId ?? null;
    const dnaId = search.dnaId ?? null;
    const dnaJobId = search.dnaJobId ?? null;
    const patternKitId = search.patternKitId ?? null;
    const viralKitId = search.viralKitId ?? null;
    const packId = search.packId ?? null;
    const preflightRunId = search.preflightRunId ?? null;
    const preflightJobId = search.preflightJobId ?? null;
    const [uploadState, setUploadState] = useState<UploadState>({
        status: "idle",
        progress: 0,
    });
    const [briefDraft, setBriefDraft] = useState("");
    const [draftVersionId, setDraftVersionId] = useState<string | null>(null);
    const [revisionDraft, setRevisionDraft] = useState("");
    const [revisionSaved, setRevisionSaved] = useState(false);
    const [revisionRunId, setRevisionRunId] = useState<string | null>(null);
    const productImportAttempt = useRef<string | null>(null);
    const referenceImportAttempt = useRef<string | null>(null);
    const presentationAttempt = useRef<string | null>(null);
    const previousActivePhase = useRef<ProductionPhaseId | null>(null);
    const backendConfigured = hasConfiguredApiBaseUrl;
    const localProduct = seedProducts.find((item) => item.id === search.localProductId);
    const sourceCreative = useAppStore((state) =>
        state.creatives.find((creative) => creative.id === search.sourceCreativeId),
    );
    const createFrontendCampaign = useAppStore((state) => state.createCampaignPack);

    const updateWorkflowSearch = useCallback(
        (updates: Partial<MvpSearch>) => {
            void navigate({
                to: "/mvp",
                replace: true,
                search: compactSearch({ ...search, ...updates }),
            });
        },
        [navigate, search],
    );

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

    const importProduct = useMutation({
        mutationFn: (seed: SeedProduct) =>
            apiPost<Product>(`/workspaces/${workspaceId}/products`, {
                name: seed.name,
                description: `${seed.category} product prepared from the Viraldy catalog for a production run.`,
                market: search.market ?? "US",
                external_source: "frontend_demo",
                external_id: seed.id,
                metadata_json: {
                    frontend_seed_id: seed.id,
                    category: seed.category,
                    price: seed.price,
                    readiness: seed.readiness,
                    fulfillment_risk: seed.fulfillmentRisk,
                },
            }),
        onSuccess: (created) => {
            queryClient.setQueryData<Product[]>(
                queryKeys.products.list(workspaceId),
                (current = []) => [...current, created],
            );
            updateWorkflowSearch({
                productId: created.id,
                localProductId: undefined,
                market: search.market ?? created.market ?? "US",
            });
            toast.success("Product context connected");
        },
        onError: (error) =>
            toast.error("Product context could not be connected", {
                description:
                    error instanceof Error ? error.message : "Retry by reopening Production Run.",
            }),
    });

    const importReference = useMutation({
        mutationFn: async () => {
            if (!workspaceId || !sourceCreative?.mediaUrl || !product) {
                throw new Error(
                    "This creative has no transferable media. Select a workspace reference instead.",
                );
            }

            const response = await fetch(sourceCreative.mediaUrl);
            if (!response.ok) throw new Error("The selected creative media could not be loaded.");
            const blob = await response.blob();
            const filename = mediaFilename(sourceCreative.mediaUrl, sourceCreative.id, blob.type);
            const file = new File([blob], filename, {
                type: blob.type || "video/mp4",
            });
            const asset = await uploadAsset(workspaceId, file, product.id, undefined, "reference");
            const board =
                boards.data?.find((item) => item.name === "Production Run imports") ??
                (await apiPost<Board>(`/workspaces/${workspaceId}/reference-boards`, {
                    name: "Production Run imports",
                    description: "Creative Library media connected to a production run.",
                    product_id: product.id,
                    board_type: "creative_research",
                }));
            const created = await apiPost<Reference>(`/workspaces/${workspaceId}/references`, {
                board_id: board.id,
                asset_id: asset.id,
                product_id: product.id,
                source_platform: sourceCreative.platform.toLowerCase().replaceAll(" ", "_"),
                source_url: demoCreativeSourceUrl(sourceCreative.id),
                title: sourceCreative.title,
                notes: "Imported from the frontend Creative Library handoff.",
            });
            return { asset, board, reference: created };
        },
        onSuccess: ({ asset, board, reference: created }) => {
            queryClient.setQueryData<Asset[]>(queryKeys.assets.list(workspaceId), (current = []) =>
                current.some((item) => item.id === asset.id) ? current : [...current, asset],
            );
            queryClient.setQueryData<Board[]>(
                queryKeys.referenceBoards.list(workspaceId),
                (current = []) =>
                    current.some((item) => item.id === board.id) ? current : [...current, board],
            );
            queryClient.setQueryData<Reference[]>(
                queryKeys.references.list(workspaceId),
                (current = []) => [...current, created],
            );
            updateWorkflowSearch({
                primaryReferenceId: created.id,
                quickAssetId: asset.id,
                sourceCreativeId: undefined,
            });
            toast.success("Creative reference connected");
        },
        onError: (error) =>
            toast.error("Creative reference needs attention", {
                description:
                    error instanceof Error
                        ? error.message
                        : "Select a workspace reference to continue.",
            }),
    });

    const product = products.data?.find((item) => item.id === search.productId);
    const reference = references.data?.find((item) => item.id === search.primaryReferenceId);
    const quickAssetId = resolveProductionAssetId({
        selectedAssetId: search.quickAssetId,
        uploadedAssetId: reference?.asset_id,
    });
    const quickAsset = assets.data?.find((asset) => asset.id === quickAssetId);
    const ugcAsset = assets.data?.find((asset) => asset.id === search.ugcAssetId);
    const selectedConceptId = search.selectedConceptId ?? "";
    const conceptConfirmed = search.conceptConfirmed === "true";

    useEffect(() => {
        const localProductId = search.localProductId;
        if (!localProductId || !workspaceId || !products.data || importProduct.isPending) return;

        if (!localProduct) {
            if (productImportAttempt.current === localProductId) return;
            productImportAttempt.current = localProductId;
            toast.error("The selected catalog product is no longer available.");
            updateWorkflowSearch({ localProductId: undefined });
            return;
        }

        const existing = findImportedProduct(products.data, localProduct);
        if (existing) {
            updateWorkflowSearch({
                productId: existing.id,
                localProductId: undefined,
                market: search.market ?? existing.market ?? "US",
            });
            return;
        }

        if (productImportAttempt.current === localProductId) return;
        productImportAttempt.current = localProductId;
        importProduct.mutate(localProduct);
    }, [
        importProduct,
        localProduct,
        products.data,
        search.localProductId,
        search.market,
        updateWorkflowSearch,
        workspaceId,
    ]);

    useEffect(() => {
        const sourceCreativeId = search.sourceCreativeId;
        if (
            !sourceCreativeId ||
            !workspaceId ||
            !product ||
            !references.data ||
            importReference.isPending
        ) {
            return;
        }

        const existing = findImportedReference(references.data, sourceCreativeId);
        if (existing) {
            updateWorkflowSearch({
                primaryReferenceId: existing.id,
                quickAssetId: existing.asset_id,
                sourceCreativeId: undefined,
            });
            return;
        }

        if (referenceImportAttempt.current === sourceCreativeId) return;
        referenceImportAttempt.current = sourceCreativeId;
        importReference.mutate();
    }, [
        importReference,
        product,
        references.data,
        search.sourceCreativeId,
        updateWorkflowSearch,
        workspaceId,
    ]);

    const quickJob = useJob(workspaceId, quickJobId);
    const dnaJob = useJob(workspaceId, dnaJobId);
    const preflightJob = useJob(workspaceId, preflightJobId);
    useJobLifecycleToast(
        quickJob.data,
        quickJobId,
        "Reference structure check",
        "Reference structure check ready",
    );
    useJobLifecycleToast(dnaJob.data, dnaJobId, "Creative DNA analysis", "Creative DNA ready");
    useJobLifecycleToast(
        preflightJob.data,
        preflightJobId,
        "Creator draft review",
        "Creator draft decision ready",
    );
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
    const patternKit = useQuery({
        queryKey: queryKeys.patternKits.detail(workspaceId, patternKitId),
        queryFn: () =>
            apiGet<PatternKitDetail>(`/workspaces/${workspaceId}/pattern-kits/${patternKitId}`),
        enabled: !!workspaceId && !!patternKitId,
    });
    const viralKit = useQuery({
        queryKey: queryKeys.viralKits.detail(workspaceId, viralKitId),
        queryFn: () =>
            apiGet<ViralKitDetail>(`/workspaces/${workspaceId}/viral-kits/${viralKitId}`),
        enabled: !!workspaceId && !!viralKitId,
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
        setRevisionDraft(
            preflight.data.creator_revision_json?.message ?? preflight.data.revision_message,
        );
        setRevisionSaved(false);
        setRevisionRunId(preflight.data.id);
    }, [preflight.data, revisionRunId]);

    const completedDnaId = successfulJobOutputId(dnaJob.data, "creative_dna_version_id");

    useEffect(() => {
        if (!completedDnaId || completedDnaId === dnaId) return;
        updateWorkflowSearch({ dnaId: completedDnaId });
    }, [completedDnaId, dnaId, updateWorkflowSearch]);

    const runQuick = useMutation({
        mutationFn: async () => {
            const response = await apiPost<{ score_run: ScoreRun; job: JobResponse }>(
                `/workspaces/${workspaceId}/tiktok-scores`,
                {
                    asset_id: quickAsset?.id,
                    product_id: product?.id ?? null,
                    objective: search.objective,
                },
            );
            updateWorkflowSearch({
                quickRunId: response.score_run.id,
                quickJobId: response.job.id,
            });
            return response;
        },
        onSuccess: (response) =>
            startJobToast("reference-score", response.job.id, "Reference structure check started"),
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
        onSuccess: (response) =>
            startJobToast("creative-dna", response.job.id, "Creative DNA analysis started"),
        onError: (error) =>
            toast.error(error instanceof Error ? error.message : "Reference analysis failed"),
    });

    const createPatternKit = useMutation({
        mutationFn: async () =>
            apiPost<PatternKitDetail>(`/workspaces/${workspaceId}/pattern-kits`, {
                name: `${product?.name ?? "Product"} demonstration pattern`,
                kind: "single_asset_abstraction",
                scope: "workspace_private",
                source_creative_dna_version_ids: [dnaId],
                primary_category:
                    product?.product_context.identity?.category ?? "uncategorized_product",
                target_platforms: ["tiktok_shop"],
                target_markets: [
                    product?.product_context.identity?.market ?? product?.market ?? "US",
                ],
                objectives: [search.objective],
                extraction_mode: "ai_assisted",
            }),
        onSuccess: (created) => {
            updateWorkflowSearch({
                patternKitId: created.kit.id,
                viralKitId: undefined,
                packId: undefined,
                campaignId: undefined,
            });
            toast.success("Reusable pattern ready");
        },
        onError: (error) =>
            toast.error(
                error instanceof Error ? error.message : "Reusable pattern could not be created",
            ),
    });

    const createViralKit = useMutation({
        mutationFn: async () =>
            apiPost<ViralKitDetail>(`/workspaces/${workspaceId}/viral-kits`, {
                product_id: product?.id,
                expected_product_context_version: product?.product_context_version,
                pattern_kit_version_ids: [patternKit.data?.latest_version.id],
                objective: search.objective,
                platform: "tiktok_shop",
                target_market: search.market,
                buyer_persona_id: search.buyerPersona,
                creator_constraints: {
                    allowed_personas: product?.product_context.creative?.creator_personas ?? [],
                    disallowed_personas: [],
                    delivery_style_preferences: [],
                },
                production_constraints: {
                    max_duration_ms: 30000,
                    required_aspect_ratio: "9:16",
                    raw_footage_required: true,
                    concept_preview_requested: false,
                },
                commercial_constraints: {
                    offer_required: Boolean(product?.product_context.commercial?.offer),
                    product_tag_required:
                        product?.product_context.commercial?.product_tag_required ?? true,
                    shipping_claim_policy: "use_product_context_only",
                },
                applicability_override_reason:
                    "User confirmed this PatternKit inside the MVP Product Run workflow.",
                concept_count: 3,
            }),
        onSuccess: (created) => {
            updateWorkflowSearch({
                viralKitId: created.kit.id,
                adaptationId: undefined,
                packId: undefined,
                campaignId: undefined,
                selectedConceptId: undefined,
                conceptConfirmed: undefined,
                preflightRunId: undefined,
                preflightJobId: undefined,
            });
            toast.success("Three product-specific concepts ready");
        },
        onError: (error) =>
            toast.error(
                error instanceof Error
                    ? error.message
                    : "Product-specific concepts could not be created",
            ),
    });

    const createPack = useMutation({
        mutationFn: async () => {
            await apiPost(`/workspaces/${workspaceId}/viral-kits/${viralKitId}/concept-actions`, {
                concept_id: selectedConceptId,
                action: "selected",
                reason: "Selected in the connected Production Run workflow.",
            });
            return apiPost<ViralKitCampaignPackResponse>(
                `/workspaces/${workspaceId}/viral-kits/${viralKitId}/concepts/${selectedConceptId}/campaign-pack`,
                { rights_note: null },
            );
        },
        onSuccess: (created) => {
            const concept = viralKit.data?.latest_version.viral_kit.concepts.find(
                (item) => item.id === selectedConceptId,
            );
            let campaignId: string | undefined;
            if (product && concept) {
                const instructions =
                    patternKit.data?.latest_version.pattern.adaptation_instructions ?? [];
                const handoff = createCampaignHandoff({
                    backendPackId: created.campaign_pack_id,
                    product: {
                        id: product.id,
                        name: product.name,
                        frontendSeedId: product.external_id ?? undefined,
                    },
                    concept,
                    referenceCreativeId: reference?.source_url?.startsWith(
                        "viraldy://creative-library/",
                    )
                        ? reference.source_url.split("/").pop()
                        : undefined,
                    objective: search.objective,
                    market: search.market,
                    buyerPersona: search.buyerPersona,
                    buyerPain: search.buyerPain,
                    desiredOutcome: search.desiredOutcome,
                    sourceHook: observedText(dna.data?.dna_json.opening?.hook_text, ""),
                    sourceAngle: observedText(dna.data?.dna_json.narrative?.structure, ""),
                    sourceDemo: observedText(dna.data?.dna_json.demo?.demo_type, ""),
                    keep: instructions
                        .filter((item) => item.instruction_type === "keep")
                        .map((item) => item.instruction),
                    change: instructions
                        .filter((item) => item.instruction_type === "change")
                        .map((item) => item.instruction),
                    avoid: instructions
                        .filter((item) => item.instruction_type === "avoid")
                        .map((item) => item.instruction),
                    now: new Date().toISOString(),
                });
                createFrontendCampaign(handoff);
                campaignId = handoff.campaignId;
            }
            updateWorkflowSearch({
                packId: created.campaign_pack_id,
                campaignId,
            });
            setBriefDraft(
                JSON.stringify(created.campaign_pack.current_version?.brief_json ?? {}, null, 2),
            );
            setDraftVersionId(created.campaign_pack.current_version?.id ?? null);
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

    const exportPack = useMutation({
        mutationFn: async () =>
            apiPost<CampaignPackExport>(
                `/workspaces/${workspaceId}/campaign-packs/${packId}/exports`,
                { format: "text" },
            ),
        onSuccess: (result) => {
            const blob = new Blob([result.content], { type: result.content_type });
            const url = URL.createObjectURL(blob);
            const anchor = document.createElement("a");
            anchor.href = url;
            anchor.download = result.filename;
            anchor.click();
            URL.revokeObjectURL(url);
            toast.success("Campaign Pack exported");
        },
        onError: (error) =>
            toast.error(
                error instanceof Error ? error.message : "Campaign Pack could not be exported",
            ),
    });

    const runPreflight = useMutation({
        mutationFn: async () => {
            const versionId = pack.data?.current_version_id;
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
        onSuccess: (response) =>
            startJobToast("creator-review", response.job.id, "Creator draft review started"),
        onError: (error) =>
            toast.error(error instanceof Error ? error.message : "UGC Preflight could not start"),
    });

    const generatePresentation = useMutation({
        mutationFn: async () =>
            apiPost<PreflightPresentation>(
                `/workspaces/${workspaceId}/preflight-runs/${preflightRunId}/presentation`,
                { seller_locale: "en-US", force_regenerate: false },
            ),
        onSuccess: (result) => {
            if (result.creator_revision) {
                setRevisionDraft(result.creator_revision.message);
                setRevisionSaved(false);
            }
            queryClient.invalidateQueries({
                queryKey: queryKeys.preflightRuns.detail(workspaceId, preflightRunId),
            });
            toast.success("Seller decision and creator message generated");
        },
        onError: (error) =>
            toast.error(
                error instanceof Error
                    ? error.message
                    : "Friendly presentation could not be generated",
            ),
    });

    useEffect(() => {
        const run = preflight.data;
        if (
            !run ||
            run.status !== "completed" ||
            run.seller_summary_json ||
            generatePresentation.data ||
            generatePresentation.isPending ||
            presentationAttempt.current === run.id
        ) {
            return;
        }
        presentationAttempt.current = run.id;
        generatePresentation.mutate();
    }, [generatePresentation, preflight.data]);

    const productionContext = {
        entryType: search.entryType,
        productId: search.productId,
        primaryReferenceId: search.primaryReferenceId,
        objective: search.objective,
        market: search.market,
        buyerPersona: search.buyerPersona,
        buyerPain: search.buyerPain,
        desiredOutcome: search.desiredOutcome,
    };
    const contextMissing = missingProductionContext(productionContext);
    const quickReason = disabledReason([
        [!workspaceId, "Connect a workspace before scoring a reference."],
        [!quickAsset, "Select or upload a reference video before scoring."],
        [runQuick.isPending, "Reference scoring is already running."],
    ]);
    const referenceReason = disabledReason([
        [contextMissing.length > 0, contextMissing[0] ?? "Complete production context first."],
        [!reference, "Select a primary reference first."],
        [analyzeReference.isPending, "Reference analysis is already queued."],
    ]);
    const patternKitReason = disabledReason([
        [!dnaId, "Finish Creative DNA before extracting a reusable pattern."],
        [!product, "Select a product before creating a reusable pattern."],
        [createPatternKit.isPending, "Reusable pattern extraction is already running."],
    ]);
    const viralKitReason = disabledReason([
        [
            !patternKit.data?.latest_version.id,
            "Create a reusable pattern before generating product concepts.",
        ],
        [!product, "Select a product before generating product concepts."],
        [createViralKit.isPending, "Product concept generation is already running."],
    ]);
    const createPackReason = disabledReason([
        [!viralKitId, "Generate product concepts before selecting a production direction."],
        [!selectedConceptId, "Select one concept before creating the brief."],
        [!conceptConfirmed, "Confirm the selected concept before creating the brief."],
        [createPack.isPending, "Campaign brief creation is already running."],
    ]);
    const briefDraftError = briefDraft ? campaignBriefDraftError(briefDraft) : null;
    const savePackReason = disabledReason([
        [!packId, "Create a campaign brief before saving a new version."],
        [!briefDraft, "Brief JSON is empty."],
        [Boolean(briefDraftError), briefDraftError ?? "Campaign Pack brief is invalid."],
        [savePackVersion.isPending, "A new Campaign Pack version is already being saved."],
    ]);
    const exportPackReason = disabledReason([
        [!packId, "Create a Campaign Pack before exporting it."],
        [exportPack.isPending, "Campaign Pack export is already running."],
    ]);
    const preflightReason = disabledReason([
        [!ugcAsset, "Select or upload a creator video before review."],
        [!pack.data?.current_version_id, "Create or load a campaign brief before reviewing UGC."],
        [runPreflight.isPending, "Creator video review is already running."],
    ]);
    const presentationReason = disabledReason([
        [preflight.data?.status !== "completed", "Complete Preflight before generating decisions."],
        [
            generatePresentation.isPending,
            "Seller and creator presentation is already being generated.",
        ],
    ]);
    const workflowLoading =
        backendConfigured &&
        (aiReadiness.isLoading ||
            workspaces.isLoading ||
            products.isLoading ||
            assets.isLoading ||
            boards.isLoading ||
            references.isLoading ||
            importProduct.isPending ||
            importReference.isPending);
    const runtimeError = backendConfigured
        ? (aiReadiness.error ??
          workspaces.error ??
          products.error ??
          assets.error ??
          boards.error ??
          references.error ??
          importProduct.error ??
          importReference.error ??
          null)
        : null;
    const presentationData =
        generatePresentation.data ??
        (preflight.data?.seller_summary_json
            ? {
                  preflight_run_id: preflight.data.id,
                  seller_summary: preflight.data.seller_summary_json,
                  creator_revision: preflight.data.creator_revision_json ?? null,
                  sources: preflight.data.presentation_source_json ?? {},
                  model_run_ids: [],
              }
            : null);
    const dnaComplete = Boolean(dnaId && dna.data);
    const patternKitComplete = Boolean(patternKitId && patternKit.data);
    const viralKitComplete = Boolean(viralKitId && viralKit.data);
    const packComplete = Boolean(packId && pack.data?.current_version);
    const preflightComplete = Boolean(preflightRunId && preflight.data);
    const presentationComplete = Boolean(presentationData);
    const ready = isPreflightReady(preflight.data);
    const productionPhases = deriveProductionRunPhases({
        context: productionContext,
        dnaId: dnaComplete ? (dnaId ?? undefined) : undefined,
        patternKitId: patternKitComplete ? (patternKitId ?? undefined) : undefined,
        viralKitId: viralKitComplete ? (viralKitId ?? undefined) : undefined,
        selectedConceptId: selectedConceptId || undefined,
        conceptConfirmed,
        packId: packComplete ? (packId ?? undefined) : undefined,
        preflightRunId: preflightComplete ? (preflightRunId ?? undefined) : undefined,
    });
    const activePhase =
        productionPhases.find((phase) => phase.active)?.id ?? ("context" as ProductionPhaseId);

    useEffect(() => {
        if (previousActivePhase.current === null) {
            previousActivePhase.current = activePhase;
            return;
        }
        if (previousActivePhase.current === activePhase) return;
        previousActivePhase.current = activePhase;
        const frame = window.requestAnimationFrame(() => {
            const panel = document.getElementById(activePhase);
            const heading = document.getElementById(`${activePhase}-heading`);
            scrollElementIntoView(panel, { block: "start" });
            heading?.focus({ preventScroll: true });
        });
        return () => window.cancelAnimationFrame(frame);
    }, [activePhase]);

    const workflowSteps: WorkflowRailStep[] = productionPhases.map((phase) => ({
        id: phase.id,
        label: phaseLabel(phase.id),
        state:
            phase.status === "complete"
                ? "complete"
                : phase.status === "locked"
                  ? "future"
                  : phase.status === "stale"
                    ? "blocked"
                    : "current",
        description: phaseDescription(phase.id, phase.status),
        blockedReason:
            phase.status === "stale"
                ? "A dependency changed. Refresh this phase before continuing."
                : undefined,
    }));

    async function handleUpload(file: File | null, target: "reference" | "ugc") {
        if (!file || !workspaceId) return;
        setUploadState({ status: "uploading", progress: 0, filename: file.name });
        try {
            const uploaded = await uploadAsset(
                workspaceId,
                file,
                product?.id,
                (progress) =>
                    setUploadState({ status: "uploading", progress, filename: file.name }),
                target,
            );
            setUploadState({ status: "completed", progress: 100, filename: file.name });
            if (target === "ugc") {
                await queryClient.invalidateQueries({
                    queryKey: queryKeys.assets.list(workspaceId),
                });
                updateWorkflowSearch({
                    ugcAssetId: uploaded.id,
                    preflightRunId: undefined,
                    preflightJobId: undefined,
                });
                toast.success("Upload completed");
                return;
            }

            const board =
                boards.data?.find((item) => item.name === "Production Run uploads") ??
                (await apiPost<Board>(`/workspaces/${workspaceId}/reference-boards`, {
                    name: "Production Run uploads",
                    description: "Reference media uploaded directly in Production Run.",
                    product_id: product?.id ?? null,
                    board_type: "creative_research",
                }));
            const reference = await apiPost<Reference>(`/workspaces/${workspaceId}/references`, {
                board_id: board.id,
                asset_id: uploaded.id,
                product_id: product?.id ?? null,
                source_platform: "uploaded",
                source_url: null,
                title: file.name,
                notes: "Uploaded as the primary reference in Production Run.",
            });
            queryClient.setQueryData<Asset[]>(queryKeys.assets.list(workspaceId), (current = []) =>
                current.some((item) => item.id === uploaded.id) ? current : [...current, uploaded],
            );
            queryClient.setQueryData<Board[]>(
                queryKeys.referenceBoards.list(workspaceId),
                (current = []) =>
                    current.some((item) => item.id === board.id) ? current : [...current, board],
            );
            queryClient.setQueryData<Reference[]>(
                queryKeys.references.list(workspaceId),
                (current = []) => [
                    ...current.filter((item) => item.id !== reference.id),
                    reference,
                ],
            );
            updateWorkflowSearch({
                primaryReferenceId: reference.id,
                quickAssetId: uploaded.id,
                ...productionContextAutofill(product, search),
                quickRunId: undefined,
                quickJobId: undefined,
                dnaId: undefined,
                dnaJobId: undefined,
                patternKitId: undefined,
                viralKitId: undefined,
                selectedConceptId: undefined,
                conceptConfirmed: undefined,
                packId: undefined,
                campaignId: undefined,
                preflightRunId: undefined,
                preflightJobId: undefined,
            });
            toast.success("Primary reference uploaded and selected");
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
                    entryType={search.entryType}
                    runObject={
                        product?.name ??
                        localProduct?.name ??
                        reference?.title ??
                        sourceCreative?.title
                    }
                />

                {!search.entryType ? (
                    <ProductionEntryChooser
                        disabled={!backendConfigured}
                        onChoose={(entryType) =>
                            updateWorkflowSearch({
                                entryType,
                                objective: "tiktok_shop_affiliate_test",
                                market: "US",
                            })
                        }
                    />
                ) : (
                    <>
                        <ProductionRunRail steps={workflowSteps} />
                        <CompletedPhaseSummary
                            phases={productionPhases
                                .filter((phase) => phase.status === "complete")
                                .map((phase) => phase.id)}
                        />

                        <div className="grid min-w-0 gap-5 min-[1500px]:grid-cols-[minmax(0,1fr)_280px] min-[1500px]:items-start">
                            <div className="min-w-0">
                                {activePhase === "context" && (
                                    <ProductionContextPanel
                                        search={search}
                                        products={products.data ?? []}
                                        references={references.data ?? []}
                                        assets={assets.data ?? []}
                                        selectedProduct={product}
                                        quickAsset={quickAsset}
                                        loading={workflowLoading}
                                        missing={contextMissing}
                                        uploadState={uploadState}
                                        uploadDisabled={!workspaceId}
                                        quickReason={quickReason}
                                        referenceReason={referenceReason}
                                        quickPending={runQuick.isPending}
                                        quickJob={quickJob.data}
                                        quickScore={quickScore.data}
                                        quickScoreError={quickScore.error}
                                        handoffLabel={
                                            localProduct?.name ??
                                            sourceCreative?.title ??
                                            product?.name ??
                                            reference?.title
                                        }
                                        handoffPending={
                                            importProduct.isPending || importReference.isPending
                                        }
                                        handoffError={importProduct.error ?? importReference.error}
                                        onChange={updateWorkflowSearch}
                                        onUpload={(file) => handleUpload(file, "reference")}
                                        onQuickScore={() => runQuick.mutate()}
                                        onAnalyze={() => analyzeReference.mutate()}
                                        onRetryQuick={() => void quickScore.refetch()}
                                    />
                                )}

                                {activePhase === "decode" && (
                                    <ActionPanel
                                        id="decode"
                                        eyebrow="Decode"
                                        title="Decide what to keep, change, and avoid"
                                        summary="Viraldy analyzes the selected reference, then extracts a reusable mechanism without treating source wording as reusable."
                                        icon={Sparkles}
                                    >
                                        {!dnaComplete && (
                                            <DisabledActionHint reason={referenceReason}>
                                                <Button
                                                    onClick={() => analyzeReference.mutate()}
                                                    disabled={!!referenceReason}
                                                >
                                                    {analyzeReference.isPending ? (
                                                        <Loader2 className="h-4 w-4 animate-spin" />
                                                    ) : (
                                                        <Play className="h-4 w-4" />
                                                    )}
                                                    {analyzeReference.isPending
                                                        ? "Analyzing Creative DNA..."
                                                        : "Analyze Creative DNA"}
                                                </Button>
                                            </DisabledActionHint>
                                        )}
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
                                        {dnaComplete && !patternKitComplete && (
                                            <div className="border-t border-divider pt-4">
                                                <DisabledActionHint reason={patternKitReason}>
                                                    <Button
                                                        onClick={() => createPatternKit.mutate()}
                                                        disabled={!!patternKitReason}
                                                    >
                                                        {createPatternKit.isPending ? (
                                                            <Loader2 className="h-4 w-4 animate-spin" />
                                                        ) : (
                                                            <Sparkles className="h-4 w-4" />
                                                        )}
                                                        {createPatternKit.isPending
                                                            ? "Extracting reusable pattern..."
                                                            : "Extract reusable pattern"}
                                                    </Button>
                                                </DisabledActionHint>
                                            </div>
                                        )}
                                        {patternKit.isError && (
                                            <WorkflowError
                                                title="Reusable pattern could not be loaded"
                                                error={patternKit.error}
                                                onRetry={() => void patternKit.refetch()}
                                            />
                                        )}
                                    </ActionPanel>
                                )}

                                {activePhase === "adapt" && (
                                    <ActionPanel
                                        id="adapt"
                                        eyebrow="Adapt"
                                        title={`Adapt the pattern to ${product?.name ?? "this product"}`}
                                        summary="Compare product-specific concepts, then explicitly confirm one direction before a Campaign Pack can be created."
                                        icon={Sparkles}
                                    >
                                        {!viralKit.data && patternKit.data && (
                                            <PatternKitResult
                                                detail={patternKit.data}
                                                onContinue={() => createViralKit.mutate()}
                                                continueDisabled={Boolean(viralKitReason)}
                                                continuePending={createViralKit.isPending}
                                            />
                                        )}
                                        {!viralKit.data && !patternKit.data && (
                                            <DisabledActionHint reason={viralKitReason}>
                                                <Button
                                                    onClick={() => createViralKit.mutate()}
                                                    disabled={!!viralKitReason}
                                                >
                                                    {createViralKit.isPending ? (
                                                        <Loader2 className="h-4 w-4 animate-spin" />
                                                    ) : (
                                                        <Play className="h-4 w-4" />
                                                    )}
                                                    {createViralKit.isPending
                                                        ? "Generating product concepts..."
                                                        : "Generate adaptation concepts"}
                                                </Button>
                                            </DisabledActionHint>
                                        )}
                                        {viralKit.isError && (
                                            <WorkflowError
                                                title="Adaptation concepts could not be loaded"
                                                error={viralKit.error}
                                                onRetry={() => void viralKit.refetch()}
                                            />
                                        )}
                                        {viralKit.data && (
                                            <>
                                                <ViralKitResult
                                                    detail={viralKit.data}
                                                    selectedId={selectedConceptId}
                                                    confirmedId={
                                                        conceptConfirmed
                                                            ? selectedConceptId
                                                            : undefined
                                                    }
                                                    onSelect={(conceptId) =>
                                                        updateWorkflowSearch({
                                                            selectedConceptId: conceptId,
                                                            conceptConfirmed: undefined,
                                                            packId: undefined,
                                                            campaignId: undefined,
                                                            preflightRunId: undefined,
                                                            preflightJobId: undefined,
                                                        })
                                                    }
                                                />
                                                <ActionTray
                                                    sticky={false}
                                                    context={
                                                        selectedConceptId
                                                            ? "Confirm this direction to unlock the creator brief."
                                                            : "Select one concept to continue."
                                                    }
                                                    primaryAction={
                                                        <Button
                                                            disabled={!selectedConceptId}
                                                            onClick={() =>
                                                                updateWorkflowSearch({
                                                                    conceptConfirmed: "true",
                                                                })
                                                            }
                                                        >
                                                            Use selected concept
                                                        </Button>
                                                    }
                                                />
                                            </>
                                        )}
                                    </ActionPanel>
                                )}

                                {activePhase === "build" && (
                                    <ActionPanel
                                        id="build"
                                        eyebrow="Build"
                                        title="Create the creator-ready Campaign Pack"
                                        summary="Turn the confirmed concept into structured guidance, requirements, guardrails, and an immutable brief version."
                                        icon={Clipboard}
                                    >
                                        <SelectedConceptSummary
                                            detail={viralKit.data}
                                            conceptId={selectedConceptId}
                                        />
                                        <DisabledActionHint reason={createPackReason}>
                                            <Button
                                                onClick={() => createPack.mutate()}
                                                disabled={!!createPackReason}
                                            >
                                                {createPack.isPending ? (
                                                    <Loader2 className="h-4 w-4 animate-spin" />
                                                ) : (
                                                    <Play className="h-4 w-4" />
                                                )}
                                                {createPack.isPending
                                                    ? "Creating Campaign Pack..."
                                                    : "Create Campaign Pack"}
                                            </Button>
                                        </DisabledActionHint>
                                        {pack.isError && (
                                            <WorkflowError
                                                title="Campaign Pack could not be loaded"
                                                error={pack.error}
                                                onRetry={() => void pack.refetch()}
                                            />
                                        )}
                                    </ActionPanel>
                                )}

                                {activePhase === "review" && (
                                    <div className="flex min-w-0 flex-col gap-5">
                                        <ActionPanel
                                            id="review"
                                            eyebrow="Review"
                                            title="Review the Campaign Pack"
                                            summary="The creator brief is usable now. A creator draft can be added later for evidence-backed preflight."
                                            icon={Clipboard}
                                        >
                                            {pack.data?.current_version && (
                                                <>
                                                    {search.campaignId && (
                                                        <ValueReceipt
                                                            title="Campaign created"
                                                            description={`${product?.name ?? "Product"} Campaign Pack version ${pack.data.current_version.version_number} is saved and ready to review.`}
                                                            items={[
                                                                "Confirmed concept preserved",
                                                                "Creator brief linked",
                                                                "Campaign available directly",
                                                            ]}
                                                            action={
                                                                <Button asChild size="sm">
                                                                    <Link
                                                                        to="/campaigns/$campaignId"
                                                                        params={{
                                                                            campaignId:
                                                                                search.campaignId,
                                                                        }}
                                                                    >
                                                                        Open campaign
                                                                    </Link>
                                                                </Button>
                                                            }
                                                        />
                                                    )}
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
                                                            onChange={(event) =>
                                                                setBriefDraft(event.target.value)
                                                            }
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
                                                        sticky={false}
                                                        context={
                                                            <span>
                                                                Campaign Pack version{" "}
                                                                <strong className="text-text-primary">
                                                                    {
                                                                        pack.data.current_version
                                                                            .version_number
                                                                    }
                                                                </strong>
                                                            </span>
                                                        }
                                                        primaryAction={
                                                            <DisabledActionHint
                                                                reason={savePackReason}
                                                            >
                                                                <Button
                                                                    onClick={() =>
                                                                        savePackVersion.mutate()
                                                                    }
                                                                    disabled={!!savePackReason}
                                                                >
                                                                    <CheckCircle2 className="h-4 w-4" />
                                                                    Save new version
                                                                </Button>
                                                            </DisabledActionHint>
                                                        }
                                                        secondaryAction={
                                                            <DisabledActionHint
                                                                reason={exportPackReason}
                                                            >
                                                                <Button
                                                                    variant="secondary"
                                                                    onClick={() =>
                                                                        exportPack.mutate()
                                                                    }
                                                                    disabled={!!exportPackReason}
                                                                >
                                                                    {exportPack.isPending ? (
                                                                        <Loader2 className="h-4 w-4 animate-spin" />
                                                                    ) : (
                                                                        <Download className="h-4 w-4" />
                                                                    )}
                                                                    {exportPack.isPending
                                                                        ? "Exporting brief..."
                                                                        : "Export brief"}
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
                                            id="ugc-review"
                                            eyebrow="Optional creator review"
                                            title="Validate a creator draft"
                                            summary="Add UGC when it exists. It is not required to create or use the Campaign Pack."
                                            icon={FileVideo}
                                        >
                                            <AssetSelection
                                                assets={assets.data ?? []}
                                                selectedId={search.ugcAssetId}
                                                uploadState={uploadState}
                                                uploadDisabled={!workspaceId}
                                                onSelect={(ugcAssetId) =>
                                                    updateWorkflowSearch({
                                                        ugcAssetId,
                                                        preflightRunId: undefined,
                                                        preflightJobId: undefined,
                                                    })
                                                }
                                                onUpload={(file) => handleUpload(file, "ugc")}
                                            />
                                            <DisabledActionHint reason={preflightReason}>
                                                <Button
                                                    onClick={() => runPreflight.mutate()}
                                                    disabled={!!preflightReason}
                                                >
                                                    {runPreflight.isPending ? (
                                                        <Loader2 className="h-4 w-4 animate-spin" />
                                                    ) : (
                                                        <Play className="h-4 w-4" />
                                                    )}
                                                    {runPreflight.isPending
                                                        ? "Reviewing creator draft..."
                                                        : "Review creator draft"}
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
                                                    title="Creator review could not be loaded"
                                                    error={preflight.error}
                                                    onRetry={() => void preflight.refetch()}
                                                />
                                            )}
                                            {preflight.data?.status === "completed" && (
                                                <PreflightBlock
                                                    run={preflight.data}
                                                    presentation={presentationData}
                                                    presentationReason={presentationReason}
                                                    presentationPending={
                                                        generatePresentation.isPending
                                                    }
                                                    presentationError={generatePresentation.error}
                                                    onGeneratePresentation={() =>
                                                        generatePresentation.mutate()
                                                    }
                                                    revisionDraft={revisionDraft}
                                                    revisionSaved={revisionSaved}
                                                    onRevisionChange={(value) => {
                                                        setRevisionDraft(value);
                                                        setRevisionSaved(false);
                                                    }}
                                                    onRevisionSave={() => {
                                                        setRevisionSaved(true);
                                                        toast.success(
                                                            "Revision message saved locally",
                                                        );
                                                    }}
                                                />
                                            )}
                                            {ready && presentationComplete && (
                                                <ValueReceipt
                                                    title="Creator draft ready"
                                                    description="The draft passed preflight and the seller decision is available."
                                                    items={[
                                                        "Campaign requirements checked",
                                                        "Hard blockers resolved",
                                                        "Seller decision generated",
                                                    ]}
                                                />
                                            )}
                                        </ActionPanel>
                                    </div>
                                )}
                            </div>

                            <ProductionRunContextCard
                                activePhase={activePhase}
                                entryType={search.entryType}
                                product={product}
                                reference={reference}
                                objective={search.objective}
                                market={search.market}
                                ugcAsset={ugcAsset}
                            />
                        </div>
                    </>
                )}
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

function useJobLifecycleToast(
    job: JobResponse | undefined,
    jobId: string | null,
    activeLabel: string,
    completeLabel: string,
) {
    useEffect(() => {
        if (!job || !jobId) return;
        const id = jobToastId(job.job_type, jobId);
        if (["queued", "running", "retrying"].includes(job.status)) {
            activeJobToastIds.add(id);
            toast.loading(job.stage ? `${activeLabel}: ${humanizeLabel(job.stage)}` : activeLabel, {
                id,
                description: `${Math.round(job.progress)}% complete`,
            });
            return;
        }
        if (!activeJobToastIds.has(id)) return;
        activeJobToastIds.delete(id);
        if (job.status === "succeeded" || job.status === "completed") {
            toast.success(completeLabel, {
                id,
                description: "The current phase has been updated with the persisted result.",
            });
            return;
        }
        toast.error(`${activeLabel} could not be completed`, {
            id,
            description:
                job.error_message ??
                "Your current selections are preserved. Retry from the active phase.",
        });
    }, [activeLabel, completeLabel, job, jobId]);
}

function jobToastId(_scope: string, jobId: string) {
    return `viraldy-job-${jobId}`;
}

function startJobToast(scope: string, jobId: string, label: string) {
    const id = jobToastId(scope, jobId);
    activeJobToastIds.add(id);
    toast.loading(label, { id });
}

function disabledReason(entries: Array<[boolean, string]>) {
    return entries.find(([blocked]) => blocked)?.[1] ?? null;
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
            aria-labelledby={id ? `${id}-heading` : undefined}
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
                        <h2
                            id={id ? `${id}-heading` : undefined}
                            tabIndex={id ? -1 : undefined}
                            className="text-base font-semibold text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                        >
                            {title}
                        </h2>
                        {summary && <p className="mt-0.5 text-sm text-text-secondary">{summary}</p>}
                    </div>
                </div>
            </div>
            <div className="flex flex-col gap-4">{children}</div>
        </section>
    );
}

function ProductionEntryChooser({
    disabled,
    onChoose,
}: {
    disabled: boolean;
    onChoose: (entryType: ProductionEntryType) => void;
}) {
    const entries = [
        {
            id: "reference-first" as const,
            icon: Library,
            title: "Start from a winning reference",
            description:
                "Decode a proven creative pattern, then adapt it to a selected product without copying source-specific context.",
            outcome: "Creative DNA, adaptation concepts, and a Campaign Pack",
        },
        {
            id: "product-first" as const,
            icon: PackageOpen,
            title: "Start from a product",
            description:
                "Ground the run in a product and buyer problem, then choose the reference pattern that best fits the test.",
            outcome: "Pattern fit, production concepts, and a Campaign Pack",
        },
    ];
    return (
        <section aria-labelledby="production-entry-heading" className="mx-auto w-full max-w-5xl">
            <div className="mb-5">
                <p className="text-xs font-semibold uppercase text-primary">
                    Choose a starting point
                </p>
                <h2
                    id="production-entry-heading"
                    className="mt-1 text-xl font-semibold text-text-primary"
                >
                    What do you already know?
                </h2>
                <p className="mt-1 text-sm text-text-secondary">
                    Both paths lead to the same five-phase production decision.
                </p>
            </div>
            <div className="grid gap-4 md:grid-cols-2">
                {entries.map((entry) => {
                    const Icon = entry.icon;
                    return (
                        <button
                            key={entry.id}
                            type="button"
                            disabled={disabled}
                            onClick={() => onChoose(entry.id)}
                            className="group min-w-0 rounded-md bg-surface p-5 text-left shadow-soft-card transition-[transform,box-shadow] duration-200 hover:-translate-y-px hover:shadow-hover-card focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-55 sm:p-6"
                        >
                            <span className="grid h-10 w-10 place-items-center rounded-md bg-primary-soft text-primary-active">
                                <Icon className="h-5 w-5" />
                            </span>
                            <h3 className="mt-4 text-base font-semibold text-text-primary">
                                {entry.title}
                            </h3>
                            <p className="mt-2 text-sm leading-6 text-text-secondary">
                                {entry.description}
                            </p>
                            <p className="mt-4 border-t border-divider pt-3 text-xs leading-5 text-text-tertiary">
                                <span className="font-medium text-text-primary">Outcome:</span>{" "}
                                {entry.outcome}
                            </p>
                        </button>
                    );
                })}
            </div>
            {disabled && (
                <p className="mt-4 text-sm text-warn" role="status">
                    Configure the backend connection to start a Production Run.
                </p>
            )}
        </section>
    );
}

function ProductionContextPanel({
    search,
    products,
    references,
    assets,
    selectedProduct,
    quickAsset,
    loading,
    missing,
    uploadState,
    uploadDisabled,
    quickReason,
    referenceReason,
    quickPending,
    quickJob,
    quickScore,
    quickScoreError,
    handoffLabel,
    handoffPending,
    handoffError,
    onChange,
    onUpload,
    onQuickScore,
    onAnalyze,
    onRetryQuick,
}: {
    search: MvpSearch;
    products: Product[];
    references: Reference[];
    assets: Asset[];
    selectedProduct?: Product;
    quickAsset?: Asset;
    loading: boolean;
    missing: string[];
    uploadState: UploadState;
    uploadDisabled: boolean;
    quickReason: string | null;
    referenceReason: string | null;
    quickPending: boolean;
    quickJob?: JobResponse;
    quickScore?: ScoreRun;
    quickScoreError: unknown;
    handoffLabel?: string;
    handoffPending: boolean;
    handoffError: unknown;
    onChange: (updates: Partial<MvpSearch>) => void;
    onUpload: (file: File | null) => void;
    onQuickScore: () => void;
    onAnalyze: () => void;
    onRetryQuick: () => void;
}) {
    const personas = selectedProduct?.product_context.personas ?? [];
    const contextReady = missing.length === 0;
    return (
        <ActionPanel
            id="context"
            eyebrow="Context"
            title="Ground the production decision"
            summary="Select the product, source pattern, buyer, and commercial outcome Viraldy should optimize."
            icon={PackageOpen}
        >
            {(handoffPending || Boolean(handoffError)) && (
                <div
                    className={cn(
                        "rounded-md p-4",
                        handoffError ? "bg-destructive-soft" : "bg-info-soft",
                    )}
                    role="status"
                    aria-live="polite"
                >
                    <div className="flex items-start gap-3">
                        {handoffPending ? (
                            <Loader2 className="mt-0.5 h-4 w-4 shrink-0 animate-spin text-info" />
                        ) : (
                            <PackageOpen className="mt-0.5 h-4 w-4 shrink-0 text-destructive" />
                        )}
                        <div className="min-w-0">
                            <p className="text-sm font-semibold text-text-primary">
                                {handoffPending
                                    ? `Connecting ${handoffLabel ?? "selected context"}`
                                    : "Connected context needs attention"}
                            </p>
                            <p className="mt-1 text-xs leading-5 text-text-secondary">
                                {handoffPending
                                    ? "Viraldy is preserving the selected product and media in this workspace."
                                    : handoffError instanceof Error
                                      ? handoffError.message
                                      : "Select a workspace product and reference to continue."}
                            </p>
                        </div>
                    </div>
                </div>
            )}
            {loading ? (
                <div
                    role="status"
                    aria-live="polite"
                    aria-busy="true"
                    className="grid gap-3 sm:grid-cols-2"
                    aria-label="Loading production context"
                >
                    {Array.from({ length: 6 }).map((_, index) => (
                        <div key={index} className="rounded-md bg-surface-soft p-3">
                            <Skeleton className="h-3 w-20" />
                            <Skeleton className="mt-3 h-4 w-3/4" />
                        </div>
                    ))}
                </div>
            ) : (
                <div className="grid gap-4 sm:grid-cols-2">
                    <ContextSelect
                        label="Product"
                        value={search.productId}
                        placeholder="Select a product"
                        options={products.map((product) => ({
                            value: product.id,
                            label: product.name,
                        }))}
                        onChange={(productId) => {
                            const nextProduct = products.find((item) => item.id === productId);
                            const contextAutofill = productionContextAutofill(nextProduct, search);
                            onChange({
                                productId,
                                market:
                                    search.market ??
                                    nextProduct?.product_context.identity?.market ??
                                    nextProduct?.market ??
                                    undefined,
                                ...contextAutofill,
                                patternKitId: undefined,
                                viralKitId: undefined,
                                selectedConceptId: undefined,
                                conceptConfirmed: undefined,
                                packId: undefined,
                                campaignId: undefined,
                                preflightRunId: undefined,
                                preflightJobId: undefined,
                            });
                        }}
                    />
                    <ContextSelect
                        label="Primary reference"
                        value={search.primaryReferenceId}
                        placeholder="Select a winning reference"
                        options={references.map((reference) => ({
                            value: reference.id,
                            label: reference.title,
                        }))}
                        onChange={(primaryReferenceId) =>
                            onChange({
                                primaryReferenceId,
                                ...productionContextAutofill(selectedProduct, search),
                                quickAssetId: undefined,
                                dnaId: undefined,
                                dnaJobId: undefined,
                                patternKitId: undefined,
                                viralKitId: undefined,
                                selectedConceptId: undefined,
                                conceptConfirmed: undefined,
                                packId: undefined,
                                campaignId: undefined,
                                preflightRunId: undefined,
                                preflightJobId: undefined,
                            })
                        }
                    />
                    <ContextSelect
                        label="Objective"
                        value={search.objective}
                        placeholder="Select an objective"
                        options={[
                            {
                                value: "tiktok_shop_affiliate_test",
                                label: "TikTok Shop affiliate test",
                            },
                            { value: "organic_product_test", label: "Organic product test" },
                            { value: "spark_ads_test", label: "Spark Ads test" },
                        ]}
                        onChange={(objective) =>
                            onChange({
                                objective,
                                viralKitId: undefined,
                                selectedConceptId: undefined,
                                conceptConfirmed: undefined,
                                packId: undefined,
                                campaignId: undefined,
                                preflightRunId: undefined,
                            })
                        }
                    />
                    <ContextSelect
                        label="Market"
                        value={search.market}
                        placeholder="Select a market"
                        options={["US", "UK", "CA", "AU"].map((market) => ({
                            value: market,
                            label: market,
                        }))}
                        onChange={(market) =>
                            onChange({
                                market,
                                viralKitId: undefined,
                                selectedConceptId: undefined,
                                conceptConfirmed: undefined,
                                packId: undefined,
                                campaignId: undefined,
                                preflightRunId: undefined,
                            })
                        }
                    />
                    {personas.length > 0 ? (
                        <ContextSelect
                            label="Buyer persona"
                            value={search.buyerPersona}
                            placeholder="Select a buyer"
                            options={personas.map((persona) => ({
                                value: persona.id,
                                label: persona.label,
                            }))}
                            onChange={(buyerPersona) =>
                                onChange({
                                    ...productionContextAutofill(selectedProduct, {
                                        ...search,
                                        buyerPersona,
                                    }),
                                    viralKitId: undefined,
                                    selectedConceptId: undefined,
                                    conceptConfirmed: undefined,
                                    packId: undefined,
                                    campaignId: undefined,
                                    preflightRunId: undefined,
                                })
                            }
                        />
                    ) : (
                        <ContextInput
                            label="Buyer persona"
                            value={search.buyerPersona}
                            placeholder="Who is this for?"
                            onChange={(buyerPersona) =>
                                onChange({
                                    ...productionContextAutofill(selectedProduct, {
                                        ...search,
                                        buyerPersona,
                                    }),
                                    viralKitId: undefined,
                                    selectedConceptId: undefined,
                                    conceptConfirmed: undefined,
                                    packId: undefined,
                                    campaignId: undefined,
                                    preflightRunId: undefined,
                                })
                            }
                        />
                    )}
                    <ContextInput
                        label="Buyer pain"
                        value={search.buyerPain}
                        placeholder="What are they trying to fix?"
                        onChange={(buyerPain) =>
                            onChange({
                                buyerPain,
                                viralKitId: undefined,
                                conceptConfirmed: undefined,
                                packId: undefined,
                                campaignId: undefined,
                            })
                        }
                    />
                    <ContextInput
                        label="Desired outcome"
                        value={search.desiredOutcome}
                        placeholder="What should change after using the product?"
                        onChange={(desiredOutcome) =>
                            onChange({
                                desiredOutcome,
                                viralKitId: undefined,
                                conceptConfirmed: undefined,
                                packId: undefined,
                                campaignId: undefined,
                            })
                        }
                    />
                    <ContextSelect
                        label="Reference video"
                        value={search.quickAssetId ?? quickAsset?.id}
                        placeholder="Use the selected reference media"
                        options={assets.map((asset) => ({
                            value: asset.id,
                            label: assetTitle(asset),
                        }))}
                        onChange={(quickAssetId) =>
                            onChange({
                                quickAssetId,
                                quickRunId: undefined,
                                quickJobId: undefined,
                            })
                        }
                    />
                </div>
            )}

            <div className="rounded-md border border-dashed border-control-border bg-surface-soft p-4">
                <label
                    htmlFor="production-reference-upload"
                    className="text-sm font-medium text-text-primary"
                >
                    Upload new primary reference
                </label>
                <p className="mt-1 text-xs text-text-secondary">
                    Upload a winning video reference when it is not already in the library. Viraldy
                    will select it as the primary reference for Creative DNA.
                </p>
                <Input
                    id="production-reference-upload"
                    className="mt-3 bg-surface"
                    type="file"
                    accept="video/mp4,video/quicktime,video/webm"
                    disabled={uploadDisabled}
                    onChange={(event) => onUpload(event.target.files?.[0] ?? null)}
                />
                <UploadStatus state={uploadState} />
            </div>

            <div
                className={cn("rounded-md p-4", contextReady ? "bg-ok-soft" : "bg-surface-soft")}
                aria-live="polite"
            >
                <p className="text-sm font-semibold text-text-primary">
                    {contextReady ? "Context ready" : "More context needed"}
                </p>
                <p className="mt-1 text-sm text-text-secondary">
                    {contextReady
                        ? `Enough information to decode this reference for ${selectedProduct?.name ?? "the selected product"}.`
                        : (missing[0] ?? "Complete the required production context.")}
                </p>
                <div className="mt-3">
                    <DisabledActionHint reason={referenceReason}>
                        <Button onClick={onAnalyze} disabled={!!referenceReason}>
                            <Play className="h-4 w-4" />
                            Analyze Creative DNA
                        </Button>
                    </DisabledActionHint>
                </div>
            </div>

            <details className="rounded-md border border-hairline bg-surface p-4">
                <summary className="cursor-pointer text-sm font-medium text-text-primary">
                    Optional structure check
                </summary>
                <div className="mt-4 flex flex-col gap-4">
                    <div className="flex flex-wrap items-center gap-2">
                        <DisabledActionHint reason={quickReason}>
                            <Button
                                variant="secondary"
                                onClick={onQuickScore}
                                disabled={!!quickReason}
                            >
                                {quickPending ? (
                                    <Loader2 className="h-4 w-4 animate-spin" />
                                ) : (
                                    <Play className="h-4 w-4" />
                                )}
                                Score reference structure
                            </Button>
                        </DisabledActionHint>
                        <p className="text-xs text-text-secondary">
                            This does not replace Creative DNA analysis.
                        </p>
                    </div>
                    <JobProgress job={quickJob} />
                    {Boolean(quickScoreError) && (
                        <WorkflowError
                            title="Structure score could not be loaded"
                            error={quickScoreError}
                            onRetry={onRetryQuick}
                        />
                    )}
                    {quickScore?.status === "completed" && <ScoreBlock score={quickScore} />}
                </div>
            </details>
        </ActionPanel>
    );
}

function ContextSelect({
    label,
    value,
    placeholder,
    options,
    onChange,
}: {
    label: string;
    value?: string;
    placeholder: string;
    options: Array<{ value: string; label: string }>;
    onChange: (value: string) => void;
}) {
    const id = `production-${label.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`;
    return (
        <label htmlFor={id} className="grid min-w-0 gap-1.5 text-sm font-medium text-text-primary">
            {label}
            <select
                id={id}
                value={value ?? ""}
                onChange={(event) => onChange(event.target.value)}
                className="h-10 min-w-0 rounded-[10px] border border-control-border bg-surface px-3 text-sm text-text-primary focus:border-primary/50 focus:outline-none focus:ring-2 focus:ring-ring/20"
            >
                <option value="" disabled>
                    {placeholder}
                </option>
                {options.map((option) => (
                    <option key={option.value} value={option.value}>
                        {option.label}
                    </option>
                ))}
            </select>
        </label>
    );
}

function ContextInput({
    label,
    value,
    placeholder,
    onChange,
}: {
    label: string;
    value?: string;
    placeholder: string;
    onChange: (value: string) => void;
}) {
    const id = `production-${label.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`;
    return (
        <label htmlFor={id} className="grid min-w-0 gap-1.5 text-sm font-medium text-text-primary">
            {label}
            <Input
                id={id}
                value={value ?? ""}
                placeholder={placeholder}
                onChange={(event) => onChange(event.target.value)}
            />
        </label>
    );
}

function AssetSelection({
    assets,
    selectedId,
    uploadState,
    uploadDisabled,
    onSelect,
    onUpload,
}: {
    assets: Asset[];
    selectedId?: string;
    uploadState: UploadState;
    uploadDisabled: boolean;
    onSelect: (assetId: string) => void;
    onUpload: (file: File | null) => void;
}) {
    return (
        <div className="grid gap-4 sm:grid-cols-2">
            <ContextSelect
                label="Creator video"
                value={selectedId}
                placeholder="Select a creator draft"
                options={assets.map((asset) => ({ value: asset.id, label: assetTitle(asset) }))}
                onChange={onSelect}
            />
            <label className="grid gap-1.5 text-sm font-medium text-text-primary">
                Upload creator draft
                <Input
                    type="file"
                    accept="video/mp4,video/quicktime,video/webm"
                    disabled={uploadDisabled}
                    onChange={(event) => onUpload(event.target.files?.[0] ?? null)}
                />
            </label>
            <div className="sm:col-span-2">
                <UploadStatus state={uploadState} />
            </div>
        </div>
    );
}

function UploadStatus({ state }: { state: UploadState }) {
    if (state.status === "idle") return null;
    return (
        <div className="mt-3 text-xs text-text-secondary" aria-live="polite">
            {state.status === "uploading" &&
                `Uploading ${state.filename ?? "media"} · ${state.progress}%`}
            {state.status === "completed" && `${state.filename ?? "Media"} uploaded and selected.`}
            {state.status === "failed" && (state.message ?? "Upload failed.")}
        </div>
    );
}

function CompletedPhaseSummary({ phases }: { phases: ProductionPhaseId[] }) {
    if (phases.length === 0) return null;
    return (
        <div className="flex flex-wrap gap-2" aria-label="Completed phases">
            {phases.map((phase) => (
                <StatusChip key={phase} tone="ok" dot>
                    {phaseLabel(phase)} complete
                </StatusChip>
            ))}
        </div>
    );
}

function ProductionRunContextCard({
    activePhase,
    entryType,
    product,
    reference,
    objective,
    market,
    ugcAsset,
}: {
    activePhase: ProductionPhaseId;
    entryType: ProductionEntryType;
    product?: Product;
    reference?: Reference;
    objective?: string;
    market?: string;
    ugcAsset?: Asset;
}) {
    const fields = [
        ["Active phase", phaseLabel(activePhase)],
        ["Entry", entryType === "reference-first" ? "Reference-first" : "Product-first"],
        ["Product", product?.name ?? "Not selected"],
        ["Reference", reference?.title ?? "Not selected"],
        ["Objective", humanizeLabel(objective ?? "not_set")],
        ["Market", market ?? "Not set"],
        ["Creator draft", ugcAsset ? assetTitle(ugcAsset) : "Optional · not added"],
    ];
    const content = (
        <dl className="mt-3 grid gap-3">
            {fields.map(([label, value]) => (
                <div key={label} className="min-w-0">
                    <dt className="text-[10px] font-semibold uppercase text-text-tertiary">
                        {label}
                    </dt>
                    <dd className="mt-0.5 break-words text-sm text-text-primary">{value}</dd>
                </div>
            ))}
        </dl>
    );
    return (
        <aside className="min-w-0 min-[1500px]:sticky min-[1500px]:top-4 min-[1500px]:self-start">
            <details className="rounded-md bg-surface p-4 shadow-soft-card min-[1500px]:hidden">
                <summary className="cursor-pointer text-sm font-semibold text-text-primary">
                    Run context
                </summary>
                {content}
            </details>
            <div className="hidden rounded-md bg-surface p-4 shadow-soft-card min-[1500px]:block">
                <p className="text-sm font-semibold text-text-primary">Run context</p>
                {content}
            </div>
        </aside>
    );
}

function SelectedConceptSummary({
    detail,
    conceptId,
}: {
    detail?: ViralKitDetail;
    conceptId: string;
}) {
    const concept = detail?.latest_version.viral_kit.concepts.find((item) => item.id === conceptId);
    if (!concept) return null;
    return (
        <div className="rounded-md bg-primary-soft/40 p-4">
            <p className="text-xs font-semibold uppercase text-primary">Confirmed direction</p>
            <h3 className="mt-1 text-base font-semibold text-text-primary">{concept.name}</h3>
            <p className="mt-2 text-sm text-text-secondary">
                {humanizeSystemText(concept.test_hypothesis)}
            </p>
        </div>
    );
}

function phaseLabel(id: ProductionPhaseId) {
    switch (id) {
        case "context":
            return "Context";
        case "decode":
            return "Decode";
        case "adapt":
            return "Adapt";
        case "build":
            return "Build";
        case "review":
            return "Review";
    }
}

function phaseDescription(
    id: ProductionPhaseId,
    status: "complete" | "active" | "locked" | "stale",
) {
    if (status === "complete") return "Complete";
    if (status === "stale") return "Refresh required";
    if (status === "locked") {
        switch (id) {
            case "context":
                return "Choose a starting point";
            case "decode":
                return "Needs context";
            case "adapt":
                return "Needs Creative DNA";
            case "build":
                return "Needs confirmed concept";
            case "review":
                return "Needs Campaign Pack";
        }
    }
    switch (id) {
        case "context":
            return "Ground the decision";
        case "decode":
            return "Find reusable mechanics";
        case "adapt":
            return "Choose a product concept";
        case "build":
            return "Create creator guidance";
        case "review":
            return "Use the brief or review UGC";
    }
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
                secondaryAction={
                    <Button asChild size="sm" variant="secondary">
                        <a href="#quick-score-evidence">Review evidence</a>
                    </Button>
                }
            />
            <div id="quick-score-evidence" className="scroll-mt-20 space-y-4">
                <AnalysisStageSummary
                    stages={["Structure checked", "Signals scored", "Fixes prioritized"]}
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
    const mechanisms = toMechanismInsights(data.reusable_mechanisms);
    const claims = toClaimInsights(data.claims);
    const watchOuts: DnaInsight[] = [
        ...toRiskInsights(data.risks),
        ...(data.uncertainties ?? []).map((uncertainty) => ({
            title: uncertainty,
            meta: "Needs verification",
            tone: "warning" as const,
        })),
    ];
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
                secondaryAction={
                    <Button asChild size="sm" variant="secondary">
                        <a href="#dna-evidence">Review extracted DNA</a>
                    </Button>
                }
            />
            <AnalysisStageSummary
                stages={["Opening decoded", "Proof isolated", "Reuse boundaries identified"]}
            />
            <div id="dna-evidence" className="scroll-mt-20">
                <p className="mb-3 text-sm font-semibold text-text-primary">Creative DNA ribbon</p>
                <div className="grid overflow-hidden rounded-2xl bg-surface-soft sm:grid-cols-2 lg:grid-cols-5">
                    <DnaRibbonItem label="Opening" value={observedText(data.opening?.hook_text)} />
                    <DnaRibbonItem
                        label="Product"
                        value={formatObservedTimestamp(data.product?.first_appearance_ms)}
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
                <DnaInsightPanel
                    className="lg:col-span-2"
                    title="What to reuse"
                    items={mechanisms}
                    tone="positive"
                />
                <DnaInsightPanel title="Watch-outs" items={watchOuts} tone="warning" />
                <DnaInsightPanel title="Observed claims" items={claims} tone="neutral" />
            </div>
            <DnaCoverage values={data.completeness ?? {}} />
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

function DnaInsightPanel({
    title,
    items,
    tone,
    className,
}: {
    title: string;
    items: DnaInsight[];
    tone: DnaInsight["tone"];
    className?: string;
}) {
    const Icon =
        tone === "positive" ? CheckCircle2 : tone === "warning" ? AlertTriangle : Clipboard;
    return (
        <section
            className={cn(
                "rounded-md p-4",
                tone === "positive" ? "bg-ok-soft/70" : "bg-surface-soft",
                className,
            )}
        >
            <div className="flex items-center gap-2">
                <Icon
                    className={cn(
                        "h-4 w-4",
                        tone === "positive"
                            ? "text-ok"
                            : tone === "warning"
                              ? "text-warn"
                              : "text-info",
                    )}
                    aria-hidden
                />
                <h3 className="text-sm font-semibold text-text-primary">{title}</h3>
            </div>
            <div className="mt-3 grid gap-3 md:grid-cols-2">
                {items.length ? (
                    items.map((item, index) => (
                        <article key={`${item.title}-${index}`} className="min-w-0">
                            <p className="break-words text-sm font-medium text-text-primary">
                                {item.title}
                            </p>
                            {item.description && (
                                <p className="mt-1 break-words text-sm text-text-secondary">
                                    {item.description}
                                </p>
                            )}
                            {item.meta && (
                                <p className="mt-1 text-xs text-text-tertiary">{item.meta}</p>
                            )}
                        </article>
                    ))
                ) : (
                    <EmptyState
                        compact
                        className="md:col-span-2"
                        title="No supporting evidence was returned"
                        description="The analysis completed without a usable observation for this section. Review the source media or run the analysis again."
                    />
                )}
            </div>
        </section>
    );
}

function DnaCoverage({ values }: { values: Record<string, boolean> }) {
    return (
        <section className="rounded-md bg-surface-soft p-4">
            <h3 className="text-sm font-semibold text-text-primary">Evidence coverage</h3>
            <div className="mt-3 flex flex-wrap gap-2">
                {Object.entries(values).map(([key, complete]) => (
                    <StatusChip key={key} tone={complete ? "ok" : "neutral"}>
                        {humanizeLabel(key)} · {complete ? "Covered" : "Not observed"}
                    </StatusChip>
                ))}
            </div>
        </section>
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

function PreflightBlock({
    run,
    presentation,
    presentationReason,
    presentationPending,
    presentationError,
    onGeneratePresentation,
    revisionDraft,
    revisionSaved,
    onRevisionChange,
    onRevisionSave,
}: {
    run: PreflightRun;
    presentation: PreflightPresentation | null;
    presentationReason: string | null;
    presentationPending: boolean;
    presentationError: unknown;
    onGeneratePresentation: () => void;
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
            <div id="preflight-decision" className="scroll-mt-20">
                {presentation ? (
                    <SellerDecisionBlock presentation={presentation} />
                ) : (
                    <div className="rounded-md border border-hairline bg-primary-soft/35 p-4">
                        <h3 className="text-sm font-semibold text-text-primary">
                            {presentationError
                                ? "Decision view needs attention"
                                : "Preparing seller decision and creator handoff"}
                        </h3>
                        <p className="mt-1 text-sm text-text-secondary">
                            {presentationError instanceof Error
                                ? `${presentationError.message} The completed review is preserved.`
                                : "Viraldy is turning the persisted review into bounded seller and creator language."}
                        </p>
                        {presentationPending ? (
                            <AnalysisThinkingSkeleton
                                compact
                                className="mt-3"
                                title="Preparing the decision view"
                                description="The completed scores and blockers remain unchanged."
                            />
                        ) : presentationError ? (
                            <div className="mt-3">
                                <DisabledActionHint reason={presentationReason}>
                                    <Button
                                        size="sm"
                                        onClick={onGeneratePresentation}
                                        disabled={Boolean(presentationReason)}
                                    >
                                        <Sparkles className="h-4 w-4" />
                                        Retry decision view
                                    </Button>
                                </DisabledActionHint>
                            </div>
                        ) : null}
                    </div>
                )}
            </div>
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
                        <Button asChild size="sm">
                            <a href="#preflight-revision">Review required fixes</a>
                        </Button>
                    ) : (
                        <Button asChild size="sm">
                            <a href="#preflight-evidence">Verify aligned requirements</a>
                        </Button>
                    )
                }
                secondaryAction={
                    <Button asChild size="sm" variant="secondary">
                        <a href="#preflight-evidence">Review evidence</a>
                    </Button>
                }
            />
            <AnalysisStageSummary
                stages={["Structure compared", "Brief matched", "Blockers prioritized"]}
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
            <div className="rounded-2xl bg-surface-soft p-3 text-sm text-text-primary">
                Spark or paid usage remains pending until creator rights and authorization are
                confirmed.
            </div>
        </div>
    );
}

function SellerDecisionBlock({ presentation }: { presentation: PreflightPresentation }) {
    const summary = presentation.seller_summary;
    return (
        <section className="rounded-md border border-hairline bg-primary-soft/35 p-4 sm:p-5">
            <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                    <p className="text-xs font-semibold uppercase text-primary">Seller decision</p>
                    <h3 className="mt-1 text-lg font-semibold text-text-primary">
                        {summary.headline}
                    </h3>
                    <p className="mt-2 text-sm leading-6 text-text-primary">
                        {summary.one_sentence_decision}
                    </p>
                    <p className="mt-1 text-sm leading-6 text-text-secondary">
                        {summary.why_this_matters}
                    </p>
                </div>
                <StatusChip tone="info">{summary.locale}</StatusChip>
            </div>

            <div className="mt-5 grid gap-4 lg:grid-cols-3">
                <DecisionList title="Keep" items={summary.strengths_to_keep} />
                <DecisionList title="Fix" items={summary.blockers_to_fix} />
                <DecisionList title="Do next" items={summary.next_actions} />
            </div>

            <div className="mt-4 border-t border-divider pt-3 text-xs leading-5 text-text-secondary">
                <p>{summary.confidence_explanation}</p>
                <p className="mt-1 font-medium text-text-primary">{summary.commercial_guardrail}</p>
            </div>
        </section>
    );
}

function DecisionList({ title, items }: { title: string; items: string[] }) {
    return (
        <div>
            <h4 className="text-xs font-semibold uppercase text-text-tertiary">{title}</h4>
            {items.length ? (
                <ul className="mt-2 space-y-2 text-sm leading-5 text-text-primary">
                    {items.map((item) => (
                        <li key={item}>{item}</li>
                    ))}
                </ul>
            ) : (
                <p className="mt-2 text-sm text-text-secondary">None identified.</p>
            )}
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
            <div
                role="status"
                aria-live="polite"
                aria-busy="true"
                aria-label="Loading Campaign Pack version history"
                className="rounded-md bg-surface-soft p-3"
            >
                <Skeleton className="h-4 w-32" />
                <div className="mt-3 grid gap-2">
                    <div className="rounded-md bg-surface p-3">
                        <Skeleton className="h-4 w-24" />
                        <Skeleton className="mt-2 h-3 w-3/5" />
                    </div>
                    <div className="rounded-md bg-surface p-3">
                        <Skeleton className="h-4 w-20" />
                        <Skeleton className="mt-2 h-3 w-2/5" />
                    </div>
                </div>
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
                                    ? "Generated provenance"
                                    : "Manual provenance"}
                            </div>
                        </div>
                    ))
                ) : (
                    <EmptyState
                        compact
                        title="No saved versions yet"
                        description="Save the current Campaign Pack to create a reviewable version history."
                    />
                )}
            </div>
        </div>
    );
}

function AnalysisStageSummary({ stages }: { stages: string[] }) {
    return (
        <section aria-label="Completed analysis stages" className="rounded-md bg-surface-soft p-3">
            <div className="flex flex-wrap gap-2">
                {stages.map((stage) => (
                    <span
                        key={stage}
                        className="inline-flex items-center gap-1.5 rounded-full bg-ok-soft px-2.5 py-1 text-xs font-medium text-ok"
                    >
                        <CheckCircle2 className="h-3.5 w-3.5" aria-hidden />
                        {stage}
                    </span>
                ))}
            </div>
            <p className="mt-2 text-xs text-text-tertiary">
                Exact timestamps appear only when the analysis returns time-linked evidence.
            </p>
        </section>
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
                    <EmptyState
                        compact
                        className="md:col-span-2"
                        title="No measurable signals were returned"
                        description="The analysis needs clearer media evidence before it can score this dimension."
                    />
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

function formatObservedTimestamp(value: unknown) {
    const observed = isObservedValue(value) ? value.value : value;
    const milliseconds =
        typeof observed === "number" ? observed : Number.parseFloat(String(observed));
    if (!Number.isFinite(milliseconds)) return "Reveal time not observed";
    return `${Math.max(0, milliseconds / 1000).toFixed(1)}s reveal`;
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

function mediaFilename(mediaUrl: string, creativeId: string, mimeType: string) {
    const pathName = mediaUrl.split("?")[0]?.split("/").pop();
    if (pathName?.includes(".")) return pathName;
    const extension = mimeType.includes("quicktime")
        ? "mov"
        : mimeType.includes("webm")
          ? "webm"
          : "mp4";
    return `${creativeId}.${extension}`;
}

function assetTitle(asset: Asset | undefined, fallback = "No video selected") {
    return assetDisplayName(asset, fallback);
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
