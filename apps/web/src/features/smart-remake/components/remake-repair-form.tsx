import { useId, useState } from "react";
import { Loader2, Sparkles, Undo2 } from "lucide-react";
import type {
    RepairIntent,
    SmartRemakeProject,
    SmartRemakePromptDraft,
    SmartRemakeSceneVersion,
} from "@/shared/api/smart-remake";
import { cn } from "@/shared/lib/utils";
import { Button } from "@/shared/ui/button";
import { Textarea } from "@/shared/ui/textarea";

type Scene = SmartRemakeProject["scenes"][number];
export type RemakeRepairDraft = RepairIntent;
export interface RemakeRepairFormProps {
    workspaceId: string;
    projectId: string;
    scene: Scene;
    sceneLabel?: string;
    clip?: { index: number; durationSeconds: number };
    active?: SmartRemakeSceneVersion;
    busy: boolean;
    onRepair(intent: RepairIntent): Promise<void>;
    draft?: RemakeRepairDraft;
    onDraftChange?(draft: RemakeRepairDraft): void;
    saveStatus?: string;
    failureReason?: string;
    legacyDraftAvailable?: boolean;
    onImportLegacyDraft?(): void;
}
const quietButton = "min-h-11 border-0 bg-surface-soft shadow-none hover:bg-surface-muted";
const primaryButton =
    "min-h-12 bg-[#e00b41] text-sm text-white hover:bg-[#c90a3a] focus-visible:ring-[#e00b41]/40";
const fieldClass =
    "border-0 bg-surface-soft shadow-none focus-visible:ring-2 focus-visible:ring-ring/60";
const repairReasons = [
    ["product_fidelity", "Sai sản phẩm"],
    ["action", "Chuyển động chưa đúng"],
    ["presentation", "Cách thể hiện chưa rõ"],
] as const;
const emptyDraft = (): RemakeRepairDraft => ({ schemaVersion: 1, issues: [], instruction: "" });

