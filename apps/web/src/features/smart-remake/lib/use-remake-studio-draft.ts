import { useCallback, useEffect, useRef, useState } from "react";
import {
    remakeDraftStore,
    type RemakeDraftScope,
    type RemakeDraftReadResult,
} from "./remake-draft";

type DraftValue = Parameters<typeof remakeDraftStore.save>[1];
export type RemakeDraftSaveStatus =
    "loading" | "unsaved" | "saving" | "saved" | "error" | "conflict";
type Options = {
    scope: RemakeDraftScope | null;
    value: DraftValue;
    suspended?: boolean;
    onRestore(saved: RemakeDraftReadResult | null, isCurrent: () => boolean): Promise<void> | void;
};
function sameDraft(left: DraftValue, right: DraftValue) {
    return (
        left.files === right.files &&
        JSON.stringify(left.sections) === JSON.stringify(right.sections) &&
        JSON.stringify(left.serverBinding) === JSON.stringify(right.serverBinding)
    );
}
export function useRemakeStudioDraft(options: Options) {
    const latest = useRef(options);
    latest.current = options;
    const [loaded, setLoaded] = useState(false);
    const [status, setStatus] = useState<RemakeDraftSaveStatus>("loading");
    const [error, setError] = useState<string | null>(null);
    const revision = useRef<number | null>(null);
    const canSave = useRef(false);
    const generation = useRef(0);
    const saving = useRef<Promise<unknown> | null>(null);
    const discarded = useRef<DraftValue | null>(null);
    const key = JSON.stringify(options.scope);
    useEffect(() => {
        const token = ++generation.current;
        setLoaded(false);
        setStatus("loading");
        setError(null);
        revision.current = null;
        canSave.current = false;
        discarded.current = null;
        const scope = latest.current.scope;
        if (!scope) {
            setLoaded(true);
            setStatus("unsaved");
            return;
        }
        void remakeDraftStore
            .read(scope)
            .then(async (saved) => {
                if (token !== generation.current) return;
                revision.current = saved?.snapshot.revision ?? null;
                await latest.current.onRestore(saved, () => token === generation.current);
                if (token === generation.current) {
                    canSave.current = true;
                    setLoaded(true);
                    setStatus("unsaved");
                }
            })
            .catch(() => {
                if (token !== generation.current) return;
                setLoaded(true);
                setStatus("error");
                setError(
                    "Chưa đọc được nháp trên thiết bị. Bản đã lưu vẫn được giữ; tải lại để thử lại.",
                );
            });
        return () => {
            generation.current += 1;
        };
    }, [key]);
    const commit = useCallback(async (update?: (value: DraftValue) => DraftValue) => {
        while (saving.current) await saving.current.catch(() => undefined);
        const { scope } = latest.current;
        if (!scope || !canSave.current || latest.current.suspended)
            throw new Error(
                "Chưa thể lưu nháp. Kiểm tra lưu trữ hoặc phần xung đột trước khi tiếp tục.",
            );
        const token = generation.current;
        const value = update ? update(latest.current.value) : latest.current.value;
        setStatus("saving");
        const promise = remakeDraftStore.save(scope, value, revision.current);
        saving.current = promise;
        try {
            const snapshot = await promise;
            if (token === generation.current) {
                revision.current = snapshot.revision;
                setStatus(sameDraft(value, latest.current.value) ? "saved" : "unsaved");
                setError(null);
            }
            return snapshot;
        } catch (cause) {
            if (token === generation.current) {
                setStatus("error");
                setError(
                    cause instanceof Error && cause.message.includes("tab khác")
                        ? cause.message
                        : "Chưa lưu được nháp trên thiết bị. Giữ trang này mở và kiểm tra dung lượng; tư liệu trong phiên vẫn được giữ.",
                );
            }
            throw cause;
        } finally {
            if (saving.current === promise) saving.current = null;
        }
    }, []);
    const flush = useCallback(async () => {
        if (!latest.current.scope || !canSave.current || !loaded) return;
        if (latest.current.suspended) {
            setStatus("conflict");
            return;
        }
        if (discarded.current && sameDraft(discarded.current, latest.current.value)) return;
        try {
            await commit();
        } catch {
            /* The committed draft and the visible error remain. */
        }
    }, [loaded, commit]);
    async function remove() {
        while (saving.current) await saving.current.catch(() => undefined);
        const { scope, value } = latest.current;
        if (!scope) return false;
        try {
            await remakeDraftStore.remove(scope);
            revision.current = null;
            discarded.current = value;
            canSave.current = true;
            setStatus("unsaved");
            setError(null);
            return true;
        } catch {
            setStatus("error");
            setError("Chưa xóa được nháp trên thiết bị. Bản đã lưu vẫn được giữ.");
            return false;
        }
    }
    const sections = JSON.stringify(options.value.sections);
    const binding = JSON.stringify(options.value.serverBinding);
    const files = options.value.files;
    useEffect(() => {
        if (!loaded || !latest.current.scope || !canSave.current) return;
        if (latest.current.suspended) {
            setStatus("conflict");
            return;
        }
        if (discarded.current && sameDraft(discarded.current, latest.current.value)) return;
        discarded.current = null;
        setStatus((current) => (current === "error" ? current : "unsaved"));
        const timer = window.setTimeout(() => void flush(), 500);
        return () => window.clearTimeout(timer);
    }, [loaded, sections, binding, files, options.suspended, flush]);
    useEffect(() => {
        const save = () => void flush();
        window.addEventListener("pagehide", save);
        document.addEventListener("visibilitychange", save);
        return () => {
            window.removeEventListener("pagehide", save);
            document.removeEventListener("visibilitychange", save);
        };
    }, [flush]);
    return { loaded, status, error, flush, commit, remove };
}
