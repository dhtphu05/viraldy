import { describe, expect, it } from "vitest";
import {
    canReviewInspectionFinding,
    isInspectionReportCurrent,
    resolveInspectionEvidence,
    isInspectionReadyForApproval,
    getSceneLocalInspectionEvidence,
    type InspectionMediaBinding,
    type InspectionClockMapping,
} from "./remake-inspection";

const hash = "a".repeat(64);
const media: InspectionMediaBinding[] = [
    { mediaId: "source", mediaHash: hash, timebase: "source", frameCount: 600, url: "/source.mp4" },
    {
        mediaId: "raw",
        mediaHash: "b".repeat(64),
        timebase: "raw_group",
        frameCount: 192,
        url: "/raw.mp4",
    },
    {
        mediaId: "scene",
        mediaHash: "c".repeat(64),
        timebase: "scene_local",
        frameCount: 48,
        url: "/scene.mp4",
    },
    {
        mediaId: "final",
        mediaHash: "d".repeat(64),
        timebase: "final",
        frameCount: 192,
        url: "/final.mp4",
    },
];
const range = (index: number, inFrame: number, outFrame: number) => ({
    ...media[index],
    inFrame,
    outFrame,
});

describe("persisted scene-local evidence projections", () => {
    const rawHash = "e".repeat(64);
    const report = {
        id: "scene-report",
        contextHash: "context",
        manifestHash: "manifest",
        subject: {
            kind: "scene" as const,
            projectId: "project",
            sceneId: "scene",
            versionId: "version",
            mediaHash: rawHash,
            range: { inFrame: 72, outFrame: 120, timebase: "raw_group" as const, fps: 24 as const },
        },
    };
    const raw = {
        mediaId: "subject",
        mediaHash: rawHash,
        timebase: "raw_group" as const,
        frameCount: 192,
        url: "/shared-raw.mp4",
    };
    const metadata = {
        reportId: report.id,
        contextHash: report.contextHash,
        manifestHash: report.manifestHash,
        sceneId: "scene",
        versionId: "version",
    };
    const virtual = {
        mediaId: "scene-local:frozen",
        mediaHash: rawHash,
        timebase: "scene_local" as const,
        frameCount: 48,
        url: raw.url,
        playbackTimebase: "raw_group" as const,
        playbackMediaId: raw.mediaId,
        playbackMediaHash: rawHash,
        ...metadata,
    };
    const mapping = {
        from: {
            mediaId: virtual.mediaId,
            mediaHash: rawHash,
            timebase: "scene_local" as const,
            inFrame: 0,
            outFrame: 48,
        },
        to: {
            mediaId: raw.mediaId,
            mediaHash: rawHash,
            timebase: "raw_group" as const,
            inFrame: 72,
            outFrame: 120,
        },
        ...metadata,
    };
    const rawEvidence = {
        mediaId: raw.mediaId,
        mediaHash: rawHash,
        timebase: "raw_group" as const,
        inFrame: 84,
        outFrame: 96,
    };
    const localEvidence = {
        mediaId: virtual.mediaId,
        mediaHash: rawHash,
        timebase: "scene_local" as const,
        inFrame: 12,
        outFrame: 24,
        ...metadata,
    };

    it("projects only the exact persisted report and plays its virtual clock on mapped raw bytes", () => {
        expect(
            getSceneLocalInspectionEvidence(report, rawEvidence, [raw, virtual], [mapping]),
        ).toEqual(localEvidence);
        expect(resolveInspectionEvidence(localEvidence, [raw, virtual], [mapping])).toMatchObject({
            url: raw.url,
            timebase: "raw_group",
            startSecond: 3.5,
            endSecond: 4,
        });
        expect(
            resolveInspectionEvidence(localEvidence, [raw, virtual], [mapping], "scene_local"),
        ).toMatchObject({ timebase: "raw_group", startSecond: 3.5 });
        expect(
            resolveInspectionEvidence(localEvidence, [raw, virtual], [], "raw_group"),
        ).toBeNull();
        expect(resolveInspectionEvidence(localEvidence, [raw, virtual], [])).toBeNull();
    });
    it("keeps historical reports viewable and separates shared-raw scene offsets", () => {
        const secondReport = {
            ...report,
            id: "other-report",
            subject: {
                ...report.subject,
                sceneId: "other-scene",
                range: { ...report.subject.range, inFrame: 24, outFrame: 72 },
            },
        };
        const otherMetadata = { ...metadata, reportId: secondReport.id, sceneId: "other-scene" };
        const otherVirtual = { ...virtual, mediaId: "scene-local:other", ...otherMetadata };
        const otherMapping = {
            from: { ...mapping.from, mediaId: otherVirtual.mediaId },
            to: { ...mapping.to, inFrame: 24, outFrame: 72 },
            ...otherMetadata,
        };
        const historicalReport = { ...report, stale: true };
        const projection = getSceneLocalInspectionEvidence(
            historicalReport,
            rawEvidence,
            [raw, virtual, otherVirtual],
            [otherMapping, mapping],
        );
        expect(projection).toEqual(localEvidence);
        expect(
            getSceneLocalInspectionEvidence(
                secondReport,
                { ...rawEvidence, inFrame: 36, outFrame: 48 },
                [raw, virtual, otherVirtual],
                [mapping, otherMapping],
            ),
        ).toMatchObject({ mediaId: otherVirtual.mediaId, inFrame: 12, outFrame: 24 });
    });
    it("rejects wrong report, context, manifest, scene/version, hashes or selected range", () => {
        for (const changed of [
            { reportId: "wrong" },
            { contextHash: "wrong" },
            { manifestHash: "wrong" },
            { sceneId: "wrong" },
            { versionId: "wrong" },
            { to: { ...mapping.to, mediaHash: "f".repeat(64) } },
            { to: { ...mapping.to, inFrame: 71, outFrame: 119 } },
        ])
            expect(
                getSceneLocalInspectionEvidence(
                    report,
                    rawEvidence,
                    [raw, virtual],
                    [{ ...mapping, ...changed }],
                ),
            ).toBeNull();
        expect(
            getSceneLocalInspectionEvidence(
                report,
                { ...rawEvidence, inFrame: 71 },
                [raw, virtual],
                [mapping],
            ),
        ).toBeNull();
        expect(
            getSceneLocalInspectionEvidence(
                report,
                { ...rawEvidence, timebase: "source" },
                [raw, virtual],
                [mapping],
            ),
        ).toBeNull();
        expect(
            getSceneLocalInspectionEvidence(
                { ...report, subject: { ...report.subject, kind: "assembly" } },
                rawEvidence,
                [raw, virtual],
                [mapping],
            ),
        ).toBeNull();
        expect(
            getSceneLocalInspectionEvidence(
                {
                    ...report,
                    subject: {
                        ...report.subject,
                        range: { ...report.subject.range, fps: 30 as unknown as 24 },
                    },
                },
                rawEvidence,
                [raw, virtual],
                [mapping],
            ),
        ).toBeNull();
    });
    it("refuses ambiguous projections and incomplete or unauthorized virtual playback bindings", () => {
        expect(
            getSceneLocalInspectionEvidence(
                report,
                rawEvidence,
                [raw, virtual, { ...virtual, url: "/ambiguous.mp4" }],
                [mapping],
            ),
        ).toBeNull();
        expect(
            getSceneLocalInspectionEvidence(
                report,
                rawEvidence,
                [raw, virtual],
                [mapping, mapping],
            ),
        ).toBeNull();
        expect(resolveInspectionEvidence(localEvidence, [virtual], [mapping])).toBeNull();
        for (const changed of [
            { playbackMediaHash: "f".repeat(64) },
            { playbackMediaId: "missing" },
            { playbackTimebase: undefined },
            { reportId: "wrong" },
            { frameCount: 47 },
        ])
            expect(
                resolveInspectionEvidence(
                    localEvidence,
                    [raw, { ...virtual, ...changed }],
                    [mapping],
                ),
            ).toBeNull();
        expect(
            resolveInspectionEvidence(
                localEvidence,
                [raw, virtual],
                [{ ...mapping, reportId: "wrong" }],
            ),
        ).toBeNull();
    });
});

