import { File } from "node:buffer";
import { IDBFactory } from "fake-indexeddb";
import { describe, expect, it } from "vitest";
import {
    createRemakeDraftStore,
    mergeRemakeDraftSections,
    remakeDraftScopeKey,
} from "./remake-draft";

const scope = { accountId: "account", workspaceId: "workspace", draftId: "draft" };
const sections = { intake: { baseline: "media-a", value: { title: "My cup", start: 0 } } };
const files = () => ({
    video: new File([new Uint8Array([1, 2, 3])], "source.mp4", {
        type: "video/mp4",
        lastModified: 10,
    }) as unknown as globalThis.File,
    products: [
        new File([new Uint8Array([9, 8])], "product.png", {
            type: "image/png",
            lastModified: 20,
        }) as unknown as globalThis.File,
    ],
    primaryProductIndex: 0,
    character: null,
});
function store(factory = new IDBFactory()) {
    return createRemakeDraftStore({ factory, databaseName: "remake-draft-test" });
}

describe("device-only Smart Remake drafts", () => {
    it("round-trips media bytes, metadata and primary selection with an atomic manifest", async () => {
        const drafts = store();
        const saved = await drafts.save(scope, { sections, files: files() }, null);
        const restored = await drafts.read(scope);
        expect(saved.revision).toBe(1);
        expect(restored?.snapshot.sections).toEqual(sections);
        expect(restored?.files.video?.name).toBe("source.mp4");
        expect(restored?.files.video?.lastModified).toBe(10);
        expect(new Uint8Array(await restored!.files.video!.arrayBuffer())).toEqual(
            new Uint8Array([1, 2, 3]),
        );
        expect(restored?.files.products[0].type).toBe("image/png");
        expect(restored?.files.primaryProductIndex).toBe(0);
        drafts.close();
    });
    it("retains the media manifest for text-only saves and preserves another account", async () => {
        const drafts = store();
        await drafts.save(scope, { sections, files: files() }, null);
        const second = await drafts.save(
            scope,
            { sections: { ...sections, view: { baseline: null, value: { sceneId: "scene-2" } } } },
            1,
        );
        expect(second.revision).toBe(2);
        expect((await drafts.read(scope))?.files.video?.size).toBe(3);
        expect(await drafts.read({ ...scope, accountId: "other" })).toBeNull();
        await drafts.save({ ...scope, accountId: "other" }, { sections }, null);
        await drafts.remove(scope);
        expect(await drafts.read(scope)).toBeNull();
        expect(await drafts.read({ ...scope, accountId: "other" })).not.toBeNull();
        drafts.close();
    });
    it("serializes writes and refuses a stale tab without replacing the committed bytes", async () => {
        const factory = new IDBFactory();
        const first = store(factory);
        const second = store(factory);
        await first.save(scope, { sections, files: files() }, null);
        const results = await Promise.allSettled([
            first.save(
                scope,
                { sections: { intake: { baseline: null, value: { title: "first" } } } },
                1,
            ),
            second.save(
                scope,
                { sections: { intake: { baseline: null, value: { title: "second" } } } },
                1,
            ),
        ]);
        expect(results.filter((result) => result.status === "fulfilled")).toHaveLength(1);
        expect(results.find((result) => result.status === "rejected")).toMatchObject({
            reason: { code: "conflict" },
        });
        expect((await first.read(scope))?.snapshot.revision).toBe(2);
        expect((await first.read(scope))?.files.video?.size).toBe(3);
        first.close();
        second.close();
    });
    it("validates MIME, size and primary index before committing", async () => {
        const drafts = store();
        const valid = files();
        await drafts.save(scope, { sections, files: valid }, null);
        await expect(
            drafts.save(scope, { sections, files: { ...valid, primaryProductIndex: 2 } }, 1),
        ).rejects.toMatchObject({ code: "invalid_media" });
        await expect(
            drafts.save(
                scope,
                {
                    sections,
                    files: {
                        ...valid,
                        video: new File(["bad"], "bad.exe", {
                            type: "application/octet-stream",
                        }) as unknown as globalThis.File,
                    },
                },
                1,
            ),
        ).rejects.toMatchObject({ code: "invalid_media" });
        expect((await drafts.read(scope))?.snapshot.revision).toBe(1);
        drafts.close();
    });
    it("fails clearly when IndexedDB is unavailable", async () => {
        const drafts = createRemakeDraftStore({ factory: null });
        await expect(drafts.read(scope)).rejects.toMatchObject({ code: "unavailable" });
    });
    it("compares section baselines independently and retains stale drafts for explicit recovery", () => {
        const result = mergeRemakeDraftSections(
            {
                intake: { baseline: "source", value: { start: 4 } },
                requirements: { baseline: "old", value: { intent: "new intent" } },
                repair: { baseline: "version-2", value: { instruction: "pour slowly" } },
            },
            { intake: "source", requirements: "current", repair: "version-2" },
        );
        expect(result.restorable.intake?.value).toEqual({ start: 4 });
        expect(result.restorable.repair?.value).toEqual({ instruction: "pour slowly" });
        expect(result.conflicts.requirements?.value).toEqual({ intent: "new intent" });
    });
    it("uses unambiguous scope keys even when IDs contain delimiters", () => {
        expect(remakeDraftScopeKey({ ...scope, accountId: "a:b", workspaceId: "c" })).not.toBe(
            remakeDraftScopeKey({ ...scope, accountId: "a", workspaceId: "b:c" }),
        );
    });
});

