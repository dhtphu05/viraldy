import { useId, type ReactNode } from "react";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/shared/ui/tooltip";
import { cn } from "@/shared/lib/utils";

export function DisabledActionHint({
    reason,
    children,
    className,
}: {
    reason?: string | null;
    children: ReactNode;
    className?: string;
}) {
    const id = useId();

    if (!reason) return <>{children}</>;

    return (
        <div className={cn("inline-flex flex-col gap-1", className)}>
            <TooltipProvider delayDuration={150}>
                <Tooltip>
                    <TooltipTrigger asChild>
                        <span aria-describedby={id} className="inline-flex cursor-not-allowed">
                            {children}
                        </span>
                    </TooltipTrigger>
                    <TooltipContent>{reason}</TooltipContent>
                </Tooltip>
            </TooltipProvider>
            <p id={id} className="max-w-xs text-xs text-text-tertiary">
                {reason}
            </p>
        </div>
    );
}
