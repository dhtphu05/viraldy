import { z } from "zod";

const requiredOidcScopes = ["openid", "profile", "email", "phone", "offline_access"] as const;

const authConfigSchema = z.object({
    auth_mode: z.enum(["local_test", "oidc"]),
    enabled: z.boolean(),
    authorization_url: z.string().url().nullable(),
    token_url: z.string().url().nullable(),
    client_id: z.string().min(1).nullable(),
    scopes: z.array(z.string().min(1)),
    registration_url: z.string().url().nullable(),
    end_session_url: z.string().url().nullable(),
});

const currentUserSchema = z.object({
    id: z.string().uuid(),
    email: z.string().email(),
    display_name: z.string().trim().min(1).max(255),
    phone_number: z.string().regex(/^\+[1-9]\d{1,14}$/),
    status: z.literal("active"),
});

export type AuthConfig = z.infer<typeof authConfigSchema>;
export type CurrentUser = z.infer<typeof currentUserSchema>;

export function parseAuthConfig(payload: unknown): AuthConfig {
    const parsed = authConfigSchema.safeParse(payload);
    if (!parsed.success) throw new Error("Auth configuration was invalid");
    if (parsed.data.auth_mode === "oidc") {
        const complete =
            parsed.data.authorization_url !== null &&
            parsed.data.token_url !== null &&
            parsed.data.client_id !== null &&
            requiredOidcScopes.every((scope) => parsed.data.scopes.includes(scope));
        if (!complete) throw new Error("OIDC browser configuration is incomplete");
    }
    return parsed.data;
}

export function parseCurrentUser(payload: unknown): CurrentUser {
    const parsed = currentUserSchema.safeParse(payload);
    if (!parsed.success) throw new Error("Authenticated profile was invalid");
    return parsed.data;
}

export function profileInitials(user: Pick<CurrentUser, "display_name" | "email">): string {
    const words = user.display_name.trim().split(/\s+/).filter(Boolean);
    if (words.length >= 2) {
        return `${words[0][0]}${words[words.length - 1][0]}`.toUpperCase();
    }
    const single = words[0] || user.email.split("@", 1)[0] || "U";
    return single.slice(0, 2).toUpperCase();
}
