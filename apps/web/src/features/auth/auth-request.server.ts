export function authRequestUrl(request: Request): URL {
    const url = new URL(request.url);
    const configuredOrigin = process.env.AUTH_PUBLIC_ORIGIN;
    if (!configuredOrigin) {
        if (process.env.NODE_ENV === "production")
            throw new Error("AUTH_PUBLIC_ORIGIN is required");
        return url;
    }
    const origin = new URL(configuredOrigin);
    if (
        !["http:", "https:"].includes(origin.protocol) ||
        origin.username ||
        origin.password ||
        origin.pathname !== "/" ||
        origin.search ||
        origin.hash ||
        (process.env.NODE_ENV === "production" && origin.protocol !== "https:")
    ) {
        throw new Error("AUTH_PUBLIC_ORIGIN must be an origin and use HTTPS in production");
    }
    return new URL(`${url.pathname}${url.search}`, origin.origin);
}
