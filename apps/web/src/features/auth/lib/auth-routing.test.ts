import { describe, expect, it } from "vitest";

import { isPublicAuthPath, loginRedirectFor } from "./auth-routing";

describe("auth route protection", () => {
    it("allows reading the specific media policy without opening protected routes", () => {
        expect(isPublicAuthPath("/policies/media-rights")).toBe(true);
        expect(isPublicAuthPath("/policies/media-rights/")).toBe(true);
        expect(isPublicAuthPath("/policies/private")).toBe(false);
        expect(isPublicAuthPath("/policies/media-rights-extra")).toBe(false);
        expect(isPublicAuthPath("/policies/media-rights/secret")).toBe(false);
        expect(isPublicAuthPath("/smart-remake")).toBe(false);
    });
    it.each(["/", "/login", "/register", "/api/auth/login", "/api/auth/callback"])(
        "keeps %s public",
        (path) => {
            expect(isPublicAuthPath(path)).toBe(true);
        },
    );

    it.each(["/dashboard", "/products", "/account"])("protects %s", (path) => {
        expect(isPublicAuthPath(path)).toBe(false);
    });

    it("preserves a safe destination when redirecting to login", () => {
        expect(loginRedirectFor("/products?tab=active")).toEqual({
            to: "/login",
            search: { returnTo: "/products?tab=active" },
        });
    });
});
