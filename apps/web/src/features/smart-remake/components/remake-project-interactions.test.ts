// @vitest-environment jsdom
import { createElement, Fragment, useState } from "react";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type {
    SmartRemakeProject,
    SmartRemakeInspectionReport,
    SmartRemakeRequirements,
    SmartRemakeRights,
    SmartRemakeBudgetPolicy,
} from "@/shared/api/smart-remake";
import { RemakeRightsConfirmation } from "./remake-rights-confirmation";
import { RemakeProjectInputs } from "./remake-project-inputs";
import { RemakeInspector, type RemakeInspectorProps } from "./remake-inspector";
import { RemakeProjectControls, type RemakeProjectControlsProps } from "./remake-project-controls";

afterEach(cleanup);
const hash = "a".repeat(64);
const evidence = {
    mediaId: "subject",
    mediaHash: hash,
    timebase: "final" as const,
    inFrame: 24,
    outFrame: 48,
};
const report: SmartRemakeInspectionReport = {
    id: "report",
    schemaVersion: 1,
    subject: { kind: "assembly", projectId: "project", assemblyId: "assembly", mediaHash: hash },
    constraintsHash: "constraints",
    manifestHash: "manifest",
    status: "passed",
    checkedAt: "2026-11-25T00:00:00Z",
    checkerVersion: "1",
    rubricVersion: "1",
    modelProfile: {},
    coverage: [
        {
            requirementId: "product",
            status: "passed",
            evidence: [evidence],
            sampledFrames: [24, 48],
            unobservedFrames: 0,
            limitations: ["Chỉ quan sát frame mẫu"],
        },
    ],
    findings: [
        {
            id: "finding",
            requirementId: "product",
            category: "product",
            severity: "info",
            status: "passed",
            expected: "Bình hồng",
            observed: "Bình hồng",
            evidence: [evidence],
            suggestedAction: "",
        },
    ],
};
const project: SmartRemakeProject = {
    id: "project",
    revision: 3,
    status: "ready",
    schemaVersion: 2,
    targetDuration: 8,
    provider: "kie",
    finalVideoUrl: "/preview.mp4",
    requirements: {
        intent: "Giới thiệu sản phẩm",
        keep: [],
        replace: [],
        forbid: [],
        claims: [],
        requiresCharacter: true,
    },
    scenes: [
        {
            id: "scene",
            index: 0,
            startSecond: 0,
            durationSeconds: 8,
            activeVersionId: "version",
            prompt: "P",
            imagePrompt: "I",
            videoPrompt: "V",
            versions: [
                {
                    id: "version",
                    parentVersionId: null,
                    videoUrl: "/raw.mp4",
                    prompt: "P",
                    imagePrompt: "I",
                    videoPrompt: "V",
                    source: "generated",
                    createdAt: "now",
                    technicalCheck: {
                        status: "passed",
                        findings: [],
                        checkedAt: "now",
                        mediaHash: hash,
                        frameCount: 192,
                    },
                },
            ],
        },
    ],
    assemblies: {
        activeAssemblyId: "assembly",
        records: [
            {
                id: "assembly",
                projectId: "project",
                schemaVersion: 1,
                parentAssemblyId: "old",
                mediaHash: hash,
                manifestHash: "manifest",
                constraintsHash: "constraints",
                contextHash: "context",
                revision: 3,
                createdAt: "now",
                technicalCheck: { status: "passed", mediaHash: hash, frameCount: 192 },
                timeline: { fps: 24, totalFrames: 192, items: [] },
            },
            {
                id: "old",
                projectId: "project",
                schemaVersion: 1,
                parentAssemblyId: null,
                restoredFromAssemblyId: "previous",
                mediaHash: "oldhash",
                manifestHash: "oldmanifest",
                constraintsHash: "constraints",
                contextHash: "context",
                revision: 2,
                createdAt: "earlier",
                technicalCheck: { status: "passed", mediaHash: "oldhash", frameCount: 192 },
                timeline: { fps: 24, totalFrames: 192, items: [] },
            },
        ],
    },
    inspectionSummary: { reports: [report], reviews: [], currentReportIds: ["report"] },
    release: { activeApprovalId: null, approvals: [] },
    budget: {
        policy: { capUsd: "5", maxAttempts: 20, maxDurationSeconds: 1800 },
        actualUsd: "1.50",
        knownActualUsd: "1.50",
        reservedUsd: "0",
        remainingUsd: "3.50",
        attemptCount: 2,
        unknownAttemptCount: 0,
    },
};
const inspectorProps = (overrides: Partial<RemakeInspectorProps> = {}): RemakeInspectorProps => ({
    project,
    busy: false,
    currentReportIds: ["report"],
    onInspect: vi.fn().mockResolvedValue(undefined),
    onReview: vi.fn().mockResolvedValue(undefined),
    onSeek: vi.fn(),
    ...overrides,
});
const controlProps = (
    overrides: Partial<RemakeProjectControlsProps> = {},
): RemakeProjectControlsProps => ({
    project,
    busy: false,
    currentReportIds: ["report"],
    onApprove: vi.fn().mockResolvedValue(undefined),
    onExport: vi.fn().mockResolvedValue(undefined),
    onRestore: vi.fn().mockResolvedValue(undefined),
    onDelete: vi.fn().mockResolvedValue(undefined),
    ...overrides,
});
const disabled = (name: string) =>
    (screen.getByRole("button", { name }) as HTMLButtonElement).disabled;

