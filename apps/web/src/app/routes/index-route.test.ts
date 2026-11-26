import { describe, expect, it } from "vitest";

import { Route } from "./index-route";

describe("home route", () => {
    it.each([false, true])(
        "redirects directly to login when authenticated is %s",
        async (authenticated) => {
            await expect(
                Promise.resolve().then(() =>
                    Route.options.beforeLoad?.({
                        context: { auth: { authenticated } },
                    } as never),
                ),
            ).rejects.toMatchObject({
                options: { to: "/login", replace: true },
            });
        },
    );
});
