import type { WorkflowRailStep } from "@/shared/ui/workflow-rail";
import { WorkflowRail } from "@/shared/ui/workflow-rail";

export function ProductionRunRail({ steps }: { steps: WorkflowRailStep[] }) {
    return (
        <div className="rounded-md bg-surface px-3 py-3 shadow-soft-card sm:px-4">
            <WorkflowRail
                steps={steps}
                orientation="horizontal"
                ariaLabel="Production Run progress"
            />
        </div>
    );
}
