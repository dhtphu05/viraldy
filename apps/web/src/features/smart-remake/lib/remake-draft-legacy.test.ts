import { IDBFactory } from "fake-indexeddb";
import { describe, expect, it, vi } from "vitest";
import { createRemakeDraftStore } from "./remake-draft";
import {
    getLegacyRemakeRepairDraft,
    importLegacyRemakeRepairDraft,
    legacyRemakeRepairDraftKey,
} from "./remake-draft-legacy";
const scope = { accountId: "account", workspaceId: "workspace", draftId: "current" };
const identity = {
    workspaceId: "workspace",
    projectId: "project",
    sceneId: "scene",
    baseVersionId: "base",
};
const payload = {
    prompt: "p",
    imagePrompt: "i",
    videoPrompt: "v",
    selectedReasons: ["Sai sản phẩm", "unknown"],
    instruction: "Keep the label",
};
function memoryStorage() {
    const values = new Map<string, string>();
    return {
        getItem: (key: string) => values.get(key) ?? null,
        setItem: (key: string, value: string) => {
            values.set(key, value);
        },
        removeItem: vi.fn((key: string) => {
            values.delete(key);
        }),
    };
}
describe("manual legacy repair recovery", () => {
    it("only reads old drafts and deletes after a scoped IndexedDB transaction commits", async () => {
        const storage = memoryStorage();
        const key = legacyRemakeRepairDraftKey(identity);
        storage.setItem(key, JSON.stringify(payload));
        expect(getLegacyRemakeRepairDraft(storage, identity)?.selectedReasons).toEqual([
            "Sai sản phẩm",
        ]);
        expect(storage.removeItem).not.toHaveBeenCalled();
        const store = createRemakeDraftStore({
            factory: new IDBFactory(),
            databaseName: "legacy-import",
        });
        const restored = await importLegacyRemakeRepairDraft({
            storage,
            identity,
            scope,
            authorizedProjectId: "project",
            commit: async (value) => {
                expect(storage.getItem(key)).not.toBeNull();
                return store.save(
                    scope,
                    { sections: { repair: { baseline: "base", value } } },
                    null,
                );
            },
        });
        expect(restored?.revision).toBe(1);
        expect(storage.getItem(key)).toBeNull();
        expect((await store.read(scope))?.snapshot.sections.repair?.baseline).toBe("base");
        store.close();
    });
    it("retains the old draft on commit failure or inaccessible project", async () => {
        const storage = memoryStorage();
        const key = legacyRemakeRepairDraftKey(identity);
        storage.setItem(key, JSON.stringify(payload));
        const commit = vi.fn().mockRejectedValue(new Error("quota"));
        await expect(
            importLegacyRemakeRepairDraft({
                storage,
                identity,
                scope,
                authorizedProjectId: "project",
                commit,
            }),
        ).rejects.toThrow("quota");
        expect(storage.getItem(key)).not.toBeNull();
        await expect(
            importLegacyRemakeRepairDraft({
                storage,
                identity,
                scope,
                authorizedProjectId: "other",
                commit,
            }),
        ).rejects.toMatchObject({ code: "invalid_data" });
        expect(commit).toHaveBeenCalledTimes(1);
        expect(storage.removeItem).not.toHaveBeenCalled();
    });
    it("rejects malformed legacy data and does nothing when there is no old draft", async () => {
        const storage = memoryStorage();
        expect(getLegacyRemakeRepairDraft(storage, identity)).toBeNull();
        const commit = vi.fn();
        expect(
            await importLegacyRemakeRepairDraft({
                storage,
                identity,
                scope,
                authorizedProjectId: "project",
                commit,
            }),
        ).toBeNull();
        expect(commit).not.toHaveBeenCalled();
        storage.setItem(
            legacyRemakeRepairDraftKey(identity),
            JSON.stringify({ ...payload, instruction: "a".repeat(4001) }),
        );
        expect(() => getLegacyRemakeRepairDraft(storage, identity)).toThrow();
    });
});
it("keeps legacy data if the importer did not commit to the requesting account", async () => {
    const storage = memoryStorage();
    const key = legacyRemakeRepairDraftKey(identity);
    storage.setItem(key, JSON.stringify({ prompt: "p", imagePrompt: "i", videoPrompt: "v" }));
    expect(getLegacyRemakeRepairDraft(storage, identity)).toEqual({
        prompt: "p",
        imagePrompt: "i",
        videoPrompt: "v",
        selectedReasons: [],
        instruction: "",
    });
    const drafts = createRemakeDraftStore({
        factory: new IDBFactory(),
        databaseName: "wrong-import",
    });
    await expect(
        importLegacyRemakeRepairDraft({
            storage,
            identity,
            scope,
            authorizedProjectId: "project",
            commit: (value) =>
                drafts.save(
                    { ...scope, accountId: "other" },
                    { sections: { repair: { baseline: "base", value } } },
                    null,
                ),
        }),
    ).rejects.toMatchObject({ code: "invalid_data" });
    expect(storage.getItem(key)).not.toBeNull();
    drafts.close();
});
