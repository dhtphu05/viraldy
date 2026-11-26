import { ArrowRight, Copy, Image, Loader2, MessageSquareText, Video } from "lucide-react";
import { useId, useState } from "react";

import { getRemakeScenes } from "@/features/smart-remake/lib/remake-studio";
import type { SmartRemakeCompileResult } from "@/shared/api/smart-remake";
import { Button } from "@/shared/ui/button";
import { Textarea } from "@/shared/ui/textarea";
import { RemakeSourceTimeline } from "./remake-source-timeline";
import { RemakeRenderGroups } from "./remake-render-groups";
import { getRenderGroupBreaks } from "../lib/remake-groups";
import { RemakeLogicalStoryboard } from "./remake-logical-storyboard";
import { RemakeImagePreview } from "./remake-image-preview";
import { RemakeSourceAudio } from "./remake-source-audio";
import "./remake-storyboard.css";

export interface RemakeStoryboardProps {
    compileResult: SmartRemakeCompileResult;
    referenceUrl?: string | null;
    productUrl?: string | null;
    onSceneChange: (index: number, patch: Record<string, string>) => void;
    disabled?: boolean;
    sourceCutFrames?: number[];
    onSourceCutFramesChange?: (cuts: number[]) => void;
    onRecompile?: () => void;
    isRecompiling?: boolean;
    renderGroupBreaks?: number[];
    onRenderGroupBreaksChange?: (breaks: number[]) => void;
    sourcePlanDirty?: boolean;
    sourceCutsDirty?: boolean;
    sourceCutsError?: string | null;
}

const fieldClass =
    "border-0 bg-surface-soft shadow-none focus-visible:ring-2 focus-visible:ring-ring/60";
const VIDEO_PROMPT_LIMIT = 12_000;

