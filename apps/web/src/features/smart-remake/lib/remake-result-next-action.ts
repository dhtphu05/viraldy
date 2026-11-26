import type {
    SmartRemakeAssembly,
    SmartRemakeProject,
    SmartRemakeTimeline,
} from "@/shared/api/smart-remake";
import type { RemakeRepairCandidate } from "./remake-action";
import { canReviewInspectionFinding, isInspectionReadyForApproval } from "./remake-inspection";
import { RAW_CLIP_FRAMES, getTimelinePublishError } from "./remake-timeline";
import { getRemakeSceneLabel } from "./remake-scene-label";

export type RemakeResultNextAction = {
    kind:
        | "progress"
        | "retry_render"
        | "update_plan"
        | "candidate"
        | "scene"
        | "compose"
        | "assembly_error"
        | "inspect"
        | "findings"
        | "approve"
        | "export"
        | "blocked";
    label: string;
    reason: string;
    sceneId?: string;
    versionId?: string;
    assemblyId?: string;
    reportId?: string;
    findingId?: string;
    view?: "watch" | "repair" | "compare";
    needsReconciliation?: boolean;
    recovery?: SmartRemakeProject["generationRecovery"];
};
export interface RemakeResultNextActionInput {
    project: SmartRemakeProject | null;
    needsPlanUpdate?: boolean;
    busy?: boolean;
    receiptUncertain?: boolean;
    candidate?: RemakeRepairCandidate | null;
    currentReportIds?: string[];
}
function sameTimeline(left?: SmartRemakeTimeline | null, right?: SmartRemakeTimeline | null) {
    if (!left || !right || left.fps !== right.fps || left.totalFrames !== right.totalFrames)
        return false;
    return (
        left.items.length === right.items.length &&
        left.items.every((item, index) => {
            const other = right.items[index];
            return (
                item.renderUnitId === other.renderUnitId &&
                item.versionId === other.versionId &&
                item.inFrame === other.inFrame &&
                item.outFrame === other.outFrame &&
                item.targetStartFrame === other.targetStartFrame &&
                item.targetDurationFrames === other.targetDurationFrames &&
                item.reviewed === other.reviewed
            );
        })
    );
}
function currentAssembly(project: SmartRemakeProject): SmartRemakeAssembly | undefined {
    const assembly = project.assemblies?.records.find(
        (item) => item.id === project.assemblies?.activeAssemblyId,
    );
    if (
        !assembly ||
        (project.constraintsHash && assembly.constraintsHash !== project.constraintsHash)
    )
        return undefined;
    if (project.schemaVersion === 2 && !sameTimeline(project.draftTimeline, assembly.timeline))
        return undefined;
    return assembly;
}
function sceneAction(
    project: SmartRemakeProject,
    scene: SmartRemakeProject["scenes"][number],
    reason: string,
    view: "watch" | "repair",
): RemakeResultNextAction {
    return {
        kind: "scene",
        label: `Xem ${getRemakeSceneLabel(project, scene.id, scene.index).toLowerCase()} cần xử lý`,
        reason,
        sceneId: scene.id,
        view,
    };
}

function timelineProblemScene(project: SmartRemakeProject) {
    let cursor = 0;
    for (const item of project.draftTimeline?.items ?? []) {
        const scene = project.scenes.find((value) => value.id === item.renderUnitId);
        const version = scene?.versions.find((value) => value.id === item.versionId);
        const frames =
            version?.frameCount ??
            version?.technicalCheck.frameCount ??
            version?.rawDurationFrames ??
            RAW_CLIP_FRAMES;
        if (
            scene &&
            (!Number.isInteger(item.inFrame) ||
                !Number.isInteger(item.outFrame) ||
                item.inFrame < 0 ||
                item.outFrame > frames ||
                item.outFrame - item.inFrame !== item.targetDurationFrames ||
                item.targetDurationFrames < 1 ||
                item.targetDurationFrames > RAW_CLIP_FRAMES ||
                item.targetStartFrame !== cursor)
        )
            return scene;
        cursor += item.targetDurationFrames;
    }
    return project.scenes[0];
}

