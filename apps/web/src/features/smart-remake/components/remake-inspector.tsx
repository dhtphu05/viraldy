import { useId, useState } from "react";
import type {
    SmartRemakeProject,
    SmartRemakeInspectionReport,
    SmartRemakeInspectionFinding,
    SmartRemakeInspectionEvidence,
    SmartRemakeInspectSubject,
} from "@/shared/api/smart-remake";
import { Button } from "@/shared/ui/button";
import { Textarea } from "@/shared/ui/textarea";
import { getRemakeSceneLabel } from "../lib/remake-scene-label";
import {
    canReviewInspectionFinding,
    getInspectionExpectationDisplay,
    getInspectionRequirementLabel,
    getSceneLocalInspectionEvidence,
} from "../lib/remake-inspection";

export interface RemakeInspectorProps {
    project: SmartRemakeProject;
    busy: boolean;
    currentReportIds?: string[];
    onInspect(subject: SmartRemakeInspectSubject): Promise<unknown>;
    onReview(
        reportId: string,
        findingId: string,
        decision: "accept" | "reject",
        reason: string,
    ): Promise<unknown>;
    onSeek(evidence: SmartRemakeInspectionEvidence): void;
}
const inspectionStatusLabels = {
    passed: "Đạt",
    failed: "Cần sửa",
    needs_review: "Cần xem xét",
    insufficient_evidence: "Chưa đủ bằng chứng",
} as const;
const clockLabels = {
    source: "Video mẫu",
    raw_group: "Clip AI gốc",
    scene_local: "Đoạn cảnh",
    final: "Video đã ghép",
};

export function RemakeInspector(props: RemakeInspectorProps) {
    const { project } = props;
    const id = useId();
    const activeAssemblyId = project.assemblies?.activeAssemblyId;
    const subjects: { label: string; subject: SmartRemakeInspectSubject }[] = [
        ...(activeAssemblyId
            ? [
                  {
                      label: "Video MP4 đã ghép",
                      subject: { kind: "assembly" as const, assemblyId: activeAssemblyId },
                  },
              ]
            : []),
        ...project.scenes.flatMap((scene) =>
            scene.versions.map((version, index) => ({
                label: `${getRemakeSceneLabel(project, scene.id, scene.index)} · bản ${index + 1}${version.id === scene.activeVersionId ? " đang dùng" : " để so sánh"}`,
                subject: { kind: "scene" as const, sceneId: scene.id, versionId: version.id },
            })),
        ),
        { label: "Ảnh sản phẩm gốc", subject: { kind: "image", imageRole: "product" } },
        ...(project.requirements?.requiresCharacter
            ? [
                  {
                      label: "Ảnh nhân vật gốc",
                      subject: { kind: "image" as const, imageRole: "character" as const },
                  },
              ]
            : []),
    ];
    const [selection, setSelection] = useState("");
    const [error, setError] = useState<string | null>(null);
    const selected =
        subjects.find((item) => JSON.stringify(item.subject) === selection) ?? subjects[0];
    const reports = project.inspectionSummary?.reports ?? [];
    const currentReportIds =
        props.currentReportIds ?? project.inspectionSummary?.currentReportIds ?? [];
    async function inspect() {
        if (!selected || props.busy) return;
        setError(null);
        try {
            await props.onInspect(selected.subject);
        } catch {
            setError("Chưa gửi được yêu cầu kiểm tra. Kiểm tra trạng thái dự án rồi thử lại.");
        }
    }
    return (
        <section
            aria-label="Inspector nội dung"
            className="min-w-0 space-y-4 rounded-3xl bg-surface p-5 sm:p-6"
        >
            <div>
                <h2 className="font-semibold">Kiểm tra nội dung</h2>
                <p className="mt-2 text-sm text-text-secondary">
                    Đối chiếu tư liệu gốc, yêu cầu và đúng đoạn được dùng. Kết quả AI có thể cần
                    người xem xét.
                </p>
            </div>
            <div className="flex flex-wrap items-end gap-3">
                <label className="min-w-0 flex-1 space-y-2 text-sm" htmlFor={`${id}-subject`}>
                    <span>Kiểm tra tư liệu</span>
                    <select
                        id={`${id}-subject`}
                        className="min-h-11 w-full rounded-xl bg-surface-soft px-3 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                        disabled={props.busy}
                        value={selected ? JSON.stringify(selected.subject) : ""}
                        onChange={(event) => setSelection(event.target.value)}
                    >
                        {subjects.map((item) => (
                            <option
                                key={JSON.stringify(item.subject)}
                                value={JSON.stringify(item.subject)}
                            >
                                {item.label}
                            </option>
                        ))}
                    </select>
                </label>
                <Button
                    type="button"
                    disabled={props.busy || !selected}
                    onClick={() => void inspect()}
                >
                    Kiểm tra bằng AI
                </Button>
            </div>
            <p className="text-xs text-text-secondary">
                AI kiểm tra đúng tư liệu, cảnh hoặc bản ghép bạn chọn và chỉ rõ phần cần xem lại.
                {props.busy ? " Tác vụ hiện tại cần hoàn tất trước khi kiểm tra mới." : ""}
            </p>
            {error && (
                <p role="alert" className="text-sm text-destructive">
                    {error}
                </p>
            )}
            {!reports.length && (
                <p role="status" className="text-sm text-text-secondary">
                    Chưa có báo cáo kiểm tra. Chọn clip hoặc ghép preview để kiểm tra bản cuối.
                </p>
            )}
            {[...reports].reverse().map((report) => (
                <Report
                    key={report.id}
                    report={report}
                    current={currentReportIds.includes(report.id) && !report.stale}
                    {...props}
                />
            ))}
        </section>
    );
}

