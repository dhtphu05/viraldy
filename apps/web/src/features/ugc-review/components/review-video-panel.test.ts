import { describe, expect, it, vi } from "vitest";

import { seekVideoToEvidence } from "../lib/review-video-seek";

describe("seekVideoToEvidence", () => {
    it("seeks and plays the exact timestamp selected by an evidence interaction", () => {
        const play = vi.fn().mockResolvedValue(undefined);
        const video = { currentTime: 0, play };

        const selectedSeconds = seekVideoToEvidence(video, 6_250, 10_000);

        expect(selectedSeconds).toBe(6.25);
        expect(video.currentTime).toBe(6.25);
        expect(play).toHaveBeenCalledOnce();
    });

    it("clamps evidence timestamps to the analyzed media duration", () => {
        const video = { currentTime: 0, play: vi.fn().mockResolvedValue(undefined) };

        expect(seekVideoToEvidence(video, 12_000, 8_000)).toBe(8);
        expect(video.currentTime).toBe(8);
    });
});
