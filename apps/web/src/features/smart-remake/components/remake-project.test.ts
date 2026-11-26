import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import type { SmartRemakeProject } from "@/shared/api/smart-remake";
import { RemakeProjectInputs, type RemakeProjectInputsProps } from "./remake-project-inputs";
import { RemakeInspector } from "./remake-inspector";
import { RemakeProjectControls } from "./remake-project-controls";

describe("project seller controls", () => {
    it("keeps optional requirements and character consent reachable without a budget or attestation wall", () => {
        const props: RemakeProjectInputsProps = {
            requirements: {
                intent: "",
                keep: [],
                replace: [],
                forbid: [],
                claims: [],
                requiresCharacter: true,
                characterReferencePolicy: "product_and_character",
            },
            rights: {
                source: { basis: "owned", scope: "", declared: false, evidenceNote: "" },
                product: { basis: "owned", scope: "", declared: false, evidenceNote: "" },
                providerDisclosureAcknowledged: false,
            },
            budget: { capUsd: "", maxAttempts: 20, maxDurationSeconds: 1800 },
            onRequirementsChange: vi.fn(),
            onRightsChange: vi.fn(),
            onBudgetChange: vi.fn(),
            onCharacterChange: vi.fn(),
            onRightsConfirmationOpen: vi.fn(),
            presentation: "details",
        };
        const html = renderToStaticMarkup(createElement(RemakeProjectInputs, props));
        expect(html).toContain("Phải giữ");
        expect(html).toContain("Đồng ý của nhân vật");
        expect(html).toContain("quyền sử dụng ảnh nhân vật");
        expect(html).not.toContain("Trần chi phí (USD)");
        expect(html).not.toContain("Đọc và xác nhận");
    });
    it("keeps explicit rights and character consent without project limit controls", () => {
        const html = renderToStaticMarkup(
            createElement(RemakeProjectInputs, {
                requirements: {
                    intent: "Giới thiệu bình",
                    keep: [],
                    replace: [],
                    forbid: [],
                    claims: [],
                    requiresCharacter: true,
                    characterReferencePolicy: "product_and_character",
                },
                rights: {
                    source: { basis: "owned", scope: "", declared: false, evidenceNote: "" },
                    product: { basis: "owned", scope: "", declared: false, evidenceNote: "" },
                    providerDisclosureAcknowledged: false,
                },
                budget: { capUsd: "", maxAttempts: 20, maxDurationSeconds: 1800 },
                onRequirementsChange: vi.fn(),
                onRightsChange: vi.fn(),
                onRightsConfirmationOpen: vi.fn(),
                onBudgetChange: vi.fn(),
                onCharacterChange: vi.fn(),
            }),
        );
        expect(html).not.toContain("Trần chi phí (USD)");
        expect(html).not.toContain("Giới hạn cho dự án này");
        expect(html).not.toContain("Tối đa lượt trả phí");
        expect(html).not.toContain("Giới hạn thời gian (giây)");
        expect(html).toContain("Ảnh nhân vật gốc");
        expect(html).toContain("Đồng ý của nhân vật");
        expect(html).toContain("Đọc và xác nhận");
        expect(html).toContain("/policies/media-rights");
        expect(html).toContain("Giấy phép, bằng chứng và ghi công (tuỳ chọn)");
        expect(html).not.toContain("Tôi có quyền sử dụng video mẫu");
        expect(html).toContain("mỗi dòng một yêu cầu");
        expect(html).not.toContain('value="10.00"');
    });

    const assembly = {
        id: "assembly",
        mediaHash: "hash",
        manifestHash: "manifest",
        constraintsHash: "constraints",
        revision: 3,
        createdAt: "2026-11-25T00:00:00Z",
    };
    const report = {
        id: "report",
        status: "needs_review",
        subject: {
            kind: "assembly",
            projectId: "project",
            assemblyId: "assembly",
            mediaHash: "hash",
        },
        constraintsHash: "constraints",
        manifestHash: "manifest",
        checkedAt: "2026-11-25T00:00:00Z",
        checkerVersion: "1",
        rubricVersion: "1",
        coverage: [{ requirementId: "product", status: "insufficient_evidence", evidence: [] }],
        findings: [
            {
                id: "finding",
                requirementId: "rights",
                category: "rights",
                severity: "critical",
                status: "failed",
                expected: "Có quyền",
                observed: "Chưa xác nhận",
                evidence: [],
                suggestedAction: "Bổ sung quyền",
            },
        ],
    };
    const project = {
        id: "project",
        revision: 3,
        scenes: [],
        assemblies: { records: [assembly], activeAssemblyId: "assembly" },
        inspectionSummary: { reports: [report], reviews: [] },
        release: { activeApprovalId: null },
        budget: {
            policy: { capUsd: "5", maxAttempts: 20, maxDurationSeconds: 1800 },
            actualUsd: null,
            unknownAttemptCount: 1,
            knownActualUsd: "0.50",
            reservedUsd: "1.00",
        },
    } as unknown as SmartRemakeProject;
    it("shows uncertainty and does not offer a hard finding acceptance", () => {
        const html = renderToStaticMarkup(
            createElement(RemakeInspector, {
                project,
                busy: false,
                currentReportIds: ["report"],
                onInspect: vi.fn(),
                onReview: vi.fn(),
                onSeek: vi.fn(),
            }),
        );
        expect(html).toContain("Cần xem xét");
        expect(html).toContain("Chưa đủ bằng chứng");
        expect(html).toContain("Lỗi bắt buộc xử lý");
        expect(html).not.toContain("Chấp nhận finding");
    });
    it("shows server unknown cost and blocks export without current approval", () => {
        const html = renderToStaticMarkup(
            createElement(RemakeProjectControls, {
                project,
                busy: false,
                currentReportIds: ["report"],
                onApprove: vi.fn(),
                onExport: vi.fn(),
                onRestore: vi.fn(),
                onDelete: vi.fn(),
            }),
        );
        expect(html).toContain("Chưa xác định đầy đủ");
        expect(html).toContain("1 lượt chưa xác định phí");
        const button = (html.match(/<button[^>]*>[\s\S]*?<\/button>/g) ?? []).find((value) =>
            value.includes("Tải bản có nhãn AI"),
        );
        expect(button).toContain('disabled=""');
        expect(html).not.toContain("href=");
    });
});
