// @vitest-environment jsdom
import { createElement } from "react";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import type { SmartRemakeInspectionReport, SmartRemakeProject } from "@/shared/api/smart-remake";
import { RemakeInspector } from "./remake-inspector";

afterEach(cleanup);

it("keeps structured requirements collapsed while preserving evidence and review identity", async () => {
    const evidence = { mediaId: "product", mediaHash: "a".repeat(64) };
    const facts = { shotPlan: { stateBefore: "closed", action: "open lid" }, userEdits: "" };
    const expected = `Match the intended opening state. ${JSON.stringify(facts)}`;
    const report: SmartRemakeInspectionReport = {
        id: "report",
        schemaVersion: 1,
        checkerVersion: "1.2",
        rubricVersion: "2",
        modelProfile: {},
        checkedAt: "now",
        constraintsHash: "constraints",
        manifestHash: "manifest",
        status: "needs_review",
        subject: {
            kind: "image",
            projectId: "project",
            mediaHash: "b".repeat(64),
        },
        findings: [
            {
                id: "finding",
                requirementId: "scene:saved-uuid:opening",
                category: "structure",
                expected,
                observed: "Review the lid position",
                status: "needs_review",
                severity: "warning",
                suggestedAction: "Review",
                evidence: [evidence],
            },
        ],
        coverage: [
            {
                requirementId: "scene:saved-uuid:opening",
                status: "needs_review",
                evidence: [evidence],
                sampledFrames: [],
                unobservedFrames: 0,
                limitations: [],
            },
        ],
    };
    const project: SmartRemakeProject = {
        id: "project",
        revision: 1,
        status: "ready",
        targetDuration: 8,
        provider: "kie",
        finalVideoUrl: "",
        scenes: [
            {
                id: "saved-uuid",
                index: 2,
                startSecond: 0,
                durationSeconds: 8,
                activeVersionId: null,
                prompt: "",
                imagePrompt: "",
                videoPrompt: "",
                versions: [],
            },
        ],
        inspectionSummary: { reports: [report], reviews: [], currentReportIds: [report.id] },
    };
    const onSeek = vi.fn();
    const onReview = vi.fn().mockResolvedValue(undefined);
    const view = render(
        createElement(RemakeInspector, {
            project,
            busy: false,
            onSeek,
            onReview,
            onInspect: vi.fn(),
        }),
    );

    expect(
        screen.getByRole("heading", { name: "Cảnh 3 · Khung mở đầu · Cần xem xét" }),
    ).toBeTruthy();
    expect(screen.getByText("Match the intended opening state.")).toBeTruthy();
    expect(screen.queryByText("scene:saved-uuid:opening")).toBeNull();
    const details = screen.getByText("Chi tiết yêu cầu AI").closest("details")!;
    expect(details.open).toBe(false);
    expect(screen.getByText("Chi tiết yêu cầu AI")).toBeTruthy();
    expect(JSON.parse(details.querySelector("pre")!.textContent!)).toEqual(facts);
    expect(report.findings[0].expected).toBe(expected);

    fireEvent.click(screen.getByRole("button", { name: "Xem ảnh bằng chứng" }));
    expect(onSeek).toHaveBeenCalledWith(evidence);
    fireEvent.change(screen.getByLabelText("Lý do nhận xét"), {
        target: { value: "Đã kiểm tra nắp" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Chấp nhận finding" }));
    expect(onReview).toHaveBeenCalledWith("report", "finding", "accept", "Đã kiểm tra nắp");
});
