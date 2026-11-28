import { useRef, useState, type RefObject } from "react";
import { ExternalLink, LoaderCircle, ShieldCheck, Sparkles } from "lucide-react";
import type { SmartRemakeAnalysisProgress, SmartRemakePreflight } from "@/shared/api/smart-remake";
import { Button } from "@/shared/ui/button";
import { Input } from "@/shared/ui/input";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/shared/ui/dialog";
import {
    MEDIA_RIGHTS_ATTESTATION_TEXT,
    MEDIA_RIGHTS_POLICY_PATH,
} from "@/features/policies/media-rights-policy";
import { type RemakeActionIntent, type RemakeActionSnapshot } from "../lib/remake-action";
import {
    confirmRemakeMediaRights,
    getRemakeRightsError,
    hasCurrentRemakeRightsAttestation,
} from "../lib/remake-intake";
import { RemakeAnalysisLoading } from "./remake-analysis-loading";

interface Props {
    intent: RemakeActionIntent | null;
    preflight: SmartRemakePreflight | null;
    snapshot: RemakeActionSnapshot;
    loading: boolean;
    submitting: boolean;
    error: string | null;
    errorCode?: string | null;
    hasCharacter?: boolean;
    productUrl?: string | null;
    productUrls?: string[];
    primaryIndex?: number;
    sourceUrl?: string | null;
    analysisPhase?: "preparing" | "analyzing";
    analysisInFlight?: boolean;
    analysisProgress?: SmartRemakeAnalysisProgress | null;
    analysisStartedAt?: number;
    analysisStatusError?: string | null;
    checkingAnalysisStatus?: boolean;
    onCheckAnalysisStatus?(): void;
    sceneNumber?: number;
    sceneLabel?: string;
    versionNumber?: number;
    onConfirm(snapshot: RemakeActionSnapshot, preflight: SmartRemakePreflight): Promise<unknown>;
    onCancel(): void;
    onRetry(): void;
}

const actions = {
    analyze: {
        title: "Tạo kịch bản cho sản phẩm này?",
        confirm: "Xác nhận và tạo kịch bản",
        description:
            "AI phân tích cách quay, hành động và nhịp của video mẫu để soạn kịch bản cho sản phẩm của bạn. Bước này chưa tạo video.",
    },
    reanalyze: {
        title: "Cập nhật kịch bản?",
        confirm: "Xác nhận và cập nhật kịch bản",
        description:
            "AI phân tích lại tư liệu và yêu cầu hiện tại. Bạn sẽ duyệt kịch bản mới trước khi tạo video.",
    },
    render: {
        title: "Tạo video theo kịch bản này?",
        confirm: "Xác nhận và tạo video",
        description:
            "AI tạo ảnh tham chiếu, kiểm tra ảnh rồi tạo các clip theo kịch bản đã duyệt. Bạn sẽ xem và hoàn thiện video ở bước tiếp theo.",
    },
    repair: {
        title: "Tạo lại cảnh đã chọn?",
        confirm: "Xác nhận và tạo lại cảnh",
        description:
            "AI tạo một phương án mới cho clip đã chọn. Các clip khác và bản đang dùng được giữ lại để bạn so sánh.",
    },
    inspect: {
        title: "Kiểm tra nội dung bằng AI?",
        confirm: "Xác nhận và kiểm tra",
        description:
            "AI đối chiếu đúng tư liệu hoặc phiên bản đã chọn với sản phẩm và yêu cầu từng cảnh. Bạn xem bằng chứng trước khi duyệt.",
    },
} as const;
const inputErrorCodes = new Set([
    "SMART_REMAKE_TIMELINE_SCENE_LIMIT",
    "SMART_REMAKE_TIMELINE_CUTS_INVALID",
    "SMART_REMAKE_TIMELINE_SCENE_TOO_LONG",
    "SMART_REMAKE_TIMELINE_DENSITY_UNSUPPORTED",
    "SMART_REMAKE_OUTPUT_DENSITY_UNSUPPORTED",
    "SMART_REMAKE_PROVIDER_PROMPT_TOO_LARGE",
    "SMART_REMAKE_PROVIDER_PLAN_UPDATE_REQUIRED",
    "SMART_REMAKE_SOURCE_ANALYSIS_INCOMPLETE",
    "SMART_REMAKE_SOURCE_ANALYSIS_UNSUPPORTED",
    "SMART_REMAKE_SOURCE_UNSUPPORTED",
    "SMART_REMAKE_SOURCE_RANGE_INVALID",
    "SMART_REMAKE_PRODUCT_ANALYSIS_INCOMPLETE",
]);

