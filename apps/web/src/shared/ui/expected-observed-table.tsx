import type { ReactNode } from "react";

import { humanizeLabel } from "@/shared/lib/display";
import type { MetricTone } from "@/shared/types";
import { ConfidenceBadge } from "@/shared/ui/confidence-badge";
import { StatusChip } from "@/shared/ui/status-chip";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/shared/ui/table";

export type ExpectedObservedRow = {
    id: string;
    requirement: ReactNode;
    observed: ReactNode;
    status: string;
    confidence?: string;
    evidence?: ReactNode;
    action?: ReactNode;
};

function statusTone(status: string): MetricTone {
    const normalized = status.toLowerCase();
    if (normalized.includes("pass") || normalized.includes("met")) return "ok";
    if (normalized.includes("fail") || normalized.includes("missing")) return "destructive";
    if (normalized.includes("partial") || normalized.includes("warn")) return "warn";
    return "info";
}

export function ExpectedObservedTable({
    rows,
    emptyMessage = "No requirement alignment data is available yet.",
}: {
    rows: ExpectedObservedRow[];
    emptyMessage?: string;
}) {
    if (!rows.length) {
        return <p className="py-6 text-sm text-text-secondary">{emptyMessage}</p>;
    }

    return (
        <>
            <div className="space-y-3 sm:hidden">
                {rows.map((row) => (
                    <article key={row.id} className="rounded-2xl bg-surface-soft p-4">
                        <div className="flex flex-wrap items-center justify-between gap-2">
                            <StatusChip tone={statusTone(row.status)}>
                                {humanizeLabel(row.status)}
                            </StatusChip>
                            {row.confidence && <ConfidenceBadge level={row.confidence} />}
                        </div>
                        <p className="mt-3 text-xs font-medium uppercase text-text-tertiary">
                            Expected
                        </p>
                        <div className="mt-1 text-sm text-text-primary">{row.requirement}</div>
                        <p className="mt-3 text-xs font-medium uppercase text-text-tertiary">
                            Observed
                        </p>
                        <div className="mt-1 text-sm text-text-primary">{row.observed}</div>
                        {(row.evidence || row.action) && (
                            <div className="mt-3 border-t border-divider pt-3 text-sm text-text-secondary">
                                {row.evidence}
                                {row.action}
                            </div>
                        )}
                    </article>
                ))}
            </div>
            <div className="hidden overflow-hidden rounded-2xl border border-control-border bg-surface sm:block">
                <Table>
                    <TableHeader>
                        <TableRow>
                            <TableHead>Requirement</TableHead>
                            <TableHead>Observed</TableHead>
                            <TableHead>Status</TableHead>
                            <TableHead>Evidence / action</TableHead>
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {rows.map((row) => (
                            <TableRow key={row.id}>
                                <TableCell className="max-w-64 align-top">
                                    {row.requirement}
                                </TableCell>
                                <TableCell className="max-w-64 align-top">{row.observed}</TableCell>
                                <TableCell className="align-top">
                                    <div className="flex flex-col items-start gap-2">
                                        <StatusChip tone={statusTone(row.status)}>
                                            {humanizeLabel(row.status)}
                                        </StatusChip>
                                        {row.confidence && (
                                            <ConfidenceBadge level={row.confidence} />
                                        )}
                                    </div>
                                </TableCell>
                                <TableCell className="max-w-72 align-top text-text-secondary">
                                    {row.evidence}
                                    {row.action}
                                </TableCell>
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>
            </div>
        </>
    );
}
