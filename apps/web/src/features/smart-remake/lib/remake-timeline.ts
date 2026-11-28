import type {
    SmartRemakeCompileResult,
    SmartRemakeProject,
    SmartRemakeSourceSceneMap,
} from "@/shared/api/smart-remake";
import { getRemakeSourceAudio } from "./remake-source-audio";

export const TIMELINE_FPS = 24;
export const RAW_CLIP_FRAMES = 8 * TIMELINE_FPS;

export function secondsToFrames(seconds: number): number {
    return Number.isFinite(seconds) && seconds >= 0 ? Math.round(seconds * TIMELINE_FPS) : 0;
}

export function getSourceExcerptError(
    sourceDuration: number | null,
    startFrame: number,
    targetSeconds: 8 | 12 | 16,
): string | null {
    if (sourceDuration === null || !Number.isFinite(sourceDuration) || sourceDuration <= 0)
        return "Đang đọc độ dài video mẫu…";
    if (!Number.isInteger(startFrame) || startFrame < 0)
        return "Chọn vị trí bắt đầu hợp lệ trong video mẫu nhé.";
    const totalFrames = Math.floor(sourceDuration * TIMELINE_FPS + 0.001);
    const targetFrames = targetSeconds * TIMELINE_FPS;
    if (totalFrames < targetFrames)
        return `Video mẫu ngắn hơn ${targetSeconds} giây. Chọn thời lượng phù hợp hoặc đổi video nhé.`;
    if (startFrame + targetFrames > totalFrames)
        return "Đoạn đã chọn vượt cuối video mẫu. Dời điểm bắt đầu về trước nhé.";
    return null;
}

export function validateSourceCuts(cuts: number[], totalFrames: number): string | null {
    if (cuts.length < 2) return "Cần ít nhất một cảnh phủ đủ video mẫu.";
    if (cuts[0] !== 0 || cuts.at(-1) !== totalFrames)
        return "Các cảnh cần phủ đủ đoạn mẫu đã chọn.";
    if (cuts.some((value) => !Number.isInteger(value) || value < 0))
        return "Mốc cắt cần nằm đúng khung hình trong đoạn mẫu.";
    for (let index = 1; index < cuts.length; index += 1) {
        const length = cuts[index] - cuts[index - 1];
        if (length <= 0) return "Mỗi cảnh cần có độ dài lớn hơn 0 và đúng thứ tự.";
    }
    return null;
}

export function getTimelinePublishError(project: SmartRemakeProject | null): string | null {
    if (project?.schemaVersion !== 2 || !project.draftTimeline)
        return "Chưa có bản nháp timeline để ghép.";
    if (project.pendingOperation)
        return "Yêu cầu trước đang được xử lý. Chờ hoàn tất rồi ghép nhé.";
    const timeline = project.draftTimeline;
    if (timeline.items.length < 1 || timeline.fps !== TIMELINE_FPS)
        return "Timeline chưa đủ các cảnh hợp lệ.";
    let cursor = 0;
    for (const item of timeline.items) {
        const scene = project.scenes.find((value) => value.id === item.renderUnitId);
        const version = scene?.versions.find((value) => value.id === item.versionId);
        if (!version || version.technicalCheck.status !== "passed")
            return "Chờ đủ clip đã kiểm tra trước khi ghép nhé.";
        if (!item.reviewed) return "Duyệt đoạn sẽ dùng của từng cảnh trước khi ghép nhé.";
        const rawFrames =
            version.frameCount ??
            version.technicalCheck.frameCount ??
            version.rawDurationFrames ??
            RAW_CLIP_FRAMES;
        if (
            !Number.isInteger(item.inFrame) ||
            !Number.isInteger(item.outFrame) ||
            item.inFrame < 0 ||
            item.outFrame > rawFrames ||
            item.outFrame - item.inFrame !== item.targetDurationFrames ||
            item.targetDurationFrames < 1 ||
            item.targetDurationFrames > RAW_CLIP_FRAMES ||
            item.targetStartFrame !== cursor
        )
            return "Đoạn cắt chưa hợp lệ. Kiểm tra lại độ dài và vị trí trong clip nhé.";
        cursor += item.targetDurationFrames;
    }
    if (cursor !== timeline.totalFrames || cursor !== project.targetDuration * TIMELINE_FPS)
        return "Timeline cần phủ đúng thời lượng video đã chọn.";
    return null;
}

export function restoreTimelineCompile(
    project: SmartRemakeProject,
): SmartRemakeCompileResult | null {
    if (project.schemaVersion !== 2 || !project.renderPlan) return null;
    const scenes = project.renderPlan.units.map((unit) => ({
        id: unit.id,
        displayOrder: unit.sceneIndex,
        prompt: unit.prompt,
        imagePrompt: unit.imagePrompt,
        videoPrompt: unit.videoPrompt,
        description: project.scenes.find((scene) => scene.id === unit.id)?.description,
    }));
    const sourceAudio = getRemakeSourceAudio(project.sourceAudio);
    return {
        success: true,
        schemaVersion: 2,
        projectId: project.id,
        revision: project.revision,
        expectationsVersion: project.expectationsVersion ?? undefined,
        expectationsHash: project.expectationsHash ?? undefined,
        sourceSceneMap: project.sourceSceneMap,
        renderPlan: project.renderPlan,
        draftTimeline: project.draftTimeline,
        mode: "smart_remake",
        renderSubmitted: false,
        inputSummary: {
            targetDuration: project.targetDuration,
            aspectRatio: "9:16",
            language: null,
        },
        referenceAnalysis: sourceAudio ? { sourceAudio } : {},
        analyzeOutput: {},
        productLock: {},
        sceneMap: { targetDuration: project.targetDuration, sceneCount: scenes.length, scenes },
        compiledPrompts:
            project.sourceSceneMap?.timingMode === "fit_target"
                ? project.sourceSceneMap.scenes.map((source, displayOrder) => ({
                      sourceSceneId: source.id,
                      displayOrder,
                      prompt: source.prompt ?? "",
                      imagePrompt: source.imagePrompt ?? "",
                      videoPrompt: source.videoPrompt ?? "",
                  }))
                : scenes,
        compilerDiagnostics: {},
        diagnostics: {},
        versions: {},
        warnings: [],
    };
}

export function settleTimelineOperationKeys(
    keys: Map<string, string>,
    project: SmartRemakeProject,
): Map<string, string> {
    if (project.pendingOperation || project.lastOperation?.kind !== "compose") return keys;
    return new Map(
        [...keys].filter(([signature]) => {
            const intent = JSON.parse(signature) as {
                kind?: string;
                projectId?: string;
                expectedRevision?: number;
            };
            return (
                intent.kind !== "publish" ||
                intent.projectId !== project.id ||
                typeof intent.expectedRevision !== "number" ||
                intent.expectedRevision > project.revision
            );
        }),
    );
}

export function getSourceCutFrames(
    map: SmartRemakeSourceSceneMap | undefined,
): number[] | undefined {
    return map
        ? [0, ...map.scenes.map((scene) => scene.endFrame - map.sourceStartFrame)]
        : undefined;
}
