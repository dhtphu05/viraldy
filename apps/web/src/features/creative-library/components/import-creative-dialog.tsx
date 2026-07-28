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
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/shared/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/shared/ui/select";
import { Link2, Upload, FileVideo, X, ImageIcon } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useAppStore } from "@/app/store/app-store";
import { toast } from "sonner";
import type {
    CreativeReference,
    CreativePlatform,
    CreativeAngle,
    ProductCategory,
} from "@/features/creative-library/types/creative";
import { thumbnailGradient } from "@/features/creative-library/lib/creative-visuals";
import { useNavigate } from "@tanstack/react-router";
import { cn } from "@/shared/lib/utils";

const urlSchema = z.object({
    url: z
        .string()
        .min(4, "Paste a URL")
        .refine((v) => /^https?:\/\/.+/.test(v), "Enter a valid https:// URL"),
    platform: z.enum(["TikTok", "Meta", "YouTube Shorts", "UGC", "Other"]),
    board: z.string().min(1, "Choose a board"),
    notes: z.string().optional(),
});
type UrlValues = z.infer<typeof urlSchema>;

const demoOptions: {
    id: string;
    title: string;
    hook: string;
    seed: string;
    angle: CreativeAngle;
    category: ProductCategory;
    platform: CreativePlatform;
    dur: number;
}[] = [
    {
        id: "d1",
        title: "Kitchen counter problem–solution",
        hook: "This counter after 2 kids and a Costco run.",
        seed: "coral",
        angle: "Problem–solution",
        category: "Home & Kitchen",
        platform: "TikTok",
        dur: 24,
    },
    {
        id: "d2",
        title: "Dog Mom personalized gift reaction",
        hook: "He finally got me the right gift.",
        seed: "peach",
        angle: "Gift reaction",
        category: "POD Gifts",
        platform: "TikTok",
        dur: 32,
    },
    {
        id: "d3",
        title: "Beauty mirror morning routine",
        hook: "The mirror I take everywhere.",
        seed: "blush",
        angle: "Day-in-the-life",
        category: "Beauty",
        platform: "TikTok",
        dur: 40,
    },
    {
        id: "d4",
        title: "Pet hair roller before-and-after",
        hook: "I'll never buy sticky rollers again.",
        seed: "mint",
        angle: "Before-and-after",
        category: "Pet",
        platform: "Meta",
        dur: 18,
    },
    {
        id: "d5",
        title: "Home organizer creator testimonial",
        hook: "Three months in, here's what stayed organized.",
        seed: "sage",
        angle: "Testimonial",
        category: "Home Organization",
        platform: "TikTok",
        dur: 46,
    },
    {
        id: "d6",
        title: "Product comparison — 4 mirrors",
        hook: "I bought all 4 viral mirrors so you don't have to.",
        seed: "lavender",
        angle: "Comparison",
        category: "Beauty",
        platform: "YouTube Shorts",
        dur: 55,
    },
];

function seedFromPlatform(p: CreativePlatform): string {
    switch (p) {
        case "TikTok":
            return "rose";
        case "Meta":
            return "sky";
        case "YouTube Shorts":
            return "lilac";
        case "UGC":
            return "amber";
        default:
            return "stone";
    }
}

