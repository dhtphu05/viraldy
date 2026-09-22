import { useMutation } from "@tanstack/react-query";
import { useNavigate } from "@tanstack/react-router";
import { ChevronDown, FileVideo2, Loader2, Sparkles, X } from "lucide-react";
import { useEffect, useRef, useState, type DragEvent, type FormEvent } from "react";

import { useUgcWorkspace } from "../hooks/use-ugc-workspace";
import type {
    MaterialConnection,
    UgcCommerceDomain,
    UgcIntendedUse,
    UgcReviewContext,
} from "../types/ugc-review";
import { createUgcReview, validateUgcVideo } from "@/shared/api/ugc-reviews";
import { uploadAsset } from "@/shared/api/uploads";
import { Alert, AlertDescription, AlertTitle } from "@/shared/ui/alert";
import { Button } from "@/shared/ui/button";
import { Input } from "@/shared/ui/input";
import { Label } from "@/shared/ui/label";
import { PageHeader } from "@/shared/ui/page-header";
import { Progress } from "@/shared/ui/progress";
import { ViraldyIcon } from "@/shared/ui/viraldy-icon";
import { StatusChip } from "@/shared/ui/status-chip";
import { SurfaceCard } from "@/shared/ui/surface-card";
import { Textarea } from "@/shared/ui/textarea";

const INITIAL_CONTEXT: UgcReviewContext = {
    market: "US",
    platform: "tiktok_shop",
    commerceDomain: "generic",
    intendedUse: "unknown",
    materialConnection: "unknown",
};

