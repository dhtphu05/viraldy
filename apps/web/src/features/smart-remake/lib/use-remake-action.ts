import { useEffect, useRef, useState } from "react";
import { ApiError } from "@/shared/api/errors";
import {
    getSmartRemakePreflight,
    type SmartRemakePreflight,
    type SmartRemakePreflightRequest,
} from "@/shared/api/smart-remake";
import { getRemakeErrorMessage } from "./smart-remake-render";
import {
    getRemakeActionBudgetError,
    remakePreflightChanged,
    type RemakeActionIntent,
    type RemakeActionSnapshot,
} from "./remake-action";

type Options = {
    workspaceId: string;
    fingerprint: string;
    request(intent: RemakeActionIntent): SmartRemakePreflightRequest;
    validate(intent: RemakeActionIntent, snapshot?: RemakeActionSnapshot): string | null;
    execute(intent: RemakeActionIntent, snapshot: RemakeActionSnapshot): Promise<boolean>;
    failureMessage?(): string | null;
    failureCode?(): string | null;
};
export function useRemakeAction(options: Options) {
    const latest = useRef(options);
    latest.current = options;
    const [pendingAction, setPendingAction] = useState<RemakeActionIntent | null>(null);
    const [actionExecutingIntent, setExecutingIntent] = useState<RemakeActionIntent | null>(null);
    const current = useRef<RemakeActionIntent | null>(null);
    const [actionPreflight, setPreflight] = useState<SmartRemakePreflight | null>(null);
    const [actionLoading, setLoading] = useState(false);
    const [actionSubmitting, setSubmitting] = useState(false);
    const [actionError, setError] = useState<string | null>(null);
    const [actionErrorCode, setErrorCode] = useState<string | null>(null);
    const version = useRef(0);
    const confirming = useRef(false);
    const directOpening = useRef(false);
    useEffect(
        () => () => {
            version.current += 1;
            current.current = null;
        },
        [],
    );

    function cancelAction() {
        if (confirming.current) return;
        version.current += 1;
        current.current = null;
        setPendingAction(null);
        setPreflight(null);
        setError(null);
        setErrorCode(null);
        setLoading(false);
    }
    async function openAction(intent: RemakeActionIntent, approvedSnapshot?: RemakeActionSnapshot) {
        if (confirming.current || directOpening.current) return;
        setErrorCode(null);
        const token = ++version.current;
        const invalid = latest.current.validate(intent, approvedSnapshot);
        if (invalid) {
            setError(invalid);
            return;
        }
        if (approvedSnapshot) {
            directOpening.current = true;
            setExecutingIntent(intent);
        }
        current.current = intent;
        setPendingAction(approvedSnapshot ? null : intent);
        setPreflight(null);
        setLoading(true);
        setError(null);
        try {
            const proposal = await getSmartRemakePreflight(
                options.workspaceId,
                latest.current.request(intent),
            );
            if (token !== version.current || current.current !== intent) return;
            setPreflight(proposal);
            if (approvedSnapshot) await confirmAction(approvedSnapshot, proposal);
        } catch (cause) {
            if (token === version.current) {
                setError(getRemakeErrorMessage(cause));
                setErrorCode(cause instanceof ApiError ? cause.code : null);
            }
        } finally {
            if (approvedSnapshot) {
                directOpening.current = false;
                setExecutingIntent(null);
            }
            if (token === version.current) setLoading(false);
        }
    }
    async function confirmAction(snapshot: RemakeActionSnapshot, displayed = actionPreflight) {
        const intent = current.current;
        const approved = structuredClone(snapshot);
        if (confirming.current || !intent || !displayed) return "blocked" as const;
        setErrorCode(null);
        const invalid = latest.current.validate(intent, approved);
        if (intent.fingerprint !== latest.current.fingerprint || invalid) {
            setError(invalid ?? "Tư liệu hoặc kịch bản đã thay đổi. Đóng và chọn lại hành động.");
            return "invalid" as const;
        }
        confirming.current = true;
        setSubmitting(true);
        setError(null);
        try {
            const proposal = await getSmartRemakePreflight(
                options.workspaceId,
                latest.current.request(intent),
            );
            if (current.current !== intent || intent.fingerprint !== latest.current.fingerprint) {
                setError("Tư liệu hoặc kịch bản đã thay đổi. Đóng và chọn lại hành động.");
                return "invalid" as const;
            }
            setPreflight(proposal);
            if (proposal.blockers.length) {
                setError(proposal.blockers.map((item) => item.message).join(" "));
                return "blocked" as const;
            }
            if (remakePreflightChanged(displayed, proposal, approved.budget)) {
                setError("Phạm vi hoặc giới hạn dự phòng đã cập nhật. Kiểm tra và xác nhận lại.");
                return "changed" as const;
            }
            const budgetError = getRemakeActionBudgetError(approved.budget, proposal);
            if (budgetError) {
                setError(budgetError);
                return "blocked" as const;
            }
            const validation = latest.current.validate(intent, approved);
            if (validation) {
                setError(validation);
                return "invalid" as const;
            }
            const done = await latest.current.execute(intent, approved);
            if (!done) {
                setErrorCode(latest.current.failureCode?.() ?? null);
                setError(
                    latest.current.failureMessage?.() ??
                        "Thao tác chưa hoàn tất. Kiểm tra trạng thái trước khi thử lại.",
                );
                return "blocked" as const;
            }
            current.current = null;
            setPendingAction(null);
            setPreflight(null);
            return "completed" as const;
        } catch (cause) {
            setError(getRemakeErrorMessage(cause));
            setErrorCode(cause instanceof ApiError ? cause.code : null);
            return "blocked" as const;
        } finally {
            confirming.current = false;
            setSubmitting(false);
        }
    }
    return {
        pendingAction,
        actionExecutingIntent,
        actionPreflight,
        actionLoading,
        actionSubmitting,
        actionError,
        actionErrorCode,
        openAction,
        confirmAction,
        cancelAction,
        retryAction: () => (current.current ? openAction(current.current) : Promise.resolve()),
    };
}