export function RemakeRepairForm(props: RemakeRepairFormProps) {
    const { scene, active, busy } = props;
    const usableBase = Boolean(
        active?.videoUrl &&
        active.id === scene.activeVersionId &&
        active.technicalCheck.status === "passed",
    );
    const id = useId();
    const [localDraft, setLocalDraft] = useState<RemakeRepairDraft>(emptyDraft);
    const draft = props.draft ?? localDraft;
    const base: SmartRemakePromptDraft = {
        prompt: active?.prompt ?? scene.prompt,
        imagePrompt: active?.imagePrompt ?? scene.imagePrompt,
        videoPrompt: active?.videoPrompt ?? scene.videoPrompt,
    };
    function change(next: RemakeRepairDraft) {
        setLocalDraft(next);
        props.onDraftChange?.(next);
    }
    function updateAdvanced(field: keyof SmartRemakePromptDraft, value: string) {
        const edits = { ...draft.advancedEdits };
        if (value === base[field]) delete edits[field];
        else edits[field] = value;
        const { advancedEdits: _previous, ...rest } = draft;
        change(Object.keys(edits).length ? { ...rest, advancedEdits: edits } : rest);
    }
    const instructionTooLong = Array.from(draft.instruction).length > 4000;
    const advancedInvalid = Object.values(draft.advancedEdits ?? {}).some(
        (value) => typeof value !== "string" || !value.trim() || Array.from(value).length > 12000,
    );
    const changed = Boolean(draft.instruction || draft.issues.length || draft.advancedEdits);
    if (!usableBase)
        return (
            <p role="status" className="text-sm text-text-secondary">
                Chưa có clip để sửa. Hoàn tất lượt tạo video trước khi tạo một bản sửa.
            </p>
        );
    return (
        <form
            className="space-y-4"
            onSubmit={(event) => {
                event.preventDefault();
                if (!usableBase || busy || instructionTooLong || advancedInvalid) return;
                void props.onRepair({
                    ...draft,
                    issues: draft.issues.length ? draft.issues : ["alternate_take"],
                    instruction: draft.instruction.trim(),
                });
            }}
        >
            <div>
                <h3 className="font-medium text-text-primary">
                    {props.clip
                        ? `Bạn muốn sửa Clip ${props.clip.index} ở điểm nào?`
                        : "Bạn muốn sửa điều gì?"}
                </h3>
                <p className="mt-2 text-sm leading-relaxed text-text-secondary">
                    {props.clip ? (
                        `AI sẽ tạo lại toàn bộ Clip ${props.clip.index} (${props.clip.durationSeconds} giây). Các clip khác được giữ nguyên.`
                    ) : (
                        <>
                            AI sẽ tạo lại clip{" "}
                            {scene.rawDurationFrames
                                ? scene.rawDurationFrames / 24
                                : scene.durationSeconds}{" "}
                            giây của {props.sceneLabel?.toLowerCase() ?? `cảnh ${scene.index + 1}`}.
                            Các clip khác được giữ nguyên.
                        </>
                    )}
                </p>
            </div>
            <div className="flex flex-wrap gap-2" aria-label="Gợi ý yêu cầu sửa">
                {repairReasons.map(([issue, label]) => (
                    <Button
                        key={issue}
                        type="button"
                        variant="ghost"
                        className={cn(
                            quietButton,
                            "rounded-full px-3 text-xs",
                            draft.issues.includes(issue) && "bg-primary-soft text-primary",
                        )}
                        disabled={busy}
                        aria-pressed={draft.issues.includes(issue)}
                        onClick={() =>
                            change({
                                ...draft,
                                issues: draft.issues.includes(issue)
                                    ? draft.issues.filter((value) => value !== issue)
                                    : [
                                          ...draft.issues.filter(
                                              (value) => value !== "alternate_take",
                                          ),
                                          issue,
                                      ],
                            })
                        }
                    >
                        {label}
                    </Button>
                ))}
            </div>
            <div className="space-y-2">
                {props.failureReason && (
                    <p
                        id={`${id}-failure`}
                        role="alert"
                        className="rounded-xl bg-destructive-soft p-3 text-sm leading-relaxed text-destructive"
                    >
                        {props.failureReason}
                    </p>
                )}
                <label htmlFor={`${id}-motion`} className="text-sm font-medium text-text-primary">
                    Bạn muốn thay đổi điều gì? (không bắt buộc)
                </label>
                <Textarea
                    id={`${id}-motion`}
                    aria-describedby={props.failureReason ? `${id}-failure` : undefined}
                    value={draft.instruction}
                    maxLength={4000}
                    onChange={(event) => change({ ...draft, instruction: event.target.value })}
                    disabled={busy}
                    placeholder="Ví dụ: Mở nắp chậm hơn, giữ nguyên nền và góc quay."
                    className={cn(fieldClass, "min-h-28")}
                />
                <p className="text-xs leading-relaxed text-text-secondary">
                    Chọn vấn đề hoặc mô tả ngắn điều cần sửa. Để trống để tạo một phiên bản khác;
                    không cần viết prompt.
                </p>
            </div>
            {!props.clip && (
                <details>
                    <summary className="min-h-11 cursor-pointer rounded-lg py-3 text-sm font-medium text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
                        Nâng cao · Prompt tự động
                    </summary>
                    <div className="space-y-4 pt-2">
                        {(
                            [
                                ["videoPrompt", "Prompt tạo video"],
                                ["imagePrompt", "Prompt tạo ảnh"],
                                ["prompt", "Prompt tổng hợp"],
                            ] as const
                        ).map(([field, label]) => (
                            <div key={field} className="space-y-2">
                                <label
                                    htmlFor={`${id}-${field}`}
                                    className="text-sm text-text-primary"
                                >
                                    {label}
                                </label>
                                <Textarea
                                    id={`${id}-${field}`}
                                    value={draft.advancedEdits?.[field] ?? base[field]}
                                    maxLength={12000}
                                    onChange={(event) => updateAdvanced(field, event.target.value)}
                                    disabled={busy}
                                    className={cn(fieldClass, "min-h-28")}
                                />
                            </div>
                        ))}
                    </div>
                </details>
            )}
            <div className="flex flex-wrap items-center justify-between gap-2">
                <p role="status" className="text-xs text-text-secondary">
                    {props.saveStatus ??
                        (changed ? "Chưa lưu trên thiết bị này" : "Chưa có thay đổi")}
                </p>
                <Button
                    type="button"
                    variant="ghost"
                    className="min-h-11 text-xs"
                    disabled={busy || !changed}
                    onClick={() => change(emptyDraft())}
                >
                    <Undo2 className="size-4" aria-hidden="true" /> Hoàn tác bản nháp
                </Button>
            </div>
            {props.legacyDraftAvailable && props.onImportLegacyDraft && (
                <Button
                    type="button"
                    variant="outline"
                    className="min-h-11"
                    disabled={busy}
                    onClick={props.onImportLegacyDraft}
                >
                    Khôi phục bản nháp cũ
                </Button>
            )}
            <Button
                type="submit"
                className={cn(primaryButton, "w-full")}
                disabled={busy || instructionTooLong || advancedInvalid}
            >
                {busy ? (
                    <Loader2 className="motion-safe:animate-spin" aria-hidden="true" />
                ) : (
                    <Sparkles aria-hidden="true" />
                )}{" "}
                Tạo lại {props.sceneLabel?.toLowerCase() ?? `cảnh ${scene.index + 1}`}
            </Button>
            {(instructionTooLong || advancedInvalid) && (
                <p role="alert" className="text-xs text-destructive">
                    {instructionTooLong
                        ? "Yêu cầu vượt 4.000 ký tự. Rút gọn để tiếp tục."
                        : "Prompt Nâng cao cần có nội dung và không vượt 12.000 ký tự."}
                </p>
            )}
            <p className="text-xs leading-relaxed text-text-secondary">
                AI sẽ kiểm tra yêu cầu trước khi tạo ảnh và video, rồi gửi một bản mới để bạn so
                sánh. Bản đang dùng được giữ đến khi bạn áp dụng bản mới.
            </p>
        </form>
    );
}
