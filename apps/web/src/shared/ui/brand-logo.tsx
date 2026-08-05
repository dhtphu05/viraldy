import { cn } from "@/shared/lib/utils";

type BrandLogoProps = {
    markOnly?: boolean;
    className?: string;
    imageClassName?: string;
};

export function BrandLogo({ markOnly = false, className, imageClassName }: BrandLogoProps) {
    const src = markOnly ? "/viraldy-logo-mark.png" : "/viraldy-logo-wordmark.png";

    return (
        <span
            className={cn(
                "inline-flex shrink-0 items-center overflow-hidden",
                markOnly ? "h-9 w-9" : "h-10 w-[148px]",
                className,
            )}
        >
            <img
                src={src}
                alt="Viraldy"
                className={cn("h-full w-full object-contain", imageClassName)}
                draggable={false}
            />
        </span>
    );
}