describe("project input interactions", () => {
    function Inputs({
        changed,
        onCharacterChange = vi.fn(),
    }: {
        changed: (kind: string, value: unknown) => void;
        onCharacterChange?: (file: File | null) => void;
    }) {
        const [requirements, setRequirements] = useState<SmartRemakeRequirements>({
            intent: "",
            keep: [],
            replace: [],
            forbid: [],
            claims: [],
            requiresCharacter: false,
        });
        const declaration = {
            basis: "owned" as const,
            scope: "",
            evidenceNote: "",
            declared: false,
        };
        const [rights, setRights] = useState<SmartRemakeRights>({
            source: declaration,
            product: declaration,
            providerDisclosureAcknowledged: false,
        });
        const [budget, setBudget] = useState<SmartRemakeBudgetPolicy>({
            capUsd: "",
            maxAttempts: 0,
            maxDurationSeconds: 0,
        });
        const [open, setOpen] = useState(false);
        const onRightsChange = (value: SmartRemakeRights) => {
            changed("rights", value);
            setRights(value);
        };
        return createElement(
            Fragment,
            null,
            createElement(RemakeProjectInputs, {
                requirements,
                rights,
                budget,
                characterUrl: "/character.png",
                characterFile: new File(["image"], "character.png", { type: "image/png" }),
                onRequirementsChange: (value) => {
                    changed("requirements", value);
                    setRequirements(value);
                },
                onRightsChange: (value) => {
                    changed("rights", value);
                    setRights(value);
                },
                onBudgetChange: (value) => {
                    changed("budget", value);
                    setBudget(value);
                },
                onCharacterChange,
                onRightsConfirmationOpen: () => setOpen(true),
            }),
            createElement(RemakeRightsConfirmation, {
                open,
                onOpenChange: setOpen,
                rights,
                onConfirm: onRightsChange,
            }),
        );
    }
    it("keeps typed multiline requirements without exposing project licensing limits", () => {
        const changed = vi.fn();
        render(createElement(Inputs, { changed }));
        fireEvent.change(screen.getByLabelText("Mục tiêu video"), {
            target: { value: "Bán bình hồng" },
        });
        for (const label of ["Phải giữ", "Cần thay", "Không được xuất hiện", "Claims được phép"])
            fireEvent.change(screen.getByLabelText(label), {
                target: { value: "Dòng một\nDòng hai\n" },
            });
        expect(changed).toHaveBeenLastCalledWith(
            "requirements",
            expect.objectContaining({
                intent: "Bán bình hồng",
                keep: ["Dòng một", "Dòng hai", ""],
                claims: ["Dòng một", "Dòng hai", ""],
            }),
        );
        expect(screen.queryByLabelText("Trần chi phí (USD)")).toBeNull();
        expect(screen.queryByLabelText("Tối đa lượt trả phí")).toBeNull();
        expect(screen.queryByLabelText("Giới hạn thời gian (giây)")).toBeNull();
        expect(changed.mock.calls.some(([kind]) => kind === "budget")).toBe(false);
    });
    it("can withdraw a confirmation locally without claiming it was saved on the server", () => {
        const changed = vi.fn();
        render(createElement(Inputs, { changed }));
        fireEvent.click(screen.getByRole("button", { name: "Đọc và xác nhận" }));
        const modal = within(screen.getByRole("dialog"));
        for (const checkbox of modal.getAllByRole("checkbox")) fireEvent.click(checkbox);
        fireEvent.click(modal.getByRole("button", { name: "Lưu xác nhận" }));
        expect(screen.queryByRole("button", { name: "Xem lại xác nhận" })).toBeNull();
        fireEvent.click(screen.getByRole("button", { name: "Thu hồi xác nhận" }));
        expect(changed).toHaveBeenLastCalledWith(
            "rights",
            expect.objectContaining({
                attestation: expect.objectContaining({ accepted: false, revoked: true }),
                source: expect.objectContaining({ declared: false, revoked: true }),
                product: expect.objectContaining({ declared: false, revoked: true }),
                providerDisclosureAcknowledged: false,
            }),
        );
        expect(screen.getByRole("button", { name: "Đọc và xác nhận" })).toBeTruthy();
    });
    it("records per-asset rights and separate optional character consent", () => {
        const changed = vi.fn(),
            onCharacterChange = vi.fn();
        render(createElement(Inputs, { changed, onCharacterChange }));
        fireEvent.click(screen.getByRole("button", { name: "Đọc và xác nhận" }));
        const modal = within(screen.getByRole("dialog"));
        for (const checkbox of modal.getAllByRole("checkbox")) fireEvent.click(checkbox);
        fireEvent.click(modal.getByRole("button", { name: "Lưu xác nhận" }));
        expect(screen.getByText("Người dùng đã xác nhận quyền")).toBeTruthy();
        fireEvent.click(screen.getByText("Giấy phép, bằng chứng và ghi công (tuỳ chọn)"));
        fireEvent.change(screen.getByLabelText("Căn cứ quyền · video mẫu"), {
            target: { value: "licensed" },
        });
        fireEvent.change(screen.getAllByLabelText("Phạm vi được dùng")[0], {
            target: { value: "Quảng cáo nội bộ" },
        });
        fireEvent.change(screen.getAllByLabelText("Ghi chú bằng chứng quyền")[0], {
            target: { value: "Giấy phép 123" },
        });
        fireEvent.change(screen.getAllByLabelText("Ghi công nếu có")[0], {
            target: { value: "Tác giả" },
        });
        fireEvent.click(screen.getByLabelText("Có nhân vật cần giữ giống ảnh gốc"));
        const file = new File(["person"], "person.png", { type: "image/png" });
        fireEvent.change(screen.getByLabelText("Ảnh nhân vật gốc"), { target: { files: [file] } });
        expect(onCharacterChange).toHaveBeenCalledWith(file);
        fireEvent.click(screen.getByLabelText("Tôi có quyền sử dụng ảnh nhân vật"));
        fireEvent.click(screen.getByLabelText("Có consent cho việc dùng hình ảnh bằng AI"));
        fireEvent.change(screen.getByLabelText("Phạm vi consent"), {
            target: { value: "AI video" },
        });
        fireEvent.change(screen.getByLabelText("Căn cứ consent"), {
            target: { value: "Văn bản đồng ý" },
        });

        expect(changed).toHaveBeenLastCalledWith(
            "rights",
            expect.objectContaining({
                providerDisclosureAcknowledged: true,
                source: expect.objectContaining({
                    declared: true,
                    basis: "licensed",
                    evidenceNote: "Giấy phép 123",
                    attribution: "Tác giả",
                }),
                character: expect.objectContaining({ declared: true }),
                characterConsent: expect.objectContaining({
                    consented: true,
                    scope: "AI video",
                    evidenceNote: "Văn bản đồng ý",
                }),
            }),
        );
    });
});

