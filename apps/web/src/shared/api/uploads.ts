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
    upload_url: string;
    upload_method: "PUT";
    required_headers: Record<string, string>;
    expires_at: string;
};

export type UploadAssetType = "reference" | "ugc" | "product_media" | "other";

export async function uploadAsset(
    workspaceId: string,
    file: File,
    productId?: string,
    onProgress?: (value: number) => void,
    assetType: UploadAssetType = "reference",
) {
    const session = await apiPost<UploadSession>(
        `/workspaces/${workspaceId}/assets/upload-sessions`,
        {
            filename: file.name,
            declared_mime_type: file.type || "video/mp4",
            declared_size_bytes: file.size,
            asset_type: assetType,
            product_id: productId ?? null,
        },
    );
    await new Promise<void>((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        xhr.open(session.upload_method, session.upload_url);
        for (const [key, value] of Object.entries(session.required_headers)) {
            xhr.setRequestHeader(key, value);
        }
        xhr.upload.onprogress = (event) => {
            if (event.lengthComputable)
                onProgress?.(Math.round((event.loaded / event.total) * 100));
        };
        xhr.onload = () =>
            xhr.status >= 200 && xhr.status < 300 ? resolve() : reject(new Error("Upload failed."));
        xhr.onerror = () => reject(new Error("Upload failed."));
        xhr.send(file);
    });
    return apiPost<Asset>(`/workspaces/${workspaceId}/assets/${session.asset_id}/complete-upload`);
}
