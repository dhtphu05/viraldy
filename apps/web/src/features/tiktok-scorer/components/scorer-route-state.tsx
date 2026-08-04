import { AlertTriangle, LockKeyhole, RefreshCw, SearchX, WifiOff } from "lucide-react";

import { ApiError } from "@/shared/api/errors";
import { Button } from "@/shared/ui/button";
import { EmptyState, LoadingState } from "@/shared/ui/empty-state";
import { SurfaceCard } from "@/shared/ui/surface-card";

export function ScorerLoadingState({ label }: { label: string }) {
    return (
        <SurfaceCard>
            <LoadingState label={label} className="min-h-40" />
        </SurfaceCard>
    );
}

export function ScorerErrorState({
    error,
    onRetry,
    resource = "TikTok score",
}: {
    error: unknown;
    onRetry: () => void;
    resource?: string;
}) {
    const apiError = error instanceof ApiError ? error : null;
    const permissionDenied = apiError?.status === 401 || apiError?.status === 403;
    const notFound = apiError?.status === 404;
    const offline =
        error instanceof TypeError || apiError?.status === 502 || apiError?.status === 503;
    const Icon = permissionDenied
        ? LockKeyhole
        : notFound
          ? SearchX
          : offline
            ? WifiOff
            : AlertTriangle;
    const title = permissionDenied
        ? "You do not have access to this workspace"
        : notFound
          ? `${resource} not found`
          : offline
            ? "Viraldy could not reach the scorer"
            : `${resource} could not load`;
    const description = permissionDenied
        ? "Switch to a workspace where you have analysis access, or ask a workspace owner for permission."
        : notFound
          ? "It may have been removed, or the link belongs to another workspace."
          : apiError?.message ||
            "Check your connection and try again. Your existing analysis is unchanged.";

    return (
        <SurfaceCard variant={permissionDenied ? "critical" : "plain"}>
            <EmptyState
                icon={Icon}
                title={title}
                description={description}
                action={
                    !permissionDenied && !notFound ? (
                        <Button type="button" variant="secondary" onClick={onRetry}>
                            <RefreshCw className="h-4 w-4" />
                            Try again
                        </Button>
                    ) : undefined
                }
            />
        </SurfaceCard>
    );
}
