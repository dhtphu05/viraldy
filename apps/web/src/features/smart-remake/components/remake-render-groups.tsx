import { Check, Clapperboard, Image, Layers3 } from "lucide-react";
import type { SmartRemakeRenderPlan } from "@/shared/api/smart-remake";
import { Button } from "@/shared/ui/button";
import { getRenderGroups, previewRenderGroups } from "../lib/remake-groups";

const seconds = (frames: number) => Number((frames / 24).toFixed(3)).toLocaleString("vi-VN");

export function RemakeRenderGroups({
    plan,
    breaks,
    onBreaksChange,
    dirty = false,
    cutsDirty = false,
    disabled,
    onRecompile,
}: {
    plan: SmartRemakeRenderPlan;
    breaks: number[];
    onBreaksChange?(breaks: number[]): void;
    dirty?: boolean;
    cutsDirty?: boolean;
    disabled: boolean;
    onRecompile?(): void;
}) {
    const fixedProviderWindows = plan.groupingPolicy === "fixed_provider_windows";
    const groups =
        !fixedProviderWindows && dirty && !cutsDirty
            ? previewRenderGroups(plan, breaks)
            : getRenderGroups(plan);
    const logicalIds = [...new Set(plan.units.map((unit) => unit.sourceSceneId))];
    const fragmented = logicalIds.length !== plan.units.length;
    const videoResolution =
        plan.videoResolution ??
        (plan.videoModel === "wan/3-0-video" || plan.videoModel === "veo3_lite"
            ? "720P"
            : undefined);
    const imageModelLabel =
        plan.imageModel === "gpt-image-2.6-sunburst"
            ? "GPT Image Sunburst · OpenAI"
            : plan.imageModel === "gpt-image-2.6-flare"
              ? "GPT Image Flare · OpenAI"
              : "GPT Image · OpenAI";
    const qualityLabel = plan.imageQuality
        ? {
              low: "Tiết kiệm",
              medium: "Chất lượng vừa",
              high: "Chất lượng cao",
              xhigh: "Chất lượng rất cao",
              max: "Chất lượng tối đa",
          }[plan.imageQuality]
        : "Theo cấu hình";
    const complexityLabel = plan.imageComplexity
        ? { low: "Suy tính thấp", medium: "Suy tính vừa", high: "Suy tính cao" }[
              plan.imageComplexity
          ]
        : null;
    return (
        <section
            aria-label="Kế hoạch tạo video"
            className="min-w-0 space-y-4 rounded-3xl bg-surface p-5 sm:p-6"
        >
            <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0 space-y-1">
                    <h2 className="flex items-center gap-2 font-semibold text-text-primary">
                        <Layers3 className="size-5 shrink-0 text-primary" aria-hidden="true" />
                        {logicalIds.length} cảnh ·{" "}
                        {fragmented ? `${plan.units.length} đoạn render · ` : ""}
                        {groups.length} lượt tạo video
                    </h2>
                    <p className="text-xs leading-relaxed text-text-secondary">
                        Video hoàn chỉnh{" "}
                        {seconds(
                            plan.units.reduce(
                                (total, unit) => total + unit.targetDurationFrames,
                                0,
                            ),
                        )}{" "}
                        giây.{" "}
                        {fixedProviderWindows
                            ? `KIE tạo ${groups.length} clip 8 giây; toàn bộ cảnh được phân bổ vào các clip này.`
                            : "Các cảnh liền nhau được tạo chung khi vừa một clip 8 giây; nhịp từng cảnh vẫn giữ riêng."}
                    </p>
                </div>
                {dirty && (
                    <span className="rounded-full bg-warn-soft px-3 py-1.5 text-xs text-warn">
                        Chưa cập nhật
                    </span>
                )}
            </div>
            <div className="grid min-w-0 gap-3 md:grid-cols-2">
                <div className="flex min-w-0 items-start gap-3 rounded-2xl bg-surface-soft p-4">
                    <Clapperboard
                        className="mt-0.5 size-4 shrink-0 text-primary"
                        aria-hidden="true"
                    />
                    <div className="min-w-0">
                        <p className="text-sm font-medium">
                            {plan.videoModel === "wan/3-0-video"
                                ? "Wan 3.0 · KIE"
                                : plan.videoModel === "veo3_lite"
                                  ? "Veo 3.1 Lite · KIE"
                                  : "KIE"}
                        </p>
                        <p className="mt-1 text-xs text-text-secondary">
                            Clip dọc 9:16{videoResolution ? ` · ${videoResolution}` : ""} · 8 giây
                            mỗi lượt
                        </p>
                    </div>
                </div>
                <div className="flex min-w-0 items-start gap-3 rounded-2xl bg-surface-soft p-4">
                    <Image className="mt-0.5 size-4 shrink-0 text-primary" aria-hidden="true" />
                    <div className="min-w-0">
                        <p className="text-sm font-medium">
                            {plan.imageModel ? imageModelLabel : "Ảnh sản phẩm gốc"}
                        </p>
                        <p className="mt-1 text-xs text-text-secondary">
                            {plan.imageModel
                                ? `${plan.imageSize?.replace("x", " × ") ?? "9:16"} · ${qualityLabel}${complexityLabel ? ` · ${complexityLabel}` : ""}`
                                : "Dùng ảnh bạn đã thêm làm tham chiếu"}
                        </p>
                    </div>
                </div>
            </div>
            <div className="remake-generation-groups">
                {groups.map((group, index) => (
                    <article key={group.id} className="min-w-0 rounded-2xl bg-primary-soft/55 p-4">
                        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                            <h3 className="text-sm font-semibold">Clip {index + 1}</h3>
                            <span className="text-xs text-text-secondary">
                                {group.renderUnitIds.length} {fragmented ? "đoạn render" : "cảnh"} ·
                                1 lượt tạo
                            </span>
                        </div>
                        <div
                            className="flex h-2 overflow-hidden rounded-full bg-surface"
                            aria-hidden="true"
                        >
                            {group.segments.map((segment, at) => (
                                <span
                                    key={segment.renderUnitId}
                                    style={{
                                        width: `${((segment.outFrame - segment.inFrame) / group.rawDurationFrames) * 100}%`,
                                    }}
                                    className={at % 2 ? "bg-primary/35" : "bg-primary/70"}
                                />
                            ))}
                        </div>
                        <ol className="mt-3 space-y-1.5 text-xs tabular-nums text-text-secondary">
                            {group.segments.map((segment) => (
                                <li key={segment.renderUnitId}>
                                    {(() => {
                                        const unit = plan.units.find(
                                            (value) => value.id === segment.renderUnitId,
                                        );
                                        return unit
                                            ? `Cảnh ${logicalIds.indexOf(unit.sourceSceneId) + 1}${(unit.fragmentCount ?? 1) > 1 ? ` · đoạn ${(unit.fragmentIndex ?? 0) + 1}/${unit.fragmentCount}` : ""}`
                                            : "Đoạn render";
                                    })()}
                                    : {seconds(segment.inFrame)}–{seconds(segment.outFrame)} giây
                                </li>
                            ))}
                        </ol>
                    </article>
                ))}
            </div>
            {!fixedProviderWindows && onBreaksChange && plan.groups && plan.units.length > 1 && (
                <details className="rounded-2xl bg-surface-soft/60 p-4">
                    <summary className="min-h-7 cursor-pointer text-sm font-medium">
                        Chọn cảnh cần tạo riêng
                    </summary>
                    <p className="mt-2 text-xs leading-relaxed text-text-secondary">
                        Tách nhóm khi cần kiểm soát hành động hoặc bố cục kỹ hơn. Việc này có thể
                        tăng số lượt tạo video.
                    </p>
                    <div className="mt-2 grid min-w-0 gap-x-5 md:grid-cols-2">
                        {plan.units.slice(0, -1).map((unit, index) => (
                            <label
                                key={unit.id}
                                className="flex min-h-11 min-w-0 cursor-pointer items-center gap-3 py-2 text-xs"
                            >
                                <input
                                    type="checkbox"
                                    className="size-4 shrink-0 accent-primary"
                                    checked={breaks.includes(index + 1)}
                                    disabled={disabled || cutsDirty}
                                    onChange={(event) =>
                                        onBreaksChange(
                                            event.target.checked
                                                ? [...breaks, index + 1].sort((a, b) => a - b)
                                                : breaks.filter((value) => value !== index + 1),
                                        )
                                    }
                                />
                                <span>
                                    Tách nhóm sau {fragmented ? "đoạn render" : "cảnh"} {index + 1}
                                </span>
                            </label>
                        ))}
                    </div>
                </details>
            )}
            <p className="text-xs leading-relaxed text-text-secondary">
                Các mốc trên là hướng dẫn cho AI; bạn vẫn cần xem và duyệt từng cảnh trong clip thực
                tế trước khi ghép.
            </p>
            {cutsDirty && (
                <p role="status" className="text-xs text-text-secondary">
                    Mốc cắt đã đổi. Cập nhật kịch bản để tính lại nhóm sinh video.
                </p>
            )}
            {onRecompile && (
                <Button
                    type="button"
                    className="min-h-11"
                    disabled={disabled || !dirty}
                    onClick={onRecompile}
                >
                    <Check className="size-4" aria-hidden="true" />
                    Cập nhật kịch bản
                </Button>
            )}
        </section>
    );
}