function Report({
    report,
    current,
    ...props
}: RemakeInspectorProps & { report: SmartRemakeInspectionReport; current: boolean }) {
    const coverage = Array.isArray(report.coverage) ? report.coverage : [];
    return (
        <article
            data-inspection-report-id={report.id}
            className="min-w-0 space-y-4 rounded-2xl bg-surface-soft p-4"
        >
            <div className="flex flex-wrap justify-between gap-2">
                <h3 className="text-sm font-semibold">
                    {report.subject.kind === "assembly"
                        ? "Video đã ghép"
                        : report.subject.kind === "scene"
                          ? "Phiên bản cảnh"
                          : "Ảnh tham chiếu"}{" "}
                    · {inspectionStatusLabels[report.status]}
                </h3>
                <span className="text-xs text-text-secondary">
                    {current ? "Đúng ngữ cảnh hiện tại" : "Báo cáo cũ · cần kiểm tra lại"}
                </span>
            </div>
            <details>
                <summary className="min-h-11 cursor-pointer py-3 text-xs text-text-secondary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
                    Thông tin báo cáo
                </summary>
                <p className="text-xs text-text-secondary">
                    Bộ kiểm tra {report.checkerVersion} · rubric {report.rubricVersion} ·{" "}
                    <time dateTime={report.checkedAt}>{report.checkedAt}</time>
                </p>
            </details>
            <div>
                <h4 className="text-sm font-medium">Phạm vi đã quan sát</h4>
                {coverage.length ? (
                    <ul className="mt-2 space-y-2 text-xs text-text-secondary">
                        {coverage.map((item, index) => (
                            <li
                                key={`${item.requirementId}-${index}`}
                                className="rounded-xl bg-surface p-3"
                            >
                                <span className="font-medium">
                                    {getInspectionRequirementLabel(
                                        item.requirementId,
                                        props.project.scenes,
                                        props.project,
                                    )}
                                </span>{" "}
                                ·{" "}
                                {inspectionStatusLabels[
                                    item.status as keyof typeof inspectionStatusLabels
                                ] ?? "Chưa đủ bằng chứng"}
                                {Array.isArray(item.sampledFrames) && (
                                    <span> · {item.sampledFrames.length} frame mẫu</span>
                                )}
                                {typeof item.unobservedFrames === "number" && (
                                    <span> · {item.unobservedFrames} frame chưa quan sát</span>
                                )}
                                {Array.isArray(item.limitations) &&
                                    item.limitations.map((limitation: string, i: number) => (
                                        <p key={i} className="mt-1">
                                            {limitation}
                                        </p>
                                    ))}
                            </li>
                        ))}
                    </ul>
                ) : (
                    <p className="mt-2 text-xs text-text-secondary">
                        Chưa đủ bằng chứng về phạm vi quan sát.
                    </p>
                )}
            </div>
            {report.notApplicableRequirements?.map((item) => (
                <p key={item.requirementId} className="text-xs text-text-secondary">
                    {getInspectionRequirementLabel(
                        item.requirementId,
                        props.project.scenes,
                        props.project,
                    )}{" "}
                    · Không áp dụng: {item.reason}
                </p>
            ))}
            {report.findings.map((finding) => (
                <Finding
                    key={finding.id}
                    finding={finding}
                    report={report}
                    current={current}
                    {...props}
                />
            ))}
            {!report.findings.length && (
                <p className="text-sm text-text-secondary">
                    Không có finding không đồng nghĩa nội dung đã đạt.
                </p>
            )}
        </article>
    );
}

