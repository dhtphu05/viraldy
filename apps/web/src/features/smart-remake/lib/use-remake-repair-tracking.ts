import { useCallback, useEffect, useRef, useState } from "react";
import {
    getSmartRemakeProject,
    getSmartRemakeRepairReceipt,
    type SmartRemakeProject,
} from "@/shared/api/smart-remake";
import {
    remakeDraftStore,
    type RemakeDraftScope,
    type RemakeSubmissionMarker,
} from "./remake-draft";
import type { RemakeRepairCandidate } from "./remake-action";

type MarkerInput = Pick<
    RemakeSubmissionMarker,
    "requestKey" | "requestFingerprint" | "projectId" | "sceneId" | "baseVersionId"
>;
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
                        marker.status === "completed"
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
                    if (
                        receipt.sceneId !== marker.sceneId ||
                        receipt.baseVersionId !== marker.baseVersionId
                    )
                        throw new Error(
                            "Biên nhận không khớp cảnh đã yêu cầu. Kiểm tra trạng thái trước khi tiếp tục.",
                        );
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
                    !project.scenes
                        .find((scene) => scene.id === marker.sceneId)
                        ?.versions.some((version) => version.id === marker.candidateVersionId),
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
    const candidateMarker = currentMarkers.find((marker) => {
        const scene = options.project?.scenes.find((item) => item.id === marker.sceneId);
        const version = scene?.versions.find((item) => item.id === marker.candidateVersionId);
        return (
            marker.status === "completed" &&
            !marker.disposition &&
            version &&
            version.parentVersionId === marker.baseVersionId &&
            version.id !== scene?.activeVersionId &&
            version.usedByRevision == null
        );
    });
    const candidate: RemakeRepairCandidate | null = candidateMarker?.candidateVersionId
        ? {
              projectId: candidateMarker.projectId,
              sceneId: candidateMarker.sceneId,
              versionId: candidateMarker.candidateVersionId,
          }
        : null;
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
            (marker) => !["completed", "failed"].includes(marker.status),
        ),
    };
}
