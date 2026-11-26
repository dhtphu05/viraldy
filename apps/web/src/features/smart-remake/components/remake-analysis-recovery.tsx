import { RefreshCw } from "lucide-react";
import type { SmartRemakeProject } from "@/shared/api/smart-remake";
import { Button } from "@/shared/ui/button";
import { getRemakeAnalysisRecovery } from "../lib/remake-analysis-recovery";
import { RemakeAnalysisSnapshot } from "./remake-analysis-loading";

interface Props {
    project: SmartRemakeProject;
    busy?: boolean;
    onRetry(): void;
    onCheckStatus(): void;
    onViewSavedScript?: () => void;
}

export function RemakeAnalysisRecovery({
    project,
    busy,
    onRetry,
    onCheckStatus,
    onViewSavedScript,
}: Props) {
    const progress = getRemakeAnalysisRecovery(project);
    if (!progress) return null;
    const canRetry = progress.retryDisposition === "new_analysis";
    const started = Date.parse(progress.startedAt);
    return (
        <section
            aria-label="Khôi phục phân tích kịch bản"
            className="space-y-4 rounded-3xl bg-surface p-5 sm:p-6"
        >
            <div className="space-y-2">
                <h2 className="text-lg font-semibold">
                    {canRetry
                        ? "Lượt phân tích vừa rồi chưa tạo được kịch bản mới"
                        : "Cần kiểm tra kết quả lượt phân tích trước"}
                </h2>
                <p className="text-sm leading-relaxed text-text-secondary">
                    {canRetry
                        ? "Video và ảnh của bạn vẫn còn. Bạn có thể phân tích lại với bộ tư liệu hiện tại."
                        : "Chưa rõ kết quả của yêu cầu đã gửi. Kiểm tra trạng thái để tiếp tục đúng lượt này."}
                </p>
                {Number.isFinite(started) && (
                    <p className="text-xs text-text-secondary">
                        Lượt phân tích bắt đầu lúc {new Date(started).toLocaleString("vi-VN")}
                    </p>
                )}
            </div>
            <div className="flex flex-wrap items-center gap-3">
                <Button disabled={busy} onClick={canRetry ? onRetry : onCheckStatus}>
                    <RefreshCw aria-hidden="true" />{" "}
                    {canRetry ? "Phân tích lại" : "Kiểm tra trạng thái"}
                </Button>
                {onViewSavedScript && (
                    <Button disabled={busy} variant="ghost" onClick={onViewSavedScript}>
                        Xem kịch bản đã lưu
                    </Button>
                )}
            </div>
            {onViewSavedScript && (
                <p className="text-xs text-text-secondary">
                    Kịch bản đã lưu thuộc lượt phân tích trước; chưa được cập nhật bởi yêu cầu vừa
                    rồi.
                </p>
            )}
            <details className="rounded-2xl border border-control-border p-4">
                <summary className="cursor-pointer text-sm">
                    Nhận định đã nhận từ lượt phân tích
                </summary>
                <div className="mt-4">
                    <RemakeAnalysisSnapshot progress={progress} />
                </div>
            </details>
        </section>
    );
}
