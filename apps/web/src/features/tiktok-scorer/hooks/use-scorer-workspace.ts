import { useQuery } from "@tanstack/react-query";

import { useAppStore } from "@/app/store/app-store";
import { listProductWorkspaces } from "@/shared/api/products";
import { queryKeys } from "@/shared/api/query-keys";

export function useScorerWorkspace() {
    const currentWorkspaceId = useAppStore((state) => state.currentWorkspaceId);
    const workspaces = useQuery({
        queryKey: queryKeys.workspaces.list,
        queryFn: listProductWorkspaces,
        staleTime: 60_000,
        retry: 1,
    });
    const workspace =
        workspaces.data?.find((item) => item.id === currentWorkspaceId) ??
        workspaces.data?.[0] ??
        null;

    return {
        workspace,
        workspaceId: workspace?.id,
        workspaces,
    };
}
