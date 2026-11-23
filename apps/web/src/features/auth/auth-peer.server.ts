import { createHmac } from "node:crypto";
import { isIP } from "node:net";
import { getRequestIP } from "@tanstack/react-start/server";

export function authPeerHeaders(): Record<string, string> {
    const secret = process.env.AUTH_PROXY_SECRET;
    if (!secret) {
        if (process.env.NODE_ENV === "production") throw new Error("AUTH_PROXY_SECRET is required");
        return {};
    }
    const ip = getRequestIP({ xForwardedFor: process.env.AUTH_TRUST_PROXY_HEADERS === "true" });
    if (!ip || !isIP(ip)) throw new Error("Client address is unavailable");
    const time = String(Math.floor(Date.now() / 1000));
    return {
        "x-viraldy-client-ip": ip,
        "x-viraldy-client-time": time,
        "x-viraldy-client-signature": createHmac("sha256", secret)
            .update(`${time}:${ip}`)
            .digest("hex"),
    };
}
