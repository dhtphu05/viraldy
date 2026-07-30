import { AlertTriangle, CheckCircle2, Loader2 } from "lucide-react";
import type { ReactNode } from "react";

import type { JobResponse } from "@/shared/api/jobs";
import { humanizeLabel } from "@/shared/lib/display";
import { AnalysisThinkingSkeleton } from "@/shared/ui/analysis-thinking-skeleton";
import { Progress } from "@/shared/ui/progress";
import { StatusChip } from "@/shared/ui/status-chip";

export function JobProgress({
    job,
    recoveryAction,
}: {
    job?: JobResponse;
    recoveryAction?: ReactNode;
}) {
    if (!job) return null;

    const active = ["queued", "running", "retrying"].includes(job.status);
    const failed = job.status === "failed" || job.status === "cancelled";
    const complete = job.status === "succeeded" || job.status === "completed";
    const statusTone = failed ? "destructive" : complete ? "ok" : "info";

    return (
        <section
            role="status"
            aria-live="polite"
            className={`rounded-2xl p-4 ${
                failed ? "bg-destructive-soft" : complete ? "bg-ok-soft" : "bg-primary-soft/55"
            }`}
        >
            <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex min-w-0 items-center gap-2">
                    {active ? (
                        <Loader2
                            className="h-4 w-4 shrink-0 animate-spin text-primary"
                            aria-hidden
                        />
                    ) : failed ? (
                        <AlertTriangle className="h-4 w-4 shrink-0 text-destructive" aria-hidden />
                    ) : (
                        <CheckCircle2 className="h-4 w-4 shrink-0 text-ok" aria-hidden />
                    )}
                    <div className="min-w-0">
                        <p className="truncate text-sm font-semibold text-text-primary">
                            {humanizeLabel(job.job_type)}
                        </p>
                        <p className="text-xs text-text-secondary">
                            {humanizeLabel(job.stage ?? job.status)}
                        </p>
                    </div>
                </div>
                <StatusChip tone={statusTone}>{humanizeLabel(job.status)}</StatusChip>
            </div>
            <Progress className="mt-3" value={job.progress} aria-label="Analysis progress" />
            <div className="mt-2 flex items-center justify-between gap-3 text-xs text-text-secondary">
                <span>{Math.round(job.progress)}% complete</span>
                {job.error_code && <span>Code: {humanizeLabel(job.error_code)}</span>}
            </div>
            {job.error_message && (
                <div className="mt-3 flex flex-col gap-2 rounded-xl bg-surface/80 p-3 text-sm text-destructive sm:flex-row sm:items-center sm:justify-between">
                    <span>{job.error_message}</span>
                    {recoveryAction}
                </div>
            )}
            {active && (
                <AnalysisThinkingSkeleton
                    compact
                    className="mt-3"
                    title={stageTitle(job)}
                    description="The backend is preparing evidence and the next decision."
                />
            )}
        </section>
    );
}

function stageTitle(job: JobResponse) {
    if (job.status === "queued") return "Queued for analysis";
    if (job.stage) return humanizeLabel(job.stage);
    return "Analyzing media";
}
