import { hashRemakeFile } from "./remake-media-binding";
import {
    RemakeDraftError,
    type RemakeDraftFiles,
    type RemakeDraftMedia,
    type RemakeDraftMediaReference,
} from "./remake-draft-types";

export type RemakeDraftBlob = { key: string; blob: Blob };
const hashes = new WeakMap<Blob, Promise<string>>();
const videoTypes = new Set(["video/mp4", "video/quicktime", "video/webm"]);
const imageTypes = new Set(["image/jpeg", "image/png", "image/webp"]);
export const emptyRemakeDraftFiles = (): RemakeDraftFiles => ({
    video: null,
    products: [],
    primaryProductIndex: 0,
    character: null,
});
export const emptyRemakeDraftMedia = (): RemakeDraftMedia => ({
    video: null,
    products: [],
    primaryProductIndex: 0,
    character: null,
});

export async function remakeDraftMediaHash(blob: Blob): Promise<string> {
    let hash = hashes.get(blob);
    if (!hash) {
        hash = hashRemakeFile(blob);
        hashes.set(blob, hash);
        void hash.catch(() => hashes.delete(blob));
    }
    return hash;
}
function validMedia(file: Blob, kind: "video" | "image") {
    const types = kind === "video" ? videoTypes : imageTypes;
    const limit = (kind === "video" ? 30 : 10) * 1024 * 1024;
    if (!types.has(file.type) || file.size < 1 || file.size > limit)
        throw new RemakeDraftError(
            "invalid_media",
            "Tư liệu chưa đúng định dạng hoặc vượt giới hạn lưu trên thiết bị.",
        );
}
export function remakeDraftMediaReferences(media: RemakeDraftMedia): RemakeDraftMediaReference[] {
    return [media.video, ...media.products, media.character].filter(
        (item): item is RemakeDraftMediaReference => Boolean(item),
    );
}
export async function prepareRemakeDraftMedia(scopeKey: string, files: RemakeDraftFiles) {
    if (
        !Number.isInteger(files.primaryProductIndex) ||
        files.primaryProductIndex < 0 ||
        files.primaryProductIndex >= Math.max(1, files.products.length)
    )
        throw new RemakeDraftError(
            "invalid_media",
            "Ảnh sản phẩm chính không còn trong bộ tư liệu.",
        );
    const blobs: RemakeDraftBlob[] = [];
    async function prepare(file: File | null, kind: "video" | "image") {
        if (!file) return null;
        validMedia(file, kind);
        const sha256 = await remakeDraftMediaHash(file);
        const key = JSON.stringify([scopeKey, sha256, file.type]);
        blobs.push({ key, blob: file.slice(0, file.size, file.type) });
        return {
            key,
            sha256,
            name: file.name,
            type: file.type,
            size: file.size,
            lastModified: file.lastModified,
        };
    }
    const video = await prepare(files.video, "video");
    const products = await Promise.all(
        files.products.map(async (file) => (await prepare(file, "image"))!),
    );
    const character = await prepare(files.character, "image");
    return {
        media: { video, products, character, primaryProductIndex: files.primaryProductIndex },
        blobs,
    };
}
export async function restoreRemakeDraftFile(
    reference: RemakeDraftMediaReference,
    stored: RemakeDraftBlob | undefined,
    kind: "video" | "image",
): Promise<File> {
    if (
        !stored ||
        !stored.blob ||
        typeof stored.blob.slice !== "function" ||
        stored.blob.size !== reference.size ||
        stored.blob.type !== reference.type
    )
        throw new RemakeDraftError(
            "corrupt",
            "Không khôi phục được tư liệu đã lưu. Giữ trang hiện tại và chọn lại tệp còn thiếu.",
        );
    validMedia(stored.blob, kind);
    if ((await remakeDraftMediaHash(stored.blob)) !== reference.sha256)
        throw new RemakeDraftError(
            "corrupt",
            "Tư liệu đã lưu không khớp mã kiểm tra. Chọn lại tệp để tiếp tục.",
        );
    return new File([stored.blob], reference.name, {
        type: reference.type,
        lastModified: reference.lastModified,
    });
}
