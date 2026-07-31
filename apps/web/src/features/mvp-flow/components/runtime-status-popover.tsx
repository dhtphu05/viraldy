import { AlertTriangle, CheckCircle2, Info, Loader2, Server } from "lucide-react";

import { humanizeLabel } from "@/shared/lib/display";
import type { AiReadiness } from "@/shared/api/system";
import { Button } from "@/shared/ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "@/shared/ui/popover";
import { StatusChip } from "@/shared/ui/status-chip";
import { deriveRuntimeStatus } from "@/features/mvp-flow/lib/runtime-status";

export function RuntimeStatusPopover({
    backendConfigured,
    loading,
    error,
    readiness,
    workspaceName,
}: {
    backendConfigured: boolean;
    loading: boolean;
    error: unknown;
    readiness?: AiReadiness;
    workspaceName?: string;
}) {
    const runtime = deriveRuntimeStatus({
        backendConfigured,
        loading,
        error,
        readiness,
    });

    return (
        <Popover>
            <PopoverTrigger asChild>
                <Button
                    variant="secondary"
                    size="sm"
                    aria-label={`Runtime status: ${runtime.label}`}
                >
                    {loading ? (
                        <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
                    ) : (
                        <Server className="h-4 w-4" aria-hidden />
                    )}
                    Runtime
                    <span
                        className={`h-2 w-2 rounded-full ${
                            runtime.tone === "destructive"
                                ? "bg-destructive"
                                : runtime.active
                                  ? "bg-ok"
                                  : runtime.tone === "info"
                                    ? "bg-info"
                                    : "bg-warn"
                        }`}
                        aria-hidden
                    />
                </Button>
            </PopoverTrigger>
            <PopoverContent
                align="end"
                className="w-[min(22rem,calc(100vw-2rem))] rounded-2xl border-control-border shadow-floating-card"
            >
                <div className="flex items-start justify-between gap-3">
                    <div>
                        <p className="text-sm font-semibold text-text-primary">Runtime status</p>
                        <p className="mt-1 text-xs leading-5 text-text-secondary">
                            Connection and analysis provenance for this production run.
                        </p>
                    </div>
                    <StatusChip tone={runtime.tone}>{runtime.label}</StatusChip>
                </div>

                <dl className="mt-4 divide-y divide-divider text-sm">
                    <RuntimeRow label="Workspace" value={workspaceName ?? "Unavailable"} />
                    <RuntimeRow
                        label="Analysis"
                        value={
                            readiness
                                ? humanizeLabel(readiness.mode)
                                : backendConfigured
                                  ? "Checking"
                                  : "Unavailable"
                        }
                    />
                    <RuntimeRow
                        label="Provider"
                        value={runtime.provider ? humanizeLabel(runtime.provider) : "Not connected"}
                    />
                </dl>

                <div
                    role="status"
                    aria-live="polite"
                    className={`mt-4 flex gap-2 rounded-xl p-3 text-xs leading-5 ${
                        runtime.tone === "destructive"
                            ? "bg-destructive-soft text-destructive"
                            : runtime.active
                              ? "bg-ok-soft text-text-primary"
                              : runtime.tone === "info"
                                ? "bg-info-soft text-text-primary"
                                : "bg-warn-soft text-text-primary"
                    }`}
                >
                    {runtime.tone === "destructive" ? (
                        <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
                    ) : runtime.active ? (
                        <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-ok" aria-hidden />
                    ) : (
                        <Info
                            className={`mt-0.5 h-4 w-4 shrink-0 ${
                                runtime.tone === "info" ? "text-info" : "text-warn"
                            }`}
                            aria-hidden
                        />
                    )}
                    <span>{runtime.message}</span>
                </div>
            </PopoverContent>
        </Popover>
    );
}

function RuntimeRow({ label, value }: { label: string; value: string }) {
    return (
        <div className="flex items-center justify-between gap-4 py-2">
            <dt className="text-text-tertiary">{label}</dt>
            <dd className="min-w-0 break-words text-right font-medium text-text-primary">
                {value}
            </dd>
        </div>
    );
}
