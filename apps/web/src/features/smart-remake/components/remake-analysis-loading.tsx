import { useEffect, useRef, useState } from "react";
import {
    Camera,
    Check,
    Clapperboard,
    Clock3,
    Hand,
    Loader2,
    RefreshCw,
    Sparkles,
    Video,
} from "lucide-react";
import type { SmartRemakeAnalysisProgress } from "@/shared/api/smart-remake";
import { DialogDescription, DialogTitle } from "@/shared/ui/dialog";
import { Button } from "@/shared/ui/button";
import storyboardIllustration from "@/assets/smart-remake/analysis-storyboard.webp";
import { RemakeImagePreview } from "./remake-image-preview";
import { RemakeSourceAudio } from "./remake-source-audio";
import { getRemakeSourceAudio } from "../lib/remake-source-audio";
import "./remake-analysis-loading.css";

interface Props {
    action: "analyze" | "reanalyze";
    presentation?: "dialog" | "inline";
    phase?: "preparing" | "analyzing";
    productUrl?: string | null;
    productUrls?: string[];
    primaryIndex?: number;
    sourceUrl?: string | null;
    durationSeconds?: number;
    progress?: SmartRemakeAnalysisProgress | null;
    startedAt?: number;
    statusError?: string | null;
    onCheckStatus?: () => void;
    checkingStatus?: boolean;
}

const stages = {
    validating_source: "Đang kiểm tra tư liệu",
    analyzing_source: "Đang đọc cảnh, hành động và nhịp quay",
    resolving_scenes: "Đang đối chiếu hành động và điểm chuyển cảnh",
    identifying_product: "Đang nhận diện sản phẩm từ ảnh chính",
    building_storyboard: "Đang soạn kịch bản cho sản phẩm",
    completed: "Kịch bản đã sẵn sàng",
    failed: "Chưa hoàn tất phân tích",
};
const seconds = new Intl.NumberFormat("vi-VN", { maximumFractionDigits: 2 });
const elapsedLabel = (value: number) =>
    `${Math.floor(value / 60)}:${String(value % 60).padStart(2, "0")}`;

function ReferencePreviews({
    sourceUrl,
    productUrl,
    productUrls,
    primaryIndex = 0,
    durationSeconds,
}: Pick<Props, "sourceUrl" | "productUrl" | "productUrls" | "primaryIndex" | "durationSeconds">) {
    const images = productUrls?.length ? productUrls : productUrl ? [productUrl] : [];
    const primary = Math.max(0, Math.min(images.length - 1, primaryIndex));
    return (
        <section
            className="remake-analysis-loading__references"
            aria-label="Tư liệu đã thêm"
            style={{
                gridTemplateColumns: `repeat(${Math.min(4, Math.max(2, images.length + 1))}, minmax(0, 1fr))`,
            }}
        >
            <figure className="remake-analysis-loading__reference" aria-label="Video mẫu">
                <div className="remake-analysis-loading__reference-media">
                    {sourceUrl ? (
                        <video
                            src={sourceUrl}
                            aria-label="Video mẫu đang phân tích"
                            controls
                            muted
                            playsInline
                            preload="metadata"
                        />
                    ) : (
                        <span>
                            <Video aria-hidden="true" /> Đang chuẩn bị video
                        </span>
                    )}
                </div>
                <figcaption>
                    Video mẫu{" "}
                    <span>
                        {durationSeconds != null &&
                        Number.isFinite(durationSeconds) &&
                        durationSeconds > 0
                            ? `${seconds.format(durationSeconds)} giây tư liệu`
                            : "Toàn bộ video"}
                    </span>
                </figcaption>
            </figure>
            {images.map((src, index) => (
                <figure
                    key={`${src}:${index}`}
                    className="remake-analysis-loading__reference"
                    aria-label={`Ảnh sản phẩm ${index + 1}`}
                >
                    <div className="remake-analysis-loading__reference-media is-product">
                        <RemakeImagePreview
                            src={src}
                            alt={
                                images.length === 1
                                    ? "Sản phẩm của bạn"
                                    : `Ảnh sản phẩm ${index + 1}`
                            }
                            enlarge
                            compact
                        />
                    </div>
                    <figcaption>
                        Ảnh sản phẩm {index + 1}
                        <span>{index === primary ? "Ảnh chính" : "Ảnh đã thêm"}</span>
                    </figcaption>
                </figure>
            ))}
            {!images.length && (
                <figure className="remake-analysis-loading__reference" aria-label="Ảnh sản phẩm">
                    <div className="remake-analysis-loading__reference-media is-product">
                        <span>
                            <Sparkles aria-hidden="true" /> Đang chuẩn bị ảnh
                        </span>
                    </div>
                    <figcaption>
                        Ảnh sản phẩm <span>Chưa có ảnh</span>
                    </figcaption>
                </figure>
            )}
        </section>
    );
}

