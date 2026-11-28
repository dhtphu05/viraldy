import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
    acceptSmartRemakeVersion,
    compileSmartRemake,
    getSmartRemakeHealth,
    getSmartRemakeProject,
    repairSmartRemakeScene,
    saveSmartRemakeTimeline,
    publishSmartRemakeTimeline,
    type SmartRemakeTimelineSelectionInput,
    type SmartRemakeCompileResult,
    type SmartRemakeProject,
    type SmartRemakePromptDraft,
    type SmartRemakeOperationResult,
    type SmartRemakePreflightAction,
    type RepairIntent,
} from "@/shared/api/smart-remake";
import { crawlProductPreview } from "@/shared/api/products";
import { ApiError } from "@/shared/api/errors";
import { consumeSmartRemakeHandoff } from "./smart-remake-handoff";
import {
    getRemakeProjectPollInterval,
    getRemakeErrorMessage,
    getRemakeProjectError,
    getRemakeGenerationSetupError,
    getRemakeProviderGroupingError,
    prepareRemakeRenderRetry,
    hasRemakeRepairClip,
    renderSmartRemakeVideo,
    type SmartRemakeRenderAttempt,
    type SmartRemakeRenderState,
} from "./smart-remake-render";
import { updateRemakeScene, type RemakeScenePatch } from "./remake-studio";
import {
    getRemakeAnalysisRecovery,
    getRemakeAnalysisRetryBinding,
} from "./remake-analysis-recovery";
import { getRenderGroupBreaks } from "./remake-groups";
import { latestRemakeProject } from "./remake-review";
import {
    getRemakeResumeStep,
    getRemakeIntakeError,
    getRemakeRightsError,
    hasCurrentRemakeRightsAttestation,
    normalizeRemakeRequirements,
    DEFAULT_REMAKE_INTENT,
    emptyRemakeRights,
} from "./remake-intake";
import { useRemakePolicy, type RemakeBusyStep } from "./use-remake-policy";
import { useRemakeAction } from "./use-remake-action";
import { useRemakeRepairTracking } from "./use-remake-repair-tracking";
import { readAnalysisProject, useRemakeAnalysisProgress } from "./use-remake-analysis-progress";
import type {
    RemakeActionArgs,
    RemakeActionIntent,
    RemakeActionSnapshot,
    RemakeRepairCandidate,
} from "./remake-action";
import {
    getSourceCutFrames,
    getTimelinePublishError,
    restoreTimelineCompile,
    settleTimelineOperationKeys,
    validateSourceCuts,
} from "./remake-timeline";

export type RemakeStep = "prepare" | "plan" | "result";
type BusyStep = RemakeBusyStep;
type LinkedProduct = {
    sourceUrl: string;
    title: string;
    description: string | null;
    imageUrls: string[];
};

