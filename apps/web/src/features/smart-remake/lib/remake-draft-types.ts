import type { SmartRemakeRepairAffectedVersion } from "@/shared/api/smart-remake";

export type RemakeDraftScope = { accountId: string; workspaceId: string; draftId: string };
export type RemakeDraftSectionName = "intake" | "requirements" | "storyboard" | "repair" | "view";
export type RemakeDraftSection = { baseline: string | null; value: unknown };
export type RemakeDraftSections = Partial<Record<RemakeDraftSectionName, RemakeDraftSection>>;
export type RemakeDraftBaselines = Partial<Record<RemakeDraftSectionName, string | null>>;
export type RemakeDraftFiles = {
    video: File | null;
    products: File[];
    primaryProductIndex: number;
    character: File | null;
};
export type RemakeDraftMediaReference = {
    key: string;
    sha256: string;
    name: string;
    type: string;
    size: number;
    lastModified: number;
};
export type RemakeDraftMedia = {
    video: RemakeDraftMediaReference | null;
    products: RemakeDraftMediaReference[];
    primaryProductIndex: number;
    character: RemakeDraftMediaReference | null;
};
export type RemakeDraftServerBinding = { projectId: string; mediaDigest: string };
export type RemakeDraftSnapshot = {
    schemaVersion: 1;
    key: string;
    scope: RemakeDraftScope;
    revision: number;
    sections: RemakeDraftSections;
    media: RemakeDraftMedia;
    serverBinding: RemakeDraftServerBinding | null;
    updatedAt: number;
};
export type RemakeDraftReadResult = { snapshot: RemakeDraftSnapshot; files: RemakeDraftFiles };
export type RemakeDraftValue = {
    sections: RemakeDraftSections;
    files?: RemakeDraftFiles;
    serverBinding?: RemakeDraftServerBinding | null;
};
export type RemakeSubmissionMarker = {
    key: string;
    scope: RemakeDraftScope;
    requestKey: string;
    requestFingerprint: string;
    projectId: string;
    sceneId: string;
    baseVersionId: string | null;
    status: "awaiting_receipt" | "not_found" | "running" | "completed" | "failed";
    operationId: string | null;
    candidateVersionId: string | null;
    needsReconciliation: boolean;
    disposition: "viewed" | "skipped" | null;
    errorCode?: string | null;
    normalizationReason?: string | null;
    repairScope?: "provider_group";
    renderGroupId?: string;
    affectedVersions?: SmartRemakeRepairAffectedVersion[];
    createdAt: number;
    updatedAt: number;
};
export type RemakeSubmissionMarkerInput = Pick<
    RemakeSubmissionMarker,
    "requestKey" | "requestFingerprint" | "projectId" | "sceneId" | "baseVersionId"
> &
    Partial<
        Pick<
            RemakeSubmissionMarker,
            | "status"
            | "operationId"
            | "candidateVersionId"
            | "needsReconciliation"
            | "disposition"
            | "errorCode"
            | "normalizationReason"
            | "repairScope"
            | "renderGroupId"
            | "affectedVersions"
        >
    >;
export type RemakeSubmissionMarkerPatch = Partial<
    Pick<
        RemakeSubmissionMarker,
        | "status"
        | "operationId"
        | "candidateVersionId"
        | "needsReconciliation"
        | "disposition"
        | "errorCode"
        | "normalizationReason"
        | "repairScope"
        | "renderGroupId"
        | "affectedVersions"
    >
>;
export type RemakeDraftErrorCode =
    | "unavailable"
    | "blocked"
    | "quota"
    | "aborted"
    | "conflict"
    | "invalid_media"
    | "corrupt"
    | "invalid_data";
export class RemakeDraftError extends Error {
    constructor(
        public readonly code: RemakeDraftErrorCode,
        message: string,
    ) {
        super(message);
        this.name = "RemakeDraftError";
    }
}
