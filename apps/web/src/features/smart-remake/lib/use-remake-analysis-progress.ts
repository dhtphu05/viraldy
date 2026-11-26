import { useCallback, useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
    getSmartRemakeProject,
    type SmartRemakeAnalysisProgress,
    type SmartRemakeProject,
} from "@/shared/api/smart-remake";
import { ApiError } from "@/shared/api/errors";

interface AnalysisRead {
    token: number;
    workspaceId: string;
    startedAt: number;
    projectId?: string;
    requestKey?: string;
    baseRevision?: number;
    initialProgress?: SmartRemakeAnalysisProgress;
    state: "pending" | "interrupted" | "completed";
}

function matchingProgress(read: AnalysisRead | null, project?: SmartRemakeProject) {
    return read?.requestKey &&
        project &&
        project.id === read.projectId &&
        project.analysisProgress?.requestKey === read.requestKey
        ? project.analysisProgress
        : null;
}

export async function readAnalysisProject(
    workspaceId: string,
    projectId: string,
    signal: AbortSignal = new AbortController().signal,
) {
    const controller = new AbortController();
    let deadline: ReturnType<typeof setTimeout> | undefined;
    let abort = () => {};
    const stopped = new Promise<never>((_resolve, reject) => {
        abort = () => {
            controller.abort();
            reject(new Error("Analysis status read cancelled"));
        };
        signal.addEventListener("abort", abort, { once: true });
        deadline = setTimeout(() => {
            controller.abort();
            reject(new Error("Analysis status read timed out"));
        }, 15_000);
    });
    try {
        if (signal.aborted) abort();
        return await Promise.race([
            getSmartRemakeProject(workspaceId, projectId, { signal: controller.signal }),
            stopped,
        ]);
    } finally {
        clearTimeout(deadline);
        signal.removeEventListener("abort", abort);
    }
}

