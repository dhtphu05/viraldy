import { useId, useState } from "react";
import type { SmartRemakeProject } from "@/shared/api/smart-remake";
import { Button } from "@/shared/ui/button";
import { Textarea } from "@/shared/ui/textarea";
import { isInspectionReadyForApproval } from "../lib/remake-inspection";

export interface RemakeProjectControlsProps {
    project: SmartRemakeProject;
    busy: boolean;
    currentReportIds?: string[];
    onApprove(assemblyId: string, reportId: string): Promise<unknown>;
    onExport(assemblyId: string): Promise<unknown>;
    onRestore(assemblyId: string): Promise<unknown>;
    onDelete(reason: string): Promise<unknown>;
    onRightsReview?(evidenceNote: string): Promise<unknown>;
}
const stages: Record<string, string> = {
    analysis: "Phân tích video mẫu",
    image: "Tạo ảnh điều kiện",
    video: "Tạo clip AI",
    inspection: "Kiểm tra nội dung",
    compose: "Ghép preview",
    render: "Tạo video",
    queued: "Đã xếp hàng",
};
const usd = (amount?: string | null) => (amount == null ? "Chưa xác định" : `${amount} USD`);

export function RemakeProjectControls(props: RemakeProjectControlsProps) {
    const { project } = props;
    const id = useId();
    const [reason, setReason] = useState("");
    const [rightsNote, setRightsNote] = useState("");
    const [confirmDelete, setConfirmDelete] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const costs = project.budget;
    const assemblies = project.assemblies?.records ?? [];
    const active = assemblies.find((item) => item.id === project.assemblies?.activeAssemblyId);
    const currentReportIds =
        props.currentReportIds ?? project.inspectionSummary?.currentReportIds ?? [];
    const report = [...(project.inspectionSummary?.reports ?? [])]
        .reverse()
        .find(
            (item) =>
                currentReportIds.includes(item.id) &&
                !item.stale &&
                item.subject.kind === "assembly" &&
                item.subject.assemblyId === active?.id &&
                item.subject.mediaHash === active?.mediaHash &&
                item.manifestHash === active?.manifestHash &&
                item.constraintsHash === active?.constraintsHash,
        );
    const approval = project.release?.approvals?.find(
        (item) =>
            item.id === project.release?.activeApprovalId &&
            item.status === "approved" &&
            item.assemblyId === active?.id &&
            item.mediaHash === active.mediaHash &&
            item.manifestHash === active.manifestHash &&
            item.constraintsHash === active.constraintsHash &&
            item.reportId === report?.id,
    );
    const deleted = Boolean(
        project.deletion && !["none", "cancelled"].includes(project.deletion.status),
    );
    const pending = props.busy || Boolean(project.pendingOperation) || deleted;
    const canApprove = Boolean(
        active &&
        report &&
        isInspectionReadyForApproval(report, project.inspectionSummary?.reviews ?? []) &&
        active.technicalCheck?.status === "passed",
    );
    async function run(action: () => Promise<unknown>) {
        setError(null);
        try {
            await action();
        } catch {
            setError(
                "Chưa hoàn tất thao tác. Làm mới dự án để kiểm tra quyền, bằng chứng và trạng thái hiện tại.",
            );
        }
    }
    const operation = project.pendingOperation;
    const progress = operation?.progress;
    const stage = progress?.stage ?? operation?.stage ?? operation?.kind;
    return (
        <section
            aria-label="Duyệt và xuất video"
            className="min-w-0 space-y-5 rounded-3xl bg-surface p-5 sm:p-6"
        >
            {operation && (
                <div
                    role="status"
                    aria-live="polite"
                    className="space-y-2 rounded-2xl bg-primary-soft p-4"
                >
                    <h3 className="text-sm font-medium">
                        {operation.needsReconciliation
                            ? "Yêu cầu cần đối soát"
                            : (stage && stages[stage]) || "Đang xử lý yêu cầu đã lưu"}
                    </h3>
                    {typeof progress?.completed === "number" &&
                        typeof progress.total === "number" &&
                        progress.total > 0 && (
                            <p className="text-xs">
                                {progress.completed}/{progress.total} công việc theo máy chủ
                            </p>
                        )}
                    <p className="text-xs text-text-secondary">
                        {operation.needsReconciliation
                            ? "Kiểm tra lại yêu cầu hiện tại trước khi gửi lượt mới."
                            : "Bạn có thể mở lại dự án để tiếp tục xem tiến trình."}
                    </p>
                </div>
            )}
            <div className="space-y-3 border-t border-control-border pt-5">
                <h2 className="font-semibold">Duyệt nội dung thành phẩm</h2>
                <p className="text-sm text-text-secondary">
                    “Dùng đoạn này” lưu lựa chọn cắt. Duyệt nội dung áp dụng cho đúng bản ghép, yêu
                    cầu và báo cáo kiểm tra hiện tại.
                </p>
                {project.release?.invalidationReason &&
                    Boolean(project.release.approvals?.length) && (
                        <p role="status" className="text-sm text-warn">
                            Bản duyệt trước đã hết hiệu lực vì nội dung hoặc ngữ cảnh thay đổi. Kiểm
                            tra và duyệt lại.
                        </p>
                    )}
                <p className="text-sm text-text-secondary">
                    {approval
                        ? "Đã duyệt đúng bản ghép hiện tại."
                        : !active
                          ? "Ghép preview trước để kiểm tra MP4 cuối."
                          : !report
                            ? "Cần báo cáo kiểm tra đúng bản ghép hiện tại."
                            : !canApprove
                              ? "Cần xử lý lỗi hoặc nhận xét có căn cứ trước khi duyệt."
                              : "Bằng chứng hiện tại đã sẵn sàng để bạn duyệt nội dung."}
                </p>
                <div className="flex flex-wrap gap-3">
                    <Button
                        type="button"
                        disabled={pending || !canApprove || Boolean(approval)}
                        onClick={() =>
                            active &&
                            report &&
                            void run(() => props.onApprove(active.id, report.id))
                        }
                    >
                        Duyệt nội dung bản ghép này
                    </Button>
                    <Button
                        type="button"
                        variant="outline"
                        disabled={pending || !approval || !active}
                        onClick={() => active && void run(() => props.onExport(active.id))}
                    >
                        Tải bản có nhãn AI
                    </Button>
                </div>
                <p className="text-xs text-text-secondary">
                    {deleted
                        ? "Dự án đã ngừng dùng. Xem trạng thái xóa tư liệu bên dưới."
                        : props.busy && !operation
                          ? "Đang lưu thao tác. Chờ cập nhật xong để duyệt hoặc tải video."
                          : !approval
                            ? "Duyệt nội dung bản ghép hiện tại để mở tải video có nhãn AI."
                            : "Máy chủ kiểm tra lại quyền, bản duyệt và bằng chứng khi xuất."}
                </p>
            </div>
            <details className="space-y-4 border-t border-control-border pt-4">
                <summary className="min-h-11 cursor-pointer py-3 text-sm font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
                    Quyền sử dụng và lịch sử chi phí
                </summary>
                <div className="space-y-3">
                    <h2 className="font-semibold">Xem xét quyền sử dụng</h2>
                    <p className="text-sm text-text-secondary">
                        Lưu việc người dùng đã xem xét bằng chứng và phạm vi quyền. Đây không phải
                        xác minh pháp lý độc lập.
                    </p>
                    <ul className="space-y-2 text-sm">
                        {(
                            [
                                "source",
                                "product",
                                ...(project.requirements?.requiresCharacter ? ["character"] : []),
                            ] as const
                        ).map((role) => {
                            const key = role as "source" | "product" | "character";
                            const declaration = project.rights?.[key];
                            const verification = declaration?.verification;
                            return (
                                <li key={role} className="rounded-xl bg-surface-soft p-3">
                                    <p>
                                        {key === "source"
                                            ? "Video mẫu"
                                            : key === "product"
                                              ? "Ảnh sản phẩm"
                                              : "Ảnh nhân vật"}{" "}
                                        ·{" "}
                                        {verification?.status === "reviewed"
                                            ? "Đã có người xem xét"
                                            : declaration?.declared
                                              ? "Đã khai báo"
                                              : "Chưa khai báo"}
                                    </p>
                                    {verification?.reviewedBy && (
                                        <p className="break-words text-xs text-text-secondary">
                                            Người xem xét: {verification.reviewedBy}
                                        </p>
                                    )}
                                    {verification?.reviewedAt && (
                                        <time
                                            dateTime={verification.reviewedAt}
                                            className="break-words text-xs text-text-secondary"
                                        >
                                            {verification.reviewedAt}
                                        </time>
                                    )}
                                </li>
                            );
                        })}
                    </ul>
                    {props.onRightsReview && (
                        <div className="space-y-3">
                            <label
                                htmlFor={`${id}-rights-review`}
                                className="block space-y-2 text-sm"
                            >
                                <span>Căn cứ xem xét quyền</span>
                                <Textarea
                                    id={`${id}-rights-review`}
                                    value={rightsNote}
                                    maxLength={4000}
                                    disabled={pending}
                                    onChange={(event) => setRightsNote(event.target.value)}
                                />
                            </label>
                            <Button
                                type="button"
                                variant="outline"
                                disabled={pending || !rightsNote.trim()}
                                onClick={() =>
                                    void run(async () => {
                                        await props.onRightsReview!(rightsNote.trim());
                                        setRightsNote("");
                                    })
                                }
                            >
                                Lưu xem xét quyền
                            </Button>
                            {!rightsNote.trim() && (
                                <p className="text-xs text-text-secondary">
                                    Nhập căn cứ đã xem xét để lưu nhận xét về quyền sử dụng.
                                </p>
                            )}
                        </div>
                    )}
                </div>
                {costs && (
                    <div className="space-y-3">
                        <h2 className="font-semibold">Chi phí đã ghi nhận</h2>
                        <dl className="grid gap-3 text-sm sm:grid-cols-2">
                            <div>
                                <dt className="text-xs text-text-secondary">Phí đã xác định</dt>
                                <dd>{usd(costs.knownActualUsd ?? costs.actualUsd)}</dd>
                            </div>
                            <div>
                                <dt className="text-xs text-text-secondary">Tổng phí thực</dt>
                                <dd>
                                    {costs.actualUsd == null
                                        ? "Chưa xác định đầy đủ"
                                        : usd(costs.actualUsd)}
                                </dd>
                            </div>
                        </dl>
                        <p className="text-xs text-text-secondary">
                            {costs.attemptCount == null
                                ? "Chưa có số lượt từ máy chủ"
                                : `${costs.attemptCount} lượt xử lý đã ghi nhận`}
                            {" · "}
                            {costs.unknownAttemptCount == null
                                ? "Chưa xác định số lượt cần đối soát"
                                : `${costs.unknownAttemptCount} lượt chưa xác định phí`}
                        </p>
                    </div>
                )}
            </details>
            {assemblies.length > 0 && (
                <details className="space-y-3 border-t border-control-border pt-4">
                    <summary className="min-h-11 cursor-pointer py-3 text-sm font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
                        Lịch sử bản ghép
                    </summary>
                    <ul className="space-y-3">
                        {[...assemblies].reverse().map((assembly) => (
                            <li
                                key={assembly.id}
                                className="flex flex-wrap items-center justify-between gap-3 rounded-xl bg-surface-soft p-3"
                            >
                                <div className="min-w-0 text-sm">
                                    <p>
                                        Bản ghép v{assembly.revision}
                                        {active?.id === assembly.id ? " · Đang dùng" : ""}
                                    </p>
                                    <time
                                        dateTime={assembly.createdAt}
                                        className="break-words text-xs text-text-secondary"
                                    >
                                        {assembly.createdAt}
                                    </time>
                                    {assembly.restoredFromAssemblyId && (
                                        <p className="text-xs text-text-secondary">
                                            Tạo từ thao tác khôi phục
                                        </p>
                                    )}
                                </div>
                                <Button
                                    type="button"
                                    variant="outline"
                                    disabled={pending || active?.id === assembly.id}
                                    onClick={() => void run(() => props.onRestore(assembly.id))}
                                >
                                    Khôi phục bản ghép
                                </Button>
                            </li>
                        ))}
                    </ul>
                    <p className="text-xs text-text-secondary">
                        Khôi phục giữ lịch sử và yêu cầu kiểm tra/duyệt lại theo ngữ cảnh hiện tại.
                    </p>
                </details>
            )}
            <details className="space-y-3 border-t border-control-border pt-4">
                <summary className="min-h-11 cursor-pointer py-3 text-sm font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
                    Ngừng dùng và xóa tư liệu dự án
                </summary>
                {project.deletion ? (
                    <div role="status" className="space-y-2 text-sm">
                        <p>Trạng thái Viraldy: {deletionLabel(project.deletion.status)}</p>
                        {project.deletion.reason && (
                            <p className="break-words">Lý do: {project.deletion.reason}</p>
                        )}
                        <p className="text-xs text-text-secondary">
                            Nhà cung cấp:{" "}
                            {project.deletion.providerDeletion === "verified"
                                ? "đã xác nhận xóa theo báo cáo máy chủ"
                                : "chưa xác minh việc xóa"}
                            .
                        </p>
                        {project.deletion.objects && (
                            <p className="text-xs text-text-secondary">
                                {
                                    project.deletion.objects.filter(
                                        (item) => item.status === "deleted",
                                    ).length
                                }
                                /{project.deletion.objects.length} đối tượng đã xác nhận xóa. Các
                                đối tượng dùng chung hoặc cần giữ bằng chứng được báo riêng.
                            </p>
                        )}
                    </div>
                ) : (
                    <div className="space-y-3">
                        <label
                            htmlFor={`${id}-deletion-reason`}
                            className="block space-y-2 text-sm"
                        >
                            <span>Lý do ngừng dùng/xóa</span>
                            <Textarea
                                id={`${id}-deletion-reason`}
                                value={reason}
                                maxLength={4000}
                                disabled={props.busy}
                                onChange={(event) => setReason(event.target.value)}
                            />
                        </label>
                        <label className="flex min-h-11 items-start gap-3 text-sm">
                            <input
                                className="mt-1 size-5 shrink-0 accent-primary"
                                type="checkbox"
                                checked={confirmDelete}
                                onChange={(event) => setConfirmDelete(event.target.checked)}
                            />
                            <span>
                                Tôi muốn ngừng dùng dự án này và yêu cầu xóa tư liệu theo các
                                dependency máy chủ kiểm tra.
                            </span>
                        </label>
                        <Button
                            type="button"
                            variant="outline"
                            disabled={props.busy || !confirmDelete || !reason.trim()}
                            onClick={() => void run(() => props.onDelete(reason.trim()))}
                        >
                            Ngừng dùng và yêu cầu xóa
                        </Button>
                        <p className="text-xs text-text-secondary">
                            File đã tải về và bản lưu tại nhà cung cấp có giới hạn thu hồi riêng.
                        </p>
                    </div>
                )}
            </details>
            {error && (
                <p role="alert" className="text-sm text-destructive">
                    {error}
                </p>
            )}
        </section>
    );
}

function deletionLabel(status: string) {
    return (
        (
            {
                suspended: "Đã ngừng dùng",
                blocked: "Đang bị chặn bởi dependency",
                partial: "Đã xử lý một phần",
                completed: "Đã xử lý",
                failed: "Cần xử lý lại",
            } as Record<string, string>
        )[status] ?? status
    );
}
