import type { AiReadiness } from "@/shared/api/system";
import type { ProductionEntryType } from "@/features/mvp-flow/lib/production-run-state";
import { StatusChip } from "@/shared/ui/status-chip";

import { RuntimeStatusPopover } from "./runtime-status-popover";

export function ProductionRunHeader({
    backendConfigured,
    loading,
    error,
    readiness,
    workspaceName,
    entryType,
    runObject,
}: {
    backendConfigured: boolean;
    loading: boolean;
    error: unknown;
    readiness?: AiReadiness;
    workspaceName?: string;
    entryType?: ProductionEntryType;
    runObject?: string;
}) {
    const fixtureMode = readiness?.mode === "fixture" && readiness.configured;

    return (
        <header className="flex flex-col gap-5 rounded-2xl bg-surface/95 px-5 py-5 shadow-[0_16px_42px_rgba(15,23,42,0.07)] sm:flex-row sm:items-start sm:justify-between sm:px-6">
            <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-primary">
                        Creative intelligence workspace
                    </p>
                    {fixtureMode && (
                        <StatusChip tone="info" dot>
                            Fixture · no model request
                        </StatusChip>
                    )}
                </div>
                <h1 className="mt-2 text-2xl font-semibold tracking-[-0.02em] text-text-primary sm:text-3xl">
                    Production Run
                </h1>
                {entryType ? (
                    <p className="mt-2 max-w-3xl text-sm leading-6 text-text-secondary">
                        <span className="font-medium text-text-primary">
                            {runObject ?? "New run"}
                        </span>
                        <span className="mx-2 text-text-tertiary" aria-hidden>
                            /
                        </span>
                        {entryType === "reference-first" ? "Reference-first" : "Product-first"}
                    </p>
                ) : (
                    <p className="mt-2 max-w-3xl text-sm leading-6 text-text-secondary">
                        Start with a product or a winning reference and leave with a production
                        decision.
                    </p>
                )}
            </div>
            <RuntimeStatusPopover
                backendConfigured={backendConfigured}
                loading={loading}
                error={error}
                readiness={readiness}
                workspaceName={workspaceName}
            />
        </header>
    );
}
