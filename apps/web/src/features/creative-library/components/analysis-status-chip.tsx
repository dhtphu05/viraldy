import { StatusChip } from "@/shared/ui/status-chip";
import type { CreativeAnalysisStatus } from "@/features/creative-library/types/creative";
import type { MetricTone } from "@/shared/types";
import { Loader2 } from "lucide-react";

const map: Record<CreativeAnalysisStatus, { label: string; tone: MetricTone; spin?: boolean }> = {
    unanalyzed: { label: "Unanalyzed", tone: "neutral" },
    ready: { label: "Ready to analyze", tone: "info" },
    processing: { label: "Analyzing…", tone: "warn", spin: true },
    analyzed: { label: "Analyzed", tone: "ok" },
    failed: { label: "Analysis failed", tone: "destructive" },
};

export function AnalysisStatusChip({ status }: { status: CreativeAnalysisStatus }) {
    const m = map[status];
    return (
        <StatusChip tone={m.tone} dot={!m.spin}>
            {m.spin && <Loader2 className="h-3 w-3 animate-spin" />}
            {m.label}
        </StatusChip>
    );
}
