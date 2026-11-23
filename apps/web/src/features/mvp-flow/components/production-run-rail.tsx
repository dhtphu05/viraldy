import type { WorkflowRailStep } from "@/shared/ui/workflow-rail";
import { WorkflowRail } from "@/shared/ui/workflow-rail";

export function ProductionRunRail({ steps }: { steps: WorkflowRailStep[] }) {
    return (
        <div className="rounded-2xl bg-surface/85 px-3 py-4 shadow-[0_12px_32px_rgba(15,23,42,0.05)] sm:px-5">
            <div className="mb-3 flex items-center justify-between gap-3">
                <div>
                    <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-text-tertiary">
                        Run map
                    </p>
                    <p className="mt-1 text-sm font-medium text-text-primary">
                        From evidence to production decision
                    </p>
                </div>
                <span className="hidden text-xs text-text-tertiary sm:block">
                    Select completed phases to revisit them
                </span>
            </div>
            <WorkflowRail
                steps={steps}
                orientation="horizontal"
                ariaLabel="Production Run progress"
            />
        </div>
    );
}