function AnalysisFindings({ progress, phase }: Pick<Props, "progress" | "phase">) {
    const scenes = progress?.scenes ?? [];
    const count = progress?.sceneCount ?? scenes.length;
    const preliminary = progress?.preliminaryObservations ?? [];
    return (
        <section
            className="remake-analysis-loading__findings"
            aria-label="Kết quả phân tích đang có"
        >
            <div className="remake-analysis-loading__section-heading">
                <h3>
                    {count > 0
                        ? `Đã nhận diện ${count} cảnh`
                        : preliminary.length
                          ? "AI đã đọc được"
                          : progress?.status === "failed"
                            ? "Nhận định đã nhận"
                            : phase === "preparing" && !progress
                              ? "Đang chuẩn bị tư liệu"
                              : "Nội dung đang được đọc"}
                </h3>
                {scenes.length < count && (
                    <span>
                        Hiện {scenes.length} trong {count} cảnh
                    </span>
                )}
            </div>
            {scenes.length ? (
                <ol className="remake-analysis-loading__scenes" aria-label="Các cảnh đã phân tích">
                    {scenes.map((scene) => (
                        <li
                            key={`${scene.index}:${scene.startSecond}:${scene.endSecond}`}
                            className="remake-analysis-loading__scene"
                        >
                            <span className="remake-analysis-loading__scene-number">
                                {scene.index + 1}
                            </span>
                            <div>
                                <div className="remake-analysis-loading__scene-heading">
                                    <strong>Cảnh {scene.index + 1}</strong>
                                    <span>
                                        {seconds.format(scene.startSecond)}–
                                        {seconds.format(scene.endSecond)} giây nguồn
                                    </span>
                                </div>
                                <p>{scene.action}</p>
                                {scene.camera && (
                                    <small>
                                        <Camera aria-hidden="true" /> {scene.camera}
                                    </small>
                                )}
                                {scene.transition && (
                                    <small>
                                        <Clapperboard aria-hidden="true" /> {scene.transition}
                                    </small>
                                )}
                            </div>
                        </li>
                    ))}
                </ol>
            ) : preliminary.length ? (
                <div className="remake-analysis-loading__quick-body">
                    <small>
                        {progress?.status === "running"
                            ? "Nhận định sơ bộ; đang đối chiếu mốc cảnh."
                            : "Nhận định sơ bộ đã nhận; mốc cảnh chưa được xác nhận."}
                    </small>
                    <dl>
                        {preliminary.map((observation, index) => (
                            <div key={index}>
                                <dt>{observation.label}</dt>
                                <dd>{observation.detail}</dd>
                            </div>
                        ))}
                    </dl>
                </div>
            ) : progress?.status === "failed" ? (
                <p className="mt-3 text-sm text-text-secondary">
                    Chưa có dữ liệu cảnh đủ để xác nhận mốc thời gian.
                </p>
            ) : (
                <div className="remake-analysis-loading__empty">
                    <img src={storyboardIllustration} alt="" width={120} height={70} />
                    <div>
                        <p>Thông tin từng cảnh sẽ xuất hiện khi AI trả kết quả.</p>
                        <span>
                            {phase === "preparing" && !progress
                                ? "Tư liệu đang được chuẩn bị để AI phân tích."
                                : "Đang tìm cách quay, hành động và điểm chuyển cảnh trong mẫu."}
                        </span>
                    </div>
                </div>
            )}
            {progress?.product && (
                <div className="remake-analysis-loading__product-facts">
                    <p>
                        <Check aria-hidden="true" /> Đã nhận diện sản phẩm
                    </p>
                    <strong>{progress.product.name}</strong>
                    {progress.product.details.length > 0 && (
                        <ul>
                            {progress.product.details.map((detail, index) => (
                                <li key={`${index}:${detail}`}>{detail}</li>
                            ))}
                        </ul>
                    )}
                </div>
            )}
        </section>
    );
}

