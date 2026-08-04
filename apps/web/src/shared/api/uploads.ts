import { apiPost } from "./client";

export type Asset = {
    id: string;
    workspace_id: string;
    product_id: string | null;
    asset_type: string;
    status: string;
    current_version_id: string | null;
    metadata_json: Record<string, unknown>;
};

export type UploadSession = {
    asset_id: string;
    asset_version_id: string;
    version_number?: number;
    upload_url: string;
    upload_method: "PUT";
    required_headers: Record<string, string>;
    expires_at: string;
};

export type AssetVersion = {
    id: string;
    asset_id: string;
    version_number: number;
    original_filename: string;
    declared_mime_type: string;
    detected_mime_type: string | null;
    size_bytes: number;
    checksum_sha256: string | null;
    validation_status: string;
    is_current: boolean;
    created_at: string;
};

export type UploadedAsset = Asset & {
    asset_version_id: string;
    version_number: number | null;
};

export type UploadAssetType = "reference" | "ugc" | "product_media" | "other";

export async function uploadAsset(
    workspaceId: string,
    file: File,
    productId?: string,
    onProgress?: (value: number) => void,
    assetType: UploadAssetType = "reference",
    signal?: AbortSignal,
): Promise<UploadedAsset> {
    const session = await apiPost<UploadSession>(
        `/workspaces/${workspaceId}/assets/upload-sessions`,
        {
            filename: file.name,
            declared_mime_type: file.type || "video/mp4",
            declared_size_bytes: file.size,
            asset_type: assetType,
            product_id: productId ?? null,
        },
        { signal },
    );
    await uploadSessionFile(session, file, onProgress, signal);
    const asset = await apiPost<Asset>(
        `/workspaces/${workspaceId}/assets/${session.asset_id}/complete-upload`,
        undefined,
        { signal },
    );
    return {
        ...asset,
        asset_version_id: session.asset_version_id,
        version_number: session.version_number ?? null,
    };
}

export async function uploadAssetRevision(
    workspaceId: string,
    assetId: string,
    file: File,
    onProgress?: (value: number) => void,
    signal?: AbortSignal,
): Promise<AssetVersion> {
    const session = await apiPost<UploadSession>(
        `/workspaces/${workspaceId}/assets/${assetId}/versions/upload-sessions`,
        {
            filename: file.name,
            declared_mime_type: file.type || "video/mp4",
            declared_size_bytes: file.size,
        },
        { signal },
    );
    await uploadSessionFile(session, file, onProgress, signal);
    return apiPost<AssetVersion>(
        `/workspaces/${workspaceId}/assets/${assetId}/versions/${session.asset_version_id}/complete-upload`,
        undefined,
        { signal },
    );
}

function uploadSessionFile(
    session: UploadSession,
    file: File,
    onProgress?: (value: number) => void,
    signal?: AbortSignal,
): Promise<void> {
    return new Promise<void>((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        const rejectAbort = () => reject(new DOMException("Upload cancelled.", "AbortError"));
        const onAbort = () => xhr.abort();
        const cleanup = () => signal?.removeEventListener("abort", onAbort);

        if (signal?.aborted) {
            rejectAbort();
            return;
        }
        xhr.open(session.upload_method, session.upload_url);
        for (const [key, value] of Object.entries(session.required_headers)) {
            xhr.setRequestHeader(key, value);
        }
        xhr.upload.onprogress = (event) => {
            if (event.lengthComputable) {
                onProgress?.(Math.round((event.loaded / event.total) * 100));
            }
        };
        xhr.onload = () => {
            cleanup();
            if (xhr.status >= 200 && xhr.status < 300) resolve();
            else reject(new Error("Upload failed."));
        };
        xhr.onerror = () => {
            cleanup();
            reject(new Error("Upload failed."));
        };
        xhr.onabort = () => {
            cleanup();
            rejectAbort();
        };
        signal?.addEventListener("abort", onAbort, { once: true });
        xhr.send(file);
    });
}
