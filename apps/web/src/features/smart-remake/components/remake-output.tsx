import { useEffect, useRef, useState } from "react";
import { ArrowLeft, Film, History, Loader2, RefreshCw, Sparkles } from "lucide-react";
import type {
    SmartRemakeProject,
    RepairIntent,
    SmartRemakeSceneVersion,
    SmartRemakeTimelineSelectionInput,
} from "@/shared/api/smart-remake";
import { cn } from "@/shared/lib/utils";
import { Button } from "@/shared/ui/button";
import { canUseRemakeVersion } from "../lib/remake-review";
import { getRemakeProjectError, type SmartRemakeRenderState } from "../lib/smart-remake-render";
import { RemakePlayer } from "./remake-player";
import { RemakeVersionReview } from "./remake-version-review";
import { RemakeRepairForm } from "./remake-repair-form";
import { RemakeTrimTools } from "./remake-trim-tools";
import { RemakeProcessingVisual } from "./remake-processing-visual";
import { RemakeImagePreview } from "./remake-image-preview";
import { RemakeClipThumbnail } from "./remake-clip-thumbnail";
import { RemakeEmptyOutput } from "./remake-empty-output";
import { getTimelinePublishError } from "../lib/remake-timeline";
import { getTimelinePreviewScope } from "../lib/remake-preview";
import { getRemakeSceneLabel } from "../lib/remake-scene-label";
import type { RemakeRepairCandidate } from "../lib/remake-action";
import "./remake-output.css";
export { RemakeVersionReview } from "./remake-version-review";

type View = "watch" | "repair" | "compare" | "history";
export type RemakeOutputNavigation = {
    requestId: string;
    sceneId: string;
    view: "watch" | "repair" | "compare";
    versionId?: string;
};
export interface RemakeOutputProps {
    workspaceId: string;
    project: SmartRemakeProject | null;
    result: SmartRemakeRenderState | null;
    productUrl?: string | null;
    busy: boolean;
    onRepair(sceneId: string, draft: RepairIntent): Promise<string | null>;
    onAccept(sceneId: string, versionId: string): Promise<boolean>;
    onRefresh(): void;
    onViewGenerationInspection?(reportId: string): void;
    onTimelineSave?(items: SmartRemakeTimelineSelectionInput[]): Promise<void>;
    onPublish?(): Promise<void>;
    savingTimeline?: boolean;
    publishing?: boolean;
    repairCandidate?: RemakeRepairCandidate | null;
    navigation?: RemakeOutputNavigation | null;
    guided?: boolean;
    generationRecoveryVisible?: boolean;
    initialSceneId?: string | null;
    onSceneChange?(sceneId: string | null): void;
    repairDrafts?: Record<string, RepairIntent>;
    onRepairDraftChange?(sceneId: string, baseVersionId: string | null, draft: RepairIntent): void;
    repairDraftSaveStatus?: string;
    repairFailures?: Record<string, string>;
    legacyRepairDraftAvailable?: boolean;
    onImportLegacyRepairDraft?(sceneId: string, baseVersionId: string | null): void;
}
const quietButton = "min-h-11 border-0 bg-surface-soft shadow-none hover:bg-surface-muted";
const primaryButton =
    "min-h-12 bg-[#e00b41] text-sm text-white hover:bg-[#c90a3a] focus-visible:ring-[#e00b41]/40";
const seconds = (value: number) => Number(value.toFixed(3));