describe("Inspector interactions", () => {
    it("uses server current report identities when the caller supplies no override", () => {
        const uncertain = {
            ...report,
            findings: [{ ...report.findings[0], status: "needs_review" as const }],
        };
        render(
            createElement(
                RemakeInspector,
                inspectorProps({
                    currentReportIds: undefined,
                    project: {
                        ...project,
                        inspectionSummary: {
                            reports: [uncertain],
                            reviews: [],
                            currentReportIds: ["report"],
                        },
                    },
                }),
            ),
        );
        expect((screen.getByLabelText("Lý do nhận xét") as HTMLTextAreaElement).disabled).toBe(
            false,
        );
    });
    it("keeps missing coverage explicit and shows requirements that do not apply", () => {
        const props = inspectorProps({
            project: {
                ...project,
                requirements: { ...project.requirements!, requiresCharacter: false },
                inspectionSummary: {
                    reports: [
                        {
                            ...report,
                            subject: { kind: "image", projectId: "project", mediaHash: hash },
                            status: "insufficient_evidence",
                            coverage: [],
                            findings: [],
                            notApplicableRequirements: [
                                { requirementId: "character", reason: "Không yêu cầu nhân vật" },
                            ],
                        },
                    ],
                    reviews: [],
                },
            },
        });
        const view = render(createElement(RemakeInspector, props));
        expect(
            screen.getByText("Không có finding không đồng nghĩa nội dung đã đạt."),
        ).toBeDefined();
        expect(screen.getByText(/Không yêu cầu nhân vật/)).toBeDefined();
        view.rerender(
            createElement(RemakeInspector, {
                ...props,
                project: { ...props.project, inspectionSummary: { reports: [], reviews: [] } },
            }),
        );
        expect(screen.getByText(/Chưa có báo cáo kiểm tra/)).toBeDefined();
    });
    it("queues only a selected owned subject and seeks evidence in its media clock", async () => {
        const props = inspectorProps();
        render(createElement(RemakeInspector, props));
        fireEvent.click(screen.getByRole("button", { name: "Kiểm tra bằng AI" }));
        await waitFor(() =>
            expect(props.onInspect).toHaveBeenCalledWith({
                kind: "assembly",
                assemblyId: "assembly",
            }),
        );
        fireEvent.change(screen.getByLabelText("Kiểm tra tư liệu"), {
            target: {
                value: JSON.stringify({ kind: "scene", sceneId: "scene", versionId: "version" }),
            },
        });
        fireEvent.click(screen.getByRole("button", { name: "Kiểm tra bằng AI" }));
        await waitFor(() =>
            expect(props.onInspect).toHaveBeenLastCalledWith({
                kind: "scene",
                sceneId: "scene",
                versionId: "version",
            }),
        );
        fireEvent.click(screen.getByRole("button", { name: /Xem bằng chứng/ }));
        expect(props.onSeek).toHaveBeenCalledWith(evidence);
        expect(screen.getByText("Chỉ quan sát frame mẫu")).toBeDefined();
    });
    it("requires a reason and submits semantic acceptance separately from content approval", async () => {
        const uncertain = {
            ...report,
            status: "needs_review" as const,
            findings: [
                {
                    ...report.findings[0],
                    status: "needs_review" as const,
                    severity: "warning" as const,
                },
            ],
        };
        const props = inspectorProps({
            project: { ...project, inspectionSummary: { reports: [uncertain], reviews: [] } },
        });
        render(createElement(RemakeInspector, props));
        expect(disabled("Chấp nhận finding")).toBe(true);
        fireEvent.change(screen.getByLabelText("Lý do nhận xét"), {
            target: { value: "  Đã đối chiếu ảnh gốc  " },
        });
        fireEvent.click(screen.getByRole("button", { name: "Chấp nhận finding" }));
        await waitFor(() =>
            expect(props.onReview).toHaveBeenCalledWith(
                "report",
                "finding",
                "accept",
                "Đã đối chiếu ảnh gốc",
            ),
        );
        expect((screen.getByLabelText("Lý do nhận xét") as HTMLTextAreaElement).value).toBe("");
    });
    it("disables stale review and offers no acceptance for hard failures", async () => {
        const hard = {
            ...report,
            status: "failed" as const,
            findings: [
                {
                    ...report.findings[0],
                    status: "failed" as const,
                    category: "rights",
                    blocking: true,
                },
            ],
        };
        const props = inspectorProps({
            project: { ...project, inspectionSummary: { reports: [hard], reviews: [] } },
            currentReportIds: [],
        });
        const view = render(createElement(RemakeInspector, props));
        expect(screen.queryByRole("button", { name: "Chấp nhận finding" })).toBeNull();
        expect((screen.getByLabelText("Lý do nhận xét") as HTMLTextAreaElement).disabled).toBe(
            true,
        );
        expect(disabled("Bác bỏ finding")).toBe(true);
        view.rerender(createElement(RemakeInspector, { ...props, currentReportIds: ["report"] }));
        fireEvent.change(screen.getByLabelText("Lý do nhận xét"), {
            target: { value: "Cần bổ sung quyền" },
        });
        fireEvent.click(screen.getByRole("button", { name: "Bác bỏ finding" }));
        await waitFor(() =>
            expect(props.onReview).toHaveBeenCalledWith(
                "report",
                "finding",
                "reject",
                "Cần bổ sung quyền",
            ),
        );
    });
    it("shows operation errors and retains review text after an unsuccessful save", async () => {
        const uncertain = {
            ...report,
            findings: [{ ...report.findings[0], status: "needs_review" as const }],
        };
        const props = inspectorProps({
            project: {
                ...project,
                inspectionSummary: {
                    reports: [uncertain],
                    reviews: [
                        {
                            reportId: "report",
                            findingId: "finding",
                            decision: "reject",
                            reason: "Bản trước cần sửa",
                            actorId: "actor",
                            reviewedAt: "now",
                        },
                    ],
                },
            },
            onInspect: vi.fn().mockRejectedValue(new Error("offline")),
            onReview: vi.fn().mockRejectedValue(new Error("stale")),
        });
        render(createElement(RemakeInspector, props));
        fireEvent.click(screen.getByRole("button", { name: "Kiểm tra bằng AI" }));
        await waitFor(() =>
            expect(screen.getByText(/Chưa gửi được yêu cầu kiểm tra/)).toBeDefined(),
        );
        fireEvent.change(screen.getByLabelText("Lý do nhận xét"), { target: { value: "Xem lại" } });
        fireEvent.click(screen.getByRole("button", { name: "Bác bỏ finding" }));
        await waitFor(() => expect(screen.getByText(/Chưa lưu được nhận xét/)).toBeDefined());
        expect((screen.getByLabelText("Lý do nhận xét") as HTMLTextAreaElement).value).toBe(
            "Xem lại",
        );
        expect(screen.getByText(/Bản trước cần sửa/)).toBeDefined();
    });
});

