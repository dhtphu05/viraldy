import { useMutation, useQuery } from "@tanstack/react-query";
import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { ArrowLeft, CheckCircle2, FileVideo, Loader2, Package, Sparkles, X } from "lucide-react";
import { useEffect, useMemo, useRef, useState, type DragEvent } from "react";
import { ViraldyIcon } from "@/shared/ui/viraldy-icon";

import { ScorerErrorState, ScorerLoadingState } from "../components/scorer-route-state";
import { useScorerWorkspace } from "../hooks/use-scorer-workspace";
import { validateScoreDraft, validateVideoFile } from "../lib/tiktok-score-view-model";
import type { IntendedUse, ScoreMode, ScoreProfileCode, TikTokScoreProfile } from "../types";
import { listProducts } from "@/shared/api/products";
import { queryKeys } from "@/shared/api/query-keys";
import {
    createTikTokScore,
    listCreativeDirections,
    listTikTokScoreProfiles,
} from "@/shared/api/tiktok-scores";
import { uploadAsset } from "@/shared/api/uploads";
import { Alert, AlertDescription, AlertTitle } from "@/shared/ui/alert";
import { Button } from "@/shared/ui/button";
import { Label } from "@/shared/ui/label";
import { PageHeader } from "@/shared/ui/page-header";
import { Progress } from "@/shared/ui/progress";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/shared/ui/select";
import { StatusChip } from "@/shared/ui/status-chip";
import { SurfaceCard } from "@/shared/ui/surface-card";
import { AppShell } from "@/widgets/app-shell/app-shell";

export const Route = createFileRoute("/tiktok-scorer/new")({
    head: () => ({ meta: [{ title: "Score a video — TikTok Scorer — Viraldy" }] }),
    component: TikTokScorerNewRoute,
});

const CANONICAL_PROFILES: TikTokScoreProfile[] = [
    ["general_tiktok_v1", "General TikTok"],
    ["product_led_demo_v1", "Product-led demo"],
    ["creator_review_v1", "Creator review"],
    ["story_led_pov_v1", "Story-led POV"],
    ["tutorial_howto_v1", "Tutorial / how-to"],
    ["unboxing_reaction_v1", "Unboxing / reaction"],
    ["comment_reply_faq_v1", "Comment reply / FAQ"],
    ["offer_led_shop_v1", "Offer-led TikTok Shop"],
].map(([code, label]) => ({
    code: code as ScoreProfileCode,
    label,
    version: 1,
    description: "",
    isDefault: code === "general_tiktok_v1",
    suggested: false,
    suggestionConfidence: null,
    suggestionReason: null,
}));

