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
import { useEffect, useMemo, useRef, useState } from "react";
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
import { DisabledActionHint } from "@/shared/ui/disabled-action-hint";
import { captureVideoPoster, posterForDemoUploadFilename } from "@/shared/lib/demo-media";

const urlSchema = z.object({
    url: z
        .string()
        .min(4, "Thêm link tham khảo nhé")
        .refine((v) => /^https?:\/\/.+/.test(v), "Thêm link bắt đầu bằng https:// nhé"),
    platform: z.enum(["TikTok", "Meta", "YouTube Shorts", "UGC", "Other"]),
    board: z.string().min(1, "Chọn bộ sưu tập nhé"),
    notes: z.string().optional(),
});
type UrlValues = z.infer<typeof urlSchema>;

type FileMeta = {
    kind: "image" | "video";
    width?: number;
    height?: number;
    durationSec?: number;
    aspectRatio?: "9:16" | "16:9" | "1:1" | "4:5";
};

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
        title: "Giải pháp cho góc bếp bừa bộn",
        hook: "Góc bếp sau một ngày chăm con và đi mua sắm.",
        seed: "coral",
        angle: "Problem–solution",
        category: "Home & Kitchen",
        platform: "TikTok",
        dur: 24,
    },
    {
        id: "d2",
        title: "Bất ngờ với món quà dành cho người yêu chó",
        hook: "Cuối cùng anh ấy cũng chọn đúng món quà mình thích.",
        seed: "peach",
        angle: "Gift reaction",
        category: "POD Gifts",
        platform: "TikTok",
        dur: 32,
    },
    {
        id: "d3",
        title: "Chiếc gương trong thói quen làm đẹp buổi sáng",
        hook: "Chiếc gương mình luôn mang theo.",
        seed: "blush",
        angle: "Day-in-the-life",
        category: "Beauty",
        platform: "TikTok",
        dur: 40,
    },
    {
        id: "d4",
        title: "Trước và sau khi dùng cây lăn lông thú",
        hook: "Mình không cần mua thêm cuộn giấy dính nữa.",
        seed: "mint",
        angle: "Before-and-after",
        category: "Pet",
        platform: "Meta",
        dur: 18,
    },
    {
        id: "d5",
        title: "Chia sẻ sau ba tháng sắp xếp nhà cửa",
        hook: "Sau ba tháng, đây là những góc vẫn giữ được ngăn nắp.",
        seed: "sage",
        angle: "Testimonial",
        category: "Home Organization",
        platform: "TikTok",
        dur: 46,
    },
    {
        id: "d6",
        title: "So sánh bốn mẫu gương được yêu thích",
        hook: "Mình đã thử cả bốn mẫu để bạn dễ chọn hơn.",
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
    const [tab, setTab] = useState("file");
    const [file, setFile] = useState<File | null>(null);
    const [fileUrl, setFileUrl] = useState<string | null>(null);
    const transferredUrlRef = useRef<string | null>(null);
    const [fileMeta, setFileMeta] = useState<FileMeta | null>(null);
    const [posterUrl, setPosterUrl] = useState<string | undefined>();
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
            setTab("file");
            setFile(null);
            setFileErr(null);
            setFileMeta(null);
            setPosterUrl(undefined);
            setDemoId(null);
            transferredUrlRef.current = null;
            form.reset({ url: "", platform: "TikTok", board: defaultBoard, notes: "" });
        } else if (fileUrl) {
            if (transferredUrlRef.current !== fileUrl) URL.revokeObjectURL(fileUrl);
            transferredUrlRef.current = null;
            setFileUrl(null);
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [open]);

    useEffect(() => {
        if (!fileUrl || fileMeta?.kind !== "video") {
            setPosterUrl(undefined);
            return;
        }
        let active = true;
        void captureVideoPoster(fileUrl).then((poster) => {
            if (active) {
                setPosterUrl(poster ?? (file ? posterForDemoUploadFilename(file.name) : undefined));
            }
        });
        return () => {
            active = false;
        };
    }, [file, fileMeta?.kind, fileUrl]);

    function handleFile(f: File | null) {
        if (!f) {
            setFile(null);
            setFileMeta(null);
            if (fileUrl) URL.revokeObjectURL(fileUrl);
            setFileUrl(null);
            return;
        }
        const allowed = ["mp4", "mov", "webm", "jpg", "jpeg", "png", "webp"];
        const ext = f.name.split(".").pop()?.toLowerCase() ?? "";
        if (!allowed.includes(ext)) {
            setFileErr("Chọn file MP4, MOV, WebM, JPG, PNG hoặc WebP nhé.");
            return;
        }
        if (f.size > 50 * 1024 * 1024) {
            setFileErr("Kho tư liệu nhận file tối đa 50 MB. Hãy chọn file nhỏ hơn nhé.");
            return;
        }
        setFileErr(null);
        setFile(f);
        setFileMeta({ kind: f.type.startsWith("image/") ? "image" : "video" });
        if (fileUrl) URL.revokeObjectURL(fileUrl);
        setFileUrl(URL.createObjectURL(f));
    }

    function updateMediaMeta(
        kind: "image" | "video",
        width: number,
        height: number,
        durationSec?: number,
    ) {
        const ratio = width / Math.max(1, height);
        const aspectRatio: FileMeta["aspectRatio"] =
            Math.abs(ratio - 1) < 0.08
                ? "1:1"
                : ratio < 0.8
                  ? "9:16"
                  : ratio > 1.4
                    ? "16:9"
                    : "4:5";
        setFileMeta({ kind, width, height, durationSec, aspectRatio });
    }

    function finish(cr: CreativeReference, message: string) {
        addCreative(cr);
        toast.success(message, { description: cr.title });
        onOpenChange(false);
        onImported?.(cr);
    }

    function openImportedCreative(cr: CreativeReference) {
        setTimeout(
            () => navigate({ to: "/creative-library/$creativeId", params: { creativeId: cr.id } }),
            60,
        );
    }

    async function submitUrl(v: UrlValues) {
        setSubmitting(true);
        const now = new Date().toISOString();
        const cr: CreativeReference = {
            id: `cr-${Date.now()}`,
            title: v.notes?.slice(0, 60) || `Link tham khảo từ ${v.platform}`,
            hookExcerpt: v.notes || "Link đã lưu để tham khảo; chưa có file video.",
            platform: v.platform,
            durationSec: 24,
            brandOrCreator: new URL(v.url).hostname.replace("www.", ""),
            angle: "Problem–solution",
            category: "Home & Kitchen",
            tags: ["link-import"],
            notes: [v.notes, `Nguồn: ${v.url}`].filter(Boolean).join("\n"),
            boardIds: v.board === "b-all" ? [] : [v.board],
            analysisStatus: "ready",
            savedAt: now,
            thumbSeed: seedFromPlatform(v.platform),
        };
        setSubmitting(false);
        finish(cr, "Đã lưu link tham khảo");
        openImportedCreative(cr);
    }

    function submitFile() {
        if (!file) {
            setFileErr("Chọn file trước khi thêm vào kho nhé.");
            return;
        }
        const now = new Date().toISOString();
        const cr: CreativeReference = {
            id: `cr-${Date.now()}`,
            title: file.name.replace(/\.[^.]+$/, ""),
            hookExcerpt: "Tư liệu từ máy của bạn, sẵn sàng để xem và tham khảo.",
            platform: "UGC",
            durationSec: Math.round(fileMeta?.durationSec ?? 22),
            mediaKind: fileMeta?.kind ?? (file.type.startsWith("image/") ? "image" : "video"),
            mediaUrl: fileUrl ?? undefined,
            posterUrl: file.type.startsWith("video/")
                ? (posterUrl ?? posterForDemoUploadFilename(file.name))
                : undefined,
            mediaAspectRatio: fileMeta?.aspectRatio,
            brandOrCreator: "Tải từ máy",
            angle: "Testimonial",
            category: "Home & Kitchen",
            tags: ["upload"],
            boardIds: defaultBoard === "b-all" ? [] : [defaultBoard],
            analysisStatus: "ready",
            savedAt: now,
            thumbSeed: "amber",
        };
        if (fileUrl) transferredUrlRef.current = fileUrl;
        finish(cr, "Đã thêm file vào kho");
        openImportedCreative(cr);
    }

    const fileBlocker =
        tab === "file"
            ? !file
                ? "Chọn ảnh hoặc video trước khi thêm vào kho nhé."
                : fileErr
            : null;

    function submitDemo() {
        const d = demoOptions.find((x) => x.id === demoId);
        if (!d) return;
        const cr: CreativeReference = {
            id: `cr-${Date.now()}`,
            title: d.title,
            hookExcerpt: d.hook,
            platform: d.platform,
            durationSec: d.dur,
            brandOrCreator: "Tư liệu minh họa",
            angle: d.angle,
            category: d.category,
            tags: ["demo"],
            boardIds: defaultBoard === "b-all" ? [] : [defaultBoard],
            analysisStatus: "ready",
            savedAt: new Date().toISOString(),
            thumbSeed: d.seed,
        };
        finish(cr, "Đã thêm tư liệu minh họa");
        openImportedCreative(cr);
    }

    return (
        <Dialog open={open} onOpenChange={submitting ? undefined : onOpenChange}>
            <DialogContent className="flex max-h-[calc(100dvh-2rem)] flex-col overflow-hidden border-0 p-4 sm:max-w-[640px] sm:p-6 [&>button]:grid [&>button]:size-11 [&>button]:place-items-center">
                <DialogHeader className="pr-10 text-left">
                    <DialogTitle>Thêm tư liệu vào kho</DialogTitle>
                    <DialogDescription>
                        Tư liệu lưu trên trình duyệt này. Thêm file để xem video hoặc lưu link để
                        tham khảo.
                    </DialogDescription>
                </DialogHeader>

                <Tabs value={tab} onValueChange={setTab} className="flex min-h-0 flex-1 flex-col">
                    <TabsList
                        aria-label="Cách thêm tư liệu"
                        className="grid h-auto w-full grid-cols-3 gap-1 bg-surface-soft p-1"
                    >
                        <TabsTrigger
                            value="file"
                            className="min-h-11 whitespace-normal px-2 text-xs sm:text-sm"
                        >
                            Tải từ máy
                        </TabsTrigger>
                        <TabsTrigger
                            value="url"
                            className="min-h-11 whitespace-normal px-2 text-xs sm:text-sm"
                        >
                            Lưu link tham khảo
                        </TabsTrigger>
                        <TabsTrigger
                            value="demo"
                            className="min-h-11 whitespace-normal px-2 text-xs sm:text-sm"
                        >
                            Minh họa
                        </TabsTrigger>
                    </TabsList>

                    <div className="min-h-0 flex-1 overflow-y-auto pr-1">
                        <TabsContent value="url" className="mt-4">
                            <form
                                id="import-url-form"
                                onSubmit={form.handleSubmit(submitUrl)}
                                className="flex flex-col gap-4"
                            >
                                <div className="grid gap-1.5">
                                    <Label htmlFor="url">Link nguồn tham khảo</Label>
                                    <div className="relative">
                                        <Link2 className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-tertiary" />
                                        <Input
                                            id="url"
                                            className="h-11 border-0 bg-surface-soft pl-9 shadow-none"
                                            placeholder="https://tiktok.com/@creator/video/…"
                                            {...form.register("url")}
                                        />
                                    </div>
                                    {form.formState.errors.url && (
                                        <p className="text-xs text-destructive">
                                            {form.formState.errors.url.message}
                                        </p>
                                    )}
                                    <p className="text-xs leading-relaxed text-text-secondary">
                                        Chỉ lưu link và ghi chú, chưa tải file video. Để dùng Smart
                                        Remake, bạn cần thêm file video từ máy.
                                    </p>
                                </div>

                                <div className="grid gap-3 sm:grid-cols-2">
                                    <div className="grid gap-1.5">
                                        <Label>Nền tảng nguồn</Label>
                                        <Select
                                            value={form.watch("platform")}
                                            onValueChange={(v) =>
                                                form.setValue("platform", v as CreativePlatform)
                                            }
                                        >
                                            <SelectTrigger
                                                aria-label="Nền tảng nguồn"
                                                className="h-11 border-0 bg-surface-soft"
                                            >
                                                <SelectValue />
                                            </SelectTrigger>
                                            <SelectContent className="border-0">
                                                <SelectItem value="TikTok" className="min-h-11">
                                                    TikTok
                                                </SelectItem>
                                                <SelectItem value="Meta" className="min-h-11">
                                                    Meta
                                                </SelectItem>
                                                <SelectItem
                                                    value="YouTube Shorts"
                                                    className="min-h-11"
                                                >
                                                    YouTube Shorts
                                                </SelectItem>
                                                <SelectItem value="UGC" className="min-h-11">
                                                    UGC
                                                </SelectItem>
                                                <SelectItem value="Other" className="min-h-11">
                                                    Khác
                                                </SelectItem>
                                            </SelectContent>
                                        </Select>
                                    </div>
                                    <div className="grid gap-1.5">
                                        <Label>Bộ sưu tập</Label>
                                        <Select
                                            value={form.watch("board")}
                                            onValueChange={(v) => form.setValue("board", v)}
                                        >
                                            <SelectTrigger
                                                aria-label="Bộ sưu tập"
                                                className="h-11 border-0 bg-surface-soft"
                                            >
                                                <SelectValue />
                                            </SelectTrigger>
                                            <SelectContent className="border-0">
                                                {boardOptions.map((b) => (
                                                    <SelectItem
                                                        key={b.id}
                                                        value={b.id}
                                                        className="min-h-11"
                                                    >
                                                        {b.system && b.filter === "all"
                                                            ? "Chưa phân loại"
                                                            : b.name}
                                                    </SelectItem>
                                                ))}
                                            </SelectContent>
                                        </Select>
                                    </div>
                                </div>

                                <div className="grid gap-1.5">
                                    <Label htmlFor="notes">Ghi chú (không bắt buộc)</Label>
                                    <Textarea
                                        id="notes"
                                        rows={3}
                                        placeholder="Bạn thích cách mở đầu, góc quay hay cách giới thiệu sản phẩm nào?"
                                        className="border-0 bg-surface-soft shadow-none"
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
                                        "flex cursor-pointer flex-col items-center justify-center gap-2 rounded-2xl bg-surface-soft px-6 py-8 text-center transition-colors hover:bg-surface-muted focus-within:ring-2 focus-within:ring-ring",
                                    )}
                                >
                                    <Upload className="h-5 w-5 text-text-tertiary" />
                                    <p className="text-sm font-medium text-text-primary">
                                        Chọn video hoặc ảnh từ máy
                                    </p>
                                    <p className="text-xs text-text-tertiary">
                                        MP4, MOV, WebM, JPG, PNG, WebP · Tối đa 50 MB
                                    </p>
                                    <input
                                        id="file-input"
                                        type="file"
                                        accept="video/mp4,video/quicktime,video/webm,image/jpeg,image/png,image/webp"
                                        className="sr-only"
                                        onChange={(e) => handleFile(e.target.files?.[0] ?? null)}
                                    />
                                </label>
                                <p className="text-xs leading-relaxed text-text-secondary">
                                    Nếu muốn tạo video bằng Smart Remake, chọn video tối đa 30 MB.
                                    File tải từ máy chỉ mở được khi còn trong phiên trình duyệt này.
                                </p>

                                {file && (
                                    <div className="grid gap-3 rounded-2xl bg-surface-soft p-3 sm:grid-cols-[168px_minmax(0,1fr)]">
                                        <div className="grid min-h-[150px] place-items-center overflow-hidden rounded-md bg-black">
                                            {fileUrl && file.type.startsWith("image/") ? (
                                                <img
                                                    src={fileUrl}
                                                    alt="Xem trước ảnh đã chọn"
                                                    className="h-full w-full object-contain"
                                                    onLoad={(event) =>
                                                        updateMediaMeta(
                                                            "image",
                                                            event.currentTarget.naturalWidth,
                                                            event.currentTarget.naturalHeight,
                                                        )
                                                    }
                                                />
                                            ) : fileUrl && file.type.startsWith("video/") ? (
                                                <video
                                                    src={fileUrl}
                                                    poster={
                                                        posterUrl ??
                                                        posterForDemoUploadFilename(file.name)
                                                    }
                                                    className="h-full w-full object-contain"
                                                    controls
                                                    muted
                                                    playsInline
                                                    preload="metadata"
                                                    onLoadedMetadata={(event) =>
                                                        updateMediaMeta(
                                                            "video",
                                                            event.currentTarget.videoWidth,
                                                            event.currentTarget.videoHeight,
                                                            event.currentTarget.duration,
                                                        )
                                                    }
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
                                                {file.type || "Chưa xác định định dạng"}
                                            </p>
                                            {fileMeta && (
                                                <p className="mt-1 text-xs text-text-secondary">
                                                    {fileMeta.kind === "video" ? "Video" : "Ảnh"} ·{" "}
                                                    {fileMeta.width && fileMeta.height
                                                        ? `${fileMeta.width}×${fileMeta.height}`
                                                        : "Đang đọc kích thước"}
                                                    {fileMeta.durationSec
                                                        ? ` · ${Math.round(fileMeta.durationSec)} giây`
                                                        : ""}
                                                    {fileMeta.aspectRatio
                                                        ? ` · ${fileMeta.aspectRatio}`
                                                        : ""}
                                                </p>
                                            )}
                                        </div>
                                        <Button
                                            type="button"
                                            variant="ghost"
                                            size="icon"
                                            aria-label="Bỏ file đã chọn"
                                            className="size-11"
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
                            <p className="mb-3 text-xs leading-relaxed text-text-secondary">
                                Các ý tưởng minh họa giúp bạn xem thử cách lưu tư liệu. Chưa kèm
                                file video để tạo bằng Smart Remake.
                            </p>
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
                                                "flex min-h-11 items-start gap-3 rounded-xl p-3 text-left transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                                                active
                                                    ? "bg-primary-softer ring-2 ring-inset ring-primary/40"
                                                    : "bg-surface-soft hover:bg-surface-muted",
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
                                                    {d.platform} · {d.dur} giây
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
                    <Button
                        type="button"
                        variant="ghost"
                        className="min-h-11"
                        onClick={() => onOpenChange(false)}
                    >
                        Hủy
                    </Button>
                    {tab === "url" && (
                        <Button
                            type="submit"
                            form="import-url-form"
                            disabled={submitting}
                            className="min-h-11 min-w-[140px]"
                        >
                            Lưu link tham khảo
                        </Button>
                    )}
                    {tab === "file" && (
                        <DisabledActionHint reason={fileBlocker} className="items-end">
                            <Button
                                type="button"
                                onClick={submitFile}
                                disabled={!!fileBlocker}
                                className="min-h-11 min-w-[140px]"
                            >
                                Thêm file vào kho
                            </Button>
                        </DisabledActionHint>
                    )}
                    {tab === "demo" && (
                        <Button
                            type="button"
                            onClick={submitDemo}
                            disabled={!demoId}
                            className="min-h-11 min-w-[140px]"
                        >
                            Thêm minh họa
                        </Button>
                    )}
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