describe("checked release controls", () => {
    it("shows a stale approval notice only when an approval actually existed", () => {
        const fresh = {
            ...project,
            release: {
                activeApprovalId: null,
                approvals: [],
                invalidationReason: "context_changed",
            },
        };
        const view = render(createElement(RemakeProjectControls, controlProps({ project: fresh })));
        expect(screen.queryByText(/Bản duyệt trước đã hết hiệu lực/)).toBeNull();
        expect(disabled("Duyệt nội dung bản ghép này")).toBe(false);
        expect(disabled("Tải bản có nhãn AI")).toBe(true);
        view.rerender(
            createElement(
                RemakeProjectControls,
                controlProps({
                    project: {
                        ...fresh,
                        release: {
                            ...fresh.release,
                            approvals: [
                                {
                                    id: "old-approval",
                                    status: "invalidated",
                                    assemblyId: "old",
                                    reportId: "old-report",
                                    mediaHash: "oldhash",
                                    manifestHash: "oldmanifest",
                                    constraintsHash: "oldconstraints",
                                    approvedAt: "earlier",
                                },
                            ],
                        },
                    },
                }),
            ),
        );
        expect(screen.getByText(/Bản duyệt trước đã hết hiệu lực/)).toBeTruthy();
        expect(disabled("Duyệt nội dung bản ghép này")).toBe(false);
        expect(disabled("Tải bản có nhãn AI")).toBe(true);
    });
    it("records explicit human rights review without claiming verified legal ownership", async () => {
        const declaration = {
            basis: "owned" as const,
            scope: "AI processing",
            evidenceNote: "Self authored",
            declared: true,
            verification: {
                status: "reviewed",
                reviewedBy: "reviewer-1",
                reviewedAt: "2026-11-25T00:00:00Z",
            },
        };
        const props = controlProps({
            project: {
                ...project,
                rights: {
                    source: declaration,
                    product: { ...declaration, verification: { status: "declared" } },
                    providerDisclosureAcknowledged: true,
                },
            },
            onRightsReview: vi.fn().mockResolvedValue(undefined),
        });
        render(createElement(RemakeProjectControls, props));
        expect(screen.getByText(/reviewer-1/)).toBeDefined();
        expect(disabled("Lưu xem xét quyền")).toBe(true);
        fireEvent.change(screen.getByLabelText("Căn cứ xem xét quyền"), {
            target: { value: "  Đã đọc giấy phép và phạm vi  " },
        });
        fireEvent.click(screen.getByRole("button", { name: "Lưu xem xét quyền" }));
        await waitFor(() =>
            expect(props.onRightsReview).toHaveBeenCalledWith("Đã đọc giấy phép và phạm vi"),
        );
        expect(screen.queryByText("Quyền đã được xác minh")).toBeNull();
    });
    it("approves the current assembly/report and exports only after an active matching approval", async () => {
        const props = controlProps(),
            view = render(createElement(RemakeProjectControls, props));
        expect(disabled("Duyệt nội dung bản ghép này")).toBe(false);
        expect(disabled("Tải bản có nhãn AI")).toBe(true);
        fireEvent.click(screen.getByRole("button", { name: "Duyệt nội dung bản ghép này" }));
        await waitFor(() => expect(props.onApprove).toHaveBeenCalledWith("assembly", "report"));
        const approved: SmartRemakeProject = {
            ...project,
            release: {
                activeApprovalId: "approval",
                approvals: [
                    {
                        id: "approval",
                        status: "approved",
                        assemblyId: "assembly",
                        reportId: "report",
                        mediaHash: hash,
                        manifestHash: "manifest",
                        constraintsHash: "constraints",
                        approvedAt: "now",
                    },
                ],
            },
        };
        view.rerender(createElement(RemakeProjectControls, { ...props, project: approved }));
        fireEvent.click(screen.getByRole("button", { name: "Tải bản có nhãn AI" }));
        await waitFor(() => expect(props.onExport).toHaveBeenCalledWith("assembly"));
        expect(disabled("Duyệt nội dung bản ghép này")).toBe(true);
        view.rerender(
            createElement(RemakeProjectControls, {
                ...props,
                project: approved,
                currentReportIds: [],
            }),
        );
        expect(disabled("Tải bản có nhãn AI")).toBe(true);
        expect(screen.queryByRole("link")).toBeNull();
    });
    it("restores an immutable assembly through the explicit history action", async () => {
        const props = controlProps();
        render(createElement(RemakeProjectControls, props));
        fireEvent.click(screen.getByText("Lịch sử bản ghép"));
        const activeHistory = screen.getByText("Bản ghép v3 · Đang dùng").closest("li")!;
        expect(
            (
                within(activeHistory).getByRole("button", {
                    name: "Khôi phục bản ghép",
                }) as HTMLButtonElement
            ).disabled,
        ).toBe(true);
        fireEvent.click(
            within(screen.getByText("Bản ghép v2").closest("li")!).getByRole("button", {
                name: "Khôi phục bản ghép",
            }),
        );
        await waitFor(() => expect(props.onRestore).toHaveBeenCalledWith("old"));
    });
    it("requires a reason and explicit deletion confirmation", async () => {
        const props = controlProps();
        render(createElement(RemakeProjectControls, props));
        fireEvent.click(screen.getByText("Ngừng dùng và xóa tư liệu dự án"));
        expect(disabled("Ngừng dùng và yêu cầu xóa")).toBe(true);
        fireEvent.change(screen.getByLabelText("Lý do ngừng dùng/xóa"), {
            target: { value: "  Thu hồi quyền  " },
        });
        expect(disabled("Ngừng dùng và yêu cầu xóa")).toBe(true);
        fireEvent.click(
            screen.getByLabelText(
                "Tôi muốn ngừng dùng dự án này và yêu cầu xóa tư liệu theo các dependency máy chủ kiểm tra.",
            ),
        );
        fireEvent.click(screen.getByRole("button", { name: "Ngừng dùng và yêu cầu xóa" }));
        await waitFor(() => expect(props.onDelete).toHaveBeenCalledWith("Thu hồi quyền"));
    });
    it("displays server progress and actual charges without project licensing limits", () => {
        const pending: SmartRemakeProject = {
            ...project,
            pendingOperation: {
                id: "operation",
                status: "running",
                kind: "inspection",
                needsReconciliation: false,
                progress: { stage: "inspection", completed: 1, total: 2 },
            },
            deletion: {
                status: "partial",
                reason: "evidence_retention",
                providerDeletion: "unverified",
                objects: [
                    { keyHash: "one", status: "deleted" },
                    { keyHash: "two", status: "retained_shared" },
                ],
            },
        };
        render(createElement(RemakeProjectControls, controlProps({ project: pending })));
        expect(screen.getByText("Kiểm tra nội dung")).toBeDefined();
        expect(screen.getByText("1/2 công việc theo máy chủ")).toBeDefined();
        expect(screen.getByText("Chi phí đã ghi nhận")).toBeDefined();
        expect(screen.queryByText(/Còn trong trần|Trần dự án/)).toBeNull();
        expect(screen.queryByText("2/20 lượt")).toBeNull();
        fireEvent.click(screen.getByText("Ngừng dùng và xóa tư liệu dự án"));
        expect(screen.getByText(/Đã xử lý một phần/)).toBeDefined();
        expect(screen.getByText(/chưa xác minh việc xóa/)).toBeDefined();
        expect(disabled("Duyệt nội dung bản ghép này")).toBe(true);
    });
    it("shows a recoverable error when the backend rejects a current-looking approval", async () => {
        const props = controlProps({
            onApprove: vi.fn().mockRejectedValue(new Error("rights revoked")),
        });
        render(createElement(RemakeProjectControls, props));
        fireEvent.click(screen.getByRole("button", { name: "Duyệt nội dung bản ghép này" }));
        await waitFor(() =>
            expect(screen.getByRole("alert").textContent).toContain("Chưa hoàn tất thao tác"),
        );
    });
});