describe("durable repair submission markers", () => {
    const marker = {
        requestKey: "request-1",
        projectId: "project",
        sceneId: "scene",
        baseVersionId: "version-1",
        requestFingerprint: "request-hash",
    };
    it("commits before returning, reads exact scope and never resets a known receipt on reuse", async () => {
        const drafts = store();
        const initial = await drafts.writeSubmissionMarker(scope, marker);
        expect(initial.status).toBe("awaiting_receipt");
        expect(initial).not.toHaveProperty("repairScope");
        expect(initial).not.toHaveProperty("renderGroupId");
        expect(initial).not.toHaveProperty("affectedVersions");
        expect(await drafts.readSubmissionMarker(scope, marker.requestKey)).toEqual(initial);
        expect(
            await drafts.readSubmissionMarker({ ...scope, accountId: "other" }, marker.requestKey),
        ).toBeNull();
        const completed = await drafts.updateSubmissionMarker(scope, marker.requestKey, {
            status: "completed",
            operationId: "operation",
            candidateVersionId: "candidate",
            disposition: "viewed",
        });
        expect(await drafts.writeSubmissionMarker(scope, marker)).toEqual(completed);
        expect(await drafts.listSubmissionMarkers(scope, "project")).toEqual([completed]);
        expect(await drafts.listSubmissionMarkers(scope, "other-project")).toEqual([]);
        expect(await drafts.listSubmissionMarkers({ ...scope, workspaceId: "other" })).toEqual([]);
        await drafts.remove(scope);
        expect(await drafts.readSubmissionMarker(scope, marker.requestKey)).toEqual(completed);
        drafts.close();
    });
    it("rejects idempotency collisions and an update without a committed marker", async () => {
        const drafts = store();
        await drafts.writeSubmissionMarker(scope, marker);
        await expect(
            drafts.writeSubmissionMarker(scope, { ...marker, requestFingerprint: "different" }),
        ).rejects.toMatchObject({ code: "conflict" });
        await expect(
            drafts.writeSubmissionMarker(scope, { ...marker, sceneId: "" }),
        ).rejects.toMatchObject({ code: "invalid_data" });
        await expect(
            drafts.updateSubmissionMarker(scope, "missing", { status: "running" }),
        ).rejects.toMatchObject({ code: "aborted" });
        drafts.close();
    });
    it("persists exact group bindings and refuses replacing their scope or member bases", async () => {
        const drafts = store();
        const affectedVersions = [
            { sceneId: "scene", baseVersionId: "version-1", candidateVersionId: null },
            { sceneId: "sibling", baseVersionId: "version-2", candidateVersionId: null },
        ];
        await drafts.writeSubmissionMarker(scope, {
            ...marker,
            repairScope: "provider_group",
            renderGroupId: "group",
            affectedVersions,
        });
        const completedBindings = affectedVersions.map((binding, index) => ({
            ...binding,
            candidateVersionId: `candidate-${index}`,
        }));
        const completed = await drafts.updateSubmissionMarker(scope, marker.requestKey, {
            status: "completed",
            operationId: "operation",
            candidateVersionId: "candidate-0",
            repairScope: "provider_group",
            renderGroupId: "group",
            affectedVersions: completedBindings,
        });
        expect(
            (await drafts.readSubmissionMarker(scope, marker.requestKey))?.affectedVersions,
        ).toEqual(completedBindings);
        await expect(
            drafts.updateSubmissionMarker(scope, marker.requestKey, { renderGroupId: "other" }),
        ).rejects.toMatchObject({ code: "conflict" });
        await expect(
            drafts.updateSubmissionMarker(scope, marker.requestKey, {
                affectedVersions: [
                    { ...completedBindings[0], baseVersionId: "other" },
                    completedBindings[1],
                ],
            }),
        ).rejects.toMatchObject({ code: "conflict" });
        await expect(
            drafts.writeSubmissionMarker(scope, {
                ...marker,
                repairScope: "provider_group",
                renderGroupId: "other",
                affectedVersions,
            }),
        ).rejects.toMatchObject({ code: "conflict" });
        const stalePoll = await drafts.updateSubmissionMarker(scope, marker.requestKey, {
            status: "running",
            affectedVersions,
        });
        expect(stalePoll.affectedVersions).toEqual(completed.affectedVersions);
        expect(stalePoll.status).toBe("completed");
        drafts.close();
    });
});

