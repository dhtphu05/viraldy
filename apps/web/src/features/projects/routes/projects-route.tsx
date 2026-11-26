import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { createFileRoute, Link } from "@tanstack/react-router";
import { Plus } from "lucide-react";

import { listSmartRemakeProjects } from "@/shared/api/smart-remake-library";
import { useApiWorkspace } from "@/shared/hooks/use-workspace";
import { Button } from "@/shared/ui/button";
import { EmptyState, LoadingState } from "@/shared/ui/empty-state";
import { PageHeader } from "@/shared/ui/page-header";
import { SurfaceCard } from "@/shared/ui/surface-card";
import { AppShell } from "@/widgets/app-shell/app-shell";
import { ProjectGallery } from "../components/project-gallery";

export const Route = createFileRoute("/projects")({
    head: () => ({ meta: [{ title: "Project - Viraldy" }] }),
    component: ProjectsPage,
});

function ProjectsPage() {
    const { workspaceId, workspaces } = useApiWorkspace();

    return (
        <AppShell>
            <div className="flex flex-col gap-6">
                <PageHeader
                    title="Project"
                    description="Theo dõi tiến độ và mở lại kịch bản, ảnh, video Smart Remake trong workspace."
                    actions={
                        <Button asChild>
                            <Link to="/smart-remake" search={{ newProject: true }}>
                                <Plus aria-hidden /> Tạo video
                            </Link>
                        </Button>
                    }
                />
                {workspaceId ? (
                    <WorkspaceProjects key={workspaceId} workspaceId={workspaceId} />
                ) : workspaces.isLoading ? (
                    <LoadingState label="Đang mở workspace" />
                ) : (
                    <SurfaceCard role={workspaces.isError ? "alert" : undefined}>
                        <EmptyState
                            title={
                                workspaces.isError ? "Chưa mở được workspace" : "Chưa có workspace"
                            }
                            description={
                                workspaces.isError
                                    ? "Bạn thử tải lại để xem video đã lưu nhé."
                                    : "Chọn workspace để xem các video Smart Remake đã tạo."
                            }
                            action={
                                workspaces.isError ? (
                                    <Button onClick={() => void workspaces.refetch()}>
                                        Thử lại
                                    </Button>
                                ) : undefined
                            }
                        />
                    </SurfaceCard>
                )}
            </div>
        </AppShell>
    );
}

function WorkspaceProjects({ workspaceId }: { workspaceId: string }) {
    const [offset, setOffset] = useState(0);
    const projects = useQuery({
        queryKey: ["smart-remake", "projects", workspaceId, offset, "unfinished"],
        queryFn: ({ signal }) =>
            listSmartRemakeProjects(workspaceId, { offset, signal, includeUnfinished: true }),
        retry: 1,
        refetchOnMount: "always",
        refetchInterval: (query) =>
            query.state.data?.items.some((item) => item.activity?.status === "running")
                ? 5000
                : false,
    });

    useEffect(() => {
        if (!projects.data || offset === 0 || offset < projects.data.total) return;
        const { total, limit } = projects.data;
        setOffset(Math.max(0, Math.ceil(total / limit) - 1) * limit);
    }, [projects.data, offset]);

    return (
        <ProjectGallery
            items={projects.data?.items ?? []}
            total={projects.data?.total ?? 0}
            limit={projects.data?.limit ?? 24}
            offset={offset}
            loading={projects.isPending}
            refreshing={projects.isFetching}
            error={projects.isError}
            onRefresh={() => void projects.refetch()}
            onPageChange={setOffset}
        />
    );
}
