import { useEffect, useRef } from "react";
import { useAppStore } from "@/app/store/app-store";
import { buildMockAnalysis, analysisSteps } from "@/features/creative-library/lib/mockAnalysis";

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
                    if (cr) save(buildMockAnalysis(cr));
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
}

export function AnalysisJobsRunner() {
    useAnalysisJobsRunner();
    return null;
}

export { analysisSteps };
