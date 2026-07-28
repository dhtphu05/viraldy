import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/shared/ui/dialog";
import { Button } from "@/shared/ui/button";
import { useAppStore } from "@/app/store/app-store";
import { analysisSteps } from "@/features/creative-library/lib/mockAnalysis";
import { ProcessingStepper, type Step } from "@/shared/ui/processing-stepper";
import { useMemo } from "react";
import { useNavigate } from "@tanstack/react-router";
import { toast } from "sonner";
import type { CreativeReference } from "@/features/creative-library/types/creative";

export function AnalyzeDnaDialog({
    open,
    onOpenChange,
    creativeIds,
}: {
    open: boolean;
    onOpenChange: (v: boolean) => void;
    creativeIds: string[];
}) {
    const jobs = useAppStore((s) => s.analysisJobs);
    const creatives = useAppStore((s) => s.creatives);
    const startJob = useAppStore((s) => s.startAnalysisJob);
    const navigate = useNavigate();

    const targets = useMemo<CreativeReference[]>(
        () => creatives.filter((c) => creativeIds.includes(c.id)),
        [creatives, creativeIds],
    );
    const primary = targets[0];
    const job = primary ? jobs[primary.id] : undefined;

    // Complete when this creative is analyzed (no longer processing)
    const analyzedIds = targets.filter((c) => c.analysisStatus === "analyzed").map((c) => c.id);
    const allDone = targets.length > 0 && analyzedIds.length === targets.length;

    function start() {
        if (targets.length === 0) return;
        for (const c of targets) {
            startJob(c.id, analysisSteps.length);
        }
        if (targets.length > 1) {
            toast(`Analyzing ${targets.length} creatives`);
        }
    }

    function runInBackground() {
        onOpenChange(false);
        toast("Running in background", {
            description: "You'll see progress on the card and get a toast when it completes.",
        });
    }

    function openResult() {
        if (!primary) return;
        onOpenChange(false);
        navigate({ to: "/creative-library/$creativeId", params: { creativeId: primary.id } });
    }

    const stepIndex = job?.step ?? 0;
    const total = analysisSteps.length;
    const stepper: Step[] = analysisSteps.map((s, i) => ({
        key: s.key,
        label: s.label,
        status:
            allDone || (job && i < stepIndex)
                ? "done"
                : job && i === stepIndex
                  ? "active"
                  : "pending",
    }));

    const running = !!job;

    return (
        <Dialog
            open={open}
            onOpenChange={(v) => (running ? v || onOpenChange(false) : onOpenChange(v))}
        >
            <DialogContent className="sm:max-w-[520px]">
                <DialogHeader>
                    <DialogTitle>
                        {allDone
                            ? "Analysis complete"
                            : running
                              ? "Analyzing Creative DNA"
                              : targets.length > 1
                                ? `Analyze ${targets.length} creatives`
                                : "Analyze Creative DNA"}
                    </DialogTitle>
                    <DialogDescription>
                        {allDone
                            ? "You can review the breakdown, evidence, and adaptation notes."
                            : running
                              ? "Viraldy is decoding the hook, product reveal, and adaptation signals."
                              : "We'll extract hook, reveal, proof, offer, and CTA structure — then suggest what to keep, change, and avoid."}
                    </DialogDescription>
                </DialogHeader>

                {!running && !allDone && primary && (
                    <div className="rounded-md bg-surface-soft/70 p-3 text-sm">
                        <p className="font-medium text-text-primary">{primary.title}</p>
                        <p className="mt-0.5 text-xs text-text-secondary">
                            {primary.platform} · {primary.durationSec}s · {primary.angle}
                        </p>
                        {targets.length > 1 && (
                            <p className="mt-2 text-xs text-text-tertiary">
                                + {targets.length - 1} more selected
                            </p>
                        )}
                    </div>
                )}

                {running && !allDone && (
                    <div className="py-1">
                        <ProcessingStepper steps={stepper} />
                    </div>
                )}

                {allDone && primary && (
                    <div className="rounded-md bg-ok-soft p-3 text-sm text-ok">
                        Creative DNA extracted for “{primary.title}”. Review the breakdown to decide
                        what to keep, change, or avoid.
                    </div>
                )}

                <DialogFooter className="mt-2">
                    {!running && !allDone && (
                        <>
                            <Button
                                type="button"
                                variant="ghost"
                                onClick={() => onOpenChange(false)}
                            >
                                Cancel
                            </Button>
                            <Button type="button" onClick={start} disabled={targets.length === 0}>
                                Start analysis
                            </Button>
                        </>
                    )}
                    {running && !allDone && (
                        <>
                            <Button type="button" variant="ghost" onClick={runInBackground}>
                                Run in background
                            </Button>
                            <Button type="button" disabled>
                                Analyzing…
                            </Button>
                        </>
                    )}
                    {allDone && (
                        <>
                            <Button
                                type="button"
                                variant="ghost"
                                onClick={() => onOpenChange(false)}
                            >
                                Close
                            </Button>
                            <Button type="button" onClick={openResult}>
                                Open analysis
                            </Button>
                        </>
                    )}
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
