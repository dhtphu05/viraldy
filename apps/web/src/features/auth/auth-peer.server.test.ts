import { createHmac } from "node:crypto";
import { afterEach, describe, expect, it, vi } from "vitest";

const getIP = vi.hoisted(() => vi.fn());
vi.mock("@tanstack/react-start/server", () => ({ getRequestIP: getIP }));
import { authPeerHeaders } from "./auth-peer.server";

afterEach(() => {
    vi.unstubAllEnvs();
    vi.clearAllMocks();
});

describe("authenticated client address forwarding", () => {
    it("uses the server transport IP unless trusted ingress headers are explicitly enabled", () => {
        vi.stubEnv("AUTH_PROXY_SECRET", "test-only-peer-key-at-least-32-characters");
        vi.stubEnv("AUTH_TRUST_PROXY_HEADERS", "false");
        getIP.mockReturnValue("203.0.113.10");
        const headers = authPeerHeaders();
        expect(getIP).toHaveBeenCalledWith({ xForwardedFor: false });
        expect(headers["x-viraldy-client-signature"]).toBe(
            createHmac("sha256", process.env.AUTH_PROXY_SECRET!)
                .update(`${headers["x-viraldy-client-time"]}:203.0.113.10`)
                .digest("hex"),
        );
    });

    it("requires a shared secret in production", () => {
        vi.stubEnv("NODE_ENV", "production");
        vi.stubEnv("AUTH_PROXY_SECRET", "");
        expect(() => authPeerHeaders()).toThrow("AUTH_PROXY_SECRET");
    });
});
