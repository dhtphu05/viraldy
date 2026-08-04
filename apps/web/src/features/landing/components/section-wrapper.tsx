import { cn } from "@/shared/lib/utils";
import type { ReactNode } from "react";

export function SectionWrapper({
    id,
    children,
    className,
    background = "default",
}: {
    id?: string;
    children: ReactNode;
    className?: string;
    background?: "default" | "surface" | "primary-soft";
}) {
    return (
        <section
            id={id}
            className={cn(
                "scroll-mt-20",
                background === "surface" && "bg-surface",
                background === "primary-soft" && "bg-primary-softer",
                className,
            )}
        >
            <div className="mx-auto max-w-[1200px] px-4 py-16 sm:px-6 sm:py-20 lg:px-10 lg:py-24">
                {children}
            </div>
        </section>
    );
}
