import { VIRALDY_ICONS, type ViraldyIconName } from "@/assets/viraldy-icons/registry";
import { cn } from "@/shared/lib/utils";

export type ViraldyIconSize = "xs" | "sm" | "md" | "nav" | "lg" | "xl" | "2xl" | "feature" | "hero";

const sizeClass: Record<ViraldyIconSize, string> = {
    xs: "h-4 w-4",
    sm: "h-[18px] w-[18px]",
    md: "h-5 w-5",
    nav: "h-[22px] w-[22px]",
    lg: "h-6 w-6",
    xl: "h-7 w-7",
    "2xl": "h-8 w-8",
    feature: "h-10 w-10",
    hero: "h-14 w-14",
};

export function ViraldyIcon({
    name,
    size = "md",
    label,
    decorative,
    className,
}: {
    name: ViraldyIconName;
    size?: ViraldyIconSize;
    label?: string;
    decorative?: boolean;
    className?: string;
}) {
    const isDecorative = decorative ?? !label;

    return (
        <img
            src={VIRALDY_ICONS[name]}
            alt={isDecorative ? "" : label}
            aria-hidden={isDecorative || undefined}
            className={cn("inline-block shrink-0 object-contain", sizeClass[size], className)}
            draggable={false}
        />
    );
}

export type { ViraldyIconName };
