import { sanitizeReturnTo } from "./auth-flow";

const PUBLIC_AUTH_PATHS = ["/login", "/register", "/api/auth"];

export function isPublicAuthPath(pathname: string): boolean {
    return PUBLIC_AUTH_PATHS.some(
        (prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`),
    );
}

export function loginRedirectFor(location: string) {
    return {
        to: "/login" as const,
        search: { returnTo: sanitizeReturnTo(location) },
    };
}