describe("inspection approval readiness", () => {
    const finding = {
        id: "f1",
        requirementId: "product",
        category: "product",
        expected: "Pink",
        observed: "Pink",
        status: "passed" as const,
        severity: "info" as const,
        evidence: [evidence],
        suggestedAction: "",
    };
    const report = {
        id: "r1",
        status: "passed" as const,
        coverage: [
            {
                requirementId: "product",
                status: "passed" as const,
                evidence: [evidence],
                sampledFrames: [84],
                unobservedFrames: 0,
                limitations: [],
            },
        ],
        findings: [finding],
    };
    it("requires complete observed coverage and findings", () => {
        expect(isInspectionReadyForApproval(report, [])).toBe(true);
        expect(isInspectionReadyForApproval({ ...report, findings: [] }, [])).toBe(false);
        expect(isInspectionReadyForApproval({ ...report, coverage: [] }, [])).toBe(false);
        expect(
            isInspectionReadyForApproval(
                {
                    ...report,
                    coverage: [{ ...report.coverage[0], status: "insufficient_evidence" }],
                },
                [],
            ),
        ).toBe(false);
        expect(
            isInspectionReadyForApproval(
                { ...report, findings: [{ ...finding, evidence: [] }] },
                [],
            ),
        ).toBe(false);
    });
    it("requires the latest reasoned human review of semantic uncertainty", () => {
        const uncertain = {
            ...report,
            status: "needs_review" as const,
            findings: [{ ...finding, status: "needs_review" as const }],
        };
        const review = {
            reportId: "r1",
            findingId: "f1",
            decision: "accept" as const,
            reason: "Viewed product",
            actorId: "actor",
            reviewedAt: "now",
        };
        expect(isInspectionReadyForApproval(uncertain, [])).toBe(false);
        expect(isInspectionReadyForApproval(uncertain, [review])).toBe(true);
        expect(
            isInspectionReadyForApproval(uncertain, [review, { ...review, decision: "reject" }]),
        ).toBe(false);
        expect(isInspectionReadyForApproval(uncertain, [{ ...review, actorId: "" }])).toBe(false);
        expect(
            isInspectionReadyForApproval(
                { ...uncertain, findings: [{ ...uncertain.findings[0], blocking: true }] },
                [review],
            ),
        ).toBe(false);
    });
});
const mappings: InspectionClockMapping[] = [
    { from: range(0, 240, 288), to: range(2, 0, 48) },
    { from: range(1, 72, 120), to: range(2, 0, 48) },
    { from: range(2, 0, 48), to: range(3, 96, 144) },
];
const evidence = {
    mediaId: "raw",
    mediaHash: media[1].mediaHash,
    timebase: "raw_group" as const,
    inFrame: 84,
    outFrame: 96,
};

