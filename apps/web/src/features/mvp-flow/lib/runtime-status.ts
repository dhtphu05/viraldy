import type { AiReadiness } from "@/shared/api/system";
import { humanizeLabel } from "@/shared/lib/display";

export type RuntimeStatusTone = "destructive" | "info" | "ok" | "warn";

export type RuntimeStatus = {
    label: string;
    tone: RuntimeStatusTone;
    active: boolean;
    message: string;
    provider: string | null;
};

export function deriveRuntimeStatus({
    backendConfigured,
    loading,
    error,
    readiness,
}: {
    backendConfigured: boolean;
    loading: boolean;
    error: unknown;
    readiness?: AiReadiness;
}): RuntimeStatus {
    if (error) {
        return {
            label: "Connection issue",
            tone: "destructive",
            active: false,
            message: error instanceof Error ? error.message : "The backend could not be reached.",
            provider: null,
        };
    }
    if (loading) {
        return {
            label: "Connecting",
            tone: "info",
            active: false,
            message: "Loading workspace data and analysis readiness.",
            provider: null,
        };
    }
    if (!backendConfigured) {
        return {
            label: "Not connected",
            tone: "warn",
            active: false,
            message: "Connect the backend to use workspace products and media.",
            provider: null,
        };
    }
    if (readiness?.mode === "live" && readiness.configured) {
        return {
            label: "Live provider configured",
            tone: "ok",
            active: true,
            message: "A live provider is configured. Qualification status is evaluated separately.",
            provider: readiness.provider,
        };
    }
    if (readiness?.mode === "mock" && readiness.configured) {
        return {
            label: "Mock runtime",
            tone: "info",
            active: false,
            message: "Mock analysis is active; it does not qualify the live OpenAI path.",
            provider: readiness.provider,
        };
    }
    if (readiness?.mode === "fixture" && readiness.configured) {
        return {
            label: "Fixture runtime",
            tone: "info",
            active: false,
            message: "Fixture analysis is active; no model request is being made.",
            provider: "fixture",
        };
    }
    if (readiness?.missing.length) {
        return {
            label: "Provider not ready",
            tone: "warn",
            active: false,
            message: `Analysis is not ready. Missing: ${readiness.missing
                .map((item) => humanizeLabel(item))
                .join(", ")}.`,
            provider: readiness.provider || null,
        };
    }
    return {
        label: "Provider not ready",
        tone: "warn",
        active: false,
        message: "Analysis is unavailable until a provider is configured.",
        provider: readiness?.provider || null,
    };
}
