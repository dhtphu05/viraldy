import {
    RemakeDraftError,
    remakeDraftScopeKey,
    type RemakeDraftScope,
    type RemakeDraftSnapshot,
} from "./remake-draft";
export type LegacyRemakeRepairIdentity = {
    workspaceId: string;
    projectId: string;
    sceneId: string;
    baseVersionId: string | null;
};
export type LegacyRemakeRepairDraft = {
    prompt: string;
    imagePrompt: string;
    videoPrompt: string;
    selectedReasons: string[];
    instruction: string;
};
type DraftStorage = Pick<Storage, "getItem" | "removeItem">;
const reasons = new Set(["Sai sản phẩm", "Chuyển động chưa đúng", "Hook chưa rõ"]);
/** Legacy keys predate account scoping. They can only be imported after an explicit user action. */
export function legacyRemakeRepairDraftKey(identity: LegacyRemakeRepairIdentity): string {
    return `viraldy:remake-draft:${identity.workspaceId}:${identity.projectId}:${identity.sceneId}:${identity.baseVersionId ?? "initial"}`;
}
export function getLegacyRemakeRepairDraft(
    storage: DraftStorage,
    identity: LegacyRemakeRepairIdentity,
): LegacyRemakeRepairDraft | null {
    try {
        const serialized = storage.getItem(legacyRemakeRepairDraftKey(identity));
        if (!serialized) return null;
        const value: unknown = JSON.parse(serialized);
        if (!value || typeof value !== "object") throw new Error("Invalid draft");
        const record = value as Record<string, unknown>;
        for (const key of ["prompt", "imagePrompt", "videoPrompt"] as const)
            if (typeof record[key] !== "string" || Array.from(record[key]).length > 12000)
                throw new Error("Invalid prompts");
        const instruction = typeof record.instruction === "string" ? record.instruction : "";
        if (Array.from(instruction).length > 4000) throw new Error("Invalid instruction");
        return {
            prompt: record.prompt as string,
            imagePrompt: record.imagePrompt as string,
            videoPrompt: record.videoPrompt as string,
            instruction,
            selectedReasons: Array.isArray(record.selectedReasons)
                ? record.selectedReasons.filter(
                      (item): item is string => typeof item === "string" && reasons.has(item),
                  )
                : [],
        };
    } catch {
        throw new RemakeDraftError(
            "invalid_data",
            "Không đọc được bản nháp cũ trên thiết bị này. Bản đã lưu chưa bị thay đổi.",
        );
    }
}
export async function importLegacyRemakeRepairDraft(options: {
    storage: DraftStorage;
    identity: LegacyRemakeRepairIdentity;
    scope: RemakeDraftScope;
    authorizedProjectId: string;
    commit(value: LegacyRemakeRepairDraft): Promise<RemakeDraftSnapshot>;
}): Promise<RemakeDraftSnapshot | null> {
    if (
        options.identity.workspaceId !== options.scope.workspaceId ||
        options.identity.projectId !== options.authorizedProjectId
    )
        throw new RemakeDraftError(
            "invalid_data",
            "Mở đúng workspace và dự án có quyền truy cập trước khi khôi phục bản nháp cũ.",
        );
    const key = remakeDraftScopeKey(options.scope);
    const value = getLegacyRemakeRepairDraft(options.storage, options.identity);
    if (!value) return null;
    const committed = await options.commit(value);
    if (remakeDraftScopeKey(committed.scope) !== key)
        throw new RemakeDraftError(
            "invalid_data",
            "Bản nháp chưa được lưu đúng tài khoản. Bản nháp cũ vẫn được giữ.",
        );
    options.storage.removeItem(legacyRemakeRepairDraftKey(options.identity));
    return committed;
}