describe("transaction and restoration failures", () => {
    async function raw(factory: IDBFactory, action: (transaction: IDBTransaction) => void) {
        const db = await new Promise<IDBDatabase>((resolve, reject) => {
            const request = factory.open("remake-draft-test");
            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });
        await new Promise<void>((resolve, reject) => {
            const transaction = db.transaction(["drafts", "media"], "readwrite");
            transaction.oncomplete = () => resolve();
            transaction.onabort = () => reject(transaction.error);
            action(transaction);
        });
        db.close();
    }
    it("reports missing or changed Blob bytes instead of restoring an unsafe manifest", async () => {
        const factory = new IDBFactory();
        const drafts = store(factory);
        const saved = await drafts.save(scope, { sections, files: files() }, null);
        await raw(factory, (transaction) =>
            transaction.objectStore("media").put({
                key: saved.media.video!.key,
                blob: new Blob([new Uint8Array([3, 2, 1])], { type: "video/mp4" }),
            }),
        );
        await expect(drafts.read(scope)).rejects.toMatchObject({ code: "corrupt" });
        await raw(factory, (transaction) =>
            transaction.objectStore("media").delete(saved.media.video!.key),
        );
        await expect(drafts.read(scope)).rejects.toMatchObject({ code: "corrupt" });
        drafts.close();
    });
    it("isolates project binding from file identity and only persists explicit user fields", async () => {
        const drafts = store();
        const first = await drafts.save(
            scope,
            {
                sections,
                files: files(),
                serverBinding: { projectId: "project", mediaDigest: "digest" },
            },
            null,
        );
        const second = await drafts.save(scope, { sections }, first.revision);
        expect(second.serverBinding).toEqual({ projectId: "project", mediaDigest: "digest" });
        const third = await drafts.save(scope, { sections, serverBinding: null }, second.revision);
        expect(third.serverBinding).toBeNull();
        await expect(
            drafts.save(
                scope,
                { sections: { intake: { baseline: null, value: { rights: { accepted: true } } } } },
                third.revision,
            ),
        ).rejects.toMatchObject({ code: "invalid_data" });
        await expect(
            drafts.save(
                scope,
                { sections: { intake: { baseline: null, value: { blob: files().video } } } },
                third.revision,
            ),
        ).rejects.toMatchObject({ code: "invalid_data" });
        expect((await drafts.read(scope))?.snapshot.revision).toBe(3);
        drafts.close();
    });
    it("restores all product images and optional character while retaining selection", async () => {
        const drafts = store();
        const media = files();
        const image = new File(["other image"], "other.webp", {
            type: "image/webp",
        }) as unknown as globalThis.File;
        await drafts.save(
            scope,
            {
                sections,
                files: {
                    ...media,
                    products: [...media.products, image],
                    character: image,
                    primaryProductIndex: 1,
                },
            },
            null,
        );
        const restored = await drafts.read(scope);
        expect(restored?.files.products.map((file) => file.name)).toEqual([
            "product.png",
            "other.webp",
        ]);
        expect(restored?.files.character?.name).toBe("other.webp");
        expect(restored?.files.primaryProductIndex).toBe(1);
        drafts.close();
    });
    it("rejects invalid draft scopes and unsupported section baselines", async () => {
        const drafts = store();
        await expect(drafts.read({ ...scope, accountId: "" })).rejects.toMatchObject({
            code: "invalid_data",
        });
        await expect(
            drafts.save(
                scope,
                { sections: { intake: { baseline: 3 as unknown as string, value: {} } } },
                null,
            ),
        ).rejects.toMatchObject({ code: "invalid_data" });
        expect(mergeRemakeDraftSections(sections, {}).conflicts).toEqual(sections);
        drafts.close();
    });
});

