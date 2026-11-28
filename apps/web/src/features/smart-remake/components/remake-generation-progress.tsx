import { Check, Clock3, Film, Image, Layers3, Loader2, RefreshCw, ShieldAlert } from "lucide-react";
import type { SmartRemakeProject } from "@/shared/api/smart-remake";
import { ApiError } from "@/shared/api/errors";
import { Button } from "@/shared/ui/button";
import { RemakeGeneratedImage, RemakeKiePrompt } from "./remake-generated-media";
import {
    generationStageLabels,
    getRemakeGenerationProgress,
} from "../lib/remake-generation-progress";
import { getRemakeErrorMessage } from "../lib/smart-remake-render";
import "./remake-generation-progress.css";

export interface RemakeGenerationProgressProps {
    workspaceId?: string;
    project: SmartRemakeProject;
    sourceUrl?: string | null;
    productUrl?: string | null;
    busy?: boolean;
    onCheckStatus?(): void;
    onViewInspection?(reportId: string): void;
    onViewScript?(): void;
}

const seconds = (value: number) => Number(value.toFixed(3)).toLocaleString("vi-VN");
const clock = (value: number) => `${Math.floor(value / 60)}:${String(value % 60).padStart(2, "0")}`;

export function RemakeGenerationProgress({
    workspaceId,
    project,
    sourceUrl,
    productUrl,
    busy,
    onCheckStatus,
    onViewInspection,
    onViewScript,
}: RemakeGenerationProgressProps) {
    const progress = getRemakeGenerationProgress(project);
    if (!progress) return null;
    const blocked = progress.groups.some((group) => group.stage === "blocked");
    const blockedImage = progress.groups.some(
        (group) =>
            group.stage === "blocked" && group.errorCode === "SMART_REMAKE_CONDITIONING_BLOCKED",
    );
    const activeGroup =
        progress.active &&
        progress.groups.find((group) =>
            [
                "preparing_image",
                "checking_image",
                "submitting_video",
                "generating",
                "checking",
            ].includes(group.stage),
        );
    const complete = progress.completedCount === progress.plannedCount;
    const heading = blocked
        ? blockedImage
            ? "Cần kiểm tra ảnh trước khi tạo video"
            : "Cần xử lý trước khi tạo tiếp"
        : complete
          ? "Các clip đã sẵn sàng để bạn xem"
          : activeGroup
            ? generationStageLabels[activeGroup.stage]
            : "Theo dõi các clip của bạn";
    const referenceSource = project.sourceVideoUrl ?? sourceUrl;
    const referenceProduct = project.productImageUrl ?? productUrl;
    const sourceThumbnail = progress.groups.find(
        (group) => group.sourceThumbnailUrl,
    )?.sourceThumbnailUrl;
    return (
        <section
            aria-label="Tiến trình tạo video"
            className="remake-generation-progress"
            data-active={progress.active}
        >
            <header className="remake-generation-progress__header">
                <div>
                    <p className="remake-generation-progress__eyebrow">
                        <Layers3 aria-hidden="true" /> TỪ KỊCH BẢN ĐẾN VIDEO
                    </p>
                    <h2>{heading}</h2>
                    <p className="remake-generation-progress__description">
                        {blockedImage
                            ? "Ảnh đã được chuẩn bị, nhưng bước kiểm chứng chưa cho phép tạo tiếp. Xem kết quả kiểm tra để biết phần cần xử lý."
                            : blocked
                              ? "Lượt tạo đang dừng. Tư liệu đã chuẩn bị và clip đã có vẫn hiển thị bên dưới."
                              : "Phần nào đã hoàn tất sẽ xuất hiện ngay bên dưới. Mỗi clip chứa nhiều cảnh từ kịch bản."}
                    </p>
                </div>
                {progress.elapsedSeconds !== null && (
                    <span className="remake-generation-progress__clock">
                        <Clock3 aria-hidden="true" /> {clock(progress.elapsedSeconds)} đã xử lý
                        <span>Theo cập nhật máy chủ</span>
                    </span>
                )}
            </header>
            <div className="remake-generation-progress__summary" role="status" aria-live="polite">
                <span>{progress.plannedCount} lượt dự kiến</span>
                <span>
                    {progress.submittedCount === null
                        ? "Chưa xác nhận số lượt đã gửi KIE"
                        : `${progress.submittedCount} lượt đã gửi KIE`}
                </span>
                {progress.completedCount > 0 && (
                    <span>{progress.completedCount} clip đã hoàn tất</span>
                )}
            </div>
            {(referenceSource || sourceThumbnail || referenceProduct) && (
                <div
                    className="remake-generation-progress__references"
                    aria-label="Tư liệu tham chiếu"
                >
                    {(referenceSource || sourceThumbnail) && (
                        <figure>
                            {sourceThumbnail ? (
                                <img src={sourceThumbnail} alt="Khung hình từ video mẫu" />
                            ) : (
                                <video
                                    src={referenceSource!}
                                    preload="metadata"
                                    muted
                                    playsInline
                                    aria-label="Video mẫu — tư liệu tham chiếu"
                                />
                            )}
                            <figcaption>
                                <Film aria-hidden="true" />
                                <span>
                                    Video mẫu<small>Tư liệu tham chiếu</small>
                                </span>
                            </figcaption>
                        </figure>
                    )}
                    {referenceProduct && (
                        <figure>
                            <img src={referenceProduct} alt="Ảnh sản phẩm chính" />
                            <figcaption>
                                <Image aria-hidden="true" />
                                <span>
                                    Sản phẩm của bạn<small>Ảnh tham chiếu chính</small>
                                </span>
                            </figcaption>
                        </figure>
                    )}
                </div>
            )}
            <div className="remake-generation-progress__groups">
                {progress.groups.map((group) => {
                    const kieError =
                        ["blocked", "unknown"].includes(group.stage) &&
                        (group.errorCode?.startsWith("KIE_") ||
                            group.errorCode === "SMART_REMAKE_SUBMISSION_UNRESOLVED")
                            ? getRemakeErrorMessage(
                                  new ApiError(group.errorCode, "", 503, {
                                      providerError: group.providerError,
                                  }),
                              )
                            : null;
                    const active =
                        progress.active &&
                        [
                            "preparing_image",
                            "checking_image",
                            "submitting_video",
                            "generating",
                            "checking",
                        ].includes(group.stage);
                    const stageLabel =
                        group.stage === "blocked" &&
                        group.errorCode === "SMART_REMAKE_CONDITIONING_BLOCKED"
                            ? "Chưa đủ bằng chứng kiểm tra ảnh"
                            : generationStageLabels[group.stage];
                    const image = group.conditioningImageUrl ?? group.sourceThumbnailUrl;
                    const imageGrid = (
                        <div className="remake-generation-progress__image-grid">
                            {group.conditioningImages.map((reference, index) => (
                                <RemakeGeneratedImage
                                    key={`${reference.requestHash ?? reference.renderUnitId}:${reference.frameRole ?? index}`}
                                    workspaceId={workspaceId}
                                    projectId={project.id}
                                    operationId={project.generationProgress?.operationId ?? ""}
                                    image={reference}
                                    sceneIndex={reference.sourceSceneIndex}
                                    ordinal={index + 1}
                                    onRefresh={onCheckStatus}
                                />
                            ))}
                        </div>
                    );
                    const StatusIcon =
                        group.stage === "completed"
                            ? Check
                            : group.stage === "blocked"
                              ? ShieldAlert
                              : active
                                ? Loader2
                                : Clock3;
                    return (
                        <article
                            key={group.id}
                            className="remake-generation-progress__group"
                            data-stage={group.stage}
                            data-active={active}
                        >
                            <div className="remake-generation-progress__group-heading">
                                <h3>Clip {group.index}</h3>
                                <span>
                                    {seconds(group.startSecond)}–{seconds(group.endSecond)} giây
                                </span>
                            </div>
                            <div
                                className="remake-generation-progress__poster"
                                data-kind={
                                    group.videoUrl
                                        ? "video"
                                        : group.conditioningImages.length
                                          ? "images"
                                          : "reference"
                                }
                            >
                                {group.videoUrl ? (
                                    <video
                                        src={group.videoUrl}
                                        controls
                                        playsInline
                                        preload="metadata"
                                        aria-label={`Clip ${group.index} đã tạo`}
                                    />
                                ) : group.conditioningImages.length ? (
                                    imageGrid
                                ) : image ? (
                                    <img
                                        src={image}
                                        alt={
                                            group.conditioningImageUrl
                                                ? `Ảnh mở đầu được tạo cho clip ${group.index}`
                                                : `Khung hình nguồn tham chiếu cho clip ${group.index}`
                                        }
                                    />
                                ) : (
                                    <div
                                        className="remake-generation-progress__placeholder"
                                        aria-hidden="true"
                                    >
                                        <Film />
                                        <span>CLIP {group.index}</span>
                                    </div>
                                )}
                                {!group.videoUrl && (
                                    <div
                                        className="remake-generation-progress__poster-frame"
                                        aria-hidden="true"
                                    />
                                )}
                                {active && (
                                    <div
                                        className="remake-generation-progress__scan"
                                        aria-hidden="true"
                                    />
                                )}
                                {!group.videoUrl && (
                                    <span className="remake-generation-progress__media-label">
                                        {group.conditioningImages.length
                                            ? `${group.conditioningImages.length} ảnh đã tạo`
                                            : group.conditioningImageUrl
                                              ? "Ảnh mở đầu đã tạo · chưa phải video"
                                              : image
                                                ? "Khung hình video mẫu · ảnh tham chiếu"
                                                : "Chờ ảnh tham chiếu"}
                                    </span>
                                )}
                            </div>
                            <div className="remake-generation-progress__group-body">
                                <p className="remake-generation-progress__stage">
                                    <StatusIcon aria-hidden="true" />
                                    {stageLabel}
                                </p>
                                <p className="remake-generation-progress__submission">
                                    {group.videoSubmitted === true
                                        ? "Đã gửi lượt tạo clip tới KIE"
                                        : group.videoSubmitted === false
                                          ? "Chưa gửi lượt tạo clip tới KIE"
                                          : "Chưa xác nhận trạng thái gửi tới KIE"}
                                </p>
                                {kieError && (
                                    <div
                                        role="alert"
                                        className="space-y-2 rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-950"
                                    >
                                        <p className="font-semibold">
                                            {group.stage === "unknown"
                                                ? "Chưa nhận được kết quả từ kie.ai"
                                                : group.errorCode === "KIE_TASK_FAILED"
                                                  ? "Lỗi từ nhà cung cấp kie.ai"
                                                  : "Bước kết nối với kie.ai gặp lỗi"}
                                        </p>
                                        <p>{kieError}</p>
                                        {group.providerError?.providerMessage && (
                                            <div>
                                                <p className="font-medium">KIE trả về</p>
                                                <p className="whitespace-pre-wrap break-words">
                                                    {group.providerError.providerMessage}
                                                </p>
                                            </div>
                                        )}
                                        {(group.providerTaskId ||
                                            group.providerError?.providerCode != null ||
                                            group.providerError?.httpStatus != null) && (
                                            <details>
                                                <summary className="cursor-pointer">
                                                    Chi tiết lỗi KIE
                                                </summary>
                                                <dl className="mt-2 space-y-1 break-words">
                                                    {group.providerTaskId && (
                                                        <div>
                                                            <dt>Mã tác vụ KIE</dt>
                                                            <dd>{group.providerTaskId}</dd>
                                                        </div>
                                                    )}
                                                    {group.providerError?.providerCode != null && (
                                                        <div>
                                                            <dt>Mã lỗi KIE</dt>
                                                            <dd>
                                                                {group.providerError.providerCode}
                                                            </dd>
                                                        </div>
                                                    )}
                                                    {group.providerError?.httpStatus != null && (
                                                        <div>
                                                            <dt>HTTP</dt>
                                                            <dd>
                                                                {group.providerError.httpStatus}
                                                            </dd>
                                                        </div>
                                                    )}
                                                </dl>
                                            </details>
                                        )}
                                    </div>
                                )}
                                {group.sourceSceneIndexes.length > 0 && (
                                    <p className="remake-generation-progress__scenes">
                                        Từ cảnh {group.sourceSceneIndexes.join(", ")}
                                    </p>
                                )}
                                {group.videoUrl && group.conditioningImages.length > 0 && (
                                    <details className="remake-generation-progress__retained-images">
                                        <summary>
                                            {group.conditioningImages.length} ảnh tham chiếu đã tạo
                                        </summary>
                                        {imageGrid}
                                    </details>
                                )}
                                <RemakeKiePrompt
                                    request={group.kieRequest}
                                    videoSubmitted={group.videoSubmitted}
                                />
                                {group.stage === "blocked" &&
                                    group.inspectionReportId &&
                                    onViewInspection && (
                                        <Button
                                            type="button"
                                            className="min-h-11 w-full whitespace-normal bg-[#e00b41] text-white hover:bg-[#c90a3a]"
                                            disabled={busy}
                                            onClick={() =>
                                                onViewInspection(group.inspectionReportId!)
                                            }
                                        >
                                            Xem kết quả kiểm tra ảnh
                                        </Button>
                                    )}
                            </div>
                        </article>
                    );
                })}
            </div>
            <footer className="remake-generation-progress__footer">
                <p>Ảnh là tư liệu chuẩn bị. Clip đã tạo có nút phát để bạn xem ngay.</p>
                {onViewScript && (
                    <Button
                        type="button"
                        variant="ghost"
                        className="min-h-11 shrink-0"
                        disabled={busy}
                        onClick={onViewScript}
                    >
                        Xem kịch bản
                    </Button>
                )}
                {onCheckStatus && (
                    <Button
                        type="button"
                        variant="ghost"
                        className="min-h-11 shrink-0"
                        disabled={busy}
                        onClick={onCheckStatus}
                    >
                        <RefreshCw aria-hidden="true" />
                        Kiểm tra trạng thái
                    </Button>
                )}
            </footer>
        </section>
    );
}
