import { describe, expect, it } from "vitest";
import type { SmartRemakeSceneVersion, SmartRemakeTimeline } from "@/shared/api/smart-remake";
import { getTimelinePreviewScope, getComparisonPlaybackTime } from "./remake-preview";

const version = {
    id: "shared-version",
    suggestedInFrame: 72,
    suggestedOutFrame: 192,
} as SmartRemakeSceneVersion;
const item = {
    versionId: version.id,
    inFrame: 72,
    outFrame: 192,
} as SmartRemakeTimeline["items"][number];

describe("selected scene playback scope", () => {
    it("defaults a later scene in a shared clip to its saved three-to-eight second interval", () => {
        expect(getTimelinePreviewScope(item, version, undefined)).toEqual({ start: 3, end: 8 });
    });
    it("preserves an explicit whole-clip choice while project objects are refreshed", () => {
        expect(getTimelinePreviewScope(item, version, null)).toBeNull();
        expect(getTimelinePreviewScope({ ...item }, { ...version }, null)).toBeNull();
    });
    it("uses the current unsaved trim preview when provided", () => {
        expect(getTimelinePreviewScope(item, version, { start: 2.5, end: 7.5 })).toEqual({
            start: 2.5,
            end: 7.5,
        });
    });
    it("uses version suggestion if no matching draft item exists", () => {
        expect(getTimelinePreviewScope(undefined, version, undefined)).toEqual({
            start: 3,
            end: 8,
        });
        expect(getTimelinePreviewScope({ ...item, versionId: "old" }, version, undefined)).toEqual({
            start: 3,
            end: 8,
        });
    });
    it("returns to a replacement singleton version's suggestion instead of an old clip's offset", () => {
        const replacement = {
            ...version,
            id: "replacement",
            suggestedInFrame: 0,
            suggestedOutFrame: 120,
        };
        expect(getTimelinePreviewScope(item, replacement, undefined)).toEqual({ start: 0, end: 5 });
    });
    it("keeps legacy versions with no segment metadata available as whole clips", () => {
        const legacy = { ...version, suggestedInFrame: undefined, suggestedOutFrame: undefined };
        expect(getTimelinePreviewScope(undefined, legacy, undefined)).toBeNull();
    });
    it("uses the logical scene length for a new candidate with no suggested metadata", () => {
        const replacement = {
            ...version,
            id: "replacement",
            suggestedInFrame: undefined,
            suggestedOutFrame: undefined,
        };
        expect(getTimelinePreviewScope(item, replacement, undefined, 120)).toEqual({
            start: 0,
            end: 5,
        });
    });
    it.each([
        [3, 0],
        [4.25, 1.25],
        [8, 5 - 1 / 24],
        [12, 5 - 1 / 24],
        [1, 0],
    ])("maps active raw time %s to candidate raw time %s", (activeTime, candidateTime) => {
        expect(getComparisonPlaybackTime(activeTime, 3, 0, 5)).toBe(candidateTime);
    });
    it("can compare two shared clip versions with different nonzero starts", () => {
        expect(getComparisonPlaybackTime(4, 3, 2, 7)).toBe(3);
    });
    it.each([
        { inFrame: -1, outFrame: 192 },
        { inFrame: 72.5, outFrame: 192 },
        { inFrame: 72, outFrame: 191.5 },
        { inFrame: 192, outFrame: 72 },
    ])("does not manufacture a playable segment for malformed saved bounds %j", (bounds) => {
        expect(getTimelinePreviewScope({ ...item, ...bounds }, version, undefined)).toBeNull();
    });
});