export function RemakeActionConfirmation(props: Props) {
    const closeGuard = useRef(false);
    const inlineAnalysis =
        props.analysisInFlight &&
        (props.intent?.action === "analyze" || props.intent?.action === "reanalyze");
    return (
        <Dialog
            open={Boolean(props.intent) && !inlineAnalysis}
            onOpenChange={(open) => {
                if (!open && !props.submitting && !closeGuard.current) props.onCancel();
            }}
        >
            {props.intent && (
                <ActionContent
                    key={props.intent.fingerprint}
                    {...props}
                    intent={props.intent}
                    closeGuard={closeGuard}
                />
            )}
        </Dialog>
    );
}

function ActionContent(
    props: Props & { intent: RemakeActionIntent; closeGuard: RefObject<boolean> },
) {
    const { intent, preflight, snapshot, loading, submitting, error } = props;
    const trigger = useRef<HTMLElement | null>(null);
    const submitLock = useRef(false);
    const [sending, setSending] = useState(false);
    const [localError, setLocalError] = useState<string | null>(null);
    const [accepted, setAccepted] = useState(false);
    const [disclosed, setDisclosed] = useState(false);
    const [characterConsented, setCharacterConsented] = useState(
        Boolean(
            snapshot.rights.characterConsent?.consented &&
            !snapshot.rights.characterConsent.revoked,
        ),
    );
    const [characterScope, setCharacterScope] = useState(
        snapshot.rights.characterConsent?.scope ?? "",
    );
    const [characterEvidence, setCharacterEvidence] = useState(
        snapshot.rights.characterConsent?.evidenceNote ?? "",
    );
    const existingRights =
        hasCurrentRemakeRightsAttestation(snapshot.rights) ||
        (!snapshot.rights.attestation &&
            snapshot.rights.providerDisclosureAcknowledged &&
            [snapshot.rights.source, snapshot.rights.product].every(
                (item) =>
                    item.basis !== "attested" &&
                    item.declared &&
                    !item.revoked &&
                    item.scope.trim() &&
                    item.evidenceNote.trim(),
            ));
    let confirmedRights = existingRights
        ? snapshot.rights
        : accepted && disclosed
          ? confirmRemakeMediaRights(snapshot.rights)
          : snapshot.rights;
    if (snapshot.requirements.requiresCharacter) {
        confirmedRights = {
            ...confirmedRights,
            character: {
                ...snapshot.rights.character,
                basis: snapshot.rights.character?.basis ?? "permission",
                declared: characterConsented,
                revoked: false,
                scope: characterScope,
                evidenceNote: characterEvidence,
            },
            characterConsent: {
                consented: characterConsented,
                revoked: false,
                scope: characterScope,
                evidenceNote: characterEvidence,
            },
        };
    }
    const intakeError =
        existingRights || (accepted && disclosed)
            ? getRemakeRightsError(
                  snapshot.requirements,
                  confirmedRights,
                  Boolean(props.hasCharacter),
              )
            : null;
    const locked = submitting || sending;
    const analysisPending =
        locked && (intent.action === "analyze" || intent.action === "reanalyze");
    const fullSourceAnalysis =
        preflight?.scope.analysisScope === "full_source" &&
        (intent.action === "analyze" || intent.action === "reanalyze");
    const analysisDuration = fullSourceAnalysis
        ? preflight.scope.sourceStartFrame != null && preflight.scope.sourceEndFrame != null
            ? Number(
                  (
                      (preflight.scope.sourceEndFrame - preflight.scope.sourceStartFrame) /
                      24
                  ).toFixed(3),
              )
            : undefined
        : preflight?.scope.targetDuration;
    const needsInputUpdate =
        (Boolean(error) && inputErrorCodes.has(props.errorCode ?? "")) ||
        Boolean(preflight?.blockers.some((blocker) => inputErrorCodes.has(blocker.code)));
    const cannotConfirm =
        locked ||
        loading ||
        needsInputUpdate ||
        !preflight ||
        Boolean(preflight.blockers.length) ||
        Boolean(intakeError) ||
        (!existingRights && (!accepted || !disclosed));
    const copy = actions[intent.action];
    const groupedRepair = intent.action === "repair" && intent.repairScope === "provider_group";
    async function confirm() {
        if (submitLock.current || cannotConfirm || !preflight) return;
        submitLock.current = true;
        props.closeGuard.current = true;
        setSending(true);
        setLocalError(null);
        try {
            await props.onConfirm(
                { ...snapshot, rights: confirmedRights, budget: { mode: "unlimited" } },
                preflight,
            );
        } catch {
            setLocalError(
                "Chưa gửi được yêu cầu. Tư liệu vẫn được giữ; kiểm tra trạng thái trước khi thử lại.",
            );
        } finally {
            submitLock.current = false;
            props.closeGuard.current = false;
            setSending(false);
        }
    }
    return (
        <DialogContent
            className={`${analysisPending ? "max-w-3xl" : "max-w-xl"} gap-5 rounded-3xl p-5 sm:p-7 motion-reduce:animate-none`}
            showCloseButton={!analysisPending}
            onOpenAutoFocus={() => {
                trigger.current =
                    document.activeElement instanceof HTMLElement ? document.activeElement : null;
            }}
            onCloseAutoFocus={(event) => {
                if (props.analysisInFlight) {
                    event.preventDefault();
                    return;
                }
                if (trigger.current?.isConnected) {
                    event.preventDefault();
                    trigger.current.focus();
                }
            }}
            onEscapeKeyDown={(event) => {
                if (locked) event.preventDefault();
            }}
            onPointerDownOutside={(event) => {
                if (locked) event.preventDefault();
            }}
        >
            {analysisPending && (intent.action === "analyze" || intent.action === "reanalyze") ? (
                <RemakeAnalysisLoading
                    action={intent.action}
                    phase={props.analysisPhase}
                    productUrl={props.productUrl}
                    productUrls={props.productUrls}
                    primaryIndex={props.primaryIndex}
                    sourceUrl={props.sourceUrl}
                    durationSeconds={analysisDuration}
                    progress={props.analysisProgress}
                    startedAt={props.analysisStartedAt}
                    statusError={props.analysisStatusError}
                    onCheckStatus={props.onCheckAnalysisStatus}
                    checkingStatus={props.checkingAnalysisStatus}
                />
            ) : (
                <>
                    <div className="flex size-11 items-center justify-center rounded-2xl bg-primary-soft text-primary">
                        <Sparkles className="size-6" aria-hidden="true" />
                    </div>
                    <div className="space-y-2 pr-5">
                        <DialogTitle className="text-xl leading-snug">
                            {intent.action === "repair" && (props.sceneLabel || props.sceneNumber)
                                ? `Tạo lại ${props.sceneLabel?.toLowerCase() ?? `cảnh ${props.sceneNumber}`}?`
                                : copy.title}
                        </DialogTitle>
                        <DialogDescription className="leading-relaxed text-text-secondary">
                            {groupedRepair
                                ? "AI kiểm tra yêu cầu sửa, tạo hai ảnh đầu/cuối rồi tạo lại toàn bộ clip đã chọn bằng 1 lượt Wan. Clip còn lại và bản đang dùng được giữ nguyên để bạn so sánh."
                                : intent.action === "repair" &&
                                    "repairIntent" in intent &&
                                    intent.repairIntent
                                  ? "Một lượt AI kiểm tra yêu cầu sửa với sản phẩm và ý định cảnh trước khi tạo ảnh và video. Nếu yêu cầu mâu thuẫn hoặc thiếu căn cứ, hệ thống dừng ở bước kiểm tra; phí đã phát sinh vẫn được ghi nhận. Các cảnh khác và bản đang dùng được giữ lại."
                                  : copy.description}
                        </DialogDescription>
                    </div>
                    {intent.startsNewProject && (
                        <p className="rounded-xl bg-surface-soft p-3 text-sm text-text-secondary">
                            Sẽ tạo dự án mới cho bộ tư liệu và thời lượng này. Dự án trước vẫn được
                            giữ.
                        </p>
                    )}
                    {preflight && (
                        <div className="flex items-center gap-3 rounded-2xl bg-surface-soft p-3 text-sm">
                            {props.productUrl && (
                                <img
                                    src={props.productUrl}
                                    alt="Sản phẩm sẽ dùng"
                                    className="size-14 rounded-xl bg-surface object-contain"
                                />
                            )}
                            <div className="min-w-0 space-y-1">
                                {(props.sceneLabel || props.sceneNumber) && (
                                    <p className="text-xs font-medium text-text-secondary">
                                        {props.sceneLabel ?? `Cảnh ${props.sceneNumber}`}
                                        {props.versionNumber ? ` · Bản ${props.versionNumber}` : ""}
                                    </p>
                                )}
                                <p className="font-medium">
                                    {intent.action === "inspect" && intent.subject.kind === "image"
                                        ? intent.subject.imageRole === "character"
                                            ? "Ảnh nhân vật đã chọn"
                                            : "Ảnh sản phẩm đã chọn"
                                        : intent.action === "inspect" &&
                                            intent.subject.kind === "scene"
                                          ? "Clip đã chọn và chuyển cảnh"
                                          : intent.action === "repair"
                                            ? `Clip tạo lại ${preflight.scope.targetDuration} giây`
                                            : fullSourceAnalysis
                                              ? `${preflight.scope.targetDuration} giây đầu ra · Video dọc 9:16`
                                              : `${preflight.scope.targetDuration} giây · Video dọc 9:16`}
                                </p>
                                {preflight.scope.sourceStartFrame != null &&
                                    preflight.scope.sourceEndFrame != null &&
                                    intent.action !== "inspect" &&
                                    intent.action !== "repair" && (
                                        <p className="text-xs text-text-secondary">
                                            {fullSourceAnalysis
                                                ? "Phân tích toàn bộ video mẫu · "
                                                : "Đoạn mẫu "}
                                            {Number(
                                                (preflight.scope.sourceStartFrame / 24).toFixed(3),
                                            )}
                                            –
                                            {Number(
                                                (preflight.scope.sourceEndFrame / 24).toFixed(3),
                                            )}{" "}
                                            giây
                                        </p>
                                    )}
                                <p className="text-xs text-text-secondary">
                                    {intent.action === "inspect" && intent.subject.kind === "scene"
                                        ? `${preflight.calls.inspection} lượt kiểm tra${preflight.calls.inspection > 1 ? " · Gồm cửa sổ giáp cảnh" : ""}`
                                        : fullSourceAnalysis
                                          ? `Tất cả cảnh từ video mẫu được phân bổ vào kịch bản ${preflight.scope.targetDuration} giây`
                                          : preflight.scope.sceneCount > 0
                                            ? `${preflight.scope.sceneCount} cảnh`
                                            : "Kịch bản từ đoạn mẫu đã chọn"}
                                    {intent.action === "repair"
                                        ? " · Chỉ clip đã chọn được tạo lại"
                                        : ""}
                                </p>
                            </div>
                        </div>
                    )}
                    {loading && (
                        <p role="status" className="flex items-center gap-2 text-sm">
                            <LoaderCircle className="size-4 animate-spin motion-reduce:animate-none" />{" "}
                            Đang kiểm tra tư liệu và phạm vi…
                        </p>
                    )}
                    {(error || localError) && (
                        <p role="alert" className="rounded-xl bg-warn-soft p-3 text-sm text-warn">
                            {error || localError}
                        </p>
                    )}
                    {preflight?.blockers.map((blocker) => (
                        <p
                            key={blocker.code}
                            role="alert"
                            className="rounded-xl bg-warn-soft p-3 text-sm text-warn"
                        >
                            {blocker.message}
                        </p>
                    ))}
                    {!loading && needsInputUpdate && (
                        <p className="text-sm leading-relaxed text-text-secondary">
                            Quay lại để cập nhật tư liệu hoặc kịch bản.
                        </p>
                    )}
                    {!loading &&
                        !needsInputUpdate &&
                        (error || !preflight || Boolean(preflight.blockers.length)) && (
                            <Button
                                variant="outline"
                                className="min-h-11"
                                onClick={props.onRetry}
                                disabled={locked}
                            >
                                {preflight?.blockers.some(
                                    (item) =>
                                        item.action === "reconcile" || item.action === "refresh",
                                )
                                    ? "Kiểm tra trạng thái"
                                    : "Kết nối lại"}
                            </Button>
                        )}
                    {preflight && preflight.mode !== "live" && (
                        <p className="text-xs text-warn">Chế độ kiểm thử · Không gọi AI trả phí.</p>
                    )}
                    <section
                        className="space-y-3 text-sm"
                        aria-label="Quyền sử dụng và xử lý tư liệu"
                    >
                        {existingRights ? (
                            <p className="flex items-center gap-2 text-xs text-text-secondary">
                                <ShieldCheck
                                    className="size-4 shrink-0 text-ok"
                                    aria-hidden="true"
                                />{" "}
                                Đã xác nhận quyền với bộ tư liệu này.
                            </p>
                        ) : (
                            <fieldset
                                disabled={locked}
                                className="space-y-3 text-xs leading-relaxed"
                            >
                                <legend className="mb-3 text-sm font-medium">
                                    Xác nhận trước khi tiếp tục
                                </legend>
                                <label className="flex cursor-pointer items-start gap-3">
                                    <input
                                        type="checkbox"
                                        className="mt-0.5 size-5 shrink-0 accent-primary"
                                        checked={accepted}
                                        onChange={(event) => setAccepted(event.target.checked)}
                                    />
                                    <span>{MEDIA_RIGHTS_ATTESTATION_TEXT}</span>
                                </label>
                                <label className="flex cursor-pointer items-start gap-3">
                                    <input
                                        type="checkbox"
                                        className="mt-0.5 size-5 shrink-0 accent-primary"
                                        checked={disclosed}
                                        onChange={(event) => setDisclosed(event.target.checked)}
                                    />
                                    <span>
                                        Tôi đồng ý để Viraldy gửi tư liệu tới Gemini, OpenAI và KIE
                                        để phân tích, tạo và kiểm tra video AI.
                                    </span>
                                </label>
                            </fieldset>
                        )}
                        {snapshot.requirements.requiresCharacter && (
                            <fieldset
                                disabled={locked}
                                className="space-y-3 rounded-xl bg-surface-soft p-3 text-xs"
                            >
                                <legend className="font-medium">Quyền hình ảnh nhân vật</legend>
                                <label className="flex items-start gap-3">
                                    <input
                                        type="checkbox"
                                        checked={characterConsented}
                                        onChange={(event) =>
                                            setCharacterConsented(event.target.checked)
                                        }
                                        className="size-5 accent-primary"
                                    />
                                    <span>
                                        Tôi có quyền dùng ảnh và sự đồng ý của nhân vật cho mục đích
                                        này.
                                    </span>
                                </label>
                                <label className="block space-y-1">
                                    <span>Phạm vi sử dụng nhân vật</span>
                                    <Input
                                        value={characterScope}
                                        onChange={(event) => setCharacterScope(event.target.value)}
                                        maxLength={4000}
                                    />
                                </label>
                                <label className="block space-y-1">
                                    <span>Căn cứ quyền và sự đồng ý của nhân vật</span>
                                    <Input
                                        value={characterEvidence}
                                        onChange={(event) =>
                                            setCharacterEvidence(event.target.value)
                                        }
                                        maxLength={4000}
                                    />
                                </label>
                            </fieldset>
                        )}
                        {intakeError && (
                            <p role="alert" className="text-xs text-destructive">
                                {intakeError}
                            </p>
                        )}
                        <a
                            href={MEDIA_RIGHTS_POLICY_PATH}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex min-h-11 items-center gap-2 text-xs text-primary underline underline-offset-4"
                        >
                            Chính sách sử dụng tư liệu{" "}
                            <ExternalLink className="size-3.5" aria-hidden="true" />
                        </a>
                    </section>
                    <div className="sticky -bottom-5 -mx-5 -mb-5 flex flex-col-reverse gap-2 border-t border-control-border bg-surface p-4 sm:-bottom-7 sm:-mx-7 sm:-mb-7 sm:flex-row sm:justify-end sm:p-5">
                        <Button
                            variant="ghost"
                            className="min-h-11"
                            onClick={props.onCancel}
                            disabled={locked}
                        >
                            Quay lại
                        </Button>
                        <Button
                            className="min-h-11"
                            disabled={cannotConfirm}
                            onClick={() => void confirm()}
                        >
                            {locked && (
                                <LoaderCircle className="size-4 animate-spin motion-reduce:animate-none" />
                            )}
                            {locked
                                ? "Đang gửi yêu cầu…"
                                : groupedRepair
                                  ? `Xác nhận và tạo lại ${props.sceneLabel?.toLowerCase() ?? "clip"}`
                                  : copy.confirm}
                        </Button>
                    </div>
                </>
            )}
        </DialogContent>
    );
}
