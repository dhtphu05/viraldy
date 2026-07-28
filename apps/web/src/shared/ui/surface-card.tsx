import * as React from "react";
import { cn } from "@/shared/lib/utils";

type Props = React.HTMLAttributes<HTMLDivElement> & {
    interactive?: boolean;
    padding?: "sm" | "md" | "lg" | "none";
    highlight?: boolean;
};

export const SurfaceCard = React.forwardRef<HTMLDivElement, Props>(
    ({ className, interactive, padding = "md", highlight = true, children, ...rest }, ref) => {
        const pad =
            padding === "none" ? "" : padding === "sm" ? "p-4" : padding === "lg" ? "p-7" : "p-5";
        return (
            <div
                ref={ref}
                className={cn(
                    interactive ? "surface-card-interactive" : "surface-card",
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