function TikTokScorerNewRoute() {
    const navigate = useNavigate();
    const { workspaceId, workspaces } = useScorerWorkspace();
    const products = useQuery({
        queryKey: queryKeys.products.list(workspaceId),
        queryFn: () => listProducts(workspaceId!),
        enabled: Boolean(workspaceId),
        retry: 1,
    });
    const profiles = useQuery({
        queryKey: queryKeys.tiktokScores.profiles(workspaceId),
        queryFn: () => listTikTokScoreProfiles(workspaceId!),
        enabled: Boolean(workspaceId),
        retry: 1,
    });
    const directions = useQuery({
        queryKey: ["creative-directions", workspaceId],
        queryFn: () => listCreativeDirections(workspaceId!),
        enabled: Boolean(workspaceId),
        retry: 0,
    });
    const availableProfiles = profiles.data?.length ? profiles.data : CANONICAL_PROFILES;
    const serverSuggestedProfile = availableProfiles.find((profile) => profile.suggested) ?? null;
    const hasServerSuggestedProfile = Boolean(serverSuggestedProfile);
    const [file, setFile] = useState<File | null>(null);
    const [durationSeconds, setDurationSeconds] = useState<number | null>(null);
    const [fileError, setFileError] = useState<string | null>(null);
    const [mode, setMode] = useState<ScoreMode>("quick");
    const [productId, setProductId] = useState<string | null>(null);
    const [intendedUse, setIntendedUse] = useState<IntendedUse>("tiktok_organic");
    const [profile, setProfile] = useState<ScoreProfileCode>("general_tiktok_v1");
    const [profileChanged, setProfileChanged] = useState(false);
    const [directionContextId, setDirectionContextId] = useState<string | null>(null);
    const [uploadProgress, setUploadProgress] = useState(0);
    const [errors, setErrors] = useState<Record<string, string>>({});
    const abortRef = useRef<AbortController | null>(null);
    const idempotencyRef = useRef<string | null>(null);
    const uploadedAssetRef = useRef<Awaited<ReturnType<typeof uploadAsset>> | null>(null);
    const suggestedProfile = useMemo(() => {
        if (serverSuggestedProfile) return serverSuggestedProfile;
        const suggestedCode: ScoreProfileCode =
            intendedUse === "tiktok_shop_affiliate"
                ? "offer_led_shop_v1"
                : mode === "product_aware"
                  ? "product_led_demo_v1"
                  : intendedUse === "ugc_paid_candidate" || intendedUse === "spark_candidate"
                    ? "creator_review_v1"
                    : "general_tiktok_v1";
        const candidate = availableProfiles.find((item) => item.code === suggestedCode);
        if (!candidate) return null;
        return {
            ...candidate,
            suggested: true,
            suggestionConfidence: 0.35,
            suggestionReason:
                "Low-confidence starting suggestion based only on the selected mode and intended use. The video has not been analyzed yet.",
        };
    }, [availableProfiles, intendedUse, mode, serverSuggestedProfile]);

    useEffect(() => {
        if (suggestedProfile && !profileChanged) setProfile(suggestedProfile.code);
    }, [profileChanged, suggestedProfile]);

    const selectedProfile = availableProfiles.find((item) => item.code === profile);
    const selectedProduct = products.data?.find((item) => item.id === productId) ?? null;
    const selectedDirection = directions.data?.find((item) => item.id === directionContextId);
    const directionWarning = useMemo(() => {
        if (!selectedDirection) return null;
        if (selectedDirection.status === "archived") return "This Creative Direction is archived.";
        if (productId && selectedDirection.productId !== productId) {
            return "This Creative Direction belongs to a different product and cannot be attached.";
        }
        return null;
    }, [productId, selectedDirection]);

    const createScore = useMutation({
        mutationFn: async () => {
            if (!workspaceId || !file) throw new Error("Choose a workspace and video first.");
            const idempotencyKey = idempotencyRef.current ?? crypto.randomUUID();
            idempotencyRef.current = idempotencyKey;
            const controller = new AbortController();
            abortRef.current = controller;
            setUploadProgress(1);
            const uploaded =
                uploadedAssetRef.current ??
                (await uploadAsset(
                    workspaceId,
                    file,
                    productId ?? undefined,
                    setUploadProgress,
                    "ugc",
                    controller.signal,
                ));
            uploadedAssetRef.current = uploaded;
            const result = await createTikTokScore(workspaceId, {
                assetId: uploaded.id,
                assetVersionId: uploaded.asset_version_id,
                productId,
                mode,
                intendedUse,
                profile,
                profileSelectionMode:
                    hasServerSuggestedProfile && suggestedProfile?.code === profile
                        ? "model_suggested_user_confirmed"
                        : profileChanged
                          ? "user_overridden"
                          : "user_selected",
                profileSelectionConfidence:
                    suggestedProfile?.code === profile
                        ? suggestedProfile.suggestionConfidence
                        : null,
                creativeDirectionContextId: directionWarning ? null : directionContextId,
                idempotencyKey,
            });
            return result;
        },
        onSuccess: (result) => {
            void navigate({
                to: "/tiktok-scorer/$scoreId",
                params: { scoreId: result.run.id },
                search: { jobId: result.jobId ?? undefined },
            });
        },
        onSettled: () => {
            abortRef.current = null;
        },
    });

    async function chooseFile(nextFile: File | null) {
        idempotencyRef.current = null;
        uploadedAssetRef.current = null;
        setFile(null);
        setDurationSeconds(null);
        if (!nextFile) return;
        const immediateError = validateVideoFile(nextFile, null);
        if (immediateError) {
            setFileError(immediateError);
            return;
        }
        const duration = await readVideoDuration(nextFile);
        const validationError = validateVideoFile(nextFile, duration);
        setFileError(validationError);
        if (!validationError) {
            setFile(nextFile);
            setDurationSeconds(duration);
        }
    }

    function submit() {
        const nextErrors: Record<string, string> = validateScoreDraft({
            fileSelected: Boolean(file),
            mode,
            productId,
            intendedUse,
            profile,
        });
        if (fileError) nextErrors.file = fileError;
        if (directionWarning && directionContextId) nextErrors.direction = directionWarning;
        setErrors(nextErrors);
        if (Object.keys(nextErrors).length === 0) createScore.mutate();
    }

    if (workspaces.isLoading) {
        return (
            <AppShell>
                <ScorerLoadingState label="Loading your workspace" />
            </AppShell>
        );
    }
    if (workspaces.isError) {
        return (
            <AppShell>
                <ScorerErrorState
                    error={workspaces.error}
                    onRetry={() => void workspaces.refetch()}
                    resource="Workspace"
                />
            </AppShell>
        );
    }

    return (
        <AppShell>
            <div className="mx-auto flex max-w-5xl flex-col gap-6">
                <div>
                    <Button asChild variant="ghost" size="sm">
                        <Link to="/tiktok-scorer">
                            <ArrowLeft className="h-4 w-4" />
                            Score history
                        </Link>
                    </Button>
                </div>
                <PageHeader
                    title="Score a video"
                    description="Create an immutable video version, choose the diagnostic context, and start a real workspace analysis."
                />

                <SurfaceCard padding="lg">
                    <StepHeading
                        step="1"
                        title="Upload video"
                        description="MP4 or QuickTime, up to 250 MB and 3 minutes."
                    />
                    <label
                        onDragOver={(event) => event.preventDefault()}
                        onDrop={(event: DragEvent<HTMLLabelElement>) => {
                            event.preventDefault();
                            void chooseFile(event.dataTransfer.files[0] ?? null);
                        }}
                        className="mt-4 flex min-h-48 cursor-pointer flex-col items-center justify-center rounded-2xl border border-dashed border-control-border bg-surface-soft px-6 text-center transition-colors hover:border-primary/50 focus-within:ring-2 focus-within:ring-ring"
                    >
                        <input
                            className="sr-only"
                            type="file"
                            accept="video/mp4,video/quicktime,.mp4,.mov"
                            onChange={(event) => void chooseFile(event.target.files?.[0] ?? null)}
                        />
                        {file ? (
                            <>
                                <CheckCircle2 className="h-8 w-8 text-ok" />
                                <p className="mt-3 font-medium text-text-primary">{file.name}</p>
                                <p className="mt-1 text-sm text-text-secondary">
                                    {formatBytes(file.size)}
                                    {durationSeconds !== null
                                        ? ` · ${formatDuration(durationSeconds)}`
                                        : " · duration verified after upload"}
                                </p>
                            </>
                        ) : (
                            <>
                                <ViraldyIcon name="uploadVideo" size="2xl" />
                                <p className="mt-3 font-medium text-text-primary">
                                    Drop a video here or choose a file
                                </p>
                                <p className="mt-1 text-sm text-text-secondary">
                                    The uploaded media is stored as an immutable UGC asset version.
                                </p>
                            </>
                        )}
                    </label>
                    {(fileError || errors.file) && (
                        <p role="alert" className="mt-2 text-sm text-destructive">
                            {fileError ?? errors.file}
                        </p>
                    )}
                </SurfaceCard>

                <SurfaceCard padding="lg">
                    <StepHeading
                        step="2"
                        title="Choose analysis context"
                        description="Only Product-Aware Score requires a product."
                    />
                    <div className="mt-4 grid gap-3 md:grid-cols-3">
                        <ModeCard
                            active={mode === "quick"}
                            title="Quick Score"
                            description="Structural diagnostics without requiring Product Context."
                            onClick={() => {
                                setMode("quick");
                                idempotencyRef.current = null;
                            }}
                        />
                        <ModeCard
                            active={mode === "product_aware"}
                            title="Product-Aware Score"
                            description="Adds verified product, offer, claim, and disclosure checks."
                            onClick={() => {
                                setMode("product_aware");
                                idempotencyRef.current = null;
                            }}
                        />
                        <ModeCard
                            active={mode === "usage_aware"}
                            title="Usage-Aware Score"
                            description="Keeps creative structure separate from paid-use rights readiness."
                            onClick={() => {
                                setMode("usage_aware");
                                idempotencyRef.current = null;
                            }}
                        />
                    </div>
                    <div className="mt-5 grid gap-4 md:grid-cols-2">
                        <Field
                            label={
                                mode === "product_aware"
                                    ? "Product (required)"
                                    : "Product (optional)"
                            }
                            error={errors.productId}
                        >
                            <Select
                                value={productId ?? "none"}
                                onValueChange={(value) => {
                                    setProductId(value === "none" ? null : value);
                                    setDirectionContextId(null);
                                    idempotencyRef.current = null;
                                    uploadedAssetRef.current = null;
                                }}
                            >
                                <SelectTrigger>
                                    <SelectValue placeholder="No product" />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="none">No product</SelectItem>
                                    {products.data?.map((product) => (
                                        <SelectItem key={product.id} value={product.id}>
                                            {product.name}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </Field>
                        <Field label="Intended use" error={errors.intendedUse}>
                            <Select
                                value={intendedUse}
                                onValueChange={(value) => {
                                    setIntendedUse(value as IntendedUse);
                                    idempotencyRef.current = null;
                                }}
                            >
                                <SelectTrigger>
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="tiktok_organic">TikTok organic</SelectItem>
                                    <SelectItem value="tiktok_shop_affiliate">
                                        TikTok Shop affiliate
                                    </SelectItem>
                                    <SelectItem value="ugc_paid_candidate">
                                        UGC paid candidate
                                    </SelectItem>
                                    <SelectItem value="spark_candidate">Spark candidate</SelectItem>
                                </SelectContent>
                            </Select>
                        </Field>
                    </div>
                </SurfaceCard>

                <SurfaceCard padding="lg">
                    <StepHeading
                        step="3"
                        title="Set the content profile"
                        description="Profile choice changes contextual expectations; it does not predict performance."
                    />
                    <div className="mt-4 grid gap-4 md:grid-cols-2">
                        <Field label="Content profile" error={errors.profile}>
                            <Select
                                value={profile}
                                onValueChange={(value) => {
                                    setProfile(value as ScoreProfileCode);
                                    setProfileChanged(true);
                                    idempotencyRef.current = null;
                                }}
                            >
                                <SelectTrigger>
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    {availableProfiles.map((item) => (
                                        <SelectItem key={item.code} value={item.code}>
                                            {item.label}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </Field>
                        <div className="rounded-xl bg-info-soft p-4 text-sm text-text-secondary">
                            <div className="flex flex-wrap items-center gap-2">
                                <Sparkles className="h-4 w-4 text-info" />
                                <p className="font-medium text-text-primary">
                                    {suggestedProfile?.code === profile
                                        ? hasServerSuggestedProfile
                                            ? "Suggested profile"
                                            : "Settings-based starting suggestion"
                                        : "Selected profile"}
                                </p>
                                {suggestedProfile?.code === profile &&
                                    suggestedProfile.suggestionConfidence !== null && (
                                        <StatusChip tone="info">
                                            {Math.round(
                                                suggestedProfile.suggestionConfidence * 100,
                                            )}
                                            % confidence
                                        </StatusChip>
                                    )}
                            </div>
                            <p className="mt-2">
                                {(suggestedProfile?.code === profile
                                    ? suggestedProfile.suggestionReason
                                    : null) ||
                                    selectedProfile?.suggestionReason ||
                                    selectedProfile?.description ||
                                    "Use General TikTok when no server-side profile suggestion is available, or override it with the format you intentionally made."}
                            </p>
                            {profiles.isError && (
                                <p className="mt-2 text-warn">
                                    Live profile descriptions are unavailable. Canonical profile
                                    selection remains available.
                                </p>
                            )}
                        </div>
                    </div>
                </SurfaceCard>

                <SurfaceCard padding="lg">
                    <StepHeading
                        step="4"
                        title="Use a Creative Direction (optional)"
                        description="A compatible selected direction can improve how fixes are executed. It never changes this score."
                    />
                    {directions.isError ? (
                        <Alert className="mt-4">
                            <AlertTitle>Creative Directions unavailable</AlertTitle>
                            <AlertDescription>
                                The core score can still run normally. Try again later if you want
                                optional direction-based upgrades.
                            </AlertDescription>
                        </Alert>
                    ) : (
                        <div className="mt-4">
                            <Select
                                value={directionContextId ?? "none"}
                                onValueChange={(value) => {
                                    setDirectionContextId(value === "none" ? null : value);
                                    idempotencyRef.current = null;
                                }}
                            >
                                <SelectTrigger aria-label="Use a Creative Direction">
                                    <SelectValue placeholder="Do not use a Creative Direction" />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="none">
                                        Do not use a Creative Direction
                                    </SelectItem>
                                    {directions.data
                                        ?.filter((direction) => direction.selectedConceptId)
                                        .map((direction) => (
                                            <SelectItem key={direction.id} value={direction.id}>
                                                {direction.name} · v{direction.version}
                                            </SelectItem>
                                        ))}
                                </SelectContent>
                            </Select>
                            {(directionWarning || errors.direction) && (
                                <p role="alert" className="mt-2 text-sm text-warn">
                                    {directionWarning ?? errors.direction}
                                </p>
                            )}
                        </div>
                    )}
                </SurfaceCard>

                <SurfaceCard padding="lg" highlight>
                    <StepHeading
                        step="5"
                        title="Review and submit"
                        description="Viraldy will use server evidence and deterministic scoring. It will not predict virality, sales, GMV, CTR, CVR, or ROAS."
                    />
                    <dl className="mt-4 grid gap-3 rounded-2xl bg-surface-soft p-4 text-sm sm:grid-cols-2 lg:grid-cols-4">
                        <ReviewItem
                            label="Video"
                            value={file?.name ?? "Not selected"}
                            icon={FileVideo}
                        />
                        <ReviewItem label="Mode" value={humanize(mode)} icon={Sparkles} />
                        <ReviewItem
                            label="Product"
                            value={selectedProduct?.name ?? "No product"}
                            icon={Package}
                        />
                        <ReviewItem
                            label="Profile"
                            value={selectedProfile?.label ?? humanize(profile)}
                            icon={Sparkles}
                        />
                    </dl>
                    {createScore.isPending && (
                        <div className="mt-4" role="status" aria-live="polite">
                            <div className="mb-2 flex items-center justify-between text-sm">
                                <span>
                                    {uploadProgress < 100
                                        ? "Uploading immutable video version"
                                        : "Starting scorer job"}
                                </span>
                                <span>{uploadProgress}%</span>
                            </div>
                            <Progress value={uploadProgress} />
                        </div>
                    )}
                    {createScore.isError && (
                        <Alert variant="destructive" className="mt-4">
                            <AlertTitle>Score could not start</AlertTitle>
                            <AlertDescription>
                                {createScore.error instanceof Error
                                    ? createScore.error.message
                                    : "Try again. The same idempotency key will prevent a duplicate run."}
                            </AlertDescription>
                        </Alert>
                    )}
                    <div className="mt-5 flex flex-wrap justify-end gap-2">
                        {createScore.isPending && uploadProgress < 100 && (
                            <Button
                                type="button"
                                variant="secondary"
                                onClick={() => abortRef.current?.abort()}
                            >
                                <X className="h-4 w-4" />
                                Cancel upload
                            </Button>
                        )}
                        <Button
                            type="button"
                            onClick={submit}
                            disabled={createScore.isPending || !workspaceId}
                        >
                            {createScore.isPending ? (
                                <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                                <Sparkles className="h-4 w-4" />
                            )}
                            {createScore.isPending ? "Starting analysis" : "Score this video"}
                        </Button>
                    </div>
                </SurfaceCard>
            </div>
        </AppShell>
    );
}

function StepHeading({
    step,
    title,
    description,
}: {
    step: string;
    title: string;
    description: string;
}) {
    return (
        <div className="flex gap-3">
            <span className="grid h-7 w-7 shrink-0 place-items-center rounded-full bg-primary text-xs font-semibold text-primary-foreground">
                {step}
            </span>
            <div>
                <h2 className="font-semibold text-text-primary">{title}</h2>
                <p className="mt-0.5 text-sm text-text-secondary">{description}</p>
            </div>
        </div>
    );
}
function ModeCard({
    active,
    title,
    description,
    onClick,
}: {
    active: boolean;
    title: string;
    description: string;
    onClick: () => void;
}) {
    return (
        <button
            type="button"
            aria-pressed={active}
            onClick={onClick}
            className={`rounded-2xl border p-4 text-left transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${active ? "border-primary bg-primary-softer" : "border-control-border bg-surface hover:bg-surface-soft"}`}
        >
            <p className="font-medium text-text-primary">{title}</p>
            <p className="mt-1 text-sm text-text-secondary">{description}</p>
        </button>
    );
}
function Field({
    label,
    error,
    children,
}: {
    label: string;
    error?: string;
    children: React.ReactNode;
}) {
    return (
        <div>
            <Label>{label}</Label>
            <div className="mt-2">{children}</div>
            {error && (
                <p role="alert" className="mt-1 text-sm text-destructive">
                    {error}
                </p>
            )}
        </div>
    );
}
function ReviewItem({
    label,
    value,
    icon: Icon,
}: {
    label: string;
    value: string;
    icon: typeof FileVideo;
}) {
    return (
        <div className="min-w-0">
            <dt className="flex items-center gap-1.5 text-xs text-text-tertiary">
                <Icon className="h-3.5 w-3.5" />
                {label}
            </dt>
            <dd className="mt-1 truncate font-medium text-text-primary">{value}</dd>
        </div>
    );
}
function humanize(value: string) {
    return value
        .replace(/_v\d+$/, "")
        .replace(/_/g, " ")
        .replace(/\b\w/g, (letter) => letter.toUpperCase());
}
function formatBytes(bytes: number) {
    return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}
function formatDuration(seconds: number) {
    const minutes = Math.floor(seconds / 60);
    return `${minutes}:${String(Math.round(seconds % 60)).padStart(2, "0")}`;
}
function readVideoDuration(file: File): Promise<number | null> {
    return new Promise((resolve) => {
        const video = document.createElement("video");
        const url = URL.createObjectURL(file);
        const finish = (value: number | null) => {
            URL.revokeObjectURL(url);
            video.removeAttribute("src");
            resolve(value);
        };
        video.preload = "metadata";
        video.onloadedmetadata = () =>
            finish(Number.isFinite(video.duration) ? video.duration : null);
        video.onerror = () => finish(null);
        video.src = url;
    });
}
