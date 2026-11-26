import { createFileRoute, useNavigate, useRouteContext, useSearch } from "@tanstack/react-router";
import {
    ArrowRight,
    Check,
    ChevronLeft,
    LoaderCircle,
    Plus,
    RefreshCw,
    Sparkles,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { AppShell } from "@/widgets/app-shell/app-shell";
import { useApiWorkspace } from "@/shared/hooks/use-workspace";
import { Button } from "@/shared/ui/button";
import { RemakeInputs } from "../components/remake-inputs";
import { RemakeStoryboard } from "../components/remake-storyboard";
import { RemakeJourney } from "../components/remake-journey";
import { RemakeOutput } from "../components/remake-output";
import { RemakeActionConfirmation } from "../components/remake-action-confirmation";
import { RemakeAnalysisLoading } from "../components/remake-analysis-loading";
import { RemakeAnalysisRecovery } from "../components/remake-analysis-recovery";
import { RemakeResultNextStep } from "../components/remake-result-next-step";
import { RemakeProcessing } from "../components/remake-processing";
import { getRemakeSceneLabel } from "../lib/remake-scene-label";
import {
    getRemakeResultNextAction,
    type RemakeResultNextAction,
} from "../lib/remake-result-next-action";
import { RemakeProjectInputs } from "../components/remake-project-inputs";
import { RemakeInspector } from "../components/remake-inspector";
import { RemakeProjectControls } from "../components/remake-project-controls";
import { RemakePlayer } from "../components/remake-player";
import { Dialog, DialogContent, DialogTitle, DialogDescription } from "@/shared/ui/dialog";
import { resolveInspectionEvidence, type InspectionSeekTarget } from "../lib/remake-inspection";
import type { SmartRemakeInspectionEvidence } from "@/shared/api/smart-remake";
import { useRemakeStudio } from "../lib/use-remake-studio";
import { getRenderTaskCount } from "../lib/remake-groups";
import { normalizeRemakeRequirements } from "../lib/remake-intake";
import { getRemakeErrorMessage, getRemakeProviderGroupingError } from "../lib/smart-remake-render";
import { getRemakeAnalysisRecovery } from "../lib/remake-analysis-recovery";
import { restoreTimelineCompile } from "../lib/remake-timeline";
import { ApiError } from "@/shared/api/errors";
import { RemakeGenerationProgress } from "../components/remake-generation-progress";
import { getRemakeGenerationProgress } from "../lib/remake-generation-progress";
import "../components/remake-studio.css";

export const Route = createFileRoute("/smart-remake")({
    head: () => ({ meta: [{ title: "Smart Remake - Viraldy" }] }),
    component: SmartRemakePage,
    validateSearch: (
        search: Record<string, unknown>,
    ): { projectId?: string; newProject?: boolean } => {
        const projectId =
            typeof search.projectId === "string" &&
            /^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/i.test(search.projectId)
                ? search.projectId
                : undefined;
        return {
            projectId,
            ...(!projectId && [true, "true", "1"].includes(search.newProject as boolean | string)
                ? { newProject: true }
                : {}),
        };
    },
});

const primary =
    "min-h-11 bg-[var(--primary-active)] px-5 text-white hover:bg-[#c90939] motion-reduce:active:scale-100";

function SmartRemakePage() {
    const { auth } = useRouteContext({ from: "__root__" });
    const { workspaceId, workspaces } = useApiWorkspace();
    const { projectId, newProject } = useSearch({ from: "/smart-remake" });
    if (!workspaceId)
        return (
            <AppShell>
                <div className="rounded-3xl bg-surface p-8" role="status">
                    {workspaces.isLoading
                        ? "Đang mở workspace…"
                        : workspaces.isError
                          ? "Chưa mở được workspace. Bạn tải lại trang để thử nhé."
                          : "Chọn workspace để bắt đầu tạo video."}
                </div>
            </AppShell>
        );
    return (
        <SmartRemakeStudio
            key={`${auth.user?.id}:${workspaceId}`}
            workspaceId={workspaceId}
            accountId={auth.user?.id}
            projectId={projectId}
            newProject={newProject}
        />
    );
}

function SmartRemakeStudio({
    workspaceId,
    accountId,
    projectId,
    newProject,
}: {
    workspaceId: string;
    accountId?: string;
    projectId?: string;
    newProject?: boolean;
}) {
    const studio = useRemakeStudio(workspaceId, accountId, projectId, Boolean(newProject));
    const navigate = useNavigate();
    const linkedProject = useRef<string | undefined>(undefined);
    useEffect(() => {
        const identity = studio.project?.id;
        if (!identity || linkedProject.current === identity) return;
        linkedProject.current = identity;
        if (identity !== projectId)
            void navigate({ to: "/smart-remake", search: { projectId: identity }, replace: true });
    }, [studio.project?.id, projectId, navigate]);
    const analyzing = studio.busy === "analyze" || Boolean(studio.analysisUnresolved);
    const controlsLocked =
        Boolean(studio.busy || studio.actionLoading || studio.actionSubmitting) || analyzing;
    const failedAnalysis = getRemakeAnalysisRecovery(studio.project);
    const savedScriptIdentity = JSON.stringify([
        failedAnalysis?.operationId,
        studio.project?.id,
        studio.project?.revision,
        studio.sourceUrl,
        studio.productUrls,
        studio.primaryIndex,
        studio.duration,
        studio.requirements,
    ]);
    const [savedScriptView, setSavedScriptView] = useState<string | null>(null);
    const viewingSavedScript = Boolean(
        failedAnalysis &&
        studio.step === "plan" &&
        savedScriptView === savedScriptIdentity &&
        studio.compiled,
    );
    const analysisRecoveryVisible = Boolean(
        failedAnalysis && !analyzing && studio.step !== "result" && !viewingSavedScript,
    );
    const step = analysisRecoveryVisible ? "prepare" : studio.step;
    const analysisErrorExplained = Boolean(
        failedAnalysis &&
        studio.errorCode === failedAnalysis.errorCode &&
        [undefined, "SMART_REMAKE_GEMINI_OUTPUT_TRUNCATED"].some(
            (causeCode) =>
                studio.error ===
                getRemakeErrorMessage(
                    new ApiError(
                        failedAnalysis.errorCode ?? "SMART_REMAKE_COMPILE_FAILED",
                        "",
                        409,
                        causeCode ? { causeCode } : undefined,
                    ),
                ),
        ),
    );
    const directAnalysis =
        studio.actionExecutingIntent?.action === "analyze" ||
        studio.actionExecutingIntent?.action === "reanalyze"
            ? studio.actionExecutingIntent
            : null;
    const actionSceneId =
        studio.pendingAction?.action === "repair"
            ? studio.pendingAction.sceneId
            : studio.pendingAction?.action === "inspect" &&
                studio.pendingAction.subject.kind === "scene"
              ? studio.pendingAction.subject.sceneId
              : null;
    const actionSceneIndex = actionSceneId
        ? (studio.project?.scenes.findIndex((scene) => scene.id === actionSceneId) ?? -1)
        : -1;
    const actionVersionId =
        studio.pendingAction?.action === "inspect" && studio.pendingAction.subject.kind === "scene"
            ? studio.pendingAction.subject.versionId
            : null;
    const actionVersionIndex = actionVersionId
        ? (studio.project?.scenes[actionSceneIndex]?.versions.findIndex(
              (version) => version.id === actionVersionId,
          ) ?? -1)
        : -1;
    const heading = useRef<HTMLHeadingElement>(null);
    const [attemptedInputs, setAttemptedInputs] = useState(false);
    const [evidenceTarget, setEvidenceTarget] = useState<InspectionSeekTarget | null>(null);
    const [evidenceError, setEvidenceError] = useState<string | null>(null);
    const evidenceTrigger = useRef<HTMLElement | null>(null);
    const inspectionDetails = useRef<HTMLDetailsElement>(null);
    const projectDetails = useRef<HTMLDetailsElement>(null);
    function seekEvidence(evidence: SmartRemakeInspectionEvidence) {
        const resolved = resolveInspectionEvidence(
            evidence,
            studio.project?.inspectionMedia ?? [],
            studio.project?.inspectionMappings ?? [],
            evidence.timebase === "scene_local" ? "raw_group" : undefined,
        );
        if (!resolved) {
            setEvidenceError(
                "Bằng chứng chưa có media đúng hash và timebase, hoặc liên kết đã hết hạn. Làm mới dự án để kiểm tra.",
            );
            return;
        }
        document.querySelectorAll("video").forEach((video) => video.pause());
        evidenceTrigger.current =
            document.activeElement instanceof HTMLElement ? document.activeElement : null;
        setEvidenceError(null);
        setEvidenceTarget(resolved);
    }
    const inputProps = {
        requirements: studio.requirements,
        rights: studio.rights,
        budget: studio.budget,
        characterFile: studio.characterFile,
        characterUrl: studio.characterUrl,
        onRequirementsChange: studio.onRequirementsChange,
        onRightsChange: studio.onRightsChange,
        onBudgetChange: studio.onBudgetChange,
        onCharacterChange: studio.onCharacterChange,
        disabled: controlsLocked,
        onRightsConfirmationOpen: () =>
            void studio.requestAction(studio.compiled ? "reanalyze" : "analyze"),
    };
    const requirementsDetails = (
        <details className="rounded-2xl bg-surface p-4">
            <summary className="min-h-11 cursor-pointer py-3 font-medium">Yêu cầu bổ sung</summary>
            <RemakeProjectInputs {...inputProps} presentation="details" />
            {studio.contextDirty && (
                <p className="my-3 text-sm text-warn" role="status">
                    Yêu cầu mới sẽ được lưu khi bạn xác nhận hành động tiếp theo.
                </p>
            )}
        </details>
    );
    const hasOutput = Boolean(
        studio.result ||
        studio.project?.generationRecovery ||
        studio.project?.pendingOperation ||
        studio.project?.scenes.some((scene) => scene.versions.length > 0),
    );
    const activeProductUrl =
        studio.project?.productImageUrl ?? studio.productUrls[studio.primaryIndex];
    const observedProduct = studio.project?.analysisProgress?.product;
    const previewCompile =
        studio.compiled &&
        studio.project &&
        studio.compiled.projectId === studio.project.id &&
        studio.compiled.revision === studio.project.revision &&
        studio.project.analysisProgress?.status === "completed" &&
        observedProduct &&
        Object.keys(studio.compiled.productLock ?? {}).length === 0
            ? {
                  ...studio.compiled,
                  productLock: {
                      productName: observedProduct.name,
                      mustPreserve: observedProduct.details,
                  },
              }
            : studio.compiled;
    const progress = analyzing || studio.busy === "generate";
    const analysisLoadingProps = {
        action:
            (directAnalysis ?? studio.pendingAction)?.action === "reanalyze"
                ? ("reanalyze" as const)
                : ("analyze" as const),
        phase:
            analyzing && !studio.analysisPreparing
                ? ("analyzing" as const)
                : ("preparing" as const),
        sourceUrl: studio.sourceUrl,
        productUrl: studio.productUrls[studio.primaryIndex] ?? studio.project?.productImageUrl,
        productUrls: studio.productUrls,
        primaryIndex: studio.primaryIndex,
        durationSeconds: studio.sourceDuration ?? undefined,
        progress: studio.analysisProgress,
        startedAt: studio.analysisStartedAt,
        statusError: studio.analysisStatusError,
        onCheckStatus: studio.canCheckAnalysisStatus ? studio.checkAnalysisStatus : undefined,
        checkingStatus: studio.checkingAnalysisStatus,
    };
    const invalidPrompts = studio.invalidPromptDraft;
    const groupingError = getRemakeProviderGroupingError(studio.compiled ?? studio.project);
    const needsPlanUpdate =
        Boolean(groupingError) ||
        (studio.compiled?.schemaVersion === 2 &&
            (studio.compiled.expectationsVersion !== 1 ||
                !/^[a-f0-9]{64}$/.test(studio.compiled.expectationsHash ?? "")));
    const updateBeforeRender =
        needsPlanUpdate || studio.sourcePlanDirty || studio.localMediaNeedsAnalysis;
    const nextAction = getRemakeResultNextAction({
        project: studio.project,
        needsPlanUpdate: Boolean(
            updateBeforeRender ||
            (studio.project?.requirements &&
                JSON.stringify(normalizeRemakeRequirements(studio.requirements)) !==
                    JSON.stringify(normalizeRemakeRequirements(studio.project.requirements))),
        ),
        busy: Boolean(studio.busy),
        receiptUncertain: studio.unresolvedRepairReceipt,
        candidate: studio.unreadRepairCandidate,
    });
    const generationRecoveryVisible = step === "result" && nextAction.kind === "retry_render";
    const videoProgress = getRemakeGenerationProgress(studio.project);
    const hasGeneratedClips = Boolean(
        studio.project?.scenes.some((scene) => scene.versions.some((version) => version.videoUrl)),
    );
    const generationProgressVisible = Boolean(
        step === "result" &&
        !generationRecoveryVisible &&
        videoProgress &&
        (studio.project?.generationProgress ||
            studio.project?.pendingOperation?.kind === "render" ||
            studio.project?.lastOperation?.kind === "render") &&
        (studio.project?.generationProgress?.status !== "completed" || !hasGeneratedClips),
    );
    const generationErrorExplained = Boolean(
        generationProgressVisible &&
        studio.errorCode &&
        studio.project?.generationProgress?.groups.some(
            (group) => group.errorCode === studio.errorCode,
        ),
    );
    const recoveryExplainsError = Boolean(
        generationRecoveryVisible &&
        studio.error &&
        studio.errorCode &&
        studio.errorCode === studio.project?.generationRecovery?.errorCode,
    );
    function revealDetails(target: HTMLDetailsElement | null, action: RemakeResultNextAction) {
        if (!target) return;
        let ancestor = target.parentElement;
        while (ancestor) {
            if (ancestor.tagName === "DETAILS") (ancestor as HTMLDetailsElement).open = true;
            ancestor = ancestor.parentElement;
        }
        target.open = true;
        const report = Array.from(
            target.querySelectorAll<HTMLElement>("[data-inspection-report-id]"),
        ).find((item) => item.dataset.inspectionReportId === action.reportId);
        const finding =
            report &&
            Array.from(report.querySelectorAll<HTMLElement>("[data-inspection-finding-id]")).find(
                (item) => item.dataset.inspectionFindingId === action.findingId,
            );
        const focus = finding ?? report ?? target.querySelector<HTMLElement>("summary");
        if (focus) {
            if (focus.tagName !== "SUMMARY") focus.tabIndex = -1;
            focus.focus();
            focus.scrollIntoView?.({ block: "center" });
        }
    }
    function viewGenerationInspection(reportId: string) {
        revealDetails(inspectionDetails.current, {
            kind: "findings",
            label: "Xem kết quả kiểm tra ảnh",
            reason: "",
            reportId,
        });
    }
    function performNextAction(action: RemakeResultNextAction) {
        switch (action.kind) {
            case "retry_render":
                void studio.requestAction("render");
                break;
            case "progress":
                revealDetails(projectDetails.current, action);
                void studio.refreshProject();
                break;
            case "update_plan":
                void studio.requestAction("reanalyze");
                break;
            case "candidate":
                void studio.viewRepairCandidate();
                break;
            case "scene":
                if (action.sceneId)
                    studio.navigateOutput(action.sceneId, action.view ?? "watch", action.versionId);
                break;
            case "compose":
                void studio.publish();
                break;
            case "inspect":
                if (action.assemblyId)
                    void studio.requestAction("inspect", {
                        subject: { kind: "assembly", assemblyId: action.assemblyId },
                    });
                break;
            case "findings":
                revealDetails(inspectionDetails.current, action);
                break;
            case "assembly_error":
                revealDetails(projectDetails.current, action);
                break;
            case "approve":
                if (action.assemblyId && action.reportId)
                    void studio.approve(action.assemblyId, action.reportId);
                break;
            case "export":
                if (action.assemblyId) void studio.exportAssembly(action.assemblyId);
                break;
        }
    }
    useEffect(() => {
        heading.current?.focus({ preventScroll: true });
    }, [step]);

    const title = analysisRecoveryVisible
        ? "Chưa cập nhật được kịch bản"
        : viewingSavedScript && step === "plan"
          ? "Kịch bản đã lưu"
          : step === "prepare"
            ? "Dùng cách quay của video mẫu cho sản phẩm của bạn"
            : step === "plan"
              ? "Duyệt kịch bản từ video mẫu"
              : "Video của bạn";
    const lead = analysisRecoveryVisible
        ? "Tư liệu đang chọn vẫn được giữ. Chọn bước tiếp theo bên dưới để tiếp tục."
        : viewingSavedScript && step === "plan"
          ? "Đang xem kịch bản trước lượt phân tích gần nhất. Yêu cầu vừa rồi chưa cập nhật bản này."
          : step === "prepare"
            ? "Thêm video mẫu và ảnh sản phẩm. AI dựa vào cách quay, hành động và nhịp của mẫu để soạn kịch bản cho bạn duyệt trước khi tạo video."
            : step === "plan"
              ? "AI đã phân tích video mẫu và soạn kịch bản cho sản phẩm của bạn. Xem lại từng cảnh rồi bấm tạo video."
              : generationRecoveryVisible || generationProgressVisible
                ? null
                : "Xem video, sửa cảnh cần thiết rồi hoàn thiện bản để tải về.";

    return (
        <AppShell
            footer={
                step !== "result" && !analysisRecoveryVisible ? (
                    <div className="remake-studio rounded-2xl bg-surface p-3 shadow-[0_-6px_24px_rgb(0_0_0/0.03)] sm:p-4">
                        <div className="flex flex-wrap items-center gap-3">
                            <div
                                id="smart-remake-prepare-status"
                                className="min-w-0 flex-1 basis-full text-xs text-text-secondary lg:basis-0"
                                aria-live="polite"
                            >
                                {studio.busy ? (
                                    <span className="flex items-center gap-2">
                                        <LoaderCircle className="size-4 animate-spin motion-reduce:animate-none" />
                                        {busyLabel(studio.busy)}
                                    </span>
                                ) : studio.submissionStatusError ? (
                                    studio.submissionStatusError
                                ) : studio.checkingSubmissionStatus ? (
                                    "Đang kiểm tra trạng thái yêu cầu đã gửi…"
                                ) : step === "prepare" ? (
                                    studio.sourceExcerptError && studio.sourceUrl ? (
                                        studio.sourceExcerptError
                                    ) : !studio.sourceUrl ? (
                                        "Thêm video mẫu để tiếp tục."
                                    ) : !studio.productUrls.length ? (
                                        "Thêm ảnh sản phẩm để tiếp tục."
                                    ) : studio.sourceCutsError ? (
                                        studio.sourceCutsError
                                    ) : studio.health.isError ? (
                                        "Chưa kết nối được dịch vụ Smart Remake. Bấm Kết nối lại để thử."
                                    ) : studio.health.data && !studio.health.data.enabled ? (
                                        "Smart Remake chưa được bật cho môi trường này."
                                    ) : studio.health.isPending ? (
                                        "Đang kiểm tra dịch vụ tạo video."
                                    ) : (
                                        `Phân tích toàn bộ video · Đầu ra ${studio.duration} giây`
                                    )
                                ) : step === "plan" ? (
                                    studio.sourceCutsError ? (
                                        studio.sourceCutsError
                                    ) : studio.sourcePlanDirty ? (
                                        "Mốc cắt hoặc nhóm cảnh đã thay đổi. Cập nhật kịch bản trước khi tạo nhé."
                                    ) : studio.generationSetupError ? (
                                        studio.generationSetupError
                                    ) : invalidPrompts ? (
                                        "Hướng dẫn tạo cảnh chưa hợp lệ. Kiểm tra mục nâng cao nếu đã chỉnh, hoặc phân tích lại video mẫu. Bản sửa prompt video tối đa 12.000 ký tự."
                                    ) : studio.hasDraftChanges ? (
                                        "Đã giữ thay đổi trong phiên này. Hệ thống sẽ dùng bản chỉnh khi tạo video."
                                    ) : (
                                        `${studio.compiled?.sourceSceneMap?.scenes.length ?? studio.compiled?.sceneMap.sceneCount} cảnh · ${getRenderTaskCount(studio.compiled?.renderPlan) || studio.compiled?.sceneMap.sceneCount} lượt tạo · Video hoàn chỉnh ${studio.duration} giây`
                                    )
                                ) : studio.project ? (
                                    `Bản đang dùng v${studio.project.revision} · ${studio.project.targetDuration} giây`
                                ) : studio.result?.isDemo ? (
                                    "Đây là video ví dụ, không phải kết quả AI vừa tạo."
                                ) : (
                                    "Chỉ tải được sau khi video hoàn tất."
                                )}
                            </div>
                            {step === "prepare" && (
                                <>
                                    <Button
                                        variant="ghost"
                                        disabled={controlsLocked}
                                        onClick={() => void studio.loadSample()}
                                        className="min-h-11"
                                    >
                                        Thử với tư liệu mẫu
                                    </Button>
                                    <Button
                                        className={primary}
                                        disabled={controlsLocked}
                                        aria-describedby="smart-remake-prepare-status"
                                        onClick={() => {
                                            if (
                                                studio.submissionStatusError ||
                                                studio.checkingSubmissionStatus
                                            ) {
                                                void studio.checkSubmissionStatus();
                                                return;
                                            }
                                            setAttemptedInputs(true);
                                            if (studio.project?.pendingOperation) {
                                                studio.setStep("result");
                                                void studio.refreshProject();
                                                return;
                                            }
                                            void studio.requestAction("analyze");
                                            const label =
                                                !studio.sourceUrl ||
                                                studio.sourceExcerptError ||
                                                studio.sourceReuploadRequired
                                                    ? "Chọn file video mẫu"
                                                    : !studio.productUrls.length
                                                      ? "Chọn ảnh sản phẩm"
                                                      : null;
                                            if (label)
                                                document
                                                    .querySelector<HTMLInputElement>(
                                                        `[aria-label="${label}"]`,
                                                    )
                                                    ?.closest("section")
                                                    ?.querySelector("button")
                                                    ?.focus();
                                        }}
                                    >
                                        {studio.submissionStatusError ||
                                        studio.checkingSubmissionStatus
                                            ? "Kiểm tra trạng thái"
                                            : studio.project?.pendingOperation
                                              ? "Xem tiến trình"
                                              : "Tạo kịch bản"}{" "}
                                        <ArrowRight />
                                    </Button>
                                </>
                            )}
                            {step === "plan" && (
                                <>
                                    <Button
                                        variant="ghost"
                                        disabled={controlsLocked}
                                        onClick={() => studio.setStep("prepare")}
                                    >
                                        <ChevronLeft /> Quay lại
                                    </Button>
                                    {studio.health.data?.mode === "fixture" && (
                                        <Button
                                            variant="ghost"
                                            disabled={controlsLocked}
                                            onClick={() => void studio.generate(true)}
                                        >
                                            Xem video ví dụ
                                        </Button>
                                    )}
                                    <Button
                                        className={primary}
                                        disabled={controlsLocked}
                                        onClick={() => {
                                            if (studio.project?.pendingOperation) {
                                                studio.setStep("result");
                                                void studio.refreshProject();
                                            } else
                                                void studio.requestAction(
                                                    updateBeforeRender ? "reanalyze" : "render",
                                                );
                                        }}
                                    >
                                        <Sparkles />{" "}
                                        {studio.project?.pendingOperation
                                            ? "Xem tiến trình"
                                            : updateBeforeRender
                                              ? "Cập nhật kịch bản"
                                              : `Tạo video · ${studio.compiled?.inputSummary.targetDuration} giây`}
                                    </Button>
                                </>
                            )}
                        </div>
                    </div>
                ) : undefined
            }
        >
            <div className="remake-studio space-y-6 pb-3">
                <RemakeJourney
                    step={step}
                    hasPlan={Boolean(studio.compiled) && !analysisRecoveryVisible}
                    hasResult={hasOutput}
                    busy={controlsLocked}
                    sourceUrl={studio.sourceUrl}
                    productUrl={studio.productUrls[studio.primaryIndex]}
                    outputUrl={studio.project?.finalVideoUrl || studio.result?.finalVideoUrl}
                    onChange={studio.setStep}
                />
                <div className="mx-auto w-full max-w-6xl space-y-6">
                    <header className="space-y-2">
                        <div className="flex flex-wrap items-center gap-3">
                            <p className="text-xs font-medium tracking-wide text-text-secondary">
                                SMART REMAKE
                            </p>
                            {studio.health.data?.mode === "fixture" && (
                                <span className="rounded-full bg-warn-soft px-2.5 py-1 text-xs text-warn">
                                    Chế độ kiểm thử · Không tạo video AI
                                </span>
                            )}
                        </div>
                        <div className="flex flex-wrap items-center justify-between gap-3">
                            <h1
                                ref={heading}
                                tabIndex={-1}
                                className="w-fit rounded text-2xl font-semibold tracking-tight text-text-primary outline-none sm:text-3xl"
                            >
                                {title}
                            </h1>
                            {step === "result" && (
                                <Button
                                    variant="ghost"
                                    disabled={controlsLocked}
                                    onClick={() => studio.setStep("prepare")}
                                >
                                    <Plus aria-hidden="true" /> Chỉnh tư liệu
                                </Button>
                            )}
                        </div>
                        {lead && (
                            <p className="max-w-2xl text-sm leading-relaxed text-text-secondary">
                                {lead}
                            </p>
                        )}
                    </header>
                    {studio.health.isError && (
                        <div
                            className="flex flex-wrap items-center gap-3 rounded-2xl bg-warn-soft p-4 text-sm text-warn"
                            role="alert"
                        >
                            <span>Chưa kết nối được dịch vụ Smart Remake.</span>
                            <Button variant="ghost" onClick={() => void studio.health.refetch()}>
                                <RefreshCw /> Kết nối lại
                            </Button>
                        </div>
                    )}
                    {studio.health.data && !studio.health.data.enabled && (
                        <div
                            className="rounded-2xl bg-warn-soft p-4 text-sm text-warn"
                            role="status"
                        >
                            Smart Remake chưa được bật cho môi trường này.
                        </div>
                    )}
                    {studio.submissionStatusError && (
                        <p role="status" className="rounded-2xl bg-warn-soft p-4 text-sm text-warn">
                            {studio.submissionStatusError}
                        </p>
                    )}
                    {studio.error &&
                        !generationErrorExplained &&
                        !recoveryExplainsError &&
                        !(
                            analysisErrorExplained &&
                            (analysisRecoveryVisible || viewingSavedScript)
                        ) && (
                            <div
                                className="rounded-2xl bg-destructive-soft p-4 text-sm text-destructive"
                                role="alert"
                            >
                                {studio.error}
                            </div>
                        )}
                    {analysisRecoveryVisible && studio.project && (
                        <RemakeAnalysisRecovery
                            project={studio.project}
                            busy={controlsLocked}
                            onRetry={() => void studio.requestAction("reanalyze")}
                            onCheckStatus={() => void studio.refreshProject()}
                            onViewSavedScript={
                                restoreTimelineCompile(studio.project)
                                    ? () => {
                                          setSavedScriptView(savedScriptIdentity);
                                          studio.viewSavedScript();
                                      }
                                    : undefined
                            }
                        />
                    )}
                    {studio.busy && step === "result" && (
                        <div
                            role="status"
                            className="flex items-center gap-3 rounded-2xl bg-primary-soft p-4 text-sm"
                        >
                            <LoaderCircle className="size-5 animate-spin text-primary motion-reduce:animate-none" />
                            {busyLabel(studio.busy)} Bản đang dùng vẫn được giữ.
                        </div>
                    )}
                    {analyzing ? (
                        <section
                            aria-label="Tiến trình phân tích video"
                            className="remake-enter mx-auto w-full max-w-4xl rounded-3xl bg-surface p-5 sm:p-8"
                        >
                            <RemakeAnalysisLoading
                                {...analysisLoadingProps}
                                presentation="inline"
                            />
                        </section>
                    ) : progress ? (
                        <RemakeProcessing
                            kind="generate"
                            sourceUrl={studio.sourceUrl}
                            productUrl={activeProductUrl}
                        />
                    ) : step === "prepare" ? (
                        <div className="remake-enter space-y-5">
                            <RemakeInputs
                                validationErrors={
                                    attemptedInputs
                                        ? {
                                              video: !studio.sourceUrl
                                                  ? "Thêm video mẫu để bắt đầu."
                                                  : (studio.sourceExcerptError ??
                                                    studio.sourceCutsError ??
                                                    (studio.sourceReuploadRequired
                                                        ? "Thêm lại video mẫu để tạo kịch bản với thời lượng mới."
                                                        : undefined)),
                                              product: !studio.productUrls.length
                                                  ? "Thêm ảnh sản phẩm để tiếp tục."
                                                  : undefined,
                                          }
                                        : undefined
                                }
                                sourceUrl={studio.sourceUrl}
                                sourceName={studio.video?.name ?? null}
                                productUrls={studio.productUrls}
                                primaryIndex={studio.primaryIndex}
                                onPrimaryChange={studio.onPrimaryChange}
                                onVideo={studio.onVideo}
                                onImages={studio.onImages}
                                onRemoveImage={studio.onRemoveImage}
                                link={studio.link}
                                onLinkChange={studio.onLinkChange}
                                onLinkSubmit={() => void studio.importLink()}
                                isLinkLoading={studio.busy === "link"}
                                linkedTitle={studio.linkedProduct?.title}
                                duration={studio.duration}
                                timelineStartFrame={studio.timelineStartFrame}
                                onTimelineStartFrameChange={studio.onTimelineStartFrameChange}
                                onSourceMetadata={studio.onSourceMetadata}
                                sourceDurationSeconds={studio.sourceDuration}
                                sourceCutFrames={
                                    studio.compiled?.sourceSceneMap?.timingMode === "fit_target" ||
                                    !studio.compiled
                                        ? studio.sourceCutFrames
                                        : undefined
                                }
                                onSourceCutFramesChange={studio.onSourceCutFramesChange}
                                onDuration={studio.onDuration}
                                language={studio.language}
                                onLanguage={studio.onLanguage}
                                description={studio.description}
                                onDescription={studio.onDescription}
                                brief={studio.brief}
                                onBrief={studio.onBrief}
                                disabled={controlsLocked}
                                isSample={studio.isSample}
                            />
                            <details
                                id="smart-remake-intake"
                                className="mx-auto max-w-4xl rounded-2xl bg-surface p-4"
                            >
                                <summary className="min-h-11 cursor-pointer py-3 text-sm font-medium">
                                    Yêu cầu bổ sung{" "}
                                    <span className="font-normal text-text-secondary">
                                        · Không bắt buộc
                                    </span>
                                </summary>
                                <RemakeProjectInputs {...inputProps} presentation="details" />
                            </details>
                        </div>
                    ) : step === "plan" && studio.compiled ? (
                        <div className="remake-enter space-y-4">
                            {viewingSavedScript && (
                                <div
                                    role="status"
                                    className="flex flex-wrap items-center justify-between gap-3 rounded-2xl bg-surface p-4 text-sm"
                                >
                                    <p>Kịch bản đã lưu trước lượt phân tích gần nhất.</p>
                                    <Button
                                        variant="ghost"
                                        onClick={() => {
                                            setSavedScriptView(null);
                                            studio.setStep("prepare");
                                        }}
                                    >
                                        Quay lại xử lý phân tích
                                    </Button>
                                </div>
                            )}
                            {needsPlanUpdate && (
                                <div role="status" className="space-y-3 rounded-2xl bg-surface p-5">
                                    <p className="text-sm text-text-secondary">
                                        {groupingError ??
                                            "Kịch bản này cần cập nhật để bước tạo ảnh, tạo video và kiểm tra dùng cùng thông tin sản phẩm và từng cảnh."}
                                    </p>
                                    <Button
                                        disabled={Boolean(
                                            studio.busy || studio.project?.pendingOperation,
                                        )}
                                        onClick={() => void studio.requestAction("reanalyze")}
                                    >
                                        Cập nhật kịch bản
                                    </Button>
                                </div>
                            )}
                            <RemakeStoryboard
                                compileResult={previewCompile ?? studio.compiled}
                                referenceUrl={studio.sourceUrl}
                                productUrl={studio.productUrls[studio.primaryIndex]}
                                onSceneChange={studio.onSceneChange}
                                sourceCutFrames={studio.sourceCutFrames}
                                onSourceCutFramesChange={studio.onSourceCutFramesChange}
                                onRecompile={() => void studio.requestAction("reanalyze")}
                                renderGroupBreaks={studio.renderGroupBreaks}
                                onRenderGroupBreaksChange={studio.onRenderGroupBreaksChange}
                                sourcePlanDirty={studio.sourcePlanDirty}
                                sourceCutsDirty={studio.sourceCutsDirty}
                                sourceCutsError={studio.sourceCutsError}
                                isRecompiling={studio.busy === "analyze"}
                                disabled={controlsLocked}
                            />
                            {studio.compiled.warnings.length > 0 && (
                                <details className="rounded-2xl bg-surface p-4 text-sm">
                                    <summary className="cursor-pointer text-text-secondary">
                                        Lưu ý từ bước phân tích ({studio.compiled.warnings.length})
                                    </summary>
                                    <ul className="mt-3 list-disc space-y-2 pl-5 text-text-secondary">
                                        {studio.compiled.warnings.map((warning) => (
                                            <li key={warning}>{warning}</li>
                                        ))}
                                    </ul>
                                </details>
                            )}
                        </div>
                    ) : step === "result" ? (
                        <div className="space-y-5">
                            {!generationProgressVisible && (
                                <RemakeResultNextStep
                                    action={nextAction}
                                    budget={studio.project?.budget}
                                    technicalError={recoveryExplainsError ? studio.error : null}
                                    onViewScript={
                                        studio.compiled ? () => studio.setStep("plan") : undefined
                                    }
                                    busy={controlsLocked && nextAction.kind !== "progress"}
                                    onAction={performNextAction}
                                    onDismissCandidate={() => void studio.dismissRepairCandidate()}
                                />
                            )}
                            {generationProgressVisible && studio.project && (
                                <RemakeGenerationProgress
                                    project={studio.project}
                                    busy={controlsLocked}
                                    onCheckStatus={() => void studio.refreshProject()}
                                    onViewInspection={viewGenerationInspection}
                                    onViewScript={() => studio.viewSavedScript()}
                                />
                            )}
                            {studio.repairReceiptError && (
                                <p role="alert" className="text-sm text-warn">
                                    {studio.repairReceiptError}
                                </p>
                            )}
                            {!generationProgressVisible && (
                                <RemakeOutput
                                    key={
                                        studio.project?.id ??
                                        studio.result?.finalVideoUrl ??
                                        "pending"
                                    }
                                    workspaceId={workspaceId}
                                    project={studio.project}
                                    result={studio.result}
                                    productUrl={activeProductUrl}
                                    busy={controlsLocked}
                                    onRepair={async (sceneId, repairIntent) => {
                                        await studio.requestAction("repair", {
                                            sceneId,
                                            repairIntent,
                                        });
                                        return null;
                                    }}
                                    guided
                                    generationRecoveryVisible={generationRecoveryVisible}
                                    repairCandidate={studio.unreadRepairCandidate}
                                    navigation={studio.outputNavigation}
                                    initialSceneId={studio.selectedSceneId}
                                    onSceneChange={studio.onOutputSceneChange}
                                    repairDrafts={studio.repairDrafts}
                                    repairFailures={studio.repairFailures}
                                    onRepairDraftChange={studio.onRepairDraftChange}
                                    repairDraftSaveStatus="Yêu cầu sửa đang được giữ trong phiên này"
                                    onAccept={studio.accept}
                                    onRefresh={() => void studio.refreshProject()}
                                    onViewGenerationInspection={viewGenerationInspection}
                                    onTimelineSave={studio.saveTimeline}
                                    onPublish={studio.publish}
                                    savingTimeline={studio.busy === "timeline"}
                                    publishing={
                                        studio.busy === "compose" ||
                                        studio.project?.pendingOperation?.kind === "compose"
                                    }
                                />
                            )}
                        </div>
                    ) : (
                        <div className="rounded-3xl bg-surface p-8 text-sm text-text-secondary">
                            Thêm tư liệu và phân tích video để xem kịch bản nhé.
                        </div>
                    )}
                    {studio.project && step === "plan" && requirementsDetails}
                    {studio.project && step === "result" && (
                        <details className="text-sm text-text-secondary">
                            <summary className="min-h-11 w-fit cursor-pointer rounded-lg py-3 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
                                Tùy chọn và thông tin
                            </summary>
                            <div className="mt-2 space-y-3 rounded-2xl bg-surface p-2">
                                {requirementsDetails}
                                <details
                                    ref={inspectionDetails}
                                    className="rounded-2xl bg-surface p-4"
                                >
                                    <summary className="min-h-11 cursor-pointer py-3 font-medium focus-visible:ring-2 focus-visible:ring-ring">
                                        Kiểm tra và bằng chứng
                                    </summary>
                                    <RemakeInspector
                                        project={studio.project}
                                        busy={controlsLocked}
                                        onInspect={async (subject) => {
                                            await studio.requestAction("inspect", { subject });
                                        }}
                                        onReview={studio.review}
                                        onSeek={seekEvidence}
                                    />
                                </details>
                                <details
                                    ref={projectDetails}
                                    className="rounded-2xl bg-surface p-4"
                                >
                                    <summary className="min-h-11 cursor-pointer py-3 font-medium focus-visible:ring-2 focus-visible:ring-ring">
                                        Tiến trình, quyền và thông tin dự án
                                    </summary>
                                    <RemakeProjectControls
                                        project={studio.project}
                                        busy={controlsLocked}
                                        onApprove={studio.approve}
                                        onExport={studio.exportAssembly}
                                        onRestore={studio.restore}
                                        onDelete={studio.deleteProject}
                                        onRightsReview={studio.rightsReview}
                                    />
                                </details>
                            </div>
                        </details>
                    )}
                    {evidenceError && (
                        <p role="alert" className="rounded-2xl bg-warn-soft p-4 text-sm text-warn">
                            {evidenceError}
                        </p>
                    )}
                    <Dialog
                        open={Boolean(evidenceTarget)}
                        onOpenChange={(open) => {
                            if (!open) setEvidenceTarget(null);
                        }}
                    >
                        <DialogContent
                            className="max-w-3xl motion-reduce:animate-none"
                            onCloseAutoFocus={(event) => {
                                event.preventDefault();
                                evidenceTrigger.current?.focus();
                            }}
                        >
                            <DialogTitle>Bằng chứng kiểm tra</DialogTitle>
                            <DialogDescription>
                                Media gốc của bằng chứng · {evidenceTarget?.timebase} · Nhấn Escape
                                để quay lại kết quả.
                            </DialogDescription>
                            {evidenceTarget?.kind === "image" ? (
                                <img
                                    className="mx-auto max-h-[60dvh] max-w-full object-contain"
                                    src={evidenceTarget.url}
                                    alt="Ảnh bằng chứng đã xác minh hash"
                                />
                            ) : (
                                evidenceTarget && (
                                    <RemakePlayer
                                        url={evidenceTarget.url}
                                        scope={{
                                            start: evidenceTarget.startSecond!,
                                            end: evidenceTarget.endSecond!,
                                        }}
                                        versionLabel="Bằng chứng"
                                    />
                                )
                            )}
                        </DialogContent>
                    </Dialog>
                    <Dialog open={Boolean(directAnalysis) && !analyzing}>
                        <DialogContent
                            className="max-w-3xl rounded-3xl p-5 sm:p-7"
                            showCloseButton={false}
                            onEscapeKeyDown={(event) => event.preventDefault()}
                            onPointerDownOutside={(event) => event.preventDefault()}
                            onCloseAutoFocus={(event) => {
                                if (analyzing) event.preventDefault();
                            }}
                        >
                            {directAnalysis && <RemakeAnalysisLoading {...analysisLoadingProps} />}
                        </DialogContent>
                    </Dialog>
                    <RemakeActionConfirmation
                        intent={studio.pendingAction ?? null}
                        preflight={studio.actionPreflight ?? null}
                        snapshot={{
                            requirements: studio.requirements,
                            rights: studio.rights,
                            budget: studio.budget,
                        }}
                        loading={studio.actionLoading ?? false}
                        submitting={studio.actionSubmitting ?? false}
                        analysisPhase={studio.busy === "analyze" ? "analyzing" : "preparing"}
                        analysisInFlight={analyzing}
                        analysisProgress={studio.analysisProgress}
                        analysisStartedAt={studio.analysisStartedAt}
                        analysisStatusError={studio.analysisStatusError}
                        checkingAnalysisStatus={studio.checkingAnalysisStatus}
                        onCheckAnalysisStatus={
                            studio.canCheckAnalysisStatus ? studio.checkAnalysisStatus : undefined
                        }
                        sourceUrl={studio.sourceUrl}
                        error={studio.actionError ?? null}
                        errorCode={studio.actionErrorCode ?? null}
                        hasCharacter={Boolean(studio.characterFile || studio.characterUrl)}
                        productUrl={analysisLoadingProps.productUrl}
                        productUrls={studio.productUrls}
                        primaryIndex={studio.primaryIndex}
                        sceneNumber={
                            actionSceneIndex >= 0
                                ? studio.project!.scenes[actionSceneIndex].index + 1
                                : undefined
                        }
                        sceneLabel={
                            studio.project && actionSceneId
                                ? getRemakeSceneLabel(
                                      studio.project,
                                      actionSceneId,
                                      actionSceneIndex,
                                  )
                                : undefined
                        }
                        versionNumber={actionVersionIndex >= 0 ? actionVersionIndex + 1 : undefined}
                        onConfirm={studio.confirmAction}
                        onCancel={studio.cancelAction}
                        onRetry={() => {
                            if (
                                studio.actionPreflight?.blockers.some(
                                    (item) =>
                                        item.action === "reconcile" || item.action === "refresh",
                                )
                            ) {
                                studio.cancelAction();
                                studio.setStep("result");
                                void studio.refreshProject();
                            } else void studio.retryAction();
                        }}
                    />
                    {studio.notice && !generationProgressVisible && (
                        <p
                            role="status"
                            aria-live="polite"
                            className="flex items-start gap-2 text-xs leading-relaxed text-text-secondary"
                        >
                            <Check className="mt-0.5 size-3.5 shrink-0" aria-hidden="true" />
                            {studio.notice}
                        </p>
                    )}
                </div>
            </div>
        </AppShell>
    );
}

function busyLabel(kind: string) {
    return (
        (
            {
                analyze: "Đang phân tích video mẫu…",
                generate: "Đang tạo video cho bạn…",
                repair: "Đang tạo lại cảnh đã chọn…",
                compose: "Đang ghép video…",
                restore: "Đang mở các phiên bản…",
                sample: "Đang thêm tư liệu mẫu…",
                link: "Đang lấy thông tin sản phẩm…",
                timeline: "Đang lưu đoạn đã chọn…",
                context: "Đang lưu yêu cầu và quyền…",
                inspect: "Đang gửi yêu cầu kiểm tra…",
                review: "Đang lưu quyết định xem xét…",
                approve: "Đang duyệt thành phẩm…",
                export: "Đang kiểm tra và cấp bản xuất…",
                delete: "Đang ngừng dùng hoặc xóa tư liệu…",
            } as Record<string, string>
        )[kind] ?? "Đang xử lý…"
    );
}
