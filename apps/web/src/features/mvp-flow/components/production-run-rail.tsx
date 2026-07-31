import type { WorkflowRailStep } from "@/shared/ui/workflow-rail";
import { WorkflowRail } from "@/shared/ui/workflow-rail";

export function ProductionRunRail({ steps }: { steps: WorkflowRailStep[] }) {
    return (
        <aside className="xl:sticky xl:top-4">
            <div className="rounded-2xl bg-surface px-4 py-4 shadow-soft-card">
                <p className="mb-4 text-sm font-semibold text-text-primary">Run progress</p>
                <WorkflowRail steps={steps} ariaLabel="Production Run progress" />
            </div>
        </aside>
    );
}
