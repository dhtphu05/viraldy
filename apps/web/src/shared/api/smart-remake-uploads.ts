import { apiPost } from "./client";
import { uploadSessionFile, type Asset, type UploadSession } from "./uploads";

type SmartRemakeUploadInput = {
    metadata: { idempotencyKey: string };
    referenceVideo: File;
    productImage: File;
    additionalProductImages?: File[];
    characterImage?: File;
};

type SmartRemakeUploadRole = "reference_video" | "product_image" | "character_image";

// Retain completed IDs for retries while their original File remains in memory.
const completedUploads = new WeakMap<File, Readonly<Record<string, string>>>();

async function uploadSmartRemakeFile(
    workspaceId: string,
    idempotencyKey: string,
    role: SmartRemakeUploadRole,
    file: File,
    signal?: AbortSignal,
): Promise<string> {
    signal?.throwIfAborted();
    const cacheKey = JSON.stringify([workspaceId, idempotencyKey, role]);
    const existing = completedUploads.get(file)?.[cacheKey];
    if (existing) return existing;

    const path = `/workspaces/${workspaceId}/smart-remake/upload-sessions`;
    const session = await apiPost<UploadSession>(
        path,
        {
            filename: file.name,
            declared_mime_type: file.type,
            declared_size_bytes: file.size,
            role,
        },
        { signal },
    );
    await uploadSessionFile(session, file, undefined, signal);
    await apiPost<Asset>(`${path}/${session.asset_id}/complete`, undefined, { signal });
    completedUploads.set(file, {
        ...completedUploads.get(file),
        [cacheKey]: session.asset_version_id,
    });
    return session.asset_version_id;
}

export async function uploadSmartRemakeInputs(
    workspaceId: string,
    input: SmartRemakeUploadInput,
    signal?: AbortSignal,
) {
    if ((input.additionalProductImages?.length ?? 0) > 13)
        throw new Error("Tối đa 14 ảnh sản phẩm. Xóa bớt ảnh rồi thử lại nhé.");
    const sourceAssetVersionId = await uploadSmartRemakeFile(
        workspaceId,
        input.metadata.idempotencyKey,
        "reference_video",
        input.referenceVideo,
        signal,
    );
    const productAssetVersionId = await uploadSmartRemakeFile(
        workspaceId,
        input.metadata.idempotencyKey,
        "product_image",
        input.productImage,
        signal,
    );
    const additionalProductAssetVersionIds: string[] = [];
    for (const file of input.additionalProductImages ?? []) {
        additionalProductAssetVersionIds.push(
            await uploadSmartRemakeFile(
                workspaceId,
                input.metadata.idempotencyKey,
                "product_image",
                file,
                signal,
            ),
        );
    }
    const characterAssetVersionId = input.characterImage
        ? await uploadSmartRemakeFile(
              workspaceId,
              input.metadata.idempotencyKey,
              "character_image",
              input.characterImage,
              signal,
          )
        : undefined;
    return {
        sourceAssetVersionId,
        productAssetVersionId,
        ...(additionalProductAssetVersionIds.length ? { additionalProductAssetVersionIds } : {}),
        ...(characterAssetVersionId ? { characterAssetVersionId } : {}),
    };
}
