import { Check, Copy, Download, Images, Loader2 } from "lucide-react";
import { useState } from "react";
import type {
    SmartRemakeConditioningImage,
    SmartRemakeKieRequest,
} from "@/shared/api/smart-remake";
import { getSmartRemakeGeneratedImageDownload } from "@/shared/api/smart-remake-generated-media";
import { Button } from "@/shared/ui/button";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogTitle,
    DialogTrigger,
} from "@/shared/ui/dialog";

type MediaIdentity = { workspaceId?: string; projectId: string; operationId: string };
type GeneratedImageProps = MediaIdentity & {
    image: SmartRemakeConditioningImage;
    ordinal: number;
    sceneIndex?: number;
    onRefresh?(): void;
};

export function RemakeGeneratedImage({
    workspaceId,
    projectId,
    operationId,
    image,
    ordinal,
    sceneIndex,
    onRefresh,
}: GeneratedImageProps) {
    const [state, setState] = useState<"idle" | "loading" | "error">("idle");
    const [failedPreview, setFailedPreview] = useState<string | null>(null);
    const label = sceneIndex ? `cảnh ${sceneIndex}` : "clip";
    const name =
        image.frameRole === "opening"
            ? "Ảnh đầu"
            : image.frameRole === "ending"
              ? "Ảnh cuối"
              : `Ảnh ${ordinal}`;
    const canDownload = Boolean(workspaceId && image.requestHash);
    async function download() {
        if (!workspaceId || !image.requestHash || state === "loading") return;
        setState("loading");
        try {
            const result = await getSmartRemakeGeneratedImageDownload(
                workspaceId,
                projectId,
                operationId,
                image.requestHash,
            );
            const url = new URL(result.url);
            if (!["https:", "http:"].includes(url.protocol)) throw new Error("Invalid download");
            const anchor = document.createElement("a");
            anchor.href = url.href;
            anchor.download = result.filename;
            anchor.rel = "noopener noreferrer";
            document.body.append(anchor);
            anchor.click();
            anchor.remove();
            setState("idle");
        } catch {
            setState("error");
        }
    }
    const downloadControls = (
        <>
            <Button
                type="button"
                variant="ghost"
                className="min-h-10 w-full justify-center gap-2 px-2 text-xs"
                aria-busy={state === "loading"}
                disabled={!canDownload || state === "loading"}
                aria-label={`${state === "error" ? "Thử tải lại" : "Tải ảnh gốc"} · ${name}`}
                title={!canDownload ? "Làm mới dự án để cập nhật thông tin tải ảnh" : undefined}
                onClick={() => void download()}
            >
                {state === "loading" ? (
                    <Loader2 className="size-3.5 animate-spin" aria-hidden="true" />
                ) : (
                    <Download className="size-3.5" aria-hidden="true" />
                )}
                {state === "loading"
                    ? "Đang chuẩn bị ảnh…"
                    : state === "error"
                      ? "Thử tải lại"
                      : "Tải ảnh gốc"}
            </Button>
            {state === "error" && (
                <p role="alert" className="text-xs text-warn">
                    Chưa tải được ảnh. Thử lại nhé.
                </p>
            )}
        </>
    );
    return (
        <div className="min-w-0 space-y-1">
            <Dialog>
                <DialogTrigger asChild>
                    <button
                        type="button"
                        className="remake-generation-progress__image"
                        aria-label={`Phóng to ảnh tham chiếu ${ordinal} · ${label}`}
                    >
                        <img
                            src={image.url}
                            alt={`Ảnh tham chiếu đã tạo cho ${label}`}
                            onError={() => setFailedPreview(image.url)}
                        />
                        <span>{image.frameRole ? name : `${name} · ${label}`}</span>
                    </button>
                </DialogTrigger>
                <DialogContent className="max-w-3xl rounded-3xl border-0 sm:max-w-3xl">
                    <DialogTitle>
                        {image.frameRole ? name : `Ảnh tham chiếu ${ordinal}`} · {label}
                    </DialogTitle>
                    <DialogDescription>Ảnh được tạo để chuẩn bị clip.</DialogDescription>
                    <img
                        className="max-h-[65dvh] w-full object-contain"
                        src={image.url}
                        alt={`Ảnh tham chiếu ${label} phóng to`}
                        onError={() => setFailedPreview(image.url)}
                    />
                    {downloadControls}
                    {onRefresh && (
                        <Button
                            type="button"
                            variant="ghost"
                            className="min-h-10"
                            onClick={onRefresh}
                        >
                            Làm mới ảnh
                        </Button>
                    )}
                </DialogContent>
            </Dialog>
            {downloadControls}
            {failedPreview === image.url && onRefresh && (
                <Button
                    type="button"
                    variant="ghost"
                    className="min-h-10 w-full text-xs"
                    onClick={onRefresh}
                >
                    Làm mới ảnh xem trước
                </Button>
            )}
        </div>
    );
}