function Finding({
    finding,
    report,
    current,
    ...props
}: RemakeInspectorProps & {
    finding: SmartRemakeInspectionFinding;
    report: SmartRemakeInspectionReport;
    current: boolean;
}) {
    const id = useId();
    const reportId = report.id;
    const [reason, setReason] = useState("");
    const [error, setError] = useState<string | null>(null);
    const expected = getInspectionExpectationDisplay(finding.expected);
    const canAccept = canReviewInspectionFinding(finding, "accept");
    const hard = finding.status !== "passed" && !canAccept;
    const previous = props.project.inspectionSummary?.reviews
        .filter((review) => review.reportId === reportId && review.findingId === finding.id)
        .at(-1);
    async function review(decision: "accept" | "reject") {
        if (
            !current ||
            props.busy ||
            !reason.trim() ||
            !canReviewInspectionFinding(finding, decision)
        )
            return;
        setError(null);
        try {
            await props.onReview(reportId, finding.id, decision, reason.trim());
            setReason("");
        } catch {
            setError("Chưa lưu được nhận xét. Báo cáo có thể đã thay đổi; hãy làm mới dự án.");
        }
    }
    return (
        <div
            data-inspection-finding-id={finding.id}
            tabIndex={-1}
            className="min-w-0 space-y-3 rounded-xl bg-surface p-4"
        >
            <h4 className="text-sm font-medium">
                {getInspectionRequirementLabel(
                    finding.requirementId,
                    props.project.scenes,
                    props.project,
                )}{" "}
                · {inspectionStatusLabels[finding.status]}
            </h4>
            <dl className="space-y-2 text-sm">
                <div>
                    <dt className="text-xs text-text-secondary">Cần có</dt>
                    <dd className="whitespace-pre-wrap break-words">
                        {expected.summary}
                        {expected.details && (
                            <details className="mt-2 text-text-secondary">
                                <summary className="cursor-pointer text-xs font-medium">
                                    Chi tiết yêu cầu AI
                                </summary>
                                <pre
                                    tabIndex={0}
                                    className="mt-2 max-h-72 overflow-auto whitespace-pre-wrap break-words rounded-lg bg-surface-soft p-3 text-xs"
                                >
                                    {expected.details}
                                </pre>
                            </details>
                        )}
                    </dd>
                </div>
                <div>
                    <dt className="text-xs text-text-secondary">Quan sát được</dt>
                    <dd className="whitespace-pre-wrap break-words">{finding.observed}</dd>
                </div>
            </dl>
            {finding.suggestedAction && (
                <p className="text-sm text-text-secondary">{finding.suggestedAction}</p>
            )}
            {hard && (
                <p className="text-xs font-medium text-destructive">
                    Lỗi bắt buộc xử lý hoặc chưa đủ bằng chứng · cần sửa/kiểm tra lại, không thể bỏ
                    qua.
                </p>
            )}
            <div className="flex flex-wrap gap-2">
                {finding.evidence.map((evidence, index) => {
                    const local = getSceneLocalInspectionEvidence(
                        report,
                        evidence,
                        props.project.inspectionMedia ?? [],
                        props.project.inspectionMappings ?? [],
                    );
                    return (
                        <span key={`${evidence.mediaId}-${index}`} className="flex flex-wrap gap-2">
                            <Button
                                type="button"
                                variant="outline"
                                className="min-h-11 text-xs"
                                onClick={() => props.onSeek(evidence)}
                            >
                                {evidence.inFrame == null
                                    ? "Xem ảnh bằng chứng"
                                    : `Xem bằng chứng · ${clockLabels[evidence.timebase as keyof typeof clockLabels] ?? "Tư liệu"} · frame ${evidence.inFrame}–${evidence.outFrame}`}
                            </Button>
                            {local && (
                                <Button
                                    type="button"
                                    variant="outline"
                                    className="min-h-11 text-xs"
                                    onClick={() => props.onSeek(local)}
                                >
                                    Trong cảnh · frame {local.inFrame}–{local.outFrame}
                                </Button>
                            )}
                        </span>
                    );
                })}
            </div>
            {previous && (
                <p className="text-xs text-text-secondary">
                    Nhận xét đã lưu: {previous.decision === "accept" ? "Chấp nhận" : "Bác bỏ"} ·{" "}
                    {previous.reason}
                </p>
            )}
            {finding.status !== "passed" && (
                <div className="space-y-2">
                    <label htmlFor={`${id}-reason`} className="text-xs font-medium">
                        Lý do nhận xét
                    </label>
                    <Textarea
                        id={`${id}-reason`}
                        value={reason}
                        maxLength={4000}
                        disabled={props.busy || !current}
                        onChange={(event) => setReason(event.target.value)}
                    />
                    <div className="flex flex-wrap gap-2">
                        {canAccept && (
                            <Button
                                type="button"
                                disabled={props.busy || !current || !reason.trim()}
                                onClick={() => void review("accept")}
                            >
                                Chấp nhận finding
                            </Button>
                        )}
                        <Button
                            type="button"
                            variant="outline"
                            disabled={props.busy || !current || !reason.trim()}
                            onClick={() => void review("reject")}
                        >
                            Bác bỏ finding
                        </Button>
                    </div>
                </div>
            )}
            {error && (
                <p role="alert" className="text-xs text-destructive">
                    {error}
                </p>
            )}
        </div>
    );
}
