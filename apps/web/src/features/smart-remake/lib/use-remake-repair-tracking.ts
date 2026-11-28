import { useCallback, useEffect, useRef, useState } from "react";
import {
    getSmartRemakeProject,
    getSmartRemakeRepairReceipt,
    type SmartRemakeProject,
    type SmartRemakeRepairAffectedVersion,
    type SmartRemakeRepairReceipt,
    type SmartRemakeSceneVersion,
} from "@/shared/api/smart-remake";
import {
    remakeDraftStore,
    type RemakeDraftScope,
    type RemakeSubmissionMarker,
    type RemakeSubmissionMarkerInput,
} from "./remake-draft";
import type { RemakeRepairCandidate } from "./remake-action";

type MarkerInput = RemakeSubmissionMarkerInput;
type Options = {
    scope: RemakeDraftScope | null;
    project: SmartRemakeProject | null;
    onProject(project: SmartRemakeProject): void;
};

function needsReceiptRecovery(marker: RemakeSubmissionMarker) {
    return (
        !marker.disposition &&
        (marker.needsReconciliation ||
            !["completed", "failed"].includes(marker.status) ||
            (marker.status === "completed" && Boolean(marker.candidateVersionId)))
    );
}

function shortIdentity(value: unknown): value is string {
    return typeof value === "string" && value.length > 0 && value.length <= 200;
}
function repairBindings(value: unknown): value is SmartRemakeRepairAffectedVersion[] {
    return (
        Array.isArray(value) &&
        value.length > 0 &&
        value.every(
            (binding) =>
                binding &&
                shortIdentity(binding.sceneId) &&
                (binding.baseVersionId === null || shortIdentity(binding.baseVersionId)) &&
                (binding.candidateVersionId === null || shortIdentity(binding.candidateVersionId)),
        ) &&
        new Set(value.map((binding) => binding.sceneId)).size === value.length
    );
}
function sameRepairBindings(left: unknown, right: unknown, pending = false) {
    return (
        repairBindings(left) &&
        repairBindings(right) &&
        left.length === right.length &&
        left.every(
            (binding, index) =>
                binding.sceneId === right[index].sceneId &&
                binding.baseVersionId === right[index].baseVersionId &&
                (binding.candidateVersionId === right[index].candidateVersionId ||
                    (pending && (!binding.candidateVersionId || !right[index].candidateVersionId))),
        )
    );
}
function hasGroupBindings(marker: RemakeSubmissionMarker) {
    return (
        marker.repairScope === "provider_group" &&
        shortIdentity(marker.operationId) &&
        shortIdentity(marker.renderGroupId) &&
        repairBindings(marker.affectedVersions) &&
        marker.affectedVersions.every(
            (binding) =>
                shortIdentity(binding.baseVersionId) &&
                (marker.status !== "completed" || shortIdentity(binding.candidateVersionId)),
        ) &&
        marker.affectedVersions.some(
            (binding) =>
                binding.sceneId === marker.sceneId &&
                binding.baseVersionId === marker.baseVersionId &&
                binding.candidateVersionId === marker.candidateVersionId,
        )
    );
}
function isGroupRepair(marker: RemakeSubmissionMarker, project: SmartRemakeProject | null) {
    const version = project?.scenes
        .find((scene) => scene.id === marker.sceneId)
        ?.versions.find((candidate) => candidate.id === marker.candidateVersionId);
    return (
        marker.repairScope === "provider_group" ||
        version?.providerMetadata?.repairScope === "provider_group"
    );
}
function needsGroupReceipt(marker: RemakeSubmissionMarker, project: SmartRemakeProject | null) {
    return (
        !marker.disposition &&
        marker.status === "completed" &&
        isGroupRepair(marker, project) &&
        !hasGroupBindings(marker)
    );
}
function matchesGroupVersion(
    version: SmartRemakeSceneVersion,
    binding: SmartRemakeRepairAffectedVersion,
    operationId: string,
    renderGroupId: string,
    bindings: SmartRemakeRepairAffectedVersion[],
) {
    const metadata = version.providerMetadata;
    return (
        version.parentVersionId === binding.baseVersionId &&
        metadata?.repairScope === "provider_group" &&
        metadata.renderGroupId === renderGroupId &&
        metadata.repairOperationId === operationId &&
        sameRepairBindings(metadata.repairAffectedVersions, bindings)
    );
}
function matchesBaseTimeline(
    saved: unknown,
    project: SmartRemakeProject | null,
    bindings: SmartRemakeRepairAffectedVersion[],
) {
    const members = new Set(bindings.map((binding) => binding.sceneId));
    const current = project?.draftTimeline?.items.filter((item) => members.has(item.renderUnitId));
    return (
        Array.isArray(saved) &&
        current?.length === bindings.length &&
        saved.length === current.length &&
        saved.every(
            (item, index) =>
                item &&
                item.renderUnitId === current[index].renderUnitId &&
                item.versionId === current[index].versionId &&
                item.inFrame === current[index].inFrame &&
                item.outFrame === current[index].outFrame,
        )
    );
}
function receiptGroupPatch(
    marker: RemakeSubmissionMarker,
    receipt: SmartRemakeRepairReceipt,
    project: SmartRemakeProject,
) {
    const mismatch = () => {
        throw new Error(
            "Biên nhận không khớp cảnh hoặc nhóm đã yêu cầu. Kiểm tra trạng thái trước khi tiếp tục.",
        );
    };
    if (
        !shortIdentity(receipt.operationId) ||
        receipt.sceneId !== marker.sceneId ||
        receipt.baseVersionId !== marker.baseVersionId ||
        (marker.operationId && marker.operationId !== receipt.operationId) ||
        (marker.candidateVersionId &&
            receipt.candidateVersionId &&
            marker.candidateVersionId !== receipt.candidateVersionId)
    )
        mismatch();
    if (!receipt.repairScope) {
        if (isGroupRepair(marker, project)) mismatch();
        return {};
    }
    const bindings = receipt.affectedVersions;
    if (
        receipt.repairScope !== "provider_group" ||
        !shortIdentity(receipt.renderGroupId) ||
        !repairBindings(bindings) ||
        (marker.repairScope && marker.repairScope !== receipt.repairScope) ||
        (marker.renderGroupId && marker.renderGroupId !== receipt.renderGroupId) ||
        (marker.affectedVersions && !sameRepairBindings(marker.affectedVersions, bindings, true))
    )
        return mismatch();
    if (
        !bindings.some(
            (binding) =>
                binding.sceneId === marker.sceneId &&
                binding.baseVersionId === marker.baseVersionId &&
                binding.candidateVersionId === receipt.candidateVersionId,
        ) ||
        bindings.some((binding) => {
            const scene = project.scenes.find((item) => item.id === binding.sceneId);
            const candidate = scene?.versions.find(
                (version) => version.id === binding.candidateVersionId,
            );
            return (
                !scene ||
                (binding.baseVersionId !== null &&
                    scene.activeVersionId !== binding.baseVersionId &&
                    !scene.versions.some((version) => version.id === binding.baseVersionId)) ||
                (candidate &&
                    !matchesGroupVersion(
                        candidate,
                        binding,
                        receipt.operationId,
                        receipt.renderGroupId!,
                        bindings,
                    ))
            );
        }) ||
        (receipt.status === "completed" &&
            bindings.some(
                (binding) =>
                    !shortIdentity(binding.baseVersionId) ||
                    !shortIdentity(binding.candidateVersionId),
            ))
    )
        return mismatch();
    return {
        repairScope: receipt.repairScope,
        renderGroupId: receipt.renderGroupId,
        affectedVersions: bindings.map((binding) => ({ ...binding })),
    };
}
function trackedCandidate(
    marker: RemakeSubmissionMarker,
    project: SmartRemakeProject | null,
): RemakeRepairCandidate | null {
    const scene = project?.scenes.find((item) => item.id === marker.sceneId);
    const version = scene?.versions.find((item) => item.id === marker.candidateVersionId);
    if (
        marker.status !== "completed" ||
        marker.disposition ||
        !version ||
        version.parentVersionId !== marker.baseVersionId ||
        version.id === scene?.activeVersionId ||
        version.usedByRevision != null
    )
        return null;
    const candidate = {
        projectId: marker.projectId,
        sceneId: marker.sceneId,
        versionId: version.id,
    };
    if (!isGroupRepair(marker, project)) return candidate;
    if (
        !hasGroupBindings(marker) ||
        !marker.affectedVersions?.every((binding) => {
            const member = project?.scenes.find((item) => item.id === binding.sceneId);
            const repaired = member?.versions.find(
                (item) => item.id === binding.candidateVersionId,
            );
            return (
                repaired &&
                member?.activeVersionId === binding.baseVersionId &&
                repaired.usedByRevision == null &&
                matchesBaseTimeline(
                    repaired.providerMetadata?.repairBaseTimeline,
                    project,
                    marker.affectedVersions!,
                ) &&
                matchesGroupVersion(
                    repaired,
                    binding,
                    marker.operationId!,
                    marker.renderGroupId!,
                    marker.affectedVersions!,
                )
            );
        })
    )
        return null;
    return {
        ...candidate,
        operationId: marker.operationId!,
        repairScope: "provider_group",
        renderGroupId: marker.renderGroupId!,
        affectedVersions: marker.affectedVersions,
    };
}