export function useRemakeStudio(
    workspaceId: string,
    accountId?: string,
    requestedProjectId?: string,
    startNewProject = false,
) {
    const [step, setStep] = useState<RemakeStep>("prepare");
    const [duration, setDuration] = useState<8 | 16>(16);
    const [timelineStartFrame, setTimelineStartFrame] = useState(0);
    const [sourceDuration, setSourceDuration] = useState<number | null>(null);
    const [sourceCutFrames, setSourceCutFrames] = useState<number[] | undefined>();
    const [renderGroupBreaks, setRenderGroupBreaks] = useState<number[]>([]);
    const [language, setLanguage] = useState("Tiếng Việt");
    const [brief, setBrief] = useState("");
    const [description, setDescription] = useState("");
    const [video, setVideo] = useState<File | null>(null);
    const [images, setImages] = useState<File[]>([]);
    const [primaryIndex, setPrimaryIndex] = useState(0);
    const [link, setLink] = useState("");
    const [linkedProduct, setLinkedProduct] = useState<LinkedProduct | null>(null);
    const [isSample, setIsSample] = useState(false);
    const [localPlanNeedsUpdate, setLocalPlanNeedsUpdate] = useState(false);
    const [compiled, setCompiled] = useState<SmartRemakeCompileResult | null>(null);
    const [sceneDrafts, setSceneDrafts] = useState<Record<number, RemakeScenePatch>>({});
    const [result, setResult] = useState<SmartRemakeRenderState | null>(null);
    const [lastActionRepairCandidate, setLastActionRepairCandidate] =
        useState<RemakeRepairCandidate | null>(null);
    const [repairDrafts, setRepairDrafts] = useState<Record<string, RepairIntent>>({});
    const [selectedSceneId, setSelectedSceneId] = useState<string | null>(null);
    const [outputNavigation, setOutputNavigation] = useState<{
        requestId: string;
        sceneId: string;
        view: "watch" | "repair" | "compare";
        versionId?: string;
    } | null>(null);
    const draftScope = useMemo(
        () => (accountId ? { accountId, workspaceId, draftId: "current" } : null),
        [accountId, workspaceId],
    );
    const [project, setProject] = useState<SmartRemakeProject | null>(null);
    const projectView = useRef<SmartRemakeProject | null>(null);
    projectView.current = project;
    const [busy, setBusy] = useState<BusyStep | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [notice, setNotice] = useState("Thêm video mẫu và ảnh sản phẩm để bắt đầu.");
    const [submissionStatusError, setSubmissionStatusError] = useState<string | null>(null);
    const [checkingSubmissionStatus, setCheckingSubmissionStatus] = useState(false);
    const submittedProject = useRef<string | null>(null);
    const submittedAnalysisKey = useRef<string | null>(null);
    const receiptStorageKey = accountId
        ? `remake-project:${accountId}:${workspaceId}`
        : `remake-project:${workspaceId}`;
    const lock = useRef(false);
    const lastOperationError = useRef<string | null>(null);
    const lastOperationErrorCode = useRef<string | null>(null);
    const operationKeys = useRef(new Map<string, string>());
    const renderAttempt = useRef<SmartRemakeRenderAttempt | null>(null);
    const repairAccepted = useRef(false);
    const compiledRequirements = useRef<string | null>(null);
    const initialized = useRef<boolean | string>(false);
    const projectOpening = useRef({ serial: 0, active: false });
    const rememberProject = useCallback(
        (next: SmartRemakeProject) => {
            setProject((current) => latestRemakeProject(current, next));
            try {
                if (submittedProject.current !== next.id) submittedAnalysisKey.current = null;
                const failure = getRemakeAnalysisRecovery(next);
                if (
                    next.pendingOperation ||
                    (failure && failure.retryDisposition !== "new_analysis") ||
                    (submittedProject.current === next.id &&
                        submittedAnalysisKey.current &&
                        next.analysisProgress?.requestKey !== submittedAnalysisKey.current)
                ) {
                    submittedProject.current = next.id;
                    localStorage.setItem(
                        receiptStorageKey,
                        submittedAnalysisKey.current
                            ? JSON.stringify({
                                  projectId: next.id,
                                  requestKey: submittedAnalysisKey.current,
                              })
                            : next.id,
                    );
                } else {
                    submittedProject.current = null;
                    submittedAnalysisKey.current = null;
                    localStorage.removeItem(receiptStorageKey);
                }
            } catch {
                /* A blocked storage area must not discard a successful render. */
            }
        },
        [receiptStorageKey],
    );
    const analysisTracker = useRemakeAnalysisProgress(workspaceId);
    const analysisView = useRef(analysisTracker);
    analysisView.current = analysisTracker;
    const {
        restore: restoreAnalysis,
        recoveredProject: recoveredAnalysisProject,
        failedProject: failedAnalysisProject,
        supersedingProject: supersedingAnalysisProject,
        token: analysisToken,
        complete: completeAnalysis,
    } = analysisTracker;
    const policy = useRemakePolicy({
        workspaceId,
        project,
        run,
        rememberProject,
        operationKey,
        performOperation,
        validFile,
        setNotice,
        isLocked: () => lock.current,
    });
    const { characterFile, loadContext } = policy;
    const openProject = useCallback(
        async (projectId: string, isCurrent: () => boolean = () => true) => {
            if (projectView.current?.id === projectId) return true;
            const previousAnalysis = analysisView.current;
            if (previousAnalysis.token !== undefined)
                previousAnalysis.complete(previousAnalysis.token);
            const serial = projectOpening.current.serial + 1;
            projectOpening.current = { serial, active: true };
            lock.current = true;
            setBusy("restore");
            setError(null);
            setProject(null);
            setVideo(null);
            setImages([]);
            setLinkedProduct(null);
            setCompiled(null);
            setResult(null);
            setSceneDrafts({});
            setRepairDrafts({});
            try {
                const saved = await getSmartRemakeProject(workspaceId, projectId);
                if (!isCurrent()) return false;
                rememberProject(saved);
                loadContext(saved);
                setDuration(saved.targetDuration);
                setSourceDuration(
                    saved.sourceSceneMap ? saved.sourceSceneMap.sourceFrameCount / 24 : null,
                );
                const restored = restoreTimelineCompile(saved);
                setCompiled(restored);
                setLocalPlanNeedsUpdate(false);
                compiledRequirements.current = saved.requirements
                    ? JSON.stringify(normalizeRemakeRequirements(saved.requirements))
                    : null;
                setSourceCutFrames(getSourceCutFrames(saved.sourceSceneMap));
                setRenderGroupBreaks(getRenderGroupBreaks(saved.renderPlan));
                const hasGeneration =
                    saved.generationProgress ||
                    saved.scenes.some((scene) => scene.versions.length) ||
                    ["render", "repair", "compose", "inspection"].includes(
                        saved.pendingOperation?.kind ?? saved.lastOperation?.kind ?? "",
                    );
                setStep(hasGeneration ? "result" : getRemakeResumeStep(saved));
                setNotice("Đã mở dự án từ máy chủ. Tiến độ và kết quả sẽ được cập nhật tại đây.");
                return true;
            } catch (cause) {
                if (isCurrent()) setError(getRemakeErrorMessage(cause));
                return false;
            } finally {
                if (projectOpening.current.serial === serial) {
                    projectOpening.current = { serial, active: false };
                    lock.current = false;
                    if (isCurrent()) setBusy(null);
                }
            }
        },
        [workspaceId, rememberProject, loadContext],
    );
    const checkSubmissionStatus = useCallback(
        async (projectId = submittedProject.current, isCurrent: () => boolean = () => true) => {
            if (!projectId) return;
            setCheckingSubmissionStatus(true);
            try {
                const saved = await getSmartRemakeProject(workspaceId, projectId);
                if (!isCurrent()) return;
                const failure = getRemakeAnalysisRecovery(saved);
                if (
                    saved.pendingOperation ||
                    (failure && failure.retryDisposition !== "new_analysis")
                ) {
                    rememberProject(saved);
                    loadContext(saved);
                    setDuration(saved.targetDuration);
                    setStep(getRemakeResumeStep(saved));
                    setNotice("Đang theo dõi yêu cầu đã gửi. Chưa gửi lượt AI mới.");
                } else if (
                    submittedAnalysisKey.current &&
                    saved.analysisProgress?.requestKey !== submittedAnalysisKey.current
                ) {
                    setSubmissionStatusError(
                        "Yêu cầu đã gửi chưa có kết quả xác nhận. Kiểm tra trạng thái trước khi gọi AI tiếp.",
                    );
                    return;
                } else {
                    submittedProject.current = null;
                    submittedAnalysisKey.current = null;
                    try {
                        localStorage.removeItem(receiptStorageKey);
                    } catch {
                        /* Server already confirmed that this request is terminal. */
                    }
                }
                setSubmissionStatusError(null);
            } catch (cause) {
                if (!isCurrent()) return;
                if (cause instanceof ApiError && [403, 404].includes(cause.status)) {
                    submittedProject.current = null;
                    submittedAnalysisKey.current = null;
                    try {
                        localStorage.removeItem(receiptStorageKey);
                    } catch {
                        /* A stale inaccessible receipt must not block new inputs. */
                    }
                    setSubmissionStatusError(null);
                } else
                    setSubmissionStatusError(
                        "Chưa kiểm tra được yêu cầu đã gửi. Kiểm tra trạng thái trước khi gọi AI tiếp.",
                    );
            } finally {
                if (isCurrent()) setCheckingSubmissionStatus(false);
            }
        },
        [workspaceId, loadContext, rememberProject, receiptStorageKey],
    );
    const repairTracking = useRemakeRepairTracking({
        scope: startNewProject && !project ? null : draftScope,
        project,
        onProject: (next) => {
            if (
                requestedProjectId &&
                next.id !== requestedProjectId &&
                projectView.current?.id !== next.id
            )
                return;
            rememberProject(next);
        },
    });
    const intakeError =
        policy.intakeError ??
        (!video && project && (images.length || linkedProduct || characterFile)
            ? "Thêm lại video mẫu để lưu bộ tư liệu mới trước khi phân tích. Tư liệu cũ vẫn được giữ."
            : null);
    const health = useQuery({
        queryKey: ["smart-remake", "health", workspaceId],
        queryFn: () => getSmartRemakeHealth(workspaceId),
        staleTime: 60_000,
        retry: 1,
    });
    useEffect(() => {
        setOutputNavigation(null);
        setSelectedSceneId(null);
    }, [project?.id]);
    useEffect(() => {
        if (project)
            operationKeys.current = settleTimelineOperationKeys(operationKeys.current, project);
    }, [project]);
    const pollInterval =
        busy === "analyze" || analysisTracker.analysisUnresolved
            ? false
            : getRemakeProjectPollInterval(project);
    const pendingProject = useQuery({
        queryKey: [
            "smart-remake",
            "project",
            workspaceId,
            project?.id,
            project?.pendingOperation?.id,
        ],
        queryFn: () => getSmartRemakeProject(workspaceId, project!.id),
        enabled: pollInterval !== false,
        refetchInterval: (query) =>
            query.state.error ? false : getRemakeProjectPollInterval(query.state.data ?? project),
        refetchOnWindowFocus: false,
        retry: 1,
    });
    useEffect(() => {
        const next = pendingProject.data;
        if (!next || busy === "analyze" || analysisTracker.analysisUnresolved) return;
        if (getRemakeAnalysisRecovery(next)) setStep("prepare");
        setProject((current) =>
            current?.id === next.id ? latestRemakeProject(current, next) : current,
        );
        if (!next.pendingOperation)
            setNotice(
                getRemakeProjectError(next)
                    ? "Yêu cầu chưa hoàn tất. Các cảnh đã có vẫn được giữ để bạn kiểm tra."
                    : next.status === "ready"
                      ? next.schemaVersion === 2 && !next.finalVideoUrl
                          ? "Các clip đã sẵn sàng. Chọn và duyệt đoạn sẽ dùng của từng cảnh, rồi ghép video."
                          : "Video đã sẵn sàng. Bạn có thể xem lại hoặc chỉnh từng cảnh."
                      : "Đã kiểm tra kết quả. Các cảnh hoàn tất được giữ lại để bạn xem và hoàn thiện.",
            );
    }, [pendingProject.data, busy, analysisTracker.analysisUnresolved]);
    useEffect(() => {
        if (project) restoreAnalysis(project);
    }, [project, restoreAnalysis]);
    useEffect(() => {
        const recovered =
            supersedingAnalysisProject ?? failedAnalysisProject ?? recoveredAnalysisProject;
        const token = analysisToken;
        if (!recovered || token === undefined) return;
        if (project && (project.id !== recovered.id || project.revision > recovered.revision)) {
            completeAnalysis(token);
            return;
        }
        if (!supersedingAnalysisProject && failedAnalysisProject) {
            completeAnalysis(token);
            rememberProject(failedAnalysisProject);
            lastOperationErrorCode.current =
                failedAnalysisProject.analysisProgress?.errorCode || "SMART_REMAKE_COMPILE_FAILED";
            lastOperationError.current = getRemakeErrorMessage(
                new ApiError(
                    lastOperationErrorCode.current,
                    "Phân tích chưa hoàn tất. Kiểm tra tư liệu và trạng thái trước khi thử lại.",
                    400,
                ),
            );
            setError(lastOperationError.current);
            setNotice("");
            setStep("prepare");
            return;
        }
        const restored =
            recovered.expectationsHash && recovered.expectationsVersion === 1
                ? restoreTimelineCompile(recovered)
                : null;
        if (!supersedingAnalysisProject && !restored) return;
        if (
            supersedingAnalysisProject?.pendingOperation?.kind === "compile" &&
            supersedingAnalysisProject.analysisProgress?.status === "running" &&
            supersedingAnalysisProject.analysisProgress.operationId ===
                supersedingAnalysisProject.pendingOperation.id
        )
            restoreAnalysis(supersedingAnalysisProject, token);
        else completeAnalysis(token);
        if (restored) {
            setCompiled(restored);
            setLocalPlanNeedsUpdate(false);
            compiledRequirements.current = JSON.stringify(
                normalizeRemakeRequirements(recovered.requirements ?? policy.requirements),
            );
            setSourceCutFrames(getSourceCutFrames(restored.sourceSceneMap));
            setRenderGroupBreaks(getRenderGroupBreaks(restored.renderPlan));
            setSceneDrafts({});
        }
        rememberProject(recovered);
        setError(null);
        setStep(supersedingAnalysisProject ? getRemakeResumeStep(recovered) : "plan");
        setNotice(
            supersedingAnalysisProject
                ? "Dự án đã có cập nhật mới. Đang hiển thị trạng thái hiện tại từ máy chủ."
                : "Đã khôi phục kịch bản đã hoàn tất. Bạn có thể duyệt từng cảnh trước khi tạo video.",
        );
    }, [
        recoveredAnalysisProject,
        failedAnalysisProject,
        supersedingAnalysisProject,
        analysisToken,
        completeAnalysis,
        restoreAnalysis,
        policy.requirements,
        project,
        rememberProject,
    ]);
    const sourceFiles = useMemo(() => (video ? [video] : []), [video]);
    const localSourceUrl = useObjectUrls(sourceFiles)[0] ?? null;
    const sourceUrl = localSourceUrl ?? (!video ? (project?.sourceVideoUrl ?? null) : null);
    const uploadedUrls = useObjectUrls(images);
    const characterFiles = useMemo(() => (characterFile ? [characterFile] : []), [characterFile]);
    const characterUrl = useObjectUrls(characterFiles)[0] ?? project?.characterImageUrl ?? null;
    const productUrls = linkedProduct
        ? linkedProduct.imageUrls.slice(0, 1)
        : uploadedUrls.length
          ? uploadedUrls
          : !video && project?.productImageUrl
            ? [project.productImageUrl]
            : [];
    const measuredSourceDuration =
        sourceDuration ??
        (!video && project?.sourceSceneMap ? project.sourceSceneMap.sourceFrameCount / 24 : null);
    const sourceReuploadRequired = Boolean(
        !video && project && project.targetDuration !== duration,
    );
    const sourceExcerptError = sourceReuploadRequired
        ? "Thêm lại video mẫu để tạo dự án với thời lượng mới. Dự án trước vẫn được giữ."
        : measuredSourceDuration === null ||
            !Number.isFinite(measuredSourceDuration) ||
            measuredSourceDuration <= 0
          ? "Đang đọc độ dài video mẫu…"
          : null;
    const historicalSourcePlan = Boolean(
        compiled?.sourceSceneMap && compiled.sourceSceneMap.timingMode !== "fit_target",
    );
    const sourceFrameCount = historicalSourcePlan
        ? duration * 24
        : (compiled?.sourceSceneMap?.sourceFrameCount ??
          Math.round((measuredSourceDuration ?? 0) * 24));
    const sourceCutsError = sourceCutFrames
        ? validateSourceCuts(sourceCutFrames, sourceFrameCount)
        : null;
    const compiledCuts = getSourceCutFrames(compiled?.sourceSceneMap);
    const sourceCutsDirty = Boolean(
        compiled &&
        sourceCutFrames &&
        JSON.stringify(sourceCutFrames) !== JSON.stringify(compiledCuts),
    );
    const sourcePlanDirty =
        sourceCutsDirty ||
        Boolean(
            compiled &&
            compiledRequirements.current &&
            compiledRequirements.current !==
                JSON.stringify(normalizeRemakeRequirements(policy.requirements)),
        ) ||
        Boolean(
            compiled &&
            compiled.renderPlan?.groupingPolicy !== "fixed_provider_windows" &&
            JSON.stringify(renderGroupBreaks) !==
                JSON.stringify(getRenderGroupBreaks(compiled.renderPlan)),
        );
    const generationSetupError = getRemakeGenerationSetupError(compiled, health.data);
    const draftCompile = useMemo(
        () =>
            compiled && {
                ...compiled,
                sceneMap: {
                    ...compiled.sceneMap,
                    scenes: compiled.sceneMap.scenes.map((scene, index) => ({
                        ...scene,
                        ...sceneDrafts[index],
                    })),
                },
            },
        [compiled, sceneDrafts],
    );
    const invalidPromptDraft =
        draftCompile?.sceneMap.scenes.some((scene, index) => {
            if (
                (["prompt", "imagePrompt", "videoPrompt"] as const).some(
                    (field) => typeof scene[field] !== "string" || !scene[field].trim(),
                )
            )
                return true;
            const edited = sceneDrafts[index]?.videoPrompt;
            return (
                edited !== undefined &&
                edited.trim() !== compiled?.sceneMap.scenes[index].videoPrompt &&
                [...edited].length > 12000
            );
        }) ?? false;

    async function run<T>(kind: BusyStep, operation: () => Promise<T>): Promise<T | undefined> {
        if (lock.current) return undefined;
        const viewSerial = projectOpening.current.serial;
        lock.current = true;
        setBusy(kind);
        setError(null);
        if (kind === "analyze") setNotice("");
        lastOperationError.current = null;
        lastOperationErrorCode.current = null;
        try {
            return await operation();
        } catch (cause) {
            if (viewSerial !== projectOpening.current.serial) return undefined;
            lastOperationError.current = getRemakeErrorMessage(cause);
            lastOperationErrorCode.current = cause instanceof ApiError ? cause.code : null;
            setError(lastOperationError.current);
            if (
                kind === "analyze" &&
                cause instanceof ApiError &&
                [
                    "SMART_REMAKE_TIMELINE_SCENE_LIMIT",
                    "SMART_REMAKE_TIMELINE_SCENE_TOO_LONG",
                ].includes(cause.code)
            ) {
                const cuts = cause.details?.sourceCutFrames;
                if (
                    Array.isArray(cuts) &&
                    cuts.length >= 2 &&
                    cuts.every((frame) => Number.isInteger(frame) && frame >= 0) &&
                    cuts[0] === 0 &&
                    cuts.at(-1) === duration * 24
                )
                    setSourceCutFrames([...cuts] as number[]);
            }
            if (cause instanceof ApiError && cause.status === 409 && project?.schemaVersion === 2) {
                try {
                    const fresh = await getSmartRemakeProject(workspaceId, project.id);
                    if (viewSerial !== projectOpening.current.serial) return undefined;
                    rememberProject(fresh);
                } catch {
                    /* Keep local selections and the original conflict if refresh is unavailable. */
                }
            }
            const projectId = cause instanceof ApiError ? cause.details?.repairProjectId : null;
            if (typeof projectId === "string") {
                try {
                    const fresh = await getSmartRemakeProject(workspaceId, projectId);
                    if (viewSerial !== projectOpening.current.serial) return undefined;
                    rememberProject(fresh);
                    setStep("result");
                    setNotice(
                        "Các cảnh đã hoàn tất được giữ lại. Bạn có thể thử lại cảnh chưa tạo được.",
                    );
                } catch {
                    /* Keep the original error if recovery cannot be loaded yet. */
                }
            }
            return undefined;
        } finally {
            if (viewSerial === projectOpening.current.serial) {
                lock.current = false;
                setBusy(null);
            }
        }
    }

    useEffect(() => {
        if (requestedProjectId) {
            if (initialized.current === requestedProjectId) return;
            initialized.current = requestedProjectId;
            let active = true;
            void openProject(requestedProjectId, () => active);
            const serial = projectOpening.current.serial;
            return () => {
                active = false;
                initialized.current = false;
                if (projectOpening.current.active && projectOpening.current.serial === serial) {
                    projectOpening.current = { serial: serial + 1, active: false };
                    lock.current = false;
                }
            };
        }
        if (initialized.current) return;
        initialized.current = true;
        const handoff = consumeSmartRemakeHandoff();
        if (handoff) {
            setVideo(handoff.referenceVideo);
            setImages(handoff.productImages);
            return;
        }
        if (startNewProject) return;
        let projectId: string | null = null;
        try {
            const saved = localStorage.getItem(receiptStorageKey);
            if (saved?.startsWith("{")) {
                const receipt = JSON.parse(saved);
                if (
                    typeof receipt.projectId === "string" &&
                    typeof receipt.requestKey === "string"
                ) {
                    projectId = receipt.projectId;
                    submittedAnalysisKey.current = receipt.requestKey;
                }
            } else projectId = saved;
        } catch {
            return;
        }
        if (!projectId) return;
        let active = true;
        submittedProject.current = projectId;
        void checkSubmissionStatus(projectId, () => active);
        return () => {
            active = false;
            initialized.current = false;
        };
    }, [
        receiptStorageKey,
        checkSubmissionStatus,
        requestedProjectId,
        startNewProject,
        openProject,
    ]);

    function navigateOutput(
        sceneId: string,
        view: "watch" | "repair" | "compare" = "watch",
        versionId?: string,
    ) {
        setSelectedSceneId(sceneId);
        setStep("result");
        setOutputNavigation(() => ({ requestId: crypto.randomUUID(), sceneId, view, versionId }));
    }

    function invalidate() {
        if (project) setLocalPlanNeedsUpdate(true);
        setCompiled(null);
        setSceneDrafts({});
        setSourceCutFrames(undefined);
        setRenderGroupBreaks([]);
        setError(null);
        setNotice(
            project || result
                ? "Kịch bản cần cập nhật. Video đang dùng vẫn được giữ."
                : "Bạn có thể xem gợi ý kịch bản khi đã có đủ video và ảnh.",
        );
    }

    function validFile(file: File, kind: "video" | "image") {
        const types =
            kind === "video"
                ? ["video/mp4", "video/webm", "video/quicktime"]
                : ["image/jpeg", "image/png", "image/webp"];
        const max = (kind === "video" ? 30 : 10) * 1024 * 1024;
        if (!types.includes(file.type) || file.size > max) {
            setError(
                kind === "video"
                    ? "Chọn video MP4, MOV hoặc WebM, tối đa 30 MB nhé."
                    : "Chọn ảnh JPG, PNG hoặc WebP, tối đa 10 MB nhé.",
            );
            return false;
        }
        return true;
    }

    function onVideo(file: File) {
        if (lock.current || !validFile(file, "video")) return;
        invalidate();
        policy.invalidateMediaRights();
        setVideo(file);
        setTimelineStartFrame(0);
        setSourceDuration(null);
        setIsSample(false);
    }

    function onImages(files: File[]) {
        if (lock.current || !files.length || !files.every((file) => validFile(file, "image")))
            return;
        const additions = files.filter(
            (file, index) =>
                files.findIndex((other) => sameFile(file, other)) === index &&
                !images.some((other) => sameFile(file, other)),
        );
        if (!additions.length) return;
        invalidate();
        policy.invalidateMediaRights();
        setLinkedProduct(null);
        setLink("");
        setIsSample(false);
        setImages((current) => [...current, ...additions]);
    }

    function onRemoveImage(index: number) {
        if (lock.current) return;
        invalidate();
        policy.invalidateMediaRights();
        if (linkedProduct) {
            setLinkedProduct(null);
            setLink("");
            return;
        }
        setImages((current) => current.filter((_, i) => i !== index));
        setPrimaryIndex((current) =>
            current === index ? 0 : current > index ? current - 1 : current,
        );
    }

    async function importLink() {
        if (!/^https?:\/\//i.test(link.trim())) {
            setError("Thêm link sản phẩm bắt đầu bằng https:// nhé.");
            return;
        }
        await run("link", async () => {
            const preview = await crawlProductPreview(workspaceId, link.trim());
            const metadata = preview.product_draft.metadata_json;
            const imageUrls = [
                metadata.image_url,
                preview.crawl.image,
                ...(Array.isArray(metadata.screenshots) ? metadata.screenshots : []),
                ...(Array.isArray(metadata.buyer_images) ? metadata.buyer_images : []),
            ].filter(
                (url, index, values): url is string =>
                    typeof url === "string" &&
                    /^https?:\/\//i.test(url) &&
                    values.indexOf(url) === index,
            );
            if (!imageUrls.length)
                throw new Error(
                    "Chưa tìm thấy ảnh sản phẩm từ link này. Bạn có thể thêm ảnh trực tiếp nhé.",
                );
            const imageResponse = await fetch(imageUrls[0]);
            if (!imageResponse.ok)
                throw new Error("Chưa tải được ảnh sản phẩm. Thêm ảnh trực tiếp để lưu nháp nhé.");
            const imageBlob = await imageResponse.blob();
            const linkedImage = new File([imageBlob], "anh-san-pham", { type: imageBlob.type });
            if (!validFile(linkedImage, "image"))
                throw new Error("Ảnh sản phẩm chưa hợp lệ để lưu trên thiết bị.");
            invalidate();
            policy.invalidateMediaRights();
            setLinkedProduct({
                sourceUrl: preview.source_url,
                title: preview.product_draft.name,
                description: preview.product_draft.description ?? null,
                imageUrls,
            });
            setImages([linkedImage]);
            setPrimaryIndex(0);
            setIsSample(false);
            setNotice("Đã thêm sản phẩm từ link. Ảnh đầu tiên sẽ được dùng làm tham chiếu.");
        });
    }

    async function loadSample() {
        await run("sample", async () => {
            const paths = [
                "/smart-remake/binhnuoc.mp4",
                "/smart-remake/binh-giu-nhiet-stay-hydrate-sunhouse-ks-tu1200sp-1.webp",
            ];
            const responses = await Promise.all(paths.map((path) => fetch(path)));
            if (responses.some((response) => !response.ok))
                throw new Error(
                    "Chưa có bộ mẫu trên máy này. Bạn có thể dùng video và ảnh của mình.",
                );
            const blobs = await Promise.all(responses.map((response) => response.blob()));
            if (!blobs[0].type.startsWith("video/") || !blobs[1].type.startsWith("image/"))
                throw new Error("Bộ mẫu chưa sẵn sàng. Bạn thử thêm tư liệu của mình nhé.");
            invalidate();
            policy.invalidateMediaRights();
            setVideo(new File([blobs[0]], "video-mau.mp4", { type: "video/mp4" }));
            setTimelineStartFrame(0);
            setSourceDuration(null);
            setImages([new File([blobs[1]], "binh-hong.webp", { type: "image/webp" })]);
            setPrimaryIndex(0);
            setLinkedProduct(null);
            setLink("");
            setIsSample(true);
            setNotice("Đã thêm tư liệu mẫu. Đây là đầu vào để bạn thử luồng tạo video.");
        });
    }

    async function analyze(snapshot?: RemakeActionSnapshot) {
        if (submissionStatusError || checkingSubmissionStatus) {
            if (!checkingSubmissionStatus) await checkSubmissionStatus();
            return false;
        }
        if (analysisTracker.analysisUnresolved) {
            await analysisTracker.checkAnalysisStatus();
            return false;
        }
        const recovery = getRemakeAnalysisRecovery(project);
        if (recovery && recovery.retryDisposition !== "new_analysis") {
            await refreshProject();
            return false;
        }
        const savedSourceProjectId =
            !video && project?.schemaVersion === 2 ? project.id : undefined;
        if ((!video && !savedSourceProjectId) || !productUrls.length) return;
        if (sourceExcerptError || sourceCutsError) {
            setError(sourceExcerptError ?? sourceCutsError);
            return;
        }
        const confirmedError = snapshot
            ? getRemakeIntakeError(
                  snapshot.requirements,
                  snapshot.rights,
                  snapshot.budget,
                  Boolean(characterFile || project?.characterImageUrl),
              )
            : intakeError;
        if (confirmedError) {
            setError(confirmedError);
            return false;
        }
        return await run("analyze", async () => {
            const viewSerial = projectOpening.current.serial;
            const isCurrent = () => viewSerial === projectOpening.current.serial;
            setStep("prepare");
            const progressToken = analysisTracker.begin();
            const analysisCuts = historicalSourcePlan ? undefined : sourceCutFrames;
            const analysisGroups: number[] = [];
            if (recovery && project) {
                const latest = await readAnalysisProject(workspaceId, project.id);
                if (!isCurrent()) return false;
                const currentFailure = getRemakeAnalysisRecovery(latest);
                rememberProject(latest);
                if (
                    currentFailure?.operationId !== recovery.operationId ||
                    currentFailure.retryDisposition !== "new_analysis"
                ) {
                    analysisTracker.complete(progressToken);
                    throw new ApiError(
                        "SMART_REMAKE_PROJECT_CHANGED",
                        "Kiểm tra trạng thái mới nhất trước khi phân tích lại.",
                        409,
                    );
                }
            }
            const owned = await policy
                .prepareProject({
                    video,
                    product: images[primaryIndex],
                    productUrl: linkedProduct?.sourceUrl,
                    productImageUrl: linkedProduct?.imageUrls[0],
                    duration,
                    snapshot,
                })
                .catch((cause) => {
                    analysisTracker.complete(progressToken);
                    throw cause;
                });
            if (!isCurrent()) return false;
            const requestKey = operationKey({
                kind: "analysis",
                projectId: owned.id,
                revision: owned.revision,
                duration,
                analysisScope: "full_source",
                sourceCutFrames: analysisCuts,
                renderGroupBreaks: analysisGroups,
                language,
                prompt: brief,
                description,
                ...(owned.id === project?.id ? getRemakeAnalysisRetryBinding(project) : {}),
            });
            try {
                localStorage.setItem(
                    receiptStorageKey,
                    JSON.stringify({ projectId: owned.id, requestKey }),
                );
                submittedProject.current = owned.id;
                submittedAnalysisKey.current = requestKey;
            } catch {
                analysisTracker.complete(progressToken);
                throw new Error(
                    "Chưa lưu được biên nhận yêu cầu. Kiểm tra lưu trữ rồi thử lại; chưa gửi AI.",
                );
            }
            analysisTracker.track(progressToken, owned.id, requestKey, owned.revision);
            const observedCompletion = analysisTracker.waitForCompletion(progressToken);
            const submitted = compileSmartRemake(workspaceId, {
                targetDuration: duration,
                language,
                prompt: brief,
                description,
                projectId: owned.id,
                expectedRevision: owned.revision,
                idempotencyKey: requestKey,
                timelineMode: "reference",
                analysisScope: "full_source",
                referenceStartFrame: 0,
                ...(analysisCuts ? { sourceCutFrames: analysisCuts } : {}),
                renderGroupBreaks: analysisGroups,
            });
            const outcome = await Promise.race([
                submitted.then((compileResult) => ({ kind: "response" as const, compileResult })),
                observedCompletion.then((project) => ({ kind: "project" as const, project })),
            ]).catch(async (cause) => {
                if (!isCurrent()) throw cause;
                let provedFailure = false;
                try {
                    const latest = await readAnalysisProject(workspaceId, owned.id);
                    if (!isCurrent()) throw cause;
                    if (
                        latest.analysisProgress?.requestKey === requestKey &&
                        latest.analysisProgress.status === "failed"
                    ) {
                        provedFailure = true;
                        rememberProject(latest);
                        setStep("prepare");
                    }
                } catch {
                    // Keep the original failure and uncertain request key when GET is unavailable.
                }
                if (!isCurrent()) throw cause;
                if (
                    provedFailure ||
                    (cause instanceof ApiError &&
                        cause.status >= 400 &&
                        cause.status < 500 &&
                        ![408, 429].includes(cause.status) &&
                        ![
                            "SMART_REMAKE_COMPILE_RECONCILIATION_REQUIRED",
                            "SMART_REMAKE_OPERATION_BUSY",
                        ].includes(cause.code))
                ) {
                    analysisTracker.complete(progressToken);
                    setNotice("");
                } else analysisTracker.interrupt(progressToken);
                throw cause;
            });
            if (!isCurrent()) return false;
            analysisTracker.complete(progressToken);
            const next =
                outcome.kind === "project"
                    ? restoreTimelineCompile(outcome.project)!
                    : outcome.compileResult;
            if (submittedAnalysisKey.current === requestKey) {
                submittedProject.current = null;
                submittedAnalysisKey.current = null;
                try {
                    localStorage.removeItem(receiptStorageKey);
                } catch {
                    /* The matching successful response has already settled this receipt. */
                }
            }
            setCompiled(next);
            setLocalPlanNeedsUpdate(false);
            compiledRequirements.current = JSON.stringify(
                normalizeRemakeRequirements(snapshot?.requirements ?? policy.requirements),
            );
            setSourceCutFrames(getSourceCutFrames(next.sourceSceneMap));
            setRenderGroupBreaks(getRenderGroupBreaks(next.renderPlan));
            setSceneDrafts({});
            if (next.projectId) {
                try {
                    const fresh =
                        outcome.kind === "project"
                            ? outcome.project
                            : await readAnalysisProject(workspaceId, next.projectId);
                    if (!isCurrent()) return false;
                    rememberProject(fresh);
                } catch {
                    /* The compile response still carries the durable render identity. */
                }
            }
            if (!isCurrent()) return false;
            setStep("plan");
            setNotice(
                "Kịch bản đã sẵn sàng. Xem lại từng cảnh rồi tạo video, không cần viết prompt.",
            );
            return true;
        });
    }

    async function generate(demo = false, snapshot?: RemakeActionSnapshot) {
        if (!compiled) return;
        if (policy.contextDirty && !snapshot) {
            setError("Lưu yêu cầu và quyền sử dụng, rồi cập nhật kịch bản trước khi tạo video.");
            return;
        }
        if (sourcePlanDirty || sourceCutsError) {
            setError(
                sourceCutsError ??
                    "Mốc cắt hoặc nhóm cảnh đã thay đổi. Cập nhật kịch bản trước khi tạo nhé.",
            );
            return;
        }
        if (project?.pendingOperation) {
            setError("Video trước vẫn đang được xử lý. Hãy kiểm tra kết quả trước khi tạo tiếp.");
            return;
        }
        return await run("generate", async () => {
            let renderProject = project;
            let ready = Object.entries(sceneDrafts).reduce(
                (value, [index, patch]) => updateRemakeScene(value, Number(index), patch),
                compiled,
            );
            if (project && project.id === ready.projectId)
                ready = { ...ready, revision: project.revision };
            if (snapshot && project) {
                const owned = await policy.syncContext(project, snapshot);
                ready = { ...ready, revision: owned.revision };
                renderProject = owned;
            }
            const productImage = images[primaryIndex];
            const productUrl = linkedProduct?.sourceUrl;
            if (!demo && health.data?.mode === "live" && health.data.kieConfigured)
                renderAttempt.current = prepareRemakeRenderRetry(
                    renderAttempt.current,
                    { compileResult: ready, productImage, productUrl },
                    renderProject?.generationRecovery,
                );
            const next = await renderSmartRemakeVideo(workspaceId, {
                compileResult: ready,
                productImage,
                productUrl,
                health: health.data,
                demo,
                ...(!demo && renderAttempt.current
                    ? { idempotencyKey: renderAttempt.current.idempotencyKey }
                    : {}),
            });
            setCompiled(ready);
            setSceneDrafts({});
            setResult(next);
            if (next.repairProject) rememberProject(next.repairProject);
            else if (next.status === "completed" && next.finalVideoUrl) setProject(null);
            renderAttempt.current = null;
            setStep("result");
            setNotice(
                next.isDemo
                    ? "Đang xem video ví dụ, không phải kết quả AI vừa tạo."
                    : next.status === "completed"
                      ? "Video đã sẵn sàng. Bạn có thể xem lại hoặc chỉnh từng cảnh."
                      : next.repairProject?.provider === "kie"
                        ? "Đã lưu yêu cầu tạo video. Kết quả sẽ tự cập nhật khi sẵn sàng."
                        : "Yêu cầu đã gửi. Chưa có video hoàn tất để phát hoặc tải.",
            );
            return true;
        });
    }

    function operationKey(payload: unknown) {
        const signature = JSON.stringify(payload);
        const existing = operationKeys.current.get(signature);
        if (existing) return existing;
        const key = crypto.randomUUID();
        operationKeys.current.set(signature, key);
        return key;
    }

    async function performOperation(
        payload: unknown,
        request: (key: string) => Promise<SmartRemakeOperationResult>,
    ) {
        const signature = JSON.stringify(payload);
        try {
            const response = await request(operationKey(payload));
            if (response.status !== "running") operationKeys.current.delete(signature);
            return response;
        } catch (cause) {
            if (cause instanceof ApiError && cause.details?.operationStatus === "failed") {
                operationKeys.current.delete(signature);
            }
            throw cause;
        }
    }

    async function repair(
        sceneId: string,
        draft: SmartRemakePromptDraft | RepairIntent,
        snapshot?: RemakeActionSnapshot,
    ) {
        if (!project) return null;
        repairAccepted.current = false;
        const scene = project.scenes.find((item) => item.id === sceneId);
        if (!scene) return null;
        if (!hasRemakeRepairClip(scene)) {
            lastOperationErrorCode.current = "SMART_REMAKE_BASE_VERSION_REQUIRED";
            lastOperationError.current = getRemakeErrorMessage(
                new ApiError(lastOperationErrorCode.current, "", 409),
            );
            setError(lastOperationError.current);
            return null;
        }
        return (
            (await run("repair", async () => {
                const owned = snapshot ? await policy.syncContext(project, snapshot) : project;
                const input = {
                    ...("schemaVersion" in draft ? { repairIntent: draft } : draft),
                    baseVersionId: scene.activeVersionId,
                    expectedRevision: owned.revision,
                };
                const payload = { projectId: project.id, sceneId, ...input };
                const key = operationKey(payload);
                await repairTracking.begin({
                    requestKey: key,
                    requestFingerprint: JSON.stringify(payload),
                    projectId: project.id,
                    sceneId,
                    baseVersionId: scene.activeVersionId,
                });
                let next: SmartRemakeOperationResult;
                try {
                    next = await repairSmartRemakeScene(workspaceId, project.id, sceneId, {
                        ...input,
                        idempotencyKey: key,
                    });
                } catch (cause) {
                    if (
                        cause instanceof ApiError &&
                        (cause.details?.operationStatus === "failed" ||
                            cause.code === "SMART_REMAKE_REVISION_CONFLICT")
                    )
                        await repairTracking.record(key, {
                            status: "failed",
                            needsReconciliation: false,
                        });
                    throw cause;
                }
                rememberProject(next.project);
                repairAccepted.current = next.status !== "failed";
                try {
                    await repairTracking.record(key, {
                        status:
                            next.status === "completed"
                                ? "completed"
                                : next.status === "failed"
                                  ? "failed"
                                  : "running",
                        operationId: next.operationId,
                        candidateVersionId: next.candidateVersionId ?? null,
                        needsReconciliation: Boolean(
                            next.project.pendingOperation?.needsReconciliation,
                        ),
                    });
                } catch {
                    setNotice(
                        "Yêu cầu đã gửi. Chưa lưu được biên nhận mới trên thiết bị; kiểm tra trạng thái trước khi tiếp tục.",
                    );
                }
                if (next.status === "failed")
                    throw new Error(
                        "Chưa tạo được cảnh mới. Video đang dùng vẫn được giữ; bạn có thể thử lại.",
                    );
                repairAccepted.current = true;
                if (next.status !== "completed") {
                    setNotice(
                        "Yêu cầu đang được xử lý. Tải lại phiên bản sau ít phút để kiểm tra nhé.",
                    );
                    return null;
                }
                setNotice("Có bản mới để bạn so sánh. Video đang dùng chưa thay đổi.");
                return next.candidateVersionId ?? null;
            })) ?? null
        );
    }

    async function accept(sceneId: string, versionId: string) {
        if (!project) return false;
        return (
            (await run("compose", async () => {
                const input = { sceneId, versionId, expectedRevision: project.revision };
                const next = await performOperation({ projectId: project.id, ...input }, (key) =>
                    acceptSmartRemakeVersion(workspaceId, project.id, {
                        ...input,
                        idempotencyKey: key,
                    }),
                );
                rememberProject(next.project);
                if (next.status === "failed")
                    throw new Error(
                        "Chưa ghép được video. Các phiên bản cảnh vẫn được giữ để bạn thử lại.",
                    );
                setNotice(
                    next.status === "completed"
                        ? next.project.schemaVersion === 2
                            ? "Đã đưa phiên bản vào bản nháp. Chọn và duyệt đoạn sẽ dùng trước khi ghép."
                            : "Đã ghép cảnh vào video. Các cảnh còn lại giữ nguyên."
                        : "Video đang được ghép. Bản đang dùng vẫn được giữ.",
                );
                return next.status === "completed";
            })) ?? false
        );
    }

    async function saveTimeline(items: SmartRemakeTimelineSelectionInput[]): Promise<void> {
        if (!project || project.schemaVersion !== 2) return;
        const saved = await run("timeline", async () => {
            const input = { expectedRevision: project.revision, items };
            const next = await performOperation(
                { kind: "timeline", projectId: project.id, ...input },
                (key) =>
                    saveSmartRemakeTimeline(workspaceId, project.id, {
                        ...input,
                        idempotencyKey: key,
                    }),
            );
            rememberProject(next.project);
            setNotice(
                "Đã duyệt đoạn sẽ dùng. Video đã xuất vẫn được giữ đến khi bạn ghép bản mới.",
            );
            return true;
        });
        if (!saved) throw new Error("Chưa lưu được đoạn cắt. Kiểm tra thông báo và thử lại nhé.");
    }

    async function publish(): Promise<void> {
        if (!project) return;
        const readinessError = getTimelinePublishError(project);
        if (readinessError) {
            setError(readinessError);
            return;
        }
        await run("compose", async () => {
            const input = { expectedRevision: project.revision };
            const next = await performOperation(
                { kind: "publish", projectId: project.id, ...input },
                (key) =>
                    publishSmartRemakeTimeline(workspaceId, project.id, {
                        ...input,
                        idempotencyKey: key,
                    }),
            );
            rememberProject(next.project);
            if (next.status === "failed")
                throw new Error("Chưa ghép được video. Bản nháp và video đã xuất vẫn được giữ.");
            setNotice(
                next.status === "running"
                    ? "Đang ghép các đoạn đã duyệt. Video đã xuất trước đó vẫn được giữ."
                    : "Đã ghép xong video từ các đoạn bạn duyệt.",
            );
        });
    }

    async function refreshProject() {
        if (!project) return;
        await run("restore", async () => {
            const next =
                pollInterval !== false
                    ? (await pendingProject.refetch({ throwOnError: true })).data
                    : await getSmartRemakeProject(workspaceId, project.id);
            if (next) rememberProject(next);
            await repairTracking.refresh();
            setNotice("Đã cập nhật các phiên bản mới nhất.");
        });
    }

    const localFileIds = useRef(new WeakMap<File, number>());
    const nextFileId = useRef(0);
    function fileId(file: File | null | undefined) {
        if (!file) return null;
        if (!localFileIds.current.has(file)) localFileIds.current.set(file, ++nextFileId.current);
        return localFileIds.current.get(file);
    }
    const actionFingerprint = JSON.stringify({
        video: fileId(video),
        images: images.map(fileId),
        character: fileId(characterFile),
        primaryIndex,
        linkedProduct,
        duration,
        timelineStartFrame,
        sourceCutFrames,
        renderGroupBreaks,
        language,
        brief,
        description,
        sceneDrafts,
        repairDrafts,
        requirements: normalizeRemakeRequirements(policy.requirements),
        compiled,
        projectId: project?.id,
        revision: project?.revision,
        analysisOperation: project?.analysisProgress && {
            id: project.analysisProgress.operationId,
            status: project.analysisProgress.status,
            retryDisposition: project.analysisProgress.retryDisposition,
        },
        scenes: project?.scenes.map((scene) => [
            scene.id,
            scene.activeVersionId,
            scene.versions.map((version) => version.id),
        ]),
    });
    function validateAction(intent: RemakeActionIntent, snapshot?: RemakeActionSnapshot) {
        if (submissionStatusError || checkingSubmissionStatus)
            return "Kiểm tra trạng thái yêu cầu đã gửi trước khi gọi AI tiếp.";
        if (lock.current) return "Đang thực hiện thao tác. Chờ kết quả trước khi tiếp tục.";
        if (analysisTracker.analysisUnresolved)
            return "Phân tích trước chưa rõ kết quả. Kiểm tra trạng thái trước khi gửi yêu cầu mới.";
        if (project?.pendingOperation || repairTracking.unresolved) {
            setStep("result");
            return "Yêu cầu trước đang xử lý hoặc cần đối soát. Kiểm tra trạng thái trước khi tạo tiếp.";
        }
        if (!health.data?.enabled) return "Dịch vụ chưa sẵn sàng. Kết nối lại để tiếp tục.";
        if (intent.action === "analyze" || intent.action === "reanalyze") {
            const recovery = getRemakeAnalysisRecovery(project);
            if (recovery && recovery.retryDisposition !== "new_analysis")
                return "Kiểm tra trạng thái lượt phân tích trước khi gửi yêu cầu mới.";
            if (!video && !(project?.schemaVersion === 2 && project.sourceVideoUrl))
                return "Thêm video mẫu để tạo kịch bản.";
            if (!productUrls.length) return "Thêm ảnh sản phẩm để tạo kịch bản.";
            if (!video && (images.length || linkedProduct || characterFile))
                return "Thêm lại video mẫu để lưu bộ tư liệu mới trước khi phân tích.";
            if (sourceExcerptError || sourceCutsError) return sourceExcerptError ?? sourceCutsError;
        } else if (intent.action === "render") {
            if (!compiled) return "Tạo kịch bản trước khi tạo video.";
            if (sourcePlanDirty || sourceCutsError)
                return (
                    sourceCutsError ??
                    "Kịch bản đã thay đổi. Cập nhật kịch bản trước khi tạo video."
                );
            if (generationSetupError) return generationSetupError;
            if (invalidPromptDraft)
                return "Kịch bản chưa hợp lệ. Cập nhật kịch bản trước khi tạo video.";
        } else if (!project) return "Mở dự án trước khi tiếp tục.";
        if (
            intent.action === "repair" &&
            (localPlanNeedsUpdate ||
                (project &&
                    video &&
                    !policy.hasCurrentIntake(
                        video,
                        images[primaryIndex],
                        linkedProduct?.sourceUrl,
                        duration,
                    )))
        )
            return "Tư liệu đã thay đổi. Cập nhật kịch bản trước khi tạo lại cảnh.";
        if (
            intent.action === "repair" &&
            !project?.scenes.some(
                (scene) =>
                    scene.id === intent.sceneId && scene.activeVersionId === intent.baseVersionId,
            )
        )
            return "Phiên bản cảnh đã thay đổi. Chọn lại cảnh cần tạo lại.";
        if (intent.action === "repair") {
            if (!hasRemakeRepairClip(project?.scenes.find((scene) => scene.id === intent.sceneId)))
                return getRemakeErrorMessage(
                    new ApiError("SMART_REMAKE_BASE_VERSION_REQUIRED", "", 409),
                );
            const groupingError = getRemakeProviderGroupingError(project);
            if (groupingError) return groupingError;
        }
        if (snapshot) {
            if (
                JSON.stringify(normalizeRemakeRequirements(snapshot.requirements)) !==
                JSON.stringify(normalizeRemakeRequirements(policy.requirements))
            )
                return "Yêu cầu đã thay đổi. Đóng và chọn lại hành động.";
            return getRemakeIntakeError(
                snapshot.requirements,
                snapshot.rights,
                snapshot.budget,
                Boolean(characterFile || project?.characterImageUrl),
            );
        }
        return null;
    }
    const actionGate = useRemakeAction({
        workspaceId,
        fingerprint: actionFingerprint,
        request: (intent) => ({
            action: intent.startsNewProject ? "analyze" : intent.action,
            budgetMode: "unlimited",
            ...(!policy.hasCurrentIntake(
                video,
                images[primaryIndex],
                linkedProduct?.sourceUrl,
                duration,
            ) &&
            (intent.action === "analyze" || intent.action === "reanalyze")
                ? {}
                : project
                  ? { projectId: project.id, expectedRevision: project.revision }
                  : {}),
            targetDuration: duration,
            ...(intent.action === "analyze" || intent.action === "reanalyze"
                ? {
                      referenceStartFrame: 0,
                      analysisScope: "full_source" as const,
                      ...(measuredSourceDuration != null
                          ? { sourceDurationSeconds: measuredSourceDuration }
                          : {}),
                  }
                : {}),
            requiresCharacter: policy.requirements.requiresCharacter,
            ...(intent.action === "repair"
                ? {
                      sceneId: intent.sceneId,
                      baseVersionId: intent.baseVersionId,
                      ...(intent.repairIntent ? { repairIntent: intent.repairIntent } : {}),
                  }
                : {}),
            ...(intent.action === "inspect" ? { subject: intent.subject } : {}),
        }),
        validate: validateAction,
        failureMessage: () => lastOperationError.current,
        failureCode: () => lastOperationErrorCode.current,
        execute: async (intent, snapshot) => {
            policy.applySnapshot(snapshot);
            if (intent.action === "analyze" || intent.action === "reanalyze")
                return Boolean(await analyze(snapshot));
            if (intent.action === "render") return Boolean(await generate(false, snapshot));
            if (intent.action === "inspect") return policy.inspect(intent.subject, snapshot);
            if (intent.action === "repair") {
                await repair(intent.sceneId, intent.repairIntent ?? intent.draft!, snapshot);
                // A queued repair has a receipt even when its candidate is not available yet.
                return repairAccepted.current;
            }
            return false;
        },
    });
    function requestAction(action: SmartRemakePreflightAction, args: RemakeActionArgs = {}) {
        let intent: RemakeActionIntent;
        if (action === "repair") {
            const scene = project?.scenes.find((item) => item.id === args.sceneId);
            if (!scene || (!args.draft && !args.repairIntent)) {
                setError("Chọn cảnh và yêu cầu tạo lại trước khi tiếp tục.");
                return Promise.resolve();
            }
            if (!hasRemakeRepairClip(scene)) {
                lastOperationErrorCode.current = "SMART_REMAKE_BASE_VERSION_REQUIRED";
                lastOperationError.current = getRemakeErrorMessage(
                    new ApiError(lastOperationErrorCode.current, "", 409),
                );
                setError(lastOperationError.current);
                return Promise.resolve();
            }
            setLastActionRepairCandidate(null);
            intent = {
                action,
                fingerprint: actionFingerprint,
                sceneId: scene.id,
                baseVersionId: scene.activeVersionId,
                ...(args.repairIntent
                    ? { repairIntent: structuredClone(args.repairIntent) }
                    : { draft: { ...args.draft! } }),
            };
        } else if (action === "inspect") {
            if (!args.subject) {
                setError("Chọn đối tượng cần kiểm tra.");
                return Promise.resolve();
            }
            intent = { action, fingerprint: actionFingerprint, subject: { ...args.subject } };
        } else
            intent = {
                action,
                fingerprint: actionFingerprint,
                ...((action === "analyze" || action === "reanalyze") &&
                project &&
                video &&
                !policy.hasCurrentIntake(
                    video,
                    images[primaryIndex],
                    linkedProduct?.sourceUrl,
                    duration,
                )
                    ? { startsNewProject: true }
                    : {}),
            };
        const snapshot: RemakeActionSnapshot = structuredClone({
            requirements: policy.requirements,
            rights: policy.rights,
            budget: { mode: "unlimited" },
        });
        const needsRights = getRemakeRightsError(
            snapshot.requirements,
            snapshot.rights,
            Boolean(characterFile || project?.characterImageUrl),
        );
        return actionGate.openAction(intent, needsRights ? undefined : snapshot);
    }

    const visibleActionError = !actionGate.pendingAction ? actionGate.actionError : null;
    const visibleProjectError =
        step !== "result" && busy !== "analyze" && !analysisTracker.analysisUnresolved
            ? getRemakeProjectError(project)
            : null;

    return {
        ...policy,
        ...actionGate,
        analysisProgress: analysisTracker.analysisProgress,
        analysisStartedAt: analysisTracker.analysisStartedAt,
        analysisPreparing: analysisTracker.analysisPreparing,
        canCheckAnalysisStatus: analysisTracker.canCheckAnalysisStatus,
        analysisUnresolved: analysisTracker.analysisUnresolved,
        analysisStatusError: analysisTracker.analysisStatusError,
        checkingAnalysisStatus: analysisTracker.checkingAnalysisStatus,
        checkAnalysisStatus: analysisTracker.checkAnalysisStatus,
        requestAction,
        openProject,
        submissionStatusError,
        checkingSubmissionStatus,
        checkSubmissionStatus: () => checkSubmissionStatus(),
        viewSavedScript: () => {
            if (!project) return;
            const saved = restoreTimelineCompile(project);
            if (!saved) return;
            setCompiled(saved);
            setStep("plan");
            setNotice(
                getRemakeAnalysisRecovery(project)
                    ? "Đang xem kịch bản đã lưu trước lượt phân tích gần nhất."
                    : "Đang xem kịch bản được dùng cho lượt tạo video này.",
            );
        },
        localMediaNeedsAnalysis:
            localPlanNeedsUpdate ||
            Boolean(
                project &&
                video &&
                !policy.hasCurrentIntake(
                    video,
                    images[primaryIndex],
                    linkedProduct?.sourceUrl,
                    duration,
                ),
            ),
        repairDrafts,
        onRepairDraftChange: (sceneId: string, versionId: string | null, value: RepairIntent) =>
            setRepairDrafts((current) => ({
                ...current,
                [`${sceneId}:${versionId ?? "initial"}`]: value,
            })),
        unreadRepairCandidate: repairTracking.candidate,
        unresolvedRepairReceipt: repairTracking.unresolved,
        repairReceiptError: repairTracking.error,
        repairFailures: repairTracking.failures,
        viewRepairCandidate: async () => {
            const candidate = repairTracking.candidate;
            if (!candidate) return;
            navigateOutput(candidate.sceneId, "compare", candidate.versionId);
            await repairTracking.acknowledgeCandidate("viewed");
        },
        dismissRepairCandidate: () => repairTracking.acknowledgeCandidate("skipped"),
        outputNavigation,
        selectedSceneId,
        onOutputSceneChange: setSelectedSceneId,
        navigateOutput,
        lastActionRepairCandidate:
            lastActionRepairCandidate?.projectId === project?.id ? lastActionRepairCandidate : null,
        intakeError,
        characterUrl,
        onCharacterChange: (file: File | null) => {
            if (!lock.current) {
                policy.onCharacterChange(file);
                invalidate();
            }
        },
        step,
        setStep,
        duration,
        timelineStartFrame,
        sourceDuration: measuredSourceDuration,
        sourceCutFrames,
        sourceExcerptError,
        sourceReuploadRequired,
        sourceCutsError,
        sourcePlanDirty,
        sourceCutsDirty,
        renderGroupBreaks,
        generationSetupError,
        onRenderGroupBreaksChange: (breaks: number[]) => {
            if (!lock.current && compiled?.renderPlan?.groupingPolicy !== "fixed_provider_windows")
                setRenderGroupBreaks([...breaks]);
        },
        onTimelineStartFrameChange: (frame: number) => {
            if (lock.current) return;
            invalidate();
            setTimelineStartFrame(frame);
        },
        onSourceMetadata: (seconds: number) => {
            if (Number.isFinite(seconds) && seconds > 0) setSourceDuration(seconds);
        },
        onSourceCutFramesChange: (cuts: number[]) => {
            if (!lock.current) {
                setSourceCutFrames([...cuts]);
                setRenderGroupBreaks([]);
            }
        },
        saveTimeline,
        publish,
        language,
        brief,
        description,
        video,
        sourceUrl,
        productUrls,
        primaryIndex,
        link,
        linkedProduct,
        isSample,
        compiled: draftCompile,
        sceneDrafts,
        result,
        project,
        busy,
        error:
            error ??
            visibleActionError ??
            visibleProjectError ??
            (pollInterval !== false && pendingProject.isError
                ? "Chưa cập nhật được tiến trình. Yêu cầu đã gửi vẫn được giữ; bấm Kiểm tra lại để kết nối lại."
                : null),
        errorCode: error
            ? error === lastOperationError.current
                ? lastOperationErrorCode.current
                : null
            : visibleActionError
              ? actionGate.actionErrorCode
              : visibleProjectError
                ? (project?.lastOperation?.errorCode ?? null)
                : null,
        notice: busy === "analyze" || analysisTracker.analysisUnresolved ? "" : notice,
        health,
        invalidPromptDraft,
        hasDraftChanges: Object.keys(sceneDrafts).length > 0,
        canConfirmRights: Boolean(
            (video || (!video && project?.schemaVersion === 2 && project.sourceVideoUrl)) &&
            productUrls.length &&
            !sourceExcerptError &&
            !sourceCutsError &&
            !hasCurrentRemakeRightsAttestation(policy.rights) &&
            health.data?.enabled &&
            !busy &&
            !analysisTracker.analysisUnresolved,
        ),
        canAnalyze: Boolean(
            (video || (!video && project?.schemaVersion === 2 && project.sourceVideoUrl)) &&
            productUrls.length &&
            !sourceExcerptError &&
            !sourceCutsError &&
            !intakeError &&
            health.data?.enabled &&
            !busy &&
            !analysisTracker.analysisUnresolved,
        ),
        onVideo,
        onImages,
        onRemoveImage,
        importLink,
        loadSample,
        analyze,
        generate,
        repair,
        accept,
        refreshProject,
        onDuration: (value: 8 | 16) => {
            invalidate();
            setDuration(value);
            if (measuredSourceDuration !== null)
                setTimelineStartFrame((current) =>
                    Math.min(
                        current,
                        Math.max(0, Math.floor(measuredSourceDuration * 24) - value * 24),
                    ),
                );
        },
        onLanguage: (value: string) => {
            invalidate();
            setLanguage(value);
        },
        onBrief: (value: string) => {
            invalidate();
            setBrief(value);
        },
        onDescription: (value: string) => {
            invalidate();
            setDescription(value);
        },
        onPrimaryChange: (value: number) => {
            if (lock.current) return;
            if (value !== primaryIndex) policy.invalidateMediaRights();
            invalidate();
            setPrimaryIndex(value);
        },
        onLinkChange: setLink,
        onSceneChange: (index: number, patch: Record<string, string>) =>
            setSceneDrafts((current) => ({ ...current, [index]: { ...current[index], ...patch } })),
    };
}

function sameFile(a: File, b: File) {
    return a.name === b.name && a.size === b.size && a.lastModified === b.lastModified;
}

function useObjectUrls(files: File[]) {
    const [urls, setUrls] = useState<string[]>([]);
    useEffect(() => {
        const next = files.map((file) => URL.createObjectURL(file));
        setUrls(next);
        return () => next.forEach((url) => URL.revokeObjectURL(url));
    }, [files]);
    return urls;
}