function QuickAnalysisSummary({ progress }: Pick<Props, "progress">) {
    const quick = progress?.quickSummary;
    if (!quick) return null;
    const observations = quick.observations ?? [];
    const pending = quick.status === "pending" && progress?.status === "running";
    const unavailable = quick.status === "unavailable" || (quick.status === "pending" && !pending);
    const reasons = {
        timeout: "Lượt đọc nhanh chưa trả kết quả trong thời gian chờ.",
        invalid_response: "Kết quả đọc nhanh chưa đọc được đầy đủ.",
        unavailable: "Chưa lấy được kết quả đọc nhanh.",
    };
    const hasFacts = Boolean(
        progress?.scenes.length ||
        progress?.preliminaryObservations?.length ||
        progress?.product ||
        progress?.sourceAudio,
    );
    const unavailableMessage =
        progress?.status === "failed"
            ? "Tóm tắt nhanh chưa có dữ liệu. Xem trạng thái phân tích để biết bước tiếp theo."
            : progress?.status === "completed"
              ? "Phân tích chi tiết đã có kết quả ở bên dưới."
              : hasFacts
                ? "Kết quả phân tích đã nhận được giữ ở bên dưới."
                : "Lượt phân tích chính chưa có kết quả đủ để hiển thị.";
    return (
        <section className="remake-analysis-loading__quick" aria-label="Tóm tắt nhanh từ video">
            <div className="remake-analysis-loading__section-heading">
                <h3>
                    <Sparkles aria-hidden="true" /> Tóm tắt nhanh từ video
                </h3>
                {quick.status === "completed" && <span>Nhận xét sơ bộ</span>}
            </div>
            <div key={quick.status} className="remake-analysis-loading__quick-body">
                {pending ? (
                    <p className="remake-analysis-loading__quick-pending">
                        <Loader2 aria-hidden="true" /> AI đang đọc nhanh nội dung video.
                    </p>
                ) : unavailable ? (
                    <>
                        <p>Chưa nhận được tóm tắt nhanh.</p>
                        {quick.reason && <small>{reasons[quick.reason]}</small>}
                        <small>{unavailableMessage}</small>
                    </>
                ) : (
                    <>
                        {quick.summary && <p>{quick.summary}</p>}
                        {observations.length > 0 && (
                            <dl>
                                {observations.map((observation, index) => (
                                    <div key={index}>
                                        <dt>{observation.label}</dt>
                                        <dd>{observation.detail}</dd>
                                    </div>
                                ))}
                            </dl>
                        )}
                        <small>Nhận xét sơ bộ; phân tích chi tiết sẽ xác nhận từng cảnh.</small>
                    </>
                )}
            </div>
        </section>
    );
}

