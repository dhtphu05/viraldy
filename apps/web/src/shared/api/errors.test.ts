import { expect, it } from "vitest";
import { ApiError, unwrapEnvelope } from "./errors";

it("preserves recoverable project details on an API failure", async () => {
    const response = Response.json(
        {
            error: {
                code: "SMART_REMAKE_RENDER_FAILED",
                message: "Render failed",
                details: { repairProjectId: "project-1" },
            },
        },
        { status: 400 },
    );
    await expect(unwrapEnvelope(response)).rejects.toMatchObject({
        code: "SMART_REMAKE_RENDER_FAILED",
        status: 400,
        details: { repairProjectId: "project-1" },
    });
});

it("keeps existing ApiError construction compatible", () => {
    const error = new ApiError("UNAUTHENTICATED", "Sign in", 401);
    expect(error.message).toBe("Sign in");
    expect(error.status).toBe(401);
});
