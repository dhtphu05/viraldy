import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/shared/ui/sheet";
import type { ComponentProps, ReactNode } from "react";
import { useRef } from "react";

export function RightDrawer({
    open,
    onOpenChange,
    title,
    description,
    children,
    footer,
    size = "md",
    onOpenAutoFocus,
    onCloseAutoFocus,
}: {
    open: boolean;
    onOpenChange: (v: boolean) => void;
    title: string;
    description?: string;
    children: ReactNode;
    footer?: ReactNode;
    size?: "sm" | "md" | "lg";
    onOpenAutoFocus?: ComponentProps<typeof SheetContent>["onOpenAutoFocus"];
    onCloseAutoFocus?: ComponentProps<typeof SheetContent>["onCloseAutoFocus"];
}) {
    const width = size === "sm" ? "sm:max-w-md" : size === "lg" ? "sm:max-w-2xl" : "sm:max-w-xl";
    const returnFocusRef = useRef<HTMLElement | null>(null);

    return (
        <Sheet open={open} onOpenChange={onOpenChange}>
            <SheetContent
                side="right"
                className={`flex w-full flex-col p-0 ${width}`}
                onOpenAutoFocus={(event) => {
                    returnFocusRef.current =
                        document.activeElement instanceof HTMLElement
                            ? document.activeElement
                            : null;
                    onOpenAutoFocus?.(event);
                }}
                onCloseAutoFocus={(event) => {
                    if (onCloseAutoFocus) {
                        onCloseAutoFocus(event);
                        return;
                    }
                    if (returnFocusRef.current) {
                        event.preventDefault();
                        returnFocusRef.current.focus();
                    }
                }}
            >
                <SheetHeader className="border-b border-hairline px-6 py-4">
                    <SheetTitle className="text-base font-semibold text-text-primary">
                        {title}
                    </SheetTitle>
                    {description && (
                        <SheetDescription className="text-sm text-text-secondary">
                            {description}
                        </SheetDescription>
                    )}
                </SheetHeader>
                <div className="min-h-0 flex-1 overflow-y-auto px-6 py-5">{children}</div>
                {footer && (
                    <div className="border-t border-hairline bg-surface-soft/50 px-6 py-3">
                        {footer}
                    </div>
                )}
            </SheetContent>
        </Sheet>
    );
}
