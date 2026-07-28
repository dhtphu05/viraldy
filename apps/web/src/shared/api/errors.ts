import type { ApiEnvelope } from "./envelope";

export class ApiError extends Error {
    code: string;
    status: number;

    constructor(code: string, message: string, status: number) {
        super(message);
        this.code = code;
        this.status = status;
    }
}

export async function unwrapEnvelope<T>(response: Response): Promise<T> {
    const payload = (await response.json()) as ApiEnvelope<T>;
    if (!response.ok || payload.error) {
        throw new ApiError(
            payload.error?.code ?? "API_ERROR",
            payload.error?.message ?? "API request failed.",
            response.status,
        );
    }
    return payload.data;
}