export function RemakeKiePrompt({
    request,
    videoSubmitted,
}: {
    request?: SmartRemakeKieRequest;
    videoSubmitted: boolean | null;
}) {
    const [copyState, setCopy] = useState<{
        requestHash: string;
        prompt: string;
        status: "copied" | "error";
    } | null>(null);
    const sent = videoSubmitted === true ? request : undefined;
    const copy =
        copyState?.requestHash === sent?.requestHash && copyState?.prompt === sent?.prompt
            ? copyState?.status
            : "idle";
    async function copyPrompt() {
        if (!sent) return;
        try {
            await navigator.clipboard.writeText(sent.prompt);
            setCopy({ requestHash: sent.requestHash, prompt: sent.prompt, status: "copied" });
        } catch {
            setCopy({ requestHash: sent.requestHash, prompt: sent.prompt, status: "error" });
        }
    }
    return (
        <details className="min-w-0 rounded-xl bg-surface-soft/65 px-4 py-3">
            <summary className="min-h-6 cursor-pointer text-sm font-medium">
                {sent ? "Prompt đã gửi KIE" : "Prompt gửi KIE"}
            </summary>
            {sent ? (
                <div className="mt-3 space-y-3">
                    <div className="flex items-center justify-between gap-3">
                        <p className="text-xs text-text-secondary">{sent.model}</p>
                        <Button
                            type="button"
                            variant="ghost"
                            className="min-h-10 text-xs"
                            onClick={() => void copyPrompt()}
                        >
                            {copy === "copied" ? (
                                <Check className="size-3.5" aria-hidden="true" />
                            ) : (
                                <Copy className="size-3.5" aria-hidden="true" />
                            )}
                            {copy === "copied" ? "Đã sao chép" : "Sao chép prompt"}
                        </Button>
                    </div>
                    <pre
                        tabIndex={0}
                        className="max-h-72 overflow-y-auto whitespace-pre-wrap break-words font-sans text-xs leading-relaxed text-text-secondary"
                    >
                        {sent.prompt}
                    </pre>
                    {copy === "error" && (
                        <p role="alert" className="text-xs text-warn">
                            Chưa sao chép được. Bạn có thể chọn nội dung prompt để sao chép.
                        </p>
                    )}
                </div>
            ) : (
                <p className="mt-3 text-xs leading-relaxed text-text-secondary">
                    {videoSubmitted === true
                        ? "Lượt này chưa lưu prompt KIE."
                        : "Prompt sẽ xuất hiện sau khi xác nhận gửi lượt tạo clip tới KIE."}
                </p>
            )}
        </details>
    );
}

export type RemakeGeneratedMediaGroup = {
    index: number;
    videoSubmitted: boolean | null;
    conditioningImages: SmartRemakeConditioningImage[];
    kieRequest?: SmartRemakeKieRequest;
};

export function RemakeGeneratedMedia({
    workspaceId,
    projectId,
    operationId,
    groups,
    onRefresh,
}: MediaIdentity & { groups: RemakeGeneratedMediaGroup[]; onRefresh?(): void }) {
    if (!groups.some((group) => group.conditioningImages.length || group.kieRequest)) return null;
    return (
        <Dialog>
            <DialogTrigger asChild>
                <Button type="button" variant="ghost" className="min-h-11 justify-start">
                    <Images className="size-4" aria-hidden="true" /> Ảnh &amp; prompt
                </Button>
            </DialogTrigger>
            <DialogContent className="max-w-4xl rounded-3xl border-0 sm:max-w-4xl">
                <DialogTitle>Ảnh &amp; prompt lần tạo clip</DialogTitle>
                <DialogDescription>
                    Thuộc lượt tạo clip gốc, trước các bản sửa cảnh.
                </DialogDescription>
                {onRefresh && (
                    <Button
                        type="button"
                        variant="ghost"
                        className="min-h-10 justify-start"
                        onClick={onRefresh}
                    >
                        Làm mới ảnh
                    </Button>
                )}
                <div className="space-y-7">
                    {groups.map((group) => (
                        <section
                            key={group.index}
                            className="min-w-0 space-y-4"
                            aria-label={`Tư liệu tạo clip ${group.index}`}
                        >
                            <h3 className="text-sm font-semibold">Clip {group.index}</h3>
                            <div className="grid grid-cols-2 gap-4">
                                {group.conditioningImages.map((image, index) => (
                                    <RemakeGeneratedImage
                                        key={`${image.requestHash ?? image.renderUnitId}:${image.frameRole ?? index}`}
                                        workspaceId={workspaceId}
                                        projectId={projectId}
                                        operationId={operationId}
                                        image={image}
                                        ordinal={index + 1}
                                        onRefresh={onRefresh}
                                    />
                                ))}
                            </div>
                            <RemakeKiePrompt
                                request={group.kieRequest}
                                videoSubmitted={group.videoSubmitted}
                            />
                        </section>
                    ))}
                </div>
            </DialogContent>
        </Dialog>
    );
}
