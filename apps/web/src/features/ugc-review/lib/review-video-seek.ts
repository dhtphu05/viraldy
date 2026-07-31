export function seekVideoToEvidence(
    video: Pick<HTMLVideoElement, "currentTime" | "play"> | null,
    startMs: number,
    durationMs: number | null,
): number {
    const clampedMs = durationMs
        ? Math.min(Math.max(0, startMs), durationMs)
        : Math.max(0, startMs);
    const seconds = clampedMs / 1_000;
    if (video) {
        video.currentTime = seconds;
        void video.play().catch(() => undefined);
    }
    return seconds;
}
