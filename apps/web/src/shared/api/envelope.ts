export type ApiEnvelope<T> = {
    success: boolean;
    data: T;
    error: { code: string; message: string; details?: Record<string, unknown> } | null;
    request_id: string;
};
