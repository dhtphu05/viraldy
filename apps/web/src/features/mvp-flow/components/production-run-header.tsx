import type { AiReadiness } from "@/shared/api/system";
import type { ProductionEntryType } from "@/features/mvp-flow/lib/production-run-state";

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
    return (
        <header className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div className="min-w-0">
                <h1 className="text-2xl font-semibold text-text-primary">Production Run</h1>
                {entryType ? (
                    <p className="mt-1 max-w-3xl text-sm leading-6 text-text-secondary">
                        {runObject ?? "New run"} ·{" "}
                        {entryType === "reference-first" ? "Reference-first" : "Product-first"}
                    </p>
                ) : (
                    <p className="mt-1 max-w-3xl text-sm leading-6 text-text-secondary">
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
