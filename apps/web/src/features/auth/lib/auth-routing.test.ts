import { describe, expect, it } from "vitest";

import { isPublicAuthPath, loginRedirectFor } from "./auth-routing";

describe("auth route protection", () => {
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
