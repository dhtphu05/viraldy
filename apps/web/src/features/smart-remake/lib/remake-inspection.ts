import type {
    SmartRemakeInspectionEvidence,
    SmartRemakeInspectionReport,
    SmartRemakeInspectionReview,
    SmartRemakeProject,
} from "@/shared/api/smart-remake";
import { getRemakeSceneLabel } from "./remake-scene-label";

export function getInspectionRequirementLabel(
    requirementId: string,
    scenes: readonly { id: string; index: number }[],
    project?: SmartRemakeProject,
): string {
    const match = /^scene:(.+):(opening|presentation|action)$/.exec(requirementId);
    if (!match) return requirementId;
    const label = {
        opening: "Khung mở đầu",
        presentation: "Cách thể hiện",
        action: "Thao tác",
    }[match[2]];
    const scene = scenes.find((item) => item.id === match[1]);
    return scene
        ? `${project ? getRemakeSceneLabel(project, scene.id, scene.index) : `Cảnh ${scene.index + 1}`} · ${label}`
        : `${label} của cảnh`;
}

export function getInspectionExpectationDisplay(expected: string): {
    summary: string;
    details?: string;
} {
    for (const match of expected.matchAll(/[[{]/g)) {
        const start = match.index;
        try {
            const facts: unknown = JSON.parse(expected.slice(start));
            if (facts === null || typeof facts !== "object") continue;
            return {
                summary: expected.slice(0, start).trim() || "Yêu cầu đã lưu",
                details: JSON.stringify(facts, null, 2),
            };
        } catch {
            // Keep ordinary braces and incomplete text visible in the requirement.
        }
    }
    return { summary: expected };
}

export type InspectionClock = "source" | "raw_group" | "scene_local" | "final" | "image";
type BindingMetadata = {
    sceneId?: string | null;
    versionId?: string | null;
    assemblyId?: string | null;
    reportId?: string | null;
    contextHash?: string | null;
    manifestHash?: string | null;
};
export type InspectionEvidenceInput = BindingMetadata & {
    mediaId: string;
    mediaHash: string;
    timebase?: string | null;
    inFrame?: number | null;
    outFrame?: number | null;
    assetId?: string | null;
};
export type InspectionMediaBinding = BindingMetadata & {
    mediaId: string;
    mediaHash: string;
    timebase: InspectionClock;
    frameCount?: number;
    assetId?: string;
    url: string;
    playbackTimebase?: InspectionClock;
    playbackMediaId?: string;
    playbackMediaHash?: string;
};
type MappingRange = InspectionEvidenceInput & { inFrame: number; outFrame: number };
export type InspectionClockMapping = BindingMetadata & { from: MappingRange; to: MappingRange };
export type InspectionSeekTarget = {
    kind: "video" | "image";
    mediaId: string;
    mediaHash: string;
    timebase: InspectionClock;
    url: string;
    startSecond?: number;
    endSecond?: number;
};

const sameMedia = (a: InspectionEvidenceInput, b: InspectionEvidenceInput) =>
    a.mediaId === b.mediaId &&
    a.mediaHash === b.mediaHash &&
    (a.timebase ?? "image") === (b.timebase ?? "image");
const validRange = (start: unknown, end: unknown, frameCount: number) =>
    typeof start === "number" &&
    typeof end === "number" &&
    Number.isInteger(start) &&
    Number.isInteger(end) &&
    start >= 0 &&
    start < end &&
    end <= frameCount;

function bindingFor(value: InspectionEvidenceInput, media: InspectionMediaBinding[]) {
    const matches = media.filter(
        (item) =>
            sameMedia(value, item) &&
            Boolean(item.url) &&
            /^[a-f0-9]{64}$/i.test(item.mediaHash) &&
            (!value.assetId || value.assetId === item.assetId),
    );
    return matches.length === 1 ? matches[0] : undefined;
}

const metadataKeys = [
    "sceneId",
    "versionId",
    "assemblyId",
    "reportId",
    "contextHash",
    "manifestHash",
] as const;
const metadataMatches = (candidate: BindingMetadata, expected: BindingMetadata) =>
    metadataKeys.every((key) => expected[key] == null || candidate[key] === expected[key]);
const isVirtual = (binding: InspectionMediaBinding) =>
    binding.mediaId.startsWith("scene-local:") ||
    binding.playbackTimebase != null ||
    binding.playbackMediaId != null ||
    binding.playbackMediaHash != null;

function mappedRange(value: InspectionEvidenceInput, from: MappingRange, to: MappingRange) {
    if (
        !sameMedia(value, from) ||
        value.inFrame! < from.inFrame ||
        value.outFrame! > from.outFrame ||
        from.outFrame - from.inFrame !== to.outFrame - to.inFrame
    )
        return null;
    return {
        ...to,
        inFrame: to.inFrame + value.inFrame! - from.inFrame,
        outFrame: to.inFrame + value.outFrame! - from.inFrame,
    };
}

function virtualPlayback(
    evidence: InspectionEvidenceInput,
    binding: InspectionMediaBinding,
    media: InspectionMediaBinding[],
    mappings: InspectionClockMapping[],
): InspectionEvidenceInput | null {
    if (
        binding.timebase !== "scene_local" ||
        !binding.playbackTimebase ||
        !binding.playbackMediaId ||
        !binding.playbackMediaHash ||
        binding.playbackMediaHash !== binding.mediaHash ||
        !binding.sceneId ||
        !binding.versionId ||
        !binding.manifestHash ||
        (!binding.reportId && !binding.assemblyId)
    )
        return null;
    const playback = bindingFor(
        {
            mediaId: binding.playbackMediaId,
            mediaHash: binding.playbackMediaHash,
            timebase: binding.playbackTimebase,
        },
        media,
    );
    if (!playback || isVirtual(playback) || playback.timebase === "image") return null;
    const candidates: InspectionEvidenceInput[] = [];
    for (const mapping of mappings) {
        if (
            !metadataMatches(mapping, binding) ||
            !metadataMatches(binding, mapping) ||
            !metadataMatches(mapping, evidence)
        )
            continue;
        for (const [from, to] of [
            [mapping.from, mapping.to],
            [mapping.to, mapping.from],
        ]) {
            if (
                !sameMedia(from, binding) ||
                !sameMedia(to, playback) ||
                from.inFrame !== 0 ||
                from.outFrame !== binding.frameCount ||
                !validRange(to.inFrame, to.outFrame, playback.frameCount ?? 0)
            )
                continue;
            const mapped = mappedRange(evidence, from, to);
            if (mapped)
                candidates.push({
                    ...mapped,
                    ...Object.fromEntries(
                        metadataKeys
                            .filter((key) => mapping[key] != null)
                            .map((key) => [key, mapping[key]]),
                    ),
                });
        }
    }
    return candidates.length === 1 ? candidates[0] : null;
}

/** Only explicit equal-length server mappings can move evidence between clocks. */
export function resolveInspectionEvidence(
    evidence: InspectionEvidenceInput,
    media: InspectionMediaBinding[],
    mappings: InspectionClockMapping[] = [],
    targetClock?: InspectionClock,
): InspectionSeekTarget | null {
    const original = bindingFor(evidence, media);
    if (!original) return null;
    if (original.timebase === "image")
        return evidence.inFrame == null &&
            evidence.outFrame == null &&
            (!targetClock || targetClock === "image")
            ? { ...original, kind: "image" }
            : null;
    if (
        !Number.isInteger(original.frameCount) ||
        !validRange(evidence.inFrame, evidence.outFrame, original.frameCount!)
    )
        return null;
    if (isVirtual(original)) {
        const playback = virtualPlayback(evidence, original, media, mappings);
        return playback
            ? resolveInspectionEvidence(
                  playback,
                  media,
                  mappings,
                  targetClock === "scene_local" ? original.playbackTimebase : targetClock,
              )
            : null;
    }
    const pending: InspectionEvidenceInput[] = [evidence];
    const visited = new Set<string>();
    while (pending.length) {
        const current = pending.shift()!;
        const key = `${current.mediaId}:${current.mediaHash}:${current.timebase}:${current.inFrame}:${current.outFrame}`;
        if (visited.has(key)) continue;
        visited.add(key);
        const binding = bindingFor(current, media);
        if (!binding || !validRange(current.inFrame, current.outFrame, binding.frameCount ?? 0))
            continue;
        if (!targetClock || binding.timebase === targetClock) {
            if (isVirtual(binding)) {
                const playback = virtualPlayback(
                    {
                        ...current,
                        ...Object.fromEntries(
                            metadataKeys
                                .filter((key) => evidence[key] != null)
                                .map((key) => [key, evidence[key]]),
                        ),
                    },
                    binding,
                    media,
                    mappings,
                );
                return playback
                    ? resolveInspectionEvidence(playback, media, [], binding.playbackTimebase)
                    : null;
            }
            return {
                ...binding,
                kind: "video",
                startSecond: current.inFrame! / 24,
                endSecond: current.outFrame! / 24,
            };
        }
        for (const mapping of mappings) {
            if (!metadataMatches(mapping, evidence)) continue;
            for (const [from, to] of [
                [mapping.from, mapping.to],
                [mapping.to, mapping.from],
            ]) {
                const fromMedia = bindingFor(from, media),
                    toMedia = bindingFor(to, media);
                if (
                    !sameMedia(current, from) ||
                    !fromMedia ||
                    !toMedia ||
                    !validRange(from.inFrame, from.outFrame, fromMedia.frameCount ?? 0) ||
                    !validRange(to.inFrame, to.outFrame, toMedia.frameCount ?? 0) ||
                    from.outFrame - from.inFrame !== to.outFrame - to.inFrame ||
                    current.inFrame! < from.inFrame ||
                    current.outFrame! > from.outFrame
                )
                    continue;
                pending.push({
                    ...to,
                    inFrame: to.inFrame + current.inFrame! - from.inFrame,
                    outFrame: to.inFrame + current.outFrame! - from.inFrame,
                });
            }
        }
    }
    return null;
}

/** View-only coordinates from one saved scene report; never a new model finding. */
export function getSceneLocalInspectionEvidence(
    report: Pick<SmartRemakeInspectionReport, "id" | "subject" | "manifestHash" | "contextHash">,
    evidence: SmartRemakeInspectionEvidence,
    media: InspectionMediaBinding[],
    mappings: InspectionClockMapping[],
): (SmartRemakeInspectionEvidence & BindingMetadata) | null {
    const subject = report.subject,
        frozen = subject.range;
    if (
        subject.kind !== "scene" ||
        !subject.sceneId ||
        !subject.versionId ||
        !frozen ||
        !("timebase" in frozen) ||
        frozen.timebase !== "raw_group" ||
        !("fps" in frozen) ||
        frozen.fps !== 24 ||
        evidence.timebase !== "raw_group" ||
        evidence.mediaHash !== subject.mediaHash ||
        !validRange(evidence.inFrame, evidence.outFrame, frozen.outFrame) ||
        evidence.inFrame! < frozen.inFrame
    )
        return null;
    const metadata: BindingMetadata = {
        reportId: report.id,
        sceneId: subject.sceneId,
        versionId: subject.versionId,
        manifestHash: report.manifestHash,
        ...(report.contextHash ? { contextHash: report.contextHash } : {}),
    };
    const candidates: Array<SmartRemakeInspectionEvidence & BindingMetadata> = [];
    for (const mapping of mappings) {
        if (!metadataMatches(mapping, metadata)) continue;
        for (const [from, to] of [
            [mapping.from, mapping.to],
            [mapping.to, mapping.from],
        ]) {
            if (
                from.inFrame !== frozen.inFrame ||
                from.outFrame !== frozen.outFrame ||
                to.timebase !== "scene_local"
            )
                continue;
            const projected = mappedRange(evidence, from, to),
                binding = bindingFor(to, media);
            if (!projected || !binding || !isVirtual(binding)) continue;
            const local = {
                mediaId: projected.mediaId,
                mediaHash: projected.mediaHash,
                timebase: "scene_local" as const,
                inFrame: projected.inFrame,
                outFrame: projected.outFrame,
                ...metadata,
            };
            if (resolveInspectionEvidence(local, media, mappings, "raw_group"))
                candidates.push(local);
        }
    }
    return candidates.length === 1 ? candidates[0] : null;
}

type ReportContext = { subject: object; constraintsHash: string; manifestHash: string };
function canonical(value: unknown): string {
    if (Array.isArray(value)) return `[${value.map(canonical).join(",")}]`;
    if (value && typeof value === "object")
        return JSON.stringify(
            Object.fromEntries(
                Object.entries(value)
                    .sort(([a], [b]) => a.localeCompare(b))
                    .map(([key, item]) => [key, canonical(item)]),
            ),
        );
    return JSON.stringify(value) ?? "undefined";
}

export function isInspectionReportCurrent(report: ReportContext, context?: ReportContext): boolean {
    if (
        !context ||
        !report.constraintsHash ||
        !report.manifestHash ||
        report.constraintsHash !== context.constraintsHash ||
        report.manifestHash !== context.manifestHash
    )
        return false;
    return canonical(report.subject) === canonical(context.subject);
}

export function canReviewInspectionFinding(
    finding: {
        status: string;
        category: string;
        severity: string;
        blocking?: boolean;
        hardBlocking?: boolean;
    },
    decision: "accept" | "reject",
): boolean {
    if (decision === "reject") return true;
    return (
        finding.status !== "passed" &&
        finding.status !== "insufficient_evidence" &&
        !finding.blocking &&
        !finding.hardBlocking &&
        !["critical", "blocker"].includes(finding.severity) &&
        !["technical", "rights", "consent", "authorization", "policy", "safety"].includes(
            finding.category,
        )
    );
}

export function isInspectionReadyForApproval(
    report: Pick<SmartRemakeInspectionReport, "id" | "status" | "coverage" | "findings">,
    reviews: SmartRemakeInspectionReview[],
): boolean {
    return (
        report.status !== "insufficient_evidence" &&
        report.coverage.length > 0 &&
        report.coverage.every(
            (item) => item.status !== "insufficient_evidence" && item.evidence.length > 0,
        ) &&
        report.findings.length > 0 &&
        report.findings.every((finding) => {
            if (!finding.evidence.length) return false;
            if (finding.status === "passed") return true;
            if (!canReviewInspectionFinding(finding, "accept")) return false;
            const review = reviews
                .filter((item) => item.reportId === report.id && item.findingId === finding.id)
                .at(-1);
            return (
                review?.decision === "accept" &&
                Boolean(review.reason.trim() && review.actorId && review.reviewedAt)
            );
        })
    );
}
