import * as React from "react";
import { cn } from "@/shared/lib/utils";

export type SurfaceVariant = "plain" | "raised" | "interactive" | "outlined" | "critical";

type Props = React.HTMLAttributes<HTMLDivElement> & {
    interactive?: boolean;
    variant?: SurfaceVariant;
    padding?: "sm" | "md" | "lg" | "none";
    highlight?: boolean;
};

export const SurfaceCard = React.forwardRef<HTMLDivElement, Props>(
    (
        {
            className,
            interactive,
            variant = "plain",
            padding = "md",
            highlight = false,
            children,
            ...rest
        },
        ref,
    ) => {
        const pad =
            padding === "none" ? "" : padding === "sm" ? "p-4" : padding === "lg" ? "p-7" : "p-5";
        const resolvedVariant = interactive ? "interactive" : variant;
        const variantClass: Record<SurfaceVariant, string> = {
            plain: "surface-card",
            raised: "surface-card-raised",
            interactive:
                "surface-card-interactive data-[selected=true]:bg-primary-softer data-[selected=true]:ring-2 data-[selected=true]:ring-inset data-[selected=true]:ring-primary",
            outlined: "surface-card-outlined",
            critical: "surface-card-critical",
        };

        return (
            <div
                ref={ref}
                className={cn(
                    variantClass[resolvedVariant],
                    highlight && "inner-top-highlight",
                    pad,
                    className,
                )}
                {...rest}
            >
                {children}
            </div>
        );
    },
);
SurfaceCard.displayName = "SurfaceCard";