export function getRemakeResultNextAction(
    input: RemakeResultNextActionInput,
): RemakeResultNextAction {
    const { project } = input;
    if (!project || (project.deletion && !["none", "cancelled"].includes(project.deletion.status)))
        return {
            kind: "blocked",
            label: "Dự án chưa sẵn sàng",
            reason: "Mở một dự án còn hiệu lực để tiếp tục.",
        };
    if (
        project.pendingOperation ||
        input.busy ||
        input.receiptUncertain ||
        project.lastOperation?.needsReconciliation
    ) {
        const needsReconciliation = Boolean(
            input.receiptUncertain ||
            project.pendingOperation?.needsReconciliation ||
            project.lastOperation?.needsReconciliation,
        );
        return {
            kind: "progress",
            label: needsReconciliation ? "Kiểm tra trạng thái" : "Xem tiến trình",
            reason: needsReconciliation
                ? "Đối soát yêu cầu đã gửi trước khi tạo lượt mới."
                : "Yêu cầu đã được lưu. Bạn có thể xem các clip đã hoàn tất.",
            needsReconciliation,
        };
    }
    if (input.needsPlanUpdate || !project.scenes.length)
        return {
            kind: "update_plan",
            label: "Cập nhật kịch bản",
            reason: "Duyệt kịch bản theo tư liệu và yêu cầu hiện tại trước khi tiếp tục.",
        };
    const candidateScene = project.scenes.find((scene) => scene.id === input.candidate?.sceneId);
    const candidate = candidateScene?.versions.find(
        (version) => version.id === input.candidate?.versionId && version.videoUrl,
    );
    if (
        input.candidate?.projectId === project.id &&
        candidateScene &&
        candidate &&
        candidate.id !== candidateScene.activeVersionId
    )
        return {
            kind: "candidate",
            label: `Xem bản mới ${getRemakeSceneLabel(project, candidateScene.id, candidateScene.index).toLowerCase()}`,
            reason: "So sánh trước khi áp dụng. Bản đang dùng vẫn được giữ.",
            sceneId: candidateScene.id,
            versionId: candidate.id,
            view: "compare",
        };
    if (project.generationRecovery?.kind === "retry_initial_render")
        return {
            kind: "retry_render",
            label: "Tiếp tục tạo video",
            reason:
                project.generationRecovery.errorCode === "OPENAI_IMAGE_CREDITS_EXHAUSTED"
                    ? project.generationRecovery.providerErrorCode === "credit_balance_exhausted"
                        ? "Dịch vụ tạo ảnh chưa đủ tín dụng. Bổ sung tín dụng cho dịch vụ này rồi tiếp tục từ kịch bản đã lưu."
                        : "Dịch vụ tạo ảnh đã chạm hạn mức chi tiêu hoặc tín dụng. Kiểm tra hạn mức của dịch vụ rồi tiếp tục từ kịch bản đã lưu."
                    : "Bước chuẩn bị ảnh tham chiếu chưa hoàn tất. Bạn có thể tiếp tục tạo video từ kịch bản đã lưu.",
            recovery: project.generationRecovery,
        };
    for (const scene of project.scenes) {
        const version = scene.versions.find((item) => item.id === scene.activeVersionId);
        if (!version?.videoUrl || version.technicalCheck.status !== "passed")
            return sceneAction(
                project,
                scene,
                "Cảnh chưa có clip dùng được. Kiểm tra lượt tạo video trước khi sửa hoặc ghép.",
                "watch",
            );
    }
    if (project.schemaVersion === 2) {
        for (const scene of project.scenes) {
            const item = project.draftTimeline?.items.find(
                (value) => value.renderUnitId === scene.id,
            );
            if (!item || !item.reviewed || item.versionId !== scene.activeVersionId)
                return sceneAction(
                    project,
                    scene,
                    "Xem clip và bấm Dùng đoạn này để xác nhận đoạn sẽ ghép.",
                    "watch",
                );
        }
        const timelineError = getTimelinePublishError(project);
        if (timelineError)
            return sceneAction(project, timelineProblemScene(project), timelineError, "watch");
    }
    const assembly = currentAssembly(project);
    if (!assembly)
        return {
            kind: "compose",
            label: "Ghép bản xem trước",
            reason: "Ghép từ các đoạn đã chọn; không tạo thêm clip AI.",
        };
    if (assembly.technicalCheck.status !== "passed")
        return {
            kind: "assembly_error",
            label: "Xem lỗi bản ghép",
            reason: "Bản ghép cần đạt kiểm tra kỹ thuật trước khi kiểm tra nội dung và duyệt.",
            assemblyId: assembly.id,
        };
    const currentIds = input.currentReportIds ?? project.inspectionSummary?.currentReportIds ?? [];
    const report = [...(project.inspectionSummary?.reports ?? [])]
        .reverse()
        .find(
            (item) =>
                currentIds.includes(item.id) &&
                !item.stale &&
                item.subject.kind === "assembly" &&
                item.subject.projectId === project.id &&
                item.subject.assemblyId === assembly.id &&
                item.subject.mediaHash === assembly.mediaHash &&
                item.manifestHash === assembly.manifestHash &&
                item.constraintsHash === assembly.constraintsHash &&
                (!assembly.expectationsHash || item.expectationsHash === assembly.expectationsHash),
        );
    if (!report)
        return {
            kind: "inspect",
            label: "Kiểm tra bản ghép",
            reason: "Kiểm tra đúng bản ghép hiện tại bằng AI trước khi duyệt nội dung.",
            assemblyId: assembly.id,
        };
    if (!isInspectionReadyForApproval(report, project.inspectionSummary?.reviews ?? [])) {
        const reviews = project.inspectionSummary?.reviews ?? [];
        const unresolved = report.findings.filter(
            (item) => !isInspectionReadyForApproval({ ...report, findings: [item] }, reviews),
        );
        const finding =
            unresolved.find(
                (item) => item.status !== "passed" && !canReviewInspectionFinding(item, "accept"),
            ) ?? unresolved[0];
        return {
            kind: "findings",
            label: "Xem vấn đề cần xử lý",
            reason: "Xem bằng chứng, sửa cảnh hoặc chấp nhận lỗi nội dung được phép kèm lý do.",
            assemblyId: assembly.id,
            reportId: report.id,
            ...(finding ? { findingId: finding.id } : {}),
        };
    }
    const approval = project.release?.approvals?.find(
        (item) =>
            item.id === project.release?.activeApprovalId &&
            item.status === "approved" &&
            item.assemblyId === assembly.id &&
            item.mediaHash === assembly.mediaHash &&
            item.manifestHash === assembly.manifestHash &&
            item.constraintsHash === assembly.constraintsHash &&
            item.reportId === report.id &&
            (!assembly.expectationsHash || item.expectationsHash === assembly.expectationsHash),
    );
    return {
        kind: approval ? "export" : "approve",
        label: approval ? "Tải video có nhãn AI" : "Duyệt nội dung bản này",
        reason: approval
            ? "Tải đúng bản ghép đã duyệt. Máy chủ kiểm tra lại quyền và bằng chứng khi xuất."
            : "Xác nhận bạn đã xem và đồng ý với nội dung của bản ghép hiện tại.",
        assemblyId: assembly.id,
        reportId: report.id,
    };
}
