import {
    RemakeDraftError,
    type RemakeDraftBaselines,
    type RemakeDraftReadResult,
    type RemakeDraftScope,
    type RemakeDraftSections,
    type RemakeDraftSnapshot,
    type RemakeDraftValue,
    type RemakeSubmissionMarker,
    type RemakeSubmissionMarkerInput,
    type RemakeSubmissionMarkerPatch,
} from "./remake-draft-types";
import {
    emptyRemakeDraftMedia,
    prepareRemakeDraftMedia,
    remakeDraftMediaReferences,
    restoreRemakeDraftFile,
    type RemakeDraftBlob,
} from "./remake-draft-media";
export * from "./remake-draft-types";
export { emptyRemakeDraftFiles } from "./remake-draft-media";

export function remakeDraftScopeKey(scope: RemakeDraftScope): string {
    if (
        ![scope.accountId, scope.workspaceId, scope.draftId].every(
            (part) => typeof part === "string" && part.trim(),
        )
    )
        throw new RemakeDraftError(
            "invalid_data",
            "Chưa xác định tài khoản và workspace để lưu nháp.",
        );
    return JSON.stringify([scope.accountId, scope.workspaceId, scope.draftId]);
}
export function mergeRemakeDraftSections(
    sections: RemakeDraftSections,
    baselines: RemakeDraftBaselines,
) {
    const restorable: RemakeDraftSections = {};
    const conflicts: RemakeDraftSections = {};
    for (const name of ["intake", "requirements", "storyboard", "repair", "view"] as const) {
        const section = sections[name];
        if (!section) continue;
        const target =
            Object.hasOwn(baselines, name) && section.baseline === baselines[name]
                ? restorable
                : conflicts;
        target[name] = section;
    }
    return { restorable, conflicts };
}
function storageError(value: unknown): RemakeDraftError {
    if (value instanceof RemakeDraftError) return value;
    const name = value && typeof value === "object" && "name" in value ? value.name : "";
    if (name === "QuotaExceededError")
        return new RemakeDraftError(
            "quota",
            "Chưa lưu được: thiết bị không còn đủ dung lượng. Giữ trang này để tiếp tục.",
        );
    if (name === "AbortError")
        return new RemakeDraftError(
            "aborted",
            "Lần lưu đã bị hủy. Thay đổi mới vẫn còn trong trang này.",
        );
    return new RemakeDraftError(
        "unavailable",
        "Chưa lưu được trên thiết bị này. Giữ trang này để tiếp tục.",
    );
}
function cloneSections(sections: RemakeDraftSections): RemakeDraftSections {
    try {
        const serialized = JSON.stringify(sections, (key, value: unknown) => {
            if (
                [
                    "rights",
                    "budget",
                    "consent",
                    "approval",
                    "preflight",
                    "token",
                    "accessToken",
                    "refreshToken",
                ].includes(key)
            )
                throw new Error("Authority cannot be stored in a draft");
            if (
                typeof value === "string" &&
                (/^(?:blob:|data:)/i.test(value) ||
                    /^https?:\/\/.*[?&](?:x-amz-signature|x-goog-signature|signature|token)=/i.test(
                        value,
                    ))
            )
                throw new Error("Ephemeral URLs cannot be stored in a draft");
            if (typeof value === "bigint" || typeof value === "function" || value instanceof Blob)
                throw new Error("Non-JSON draft value");
            return value;
        });
        const clone = JSON.parse(serialized) as RemakeDraftSections;
        for (const [name, section] of Object.entries(clone)) {
            if (
                !["intake", "requirements", "storyboard", "repair", "view"].includes(name) ||
                !section ||
                !(section.baseline === null || typeof section.baseline === "string") ||
                !Object.hasOwn(section, "value")
            )
                throw new Error("Invalid section");
        }
        return clone;
    } catch {
        throw new RemakeDraftError("invalid_data", "Bản nháp chứa dữ liệu không thể lưu an toàn.");
    }
}
function requestValue<T>(request: IDBRequest<T>): Promise<T> {
    return new Promise((resolve, reject) => {
        request.onsuccess = () => resolve(request.result);
        request.onerror = () => reject(storageError(request.error));
    });
}
function transactionDone(transaction: IDBTransaction): Promise<void> {
    return new Promise((resolve, reject) => {
        transaction.oncomplete = () => resolve();
        transaction.onabort = () =>
            reject(storageError(transaction.error ?? new DOMException("Aborted", "AbortError")));
        transaction.onerror = () => {
            /* Abort owns the definitive transaction outcome. */
        };
    });
}
function repairBindingConflict(
    previous: RemakeSubmissionMarker["affectedVersions"],
    next: RemakeSubmissionMarker["affectedVersions"],
) {
    return Boolean(
        previous &&
        next &&
        (previous.length !== next.length ||
            previous.some((binding, index) => {
                const replacement = next[index];
                return (
                    binding.sceneId !== replacement.sceneId ||
                    binding.baseVersionId !== replacement.baseVersionId ||
                    (binding.candidateVersionId &&
                        replacement.candidateVersionId &&
                        binding.candidateVersionId !== replacement.candidateVersionId)
                );
            })),
    );
}
export function createRemakeDraftStore(
    options: { factory?: IDBFactory | null; databaseName?: string } = {},
) {
    let database: Promise<IDBDatabase> | null = null;
    const factory = options.factory === undefined ? globalThis.indexedDB : options.factory;
    function open(): Promise<IDBDatabase> {
        if (database) return database;
        if (!factory)
            return Promise.reject(
                new RemakeDraftError(
                    "unavailable",
                    "Trình duyệt chưa cho phép lưu nháp trên thiết bị.",
                ),
            );
        database = new Promise<IDBDatabase>((resolve, reject) => {
            let request: IDBOpenDBRequest;
            try {
                request = factory.open(options.databaseName ?? "viraldy-smart-remake", 1);
            } catch (error) {
                reject(storageError(error));
                return;
            }
            let rejected = false;
            request.onupgradeneeded = () => {
                const db = request.result;
                for (const name of ["drafts", "media", "submissionMarkers"])
                    if (!db.objectStoreNames.contains(name))
                        db.createObjectStore(name, { keyPath: "key" });
            };
            request.onsuccess = () => {
                if (rejected) {
                    request.result.close();
                    return;
                }
                request.result.onversionchange = () => {
                    request.result.close();
                    database = null;
                };
                resolve(request.result);
            };
            request.onerror = () => reject(storageError(request.error));
            request.onblocked = () => {
                rejected = true;
                reject(
                    new RemakeDraftError(
                        "blocked",
                        "Bộ lưu nháp đang bị tab khác khóa. Đóng tab cũ rồi thử lại.",
                    ),
                );
            };
        }).catch((error: unknown) => {
            database = null;
            throw error;
        });
        return database;
    }
    async function read(scope: RemakeDraftScope): Promise<RemakeDraftReadResult | null> {
        const key = remakeDraftScopeKey(scope);
        const db = await open();
        const transaction = db.transaction(["drafts", "media"], "readonly");
        const done = transactionDone(transaction);
        const snapshot = await requestValue<RemakeDraftSnapshot | undefined>(
            transaction.objectStore("drafts").get(key),
        );
        if (!snapshot) {
            await done;
            return null;
        }
        if (
            snapshot.schemaVersion !== 1 ||
            snapshot.key !== key ||
            remakeDraftScopeKey(snapshot.scope) !== key
        )
            throw new RemakeDraftError(
                "corrupt",
                "Bản nháp đã lưu không còn đúng định dạng hoặc tài khoản.",
            );
        const references = remakeDraftMediaReferences(snapshot.media);
        const blobs = await Promise.all(
            references.map(
                async (reference) =>
                    [
                        reference.key,
                        await requestValue<RemakeDraftBlob | undefined>(
                            transaction.objectStore("media").get(reference.key),
                        ),
                    ] as const,
            ),
        );
        await done;
        const stored = new Map(blobs);
        const restore = (
            reference: NonNullable<typeof snapshot.media.video> | null,
            kind: "video" | "image",
        ) =>
            reference
                ? restoreRemakeDraftFile(reference, stored.get(reference.key), kind)
                : Promise.resolve(null);
        const video = await restore(snapshot.media.video, "video");
        const products = await Promise.all(
            snapshot.media.products.map(async (reference) => (await restore(reference, "image"))!),
        );
        const character = await restore(snapshot.media.character, "image");
        const files = {
            video,
            products,
            character,
            primaryProductIndex: snapshot.media.primaryProductIndex,
        };
        if (
            !Number.isInteger(files.primaryProductIndex) ||
            files.primaryProductIndex < 0 ||
            files.primaryProductIndex >= Math.max(1, files.products.length)
        )
            throw new RemakeDraftError(
                "corrupt",
                "Không tìm thấy ảnh chính trong bản nháp đã lưu.",
            );
        return { snapshot: { ...snapshot, sections: cloneSections(snapshot.sections) }, files };
    }
    async function save(
        scope: RemakeDraftScope,
        value: RemakeDraftValue,
        expectedRevision: number | null,
    ): Promise<RemakeDraftSnapshot> {
        const key = remakeDraftScopeKey(scope);
        const sections = cloneSections(value.sections);
        const prepared = value.files ? await prepareRemakeDraftMedia(key, value.files) : null;
        const db = await open();
        const transaction = db.transaction(["drafts", "media"], "readwrite");
        const done = transactionDone(transaction);
        let snapshot: RemakeDraftSnapshot | undefined;
        let conflict = false;
        const previous = transaction.objectStore("drafts").get(key);
        let mutationError: unknown;
        previous.onsuccess = () => {
            try {
                const old = previous.result as RemakeDraftSnapshot | undefined;
                if ((old?.revision ?? null) !== expectedRevision) {
                    conflict = true;
                    transaction.abort();
                    return;
                }
                const media = prepared?.media ?? old?.media ?? emptyRemakeDraftMedia();
                snapshot = {
                    schemaVersion: 1,
                    key,
                    scope: { ...scope },
                    revision: (old?.revision ?? 0) + 1,
                    sections,
                    media,
                    serverBinding:
                        value.serverBinding === undefined
                            ? (old?.serverBinding ?? null)
                            : value.serverBinding,
                    updatedAt: Date.now(),
                };
                const existing = new Set(
                    old
                        ? remakeDraftMediaReferences(old.media).map((reference) => reference.key)
                        : [],
                );
                const next = new Set(
                    remakeDraftMediaReferences(media).map((reference) => reference.key),
                );
                for (const blob of prepared?.blobs ?? [])
                    if (!existing.has(blob.key)) transaction.objectStore("media").put(blob);
                for (const oldKey of existing)
                    if (!next.has(oldKey)) transaction.objectStore("media").delete(oldKey);
                transaction.objectStore("drafts").put(snapshot);
            } catch (error) {
                mutationError = error;
                transaction.abort();
            }
        };
        try {
            await done;
        } catch (error) {
            if (conflict)
                throw new RemakeDraftError(
                    "conflict",
                    "Bản nháp đã được thay đổi trong tab khác. Xem lại bản đã lưu trước khi tiếp tục.",
                );
            throw storageError(mutationError ?? error);
        }
        return snapshot!;
    }
    async function remove(scope: RemakeDraftScope): Promise<void> {
        const key = remakeDraftScopeKey(scope);
        const db = await open();
        const transaction = db.transaction(["drafts", "media"], "readwrite");
        const done = transactionDone(transaction);
        const request = transaction.objectStore("drafts").get(key);
        request.onsuccess = () => {
            const previous = request.result as RemakeDraftSnapshot | undefined;
            for (const reference of previous ? remakeDraftMediaReferences(previous.media) : [])
                transaction.objectStore("media").delete(reference.key);
            transaction.objectStore("drafts").delete(key);
        };
        // Markers remain: deleting a draft cannot erase an unresolved paid receipt.
        await done;
    }
    const markerKey = (scope: RemakeDraftScope, requestKey: string) =>
        JSON.stringify([remakeDraftScopeKey(scope), requestKey]);
    async function readSubmissionMarker(
        scope: RemakeDraftScope,
        requestKey: string,
    ): Promise<RemakeSubmissionMarker | null> {
        const db = await open();
        const transaction = db.transaction("submissionMarkers", "readonly");
        const done = transactionDone(transaction);
        const marker = await requestValue<RemakeSubmissionMarker | undefined>(
            transaction.objectStore("submissionMarkers").get(markerKey(scope, requestKey)),
        );
        await done;
        return marker ?? null;
    }
    async function listSubmissionMarkers(
        scope: RemakeDraftScope,
        projectId?: string,
    ): Promise<RemakeSubmissionMarker[]> {
        const key = remakeDraftScopeKey(scope);
        const db = await open();
        const transaction = db.transaction("submissionMarkers", "readonly");
        const done = transactionDone(transaction);
        const markers = await requestValue<RemakeSubmissionMarker[]>(
            transaction.objectStore("submissionMarkers").getAll(),
        );
        await done;
        return markers.filter(
            (marker) =>
                remakeDraftScopeKey(marker.scope) === key &&
                (!projectId || marker.projectId === projectId),
        );
    }
    async function writeSubmissionMarker(
        scope: RemakeDraftScope,
        input: RemakeSubmissionMarkerInput,
    ): Promise<RemakeSubmissionMarker> {
        if (
            ![input.requestKey, input.requestFingerprint, input.projectId, input.sceneId].every(
                (part) => typeof part === "string" && part.length > 0,
            )
        )
            throw new RemakeDraftError(
                "invalid_data",
                "Chưa đủ thông tin để theo dõi yêu cầu sửa.",
            );
        const key = markerKey(scope, input.requestKey);
        const db = await open();
        const transaction = db.transaction("submissionMarkers", "readwrite");
        const done = transactionDone(transaction);
        let result: RemakeSubmissionMarker | undefined;
        let conflict = false;
        const request = transaction.objectStore("submissionMarkers").get(key);
        request.onsuccess = () => {
            const old = request.result as RemakeSubmissionMarker | undefined;
            if (
                old &&
                (old.requestFingerprint !== input.requestFingerprint ||
                    old.projectId !== input.projectId ||
                    old.sceneId !== input.sceneId ||
                    old.baseVersionId !== input.baseVersionId ||
                    (old.repairScope &&
                        input.repairScope &&
                        old.repairScope !== input.repairScope) ||
                    (old.renderGroupId &&
                        input.renderGroupId &&
                        old.renderGroupId !== input.renderGroupId) ||
                    repairBindingConflict(old.affectedVersions, input.affectedVersions))
            ) {
                conflict = true;
                transaction.abort();
                return;
            }
            result = old ?? {
                key,
                scope: { ...scope },
                ...input,
                status: input.status ?? "awaiting_receipt",
                operationId: input.operationId ?? null,
                candidateVersionId: input.candidateVersionId ?? null,
                needsReconciliation: input.needsReconciliation ?? false,
                disposition: input.disposition ?? null,
                createdAt: Date.now(),
                updatedAt: Date.now(),
            };
            if (!old) transaction.objectStore("submissionMarkers").put(result);
        };
        try {
            await done;
        } catch (error) {
            if (conflict)
                throw new RemakeDraftError(
                    "conflict",
                    "Khóa yêu cầu đã gắn với một lần sửa khác. Kiểm tra trạng thái trước khi tiếp tục.",
                );
            throw storageError(error);
        }
        return result!;
    }
    async function updateSubmissionMarker(
        scope: RemakeDraftScope,
        requestKey: string,
        patch: RemakeSubmissionMarkerPatch,
    ): Promise<RemakeSubmissionMarker> {
        const key = markerKey(scope, requestKey);
        const db = await open();
        const transaction = db.transaction("submissionMarkers", "readwrite");
        const done = transactionDone(transaction);
        let result: RemakeSubmissionMarker | undefined;
        let conflict = false;
        const request = transaction.objectStore("submissionMarkers").get(key);
        request.onsuccess = () => {
            const old = request.result as RemakeSubmissionMarker | undefined;
            if (!old) {
                transaction.abort();
                return;
            }
            if (
                (old.operationId && patch.operationId && old.operationId !== patch.operationId) ||
                (old.candidateVersionId &&
                    patch.candidateVersionId &&
                    old.candidateVersionId !== patch.candidateVersionId) ||
                (old.repairScope && patch.repairScope && old.repairScope !== patch.repairScope) ||
                (old.renderGroupId &&
                    patch.renderGroupId &&
                    old.renderGroupId !== patch.renderGroupId) ||
                repairBindingConflict(old.affectedVersions, patch.affectedVersions)
            ) {
                conflict = true;
                transaction.abort();
                return;
            }
            const affectedVersions = old.affectedVersions
                ? old.affectedVersions.map((binding, index) => ({
                      ...binding,
                      candidateVersionId:
                          binding.candidateVersionId ??
                          patch.affectedVersions?.[index].candidateVersionId ??
                          null,
                  }))
                : patch.affectedVersions;
            result = {
                ...old,
                ...patch,
                operationId: old.operationId ?? patch.operationId ?? null,
                candidateVersionId: old.candidateVersionId ?? patch.candidateVersionId ?? null,
                ...((old.repairScope ?? patch.repairScope)
                    ? { repairScope: old.repairScope ?? patch.repairScope }
                    : {}),
                ...((old.renderGroupId ?? patch.renderGroupId)
                    ? { renderGroupId: old.renderGroupId ?? patch.renderGroupId }
                    : {}),
                ...(affectedVersions ? { affectedVersions } : {}),
                status: old.status === "completed" ? "completed" : (patch.status ?? old.status),
                key: old.key,
                scope: old.scope,
                updatedAt: Date.now(),
            };
            transaction.objectStore("submissionMarkers").put(result);
        };
        try {
            await done;
        } catch (error) {
            if (conflict)
                throw new RemakeDraftError(
                    "conflict",
                    "Kết quả không khớp yêu cầu đã theo dõi. Kiểm tra trạng thái trước khi tiếp tục.",
                );
            throw storageError(error);
        }
        return result!;
    }
    function close() {
        if (database) void database.then((db) => db.close()).catch(() => undefined);
        database = null;
    }
    return {
        read,
        save,
        remove,
        close,
        writeSubmissionMarker,
        saveSubmissionMarker: writeSubmissionMarker,
        readSubmissionMarker,
        listSubmissionMarkers,
        updateSubmissionMarker,
    };
}
export const remakeDraftStore = createRemakeDraftStore();
export type RemakeDraftStore = ReturnType<typeof createRemakeDraftStore>;
