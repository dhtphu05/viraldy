import type { SmartRemakeGenerationStage, SmartRemakeProject } from "@/shared/api/smart-remake";

export const generationStageLabels: Record<SmartRemakeGenerationStage, string> = {
    queued: "Chưa bắt đầu",
    preparing_image: "Đang tạo ảnh mở đầu",
    checking_image: "Đang kiểm tra ảnh tham chiếu",
    submitting_video: "Đang gửi yêu cầu tạo video",
    generating: "KIE đang tạo clip",
    checking: "Đang kiểm tra clip",
    completed: "Đã tạo xong clip",
    blocked: "Chưa thể tạo tiếp",
    unknown: "Cần kiểm tra trạng thái",
};

export function getRemakeGenerationProgress(project: SmartRemakeProject | null) {
    const plan = project?.renderPlan;
    if (!project || !plan?.groups?.length) return null;
    const progress = project.generationProgress;
    let offset = 0;
    const groups = plan.groups.map((group, index) => {
        const sourceSceneIndexes = [
            ...new Set(
                group.renderUnitIds.flatMap((id) => {
                    const unit = plan.units.find((value) => value.id === id);
                    const sourceIndex = project.sourceSceneMap?.scenes.findIndex(
                        (scene) => scene.id === unit?.sourceSceneId,
                    );
                    return sourceIndex != null && sourceIndex >= 0 ? [sourceIndex + 1] : [];
                }),
            ),
        ];
        const state = progress?.groups.find((value) => value.groupId === group.id);
        const startSecond = offset / plan.fps;
        offset += group.targetDurationFrames;
        return {
            id: group.id,
            index: index + 1,
            startSecond,
            endSecond: offset / plan.fps,
            sourceSceneIndexes,
            sourceThumbnailUrl:
                project.sourceSceneMap?.scenes[(sourceSceneIndexes[0] ?? 0) - 1]?.thumbnailUrl,
            stage: state?.stage ?? ("unknown" as SmartRemakeGenerationStage),
            videoSubmitted: state?.videoSubmitted ?? null,
            conditioningImageUrl: state?.conditioningImageUrl,
            kieRequest: state?.videoSubmitted === true ? state.kieRequest : undefined,
            conditioningImages: (state?.conditioningImages ?? [])
                .filter((image) => group.renderUnitIds.includes(image.renderUnitId))
                .map((image) => {
                    const unit = plan.units.find((value) => value.id === image.renderUnitId);
                    const sourceIndex = project.sourceSceneMap?.scenes.findIndex(
                        (scene) => scene.id === unit?.sourceSceneId,
                    );
                    return {
                        ...image,
                        sourceSceneIndex:
                            sourceIndex != null && sourceIndex >= 0 ? sourceIndex + 1 : undefined,
                    };
                }),
            videoUrl: state?.videoUrl,
            errorCode: state?.errorCode,
            providerError: state?.providerError,
            providerTaskId: state?.providerTaskId,
            inspectionReportId: state?.inspectionReportId,
        };
    });
    const dates = progress && [Date.parse(progress.startedAt), Date.parse(progress.updatedAt)];
    const elapsedSeconds = dates?.every(Number.isFinite)
        ? Math.min(86400, Math.max(0, Math.floor((dates[1] - dates[0]) / 1000)))
        : null;
    return {
        plannedCount: groups.length,
        submittedCount: groups.every((group) => group.videoSubmitted !== null)
            ? groups.filter((group) => group.videoSubmitted === true).length
            : null,
        completedCount: groups.filter((group) => group.stage === "completed").length,
        active:
            progress?.status === "running" &&
            groups.some((group) =>
                [
                    "preparing_image",
                    "checking_image",
                    "submitting_video",
                    "generating",
                    "checking",
                ].includes(group.stage),
            ),
        status: progress?.status,
        elapsedSeconds,
        groups,
    };
}