describe("inspection evidence clocks", () => {
    it("seeks the evidence's own media and maps explicit four-clock ranges without stretching", () => {
        expect(resolveInspectionEvidence(evidence, media)).toMatchObject({
            url: "/raw.mp4",
            startSecond: 3.5,
            endSecond: 4,
        });
        expect(resolveInspectionEvidence(evidence, media, mappings, "scene_local")).toMatchObject({
            startSecond: 0.5,
            endSecond: 1,
        });
        expect(resolveInspectionEvidence(evidence, media, mappings, "final")).toMatchObject({
            startSecond: 4.5,
            endSecond: 5,
        });
        expect(resolveInspectionEvidence(evidence, media, mappings, "source")).toMatchObject({
            startSecond: 10.5,
            endSecond: 11,
        });
    });
    it("requires identity, hash and valid exact frame bounds", () => {
        for (const changed of [
            { mediaHash: "changed" },
            { mediaId: "missing" },
            { inFrame: -1 },
            { inFrame: 1.5 },
            { outFrame: 193 },
            { outFrame: 84 },
        ])
            expect(resolveInspectionEvidence({ ...evidence, ...changed }, media)).toBeNull();
        expect(
            resolveInspectionEvidence({ ...evidence, inFrame: 191, outFrame: 192 }, media),
        ).not.toBeNull();
    });
    it("does not move raw evidence outside the selected range into the final clip", () => {
        expect(
            resolveInspectionEvidence(
                { ...evidence, inFrame: 71, outFrame: 85 },
                media,
                mappings,
                "final",
            ),
        ).toBeNull();
        expect(
            resolveInspectionEvidence(
                evidence,
                media,
                [{ from: range(1, 72, 120), to: range(3, 96, 145) }],
                "final",
            ),
        ).toBeNull();
    });
    it("does not invent a mapping or image timestamp", () => {
        expect(resolveInspectionEvidence(evidence, media, [], "source")).toBeNull();
        const image = {
            mediaId: "product",
            mediaHash: hash,
            timebase: "image",
            assetId: "asset",
        } as const;
        const images = [{ ...image, url: "/product.png" }];
        expect(resolveInspectionEvidence(image, images)).toMatchObject({
            kind: "image",
            url: "/product.png",
        });
        expect(resolveInspectionEvidence({ ...image, inFrame: 0, outFrame: 1 }, images)).toBeNull();
    });
});

describe("inspection review binding", () => {
    const report = {
        subject: {
            kind: "scene",
            projectId: "project",
            sceneId: "scene",
            versionId: "v1",
            mediaHash: hash,
            range: { inFrame: 72, outFrame: 120, fps: 24, timebase: "raw_group" },
            neighborVersionIds: ["n1"],
        },
        constraintsHash: "constraints",
        manifestHash: "manifest",
    };
    it("uses explicit content context rather than mutable project revision", () => {
        expect(isInspectionReportCurrent(report, structuredClone(report))).toBe(true);
        for (const context of [
            undefined,
            { ...report, manifestHash: "new" },
            { ...report, constraintsHash: "new" },
            { ...report, subject: { ...report.subject, versionId: "v2" } },
            {
                ...report,
                subject: { ...report.subject, range: { ...report.subject.range, inFrame: 73 } },
            },
            { ...report, subject: { ...report.subject, neighborVersionIds: ["n2"] } },
        ])
            expect(isInspectionReportCurrent(report, context)).toBe(false);
    });
    it("does not offer acceptance of a hard finding", () => {
        expect(
            canReviewInspectionFinding(
                { status: "needs_review", category: "product", severity: "warning" },
                "accept",
            ),
        ).toBe(true);
        for (const finding of [
            { category: "rights" },
            { blocking: true },
            { hardBlocking: true },
            { severity: "critical" },
            { severity: "blocker" },
        ])
            expect(
                canReviewInspectionFinding(
                    { status: "failed", category: "product", severity: "warning", ...finding },
                    "accept",
                ),
            ).toBe(false);
        expect(
            canReviewInspectionFinding(
                { status: "failed", category: "rights", severity: "critical" },
                "reject",
            ),
        ).toBe(true);
    });
});