export function RemakeOutput(props: RemakeOutputProps) {
    return <OutputSession key={props.project?.id ?? "pending"} {...props} />;
}
function OutputSession(props: RemakeOutputProps) {
    const { project, result, busy } = props;
    const timelineMode = project?.schemaVersion === 2;
    const [selectedSceneId, setSelectedSceneId] = useState<string | null>(
        props.initialSceneId && project?.scenes.some((scene) => scene.id === props.initialSceneId)
            ? props.initialSceneId
            : timelineMode
              ? (project.scenes[0]?.id ?? null)
              : null,
    );
    const [view, setView] = useState<View>("watch");
    const [candidateId, setCandidateId] = useState<string | null>(null);
    const sessionElement = useRef<HTMLElement>(null);
    const consumedNavigation = useRef<string | null>(null);
    useEffect(() => {
        const next = props.navigation;
        if (!next || !project || consumedNavigation.current === next.requestId) return;
        const target = project.scenes.find((item) => item.id === next.sceneId);
        if (!target) return;
        if (
            next.view === "compare" &&
            !target.versions.some((version) => version.id === next.versionId && version.videoUrl)
        )
            return;
        consumedNavigation.current = next.requestId;

        setSelectedSceneId(target.id);
        setCandidateId(next.view === "compare" ? (next.versionId ?? null) : null);
        const base = target.versions.find((version) => version.id === target.activeVersionId);
        setView(
            next.view === "repair" && (!base?.videoUrl || base.technicalCheck.status !== "passed")
                ? "watch"
                : next.view,
        );
        sessionElement.current?.focus({ preventScroll: true });
        sessionElement.current?.scrollIntoView?.({ block: "start", behavior: "smooth" });
    }, [project, props.navigation]);
    const [localBusy, setLocalBusy] = useState(false);
    const [message, setMessage] = useState<string | null>(null);
    const [trimPreview, setTrimPreview] = useState<
        | {
              sceneId: string;
              versionId: string;
              scope: { start: number; end: number } | null;
          }
        | undefined
    >();
    const [measuredFrames, setMeasuredFrames] = useState<Record<string, number>>({});
    const processing = busy || localBusy;
    const pending = processing || Boolean(project?.pendingOperation);
    const scene = project?.scenes.find((item) => item.id === selectedSceneId);
    const sceneLabel = scene ? getRemakeSceneLabel(project, scene.id, scene.index) : null;
    const logicalSceneCount = project?.sourceSceneMap?.scenes.length ?? project?.scenes.length ?? 0;
    const hasRenderFragments = Boolean(
        project?.renderPlan?.units.some((unit) => (unit.fragmentCount ?? 1) > 1),
    );
    const active = scene?.versions.find((version) => version.id === scene.activeVersionId);
    const usableBase = Boolean(active?.videoUrl && active.technicalCheck.status === "passed");
    useEffect(() => setTrimPreview(undefined), [scene?.id, active?.id]);
    const candidate = scene?.versions.find((version) => version.id === candidateId);
    const timelineItem = project?.draftTimeline?.items.find(
        (item) => item.renderUnitId === scene?.id,
    );
    const publishError = timelineMode ? getTimelinePublishError(project) : null;
    const productImage = project?.productImageUrl || props.productUrl;
    const finalUrl = project
        ? project.finalVideoUrl || null
        : result?.status === "completed"
          ? result.finalVideoUrl
          : null;
    const demo = Boolean(result?.isDemo);
    const fixtureOnly = !project && result?.provider === "fixture";
    const waitingForOutput = result?.status === "submitted" || result?.status === "running";
    const autoUpdating =
        project?.provider === "kie" &&
        Boolean(project.pendingOperation) &&
        !project.pendingOperation?.needsReconciliation;
    const operationError = getRemakeProjectError(project);
    const canRecover =
        !timelineMode &&
        project?.status === "incomplete" &&
        !finalUrl &&
        project.scenes.length > 0 &&
        project.scenes.every((item) =>
            item.versions.some(
                (version) =>
                    version.id === item.activeVersionId &&
                    version.videoUrl &&
                    version.technicalCheck.status === "passed",
            ),
        );
    async function recoverComposition() {
        const first = project?.scenes[0];
        if (!canRecover || !first?.activeVersionId || pending) return;
        setLocalBusy(true);
        setMessage(null);
        try {
            if (await props.onAccept(first.id, first.activeVersionId)) {
                setMessage("Đã ghép lại toàn video từ các cảnh đang dùng.");
            }
        } catch {
            setMessage("Chưa ghép lại được video. Các cảnh đang dùng vẫn được giữ. Hãy thử lại.");
        } finally {
            setLocalBusy(false);
        }
    }
    async function repair(draft: RepairIntent) {
        if (!scene || !usableBase || pending) return;
        setLocalBusy(true);
        setMessage(null);
        try {
            await props.onRepair(scene.id, draft);
        } catch {
            setMessage("Chưa tạo lại được cảnh. Bản đang dùng vẫn được giữ. Hãy thử lại.");
        } finally {
            setLocalBusy(false);
        }
    }
    async function accept(versionId: string) {
        if (!project || !scene || pending || !canUseRemakeVersion(project, scene.id, versionId))
            return;
        setLocalBusy(true);
        setMessage(null);
        try {
            if (await props.onAccept(scene.id, versionId)) {
                setSelectedSceneId(timelineMode ? scene.id : null);
                setCandidateId(null);
                setTrimPreview(undefined);
                setView("watch");
                setMessage(
                    timelineMode
                        ? "Đã chọn phiên bản này. Chọn và duyệt đoạn sẽ dùng trước khi ghép."
                        : "Đã áp dụng cảnh và cập nhật toàn video.",
                );
            }
        } catch {
            setMessage("Chưa áp dụng được bản này. Hãy tải lại dự án và thử lại.");
        } finally {
            setLocalBusy(false);
        }
    }
    async function publish() {
        if (!props.onPublish || publishError || pending) return;
        setMessage(null);
        try {
            await props.onPublish();
        } catch {
            setMessage(
                "Chưa ghép được video. Các đoạn đã chọn và video đã xuất vẫn được giữ; thử ghép lại nhé.",
            );
        }
    }
    if (
        project?.schemaVersion === 2 &&
        !finalUrl &&
        !project.scenes.some((item) => item.versions.some((version) => version.videoUrl))
    ) {
        const emptyError =
            props.generationRecoveryVisible &&
            project.generationRecovery?.errorCode &&
            project.lastOperation?.errorCode === project.generationRecovery?.errorCode
                ? null
                : operationError;
        if (props.guided && props.generationRecoveryVisible)
            return emptyError ? (
                <p role="alert" className="text-sm text-destructive">
                    {emptyError}
                </p>
            ) : null;
        return (
            <RemakeEmptyOutput
                project={project}
                guided={props.guided}
                busy={processing}
                recoveryPresented={props.generationRecoveryVisible}
                operationError={emptyError}
                onRefresh={props.onRefresh}
                onViewInspection={props.onViewGenerationInspection}
            />
        );
    }
    const projectInformation = project && props.guided && (
        <details className="remake-output-info">
            <summary className="min-h-11 cursor-pointer py-3 text-xs text-text-secondary focus-visible:ring-2 focus-visible:ring-ring">
                Thông tin video
            </summary>
            <div className="remake-output-info__body">
                <div className="remake-output-specs" aria-label="Thông tin video">
                    <span>{project.targetDuration} giây</span>
                    <span>{logicalSceneCount} cảnh nguồn</span>
                    <span>
                        {project.renderPlan?.units.length ?? project.scenes.length} đoạn dựng
                    </span>
                    <span>Preview riêng tư</span>
                </div>
                {hasRenderFragments && (
                    <p className="text-xs leading-relaxed text-text-secondary">
                        Một cảnh nguồn có thể được chia thành hai đoạn khi đi qua mốc 8 giây; số
                        cảnh nguồn không đổi.
                    </p>
                )}
                <Button
                    type="button"
                    variant="ghost"
                    className={quietButton}
                    disabled={processing}
                    onClick={props.onRefresh}
                >
                    <RefreshCw aria-hidden="true" />{" "}
                    {project.pendingOperation ? "Kiểm tra lại" : "Làm mới dự án"}
                </Button>
            </div>
        </details>
    );
    return (
        <section
            ref={sessionElement}
            tabIndex={-1}
            aria-label="Kết quả Smart Remake"
            aria-busy={pending}
            data-guided={Boolean(props.guided)}
            className="remake-output space-y-5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
            {props.guided && timelineMode && !demo && <h2 className="sr-only">Xem &amp; ghép</h2>}
            {(!props.guided || !timelineMode || demo) && (
                <header className="remake-output-header flex flex-wrap items-center justify-between gap-4">
                    <div>
                        <h2
                            className={
                                props.guided ? "sr-only" : "text-xl font-semibold text-text-primary"
                            }
                        >
                            {timelineMode ? "Xem & ghép" : "Video của bạn"}
                        </h2>
                        {(!props.guided || demo) && (
                            <p className="mt-1 text-sm text-text-secondary">
                                {demo
                                    ? "Video minh họa · chưa tạo từ sản phẩm của bạn"
                                    : timelineMode
                                      ? "Chọn đoạn sẽ dùng ở mỗi cảnh, ghép preview, rồi kiểm tra và duyệt để tải video."
                                      : "Xem toàn video, chọn cảnh cần sửa và duyệt bản mới."}
                            </p>
                        )}
                        {project && !props.guided && (
                            <div className="remake-output-specs" aria-label="Thông tin video">
                                <span>{project.targetDuration} giây</span>
                                <span>{logicalSceneCount} cảnh nguồn</span>
                                <span>Preview riêng tư</span>
                            </div>
                        )}
                        {props.guided && projectInformation}
                    </div>
                    {finalUrl && !demo && !props.guided && (
                        <p className="text-xs text-text-secondary">
                            Preview riêng tư · Duyệt nội dung và xuất bản có nhãn AI ở bên dưới.
                        </p>
                    )}
                    {project && !props.guided && (
                        <Button
                            type="button"
                            variant="ghost"
                            className={quietButton}
                            disabled={processing}
                            onClick={props.onRefresh}
                        >
                            <RefreshCw aria-hidden="true" />{" "}
                            {project.pendingOperation ? "Kiểm tra lại" : "Làm mới dự án"}
                        </Button>
                    )}
                </header>
            )}
            {timelineMode && (
                <div className="remake-output-selection flex flex-wrap items-center justify-between gap-4">
                    <div className="remake-output-selection__copy">
                        <div>
                            <p className="text-sm font-medium text-text-primary">
                                Đã chọn{" "}
                                {project.draftTimeline?.items.filter((item) => item.reviewed)
                                    .length ?? 0}
                                /{project.draftTimeline?.items.length ?? project.scenes.length} đoạn
                                · Video {project.targetDuration} giây
                            </p>
                            <p className="mt-1 text-xs text-text-secondary">
                                {publishError ??
                                    "Đủ các đoạn đã chọn. Sẵn sàng ghép preview để kiểm tra nội dung."}
                            </p>
                        </div>
                    </div>
                    {projectInformation}
                    {!props.guided && (
                        <Button
                            type="button"
                            className={primaryButton}
                            disabled={
                                pending ||
                                props.publishing ||
                                Boolean(publishError) ||
                                !props.onPublish
                            }
                            onClick={() => void publish()}
                        >
                            {props.publishing ? (
                                <Loader2
                                    className="size-4 motion-safe:animate-spin"
                                    aria-hidden="true"
                                />
                            ) : (
                                <Film className="size-4" aria-hidden="true" />
                            )}
                            {project.lastOperation?.kind === "compose" &&
                            project.lastOperation.status === "failed" &&
                            !publishError
                                ? "Thử ghép lại"
                                : `Ghép video · ${project.targetDuration} giây`}
                        </Button>
                    )}
                </div>
            )}
            {operationError && (
                <p
                    role="alert"
                    className="rounded-xl bg-destructive-soft p-4 text-sm text-destructive"
                >
                    {operationError}
                </p>
            )}
            {message && (
                <p
                    role="status"
                    className="rounded-xl bg-surface-soft p-4 text-sm text-text-secondary"
                >
                    {message}
                </p>
            )}
            {pending && (
                <p role="status" className="flex items-center gap-2 text-sm text-text-secondary">
                    {(processing || autoUpdating) && (
                        <Loader2 className="size-4 motion-safe:animate-spin" aria-hidden="true" />
                    )}
                    {project?.pendingOperation?.needsReconciliation
                        ? "Chưa xác định được kết quả của yêu cầu trước. Bấm Kiểm tra lại để cập nhật; nếu trạng thái không đổi, hãy nhờ hỗ trợ kiểm tra tác vụ trước khi tạo tiếp."
                        : autoUpdating
                          ? timelineMode
                              ? "Đang xử lý các cảnh hoặc ghép video. Kết quả sẽ tự cập nhật; bạn vẫn có thể xem clip đã hoàn tất."
                              : "Đang tạo video. Kết quả sẽ tự cập nhật; bạn không cần gửi lại yêu cầu."
                          : project?.pendingOperation
                            ? "Yêu cầu trước vẫn đang được xử lý. Bấm Kiểm tra lại để cập nhật kết quả."
                            : "Đang xử lý. Bạn có thể tiếp tục xem video."}
                </p>
            )}
            {!finalUrl && !project ? (
                <div className="rounded-3xl bg-surface p-8 text-center">
                    {waitingForOutput && !fixtureOnly ? (
                        <RemakeProcessingVisual compact />
                    ) : (
                        <Film
                            className="mx-auto mb-3 size-8 text-text-tertiary"
                            aria-hidden="true"
                        />
                    )}
                    <h3 className="font-medium text-text-primary">
                        {fixtureOnly
                            ? "Đã kiểm tra yêu cầu · Chưa tạo video"
                            : waitingForOutput
                              ? "Đang tạo video"
                              : "Chưa có video kết quả"}
                    </h3>
                    <p className="mt-2 text-sm text-text-secondary">
                        {fixtureOnly
                            ? "Chế độ kiểm tra không tạo video. Chuyển sang dịch vụ tạo video để có kết quả thật."
                            : waitingForOutput
                              ? "Yêu cầu đã được gửi. Video sẽ xuất hiện khi xử lý xong."
                              : "Tạo video từ kịch bản để bắt đầu xem và sửa từng cảnh."}
                    </p>
                </div>
            ) : (
                <div
                    className="remake-preview-tools remake-output-workspace"
                    data-view={scene ? "scene" : "whole"}
                >
                    <div className="remake-output-canvas min-w-0">
                        <div className="remake-output-canvas__heading flex flex-wrap items-center justify-between gap-2">
                            <div>
                                <h3 className="font-medium text-text-primary">
                                    {scene
                                        ? `${sceneLabel} · ${seconds(scene.startSecond)}–${seconds(scene.startSecond + scene.durationSeconds)} giây`
                                        : "Toàn video"}
                                </h3>
                            </div>
                            {scene && (!timelineMode || finalUrl) && (
                                <Button
                                    type="button"
                                    variant="ghost"
                                    className="min-h-11"
                                    disabled={pending && !timelineMode}
                                    onClick={() => {
                                        setSelectedSceneId(null);
                                        props.onSceneChange?.(null);
                                        setCandidateId(null);
                                        setView("watch");
                                    }}
                                >
                                    <ArrowLeft aria-hidden="true" />{" "}
                                    {timelineMode ? "Xem video đã xuất" : "Xem toàn video"}
                                </Button>
                            )}
                            {demo && (
                                <span className="rounded-full bg-surface-soft px-3 py-1 text-xs text-text-secondary">
                                    Video minh họa
                                </span>
                            )}
                        </div>
                        <div className="remake-output-stage">
                            {scene ? (
                                active ? (
                                    <RemakePlayer
                                        url={active.videoUrl}
                                        compareUrl={
                                            view === "compare" ? candidate?.videoUrl : undefined
                                        }
                                        compareScope={
                                            timelineMode && candidate
                                                ? getTimelinePreviewScope(
                                                      timelineItem,
                                                      candidate,
                                                      undefined,
                                                      timelineItem?.targetDurationFrames ??
                                                          scene.durationSeconds * 24,
                                                  )
                                                : undefined
                                        }
                                        scope={
                                            timelineMode
                                                ? getTimelinePreviewScope(
                                                      timelineItem,
                                                      active,
                                                      view !== "compare" &&
                                                          trimPreview?.sceneId === scene.id &&
                                                          trimPreview.versionId === active.id
                                                          ? trimPreview.scope
                                                          : undefined,
                                                      timelineItem?.targetDurationFrames ??
                                                          scene.durationSeconds * 24,
                                                  )
                                                : null
                                        }
                                        versionLabel={
                                            timelineMode
                                                ? `Clip AI · 8 giây · ${sceneLabel}`
                                                : "Cảnh đang dùng"
                                        }
                                        onMetadata={
                                            timelineMode
                                                ? (duration) =>
                                                      setMeasuredFrames((current) => ({
                                                          ...current,
                                                          [active.id]: Math.floor(
                                                              duration * 24 + 0.01,
                                                          ),
                                                      }))
                                                : undefined
                                        }
                                        compareLabel={
                                            candidate?.usedByRevision ? "Bản trước" : "Bản mới"
                                        }
                                    />
                                ) : view === "compare" && candidate?.videoUrl ? (
                                    <RemakePlayer
                                        url={candidate.videoUrl}
                                        scope={
                                            timelineMode
                                                ? getTimelinePreviewScope(
                                                      timelineItem,
                                                      candidate,
                                                      undefined,
                                                      timelineItem?.targetDurationFrames ??
                                                          scene.durationSeconds * 24,
                                                  )
                                                : null
                                        }
                                        versionLabel="Bản mới · chưa có bản đang dùng"
                                    />
                                ) : (
                                    <p className="rounded-xl bg-surface-soft p-5 text-sm text-text-secondary">
                                        Cảnh này chưa có video đang dùng.
                                    </p>
                                )
                            ) : finalUrl ? (
                                <RemakePlayer
                                    url={finalUrl}
                                    scope={null}
                                    versionLabel={
                                        timelineMode
                                            ? "Video đã xuất · Bản đã ghép"
                                            : "Toàn video đang dùng"
                                    }
                                />
                            ) : (
                                <div className="space-y-3 rounded-xl bg-surface-soft p-5 text-sm text-text-secondary">
                                    {autoUpdating && !canRecover && (
                                        <RemakeProcessingVisual compact />
                                    )}
                                    <p>
                                        {canRecover
                                            ? "Các cảnh đã sẵn sàng. Hãy ghép lại để có toàn video."
                                            : autoUpdating
                                              ? "Đang tạo video từ kịch bản đã duyệt. Các cảnh hoàn tất sẽ được giữ trong dự án này."
                                              : "Cần hoàn thiện cảnh trước khi có toàn video. Chọn cảnh bên dưới để xem và tạo lại."}
                                    </p>
                                    {canRecover && (
                                        <div className="space-y-2">
                                            <Button
                                                type="button"
                                                className={primaryButton}
                                                disabled={pending}
                                                onClick={() => void recoverComposition()}
                                            >
                                                <RefreshCw aria-hidden="true" /> Ghép lại video
                                            </Button>
                                            <p className="text-xs">
                                                Dùng các clip đã có. Không tạo lại cảnh bằng AI.
                                            </p>
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>
                        {timelineMode && project?.draftTimeline && (
                            <div className="remake-output-timeline space-y-3">
                                <div className="remake-output-timeline__heading">
                                    <h3 className="text-sm font-medium text-text-primary">
                                        Các cảnh sẽ ghép · {project.targetDuration} giây
                                    </h3>
                                    <span className="remake-output-timeline__legend">
                                        <i aria-hidden="true" /> Cảnh đang xem
                                    </span>
                                </div>
                                <div className="remake-filmstrip-scroll">
                                    <div
                                        className="remake-filmstrip"
                                        style={{
                                            minWidth: Math.max(
                                                280,
                                                project.draftTimeline.items.length * 100,
                                            ),
                                        }}
                                    >
                                        {project.draftTimeline.items.map((item, index) => {
                                            const unit = project.scenes.find(
                                                (value) => value.id === item.renderUnitId,
                                            );
                                            const timelineClip = unit?.versions.find(
                                                (value) => value.id === unit.activeVersionId,
                                            );
                                            const hasClip = Boolean(timelineClip);
                                            return (
                                                <button
                                                    key={item.id}
                                                    type="button"
                                                    aria-pressed={scene?.id === item.renderUnitId}
                                                    title={`${getRemakeSceneLabel(project, item.renderUnitId, index)} · ${Number((item.targetDurationFrames / 24).toFixed(3))} giây · ${item.reviewed ? "Đã chọn" : hasClip ? "Chưa chọn" : "Chờ clip"}`}
                                                    className={cn(
                                                        "remake-filmstrip-scene",
                                                        scene?.id === item.renderUnitId &&
                                                            "is-selected",
                                                    )}
                                                    style={{
                                                        flexBasis: `${(item.targetDurationFrames / project.draftTimeline!.totalFrames) * 100}%`,
                                                    }}
                                                    onClick={() => {
                                                        setSelectedSceneId(item.renderUnitId);
                                                        props.onSceneChange?.(item.renderUnitId);
                                                        setCandidateId(null);
                                                        setView("watch");
                                                        setTrimPreview(undefined);
                                                    }}
                                                >
                                                    <span
                                                        className="remake-scene-grain"
                                                        aria-hidden="true"
                                                    >
                                                        {timelineClip?.videoUrl ? (
                                                            <RemakeClipThumbnail
                                                                key={timelineClip.videoUrl}
                                                                src={timelineClip.videoUrl}
                                                            />
                                                        ) : (
                                                            <Film className="size-5 opacity-40" />
                                                        )}
                                                    </span>
                                                    <strong>
                                                        {getRemakeSceneLabel(
                                                            project,
                                                            item.renderUnitId,
                                                            index,
                                                        )}
                                                    </strong>
                                                    <span>
                                                        {Number(
                                                            (
                                                                item.targetDurationFrames / 24
                                                            ).toFixed(3),
                                                        )}{" "}
                                                        giây ·{" "}
                                                        {item.reviewed
                                                            ? "Đã chọn"
                                                            : hasClip
                                                              ? "Chưa chọn"
                                                              : "Chờ clip"}
                                                    </span>
                                                </button>
                                            );
                                        })}
                                    </div>
                                    <div className="mt-2 flex justify-between text-xs text-text-tertiary">
                                        <span>0 giây</span>
                                        <span>{project.targetDuration} giây</span>
                                    </div>
                                </div>
                                <p className="text-xs text-text-secondary">
                                    Bấm một cảnh để xem và chọn đoạn dùng. Tua video bằng thanh
                                    trong trình phát.
                                </p>
                            </div>
                        )}
                        {project && !demo && !timelineMode && (
                            <div className="remake-output-timeline space-y-3">
                                <p className="text-sm font-medium text-text-primary">
                                    Chọn cảnh để xem hoặc sửa
                                </p>
                                <div
                                    className="flex gap-3 overflow-x-auto pb-2"
                                    aria-label="Danh sách cảnh"
                                >
                                    {project.scenes.map((item) => {
                                        const clip = item.versions.find(
                                            (version) => version.id === item.activeVersionId,
                                        );
                                        const unseen = item.versions.filter(
                                            (version) =>
                                                version.id !== item.activeVersionId &&
                                                !version.usedByRevision,
                                        );
                                        return (
                                            <button
                                                type="button"
                                                key={item.id}
                                                aria-pressed={item.id === scene?.id}
                                                disabled={pending}
                                                className={cn(
                                                    "w-36 shrink-0 rounded-2xl bg-surface-soft p-2 text-left transition-colors hover:bg-surface-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-60",
                                                    item.id === scene?.id &&
                                                        "bg-primary-soft ring-2 ring-primary/40",
                                                )}
                                                onClick={() => {
                                                    setSelectedSceneId(item.id);
                                                    props.onSceneChange?.(item.id);
                                                    setCandidateId(null);
                                                    setView("watch");
                                                    setMessage(null);
                                                }}
                                            >
                                                <div className="flex h-24 items-center justify-center overflow-hidden rounded-xl bg-black/90">
                                                    {clip?.videoUrl ? (
                                                        <RemakeClipThumbnail
                                                            key={clip.videoUrl}
                                                            src={clip.videoUrl}
                                                            label={`Hình xem trước ${getRemakeSceneLabel(project, item.id, item.index).toLowerCase()}`}
                                                        />
                                                    ) : (
                                                        <Film
                                                            className="size-6 text-white/60"
                                                            aria-hidden="true"
                                                        />
                                                    )}
                                                </div>
                                                <span className="mt-2 block text-sm font-medium text-text-primary">
                                                    {getRemakeSceneLabel(
                                                        project,
                                                        item.id,
                                                        item.index,
                                                    )}
                                                </span>
                                                {unseen.length > 0 && (
                                                    <span className="mt-1 block text-xs font-medium text-primary">
                                                        {unseen.length} bản mới chờ xem
                                                    </span>
                                                )}
                                                <span className="block text-xs text-text-secondary">
                                                    {seconds(item.startSecond)}–
                                                    {seconds(
                                                        item.startSecond + item.durationSeconds,
                                                    )}{" "}
                                                    giây
                                                </span>
                                            </button>
                                        );
                                    })}
                                </div>
                            </div>
                        )}
                    </div>
                    <aside
                        className="remake-output-dock min-w-0"
                        aria-label="Hoàn thiện cảnh đang xem"
                    >
                        {timelineMode && timelineItem && active && props.onTimelineSave && (
                            <RemakeTrimTools
                                key={`${timelineItem.id}:${active.id}:${timelineItem.inFrame}:${timelineItem.reviewed}`}
                                item={timelineItem}
                                versionId={active.id}
                                sharedClip={Boolean(
                                    active.renderGroupId &&
                                    project?.renderPlan?.groups?.some(
                                        (group) =>
                                            group.id === active.renderGroupId &&
                                            group.renderUnitIds.length > 1,
                                    ),
                                )}
                                rawFrameCount={
                                    active.frameCount ??
                                    active.technicalCheck.frameCount ??
                                    measuredFrames[active.id] ??
                                    null
                                }
                                busy={pending || Boolean(props.savingTimeline)}
                                onSave={props.onTimelineSave}
                                onPreview={(scope) =>
                                    setTrimPreview({
                                        sceneId: scene!.id,
                                        versionId: active.id,
                                        scope,
                                    })
                                }
                            />
                        )}
                        <div className="remake-output-side-panels">
                            {productImage && (
                                <div className="remake-output-reference flex items-center gap-4">
                                    <div className="remake-output-reference__image">
                                        <RemakeImagePreview
                                            src={productImage}
                                            alt="Ảnh sản phẩm dùng khi tạo video"
                                            enlarge
                                        />
                                    </div>
                                    <div>
                                        <h3 className="text-sm font-medium text-text-primary">
                                            Sản phẩm tham chiếu
                                        </h3>
                                        <p className="mt-1 text-xs text-text-secondary">
                                            Đối chiếu hình dáng, màu sắc và bao bì khi duyệt cảnh.
                                        </p>
                                    </div>
                                </div>
                            )}
                            {scene && project && !demo && usableBase ? (
                                <div className="remake-output-scene-tools space-y-5">
                                    <div
                                        className="remake-output-scene-tabs grid min-w-0 auto-rows-fr grid-cols-2 gap-2"
                                        role="group"
                                        aria-label="Công cụ cảnh"
                                    >
                                        {(
                                            [
                                                ["watch", "Xem"],
                                                ["repair", "Sửa cảnh"],
                                                ["compare", "So sánh"],
                                                ["history", "Lịch sử"],
                                            ] as const
                                        ).map(([value, label]) => (
                                            <Button
                                                key={value}
                                                type="button"
                                                variant="ghost"
                                                className={cn(
                                                    "min-h-11 px-3",
                                                    view === value &&
                                                        "bg-primary-soft text-primary",
                                                )}
                                                aria-pressed={view === value}
                                                disabled={value === "repair" && !usableBase}
                                                onClick={() => setView(value)}
                                            >
                                                {label}
                                            </Button>
                                        ))}
                                    </div>
                                    {view === "watch" && !props.guided && (
                                        <div className="space-y-4">
                                            <div>
                                                <h3 className="font-medium text-text-primary">
                                                    Cảnh này đã đạt chưa?
                                                </h3>
                                                <p className="mt-2 text-sm leading-relaxed text-text-secondary">
                                                    Kiểm tra sản phẩm, chuyển động và nội dung. Nếu
                                                    chưa đạt, chọn vấn đề cần sửa để AI tạo một bản
                                                    mới cho riêng cảnh này.
                                                </p>
                                            </div>
                                            <Button
                                                type="button"
                                                variant={props.guided ? "outline" : "default"}
                                                className={cn(
                                                    props.guided ? quietButton : primaryButton,
                                                    "w-full",
                                                )}
                                                disabled={pending}
                                                onClick={() => setView("repair")}
                                            >
                                                <Sparkles aria-hidden="true" /> Sửa và tạo lại cảnh
                                            </Button>
                                            <p className="text-xs leading-relaxed text-text-secondary">
                                                Cảnh khác giữ nguyên. Bản mới chỉ thay thế sau khi
                                                bạn bấm áp dụng.
                                            </p>
                                        </div>
                                    )}
                                    {view === "repair" && usableBase && (
                                        <RemakeRepairForm
                                            key={`${props.workspaceId}:${project.id}:${scene.id}:${scene.activeVersionId ?? "initial"}`}
                                            workspaceId={props.workspaceId}
                                            projectId={project.id}
                                            scene={scene}
                                            sceneLabel={sceneLabel ?? undefined}
                                            active={active}
                                            busy={pending}
                                            onRepair={repair}
                                            draft={
                                                props.repairDrafts?.[
                                                    `${scene.id}:${scene.activeVersionId ?? "initial"}`
                                                ]
                                            }
                                            onDraftChange={(draft) =>
                                                props.onRepairDraftChange?.(
                                                    scene.id,
                                                    scene.activeVersionId,
                                                    draft,
                                                )
                                            }
                                            saveStatus={props.repairDraftSaveStatus}
                                            failureReason={props.repairFailures?.[scene.id]}
                                            legacyDraftAvailable={props.legacyRepairDraftAvailable}
                                            onImportLegacyDraft={
                                                props.onImportLegacyRepairDraft
                                                    ? () =>
                                                          props.onImportLegacyRepairDraft?.(
                                                              scene.id,
                                                              scene.activeVersionId,
                                                          )
                                                    : undefined
                                            }
                                        />
                                    )}
                                    {view === "compare" &&
                                        (candidate ? (
                                            <RemakeVersionReview
                                                project={project}
                                                sceneId={scene.id}
                                                version={candidate}
                                                busy={pending}
                                                onAccept={accept}
                                            />
                                        ) : (
                                            <div className="space-y-3">
                                                <p className="text-sm text-text-secondary">
                                                    Chọn một phiên bản trong lịch sử hoặc tạo lại
                                                    cảnh để so sánh.
                                                </p>
                                                <Button
                                                    type="button"
                                                    variant="ghost"
                                                    className={quietButton}
                                                    onClick={() => setView("history")}
                                                >
                                                    <History aria-hidden="true" /> Mở lịch sử
                                                </Button>
                                            </div>
                                        ))}
                                    {view === "history" && (
                                        <div className="space-y-3">
                                            <h3 className="font-medium text-text-primary">
                                                Phiên bản {sceneLabel?.toLowerCase()}
                                            </h3>
                                            {[...scene.versions].reverse().map((version, index) => (
                                                <div
                                                    key={version.id}
                                                    className="rounded-2xl bg-surface-soft p-4"
                                                >
                                                    <div className="flex flex-wrap items-center justify-between gap-2">
                                                        <span className="text-sm font-medium text-text-primary">
                                                            Phiên bản{" "}
                                                            {scene.versions.length - index}
                                                        </span>
                                                        <span className="text-xs text-text-secondary">
                                                            {version.id === scene.activeVersionId
                                                                ? "Đang dùng"
                                                                : version.usedByRevision
                                                                  ? "Đã dùng trước đây"
                                                                  : "Chưa áp dụng"}
                                                        </span>
                                                    </div>
                                                    <p className="mt-2 line-clamp-2 text-xs text-text-secondary">
                                                        {version.videoPrompt || version.prompt}
                                                    </p>
                                                    {version.id !== scene.activeVersionId && (
                                                        <Button
                                                            type="button"
                                                            variant="ghost"
                                                            className="mt-2 min-h-11 w-full"
                                                            disabled={pending}
                                                            onClick={() => {
                                                                setCandidateId(version.id);
                                                                setView("compare");
                                                            }}
                                                        >
                                                            So sánh
                                                            {version.usedByRevision
                                                                ? " và khôi phục"
                                                                : " bản này"}
                                                        </Button>
                                                    )}
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            ) : (
                                !demo && (
                                    <div className="rounded-3xl bg-surface p-5 text-sm leading-relaxed text-text-secondary">
                                        {scene && !usableBase
                                            ? "Cảnh này chưa có clip dùng được để sửa. Hoàn tất lượt tạo video trước."
                                            : project
                                              ? "Chọn một cảnh bên dưới video để xem yêu cầu, tạo bản mới hoặc mở lịch sử."
                                              : "Video này chưa có dữ liệu cảnh để sửa riêng. Bạn vẫn có thể xem và tải toàn video."}
                                    </div>
                                )
                            )}
                        </div>
                    </aside>
                </div>
            )}
        </section>
    );
}
