import { Eye, Loader2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import type { SmartRemakeCompileResult, SmartRemakeRequirements } from "@/shared/api/smart-remake";
import { ApiError } from "@/shared/api/errors";
import {
    previewSmartRemakeKiePrompts,
    type SmartRemakePromptPreview,
    type SmartRemakePromptPreviewInput,
} from "@/shared/api/smart-remake-prompt-preview";
import { Button } from "@/shared/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/shared/ui/dialog";
import { RemakeKiePrompt } from "./remake-generated-media";
import { updateRemakeScene, type RemakeScenePatch } from "../lib/remake-studio";

type Props = {
    workspaceId?: string;
    projectRevision?: number;
    compileResult: SmartRemakeCompileResult;
    sceneDrafts?: Record<number, RemakeScenePatch>;
    requirements?: SmartRemakeRequirements;
    stale?: boolean;
};

export function RemakePlannedKiePrompts(props: Props) {
    const plan = props.compileResult.renderPlan;
    let ready = props.compileResult;
    let invalidDraft = false;
    try {
        ready = Object.entries(props.sceneDrafts ?? {}).reduce(
            (value, [index, patch]) => updateRemakeScene(value, Number(index), patch),
            ready,
        );
    } catch {
        invalidDraft = true;
    }
    const input: SmartRemakePromptPreviewInput = {
        expectedRevision: props.projectRevision ?? props.compileResult.revision ?? 0,
        scenePrompts: (plan?.units ?? []).map((unit, index) => {
            const draft = ready.sceneMap.scenes[index];
            return {
                renderUnitId: unit.id,
                prompt: typeof draft?.prompt === "string" ? draft.prompt : unit.prompt,
                imagePrompt:
                    typeof draft?.imagePrompt === "string" ? draft.imagePrompt : unit.imagePrompt,
                videoPrompt:
                    typeof draft?.videoPrompt === "string" ? draft.videoPrompt : unit.videoPrompt,
            };
        }),
        ...(props.requirements ? { requirements: props.requirements } : {}),
    };
    const identity = JSON.stringify({
        workspaceId: props.workspaceId,
        projectId: props.compileResult.projectId,
        input,
        groups: plan?.groups,
        stale: Boolean(props.stale),
        invalidDraft,
    });
    return (
        <PromptPreviewSession key={identity} {...props} input={input} invalidDraft={invalidDraft} />
    );
}

function PromptPreviewSession({
    workspaceId,
    compileResult,
    stale,
    input,
    invalidDraft,
}: Props & { input: SmartRemakePromptPreviewInput; invalidDraft: boolean }) {
    const groups = compileResult.renderPlan?.groups ?? [];
    const [selected, setSelected] = useState<string | null>(null);
    const [preview, setPreview] = useState<SmartRemakePromptPreview | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const request = useRef<AbortController | null>(null);
    useEffect(() => () => request.current?.abort(), []);
    const available = Boolean(
        workspaceId &&
        compileResult.projectId &&
        input.expectedRevision > 0 &&
        groups.length &&
        !invalidDraft,
    );
    const selectedIndex = groups.findIndex((group) => group.id === selected);
    const current = preview?.groups.find((group) => group.groupId === selected);

    async function loadPreview() {
        if (!workspaceId || !compileResult.projectId || !available || stale) return;
        request.current?.abort();
        const controller = new AbortController();
        request.current = controller;
        setLoading(true);
        setError(null);
        try {
            const result = await previewSmartRemakeKiePrompts(
                workspaceId,
                compileResult.projectId,
                input,
                { signal: controller.signal },
            );
            if (controller.signal.aborted) return;
            if (
                result.projectId !== compileResult.projectId ||
                result.revision !== input.expectedRevision ||
                groups.some((group) => !result.groups.some((item) => item.groupId === group.id))
            )
                throw new Error("Preview binding changed");
            setPreview(result);
        } catch (cause) {
            if (controller.signal.aborted) return;
            setError(
                cause instanceof ApiError && cause.status === 409
                    ? "Kịch bản đã được cập nhật. Làm mới dự án rồi thử lại."
                    : "Chưa lấy được prompt. Thử lại nhé.",
            );
        } finally {
            if (!controller.signal.aborted) setLoading(false);
        }
    }

    return (
        <section
            aria-label="Prompt KIE ở bước duyệt kịch bản"
            className="flex flex-wrap items-center justify-between gap-4 rounded-2xl bg-surface px-5 py-4"
        >
            <div className="space-y-1">
                <h2 className="text-sm font-semibold">Prompt KIE cho từng clip</h2>
                <p className="text-xs text-text-secondary">
                    Xem và sao chép hướng dẫn cho từng clip trước khi tạo video.
                </p>
            </div>
            <div className="flex flex-wrap gap-2">
                {groups.map((group, index) => (
                    <Button
                        key={group.id}
                        type="button"
                        variant="ghost"
                        className="min-h-11 bg-primary-soft text-primary hover:bg-primary-soft/80"
                        disabled={!available || stale}
                        onClick={() => {
                            setSelected(group.id);
                            if (!preview) void loadPreview();
                        }}
                    >
                        <Eye className="size-4" aria-hidden="true" /> Clip {index + 1} · Xem prompt
                        KIE
                    </Button>
                ))}
            </div>
            {(stale || !available) && (
                <p role="status" className="text-xs text-text-secondary">
                    {invalidDraft
                        ? "Hoàn tất nội dung cảnh trước khi xem prompt KIE."
                        : stale
                          ? "Kịch bản hoặc mốc cắt đã thay đổi. Cập nhật kịch bản để xem prompt KIE mới."
                          : "Chưa có dữ liệu dự án đã lưu để xem prompt KIE. Cập nhật kịch bản để tiếp tục."}
                </p>
            )}
            <Dialog
                open={selected !== null}
                onOpenChange={(open) => {
                    if (!open) setSelected(null);
                }}
            >
                <DialogContent className="max-h-[85vh] max-w-3xl overflow-y-auto rounded-3xl border-0 sm:max-w-3xl">
                    <DialogTitle>Clip {selectedIndex + 1} · Prompt KIE</DialogTitle>
                    <DialogDescription>
                        Hướng dẫn theo kịch bản và các chỉnh sửa hiện tại của bạn.
                    </DialogDescription>
                    {loading ? (
                        <p
                            role="status"
                            className="flex items-center gap-2 py-4 text-sm text-text-secondary"
                        >
                            <Loader2 className="size-4 animate-spin" aria-hidden="true" />
                            Đang chuẩn bị prompt…
                        </p>
                    ) : error ? (
                        <div className="space-y-3">
                            <p role="alert" className="text-sm text-warn">
                                {error}
                            </p>
                            <Button
                                type="button"
                                variant="ghost"
                                onClick={() => void loadPreview()}
                            >
                                Thử lại
                            </Button>
                        </div>
                    ) : (
                        current && <RemakeKiePrompt request={current} mode="planned" expanded />
                    )}
                </DialogContent>
            </Dialog>
        </section>
    );
}
