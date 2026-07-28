import { createFileRoute } from "@tanstack/react-router";
import { AppShell } from "@/widgets/app-shell/app-shell";
import { PageHeader } from "@/shared/ui/page-header";
import { SurfaceCard } from "@/shared/ui/surface-card";
import { Button } from "@/shared/ui/button";
import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
    AlertDialogTrigger,
} from "@/shared/ui/alert-dialog";
import { Switch } from "@/shared/ui/switch";
import { useAppStore } from "@/app/store/app-store";
import { workspaces } from "@/shared/mocks/workspaces";
import { toast } from "sonner";

export const Route = createFileRoute("/settings")({
    head: () => ({ meta: [{ title: "Settings — Viraldy" }] }),
    component: SettingsPage,
});

function SettingsPage() {
    const currentId = useAppStore((s) => s.currentWorkspaceId);
    const collapsed = useAppStore((s) => s.sidebarCollapsed);
    const setCollapsed = useAppStore((s) => s.setSidebarCollapsed);
    const reset = useAppStore((s) => s.reset);
    const workspace = workspaces.find((w) => w.id === currentId) ?? workspaces[0];

    return (
        <AppShell>
            <div className="flex flex-col gap-8">
                <PageHeader
                    title="Settings"
                    description="Workspace preferences and demo data controls."
                />

                <div className="grid gap-6 lg:grid-cols-2">
                    <SurfaceCard className="flex flex-col gap-4">
                        <div>
                            <h2 className="text-sm font-semibold text-text-primary">Workspace</h2>
                            <p className="mt-1 text-sm text-text-secondary">
                                You're viewing demo data for {workspace.name} ({workspace.handle}).
                            </p>
                        </div>
                        <div className="flex items-center justify-between rounded-md bg-surface-soft px-3 py-2">
                            <div>
                                <p className="text-sm font-medium text-text-primary">
                                    Sidebar collapsed by default
                                </p>
                                <p className="text-xs text-text-secondary">
                                    Persisted across reloads.
                                </p>
                            </div>
                            <Switch checked={collapsed} onCheckedChange={setCollapsed} />
                        </div>
                    </SurfaceCard>

                    <SurfaceCard className="flex flex-col gap-4">
                        <div>
                            <h2 className="text-sm font-semibold text-text-primary">Demo data</h2>
                            <p className="mt-1 text-sm text-text-secondary">
                                Reset locally-created campaigns, dismissed recommendations, and
                                imports to the initial demo state.
                            </p>
                        </div>
                        <AlertDialog>
                            <AlertDialogTrigger asChild>
                                <Button variant="destructive" className="w-fit">
                                    Reset demo data
                                </Button>
                            </AlertDialogTrigger>
                            <AlertDialogContent>
                                <AlertDialogHeader>
                                    <AlertDialogTitle>Reset demo data?</AlertDialogTitle>
                                    <AlertDialogDescription>
                                        This clears locally-created campaigns, imports, and
                                        dismissed recommendations. Seed mock data is unchanged.
                                    </AlertDialogDescription>
                                </AlertDialogHeader>
                                <AlertDialogFooter>
                                    <AlertDialogCancel>Cancel</AlertDialogCancel>
                                    <AlertDialogAction
                                        onClick={() => {
                                            reset();
                                            toast.success("Demo data reset");
                                        }}
                                    >
                                        Reset
                                    </AlertDialogAction>
                                </AlertDialogFooter>
                            </AlertDialogContent>
                        </AlertDialog>
                    </SurfaceCard>
                </div>
            </div>
        </AppShell>
    );
}
