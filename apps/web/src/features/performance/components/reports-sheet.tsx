import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from "@/shared/ui/sheet";
import { Button } from "@/shared/ui/button";
import { StatusChip } from "@/shared/ui/status-chip";
import { RelativeTime } from "@/shared/ui/relative-time";
import { useAppStore } from "@/app/store/app-store";
import { downloadBlob } from "@/features/performance/lib/performanceEngine";
import { toast } from "sonner";
import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
    AlertDialogTrigger,
} from "@/shared/ui/alert-dialog";
import { FileDown, Copy, Trash2 } from "lucide-react";
import { seedRecommendations } from "@/features/performance/mocks/performanceSeed";

export function ReportsSheet({
    open,
    onOpenChange,
}: {
    open: boolean;
    onOpenChange: (v: boolean) => void;
}) {
    const reports = useAppStore((s) => s.perfReports);
    const deleteReport = useAppStore((s) => s.deletePerfReport);
    const addReport = useAppStore((s) => s.addPerfReport);

    return (
        <Sheet open={open} onOpenChange={onOpenChange}>
            <SheetContent side="right" className="flex w-full flex-col p-0 sm:max-w-lg">
                <SheetHeader className="border-b border-hairline px-6 py-4">
                    <SheetTitle>Reports</SheetTitle>
                    <SheetDescription>
                        Weekly decision reports and saved performance snapshots.
                    </SheetDescription>
                </SheetHeader>
                <div className="min-h-0 flex-1 overflow-y-auto px-6 py-4">
                    <div className="space-y-3">
                        {reports.map((r) => (
                            <div key={r.id} className="rounded-md border border-hairline p-3">
                                <div className="flex items-start justify-between gap-3">
                                    <div className="min-w-0">
                                        <p className="truncate text-sm font-medium">{r.name}</p>
                                        <p className="mt-0.5 truncate text-xs text-text-secondary">
                                            {r.scope} · {r.dateRange}
                                        </p>
                                    </div>
                                    <StatusChip
                                        tone={
                                            r.status === "Ready"
                                                ? "ok"
                                                : r.status === "Stale"
                                                  ? "warn"
                                                  : "info"
                                        }
                                    >
                                        {r.status}
                                    </StatusChip>
                                </div>
                                <div className="mt-2 flex items-center justify-between">
                                    <p className="text-xs text-text-tertiary">
                                        {r.includedAssets} assets · updated{" "}
                                        <RelativeTime value={r.lastGenerated} />
                                    </p>
                                    <div className="flex items-center gap-1">
                                        <Button
                                            size="sm"
                                            variant="ghost"
                                            onClick={() => {
                                                const text = seedRecommendations
                                                    .map(
                                                        (rec) =>
                                                            `${rec.kind.toUpperCase()} — ${rec.title}\nReason: ${rec.reason}\n`,
                                                    )
                                                    .join("\n");
                                                downloadBlob(
                                                    `${r.name.toLowerCase().replace(/\s+/g, "-")}.txt`,
                                                    text,
                                                );
                                                toast.success("Report exported");
                                            }}
                                        >
                                            <FileDown className="h-3.5 w-3.5" />
                                        </Button>
                                        <Button
                                            size="sm"
                                            variant="ghost"
                                            onClick={() => {
                                                addReport({
                                                    ...r,
                                                    id: `rp-${Date.now()}`,
                                                    name: `${r.name} (copy)`,
                                                    lastGenerated: new Date().toISOString(),
                                                });
                                                toast.success("Report duplicated");
                                            }}
                                        >
                                            <Copy className="h-3.5 w-3.5" />
                                        </Button>
                                        <AlertDialog>
                                            <AlertDialogTrigger asChild>
                                                <Button size="sm" variant="ghost">
                                                    <Trash2 className="h-3.5 w-3.5" />
                                                </Button>
                                            </AlertDialogTrigger>
                                            <AlertDialogContent>
                                                <AlertDialogHeader>
                                                    <AlertDialogTitle>
                                                        Delete this report?
                                                    </AlertDialogTitle>
                                                    <AlertDialogDescription>
                                                        The local report will be removed. Seeded
                                                        reports return on Reset Demo Data.
                                                    </AlertDialogDescription>
                                                </AlertDialogHeader>
                                                <AlertDialogFooter>
                                                    <AlertDialogCancel>Cancel</AlertDialogCancel>
                                                    <AlertDialogAction
                                                        onClick={() => {
                                                            deleteReport(r.id);
                                                            toast.success("Report deleted");
                                                        }}
                                                    >
                                                        Delete
                                                    </AlertDialogAction>
                                                </AlertDialogFooter>
                                            </AlertDialogContent>
                                        </AlertDialog>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </SheetContent>
        </Sheet>
    );
}
