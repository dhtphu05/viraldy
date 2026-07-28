import { AppShell } from "@/widgets/app-shell/app-shell";
import { PageHeader } from "@/shared/ui/page-header";
import { SurfaceCard } from "@/shared/ui/surface-card";
import { EmptyState } from "@/shared/ui/empty-state";
import { Button } from "@/shared/ui/button";
import type { ReactNode } from "react";

export function PlaceholderPage({
    title,
    description,
    actions,
    emptyTitle,
    emptyDescription,
    icon,
}: {
    title: string;
    description: string;
    actions?: ReactNode;
    emptyTitle: string;
    emptyDescription: string;
    icon?: React.ComponentType<{ className?: string }>;
}) {
    return (
        <AppShell>
            <div className="flex flex-col gap-8">
                <PageHeader title={title} description={description} actions={actions} />
                <SurfaceCard padding="lg">
                    <EmptyState
                        icon={icon}
                        title={emptyTitle}
                        description={emptyDescription}
                        action={
                            <Button variant="secondary" size="sm" asChild>
                                <a href="/dashboard">Back to Overview</a>
                            </Button>
                        }
                    />
                </SurfaceCard>
            </div>
        </AppShell>
    );
}