export function UgcReviewForm({ preferredWorkspaceId }: { preferredWorkspaceId?: string }) {
    const navigate = useNavigate();
    const { workspace, workspaceId, workspaces } = useUgcWorkspace(preferredWorkspaceId);
    const [file, setFile] = useState<File | null>(null);
    const [fileError, setFileError] = useState<string | null>(null);
    const [context, setContext] = useState<UgcReviewContext>(INITIAL_CONTEXT);
    const [uploadProgress, setUploadProgress] = useState(0);
    const [previewUrl, setPreviewUrl] = useState<string | null>(null);
    const inputRef = useRef<HTMLInputElement>(null);
    const abortRef = useRef<AbortController | null>(null);

    useEffect(() => {
        if (!file) {
            setPreviewUrl(null);
            return;
        }
        const url = URL.createObjectURL(file);
        setPreviewUrl(url);
        return () => URL.revokeObjectURL(url);
    }, [file]);

    useEffect(() => () => abortRef.current?.abort(), []);

    const createReview = useMutation({
        mutationFn: async () => {
            if (!workspaceId || !file) throw new Error("Choose a workspace and video first.");
            const validationError = validateUgcVideo(file);
            if (validationError) throw new Error(validationError);
            const controller = new AbortController();
            abortRef.current = controller;
            setUploadProgress(1);
            const uploaded = await uploadAsset(
                workspaceId,
                file,
                undefined,
                setUploadProgress,
                "ugc",
                controller.signal,
            );
            return createUgcReview(
                workspaceId,
                {
                    assetId: uploaded.id,
                    assetVersionId: uploaded.asset_version_id,
                    context,
                },
                controller.signal,
            );
        },
        onSuccess: (review) => {
            void navigate({
                to: "/ugc-review/$assetId",
                params: { assetId: review.reviewId },
                search: { workspaceId },
            });
        },
        onSettled: () => {
            abortRef.current = null;
        },
    });

    function chooseFile(nextFile: File | null) {
        if (!nextFile) return;
        const error = validateUgcVideo(nextFile);
        setFileError(error);
        if (!error) setFile(nextFile);
    }

    function handleDrop(event: DragEvent<HTMLDivElement>) {
        event.preventDefault();
        chooseFile(event.dataTransfer.files.item(0));
    }

    function submit(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        const validationError = file ? validateUgcVideo(file) : "Choose a video to review.";
        setFileError(validationError);
        if (!validationError && workspaceId && !createReview.isPending) createReview.mutate();
    }

    const updateContext = <K extends keyof UgcReviewContext>(key: K, value: UgcReviewContext[K]) =>
        setContext((current) => ({ ...current, [key]: value }));

    const submitLabel = createReview.isPending
        ? uploadProgress < 100
            ? `Uploading ${Math.max(1, uploadProgress)}%`
            : "Starting your review"
        : "Review draft";

    return (
        <form onSubmit={submit} className="mx-auto flex w-full max-w-5xl flex-col gap-6">
            <PageHeader
                title="Review a creator draft"
                description="See what to keep, what to fix first, and get a revision message you can send right away."
                actions={
                    workspace ? (
                        <StatusChip tone="neutral">Workspace: {workspace.name}</StatusChip>
                    ) : undefined
                }
            />

            <div className="grid min-w-0 gap-6 lg:grid-cols-[minmax(0,1.15fr)_minmax(300px,0.85fr)] lg:items-start">
                <SurfaceCard padding="lg">
                    <div className="flex items-start gap-3">
                        <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-primary-softer text-primary">
                            <FileVideo2 className="h-5 w-5" />
                        </span>
                        <div>
                            <h2 className="text-lg font-semibold text-text-primary">UGC draft</h2>
                            <p className="mt-1 text-sm text-text-secondary">
                                MP4 or QuickTime video, up to 250 MB.
                            </p>
                        </div>
                    </div>

                    {file && previewUrl ? (
                        <div className="mt-5 overflow-hidden rounded-2xl border border-hairline bg-black">
                            <div className="relative mx-auto aspect-[9/16] max-h-[440px] max-w-[280px]">
                                <video
                                    src={previewUrl}
                                    controls
                                    playsInline
                                    preload="metadata"
                                    aria-label="Selected UGC draft preview"
                                    className="h-full w-full object-contain"
                                />
                            </div>
                            <div className="flex items-center justify-between gap-3 bg-surface px-4 py-3">
                                <div className="min-w-0">
                                    <p className="truncate text-sm font-medium text-text-primary">
                                        {file.name}
                                    </p>
                                    <p className="text-xs text-text-tertiary">
                                        {formatFileSize(file.size)}
                                    </p>
                                </div>
                                <Button
                                    type="button"
                                    variant="ghost"
                                    size="sm"
                                    disabled={createReview.isPending}
                                    onClick={() => {
                                        setFile(null);
                                        setFileError(null);
                                        if (inputRef.current) inputRef.current.value = "";
                                    }}
                                >
                                    <X className="h-4 w-4" />
                                    Remove
                                </Button>
                            </div>
                        </div>
                    ) : (
                        <div
                            onDragOver={(event) => event.preventDefault()}
                            onDrop={handleDrop}
                            className="mt-5 rounded-2xl border border-dashed border-control-border bg-surface-soft px-6 py-10 text-center transition-colors duration-[180ms] hover:border-primary/50"
                        >
                            <ViraldyIcon name="uploadVideo" size="2xl" className="mx-auto" />
                            <p className="mt-3 text-sm font-medium text-text-primary">
                                Drop your draft here
                            </p>
                            <p className="mt-1 text-xs text-text-secondary">or choose a file</p>
                            <Button
                                type="button"
                                variant="secondary"
                                size="sm"
                                className="mt-4"
                                onClick={() => inputRef.current?.click()}
                            >
                                Choose video
                            </Button>
                            <input
                                ref={inputRef}
                                type="file"
                                accept="video/mp4,video/quicktime,.mp4,.mov"
                                className="sr-only"
                                aria-label="Choose a UGC video"
                                onChange={(event) =>
                                    chooseFile(event.target.files?.item(0) ?? null)
                                }
                            />
                        </div>
                    )}
                    {fileError && (
                        <p className="mt-3 text-sm text-destructive" role="alert">
                            {fileError}
                        </p>
                    )}
                </SurfaceCard>

                <div className="min-w-0 space-y-5">
                    <SurfaceCard padding="lg">
                        <details className="group" open>
                            <summary className="flex cursor-pointer list-none items-center justify-between gap-3">
                                <div>
                                    <h2 className="font-semibold text-text-primary">
                                        Add context for a more precise review
                                    </h2>
                                    <p className="mt-1 text-sm text-text-secondary">
                                        Optional — start with only a video if that is all you have.
                                    </p>
                                </div>
                                <ChevronDown className="h-4 w-4 shrink-0 text-text-tertiary transition-transform duration-[180ms] group-open:rotate-180" />
                            </summary>

                            <div className="mt-5 grid gap-4">
                                <SelectField
                                    id="commerce-domain"
                                    label="Commerce domain"
                                    value={context.commerceDomain ?? "generic"}
                                    onChange={(value) =>
                                        updateContext("commerceDomain", value as UgcCommerceDomain)
                                    }
                                    options={[
                                        ["generic", "General commerce"],
                                        ["tiktok_shop_us", "TikTok Shop US"],
                                        ["pod_personalization", "Print-on-demand / personalized"],
                                        ["dropshipping", "Dropshipping"],
                                    ]}
                                />
                                <SelectField
                                    id="intended-use"
                                    label="Intended use"
                                    value={context.intendedUse ?? "unknown"}
                                    onChange={(value) =>
                                        updateContext("intendedUse", value as UgcIntendedUse)
                                    }
                                    options={[
                                        ["unknown", "Not decided yet"],
                                        ["organic", "Organic post"],
                                        ["affiliate", "Affiliate content"],
                                        ["paid_candidate", "Paid candidate"],
                                        ["spark_candidate", "Spark candidate"],
                                    ]}
                                />
                                <TextField
                                    id="product-name"
                                    label="Product name"
                                    value={context.productName ?? ""}
                                    onChange={(value) => updateContext("productName", value)}
                                />
                                <TextField
                                    id="product-category"
                                    label="Category"
                                    value={context.productCategory ?? ""}
                                    onChange={(value) => updateContext("productCategory", value)}
                                />
                                <TextField
                                    id="exact-variant"
                                    label="Exact variant or SKU"
                                    value={context.exactVariantOrSku ?? ""}
                                    onChange={(value) => updateContext("exactVariantOrSku", value)}
                                />
                                <TextAreaField
                                    id="product-description"
                                    label="Product description"
                                    value={context.productDescription ?? ""}
                                    onChange={(value) => updateContext("productDescription", value)}
                                />
                                <TextField
                                    id="current-offer"
                                    label="Current offer"
                                    value={context.currentOffer ?? ""}
                                    onChange={(value) => updateContext("currentOffer", value)}
                                />
                                <TextField
                                    id="shipping-language"
                                    label="Verified shipping language"
                                    value={context.verifiedShippingLanguage ?? ""}
                                    onChange={(value) =>
                                        updateContext("verifiedShippingLanguage", value)
                                    }
                                />
                                <TextAreaField
                                    id="approved-personalization"
                                    label="Approved personalization"
                                    value={context.approvedPersonalization ?? ""}
                                    onChange={(value) =>
                                        updateContext("approvedPersonalization", value)
                                    }
                                />
                                <SelectField
                                    id="physical-sample"
                                    label="Physical sample available"
                                    value={
                                        context.physicalSampleAvailable === undefined
                                            ? "unknown"
                                            : String(context.physicalSampleAvailable)
                                    }
                                    onChange={(value) =>
                                        updateContext(
                                            "physicalSampleAvailable",
                                            value === "unknown" ? undefined : value === "true",
                                        )
                                    }
                                    options={[
                                        ["unknown", "Not specified"],
                                        ["true", "Yes"],
                                        ["false", "No"],
                                    ]}
                                />
                                <TextAreaField
                                    id="creator-brief"
                                    label="Original creator brief"
                                    value={context.creatorBrief ?? ""}
                                    onChange={(value) => updateContext("creatorBrief", value)}
                                />
                                <SelectField
                                    id="material-connection"
                                    label="Material connection"
                                    value={context.materialConnection ?? "unknown"}
                                    onChange={(value) =>
                                        updateContext(
                                            "materialConnection",
                                            value as MaterialConnection,
                                        )
                                    }
                                    options={[
                                        ["unknown", "Not specified"],
                                        ["yes", "Yes"],
                                        ["no", "No"],
                                    ]}
                                />
                                <TextAreaField
                                    id="seller-notes"
                                    label="Seller notes"
                                    value={context.sellerNotes ?? ""}
                                    onChange={(value) => updateContext("sellerNotes", value)}
                                />
                            </div>
                        </details>
                    </SurfaceCard>

                    {workspaces.isError && (
                        <Alert>
                            <AlertTitle>Workspace unavailable</AlertTitle>
                            <AlertDescription>
                                Refresh the page, then choose your workspace again.
                            </AlertDescription>
                        </Alert>
                    )}
                    {createReview.isError && (
                        <Alert>
                            <AlertTitle>Your review could not start yet</AlertTitle>
                            <AlertDescription>
                                Your video and context are still here. Check your connection and try
                                again.
                            </AlertDescription>
                        </Alert>
                    )}
                    {createReview.isPending && (
                        <div aria-live="polite">
                            <Progress value={uploadProgress} />
                            <p className="mt-2 text-xs text-text-secondary">{submitLabel}</p>
                        </div>
                    )}
                    <Button
                        type="submit"
                        size="lg"
                        className="w-full"
                        disabled={!workspaceId || createReview.isPending}
                    >
                        {createReview.isPending ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                            <Sparkles className="h-4 w-4" />
                        )}
                        {submitLabel}
                    </Button>
                </div>
            </div>
        </form>
    );
}

