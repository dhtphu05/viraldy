// @vitest-environment jsdom
import { createElement } from "react";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { SmartRemakeInspectionReport, SmartRemakeProject } from "@/shared/api/smart-remake";
import { RemakeInspector } from "./remake-inspector";

afterEach(cleanup);
const hash = "a".repeat(64);
const evidence = {
    mediaId: "subject",
    mediaHash: hash,
    timebase: "raw_group" as const,
    inFrame: 132,
    outFrame: 144,
};
const report: SmartRemakeInspectionReport = {
    id: "saved-report",
    schemaVersion: 1,
    checkerVersion: "1",
    rubricVersion: "1",
    modelProfile: {},
    checkedAt: "now",
    constraintsHash: "constraints",
    contextHash: "saved-context",
    manifestHash: "saved-manifest",
    stale: true,
    status: "needs_review",
    subject: {
        kind: "scene",
        projectId: "project",
        sceneId: "scene",
        versionId: "version",
        mediaHash: hash,
        range: { inFrame: 120, outFrame: 168, fps: 24, timebase: "raw_group" },
    },
    findings: [
        {
            id: "finding",
            requirementId: "action",
            category: "action",
            status: "needs_review",
            severity: "warning",
            expected: "Open lid",
            observed: "Open lid at sampled frame",
            suggestedAction: "Review",
            evidence: [evidence],
        },
    ],
    coverage: [],
};
const metadata = {
    reportId: report.id,
    contextHash: report.contextHash,
    manifestHash: report.manifestHash,
    sceneId: "scene",
    versionId: "version",
};
const raw = {
    mediaId: "subject",
    mediaHash: hash,
    timebase: "raw_group" as const,
    frameCount: 192,
    url: "/raw.mp4",
};
const virtual = {
    mediaId: "scene-local:saved-report-binding",
    mediaHash: hash,
    timebase: "scene_local" as const,
    frameCount: 48,
    url: raw.url,
    playbackTimebase: "raw_group" as const,
    playbackMediaId: raw.mediaId,
    playbackMediaHash: hash,
    ...metadata,
};
const mapping = {
    from: {
        mediaId: virtual.mediaId,
        mediaHash: hash,
        timebase: "scene_local" as const,
        inFrame: 0,
        outFrame: 48,
    },
    to: {
        mediaId: raw.mediaId,
        mediaHash: hash,
        timebase: "raw_group" as const,
        inFrame: 120,
        outFrame: 168,
    },
    ...metadata,
};
const project: SmartRemakeProject = {
    id: "project",
    revision: 10,
    targetDuration: 8,
    status: "ready",
    provider: "kie",
    finalVideoUrl: "/preview.mp4",
    scenes: [],
    inspectionMedia: [raw, virtual],
    inspectionMappings: [mapping],
    inspectionSummary: { reports: [report], reviews: [], currentReportIds: [] },
};

describe("persisted report scene-local evidence buttons", () => {
    it("projects a historical saved report and sends actual virtual evidence without using current draft offsets", () => {
        const onSeek = vi.fn();
        const view = render(
            createElement(RemakeInspector, {
                project,
                busy: false,
                onInspect: vi.fn(),
                onReview: vi.fn(),
                onSeek,
            }),
        );
        const article = view.container.querySelector<HTMLElement>(
            '[data-inspection-report-id="saved-report"]',
        )!;
        fireEvent.click(within(article).getByRole("button", { name: "Trong cảnh · frame 12–24" }));
        expect(onSeek).toHaveBeenCalledWith({
            mediaId: virtual.mediaId,
            mediaHash: hash,
            timebase: "scene_local",
            inFrame: 12,
            outFrame: 24,
            ...metadata,
        });
        fireEvent.click(within(article).getByRole("button", { name: /Xem bằng chứng/ }));
        expect(onSeek).toHaveBeenLastCalledWith(evidence);
        expect((screen.getByLabelText("Lý do nhận xét") as HTMLTextAreaElement).disabled).toBe(
            true,
        );
    });
    it("does not offer local coordinates from a different report or stale snapshot mapping", () => {
        const view = render(
            createElement(RemakeInspector, {
                project: {
                    ...project,
                    inspectionMappings: [{ ...mapping, reportId: "other-report" }],
                },
                busy: false,
                onInspect: vi.fn(),
                onReview: vi.fn(),
                onSeek: vi.fn(),
            }),
        );
        expect(screen.queryByRole("button", { name: /Trong cảnh/ })).toBeNull();
        view.rerender(
            createElement(RemakeInspector, {
                project: {
                    ...project,
                    inspectionMappings: [{ ...mapping, contextHash: "new-context" }],
                },
                busy: false,
                onInspect: vi.fn(),
                onReview: vi.fn(),
                onSeek: vi.fn(),
            }),
        );
        expect(screen.queryByRole("button", { name: /Trong cảnh/ })).toBeNull();
    });
});
