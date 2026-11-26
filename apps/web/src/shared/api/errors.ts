import type { ApiEnvelope } from "./envelope";

export class ApiError extends Error {
    code: string;
    status: number;
    details?: Record<string, unknown>;

    constructor(code: string, message: string, status: number, details?: Record<string, unknown>) {
        super(message);
        this.code = code;
        this.status = status;
        this.details = details;
    }
}

export async function unwrapEnvelope<T>(response: Response): Promise<T> {
    const payload = (await response.json()) as ApiEnvelope<T>;
    if (!response.ok || payload.error) {
        throw new ApiError(
            payload.error?.code ?? "API_ERROR",
            payload.error?.message ?? "API request failed.",
            response.status,
            payload.error?.details,
        );
    }
    return payload.data;
}
