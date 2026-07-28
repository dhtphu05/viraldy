import { Check, Loader2 } from "lucide-react";
import { cn } from "@/shared/lib/utils";

export type Step = { key: string; label: string; status: "pending" | "active" | "done" };

export function ProcessingStepper({ steps }: { steps: Step[] }) {
    return (
        <ol className="flex flex-col gap-2">
            {steps.map((s) => (
                <li
                    key={s.key}
                    className="flex items-center gap-3 rounded-md bg-surface-soft/60 px-3 py-2 text-sm"
                >
                    <span
                        className={cn(
                            "grid h-6 w-6 place-items-center rounded-full",
                            s.status === "done" && "bg-ok text-white",
                            s.status === "active" && "bg-primary text-primary-foreground",
                            s.status === "pending" && "bg-surface-muted text-text-tertiary",
                        )}
                    >
                        {s.status === "done" ? (
                            <Check className="h-3.5 w-3.5" />
                        ) : s.status === "active" ? (
                            <Loader2 className="h-3.5 w-3.5 animate-spin" />
                        ) : (
                            <span className="text-[10px]">•</span>
                        )}
                    </span>
                    <span
                        className={cn(
                            s.status === "pending" ? "text-text-tertiary" : "text-text-primary",
                        )}
                    >
                        {s.label}
                    </span>
                </li>
            ))}
        </ol>
    );
}