export function ImportCreativeDialog({
    open,
    onOpenChange,
    defaultBoardId,
    onImported,
}: {
    open: boolean;
    onOpenChange: (v: boolean) => void;
    defaultBoardId?: string;
    onImported?: (c: CreativeReference) => void;
}) {
    const boards = useAppStore((s) => s.boards);
    const addCreative = useAppStore((s) => s.addCreative);
    const navigate = useNavigate();
    const [tab, setTab] = useState("url");
    const [file, setFile] = useState<File | null>(null);
    const [fileUrl, setFileUrl] = useState<string | null>(null);
    const [fileErr, setFileErr] = useState<string | null>(null);
    const [demoId, setDemoId] = useState<string | null>(null);
    const [submitting, setSubmitting] = useState(false);

    const boardOptions = useMemo(
        () => boards.filter((b) => !b.system || b.id === "b-all"),
        [boards],
    );
    const defaultBoard =
        defaultBoardId && boardOptions.some((b) => b.id === defaultBoardId)
            ? defaultBoardId
            : (boardOptions.find((b) => !b.system)?.id ?? "b-all");

    const form = useForm<UrlValues>({
        resolver: zodResolver(urlSchema),
        defaultValues: { url: "", platform: "TikTok", board: defaultBoard, notes: "" },
    });

    useEffect(() => {
        if (open) {
            setTab("url");
            setFile(null);
            setFileErr(null);
            setDemoId(null);
            form.reset({ url: "", platform: "TikTok", board: defaultBoard, notes: "" });
        } else if (fileUrl) {
            URL.revokeObjectURL(fileUrl);
            setFileUrl(null);
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [open]);

    function handleFile(f: File | null) {
        if (!f) {
            setFile(null);
            if (fileUrl) URL.revokeObjectURL(fileUrl);
            setFileUrl(null);
            return;
        }
        const allowed = ["mp4", "mov", "webm", "jpg", "jpeg", "png", "webp"];
        const ext = f.name.split(".").pop()?.toLowerCase() ?? "";
        if (!allowed.includes(ext)) {
            setFileErr("Use mp4, mov, webm, jpg, png, or webp.");
            return;
        }
        if (f.size > 50 * 1024 * 1024) {
            setFileErr("File must be under 50MB.");
            return;
        }
        setFileErr(null);
        setFile(f);
        if (fileUrl) URL.revokeObjectURL(fileUrl);
        setFileUrl(URL.createObjectURL(f));
    }

    function finish(cr: CreativeReference, message: string) {
        addCreative(cr);
        toast.success(message, { description: cr.title });
        onOpenChange(false);
        onImported?.(cr);
    }

    async function submitUrl(v: UrlValues) {
        setSubmitting(true);
        const now = new Date().toISOString();
        const cr: CreativeReference = {
            id: `cr-${Date.now()}`,
            title: v.notes?.slice(0, 60) || `Imported ${v.platform} reference`,
            hookExcerpt: v.notes || "Demo import — analyze to extract the hook.",
            platform: v.platform,
            durationSec: 24,
            brandOrCreator: new URL(v.url).hostname.replace("www.", ""),
            angle: "Problem–solution",
            category: "Home & Kitchen",
            tags: ["demo-import"],
            notes: v.notes,
            boardIds: v.board === "b-all" ? [] : [v.board],
            analysisStatus: "ready",
            savedAt: now,
            thumbSeed: seedFromPlatform(v.platform),
        };
        setSubmitting(false);
        finish(cr, "Reference imported");
        setTimeout(
            () => navigate({ to: "/creative-library/$creativeId", params: { creativeId: cr.id } }),
            60,
        );
    }

    function submitFile() {
        if (!file) {
            setFileErr("Choose a file first.");
            return;
        }
        const now = new Date().toISOString();
        const cr: CreativeReference = {
            id: `cr-${Date.now()}`,
            title: file.name.replace(/\.[^.]+$/, ""),
            hookExcerpt: "Uploaded reference — analyze to extract the hook.",
            platform: "UGC",
            durationSec: 22,
            brandOrCreator: "Local upload",
            angle: "Testimonial",
            category: "Home & Kitchen",
            tags: ["upload"],
            boardIds: defaultBoard === "b-all" ? [] : [defaultBoard],
            analysisStatus: "ready",
            savedAt: now,
            thumbSeed: "amber",
        };
        finish(cr, "File imported");
    }

    function submitDemo() {
        const d = demoOptions.find((x) => x.id === demoId);
        if (!d) return;
        const cr: CreativeReference = {
            id: `cr-${Date.now()}`,
            title: d.title,
            hookExcerpt: d.hook,
            platform: d.platform,
            durationSec: d.dur,
            brandOrCreator: "Demo reference",
            angle: d.angle,
            category: d.category,
            tags: ["demo"],
            boardIds: defaultBoard === "b-all" ? [] : [defaultBoard],
            analysisStatus: "ready",
            savedAt: new Date().toISOString(),
            thumbSeed: d.seed,
        };
        finish(cr, "Demo creative added");
    }

    return (
        <Dialog open={open} onOpenChange={submitting ? undefined : onOpenChange}>
            <DialogContent className="flex max-h-[calc(100dvh-4rem)] flex-col overflow-hidden sm:max-w-[600px]">
                <DialogHeader>
                    <DialogTitle>Import creative</DialogTitle>
                    <DialogDescription>
                        Paste a link, upload a file, or start from a demo reference. Frontend-only —
                        nothing is uploaded to a server.
                    </DialogDescription>
                </DialogHeader>

                <Tabs value={tab} onValueChange={setTab} className="flex min-h-0 flex-1 flex-col">
                    <TabsList className="grid w-full grid-cols-3">
                        <TabsTrigger value="url">Paste URL</TabsTrigger>
                        <TabsTrigger value="file">Upload file</TabsTrigger>
                        <TabsTrigger value="demo">Demo creative</TabsTrigger>
                    </TabsList>

                    <div className="min-h-0 flex-1 overflow-y-auto pr-1">
                        <TabsContent value="url" className="mt-4">
                            <form
                                id="import-url-form"
                                onSubmit={form.handleSubmit(submitUrl)}
                                className="flex flex-col gap-4"
                            >
                                <div className="grid gap-1.5">
                                    <Label htmlFor="url">Creative URL</Label>
                                    <div className="relative">
                                        <Link2 className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-tertiary" />
                                        <Input
                                            id="url"
                                            className="pl-9"
                                            placeholder="https://tiktok.com/@creator/video/…"
                                            {...form.register("url")}
                                        />
                                    </div>
                                    {form.formState.errors.url && (
                                        <p className="text-xs text-destructive">
                                            {form.formState.errors.url.message}
                                        </p>
                                    )}
                                    <p className="text-[11px] text-text-tertiary">
                                        Demo import — Viraldy does not fetch external videos in this
                                        preview.
                                    </p>
                                </div>

                                <div className="grid gap-3 sm:grid-cols-2">
                                    <div className="grid gap-1.5">
                                        <Label>Source platform</Label>
                                        <Select
                                            value={form.watch("platform")}
                                            onValueChange={(v) =>
                                                form.setValue("platform", v as CreativePlatform)
                                            }
                                        >
                                            <SelectTrigger>
                                                <SelectValue />
                                            </SelectTrigger>
                                            <SelectContent>
                                                <SelectItem value="TikTok">TikTok</SelectItem>
                                                <SelectItem value="Meta">Meta</SelectItem>
                                                <SelectItem value="YouTube Shorts">
                                                    YouTube Shorts
                                                </SelectItem>
                                                <SelectItem value="UGC">UGC</SelectItem>
                                                <SelectItem value="Other">Other</SelectItem>
                                            </SelectContent>
                                        </Select>
                                    </div>
                                    <div className="grid gap-1.5">
                                        <Label>Board</Label>
                                        <Select
                                            value={form.watch("board")}
                                            onValueChange={(v) => form.setValue("board", v)}
                                        >
                                            <SelectTrigger>
                                                <SelectValue />
                                            </SelectTrigger>
                                            <SelectContent>
                                                {boardOptions.map((b) => (
                                                    <SelectItem key={b.id} value={b.id}>
                                                        {b.name}
                                                    </SelectItem>
                                                ))}
                                            </SelectContent>
                                        </Select>
                                    </div>
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
                            </form>
                        </TabsContent>

                        <TabsContent value="file" className="mt-4">
                            <div className="flex flex-col gap-3">
                                <label
                                    htmlFor="file-input"
                                    className={cn(
                                        "flex cursor-pointer flex-col items-center justify-center gap-2 rounded-md border border-dashed border-hairline bg-surface-soft/60 px-6 py-10 text-center transition-colors hover:bg-surface-soft",
                                    )}
                                >
                                    <Upload className="h-5 w-5 text-text-tertiary" />
                                    <p className="text-sm font-medium text-text-primary">
                                        Click to choose a file
                                    </p>
                                    <p className="text-xs text-text-tertiary">
                                        mp4, mov, webm, jpg, png, webp · up to 50MB
                                    </p>
                                    <input
                                        id="file-input"
                                        type="file"
                                        accept="video/mp4,video/quicktime,video/webm,image/jpeg,image/png,image/webp"
                                        className="sr-only"
                                        onChange={(e) => handleFile(e.target.files?.[0] ?? null)}
                                    />
                                </label>

                                {file && (
                                    <div className="flex items-center gap-3 rounded-md border border-hairline bg-surface p-3">
                                        <div className="grid h-14 w-14 shrink-0 place-items-center overflow-hidden rounded-md bg-surface-muted">
                                            {fileUrl && file.type.startsWith("image/") ? (
                                                <img
                                                    src={fileUrl}
                                                    alt=""
                                                    className="h-full w-full object-cover"
                                                />
                                            ) : file.type.startsWith("video/") ? (
                                                <FileVideo className="h-5 w-5 text-text-tertiary" />
                                            ) : (
                                                <ImageIcon className="h-5 w-5 text-text-tertiary" />
                                            )}
                                        </div>
                                        <div className="min-w-0 flex-1">
                                            <p className="truncate text-sm font-medium text-text-primary">
                                                {file.name}
                                            </p>
                                            <p className="text-xs text-text-tertiary">
                                                {(file.size / (1024 * 1024)).toFixed(1)} MB ·{" "}
                                                {file.type || "unknown"}
                                            </p>
                                        </div>
                                        <Button
                                            type="button"
                                            variant="ghost"
                                            size="icon"
                                            aria-label="Remove file"
                                            onClick={() => handleFile(null)}
                                        >
                                            <X className="h-4 w-4" />
                                        </Button>
                                    </div>
                                )}

                                {fileErr && <p className="text-xs text-destructive">{fileErr}</p>}
                            </div>
                        </TabsContent>

                        <TabsContent value="demo" className="mt-4">
                            <div className="grid gap-2 sm:grid-cols-2">
                                {demoOptions.map((d) => {
                                    const active = demoId === d.id;
                                    return (
                                        <button
                                            key={d.id}
                                            type="button"
                                            onClick={() => setDemoId(d.id)}
                                            aria-pressed={active}
                                            className={cn(
                                                "flex items-start gap-3 rounded-md border p-3 text-left transition-all focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring",
                                                active
                                                    ? "border-primary bg-primary-softer"
                                                    : "border-hairline bg-surface hover:bg-surface-soft",
                                            )}
                                        >
                                            <span
                                                className="h-12 w-12 shrink-0 rounded-md"
                                                style={{
                                                    backgroundImage: thumbnailGradient(d.seed),
                                                }}
                                                aria-hidden
                                            />
                                            <span className="min-w-0 flex-1">
                                                <span className="block truncate text-sm font-medium text-text-primary">
                                                    {d.title}
                                                </span>
                                                <span className="mt-0.5 line-clamp-2 text-xs text-text-secondary">
                                                    “{d.hook}”
                                                </span>
                                                <span className="mt-1 block text-[11px] text-text-tertiary">
                                                    {d.platform} · {d.angle}
                                                </span>
                                            </span>
                                        </button>
                                    );
                                })}
                            </div>
                        </TabsContent>
                    </div>
                </Tabs>

                <DialogFooter className="mt-2 shrink-0">
                    <Button type="button" variant="ghost" onClick={() => onOpenChange(false)}>
                        Cancel
                    </Button>
                    {tab === "url" && (
                        <Button
                            type="submit"
                            form="import-url-form"
                            disabled={submitting}
                            className="min-w-[140px]"
                        >
                            Import creative
                        </Button>
                    )}
                    {tab === "file" && (
                        <Button
                            type="button"
                            onClick={submitFile}
                            disabled={!file}
                            className="min-w-[140px]"
                        >
                            Import creative
                        </Button>
                    )}
                    {tab === "demo" && (
                        <Button
                            type="button"
                            onClick={submitDemo}
                            disabled={!demoId}
                            className="min-w-[140px]"
                        >
                            Import creative
                        </Button>
                    )}
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
