import type { ReactNode } from "react";
import { CheckCircle2 } from "lucide-react";

import { cn } from "@/shared/lib/utils";

export function ValueReceipt({
    title,
    description,
    items,
    action,
    className,
}: {
    title: string;
    description?: ReactNode;
    items?: string[];
    action?: ReactNode;
    className?: string;
}) {
    return (
        <section
            role="status"
            aria-live="polite"
            className={cn("rounded-2xl bg-ok-soft p-5", className)}
        >
            <div className="flex items-start gap-3">
                <span className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-ok text-white">
                    <CheckCircle2 className="h-5 w-5" aria-hidden />
                </span>
                <div className="min-w-0 flex-1">
                    <h3 className="text-base font-semibold text-text-primary">{title}</h3>
                    {description && (
                        <div className="mt-1 text-sm leading-5 text-text-secondary">
                            {description}
                        </div>
                    )}
                    {items?.length ? (
                        <ul className="mt-3 grid gap-1 text-sm text-text-primary sm:grid-cols-2">
                            {items.map((item) => (
                                <li key={item} className="flex items-center gap-2">
                                    <CheckCircle2
                                        className="h-4 w-4 shrink-0 text-ok"
                                        aria-hidden
                                    />
                                    {item}
                                </li>
                            ))}
                        </ul>
                    ) : null}
                </div>
                {action && <div className="shrink-0">{action}</div>}
            </div>
        </section>
    );
}