export function RemakeAnalysisSnapshot({ progress }: { progress?: SmartRemakeAnalysisProgress }) {
    if (progress?.status !== "failed") return null;
    const audio = getRemakeSourceAudio(progress?.sourceAudio);
    const quickAudio =
        progress?.quickSummary?.status === "completed"
            ? getRemakeSourceAudio(progress.quickSummary.sourceAudio)
            : null;
    const findings = Boolean(
        progress?.scenes.length || progress?.preliminaryObservations?.length || progress?.product,
    );
    if (!(
        findings ||
        audio ||
        quickAudio ||
        (progress.quickSummary?.status === "completed" && progress.quickSummary.summary)
    ))
        return null;
    return (
        <section
            aria-label="Nhận định từ lượt phân tích trước"
            className="space-y-4 rounded-3xl bg-surface p-5 sm:p-6"
        >
            <header className="space-y-2">
                <h2 className="font-semibold">Từ lượt phân tích trước</h2>
                <p className="text-sm leading-relaxed text-text-secondary">
                    Phân tích trước chưa hoàn tất. Các nhận định đã có vẫn được giữ để bạn tham
                    khảo; chúng chưa xác nhận bộ tư liệu đang chọn bên dưới.
                </p>
            </header>
            {progress.quickSummary?.status === "completed" && (
                <QuickAnalysisSummary progress={progress} />
            )}
            {findings && <AnalysisFindings progress={progress} />}
            <RemakeSourceAudio value={audio ?? quickAudio} preliminary={!audio} />
        </section>
    );
}