it("preserves the last committed snapshot when a quota write throws synchronously", async () => {
    const { IDBObjectStore } = await import("fake-indexeddb");
    const { vi } = await import("vitest");
    const drafts = store();
    await drafts.save(scope, { sections, files: files() }, null);
    const put = vi.spyOn(IDBObjectStore.prototype, "put").mockImplementationOnce(() => {
        throw new DOMException("Storage full", "QuotaExceededError");
    });
    await expect(
        drafts.save(
            scope,
            { sections: { intake: { baseline: null, value: { title: "new" } } } },
            1,
        ),
    ).rejects.toMatchObject({ code: "quota" });
    put.mockRestore();
    expect((await drafts.read(scope))?.snapshot.revision).toBe(1);
    expect((await drafts.read(scope))?.snapshot.sections).toEqual(sections);
    drafts.close();
});

it("reports a database blocked by another tab without claiming a save", async () => {
    const request = {} as IDBOpenDBRequest;
    const factory = {
        open: () => {
            queueMicrotask(() =>
                request.onblocked?.call(request, new Event("blocked") as IDBVersionChangeEvent),
            );
            return request;
        },
    } as unknown as globalThis.IDBFactory;
    const drafts = createRemakeDraftStore({ factory });
    await expect(drafts.read(scope)).rejects.toMatchObject({ code: "blocked" });
});
it("reports explicit transaction abort while preserving the old snapshot", async () => {
    const { IDBObjectStore } = await import("fake-indexeddb");
    const { vi } = await import("vitest");
    const drafts = store();
    await drafts.save(scope, { sections }, null);
    const original = IDBObjectStore.prototype.put;
    const put = vi.spyOn(IDBObjectStore.prototype, "put").mockImplementationOnce(function (
        this: IDBObjectStore,
        value: unknown,
        key?: IDBValidKey,
    ) {
        const request = original.call(this, value, key);
        this.transaction.abort();
        return request;
    });
    await expect(drafts.save(scope, { sections: {} }, 1)).rejects.toMatchObject({
        code: "aborted",
    });
    put.mockRestore();
    expect((await drafts.read(scope))?.snapshot.sections).toEqual(sections);
    drafts.close();
});
it("does not persist preview URLs or signed media links in text sections", async () => {
    const drafts = store();
    await expect(
        drafts.save(
            scope,
            {
                sections: {
                    intake: { baseline: null, value: { previewUrl: "blob:http://localhost/file" } },
                },
            },
            null,
        ),
    ).rejects.toMatchObject({ code: "invalid_data" });
    await expect(
        drafts.save(
            scope,
            {
                sections: {
                    intake: {
                        baseline: null,
                        value: {
                            sourceUrl: "https://storage.example/video?X-Amz-Signature=secret",
                        },
                    },
                },
            },
            null,
        ),
    ).rejects.toMatchObject({ code: "invalid_data" });
    drafts.close();
});
it("retains the exact completed receipt if an older poll arrives later", async () => {
    const drafts = store();
    await drafts.writeSubmissionMarker(scope, {
        requestKey: "paid",
        requestFingerprint: "same",
        projectId: "p",
        sceneId: "s",
        baseVersionId: "v",
    });
    await drafts.updateSubmissionMarker(scope, "paid", {
        status: "completed",
        operationId: "operation",
        candidateVersionId: "candidate",
    });
    await expect(
        drafts.updateSubmissionMarker(scope, "paid", { operationId: "other" }),
    ).rejects.toMatchObject({ code: "conflict" });
    const result = await drafts.updateSubmissionMarker(scope, "paid", {
        status: "running",
        candidateVersionId: null,
        operationId: null,
    });
    expect(result).toMatchObject({
        status: "completed",
        operationId: "operation",
        candidateVersionId: "candidate",
    });
    drafts.close();
});
it("keeps media with equal bytes but different declared types separate", async () => {
    const drafts = store();
    const png = new File(["same bytes"], "one.png", {
        type: "image/png",
    }) as unknown as globalThis.File;
    const jpeg = new File(["same bytes"], "two.jpg", {
        type: "image/jpeg",
    }) as unknown as globalThis.File;
    await drafts.save(
        scope,
        {
            sections,
            files: { video: null, products: [png, jpeg], primaryProductIndex: 1, character: null },
        },
        null,
    );
    expect((await drafts.read(scope))?.files.products.map((file) => file.type)).toEqual([
        "image/png",
        "image/jpeg",
    ]);
    drafts.close();
});
