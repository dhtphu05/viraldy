import { describe, expect, it } from "vitest";
import type {
    SmartRemakeAssembly,
    SmartRemakeInspectionReport,
    SmartRemakeProject,
} from "@/shared/api/smart-remake";
import { getRemakeResultNextAction } from "./remake-result-next-action";

const timeline = {
    fps: 24 as const,
    totalFrames: 192,
    items: [
        {
            id: "item",
            sourceSceneId: "source",
            renderUnitId: "scene",
            targetStartFrame: 0,
            targetDurationFrames: 192,
            versionId: "version",
            inFrame: 0,
            outFrame: 192,
            reviewed: true,
        },
    ],
};
const evidence = [{ mediaId: "media", mediaHash: "media-hash", assemblyId: "assembly" }];
const assembly: SmartRemakeAssembly = {
    id: "assembly",
    projectId: "project",
    schemaVersion: 2,
    parentAssemblyId: null,
    mediaHash: "media-hash",
    manifestHash: "manifest",
    constraintsHash: "constraints",
    contextHash: "context",
    revision: 2,
    createdAt: "",
    technicalCheck: { status: "passed", mediaHash: "media-hash" },
    timeline,
};
const report: SmartRemakeInspectionReport = {
    id: "report",
    schemaVersion: 1,
    subject: {
        kind: "assembly",
        projectId: "project",
        assemblyId: "assembly",
        mediaHash: "media-hash",
    },
    status: "passed",
    checkedAt: "",
    checkerVersion: "checker",
    rubricVersion: "rubric",
    modelProfile: "model",
    constraintsHash: "constraints",
    manifestHash: "manifest",
    coverage: [
        {
            requirementId: "product",
            status: "passed",
            evidence,
            sampledFrames: [0],
            unobservedFrames: 191,
            limitations: [],
        },
    ],
    findings: [
        {
            id: "finding",
            requirementId: "product",
            category: "product",
            expected: "Keep product",
            observed: "Product retained",
            status: "passed",
            severity: "info",
            evidence,
            suggestedAction: "",
        },
    ],
};
const project: SmartRemakeProject = {
    id: "project",
    revision: 2,
    schemaVersion: 2,
    status: "ready",
    provider: "kie",
    targetDuration: 8,
    finalVideoUrl: "/final.mp4",
    constraintsHash: "constraints",
    draftTimeline: timeline,
    publishedTimeline: timeline,
    scenes: [
        {
            id: "scene",
            index: 0,
            startSecond: 0,
            durationSeconds: 8,
            activeVersionId: "version",
            prompt: "scene",
            imagePrompt: "image",
            videoPrompt: "motion",
            versions: [
                {
                    id: "version",
                    parentVersionId: null,
                    videoUrl: "/clip.mp4",
                    prompt: "scene",
                    imagePrompt: "image",
                    videoPrompt: "motion",
                    source: "generated",
                    createdAt: "",
                    frameCount: 192,
                    technicalCheck: {
                        status: "passed",
                        mediaHash: "clip",
                        checkedAt: "",
                        findings: [],
                    },
                },
            ],
        },
    ],
    assemblies: { records: [assembly], activeAssemblyId: "assembly" },
    inspectionSummary: { reports: [report], reviews: [], currentReportIds: ["report"] },
};
const next = (overrides: Partial<SmartRemakeProject> = {}) =>
    getRemakeResultNextAction({ project: { ...project, ...overrides } });