export function useRemakeAnalysisProgress(workspaceId: string) {
    const serial = useRef(0);
    const completionWaiter = useRef<{
        token: number;
        resolve(project: SmartRemakeProject): void;
        reject(cause: Error): void;
    } | null>(null);
    const [read, setRead] = useState<AnalysisRead | null>(null);
    const current = read?.workspaceId === workspaceId ? read : null;
    const active = current?.state !== "completed" ? current : null;
    const query = useQuery({
        queryKey: [
            "smart-remake",
            "analysis-progress",
            workspaceId,
            active?.projectId,
            active?.requestKey,
            active?.token,
        ],
        queryFn: ({ signal }) => readAnalysisProject(workspaceId, active!.projectId!, signal),
        enabled: Boolean(active?.projectId && active.requestKey),
        refetchInterval: (query) => {
            const checkpoint = matchingProgress(active, query.state.data);
            return query.state.error || (checkpoint && checkpoint.status !== "running")
                ? false
                : 2000;
        },
        refetchOnWindowFocus: false,
        retry: false,
        gcTime: 0,
    });
    const data = query.data;
    const supersedingProject =
        active?.state === "interrupted" &&
        data &&
        data.id === active.projectId &&
        ((data.pendingOperation &&
            ((Boolean(data.pendingOperation.kind) && data.pendingOperation.kind !== "compile") ||
                (active.initialProgress &&
                    data.pendingOperation.id !== active.initialProgress.operationId) ||
                (data.analysisProgress &&
                    data.analysisProgress.requestKey !== active.requestKey))) ||
            (data.analysisProgress &&
                data.analysisProgress.requestKey !== active.requestKey &&
                data.revision > (active.baseRevision ?? 0)))
            ? data
            : null;
    const progress = supersedingProject
        ? null
        : (matchingProgress(active, data) ?? active?.initialProgress ?? null);
    const { refetch } = query;
    useEffect(() => {
        const checkpoint = matchingProgress(active, data);
        const waiter = completionWaiter.current;
        if (!waiter || waiter.token !== active?.token) return;
        if (checkpoint?.status === "failed") {
            completionWaiter.current = null;
            waiter.reject(
                new ApiError(
                    checkpoint.errorCode || "SMART_REMAKE_COMPILE_FAILED",
                    "Phân tích chưa hoàn tất. Kiểm tra tư liệu và trạng thái trước khi thử lại.",
                    400,
                ),
            );
            return;
        }
        if (
            checkpoint?.status === "completed" &&
            data?.schemaVersion === 2 &&
            data.renderPlan &&
            data.expectationsVersion === 1 &&
            data.expectationsHash
        ) {
            completionWaiter.current = null;
            waiter.resolve(data);
        }
    }, [active, data]);
    useEffect(
        () => () => {
            completionWaiter.current = null;
        },
        [workspaceId],
    );
    const waitForCompletion = useCallback(
        (token: number) =>
            new Promise<SmartRemakeProject>((resolve, reject) => {
                completionWaiter.current = { token, resolve, reject };
            }),
        [],
    );
    const change = useCallback(
        (token: number, update: Partial<AnalysisRead>) => {
            setRead((current) =>
                current?.token === token && current.workspaceId === workspaceId
                    ? { ...current, ...update }
                    : current,
            );
        },
        [workspaceId],
    );
    const begin = useCallback(() => {
        completionWaiter.current = null;
        const token = ++serial.current;
        setRead({ token, workspaceId, startedAt: Date.now(), state: "pending" });
        return token;
    }, [workspaceId]);
    const track = useCallback(
        (token: number, projectId: string, requestKey: string, baseRevision = 0) => {
            change(token, { projectId, requestKey, baseRevision });
        },
        [change],
    );
    const complete = useCallback(
        (token: number) => {
            if (completionWaiter.current?.token === token) completionWaiter.current = null;
            change(token, { state: "completed" });
        },
        [change],
    );
    const interrupt = useCallback(
        (token: number) => {
            if (completionWaiter.current?.token === token) completionWaiter.current = null;
            setRead((current) =>
                current?.token === token && current.workspaceId === workspaceId
                    ? { ...current, state: current.projectId ? "interrupted" : "completed" }
                    : current,
            );
        },
        [workspaceId],
    );
    const restore = useCallback(
        (project: SmartRemakeProject, supersededToken?: number) => {
            const progress = project.analysisProgress;
            const operation = project.pendingOperation;
            if (
                !progress ||
                progress.status !== "running" ||
                operation?.kind !== "compile" ||
                operation.id !== progress.operationId
            )
                return;
            const token = ++serial.current;
            setRead((current) =>
                current?.workspaceId === workspaceId &&
                current.projectId === project.id &&
                !(current.token === supersededToken && current.state === "interrupted") &&
                !(
                    current.state === "completed" &&
                    progress.requestKey !== current.requestKey &&
                    project.revision > (current.baseRevision ?? -1)
                )
                    ? current
                    : {
                          token,
                          workspaceId,
                          projectId: project.id,
                          baseRevision: project.revision,
                          requestKey: progress.requestKey,
                          startedAt: Number.isFinite(Date.parse(progress.startedAt))
                              ? Date.parse(progress.startedAt)
                              : Date.now(),
                          state: "interrupted",
                          initialProgress: progress,
                      },
            );
        },
        [workspaceId],
    );
    const checkAnalysisStatus = useCallback(async () => {
        if (!active?.projectId || !active.requestKey) return;
        await refetch();
    }, [active?.projectId, active?.requestKey, refetch]);

    return {
        begin,
        waitForCompletion,
        track,
        complete,
        interrupt,
        restore,
        token: current?.token,
        analysisProgress: progress,
        analysisStartedAt: current?.startedAt,
        analysisPreparing: Boolean(
            active?.state === "pending" && (!active.projectId || !active.requestKey),
        ),
        canCheckAnalysisStatus: Boolean(active?.projectId && active.requestKey),
        analysisUnresolved:
            current?.state === "interrupted" &&
            progress?.status !== "failed" &&
            !supersedingProject,
        analysisStatusError: query.isError
            ? "Chưa lấy được tiến trình. Yêu cầu đã gửi vẫn được giữ; kiểm tra trạng thái để cập nhật."
            : current?.state === "interrupted" && !progress
              ? "Kết nối chờ kết quả bị gián đoạn. Kiểm tra trạng thái của yêu cầu đã gửi."
              : null,
        checkingAnalysisStatus: Boolean(active?.projectId && query.isFetching),
        checkAnalysisStatus,
        supersedingProject,
        failedProject:
            current?.state === "interrupted" && matchingProgress(active, data)?.status === "failed"
                ? (data ?? null)
                : null,
        recoveredProject:
            current?.state === "interrupted" && progress?.status === "completed"
                ? (query.data ?? null)
                : null,
    };
}
