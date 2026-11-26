import { z } from "zod";

const requiredOidcScopes = ["openid", "profile", "email", "offline_access"] as const;

const authConfigSchema = z.object({
    auth_mode: z.enum(["local_test", "oidc", "password"]),
    enabled: z.boolean(),
    authorization_url: z.string().url().nullable(),
    token_url: z.string().url().nullable(),
    client_id: z.string().min(1).nullable(),
    scopes: z.array(z.string().min(1)),
    registration_url: z.string().url().nullable(),
    end_session_url: z.string().url().nullable(),
    revocation_url: z.string().url().nullable().default(null),
});

const currentUserSchema = z.object({
    id: z.string().uuid(),
    email: z.string().email(),
    display_name: z.string().trim().min(1).max(255),
    phone_number: z
        .string()
        .regex(/^\+[1-9]\d{1,14}$/)
        .nullable(),
    status: z.literal("active"),
});

export type AuthConfig = z.infer<typeof authConfigSchema>;
export type CurrentUser = z.infer<typeof currentUserSchema>;

export const MAX_PASSWORD_CHARACTERS = 1024;

function passwordSchema(minimum: number) {
    return z.string().superRefine((password, context) => {
        const characters = Array.from(password).length;
        if (characters < minimum) {
            context.addIssue({
                code: z.ZodIssueCode.custom,
                message:
                    minimum === 1
                        ? "Vui lòng nhập mật khẩu."
                        : "Mật khẩu hoặc cụm mật khẩu phải có ít nhất 12 ký tự.",
            });
        } else if (characters > MAX_PASSWORD_CHARACTERS) {
            context.addIssue({
                code: z.ZodIssueCode.custom,
                message: "Mật khẩu quá dài. Vui lòng chọn mật khẩu ngắn hơn.",
            });
        }
    });
}

export const passwordCredentialsSchema = z.object({
    email: z
        .string()
        .trim()
        .email("Vui lòng nhập địa chỉ email hợp lệ.")
        .max(255, "Địa chỉ email quá dài."),
    password: passwordSchema(1),
});

export const passwordRegistrationSchema = passwordCredentialsSchema
    .extend({
        password: passwordSchema(12),
        display_name: z
            .string()
            .trim()
            .min(1, "Vui lòng nhập họ và tên.")
            .max(255, "Họ và tên quá dài."),
        confirmPassword: z.string().min(1, "Vui lòng xác nhận mật khẩu."),
    })
    .refine((credentials) => credentials.password === credentials.confirmPassword, {
        path: ["confirmPassword"],
        message: "Mật khẩu xác nhận không khớp. Vui lòng thử lại.",
    });

export const passwordAuthResponseSchema = z.object({
    authenticated: z.literal(true),
    returnTo: z.string(),
});

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
