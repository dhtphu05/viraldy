import { AlertTriangle, Check, Circle } from "lucide-react";

import { cn } from "@/shared/lib/utils";

export type WorkflowRailState = "complete" | "current" | "blocked" | "future";

export type WorkflowRailStep = {
    id: string;
    label: string;
    state: WorkflowRailState;
    description?: string;
    blockedReason?: string;
    onSelect?: () => void;
};

export function WorkflowRail({
    steps,
    className,
    ariaLabel = "Workflow progress",
}: {
    steps: WorkflowRailStep[];
    className?: string;
    ariaLabel?: string;
}) {
    return (
        <nav aria-label={ariaLabel} className={className}>
            <ol className="space-y-0">
                {steps.map((step, index) => {
                    const clickable =
                        Boolean(step.onSelect) &&
                        (step.state === "complete" || step.state === "current");
                    const marker =
                        step.state === "complete" ? (
                            <Check className="h-3.5 w-3.5" />
                        ) : step.state === "blocked" ? (
                            <AlertTriangle className="h-3.5 w-3.5" />
                        ) : (
                            <Circle className="h-2.5 w-2.5 fill-current" />
                        );
                    const content = (
                        <>
                            <span className="relative flex w-7 shrink-0 justify-center self-stretch">
                                {index < steps.length - 1 && (
                                    <span
                                        aria-hidden
                                        className="absolute bottom-0 top-7 w-px bg-divider"
                                    />
                                )}
                                <span
                                    className={cn(
                                        "relative z-10 mt-0.5 grid h-7 w-7 place-items-center rounded-full",
                                        step.state === "complete" && "bg-ok-soft text-ok",
                                        step.state === "current" &&
                                            "bg-primary text-primary-foreground",
                                        step.state === "blocked" && "bg-warn-soft text-warn",
                                        step.state === "future" &&
                                            "bg-surface-muted text-text-tertiary",
                                    )}
                                >
                                    {marker}
                                </span>
                            </span>
                            <span className="min-w-0 pb-5 pt-1">
                                <span
                                    className={cn(
                                        "block text-sm font-medium leading-5",
                                        step.state === "current" && "text-primary-active",
                                        step.state === "complete" && "text-text-primary",
                                        step.state === "blocked" && "text-warn",
                                        step.state === "future" && "text-text-tertiary",
                                    )}
                                >
                                    {step.label}
                                </span>
                                {step.description && (
                                    <span className="mt-0.5 block text-xs leading-4 text-text-secondary">
                                        {step.description}
                                    </span>
                                )}
                                {step.state === "blocked" && step.blockedReason && (
                                    <span className="mt-1 block text-xs leading-4 text-warn">
                                        {step.blockedReason}
                                    </span>
                                )}
                            </span>
                        </>
                    );

                    return (
                        <li key={step.id}>
                            {clickable ? (
                                <button
                                    type="button"
                                    onClick={step.onSelect}
                                    aria-current={step.state === "current" ? "step" : undefined}
                                    className="flex w-full min-w-0 gap-2 rounded-xl text-left transition-colors duration-[180ms] hover:bg-surface-soft focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                                >
                                    {content}
                                </button>
                            ) : (
                                <div
                                    className="flex min-w-0 gap-2"
                                    aria-current={step.state === "current" ? "step" : undefined}
                                >
                                    {content}
                                </div>
                            )}
                        </li>
                    );
                })}
            </ol>
        </nav>
    );
}
