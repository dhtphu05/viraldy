import type { CreativeReference } from "@/features/creative-library/types/creative";
import {
    getCreativeMediaKind,
    isIllustrativeCreative,
    matchesCreativeQuery,
} from "@/features/creative-library/lib/library-catalog";

const MAX_VIDEO_BYTES = 30 * 1024 * 1024;
const VIDEO_EXTENSIONS: Record<string, string> = {
    "video/mp4": "mp4",
    "video/webm": "webm",
    "video/quicktime": "mov",
};

export function getRemakeLibraryVideos(creatives: CreativeReference[], query = "") {
    return creatives
        .filter(
            (creative) =>
                !creative.archived &&
                (creative.mediaKind === "video" ||
                    (!creative.mediaKind && creative.durationSec > 0)) &&
                matchesCreativeQuery(creative, query),
        )
        .sort(
            (a, b) =>
                Number(getCreativeMediaKind(b) === "video") -
                    Number(getCreativeMediaKind(a) === "video") ||
                (Date.parse(b.savedAt) || 0) - (Date.parse(a.savedAt) || 0),
        );
}

export function isDemoLibraryVideo(creative: CreativeReference) {
    return isIllustrativeCreative(creative);
}

export async function loadRemakeLibraryVideo(creative: CreativeReference, signal?: AbortSignal) {
    const url = creative.mediaUrl;
    if (!url || !/^(https?:\/\/|blob:|\/(?!\/))/.test(url))
        throw new Error("Mục này chưa có file video. Hãy thêm file vào kho rồi chọn lại nhé.");

    let response: Response;
    try {
        response = await fetch(url, { signal });
    } catch (cause) {
        if (signal?.aborted) throw cause;
        throw new Error(
            "Chưa mở được video này. Hãy tải lại file trong kho hoặc chọn video khác.",
            { cause },
        );
    }
    if (!response.ok)
        throw new Error("Chưa mở được video này. Hãy tải lại file trong kho hoặc chọn video khác.");
    if (Number(response.headers.get("Content-Length")) > MAX_VIDEO_BYTES) {
        await response.body?.cancel();
        throw new Error("Video này lớn hơn 30 MB. Bạn chọn video nhỏ hơn nhé.");
    }
    const blob = await response.blob();
    signal?.throwIfAborted();
    if (blob.size > MAX_VIDEO_BYTES)
        throw new Error("Video này lớn hơn 30 MB. Bạn chọn video nhỏ hơn nhé.");
    let type = blob.type.split(";")[0].toLowerCase();
    if (!type || type === "application/octet-stream") {
        const extension = url.split(/[?#]/)[0].split(".").at(-1)?.toLowerCase();
        type =
            Object.keys(VIDEO_EXTENSIONS).find((key) => VIDEO_EXTENSIONS[key] === extension) ?? "";
    }
    if (!blob.size || !VIDEO_EXTENSIONS[type])
        throw new Error(
            "Mục này chưa có video MP4, MOV hoặc WebM có thể dùng. Bạn chọn video khác nhé.",
        );
    const title =
        creative.title
            .trim()
            .replace(/[\\/:*?"<>|\p{Cc}]/gu, "-")
            .replace(/\.(mp4|mov|webm)$/i, "")
            .slice(0, 120) || "video-tu-kho";
    return new File([blob], `${title}.${VIDEO_EXTENSIONS[type]}`, { type });
}