export function RemakeStoryboard({
    compileResult,
    referenceUrl,
    productUrl,
    onSceneChange,
    disabled = false,
    sourceCutFrames,
    onSourceCutFramesChange,
    onRecompile,
    isRecompiling,
    renderGroupBreaks,
    onRenderGroupBreaksChange,
    sourcePlanDirty,
    sourceCutsDirty,
    sourceCutsError,
}: RemakeStoryboardProps) {
    const id = useId();
    const scenes = getRemakeScenes(compileResult);
    const productName =
        typeof compileResult.productLock?.productName === "string"
            ? compileResult.productLock.productName
            : "";
    const preserveDetails = Array.isArray(compileResult.productLock?.mustPreserve)
        ? compileResult.productLock.mustPreserve.filter(
              (value): value is string => typeof value === "string",
          )
        : [];
    const [selectedScene, setSelectedScene] = useState(0);
    const sourceMap = compileResult.sourceSceneMap;
    const logicalSceneCount = sourceMap?.scenes.length ?? scenes.length;
    const activeSceneIndex = Math.min(selectedScene, Math.max(0, logicalSceneCount - 1));
    const compiledCuts = sourceMap
        ? [0, ...sourceMap.scenes.map((scene) => scene.endFrame - sourceMap.sourceStartFrame)]
        : [];
    const [editedScenes, setEditedScenes] = useState<Record<string, boolean>>({});
    const [copyStates, setCopyStates] = useState<
        Record<string, { status: "copying" | "copied" | "error"; content: string }>
    >({});

    const copyPrompts = async (sceneId: string, content: string) => {
        setCopyStates((current) => ({ ...current, [sceneId]: { status: "copying", content } }));
        try {
            await navigator.clipboard.writeText(content);
            setCopyStates((current) => ({ ...current, [sceneId]: { status: "copied", content } }));
        } catch {
            setCopyStates((current) => ({ ...current, [sceneId]: { status: "error", content } }));
        }
    };

    const changeScene = (sceneId: string, index: number, patch: Record<string, string>) => {
        setCopyStates((current) =>
            Object.fromEntries(Object.entries(current).filter(([key]) => key !== sceneId)),
        );
        onSceneChange(index, patch);
    };

    const productReference = (productUrl || productName || preserveDetails.length > 0) && (
        <section
            aria-label="Nhận diện sản phẩm trong kịch bản"
            className="remake-storyboard-product"
        >
            {productUrl && (
                <div className="remake-storyboard-product__image">
                    <RemakeImagePreview
                        src={productUrl}
                        alt="Ảnh chính của sản phẩm"
                        enlarge
                        disabled={disabled}
                    />
                </div>
            )}
            <div className="min-w-0 space-y-1">
                <h2 className="text-sm font-semibold">Sản phẩm cần giữ đúng</h2>
                {productName && <p className="text-sm text-text-secondary">{productName}</p>}
                {preserveDetails.length > 0 && (
                    <ul className="remake-storyboard-product__details">
                        {preserveDetails.map((detail, index) => (
                            <li key={`${index}-${detail}`}>{detail}</li>
                        ))}
                    </ul>
                )}
            </div>
        </section>
    );

    return (
        <div className="remake-storyboard mx-auto w-full max-w-6xl space-y-5">
            <div className="remake-storyboard-overview">
                <p>
                    {logicalSceneCount} cảnh · {compileResult.inputSummary.targetDuration} giây ·{" "}
                    {compileResult.inputSummary.aspectRatio}
                </p>
                <span>Chưa tạo video</span>
            </div>
            <RemakeSourceAudio value={compileResult.referenceAnalysis?.sourceAudio} />
            <div className={sourceMap ? "remake-storyboard-workspace" : "space-y-5"}>
                <aside id={`${id}-reference`} className="remake-storyboard-reference">
                    <div className="remake-storyboard-section-heading">
                        <h2>Video mẫu</h2>
                        <p>Chọn cảnh để đối chiếu</p>
                    </div>
                    {sourceMap && (
                        <div className="remake-storyboard-source">
                            <RemakeSourceTimeline
                                referenceUrl={referenceUrl}
                                sourceStartFrame={sourceMap.sourceStartFrame}
                                totalFrames={
                                    sourceMap.timingMode === "fit_target"
                                        ? sourceMap.sourceFrameCount
                                        : compileResult.inputSummary.targetDuration * 24
                                }
                                sourceCutFrames={sourceCutFrames ?? compiledCuts}
                                compiledCutFrames={compiledCuts}
                                selectedScene={activeSceneIndex}
                                onSelect={setSelectedScene}
                                onCutsChange={onSourceCutFramesChange}
                                onRecompile={
                                    compileResult.renderPlan?.groups ? undefined : onRecompile
                                }
                                disabled={disabled}
                                isRecompiling={isRecompiling}
                                thumbnails={sourceMap.scenes.map((scene) => scene.thumbnailUrl)}
                            />
                        </div>
                    )}
                    {!sourceMap && productReference}
                </aside>
                <div id={`${id}-scenes`} className="remake-storyboard-review">
                    <div className="remake-storyboard-section-heading">
                        <h2>Kịch bản</h2>
                        <p>{logicalSceneCount} cảnh cho sản phẩm của bạn</p>
                    </div>
                    {sourceMap?.timingMode === "fit_target" && (
                        <RemakeLogicalStoryboard
                            compiled={compileResult}
                            selectedScene={activeSceneIndex}
                            onSceneChange={onSceneChange}
                            disabled={disabled}
                        />
                    )}
                    {sourceMap?.timingMode !== "fit_target" &&
                        scenes.map((scene) => {
                            const sceneId = `${id}-scene-${scene.index}`;
                            const promptLength = Array.from(scene.videoPrompt).length;
                            const promptTooLong =
                                Boolean(editedScenes[scene.id]) &&
                                promptLength > VIDEO_PROMPT_LIMIT;
                            const copyContent = `Prompt tạo video\n${scene.videoPrompt}\n\nPrompt tạo ảnh\n${scene.imagePrompt}\n\nPrompt tổng hợp\n${scene.prompt}`;
                            const copyState =
                                copyStates[scene.id]?.content === copyContent
                                    ? copyStates[scene.id].status
                                    : undefined;

                            return (
                                <section
                                    key={scene.id}
                                    aria-labelledby={`${sceneId}-heading`}
                                    className={`remake-script-scene min-w-0 rounded-3xl bg-surface p-5 sm:p-6 ${sourceMap && activeSceneIndex !== scene.index ? "hidden" : ""}`}
                                >
                                    <div className="mb-5 flex flex-wrap items-center gap-3">
                                        <h2
                                            id={`${sceneId}-heading`}
                                            className="font-semibold text-text-primary"
                                        >
                                            Cảnh {scene.index + 1}
                                        </h2>
                                        <span className="ml-auto text-xs tabular-nums text-text-secondary">
                                            {scene.start}–{scene.end} giây
                                        </span>
                                    </div>
                                    <div
                                        className={`grid min-w-0 items-start gap-6 ${!sourceMap ? "md:grid-cols-[minmax(0,200px)_minmax(0,1fr)]" : ""}`}
                                    >
                                        {!sourceMap && (
                                            <div className="min-w-0 space-y-3">
                                                <div className="flex h-52 items-center justify-center rounded-2xl bg-surface-soft p-2.5 sm:h-60">
                                                    {referenceUrl ? (
                                                        <video
                                                            src={referenceUrl}
                                                            controls
                                                            playsInline
                                                            preload="metadata"
                                                            aria-label={`Video mẫu tham chiếu cho cảnh ${scene.index + 1}`}
                                                            className="h-auto max-h-full w-auto max-w-full rounded-xl object-contain"
                                                        />
                                                    ) : (
                                                        <div className="space-y-2 text-center text-text-tertiary">
                                                            <Video
                                                                className="mx-auto size-8"
                                                                aria-hidden="true"
                                                            />
                                                            <p className="text-xs">Video mẫu</p>
                                                        </div>
                                                    )}
                                                </div>
                                                <p className="text-xs text-text-secondary">
                                                    Video tham chiếu · Chưa tạo video
                                                </p>
                                                <div className="flex items-center gap-2 rounded-xl bg-surface-soft p-3">
                                                    {productUrl ? (
                                                        <img
                                                            src={productUrl}
                                                            alt="Ảnh sản phẩm tham chiếu"
                                                            className="size-12 shrink-0 rounded-lg object-contain"
                                                        />
                                                    ) : (
                                                        <Image
                                                            className="size-6 shrink-0 text-text-tertiary"
                                                            aria-hidden="true"
                                                        />
                                                    )}
                                                    <span className="min-w-0 text-xs text-text-secondary">
                                                        Sản phẩm của bạn
                                                    </span>
                                                    <ArrowRight
                                                        className="ml-auto size-4 shrink-0 text-text-tertiary"
                                                        aria-hidden="true"
                                                    />
                                                </div>
                                            </div>
                                        )}
                                        <div className="min-w-0 space-y-4">
                                            <div className="space-y-2">
                                                <p className="text-sm font-medium text-text-primary">
                                                    Nội dung chính
                                                </p>
                                                <p className="text-sm text-text-secondary">
                                                    {scene.title}
                                                </p>
                                            </div>
                                            <div className="grid gap-3 rounded-2xl bg-surface-soft p-4 sm:grid-cols-2">
                                                <div>
                                                    <p className="text-xs font-medium text-text-primary">
                                                        Giữ từ video mẫu
                                                    </p>
                                                    <p className="mt-1 text-xs leading-relaxed text-text-secondary">
                                                        Hành động, cách quay và nhịp cảnh theo kịch
                                                        bản đã phân tích.
                                                    </p>
                                                </div>
                                                <div>
                                                    <p className="text-xs font-medium text-text-primary">
                                                        Thay bằng sản phẩm của bạn
                                                    </p>
                                                    <p className="mt-1 text-xs leading-relaxed text-text-secondary">
                                                        Dùng ảnh chính để tham chiếu nhận diện sản
                                                        phẩm. Bạn kiểm tra lại trên video tạo ra.
                                                    </p>
                                                </div>
                                            </div>
                                            <div className="space-y-2">
                                                <p className="text-sm font-medium text-text-primary">
                                                    Điều sẽ diễn ra
                                                </p>
                                                <p className="whitespace-pre-wrap text-sm leading-relaxed text-text-secondary">
                                                    {scene.description ||
                                                        "Hệ thống đã tự tạo hướng dẫn cho cảnh này từ video mẫu và ảnh sản phẩm."}
                                                </p>
                                            </div>
                                            <p className="text-sm leading-relaxed text-text-secondary">
                                                Hệ thống đã phân tích video mẫu và tự tạo hướng dẫn
                                                cho từng cảnh. Bạn có thể tạo video ngay, không cần
                                                viết prompt.
                                            </p>
                                            <details className="rounded-xl bg-surface-soft p-3">
                                                <summary className="min-h-8 cursor-pointer text-sm text-text-secondary focus-visible:rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
                                                    Nâng cao · Xem/chỉnh prompt tự động (không bắt
                                                    buộc)
                                                </summary>
                                                <div className="mt-3 space-y-4">
                                                    <div className="space-y-2">
                                                        <div className="flex flex-wrap items-center justify-between gap-2">
                                                            <label
                                                                htmlFor={`${sceneId}-video-prompt`}
                                                                className="flex items-center gap-2 text-sm font-medium text-text-primary"
                                                            >
                                                                <MessageSquareText
                                                                    className="size-4 text-primary"
                                                                    aria-hidden="true"
                                                                />
                                                                Prompt tạo video
                                                            </label>
                                                            <Button
                                                                type="button"
                                                                variant="ghost"
                                                                className="min-h-11 text-text-secondary"
                                                                aria-label={`Sao chép prompt cảnh ${scene.index + 1}`}
                                                                disabled={copyState === "copying"}
                                                                onClick={() =>
                                                                    void copyPrompts(
                                                                        scene.id,
                                                                        copyContent,
                                                                    )
                                                                }
                                                            >
                                                                {copyState === "copying" ? (
                                                                    <Loader2
                                                                        className="animate-spin motion-reduce:animate-none"
                                                                        aria-hidden="true"
                                                                    />
                                                                ) : (
                                                                    <Copy aria-hidden="true" />
                                                                )}
                                                                Sao chép
                                                            </Button>
                                                        </div>
                                                        <Textarea
                                                            id={`${sceneId}-video-prompt`}
                                                            value={scene.videoPrompt}
                                                            onChange={(event) => {
                                                                setEditedScenes((current) => ({
                                                                    ...current,
                                                                    [scene.id]: true,
                                                                }));
                                                                changeScene(scene.id, scene.index, {
                                                                    videoPrompt: event.target.value,
                                                                });
                                                            }}
                                                            disabled={disabled}
                                                            aria-invalid={promptTooLong}
                                                            aria-describedby={`${sceneId}-prompt-helper ${sceneId}-prompt-count${promptTooLong ? ` ${sceneId}-prompt-error` : ""}`}
                                                            placeholder="Chưa có yêu cầu tạo video cho cảnh này."
                                                            className={`${fieldClass} min-h-36 leading-relaxed`}
                                                        />
                                                        <p
                                                            id={`${sceneId}-prompt-count`}
                                                            className="text-right text-xs tabular-nums text-text-secondary"
                                                        >{`${promptLength.toLocaleString("vi-VN")} / ${VIDEO_PROMPT_LIMIT.toLocaleString("vi-VN")} ký tự`}</p>
                                                        {promptTooLong && (
                                                            <p
                                                                id={`${sceneId}-prompt-error`}
                                                                role="alert"
                                                                className="text-xs text-destructive"
                                                            >
                                                                Hãy rút gọn prompt còn tối đa 12.000
                                                                ký tự trước khi tạo video.
                                                            </p>
                                                        )}
                                                        <p
                                                            id={`${sceneId}-prompt-helper`}
                                                            className="text-xs leading-relaxed text-text-secondary"
                                                        >
                                                            Prompt đã được tạo tự động. Chỉ chỉnh
                                                            nếu bạn muốn thay đổi hướng dẫn; bản sửa
                                                            sẽ kết hợp với thông tin sản phẩm để tạo
                                                            cảnh.
                                                        </p>
                                                        {copyState === "copied" && (
                                                            <p
                                                                role="status"
                                                                className="text-xs text-text-secondary"
                                                            >
                                                                Đã sao chép cả 3 prompt của cảnh{" "}
                                                                {scene.index + 1}.
                                                            </p>
                                                        )}
                                                        {copyState === "error" && (
                                                            <div className="space-y-2">
                                                                <p
                                                                    role="status"
                                                                    className="text-xs text-text-secondary"
                                                                >
                                                                    Chưa sao chép được. Chọn nội
                                                                    dung bên dưới rồi sao chép thủ
                                                                    công.
                                                                </p>
                                                                <Textarea
                                                                    readOnly
                                                                    aria-label={`Nội dung prompt cảnh ${scene.index + 1} để sao chép thủ công`}
                                                                    value={copyContent}
                                                                    onFocus={(event) =>
                                                                        event.currentTarget.select()
                                                                    }
                                                                    className={`${fieldClass} min-h-28`}
                                                                />
                                                            </div>
                                                        )}
                                                    </div>
                                                    <div className="space-y-2">
                                                        <label
                                                            htmlFor={`${sceneId}-image-prompt`}
                                                            className="text-sm font-medium text-text-primary"
                                                        >
                                                            Prompt tạo ảnh
                                                        </label>
                                                        <Textarea
                                                            id={`${sceneId}-image-prompt`}
                                                            value={scene.imagePrompt}
                                                            onChange={(event) =>
                                                                changeScene(scene.id, scene.index, {
                                                                    imagePrompt: event.target.value,
                                                                })
                                                            }
                                                            disabled={disabled}
                                                            className="min-h-28 border-0 bg-surface shadow-none focus-visible:ring-2 focus-visible:ring-ring/60"
                                                        />
                                                    </div>
                                                    <div className="space-y-2">
                                                        <label
                                                            htmlFor={`${sceneId}-prompt`}
                                                            className="text-sm font-medium text-text-primary"
                                                        >
                                                            Prompt tổng hợp
                                                        </label>
                                                        <Textarea
                                                            id={`${sceneId}-prompt`}
                                                            value={scene.prompt}
                                                            onChange={(event) =>
                                                                changeScene(scene.id, scene.index, {
                                                                    prompt: event.target.value,
                                                                })
                                                            }
                                                            disabled={disabled}
                                                            className="min-h-28 border-0 bg-surface shadow-none focus-visible:ring-2 focus-visible:ring-ring/60"
                                                        />
                                                        <p className="text-xs text-text-secondary">
                                                            Khi có yêu cầu tạo video riêng, hệ thống
                                                            ưu tiên nội dung ở ô Prompt tạo video.
                                                        </p>
                                                    </div>
                                                </div>
                                            </details>
                                        </div>
                                    </div>
                                </section>
                            );
                        })}
                    {sourceMap && productReference}
                </div>
            </div>
            {sourceMap && (
                <details id={`${id}-generation`} className="remake-storyboard-generation">
                    <summary>Kế hoạch tạo video và cấu hình nâng cao</summary>
                    {compileResult.renderPlan ? (
                        <RemakeRenderGroups
                            plan={compileResult.renderPlan}
                            breaks={
                                renderGroupBreaks ?? getRenderGroupBreaks(compileResult.renderPlan)
                            }
                            onBreaksChange={onRenderGroupBreaksChange}
                            dirty={sourcePlanDirty}
                            cutsDirty={sourceCutsDirty}
                            disabled={disabled || Boolean(sourceCutsError)}
                            onRecompile={compileResult.renderPlan.groups ? onRecompile : undefined}
                        />
                    ) : (
                        <p className="mt-3 text-sm leading-relaxed text-text-secondary">
                            {sourceMap.scenes.length} cảnh · {sourceMap.scenes.length} lượt tạo ·
                            Video hoàn chỉnh {compileResult.inputSummary.targetDuration} giây. Mỗi
                            lượt tạo một clip 8 giây. Bạn chọn và duyệt đoạn phù hợp cho từng cảnh
                            trước khi ghép.
                        </p>
                    )}
                </details>
            )}
            <p className="remake-storyboard-next">
                Xem lại kịch bản rồi bấm tạo video. Bạn không cần chỉnh prompt để tiếp tục.
            </p>
        </div>
    );
}
