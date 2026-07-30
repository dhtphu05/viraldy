import { RightDrawer } from "@/shared/ui/right-drawer";
import { StatusChip } from "@/shared/ui/status-chip";
import { Button } from "@/shared/ui/button";
import { Separator } from "@/shared/ui/separator";
import { DemoMediaTile } from "@/shared/ui/demo-media-tile";
import type { PerfRecommendation } from "@/features/performance/types/performance";
import { decisionTone } from "@/features/performance/lib/performanceEngine";
import { useAppStore } from "@/app/store/app-store";
import { toast } from "sonner";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger,
} from "@/shared/ui/dropdown-menu";
import { MoreHorizontal } from "lucide-react";

const dismissReasons = [
    "Already handled",
    "Not enough data",
    "Not relevant",
    "Wrong diagnosis",
    "Testing another direction",
    "Other",
];

export function EvidenceDrawer({
    rec,
    open,
    onOpenChange,
    onGenerateVariants,
}: {
    rec: PerfRecommendation | null;
    open: boolean;
    onOpenChange: (v: boolean) => void;
    onGenerateVariants?: (rec: PerfRecommendation) => void;
}) {
    const accept = useAppStore((s) => s.acceptPerfRec);
    const unaccept = useAppStore((s) => s.unacceptPerfRec);
    const dismiss = useAppStore((s) => s.dismissPerfRec);
    const undismiss = useAppStore((s) => s.undismissPerfRec);
    const snooze = useAppStore((s) => s.snoozePerfRec);
    const unsnooze = useAppStore((s) => s.unsnoozePerfRec);
    const markReview = useAppStore((s) => s.markPerfReviewStarted);
    if (!rec) return null;
    return (
        <RightDrawer
            open={open}
            onOpenChange={onOpenChange}
            title={rec.title}
            description={`${rec.kind} · ${rec.object}`}
            size="lg"
            footer={
                <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                    <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="sm">
                                <MoreHorizontal className="h-4 w-4" />
                            </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="start">
                            {dismissReasons.map((r) => (
                                <DropdownMenuItem
                                    key={r}
                                    onClick={() => {
                                        dismiss(rec.id, r);
                                        toast.success(`Dismissed: ${r}`, {
                                            action: {
                                                label: "Undo",
                                                onClick: () => undismiss(rec.id),
                                            },
                                        });
                                        onOpenChange(false);
                                    }}
                                >
                                    Dismiss — {r}
                                </DropdownMenuItem>
                            ))}
                            <DropdownMenuItem
                                onClick={() => {
                                    snooze(
                                        rec.id,
                                        new Date(Date.now() + 3 * 86_400_000).toISOString(),
                                    );
                                    toast.success("Snoozed 3 days", {
                                        action: {
                                            label: "Undo",
                                            onClick: () => unsnooze(rec.id),
                                        },
                                    });
                                    onOpenChange(false);
                                }}
                            >
                                Snooze 3 days
                            </DropdownMenuItem>
                            <DropdownMenuItem
                                onClick={() => {
                                    markReview(rec.id);
                                    toast.success("Review started");
                                }}
                            >
                                Mark review started
                            </DropdownMenuItem>
                        </DropdownMenuContent>
                    </DropdownMenu>
                    <div className="flex flex-wrap items-center gap-2">
                        {onGenerateVariants && rec.group === "Scale" && (
                            <Button
                                size="sm"
                                variant="secondary"
                                onClick={() => onGenerateVariants(rec)}
                            >
                                Create variants
                            </Button>
                        )}
                        <Button
                            size="sm"
                            onClick={() => {
                                accept(rec.id);
                                toast.success("Recommendation accepted", {
                                    action: {
                                        label: "Undo",
                                        onClick: () => unaccept(rec.id),
                                    },
                                });
                                onOpenChange(false);
                            }}
                        >
                            Accept recommendation
                        </Button>
                    </div>
                </div>
            }
        >
            <div className="space-y-5">
                {rec.mediaUrl && (
                    <DemoMediaTile
                        mediaUrl={rec.mediaUrl}
                        mediaKind={rec.mediaKind}
                        posterUrl={rec.posterUrl}
                        seed={rec.objectId ?? rec.id}
                        label={rec.object}
                        badges={[rec.mediaAspectRatio ?? "media", rec.objectType]}
                        aspect={rec.mediaAspectRatio ?? "16 / 9"}
                        fit={rec.mediaAspectRatio === "9:16" ? "contain" : "cover"}
                        controls={rec.mediaKind === "video"}
                        className="rounded-md bg-black"
                    />
                )}
                <div className="flex flex-wrap items-center gap-2">
                    <StatusChip tone={decisionTone[rec.group]}>{rec.kind}</StatusChip>
                    <StatusChip
                        tone={
                            rec.confidence === "High"
                                ? "ok"
                                : rec.confidence === "Medium"
                                  ? "info"
                                  : "warn"
                        }
                    >
                        Confidence: {rec.confidence}
                    </StatusChip>
                </div>

                <Section title="Business impact">
                    <p className="text-sm text-text-primary">
                        <span className="font-medium">Demo scenario estimate:</span>{" "}
                        {rec.estimatedImpact}
                    </p>
                </Section>

                <Section title="Reason">
                    <p className="text-sm text-text-secondary">{rec.reason}</p>
                </Section>

                <Section title="Evidence">
                    <ul className="space-y-1.5">
                        {rec.evidence.map((e) => (
                            <li key={e} className="flex gap-2 text-sm text-text-secondary">
                                <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-text-tertiary" />
                                {e}
                            </li>
                        ))}
                    </ul>
                </Section>

                <Section title="Supporting metrics">
                    <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                        {rec.supportingMetrics.map((m) => (
                            <div key={m.label} className="rounded-md border border-hairline p-2.5">
                                <p className="text-[10px] uppercase text-text-tertiary">
                                    {m.label}
                                </p>
                                <p className="tabular text-sm font-semibold text-text-primary">
                                    {m.value}
                                </p>
                            </div>
                        ))}
                    </div>
                </Section>

                {rec.assumptions && rec.assumptions.length > 0 && (
                    <Section title="Assumptions">
                        <ul className="space-y-1 text-sm text-text-secondary">
                            {rec.assumptions.map((a) => (
                                <li key={a}>· {a}</li>
                            ))}
                        </ul>
                    </Section>
                )}

                {rec.missingData && rec.missingData.length > 0 && (
                    <Section title="Missing data">
                        <ul className="space-y-1 text-sm text-warn">
                            {rec.missingData.map((a) => (
                                <li key={a}>· {a}</li>
                            ))}
                        </ul>
                    </Section>
                )}

                <Separator />
                <Section title="Next action">
                    <p className="text-sm text-text-primary">{rec.nextAction}</p>
                </Section>
            </div>
        </RightDrawer>
    );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
    return (
        <div>
            <p className="mb-1.5 text-xs font-medium uppercase text-text-tertiary">{title}</p>
            {children}
        </div>
    );
}
