import { CheckCircle2, Circle, Upload } from "lucide-react";
import type { ChangeEvent, ReactNode } from "react";

import { cn } from "@/shared/lib/utils";
import { Progress } from "@/shared/ui/progress";
import { Skeleton } from "@/shared/ui/skeleton";
import { StatusChip } from "@/shared/ui/status-chip";
import { SurfaceCard } from "@/shared/ui/surface-card";

export type ProductionInputItem = {
    label: string;
    value: string;
    complete: boolean;
};

type UploadState = {
    status: "idle" | "uploading" | "completed" | "failed";
    progress: number;
    filename?: string;
    message?: string;
};

export function InputStep({
    items,
    loading,
    uploadDisabled,
    uploadState,
    onUpload,
    missingRequirements,
    quickCheck,
}: {
    items: ProductionInputItem[];
    loading: boolean;
    uploadDisabled: boolean;
    uploadState: UploadState;
    onUpload: (file: File | null) => void;
    missingRequirements: string[];
    quickCheck: ReactNode;
}) {
    const completeCount = items.filter((item) => item.complete).length;
    const completeness = Math.round((completeCount / items.length) * 100);

    function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
        onUpload(event.target.files?.[0] ?? null);
        event.currentTarget.value = "";
    }

    return (
        <section id="input" className="scroll-mt-20">
            <SurfaceCard variant="raised" padding="lg">
                <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                    <div>
                        <p className="text-xs font-semibold uppercase text-primary">Input</p>
                        <h2 className="mt-1 text-lg font-semibold text-text-primary">
                            Production context
                        </h2>
                        <p className="mt-1 text-sm text-text-secondary">
                            Confirm the product, source pattern, and media before analysis.
                        </p>
                    </div>
                    <StatusChip tone={missingRequirements.length ? "warn" : "ok"}>
                        {completeCount} of {items.length} ready
                    </StatusChip>
                </div>

                <div className="mt-5 grid gap-x-6 gap-y-1 md:grid-cols-2">
                    {items.map((item) => (
                        <div
                            key={item.label}
                            className="flex min-w-0 items-start gap-3 border-b border-divider py-3"
                        >
                            {item.complete ? (
                                <CheckCircle2
                                    className="mt-0.5 h-4 w-4 shrink-0 text-ok"
                                    aria-hidden
                                />
                            ) : (
                                <Circle
                                    className="mt-0.5 h-4 w-4 shrink-0 text-text-tertiary"
                                    aria-hidden
                                />
                            )}
                            <div className="min-w-0">
                                <p className="text-xs font-medium text-text-tertiary">
                                    {item.label}
                                </p>
                                {loading ? (
                                    <Skeleton className="mt-1.5 h-4 w-40 max-w-full" />
                                ) : (
                                    <p className="mt-0.5 break-words text-sm font-medium text-text-primary">
                                        {item.value}
                                    </p>
                                )}
                            </div>
                        </div>
                    ))}
                </div>

                <div className="mt-5 grid gap-4 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-center">
                    <div>
                        <div className="flex items-center justify-between gap-3 text-xs">
                            <span className="font-medium text-text-secondary">
                                Input completeness
                            </span>
                            <span className="tabular text-text-tertiary">{completeness}%</span>
                        </div>
                        <Progress className="mt-2" value={completeness} />
                        <p className="mt-2 text-xs leading-5 text-text-secondary">
                            {missingRequirements.length
                                ? `Still needed: ${missingRequirements.join(", ")}.`
                                : "All required production inputs are available."}
                        </p>
                    </div>
                    <label
                        className={cn(
                            "inline-flex h-10 items-center justify-center gap-2 rounded-[10px] border border-control-border bg-surface px-4 text-sm font-medium text-text-primary transition-colors duration-[180ms] hover:bg-surface-soft focus-within:ring-2 focus-within:ring-ring",
                            uploadDisabled && "cursor-not-allowed opacity-55 hover:bg-surface",
                            !uploadDisabled && "cursor-pointer",
                        )}
                    >
                        <Upload className="h-4 w-4" aria-hidden />
                        Upload media
                        <input
                            type="file"
                            aria-label="Upload reference or creator video"
                            accept="video/mp4,video/quicktime"
                            className="sr-only"
                            disabled={uploadDisabled}
                            onChange={handleFileChange}
                        />
                    </label>
                </div>

                {uploadState.status !== "idle" && (
                    <div
                        className="mt-4 rounded-xl bg-surface-soft p-3"
                        role="status"
                        aria-live="polite"
                    >
                        <Progress value={uploadState.progress} />
                        <p className="mt-2 text-xs text-text-secondary">
                            Upload {uploadState.status}
                            {uploadState.filename ? `: ${uploadState.filename}` : ""}
                            {uploadState.message ? ` - ${uploadState.message}` : ""}
                        </p>
                    </div>
                )}

                <details className="mt-5 border-t border-divider pt-4">
                    <summary className="cursor-pointer text-sm font-medium text-text-primary">
                        Quick TikTok Scorer
                        <span className="ml-2 font-normal text-text-secondary">
                            Optional structure check
                        </span>
                    </summary>
                    <div className="mt-4">{quickCheck}</div>
                </details>
            </SurfaceCard>
        </section>
    );
}