export function RemakeAnalysisLoading({
    action,
    presentation = "dialog",
    phase = "preparing",
    productUrl,
    productUrls,
    primaryIndex,
    sourceUrl,
    durationSeconds,
    progress,
    startedAt,
    statusError,
    onCheckStatus,
    checkingStatus,
}: Props) {
    const heading = useRef<HTMLHeadingElement>(null);
    const mountedAt = useRef<number | null>(null);
    const [elapsed, setElapsed] = useState(0);
    const terminal = progress?.status === "completed" || progress?.status === "failed";
    useEffect(() => {
        heading.current?.focus({ preventScroll: true });
    }, []);
    useEffect(() => {
        mountedAt.current ??= Date.now();
        const savedStart = progress?.startedAt ? Date.parse(progress.startedAt) : NaN;
        const start = startedAt ?? (Number.isFinite(savedStart) ? savedStart : mountedAt.current);
        const receivedEnd = terminal ? Date.parse(progress?.updatedAt ?? "") : NaN;
        const end = Number.isFinite(receivedEnd) ? receivedEnd : start;
        const update = () =>
            setElapsed(Math.max(0, Math.floor(((terminal ? end : Date.now()) - start) / 1000)));
        update();
        if (terminal) return;
        const timer = window.setInterval(update, 1000);
        return () => window.clearInterval(timer);
    }, [startedAt, progress?.startedAt, progress?.updatedAt, terminal]);
    const title = progress
        ? stages[progress.stage]
        : phase === "preparing"
          ? "Đang chuẩn bị phân tích"
          : action === "reanalyze"
            ? "Đang cập nhật kịch bản"
            : "Đang đọc video mẫu";
    const count = progress?.sceneCount ?? progress?.scenes.length ?? 0;
    const longWait = elapsed >= 45;
    const failed = progress?.status === "failed";
    const showStatusCheck = Boolean(onCheckStatus && (longWait || statusError || failed));
    const Title = presentation === "inline" ? "h2" : DialogTitle;
    const Description = presentation === "inline" ? "p" : DialogDescription;
    return (
        <div className="remake-analysis-loading">
            <div className="remake-analysis-loading__eyebrow">
                <span>
                    <i
                        className="remake-analysis-loading__signal"
                        aria-hidden="true"
                        style={terminal ? { animation: "none" } : undefined}
                    />{" "}
                    SMART REMAKE · ĐỌC VIDEO MẪU
                </span>
                <time aria-label="Thời gian đã chờ" dateTime={`PT${elapsed}S`}>
                    <Clock3 aria-hidden="true" /> {terminal ? "Thời gian xử lý" : "Đã chờ"}{" "}
                    {elapsedLabel(elapsed)}
                </time>
            </div>
            <div className="remake-analysis-loading__intro">
                <Title
                    ref={heading}
                    tabIndex={-1}
                    className="text-xl leading-tight outline-none sm:text-2xl"
                >
                    {title}
                </Title>
                <Description>
                    Những gì AI nhận diện được sẽ xuất hiện bên dưới. Bạn sẽ duyệt kịch bản trước
                    khi tạo video.
                </Description>
            </div>
            <div
                role="status"
                aria-label="Tiến trình phân tích"
                aria-live="polite"
                aria-atomic="true"
                className="sr-only"
            >
                {title}. {count > 0 ? `Đã nhận diện ${count} cảnh. ` : ""}
                {progress?.quickSummary?.status === "completed"
                    ? "Đã có tóm tắt nhanh, nhận xét sơ bộ. "
                    : ""}
                {!progress?.scenes.length && progress?.preliminaryObservations?.length
                    ? "Đã có nhận định sơ bộ từ lượt phân tích chính. "
                    : ""}
                {progress?.product ? `Đã nhận diện sản phẩm ${progress.product.name}. ` : ""}Bạn sẽ
                duyệt kịch bản trước khi tạo video.
            </div>
            <ReferencePreviews
                sourceUrl={sourceUrl}
                productUrl={productUrl}
                productUrls={productUrls}
                primaryIndex={primaryIndex}
                durationSeconds={progress?.sourceDurationSeconds ?? durationSeconds}
            />
            <div className="remake-analysis-loading__concepts" aria-label="Nội dung phân tích">
                <span>
                    <Camera aria-hidden="true" /> Góc quay
                </span>
                <span>
                    <Hand aria-hidden="true" /> Hành động
                </span>
                <span>
                    <Clapperboard aria-hidden="true" /> Nhịp dựng
                </span>
            </div>
            <QuickAnalysisSummary progress={progress} />
            <RemakeSourceAudio
                value={
                    getRemakeSourceAudio(progress?.sourceAudio) ??
                    (progress?.quickSummary?.status === "completed"
                        ? progress.quickSummary.sourceAudio
                        : undefined)
                }
                pending={
                    progress?.status === "running" && progress.quickSummary?.status === "pending"
                }
                preliminary={!getRemakeSourceAudio(progress?.sourceAudio)}
            />
            <AnalysisFindings progress={progress} phase={phase} />
            <div className="remake-analysis-loading__footer">
                {statusError ? (
                    <p role="alert">{statusError}</p>
                ) : progress?.status === "completed" ? (
                    <p>Phân tích đã xong. Đang lấy kịch bản đã lưu để bạn xem.</p>
                ) : failed ? (
                    <p>Kết quả đã nhận vẫn được giữ. Kiểm tra trạng thái để biết bước cần xử lý.</p>
                ) : longWait ? (
                    <p>
                        {phase === "preparing" && !progress
                            ? "Đang tải và kiểm tra tư liệu. Thời gian chờ phụ thuộc dung lượng và kết nối."
                            : "AI có thể cần thêm thời gian với video nhiều chi tiết. Thông tin đã nhận vẫn được giữ trong lúc chờ cập nhật."}
                    </p>
                ) : (
                    <p>Bước này chưa tạo video. Bạn có thể xem lại tư liệu trong lúc chờ.</p>
                )}
                {showStatusCheck && (
                    <>
                        <Button
                            type="button"
                            variant="outline"
                            onClick={onCheckStatus}
                            disabled={checkingStatus}
                        >
                            {checkingStatus ? (
                                <Loader2
                                    className="size-4 animate-spin motion-reduce:animate-none"
                                    aria-hidden="true"
                                />
                            ) : (
                                <RefreshCw className="size-4" aria-hidden="true" />
                            )}
                            {checkingStatus ? "Đang kiểm tra…" : "Kiểm tra trạng thái"}
                        </Button>
                        <small>Chỉ lấy trạng thái hiện tại, không gửi lại yêu cầu AI.</small>
                    </>
                )}
            </div>
        </div>
    );
}