function TextField({
    id,
    label,
    value,
    onChange,
}: {
    id: string;
    label: string;
    value: string;
    onChange: (value: string) => void;
}) {
    return (
        <div className="space-y-2">
            <Label htmlFor={id}>{label}</Label>
            <Input id={id} value={value} onChange={(event) => onChange(event.target.value)} />
        </div>
    );
}

function TextAreaField({
    id,
    label,
    value,
    onChange,
}: {
    id: string;
    label: string;
    value: string;
    onChange: (value: string) => void;
}) {
    return (
        <div className="space-y-2">
            <Label htmlFor={id}>{label}</Label>
            <Textarea
                id={id}
                value={value}
                rows={3}
                onChange={(event) => onChange(event.target.value)}
            />
        </div>
    );
}

function SelectField({
    id,
    label,
    value,
    onChange,
    options,
}: {
    id: string;
    label: string;
    value: string;
    onChange: (value: string) => void;
    options: readonly (readonly [string, string])[];
}) {
    return (
        <div className="space-y-2">
            <Label htmlFor={id}>{label}</Label>
            <select
                id={id}
                value={value}
                onChange={(event) => onChange(event.target.value)}
                className="flex h-10 w-full rounded-[10px] border border-control-border bg-surface px-3 text-sm text-text-primary transition-[border-color,box-shadow] duration-[180ms] focus-visible:border-primary/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/20"
            >
                {options.map(([optionValue, optionLabel]) => (
                    <option key={optionValue} value={optionValue}>
                        {optionLabel}
                    </option>
                ))}
            </select>
        </div>
    );
}

function formatFileSize(size: number): string {
    return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}
