import type { AiReadiness } from "@/shared/api/system";

import { RuntimeStatusPopover } from "./runtime-status-popover";

export function ProductionRunHeader({
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
    return (
        <header className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div className="min-w-0">
                <h1 className="text-2xl font-semibold text-text-primary">Production Run</h1>
                <p className="mt-1 max-w-3xl text-sm leading-6 text-text-secondary">
                    Move from a product or winning reference to a creator-ready Campaign Pack and
                    validated UGC.
                </p>
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
