import { ImageOff, Loader2 } from "lucide-react";
import type { SmartRemakeProject } from "@/shared/api/smart-remake";
import { Button } from "@/shared/ui/button";
import type { RemakeResultNextAction } from "../lib/remake-result-next-action";

interface Props {
    action: RemakeResultNextAction;
    busy?: boolean;
    budget?: SmartRemakeProject["budget"];
    technicalError?: string | null;
    onAction(action: RemakeResultNextAction): void;
    onViewScript?(): void;
}

export function RemakeGenerationRecovery(props: Props) {
    const recovery = props.action.recovery;
    const title =
        recovery?.errorCode === "OPENAI_IMAGE_CREDITS_EXHAUSTED"
            ? recovery.providerErrorCode === "credit_balance_exhausted"
                ? "Cần bổ sung tín dụng tạo ảnh"
                : "Chạm hạn mức tạo ảnh"
            : "Tạo video chưa hoàn tất";
    const knownCost = props.budget?.knownActualUsd ?? props.budget?.actualUsd;
    const unknownCost =
        knownCost == null ||
        props.budget?.exposureUsd === null ||
        Boolean(props.budget?.unknownAttemptCount || props.budget?.unknownCosts);
    return (
        <section aria-label="Bước tiếp theo" className="remake-generation-recovery">
            <div className="remake-generation-recovery__heading">
                <ImageOff aria-hidden="true" />
                <h2>{title}</h2>
            </div>
            <div className="remake-generation-recovery__content">
                <p role="status" className="text-sm leading-relaxed">
                    {props.action.reason}
                </p>
                <div className="remake-generation-recovery__actions">
                    <Button
                        type="button"
                        className="min-h-11 whitespace-normal bg-[#e00b41] text-white hover:bg-[#c90a3a]"
                        disabled={props.busy}
                        aria-busy={props.busy}
                        onClick={() => props.onAction(props.action)}
                    >
                        {props.busy && (
                            <Loader2
                                className="size-4 animate-spin motion-reduce:animate-none"
                                aria-hidden="true"
                            />
                        )}
                        {props.busy ? "Đang kiểm tra…" : props.action.label}
                    </Button>
                    {props.onViewScript && (
                        <Button
                            type="button"
                            variant="ghost"
                            className="min-h-11 text-text-secondary"
                            disabled={props.busy}
                            onClick={props.onViewScript}
                        >
                            Xem kịch bản
                        </Button>
                    )}
                </div>
            </div>
            <details className="text-xs text-text-secondary">
                <summary className="min-h-9 cursor-pointer py-2 font-medium">
                    Chi tiết lỗi và chi phí
                </summary>
                <div className="space-y-2 pb-2 pt-1">
                    <p>Kịch bản và tư liệu của bạn vẫn được giữ.</p>
                    <p>Chưa gửi lượt tạo video tới KIE.</p>
                    <p>
                        {recovery?.errorCode}
                        {recovery?.httpStatus ? ` · HTTP ${recovery.httpStatus}` : ""}
                        {recovery?.providerErrorCode ? ` · ${recovery.providerErrorCode}` : ""}
                    </p>
                    {recovery?.retryAfterSeconds != null && (
                        <p>
                            Dịch vụ đề nghị chờ {recovery.retryAfterSeconds} giây trước lượt tiếp
                            theo.
                        </p>
                    )}
                    {props.technicalError && <p>{props.technicalError}</p>}
                    {knownCost != null && <p>Phí đã xác định: {knownCost} USD</p>}
                    {unknownCost && <p>Chi phí chưa xác định</p>}
                </div>
            </details>
        </section>
    );
}
