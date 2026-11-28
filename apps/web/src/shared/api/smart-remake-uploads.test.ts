import { afterEach, describe, expect, it, vi } from "vitest";

import { createSmartRemakeProject, type SmartRemakeIntakeMetadata } from "./smart-remake";

afterEach(() => vi.unstubAllGlobals());

const response = (data: unknown) => Response.json({ data, meta: { requestId: "upload-test" } });
const project = { id: "owned", revision: 1, phase: "intake" };

function inputs(character = false) {
    return {
        metadata: { idempotencyKey: "intake", targetDuration: 8 } as SmartRemakeIntakeMetadata,
        referenceVideo: new File(["video"], "source.mp4", { type: "video/mp4" }),
        productImage: new File(["product"], "product.png", { type: "image/png" }),
        ...(character
            ? { characterImage: new File(["person"], "person.png", { type: "image/png" }) }
            : {}),
    };
}

function storageTransport(autoComplete = true) {
    const uploads: StorageRequest[] = [];
    class StorageRequest {
        method = "";
        url = "";
        headers: Record<string, string> = {};
        file: File | null = null;
        status = 200;
        upload = { onprogress: null };
        onload: (() => void) | null = null;
        onerror: (() => void) | null = null;
        onabort: (() => void) | null = null;

        open(method: string, url: string) {
            this.method = method;
            this.url = url;
        }
        setRequestHeader(key: string, value: string) {
            this.headers[key] = value;
        }
        send(file: File) {
            this.file = file;
            uploads.push(this);
            if (autoComplete) queueMicrotask(() => this.onload?.());
        }
        abort = vi.fn(() => this.onabort?.());
    }

    let sessionCount = 0;
    const fetch = vi.fn(async (path: string, init: RequestInit) => {
        if (path.endsWith("/upload-sessions")) {
            sessionCount += 1;
            const declaration = JSON.parse(String(init.body));
            return response({
                asset_id: `asset-${sessionCount}`,
                asset_version_id: `version-${sessionCount}`,
                upload_url: `https://storage.example/upload-${sessionCount}?signature=temporary`,
                upload_method: "PUT",
                required_headers: {
                    "Content-Type": declaration.declared_mime_type,
                    "x-amz-meta-upload": `upload-${sessionCount}`,
                },
                expires_at: "2030-01-01T00:00:00Z",
            });
        }
        if (/\/upload-sessions\/[^/]+\/complete$/.test(path)) return response({ id: "asset" });
        return response({ project });
    });
    vi.stubGlobal("XMLHttpRequest", StorageRequest);
    vi.stubGlobal("fetch", fetch);
    return { fetch, uploads };
}

