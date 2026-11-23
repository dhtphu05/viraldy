import { afterEach, beforeEach, expect, it, vi } from "vitest";

const assign = vi.fn();
let fetchMock: ReturnType<typeof vi.fn>;

beforeEach(() => {
    vi.resetModules();
    vi.clearAllMocks();
    fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    vi.stubGlobal("window", {
        location: {
            origin: "https://app.example",
            pathname: "/account",
            search: "",
            hash: "",
            assign,
        },
    });
});
afterEach(() => vi.unstubAllGlobals());

it("preserves the session on a temporary refresh service failure", async () => {
    fetchMock
        .mockResolvedValueOnce(new Response(null, { status: 401 }))
        .mockResolvedValueOnce(new Response(null, { status: 503 }));
    const { apiGet } = await import("./client");
    await expect(apiGet("/me")).rejects.toMatchObject({ status: 503 });
    expect(assign).not.toHaveBeenCalled();
});

it("redirects to sign-in only when refresh credentials are rejected", async () => {
    fetchMock
        .mockResolvedValueOnce(
            Response.json({ error: { code: "UNAUTHENTICATED" } }, { status: 401 }),
        )
        .mockResolvedValueOnce(new Response(null, { status: 401 }));
    const { apiGet } = await import("./client");
    await expect(apiGet("/me")).rejects.toMatchObject({ status: 401 });
    expect(assign).toHaveBeenCalledWith(expect.stringContaining("/login?returnTo=%2Faccount"));
});