describe("result next action", () => {
    const generationRecovery = {
        kind: "retry_initial_render" as const,
        stage: "image" as const,
        errorCode: "OPENAI_RATE_LIMITED",
        requestKey: "failed-render",
        httpStatus: 429,
    };
    const emptyScenes = [{ ...project.scenes[0], activeVersionId: null, versions: [] }];
    it("offers initial render recovery only from the server capability", () => {
        expect(next({ scenes: emptyScenes, finalVideoUrl: "", generationRecovery })).toMatchObject({
            kind: "retry_render",
            label: "Tiếp tục tạo video",
        });
        expect(
            next({
                scenes: emptyScenes,
                finalVideoUrl: "",
                lastOperation: {
                    id: "failed",
                    kind: "render",
                    status: "failed",
                    errorCode: "OPENAI_RATE_LIMITED",
                },
            }),
        ).toMatchObject({ kind: "scene", view: "watch" });
    });
    it.each([
        undefined,
        "insufficient_quota",
        "billing_hard_limit_reached",
        "project_spend_limit_exceeded",
        "organization_spend_limit_exceeded",
        "organization_usage_limit_exceeded",
    ])("does not require topping up for generic quota or spend limits: %s", (providerErrorCode) => {
        const action = next({
            scenes: emptyScenes,
            generationRecovery: {
                ...generationRecovery,
                errorCode: "OPENAI_IMAGE_CREDITS_EXHAUSTED",
                providerErrorCode,
            },
        });
        expect(action.reason).toContain("hạn mức chi tiêu hoặc tín dụng");
        expect(action.reason).toContain("Kiểm tra hạn mức");
        expect(action.reason).not.toMatch(/bổ sung|nạp/i);
    });
    it("only suggests adding credits when the provider explicitly reports an exhausted balance", () => {
        expect(
            next({
                scenes: emptyScenes,
                generationRecovery: {
                    ...generationRecovery,
                    errorCode: "OPENAI_IMAGE_CREDITS_EXHAUSTED",
                    providerErrorCode: "credit_balance_exhausted",
                },
            }).reason,
        ).toContain("Bổ sung tín dụng");
    });
    it("keeps a legacy 429 ambiguous without a provider quota code", () => {
        const action = next({ scenes: emptyScenes, generationRecovery });
        expect(action.reason).toContain("Bước chuẩn bị ảnh tham chiếu chưa hoàn tất");
        expect(action.reason).not.toMatch(/bổ sung|tín dụng|chi tiêu/i);
    });
    it("prioritizes actual unknown receipts and stale scripts over retrying initial generation", () => {
        const value = { ...project, scenes: emptyScenes, generationRecovery };
        expect(
            getRemakeResultNextAction({
                project: {
                    ...value,
                    lastOperation: { id: "unknown", status: "failed", needsReconciliation: true },
                },
            }),
        ).toMatchObject({ kind: "progress", label: "Kiểm tra trạng thái" });
        expect(getRemakeResultNextAction({ project: value, needsPlanUpdate: true }).kind).toBe(
            "update_plan",
        );
    });
    it("prioritizes reconciliation over stale plans and completed unknown charges do not block", () => {
        expect(
            getRemakeResultNextAction({ project, receiptUncertain: true, needsPlanUpdate: true })
                .kind,
        ).toBe("progress");
        expect(
            next({
                budget: {
                    policy: { capUsd: "5", maxAttempts: 20, maxDurationSeconds: 1800 },
                    unknownAttemptCount: 1,
                    needsReconciliation: true,
                },
            }).kind,
        ).toBe("approve");
        expect(
            next({ pendingOperation: { id: "op", status: "running", needsReconciliation: true } })
                .needsReconciliation,
        ).toBe(true);
    });
    it("asks to update changed inputs before offering a candidate", () => {
        expect(getRemakeResultNextAction({ project, needsPlanUpdate: true }).kind).toBe(
            "update_plan",
        );
    });
    it("only introduces candidates that exist in the matching project and scene", () => {
        const candidate = {
            ...project.scenes[0].versions[0],
            id: "candidate",
            parentVersionId: "version",
        };
        const updated = {
            ...project,
            scenes: [
                { ...project.scenes[0], versions: [...project.scenes[0].versions, candidate] },
            ],
        };
        expect(
            getRemakeResultNextAction({
                project: updated,
                candidate: { projectId: "project", sceneId: "scene", versionId: "candidate" },
            }),
        ).toMatchObject({ kind: "candidate", sceneId: "scene", versionId: "candidate" });
        expect(
            getRemakeResultNextAction({
                project: updated,
                candidate: { projectId: "other", sceneId: "scene", versionId: "candidate" },
            }).kind,
        ).toBe("approve");
        expect(
            getRemakeResultNextAction({
                project,
                candidate: { projectId: "project", sceneId: "scene", versionId: "missing" },
            }).kind,
        ).toBe("approve");
    });
    it("targets missing and technically invalid clips before composing", () => {
        expect(next({ scenes: [{ ...project.scenes[0], versions: [] }] })).toMatchObject({
            kind: "scene",
            sceneId: "scene",
            view: "watch",
        });
        expect(
            next({
                scenes: [
                    {
                        ...project.scenes[0],
                        versions: [
                            {
                                ...project.scenes[0].versions[0],
                                technicalCheck: {
                                    status: "failed",
                                    mediaHash: "",
                                    findings: [],
                                    checkedAt: "",
                                },
                            },
                        ],
                    },
                ],
            }).kind,
        ).toBe("scene");
    });
    it("targets unreviewed and invalid ranges and notices missing timeline items", () => {
        for (const change of [{ reviewed: false }, { inFrame: 1 }, { versionId: "old" }]) {
            expect(
                next({
                    draftTimeline: { ...timeline, items: [{ ...timeline.items[0], ...change }] },
                }),
            ).toMatchObject({ kind: "scene", sceneId: "scene", view: "watch" });
        }
        expect(next({ draftTimeline: { ...timeline, items: [] } }).kind).toBe("scene");
    });
    it("requires a new composition after range, version, or requirements change", () => {
        expect(next({ assemblies: { records: [], activeAssemblyId: null } }).kind).toBe("compose");
        expect(
            next({
                assemblies: {
                    records: [
                        {
                            ...assembly,
                            timeline: {
                                ...timeline,
                                items: [{ ...timeline.items[0], inFrame: 1, outFrame: 193 }],
                            },
                        },
                    ],
                    activeAssemblyId: "assembly",
                },
            }).kind,
        ).toBe("compose");
        expect(next({ constraintsHash: "changed" }).kind).toBe("compose");
    });
    it("surfaces assembly technical failure before inspection", () => {
        expect(
            next({
                assemblies: {
                    records: [
                        {
                            ...assembly,
                            technicalCheck: { status: "failed", mediaHash: "media-hash" },
                        },
                    ],
                    activeAssemblyId: "assembly",
                },
            }).kind,
        ).toBe("assembly_error");
    });
    it("requires a current report matching media, manifest, constraints, and expectations", () => {
        for (const patch of [
            { stale: true },
            { manifestHash: "old" },
            { constraintsHash: "old" },
            { subject: { ...report.subject, mediaHash: "old" } },
        ]) {
            expect(
                next({
                    inspectionSummary: {
                        reports: [{ ...report, ...patch }],
                        reviews: [],
                        currentReportIds: ["report"],
                    },
                }).kind,
            ).toBe("inspect");
        }
        expect(
            next({ inspectionSummary: { reports: [report], reviews: [], currentReportIds: [] } })
                .kind,
        ).toBe("inspect");
    });
    it("takes the seller to findings while respecting hard blockers and justified content acceptance", () => {
        const finding = { ...report.findings[0], status: "needs_review" as const };
        const needsReview = { ...report, status: "needs_review" as const, findings: [finding] };
        expect(
            next({
                inspectionSummary: {
                    reports: [needsReview],
                    reviews: [],
                    currentReportIds: ["report"],
                },
            }),
        ).toMatchObject({ kind: "findings", reportId: "report", findingId: "finding" });
        const review = {
            reportId: "report",
            findingId: "finding",
            decision: "accept" as const,
            reason: "Accept the variation",
            actorId: "seller",
            reviewedAt: "now",
        };
        expect(
            next({
                inspectionSummary: {
                    reports: [needsReview],
                    reviews: [review],
                    currentReportIds: ["report"],
                },
            }).kind,
        ).toBe("approve");
        expect(
            next({
                inspectionSummary: {
                    reports: [
                        {
                            ...needsReview,
                            findings: [{ ...finding, category: "rights", hardBlocking: true }],
                        },
                    ],
                    reviews: [review],
                    currentReportIds: ["report"],
                },
            }).kind,
        ).toBe("findings");
    });
    it("skips accepted content findings and prioritizes unresolved hard blockers", () => {
        const accepted = { ...report.findings[0], status: "needs_review" as const };
        const unresolved = { ...accepted, id: "unresolved" };
        const hard = { ...unresolved, id: "hard", category: "technical", hardBlocking: true };
        const reviews = [
            {
                reportId: report.id,
                findingId: accepted.id,
                decision: "accept" as const,
                reason: "Accept the variation",
                actorId: "seller",
                reviewedAt: "now",
            },
        ];
        const nextReport = (findings: typeof report.findings) =>
            next({
                inspectionSummary: {
                    reports: [{ ...report, status: "needs_review", findings }],
                    reviews,
                    currentReportIds: [report.id],
                },
            });
        expect(nextReport([accepted, unresolved]).findingId).toBe("unresolved");
        expect(nextReport([accepted, unresolved, hard]).findingId).toBe("hard");
    });
    it("targets the later scene when only its selected range is invalid", () => {
        const first = { ...project.scenes[0], durationSeconds: 4 };
        const second = { ...first, id: "scene-2", index: 1, startSecond: 4 };
        const items = [
            { ...timeline.items[0], targetDurationFrames: 96, outFrame: 96 },
            {
                ...timeline.items[0],
                id: "item-2",
                renderUnitId: "scene-2",
                targetStartFrame: 96,
                targetDurationFrames: 96,
                inFrame: 150,
                outFrame: 246,
            },
        ];
        expect(
            next({ scenes: [first, second], draftTimeline: { ...timeline, items } }),
        ).toMatchObject({ kind: "scene", sceneId: "scene-2" });
    });
    it("exports only an approval bound to the exact assembly and report", () => {
        const approval = {
            id: "approval",
            status: "approved",
            assemblyId: "assembly",
            mediaHash: "media-hash",
            manifestHash: "manifest",
            constraintsHash: "constraints",
            reportId: "report",
            approvedAt: "",
        };
        expect(
            next({ release: { approvals: [approval], activeApprovalId: "approval" } }).kind,
        ).toBe("export");
        expect(
            next({
                release: {
                    approvals: [{ ...approval, reportId: "old" }],
                    activeApprovalId: "approval",
                },
            }).kind,
        ).toBe("approve");
    });
    it("blocks deleted projects and otherwise handles legacy output without a new paid task", () => {
        expect(next({ deletion: { status: "deleted" } }).kind).toBe("blocked");
        expect(getRemakeResultNextAction({ project: null }).kind).toBe("blocked");
        expect(next({ schemaVersion: 1 }).kind).toBe("approve");
    });
});
