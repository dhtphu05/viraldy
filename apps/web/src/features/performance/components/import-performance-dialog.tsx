import { useState, useMemo } from "react";
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogDescription,
    DialogFooter,
} from "@/shared/ui/dialog";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/shared/ui/tabs";
import { Button } from "@/shared/ui/button";
import { Textarea } from "@/shared/ui/textarea";
import { Input } from "@/shared/ui/input";
import { Label } from "@/shared/ui/label";
import { StatusChip } from "@/shared/ui/status-chip";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/shared/ui/select";
import { useAppStore } from "@/app/store/app-store";
import {
    parseCsv,
    canonicalFields,
    requiredFields,
} from "@/features/performance/lib/performanceEngine";
import { humanizeLabel } from "@/shared/lib/display";
import { toast } from "sonner";
import { UploadCloud, FileText, Sparkles, CheckCircle2, AlertTriangle } from "lucide-react";

const demoDatasets = [
    { id: "d-kitchen", name: "Kitchen Organizer performance", rows: 42 },
    { id: "d-dog", name: "Dog Mom Holiday campaign", rows: 36 },
    { id: "d-beauty", name: "Beauty Mirror creator test", rows: 24 },
    { id: "d-pet", name: "Pet Hair Roller affiliate test", rows: 18 },
];

type Step = "source" | "preview" | "map" | "assets" | "review";

