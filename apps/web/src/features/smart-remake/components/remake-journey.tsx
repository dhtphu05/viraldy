import { Check, Clock3 } from "lucide-react";
import referenceVideoIllustration from "@/assets/smart-remake/reference-video.webp";
import storyboardIllustration from "@/assets/smart-remake/analysis-storyboard.webp";
import renderStudioIllustration from "@/assets/smart-remake/render-studio.webp";
import { cn } from "@/shared/lib/utils";
import type { RemakeStep } from "../lib/use-remake-studio";

type Props = {
    step: RemakeStep;
    hasPlan: boolean;
    hasResult: boolean;
    busy: boolean;
    sourceUrl?: string | null;
    productUrl?: string | null;
    outputUrl?: string | null;
    onChange(step: RemakeStep): void;
};

export function RemakeJourney({
    step,
    hasPlan,
    hasResult,
    busy,
    sourceUrl,
    productUrl,
    outputUrl,
    onChange,
}: Props) {
    const steps = [
        {
            id: "prepare",
            title: "Chọn tư liệu",
            hint: "Video mẫu và sản phẩm",
            illustration: referenceVideoIllustration,
            available: true,
        },
        {
            id: "plan",
            title: "Duyệt kịch bản",
            hint: "Xem từng cảnh trước khi tạo",
            illustration: storyboardIllustration,
            available: hasPlan,
        },
        {
            id: "result",
            title: "Xem & ghép",
            hint: "Duyệt, sửa và tải video",
            illustration: renderStudioIllustration,
            available: hasResult,
        },
    ] as const;
    return (
        <nav aria-label="Các bước Smart Remake" className="grid grid-cols-3 gap-2 sm:gap-3">
            {steps.map(({ id, title, hint, illustration, available }, index) => (
                <button
                    type="button"
                    key={id}
                    disabled={busy || !available}
                    aria-current={step === id ? "step" : undefined}
                    onClick={() => onChange(id)}
                    className={cn(
                        "flex min-h-16 min-w-0 items-center gap-3 rounded-2xl p-3 text-left transition-[background-color,box-shadow] motion-reduce:transition-none disabled:cursor-not-allowed focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring sm:p-4",
                        step === id ? "bg-surface shadow-soft-card" : "hover:bg-surface/60",
                        !available && "opacity-50",
                    )}
                >
                    <span
                        className="relative hidden size-11 shrink-0 items-center justify-center overflow-hidden rounded-xl bg-primary-soft/60 sm:flex"
                        aria-hidden="true"
                    >
                        {id === "prepare" && sourceUrl ? (
                            <video
                                src={sourceUrl}
                                muted
                                playsInline
                                preload="metadata"
                                className="h-full w-auto max-w-full object-contain"
                            />
                        ) : id === "plan" && productUrl ? (
                            <img src={productUrl} alt="" className="size-full object-contain" />
                        ) : id === "result" && outputUrl ? (
                            <video
                                src={outputUrl}
                                muted
                                playsInline
                                preload="metadata"
                                className="h-full w-auto max-w-full object-contain"
                            />
                        ) : (
                            <img
                                src={illustration}
                                alt=""
                                width={44}
                                height={44}
                                draggable={false}
                                className="size-full object-contain"
                            />
                        )}
                    </span>
                    <span className="min-w-0">
                        <span className="block text-xs font-medium sm:text-sm">
                            {index + 1}. {title}
                        </span>
                        <span className="mt-0.5 hidden text-xs text-text-secondary md:block">
                            {hint}
                        </span>
                        {id === "result" && hasResult && !outputUrl && (
                            <span className="mt-0.5 block text-[10px] text-text-tertiary sm:text-xs">
                                Chưa có video
                            </span>
                        )}
                    </span>
                    {available &&
                        step !== id &&
                        id !== "prepare" &&
                        (id !== "result" || Boolean(outputUrl)) && (
                            <Check
                                className="ml-auto hidden size-4 shrink-0 text-ok lg:block"
                                aria-label="Có thể mở"
                            />
                        )}
                    {id === "result" && hasResult && !outputUrl && (
                        <Clock3
                            className="ml-auto hidden size-4 shrink-0 text-text-tertiary lg:block"
                            aria-hidden="true"
                        />
                    )}
                </button>
            ))}
        </nav>
    );
}
