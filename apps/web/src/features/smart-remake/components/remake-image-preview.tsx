import { useEffect, useRef, useState } from "react";
import { ImageOff, ScanLine } from "lucide-react";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogTitle,
    DialogTrigger,
} from "@/shared/ui/dialog";
import { cn } from "@/shared/lib/utils";
import "./remake-image-preview.css";

interface Props {
    src: string;
    alt: string;
    enlarge?: boolean;
    compact?: boolean;
    disabled?: boolean;
}

export function RemakeImagePreview({ src, alt, enlarge, compact, disabled }: Props) {
    if (!enlarge) return <ImageSurface key={src} src={src} alt={alt} compact={compact} />;
    return (
        <Dialog key={src}>
            <DialogTrigger asChild>
                <button
                    type="button"
                    disabled={disabled}
                    aria-label="Phóng to ảnh sản phẩm"
                    className="remake-image-preview__trigger"
                >
                    <ImageSurface key={src} src={src} alt={alt} />
                    <span className="remake-image-preview__badge" aria-hidden="true">
                        <ScanLine className="size-3.5" /> Phóng to
                    </span>
                </button>
            </DialogTrigger>
            <DialogContent className="remake-image-preview-dialog max-w-3xl rounded-3xl p-5 motion-reduce:animate-none sm:p-6">
                <DialogTitle className="pr-12">Ảnh sản phẩm</DialogTitle>
                <DialogDescription>
                    Xem toàn bộ ảnh gốc để kiểm tra chi tiết trước khi tạo video.
                </DialogDescription>
                <div className="remake-image-preview__expanded">
                    <ImageSurface src={src} alt={alt} />
                </div>
            </DialogContent>
        </Dialog>
    );
}

function ImageSurface({ src, alt, compact }: Pick<Props, "src" | "alt" | "compact">) {
    const image = useRef<HTMLImageElement>(null);
    const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
    useEffect(() => {
        if (status !== "loading") return;
        if (image.current?.complete && image.current.naturalWidth > 0) {
            setStatus("ready");
            return;
        }
        const timeout = window.setTimeout(() => setStatus("error"), 15000);
        return () => window.clearTimeout(timeout);
    }, [status]);
    return (
        <span
            className={cn("remake-image-preview__surface", compact && "is-compact")}
            data-state={status}
        >
            <img
                ref={image}
                src={src}
                alt={alt}
                decoding="async"
                draggable={false}
                className="object-contain"
                onLoad={() => setStatus("ready")}
                onError={() => setStatus("error")}
            />
            {status !== "ready" && (
                <span
                    className="remake-image-preview__feedback"
                    role={compact ? undefined : status === "error" ? "alert" : "status"}
                >
                    {status === "error" ? (
                        <>
                            <ImageOff className="size-5" aria-hidden="true" />
                            <span className={compact ? "sr-only" : undefined}>
                                Chưa mở được ảnh. Chọn lại ảnh hoặc thêm ảnh khác nhé.
                            </span>
                        </>
                    ) : (
                        <>
                            <span className="remake-image-preview__skeleton" aria-hidden="true" />
                            <span className="sr-only">Đang tải ảnh…</span>
                        </>
                    )}
                </span>
            )}
        </span>
    );
}