export function ImportPerformanceDialog({
    open,
    onOpenChange,
}: {
    open: boolean;
    onOpenChange: (v: boolean) => void;
}) {
    const addPerfImport = useAppStore((s) => s.addPerfImport);
    const [tab, setTab] = useState<"csv" | "paste" | "demo">("csv");
    const [step, setStep] = useState<Step>("source");
    const [csvText, setCsvText] = useState("");
    const [pasted, setPasted] = useState("");
    const [demoId, setDemoId] = useState<string>("d-kitchen");
    const [mapping, setMapping] = useState<Record<string, string>>({});

    const parsed = useMemo(() => {
        if (tab === "csv") return csvText ? parseCsv(csvText) : { headers: [], rows: [] };
        if (tab === "paste") return pasted ? parseCsv(pasted) : { headers: [], rows: [] };
        return {
            headers: [...canonicalFields],
            rows: [{ asset_name: "demo", gmv: "1240", orders: "42" }],
        };
    }, [tab, csvText, pasted]);

    const onFile = async (file: File) => {
        const text = await file.text();
        setCsvText(text);
        setStep("preview");
    };

    const missingRequired = requiredFields.filter(
        (r) => !Object.values(mapping).includes(r) && !parsed.headers.includes(r),
    );

    const runImport = () => {
        const source = tab === "csv" ? "csv" : tab === "paste" ? "paste" : "demo";
        const name =
            tab === "demo"
                ? (demoDatasets.find((d) => d.id === demoId)?.name ?? "Demo dataset")
                : `Import ${new Date().toLocaleDateString()}`;
        const rowCount =
            tab === "demo"
                ? (demoDatasets.find((d) => d.id === demoId)?.rows ?? 0)
                : parsed.rows.length;
        const matched = Math.max(0, rowCount - 1 - (tab === "csv" ? 1 : 0));
        addPerfImport({
            id: `imp-${Date.now()}`,
            name,
            source: source as "csv" | "paste" | "demo",
            createdAt: new Date().toISOString(),
            rowCount,
            matched,
            unmatched: rowCount - matched,
            duplicates: tab === "csv" ? 1 : 0,
            missingFields: missingRequired as unknown as string[],
        });
        toast.success("Performance data imported", {
            description: `${rowCount} rows added locally.`,
        });
        onOpenChange(false);
        reset();
    };

    const reset = () => {
        setTab("csv");
        setStep("source");
        setCsvText("");
        setPasted("");
        setMapping({});
    };

    return (
        <Dialog
            open={open}
            onOpenChange={(v) => {
                onOpenChange(v);
                if (!v) reset();
            }}
        >
            <DialogContent className="flex max-h-[85vh] max-w-3xl flex-col p-0">
                <DialogHeader className="border-b border-hairline px-6 py-4">
                    <DialogTitle>Import performance data</DialogTitle>
                    <DialogDescription>
                        Bring TikTok Shop, Ads, or manually prepared CSV metrics into Viraldy. Runs
                        locally in your browser.
                    </DialogDescription>
                </DialogHeader>

                <div className="min-h-0 flex-1 overflow-y-auto px-6 py-4">
                    {step === "source" && (
                        <Tabs value={tab} onValueChange={(v) => setTab(v as typeof tab)}>
                            <TabsList className="grid w-full grid-cols-3">
                                <TabsTrigger value="csv">Upload CSV</TabsTrigger>
                                <TabsTrigger value="paste">Paste data</TabsTrigger>
                                <TabsTrigger value="demo">Use demo dataset</TabsTrigger>
                            </TabsList>

                            <TabsContent value="csv" className="mt-4">
                                <label className="flex cursor-pointer flex-col items-center justify-center gap-2 rounded-md border border-dashed border-hairline bg-surface-soft/50 p-8 text-center hover:bg-surface-soft">
                                    <UploadCloud className="h-6 w-6 text-text-tertiary" />
                                    <span className="text-sm font-medium">Choose a CSV file</span>
                                    <span className="text-xs text-text-tertiary">
                                        Max 5MB. Headers required.
                                    </span>
                                    <input
                                        type="file"
                                        accept=".csv,text/csv"
                                        className="hidden"
                                        onChange={(e) => {
                                            const f = e.target.files?.[0];
                                            if (f) onFile(f);
                                        }}
                                    />
                                </label>
                                {csvText && (
                                    <p className="mt-3 text-xs text-text-secondary">
                                        Loaded {parsed.rows.length} rows · {parsed.headers.length}{" "}
                                        columns
                                    </p>
                                )}
                            </TabsContent>

                            <TabsContent value="paste" className="mt-4">
                                <Label htmlFor="paste">Paste CSV-formatted text</Label>
                                <Textarea
                                    id="paste"
                                    className="mt-2 h-40 font-mono text-xs"
                                    placeholder="Asset Name,GMV,Orders&#10;Kitchen Organizer UGC V3,4920,246"
                                    value={pasted}
                                    onChange={(e) => setPasted(e.target.value)}
                                />
                                {pasted && (
                                    <p className="mt-2 text-xs text-text-secondary">
                                        Detected {parsed.headers.length} columns and{" "}
                                        {parsed.rows.length} rows.
                                    </p>
                                )}
                            </TabsContent>

                            <TabsContent value="demo" className="mt-4 space-y-3">
                                <Label>Choose a demo dataset</Label>
                                <Select value={demoId} onValueChange={setDemoId}>
                                    <SelectTrigger>
                                        <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                        {demoDatasets.map((d) => (
                                            <SelectItem key={d.id} value={d.id}>
                                                {d.name} · {d.rows} rows
                                            </SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                                <div className="flex items-start gap-2 rounded-md bg-info-soft p-3 text-xs text-info">
                                    <Sparkles className="mt-0.5 h-3.5 w-3.5" />
                                    Demo datasets seed campaign performance instantly. Ideal for
                                    first-time exploration.
                                </div>
                            </TabsContent>
                        </Tabs>
                    )}

                    {step === "preview" && (
                        <div>
                            <p className="text-sm font-medium">Preview columns</p>
                            <p className="text-xs text-text-tertiary">
                                First 3 rows of {parsed.rows.length}
                            </p>
                            <div className="mt-3 overflow-x-auto rounded-md border border-hairline">
                                <table className="w-full min-w-max text-xs">
                                    <thead className="bg-surface-soft">
                                        <tr>
                                            {parsed.headers.map((h) => (
                                                <th
                                                    key={h}
                                                    className="px-3 py-2 text-left font-medium"
                                                >
                                                    {humanizeLabel(h)}
                                                </th>
                                            ))}
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {parsed.rows.slice(0, 3).map((r, i) => (
                                            <tr key={i} className="border-t border-hairline">
                                                {parsed.headers.map((h) => (
                                                    <td
                                                        key={h}
                                                        className="px-3 py-2 text-text-secondary"
                                                    >
                                                        {r[h]}
                                                    </td>
                                                ))}
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    )}

                    {step === "map" && (
                        <div className="space-y-3">
                            <p className="text-sm font-medium">Map fields</p>
                            <p className="text-xs text-text-tertiary">
                                Match your columns to Viraldy fields. Required: Asset name, GMV,
                                Orders.
                            </p>
                            <div className="space-y-2">
                                {parsed.headers.map((h) => (
                                    <div
                                        key={h}
                                        className="grid grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)_auto] items-center gap-3 rounded-md border border-hairline px-3 py-2"
                                    >
                                        <span className="truncate text-sm">{humanizeLabel(h)}</span>
                                        <span className="text-text-tertiary">→</span>
                                        <Select
                                            value={
                                                (mapping[h] ??
                                                (canonicalFields as readonly string[]).includes(h))
                                                    ? h
                                                    : "__ignore"
                                            }
                                            onValueChange={(v) =>
                                                setMapping((m) => ({ ...m, [h]: v }))
                                            }
                                        >
                                            <SelectTrigger className="h-8">
                                                <SelectValue placeholder="Ignore" />
                                            </SelectTrigger>
                                            <SelectContent>
                                                <SelectItem value="__ignore">Ignore</SelectItem>
                                                {canonicalFields.map((f) => (
                                                    <SelectItem key={f} value={f}>
                                                        {humanizeLabel(f)}
                                                    </SelectItem>
                                                ))}
                                            </SelectContent>
                                        </Select>
                                        <StatusChip
                                            tone={
                                                (requiredFields as readonly string[]).includes(h)
                                                    ? "warn"
                                                    : "neutral"
                                            }
                                        >
                                            {(requiredFields as readonly string[]).includes(h)
                                                ? "Required"
                                                : "Optional"}
                                        </StatusChip>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {step === "assets" && (
                        <div className="space-y-3">
                            <p className="text-sm font-medium">Map assets</p>
                            <p className="text-xs text-text-tertiary">
                                Auto-matched to existing library where possible.
                            </p>
                            <div className="rounded-md border border-hairline">
                                <div className="grid grid-cols-[minmax(0,2fr)_auto_minmax(0,2fr)_auto] items-center gap-3 border-b border-hairline bg-surface-soft px-3 py-2 text-xs font-medium text-text-tertiary">
                                    <span>Source row</span>
                                    <span>→</span>
                                    <span>Matched to</span>
                                    <span>Status</span>
                                </div>
                                {parsed.rows.slice(0, 5).map((r, i) => (
                                    <div
                                        key={i}
                                        className="grid grid-cols-[minmax(0,2fr)_auto_minmax(0,2fr)_auto] items-center gap-3 border-b border-hairline px-3 py-2 text-xs last:border-b-0"
                                    >
                                        <span className="truncate">
                                            {r.asset_name ?? r.asset_id ?? `Row ${i + 1}`}
                                        </span>
                                        <span className="text-text-tertiary">→</span>
                                        <span className="truncate text-text-secondary">
                                            Kitchen Organizer UGC V{(i % 3) + 1}
                                        </span>
                                        <StatusChip tone={i === 3 ? "warn" : "ok"}>
                                            {i === 3 ? "Unmatched" : "Auto-matched"}
                                        </StatusChip>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {step === "review" && (
                        <div className="space-y-3">
                            <p className="text-sm font-medium">Review import</p>
                            <div className="grid grid-cols-2 gap-3">
                                <div className="rounded-md border border-hairline p-3">
                                    <p className="text-xs text-text-tertiary">Rows to import</p>
                                    <p className="text-lg font-semibold">{parsed.rows.length}</p>
                                </div>
                                <div className="rounded-md border border-hairline p-3">
                                    <p className="text-xs text-text-tertiary">Missing required</p>
                                    <p className="text-lg font-semibold">
                                        {missingRequired.length}
                                    </p>
                                </div>
                            </div>
                            {missingRequired.length > 0 ? (
                                <div className="flex items-start gap-2 rounded-md bg-warn-soft p-3 text-xs text-warn">
                                    <AlertTriangle className="mt-0.5 h-3.5 w-3.5" />
                                    Some rows are missing required fields. They will import as
                                    partial data.
                                </div>
                            ) : (
                                <div className="flex items-start gap-2 rounded-md bg-ok-soft p-3 text-xs text-ok">
                                    <CheckCircle2 className="mt-0.5 h-3.5 w-3.5" />
                                    All required fields resolved. Ready to import.
                                </div>
                            )}
                        </div>
                    )}
                </div>

                <DialogFooter className="flex items-center justify-between gap-2 border-t border-hairline bg-surface-soft/40 px-6 py-3">
                    <div className="flex items-center gap-2 text-xs text-text-tertiary">
                        <FileText className="h-3.5 w-3.5" /> Step: {humanizeLabel(step)}
                    </div>
                    <div className="flex items-center gap-2">
                        {step !== "source" && (
                            <Button variant="ghost" size="sm" onClick={() => setStep(prev)}>
                                Back
                            </Button>
                        )}
                        {step !== "review" ? (
                            <Button size="sm" onClick={() => setStep(nextStep(step, tab))}>
                                Continue
                            </Button>
                        ) : (
                            <Button size="sm" onClick={runImport}>
                                Import locally
                            </Button>
                        )}
                    </div>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );

    function nextStep(cur: Step, currentTab: typeof tab): Step {
        if (cur === "source") return currentTab === "demo" ? "review" : "preview";
        if (cur === "preview") return "map";
        if (cur === "map") return "assets";
        return "review";
    }
    function prev(): Step {
        if (step === "review") return tab === "demo" ? "source" : "assets";
        if (step === "assets") return "map";
        if (step === "map") return "preview";
        return "source";
    }
}