describe("Smart Remake direct storage intake", () => {
    it("uploads every supplemental angle while preserving the selected primary and retry identity", async () => {
        const { fetch, uploads } = storageTransport();
        const input = {
            ...inputs(),
            additionalProductImages: [
                new File(["back"], "back.png", { type: "image/png" }),
                new File(["side"], "side.png", { type: "image/png" }),
            ],
        };
        await createSmartRemakeProject("workspace", input);
        await createSmartRemakeProject("workspace", input);
        expect(uploads.map(({ file }) => file)).toEqual([
            input.referenceVideo,
            input.productImage,
            ...input.additionalProductImages,
        ]);
        expect(JSON.parse(String(fetch.mock.lastCall![1].body))).toEqual({
            metadata: input.metadata,
            sourceAssetVersionId: "version-1",
            productAssetVersionId: "version-2",
            additionalProductAssetVersionIds: ["version-3", "version-4"],
        });
    });

    it("rejects more than fourteen product images before uploading any media", async () => {
        const { fetch, uploads } = storageTransport();
        const input = {
            ...inputs(),
            additionalProductImages: Array.from(
                { length: 14 },
                (_, index) =>
                    new File([String(index)], `angle-${index}.png`, { type: "image/png" }),
            ),
        };
        await expect(createSmartRemakeProject("workspace", input)).rejects.toThrow("14 ảnh");
        expect(fetch).not.toHaveBeenCalled();
        expect(uploads).toHaveLength(0);
    });

    it("surfaces an unavailable R2 session without sending media through a fallback", async () => {
        const { fetch, uploads } = storageTransport();
        const message = "Smart Remake private storage is unavailable.";
        fetch.mockResolvedValue(
            Response.json(
                { error: { code: "SMART_REMAKE_R2_NOT_CONFIGURED", message } },
                { status: 503 },
            ),
        );

        await expect(createSmartRemakeProject("workspace", inputs())).rejects.toMatchObject({
            status: 503,
            message,
        });
        expect(fetch).toHaveBeenCalledOnce();
        expect(uploads).toHaveLength(0);
    });

    it("PUTs all media directly with signed headers and creates intake using only asset IDs", async () => {
        const { fetch, uploads } = storageTransport();
        const input = inputs(true);
        const controller = new AbortController();

        await expect(
            createSmartRemakeProject("workspace", input, { signal: controller.signal }),
        ).resolves.toEqual({ project });

        expect(
            uploads.map(({ method, url, file, headers }) => ({ method, url, file, headers })),
        ).toEqual(
            [input.referenceVideo, input.productImage, input.characterImage].map((file, index) => ({
                method: "PUT",
                url: `https://storage.example/upload-${index + 1}?signature=temporary`,
                file,
                headers: {
                    "Content-Type": file!.type,
                    "x-amz-meta-upload": `upload-${index + 1}`,
                },
            })),
        );
        expect(fetch.mock.calls.map(([path]) => path)).toEqual([
            "/api/backend/workspaces/workspace/smart-remake/upload-sessions",
            "/api/backend/workspaces/workspace/smart-remake/upload-sessions/asset-1/complete",
            "/api/backend/workspaces/workspace/smart-remake/upload-sessions",
            "/api/backend/workspaces/workspace/smart-remake/upload-sessions/asset-2/complete",
            "/api/backend/workspaces/workspace/smart-remake/upload-sessions",
            "/api/backend/workspaces/workspace/smart-remake/upload-sessions/asset-3/complete",
            "/api/backend/workspaces/workspace/smart-remake/projects/from-assets",
        ]);
        const declarations = fetch.mock.calls
            .filter(([path]) => path.endsWith("/upload-sessions"))
            .map(([, init]) => JSON.parse(String(init.body)));
        expect(declarations.map(({ role }) => role)).toEqual([
            "reference_video",
            "product_image",
            "character_image",
        ]);
        expect(declarations[0]).toMatchObject({
            filename: input.referenceVideo.name,
            declared_mime_type: input.referenceVideo.type,
            declared_size_bytes: input.referenceVideo.size,
        });
        expect(JSON.parse(String(fetch.mock.lastCall![1].body))).toEqual({
            metadata: input.metadata,
            sourceAssetVersionId: "version-1",
            productAssetVersionId: "version-2",
            characterAssetVersionId: "version-3",
        });
        expect(fetch.mock.calls.every(([, init]) => init.signal === controller.signal)).toBe(true);
        expect(fetch.mock.calls.every(([, init]) => !(init.body instanceof FormData))).toBe(true);
    });

    it("reuses completed uploads when the JSON intake fails and the same files are retried", async () => {
        const { fetch, uploads } = storageTransport();
        const transport = fetch.getMockImplementation()!;
        let failed = false;
        fetch.mockImplementation(async (path, init) => {
            if (path.endsWith("/from-assets") && !failed) {
                failed = true;
                return Response.json({ error: { message: "Try again" } }, { status: 503 });
            }
            return transport(path, init);
        });
        const input = inputs();

        await expect(createSmartRemakeProject("workspace", input)).rejects.toMatchObject({
            status: 503,
        });
        await expect(createSmartRemakeProject("workspace", input)).resolves.toEqual({ project });

        expect(uploads).toHaveLength(2);
        expect(fetch.mock.calls.filter(([path]) => path.endsWith("/from-assets"))).toHaveLength(2);
        expect(JSON.parse(String(fetch.mock.lastCall![1].body))).toEqual({
            metadata: input.metadata,
            sourceAssetVersionId: "version-1",
            productAssetVersionId: "version-2",
        });
    });

    it("reuses only completed media after a failed PUT and obtains a new upload session", async () => {
        const { fetch, uploads } = storageTransport(false);
        const input = inputs();
        const failure = createSmartRemakeProject("workspace", input).catch(
            (error: unknown) => error,
        );
        await vi.waitFor(() => expect(uploads).toHaveLength(1));
        uploads[0].onload?.();
        await vi.waitFor(() => expect(uploads).toHaveLength(2));
        uploads[1].status = 403;
        uploads[1].onload?.();
        expect(await failure).toMatchObject({ message: "Upload failed." });
        expect(fetch.mock.calls.some(([path]) => path.endsWith("/from-assets"))).toBe(false);

        const retried = createSmartRemakeProject("workspace", input);
        await vi.waitFor(() => expect(uploads).toHaveLength(3));
        expect(uploads[2].file).toBe(input.productImage);
        expect(uploads[2].url).toContain("/upload-3?");
        uploads[2].onload?.();
        await expect(retried).resolves.toEqual({ project });
        expect(JSON.parse(String(fetch.mock.lastCall![1].body))).toMatchObject({
            sourceAssetVersionId: "version-1",
            productAssetVersionId: "version-3",
        });
    });

    it("cancels a storage PUT and can retry without reusing the cancelled upload", async () => {
        const { fetch, uploads } = storageTransport(false);
        const input = inputs();
        const controller = new AbortController();
        const cancelled = createSmartRemakeProject("workspace", input, {
            signal: controller.signal,
        }).catch((error: unknown) => error);
        await vi.waitFor(() => expect(uploads).toHaveLength(1));
        controller.abort();
        expect(await cancelled).toMatchObject({ name: "AbortError" });
        expect(uploads[0].abort).toHaveBeenCalledOnce();
        expect(fetch).toHaveBeenCalledTimes(1);

        const retry = createSmartRemakeProject("workspace", input);
        await vi.waitFor(() => expect(uploads).toHaveLength(2));
        uploads[1].onload?.();
        await vi.waitFor(() => expect(uploads).toHaveLength(3));
        uploads[2].onload?.();
        await expect(retry).resolves.toEqual({ project });
    });

    it("does not start requests for an already cancelled intake, including cached media", async () => {
        const { fetch, uploads } = storageTransport();
        const input = inputs();
        await createSmartRemakeProject("workspace", input);
        const controller = new AbortController();
        controller.abort();
        fetch.mockClear();

        await expect(
            createSmartRemakeProject("workspace", input, { signal: controller.signal }),
        ).rejects.toMatchObject({ name: "AbortError" });
        expect(fetch).not.toHaveBeenCalled();
        expect(uploads).toHaveLength(2);
    });

    it("does not reuse completed asset IDs across a changed file, intake key, or workspace", async () => {
        const { uploads } = storageTransport();
        const input = inputs();
        await createSmartRemakeProject("workspace", input);
        await createSmartRemakeProject("workspace", {
            ...input,
            productImage: new File(["updated"], "product.png", { type: "image/png" }),
        });
        expect(uploads).toHaveLength(3);
        const nextIntake = { ...input, metadata: { ...input.metadata, idempotencyKey: "next" } };
        await createSmartRemakeProject("workspace", nextIntake);
        expect(uploads).toHaveLength(5);
        await createSmartRemakeProject("another-workspace", input);
        expect(uploads).toHaveLength(7);
    });

    it("does not complete intake or cache a version when completion fails", async () => {
        const { fetch, uploads } = storageTransport();
        const transport = fetch.getMockImplementation()!;
        let failed = false;
        fetch.mockImplementation(async (path, init) => {
            if (/\/upload-sessions\/[^/]+\/complete$/.test(path) && !failed) {
                failed = true;
                return Response.json({ error: { message: "Not complete" } }, { status: 409 });
            }
            return transport(path, init);
        });
        const input = inputs();
        await expect(createSmartRemakeProject("workspace", input)).rejects.toMatchObject({
            status: 409,
        });
        expect(fetch.mock.calls.some(([path]) => path.endsWith("/from-assets"))).toBe(false);
        await createSmartRemakeProject("workspace", input);
        expect(uploads.map(({ file }) => file)).toEqual([
            input.referenceVideo,
            input.referenceVideo,
            input.productImage,
        ]);
    });
});
