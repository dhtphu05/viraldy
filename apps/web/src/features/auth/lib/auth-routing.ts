import { sanitizeReturnTo } from "./auth-flow";
import { MEDIA_RIGHTS_POLICY_PATH } from "@/features/policies/media-rights-policy";

const PUBLIC_AUTH_PATHS = ["/", "/login", "/register", "/api/auth"];

export function isPublicAuthPath(pathname: string): boolean {
    if (pathname === MEDIA_RIGHTS_POLICY_PATH || pathname === `${MEDIA_RIGHTS_POLICY_PATH}/`)
        return true;
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
