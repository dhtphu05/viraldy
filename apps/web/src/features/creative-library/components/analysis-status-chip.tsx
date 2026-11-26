import { StatusChip } from "@/shared/ui/status-chip";
import type { CreativeAnalysisStatus } from "@/features/creative-library/types/creative";
import type { MetricTone } from "@/shared/types";
import { Loader2 } from "lucide-react";

const map: Record<CreativeAnalysisStatus, { label: string; tone: MetricTone; spin?: boolean }> = {
    unanalyzed: { label: "Chưa phân tích", tone: "neutral" },
    ready: { label: "Sẵn sàng phân tích", tone: "info" },
    processing: { label: "Đang phân tích…", tone: "warn", spin: true },
    analyzed: { label: "Đã phân tích", tone: "ok" },
    failed: { label: "Phân tích chưa thành công", tone: "destructive" },
};

export function AnalysisStatusChip({ status }: { status: CreativeAnalysisStatus }) {
    const m = map[status];
    return (
        <StatusChip tone={m.tone} dot={!m.spin}>
            {m.spin && (
                <Loader2
                    className="h-3 w-3 animate-spin motion-reduce:animate-none"
                    aria-hidden="true"
                />
            )}
            {m.label}
        </StatusChip>
    );
}