export function useRemakeRepairTracking(options: Options) {
    const latest = useRef(options);
    latest.current = options;
    const scopeKey = JSON.stringify(options.scope);
    const [markers, setMarkers] = useState<RemakeSubmissionMarker[]>([]);
    const [loaded, setLoaded] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const checking = useRef(false);
    const readable = useRef(false);
    const generation = useRef(0);

    useEffect(() => {
        const token = ++generation.current;
        setMarkers([]);
        readable.current = false;
        setLoaded(false);
        setError(null);
        const scope = latest.current.scope;
        if (!scope) {
            setLoaded(true);
            return;
        }
        void remakeDraftStore
            .listSubmissionMarkers(scope)
            .then(
                (saved) => {
                    if (token === generation.current) {
                        readable.current = true;
                        setMarkers(saved);
                    }
                },
                () => {
                    if (token === generation.current)
                        setError(
                            "Chưa đọc được yêu cầu đã lưu. Kiểm tra lưu trữ trước khi tạo lại cảnh.",
                        );
                },
            )
            .finally(() => {
                if (token === generation.current) setLoaded(true);
            });
        return () => {
            generation.current += 1;
        };
    }, [scopeKey]);

    function replaceMarker(marker: RemakeSubmissionMarker) {
        setMarkers((current) => [
            ...current.filter((item) => item.requestKey !== marker.requestKey),
            marker,
        ]);
    }
    async function begin(input: MarkerInput) {
        const scope = latest.current.scope;
        if (!scope || !loaded || !readable.current)
            throw new Error(
                "Chưa lưu được yêu cầu trên thiết bị. Mở lại phiên đăng nhập trước khi tạo lại.",
            );
        try {
            const saved = await remakeDraftStore.writeSubmissionMarker(scope, input);
            replaceMarker(saved);
            return saved;
        } catch {
            throw new Error(
                "Chưa lưu được yêu cầu trên thiết bị. Kiểm tra dung lượng rồi thử lại; chưa gửi AI.",
            );
        }
    }
    async function record(
        requestKey: string,
        patch: Parameters<typeof remakeDraftStore.updateSubmissionMarker>[2],
    ) {
        const scope = latest.current.scope;
        if (!scope) return;
        const saved = await remakeDraftStore.updateSubmissionMarker(scope, requestKey, patch);
        if (saved) replaceMarker(saved);
    }
    const refresh = useCallback(async () => {
        const { scope, project, onProject } = latest.current;
        if (!scope || checking.current) return;
        checking.current = true;
        const token = generation.current;
        try {
            const saved = await remakeDraftStore.listSubmissionMarkers(scope, project?.id);
            if (!project) {
                const marker = [...saved]
                    .filter(needsReceiptRecovery)
                    .sort((left, right) => right.createdAt - left.createdAt)[0];
                if (!marker) return;
                const fresh = await getSmartRemakeProject(scope.workspaceId, marker.projectId);
                if (token === generation.current && !latest.current.project) onProject(fresh);
                return;
            }
            const next = await Promise.all(
                saved.map(async (marker) => {
                    if (
                        marker.disposition ||
                        (marker.status === "failed" && marker.errorCode) ||
                        (marker.status === "completed" && !needsGroupReceipt(marker, project))
                    )
                        return marker;
                    const { receipt } = await getSmartRemakeRepairReceipt(
                        scope.workspaceId,
                        project.id,
                        marker.requestKey,
                    );
                    if (!receipt)
                        return await remakeDraftStore.updateSubmissionMarker(
                            scope,
                            marker.requestKey,
                            { status: "not_found", needsReconciliation: true },
                        );
                    const groupPatch = receiptGroupPatch(marker, receipt, project);
                    return await remakeDraftStore.updateSubmissionMarker(scope, marker.requestKey, {
                        status:
                            receipt.status === "completed"
                                ? "completed"
                                : receipt.status === "failed"
                                  ? "failed"
                                  : "running",
                        operationId: receipt.operationId,
                        candidateVersionId: receipt.candidateVersionId,
                        needsReconciliation: receipt.needsReconciliation,
                        errorCode: receipt.errorCode ?? null,
                        normalizationReason: receipt.normalizationReason ?? null,
                        ...groupPatch,
                    });
                }),
            );
            if (token !== generation.current || latest.current.project?.id !== project.id) return;
            readable.current = true;
            setMarkers((current) => [
                ...current.filter((item) => item.projectId !== project.id),
                ...next.filter((item): item is RemakeSubmissionMarker => Boolean(item)),
            ]);
            const missingCandidate = next.some(
                (marker) =>
                    marker?.status === "completed" &&
                    marker.candidateVersionId &&
                    [
                        { sceneId: marker.sceneId, candidateVersionId: marker.candidateVersionId },
                        ...(marker.affectedVersions ?? []),
                    ].some(
                        (binding) =>
                            binding.candidateVersionId &&
                            !project.scenes
                                .find((scene) => scene.id === binding.sceneId)
                                ?.versions.some(
                                    (version) => version.id === binding.candidateVersionId,
                                ),
                    ),
            );
            if (missingCandidate) {
                const fresh = await getSmartRemakeProject(scope.workspaceId, project.id);
                if (token === generation.current && latest.current.project?.id === project.id)
                    onProject(fresh);
            }
            setError(null);
        } catch (cause) {
            if (token === generation.current)
                setError(
                    cause instanceof Error
                        ? cause.message
                        : "Chưa kiểm tra được yêu cầu đã gửi. Thử kết nối lại.",
                );
        } finally {
            checking.current = false;
        }
    }, []);
    const projectId = options.project?.id;
    const revision = options.project?.revision;
    const recoverableReceipt = !projectId && markers.some(needsReceiptRecovery);
    useEffect(() => {
        if (!loaded || (!projectId && !recoverableReceipt)) return;
        void refresh();
        const timer = window.setInterval(() => void refresh(), 5000);
        return () => window.clearInterval(timer);
    }, [loaded, projectId, revision, recoverableReceipt, refresh]);

    const currentMarkers = markers.filter((marker) => !projectId || marker.projectId === projectId);
    const candidateMarker = currentMarkers.find((marker) =>
        trackedCandidate(marker, options.project),
    );
    const candidate = candidateMarker ? trackedCandidate(candidateMarker, options.project) : null;
    async function acknowledgeCandidate(disposition: "viewed" | "skipped") {
        if (!candidateMarker) return;
        try {
            await record(candidateMarker.requestKey, { disposition });
        } catch {
            setError("Chưa lưu được lựa chọn này trên thiết bị. Bản video hiện tại vẫn được giữ.");
        }
    }
    const latestByScene = new Map<string, RemakeSubmissionMarker>();
    for (const marker of [...currentMarkers].sort(
        (left, right) => right.createdAt - left.createdAt,
    ))
        if (!latestByScene.has(marker.sceneId)) latestByScene.set(marker.sceneId, marker);
    const failures = Object.fromEntries(
        [...latestByScene.values()]
            .filter(
                (marker) =>
                    marker.status === "failed" &&
                    options.project?.scenes.some(
                        (scene) =>
                            scene.id === marker.sceneId &&
                            scene.activeVersionId === marker.baseVersionId,
                    ),
            )
            .map((marker) => [
                marker.sceneId,
                marker.normalizationReason ??
                    (marker.errorCode === "SMART_REMAKE_REPAIR_INTENT_INVALID"
                        ? "Chưa hiểu rõ yêu cầu sửa. Mô tả lại hành động hoặc cách quay bạn muốn, rồi xác nhận một lượt mới."
                        : "Chưa tạo được bản sửa. Xem lại yêu cầu bằng ngôn ngữ thường trước khi thử lại."),
            ]),
    );
    return {
        loaded,
        error,
        candidate,
        failures,
        begin,
        record,
        refresh,
        acknowledgeCandidate,
        unresolved: currentMarkers.some(
            (marker) =>
                !["completed", "failed"].includes(marker.status) ||
                needsGroupReceipt(marker, options.project),
        ),
    };
}
