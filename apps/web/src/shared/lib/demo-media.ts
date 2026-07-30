export const SOFA_COVER_POSTER_URL = "/demo-media/sofa-cover-product.jpg";

export function posterForDemoUploadFilename(filename?: string) {
    if (!filename) return undefined;
    const normalized = filename.toLowerCase();
    return normalized.includes("sofa") && normalized.includes("cover")
        ? SOFA_COVER_POSTER_URL
        : undefined;
}

export async function captureVideoPoster(
    mediaUrl: string,
    seekSec = 0.6,
): Promise<string | undefined> {
    if (typeof document === "undefined") return undefined;

    return new Promise((resolve) => {
        const video = document.createElement("video");
        let settled = false;
        let timeoutId = 0;

        const finish = (poster?: string) => {
            if (settled) return;
            settled = true;
            window.clearTimeout(timeoutId);
            video.removeAttribute("src");
            video.load();
            resolve(poster);
        };

        const capture = () => {
            if (!video.videoWidth || !video.videoHeight) {
                finish();
                return;
            }
            const scale = Math.min(1, 480 / Math.max(video.videoWidth, video.videoHeight));
            const canvas = document.createElement("canvas");
            canvas.width = Math.max(1, Math.round(video.videoWidth * scale));
            canvas.height = Math.max(1, Math.round(video.videoHeight * scale));
            const context = canvas.getContext("2d");
            if (!context) {
                finish();
                return;
            }
            try {
                context.drawImage(video, 0, 0, canvas.width, canvas.height);
                finish(canvas.toDataURL("image/jpeg", 0.78));
            } catch {
                finish();
            }
        };

        video.muted = true;
        video.playsInline = true;
        video.preload = "auto";
        video.addEventListener(
            "loadedmetadata",
            () => {
                const target = Math.min(Math.max(0, seekSec), Math.max(0, video.duration - 0.05));
                if (target <= 0.01) capture();
                else video.currentTime = target;
            },
            { once: true },
        );
        video.addEventListener("seeked", capture, { once: true });
        video.addEventListener("error", () => finish(), { once: true });
        timeoutId = window.setTimeout(() => finish(), 5_000);
        video.src = mediaUrl;
    });
}
