import { describe, expect, it } from "vitest";

import { backendPathFromRequest, hasValidMutationOrigin, upstreamRequestInit } from "./auth-proxy";

describe("backendPathFromRequest", () => {
    it("keeps only the backend-relative path and query", () => {
        expect(
            backendPathFromRequest(
                "https://app.viraldy.com/api/backend/workspaces/123/products?limit=20",
            ),
        ).toBe("/workspaces/123/products?limit=20");
    });

    it.each([
        "https://app.viraldy.com/api/backend",
        "https://app.viraldy.com/api/backend/",
        "https://app.viraldy.com/not-the-proxy/workspaces",
    ])("rejects a request outside the proxy contract: %s", (url) => {
        expect(() => backendPathFromRequest(url)).toThrow("Invalid backend proxy path");
    });
});

describe("hasValidMutationOrigin", () => {
    it("accepts a same-origin POST", () => {
        expect(
            hasValidMutationOrigin({
                requestUrl: "https://app.viraldy.com/api/backend/workspaces",
                origin: "https://app.viraldy.com",
            }),
        ).toBe(true);
    });

    it.each([undefined, "https://evil.example"])("rejects origin %s", (origin) => {
        expect(
            hasValidMutationOrigin({
                requestUrl: "https://app.viraldy.com/api/backend/workspaces",
                origin,
            }),
        ).toBe(false);
    });
});

describe("upstreamRequestInit", () => {
    it("streams mutation bodies with the Node fetch duplex contract", () => {
        const request = new Request("https://app.viraldy.com/api/backend/workspaces", {
            method: "POST",
            body: JSON.stringify({ name: "Store" }),
        });
        const init = upstreamRequestInit(request, new Headers());

        expect(init.body).toBe(request.body);
        expect(init.duplex).toBe("half");
    });

    it("does not attach a body or duplex mode to GET requests", () => {
        const init = upstreamRequestInit(
            new Request("https://app.viraldy.com/api/backend/me"),
            new Headers(),
        );

        expect(init.body).toBeUndefined();
        expect(init.duplex).toBeUndefined();
    });
});
