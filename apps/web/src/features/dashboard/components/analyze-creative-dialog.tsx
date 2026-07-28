import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/shared/ui/dialog";
import { Button } from "@/shared/ui/button";
import { Input } from "@/shared/ui/input";
import { Label } from "@/shared/ui/label";
import { Textarea } from "@/shared/ui/textarea";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useState } from "react";
import { ProcessingStepper, type Step } from "@/shared/ui/processing-stepper";
import { useAppStore } from "@/app/store/app-store";
import { toast } from "sonner";
import { Link2, Upload } from "lucide-react";

const schema = z.object({
    name: z.string().min(2, "Give this creative a name"),
    source: z.string().min(3, "Paste a link or add a note"),
    notes: z.string().optional(),
});
type Values = z.infer<typeof schema>;

export function AnalyzeCreativeDialog({
    open,
    onOpenChange,
}: {
    open: boolean;
    onOpenChange: (v: boolean) => void;
}) {
    const [steps, setSteps] = useState<Step[]>([]);
    const [processing, setProcessing] = useState(false);
    const addImport = useAppStore((s) => s.addDemoImport);

    const form = useForm<Values>({
        resolver: zodResolver(schema),
        defaultValues: { name: "", source: "", notes: "" },
    });

    async function onSubmit(v: Values) {
        setProcessing(true);
        const seq: Step[] = [
            { key: "fetch", label: "Fetching reference", status: "active" },
            { key: "frames", label: "Extracting key frames", status: "pending" },
            { key: "dna", label: "Analyzing Creative DNA", status: "pending" },
            { key: "match", label: "Matching to your products", status: "pending" },
        ];
        setSteps(seq);
        for (let i = 0; i < seq.length; i++) {
            await new Promise((r) => setTimeout(r, 550));
            setSteps((prev) =>
                prev.map((s, idx) =>
                    idx < i
                        ? { ...s, status: "done" }
                        : idx === i
                          ? { ...s, status: "done" }
                          : idx === i + 1
                            ? { ...s, status: "active" }
                            : s,
                ),
            );
        }
        addImport({
            id: `imp-${Date.now()}`,
            name: v.name,
            source: v.source,
            createdAt: new Date().toISOString(),
        });
        setProcessing(false);
        setSteps([]);
        form.reset();
        onOpenChange(false);
        toast.success("Creative analyzed", { description: `“${v.name}” added to library.` });
    }

    return (
        <Dialog
            open={open}
            onOpenChange={(v) => {
                if (!processing) onOpenChange(v);
            }}
        >
            <DialogContent className="sm:max-w-[520px]">
                <DialogHeader>
                    <DialogTitle>Analyze creative</DialogTitle>
                    <DialogDescription>
                        Paste a TikTok or reference link. Viraldy extracts Creative DNA and matches
                        it to your products.
                    </DialogDescription>
                </DialogHeader>

                {processing ? (
                    <div className="py-2">
                        <ProcessingStepper steps={steps} />
                    </div>
                ) : (
                    <form onSubmit={form.handleSubmit(onSubmit)} className="flex flex-col gap-4">
                        <div className="grid gap-1.5">
                            <Label htmlFor="name">Reference name</Label>
                            <Input
                                id="name"
                                placeholder="e.g. Under-cabinet problem-solve v3"
                                {...form.register("name")}
                            />
                            {form.formState.errors.name && (
                                <p className="text-xs text-destructive">
                                    {form.formState.errors.name.message}
                                </p>
                            )}
                        </div>
                        <div className="grid gap-1.5">
                            <Label htmlFor="source">Source</Label>
                            <div className="relative">
                                <Link2 className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-tertiary" />
                                <Input
                                    id="source"
                                    className="pl-9"
                                    placeholder="https://tiktok.com/…"
                                    {...form.register("source")}
                                />
                            </div>
                            {form.formState.errors.source && (
                                <p className="text-xs text-destructive">
                                    {form.formState.errors.source.message}
                                </p>
                            )}
                        </div>
                        <div className="grid gap-1.5">
                            <Label htmlFor="notes">Notes (optional)</Label>
                            <Textarea
                                id="notes"
                                rows={3}
                                placeholder="What caught your eye?"
                                {...form.register("notes")}
                            />
                        </div>
                        <DialogFooter className="mt-2">
                            <Button
                                type="button"
                                variant="ghost"
                                onClick={() => onOpenChange(false)}
                            >
                                Cancel
                            </Button>
                            <Button type="submit">
                                <Upload className="h-4 w-4" />
                                Analyze
                            </Button>
                        </DialogFooter>
                    </form>
                )}
            </DialogContent>
        </Dialog>
    );
}
