import { useEffect, useRef } from "react";
import { toast } from "sonner";
import { useAppStore } from "@/app/store/app-store";
import { buildMockAnalysis, analysisSteps } from "@/features/creative-library/lib/mockAnalysis";
import { getAnalysisJobFeedback } from "@/features/creative-library/lib/analysis-job-feedback";

// Drives any creative that is in `processing` state forward, whether the
// analyze dialog is currently open or was closed via "Run in background".
export function useAnalysisJobsRunner() {
    const jobs = useAppStore((s) => s.analysisJobs);
    const creatives = useAppStore((s) => s.creatives);
    const advance = useAppStore((s) => s.advanceAnalysisJob);
    const save = useAppStore((s) => s.saveAnalysis);
    const timersRef = useRef<Record<string, number>>({});

    useEffect(() => {
        const active = Object.keys(jobs);
        for (const id of active) {
            const creative = creatives.find((item) => item.id === id);
            if (creative) {
                const feedback = getAnalysisJobFeedback(
                    id,
                    creative.title,
                    jobs[id].step,
                    jobs[id].total,
                );
                toast.loading(feedback.title, {
                    id: feedback.id,
                    description: feedback.description,
                });
            }
            if (timersRef.current[id]) continue;
            timersRef.current[id] = window.setInterval(() => {
                const j = useAppStore.getState().analysisJobs[id];
                if (!j) {
                    window.clearInterval(timersRef.current[id]);
                    delete timersRef.current[id];
                    return;
                }
                if (j.step >= j.total - 1) {
                    const cr = useAppStore.getState().creatives.find((c) => c.id === id);
                    if (cr) {
                        save(buildMockAnalysis(cr));
                        const feedback = getAnalysisJobFeedback(id, cr.title, j.total, j.total);
                        toast.success(feedback.title, {
                            id: feedback.id,
                            description: feedback.description,
                            duration: 5000,
                        });
                    }
                    window.clearInterval(timersRef.current[id]);
                    delete timersRef.current[id];
                } else {
                    advance(id);
                }
            }, 700);
        }
        // cleanup timers for jobs that disappeared
        for (const id of Object.keys(timersRef.current)) {
            if (!jobs[id]) {
                window.clearInterval(timersRef.current[id]);
                delete timersRef.current[id];
            }
        }
        return () => {};
    }, [jobs, advance, save, creatives]);

    useEffect(
        () => () => {
            for (const timer of Object.values(timersRef.current)) {
                window.clearInterval(timer);
            }
            timersRef.current = {};
        },
        [],
    );
}

export function AnalysisJobsRunner() {
    useAnalysisJobsRunner();
    return null;
}

export { analysisSteps };
