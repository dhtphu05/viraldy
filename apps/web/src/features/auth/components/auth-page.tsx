import { Link } from "@tanstack/react-router";
import { Check, LoaderCircle, LockKeyhole, ShieldCheck } from "lucide-react";
import { useId, useRef, useState, type FormEvent } from "react";

import { BrandLogo } from "@/shared/ui/brand-logo";
import { Button } from "@/shared/ui/button";
import { Input } from "@/shared/ui/input";
import { Label } from "@/shared/ui/label";
import type { AuthSnapshot } from "../auth-session";
import { authPagePresentation, passwordAuthErrorMessage } from "../lib/auth-presentation";
import {
    MAX_PASSWORD_CHARACTERS,
    passwordAuthResponseSchema,
    passwordCredentialsSchema,
    passwordRegistrationSchema,
} from "../lib/auth-contract";
import { sanitizeReturnTo, type AuthIntent } from "../lib/auth-flow";

type AuthPageProps = {
    auth: AuthSnapshot;
    intent: AuthIntent;
    returnTo?: string;
    error?: string;
    reason?: string;
    loggedOut?: string | number;
};

const errorMessages: Record<string, string> = {
    auth_unavailable: "Tạm thời không thể đăng nhập. Vui lòng thử lại sau ít phút.",
    callback_failed:
        "Không thể hoàn tất đăng nhập. Vui lòng bắt đầu lại quá trình đăng nhập an toàn.",
    invalid_credentials: "Email hoặc mật khẩu không chính xác. Vui lòng thử lại.",
    signup_failed: "Không thể tạo tài khoản. Vui lòng kiểm tra thông tin và thử lại.",
};

export function AuthPage({ auth, intent, returnTo, error, reason, loggedOut }: AuthPageProps) {
    const isSignup = intent === "signup";
    const isLocalTest = auth.mode === "local_test";
    const isPassword = auth.mode === "password";
    const safeReturnTo = sanitizeReturnTo(returnTo);
    const action = new URLSearchParams({ intent, returnTo: safeReturnTo });
    const unavailable = !auth.enabled || auth.mode === "unavailable";
    const presentation = authPagePresentation(auth.mode, intent);
    const notice =
        (error &&
            (errorMessages[error] ??
                "Không thể hoàn tất yêu cầu. Vui lòng bắt đầu lại quá trình đăng nhập.")) ||
        (reason === "session_expired"
            ? "Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại để tiếp tục."
            : reason === "auth_unavailable" || unavailable
              ? errorMessages.auth_unavailable
              : String(loggedOut) === "1"
                ? "Bạn đã đăng xuất."
                : null);
    const noticeIsAlert =
        Boolean(error) ||
        reason === "session_expired" ||
        reason === "auth_unavailable" ||
        unavailable;
    const hero = isLocalTest
        ? {
              eyebrow: "Không gian làm việc thử nghiệm",
              title: "Mọi thứ đã sẵn sàng để bạn khám phá Viraldy.",
              description:
                  "Tài khoản và không gian làm việc thử nghiệm được tạo sẵn giúp bạn trải nghiệm toàn bộ sản phẩm mà không cần cấu hình nhà cung cấp bên ngoài.",
              benefits: [
                  "Đăng nhập chỉ với một lần nhấn, không cần nhớ mật khẩu",
                  "Hồ sơ có sẵn email, họ tên và số điện thoại",
                  "Có sẵn quyền chủ sở hữu trong không gian làm việc thử nghiệm",
              ],
              footer: "Chỉ dùng trong môi trường phát triển. Tắt local_test khi triển khai chính thức.",
          }
        : isPassword
          ? {
                eyebrow: "Sáng tạo thông minh, bảo mật cho bạn",
                title: "Ý tưởng sáng tạo tiếp theo của bạn bắt đầu từ đây.",
                description:
                    "Đăng nhập bằng email và mật khẩu để truy cập không gian làm việc cùng các công cụ sáng tạo.",
                benefits: [
                    "Mật khẩu được bảo vệ bằng hàm băm an toàn",
                    "Quyền truy cập được quản lý theo vai trò và tư cách thành viên",
                    "Phiên đăng nhập riêng tư được lưu trong cookie HttpOnly",
                ],
                footer: "Viraldy bảo vệ tài khoản và không gian làm việc của bạn.",
            }
          : {
                eyebrow: "Sáng tạo thông minh, bảo mật cho bạn",
                title: "Đưa ra mọi quyết định sáng tạo từ một không gian làm việc đáng tin cậy.",
                description:
                    "Nhà cung cấp danh tính xác minh email và chia sẻ hồ sơ của bạn. Viraldy không lưu mật khẩu của bạn.",
                benefits: [
                    "Đăng nhập an toàn bằng mã ủy quyền và PKCE",
                    "Quyền truy cập được quản lý theo vai trò và tư cách thành viên",
                    "Phiên đăng nhập riêng tư được lưu trong cookie HttpOnly",
                ],
                footer: "Được bảo vệ bởi nhà cung cấp danh tính của tổ chức bạn.",
            };

    return (
        <main
            lang="vi"
            className="grid min-h-screen bg-background lg:grid-cols-[minmax(0,1.05fr)_minmax(440px,0.95fr)]"
        >
            <section className="relative hidden overflow-hidden border-r border-divider bg-surface px-12 py-12 lg:flex lg:flex-col lg:justify-between">
                <div className="pointer-events-none absolute -left-40 top-1/3 h-96 w-96 rounded-full bg-primary/10 blur-3xl" />
                <Brand />
                <div className="relative max-w-xl">
                    <p className="text-xs font-semibold uppercase tracking-[0.18em] text-primary">
                        {hero.eyebrow}
                    </p>
                    <h2 className="mt-4 text-4xl font-semibold leading-tight text-text-primary">
                        {hero.title}
                    </h2>
                    <p className="mt-5 max-w-lg text-base leading-7 text-text-secondary">
                        {hero.description}
                    </p>
                    <ul className="mt-8 grid gap-4 text-sm text-text-secondary">
                        {hero.benefits.map((item) => (
                            <li key={item} className="flex items-center gap-3">
                                <span className="grid h-6 w-6 place-items-center rounded-full bg-primary-soft text-primary-active">
                                    <Check className="h-3.5 w-3.5" aria-hidden />
                                </span>
                                {item}
                            </li>
                        ))}
                    </ul>
                </div>
                <p className="relative text-xs text-text-tertiary">{hero.footer}</p>
            </section>

            <section className="flex min-h-screen items-center justify-center px-5 py-10 sm:px-10">
                <div className="w-full max-w-md">
                    <div className="mb-10 lg:hidden">
                        <Brand />
                    </div>
                    <div className="rounded-2xl border border-hairline bg-surface p-6 shadow-sm sm:p-8">
                        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-primary">
                            {presentation.eyebrow}
                        </p>
                        <div className="mt-4 grid h-11 w-11 place-items-center rounded-xl bg-primary-soft text-primary-active">
                            {isSignup ? (
                                <ShieldCheck className="h-5 w-5" aria-hidden />
                            ) : (
                                <LockKeyhole className="h-5 w-5" aria-hidden />
                            )}
                        </div>
                        <h1 className="mt-6 text-2xl font-semibold text-text-primary">
                            {presentation.title}
                        </h1>
                        <p className="mt-2 text-sm leading-6 text-text-secondary">
                            {presentation.description}
                        </p>

                        {notice && (
                            <div
                                role={noticeIsAlert ? "alert" : "status"}
                                aria-live={noticeIsAlert ? "assertive" : "polite"}
                                className="mt-5 rounded-lg border border-hairline bg-surface-soft px-3 py-2.5 text-sm text-text-secondary"
                            >
                                {notice}
                            </div>
                        )}

                        {presentation.showDevAccount && (
                            <div className="mt-6 rounded-xl border border-hairline bg-surface-soft px-4 py-4">
                                <p className="text-sm font-semibold text-text-primary">
                                    Tài khoản thử nghiệm Viraldy
                                </p>
                                <dl className="mt-3 space-y-2 text-sm text-text-secondary">
                                    <div className="flex items-start justify-between gap-3">
                                        <dt className="text-text-tertiary">Họ và tên</dt>
                                        <dd className="text-right text-text-primary">
                                            Người dùng thử nghiệm Viraldy
                                        </dd>
                                    </div>
                                    <div className="flex items-start justify-between gap-3">
                                        <dt className="text-text-tertiary">Email</dt>
                                        <dd className="min-w-0 break-all text-right text-text-primary">
                                            local@viraldy.example.com
                                        </dd>
                                    </div>
                                    <div className="flex items-start justify-between gap-3">
                                        <dt className="text-text-tertiary">Số điện thoại</dt>
                                        <dd className="text-right text-text-primary">
                                            +84901234567
                                        </dd>
                                    </div>
                                </dl>
                                <p className="mt-3 text-xs leading-5 text-text-tertiary">
                                    Chỉ một lần nhấn, không cần mật khẩu. Chỉ dùng trong môi trường
                                    phát triển.
                                </p>
                            </div>
                        )}

                        {isPassword ? (
                            <PasswordAuthForm
                                key={intent}
                                intent={intent}
                                returnTo={safeReturnTo}
                                disabled={unavailable}
                            />
                        ) : unavailable ? (
                            <button
                                type="button"
                                disabled
                                className="mt-6 inline-flex min-h-11 w-full cursor-not-allowed items-center justify-center rounded-lg bg-surface-muted px-4 text-sm font-semibold text-text-tertiary"
                            >
                                {presentation.ctaLabel}
                            </button>
                        ) : (
                            <a
                                href={`/api/auth/login?${action.toString()}`}
                                className="mt-6 inline-flex min-h-11 w-full items-center justify-center rounded-lg bg-primary px-4 text-sm font-semibold text-primary-foreground transition-colors hover:bg-primary-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                            >
                                {presentation.ctaLabel}
                            </a>
                        )}

                        <div className="mt-5 flex items-start gap-2 rounded-lg bg-surface-soft px-3 py-3 text-xs leading-5 text-text-tertiary">
                            <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
                            <span>
                                {presentation.showDevAccount
                                    ? "Tài khoản này chỉ dùng trong môi trường phát triển. Mã truy cập được lưu trong phiên HttpOnly an toàn."
                                    : isPassword
                                      ? "Mật khẩu được bảo vệ bằng hàm băm an toàn. Phiên đăng nhập được lưu trong cookie HttpOnly riêng tư."
                                      : "Viraldy chỉ nhận hồ sơ đã xác minh và mã truy cập. Mật khẩu của bạn được lưu tại nhà cung cấp danh tính."}
                            </span>
                        </div>

                        <p className="mt-6 text-center text-sm text-text-secondary">
                            {isSignup ? "Bạn đã có tài khoản?" : "Bạn mới sử dụng Viraldy?"}{" "}
                            <Link
                                to={isSignup ? "/login" : "/register"}
                                search={{ returnTo: safeReturnTo }}
                                className="font-semibold text-primary-active underline-offset-4 hover:underline"
                            >
                                {isSignup ? "Đăng nhập" : "Tạo tài khoản"}
                            </Link>
                        </p>
                    </div>
                    <p className="mt-5 text-center text-xs text-text-tertiary">
                        Khi tiếp tục, bạn đồng ý tuân thủ chính sách truy cập của không gian làm
                        việc.
                    </p>
                </div>
            </section>
        </main>
    );
}

function PasswordAuthForm({
    intent,
    returnTo,
    disabled,
}: {
    intent: AuthIntent;
    returnTo: string;
    disabled: boolean;
}) {
    const isSignup = intent === "signup";
    const id = useId();
    const submitting = useRef(false);
    const [pending, setPending] = useState(false);
    const [formError, setFormError] = useState<string | null>(null);
    const [invalidField, setInvalidField] = useState<string | null>(null);
    const endpoint = isSignup ? "/api/auth/register" : "/api/auth/login";

    async function handleSubmit(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        if (disabled || submitting.current) return;
        const form = event.currentTarget;
        const fields = Object.fromEntries(new FormData(form));
        const result = (
            isSignup ? passwordRegistrationSchema : passwordCredentialsSchema
        ).safeParse(fields);
        setFormError(null);
        setInvalidField(null);
        if (!result.success) {
            const issue = result.error.issues[0];
            const fieldName = String(issue.path[0] ?? "");
            setFormError(issue.message);
            setInvalidField(fieldName);
            const field = form.elements.namedItem(fieldName);
            if (field instanceof HTMLElement) field.focus();
            return;
        }

        submitting.current = true;
        setPending(true);
        try {
            const response = await fetch(endpoint, {
                method: "POST",
                credentials: "same-origin",
                headers: { "Content-Type": "application/json", Accept: "application/json" },
                body: JSON.stringify({
                    email: result.data.email,
                    password: result.data.password,
                    ...(isSignup && "display_name" in result.data
                        ? { display_name: result.data.display_name }
                        : {}),
                    returnTo: sanitizeReturnTo(returnTo),
                }),
            });
            if (!response.ok) {
                setFormError(passwordAuthErrorMessage(response.status));
                return;
            }
            const session = passwordAuthResponseSchema.safeParse(
                await response.json().catch(() => null),
            );
            if (!session.success) {
                setFormError(passwordAuthErrorMessage(503));
                return;
            }
            form.reset();
            window.location.assign(sanitizeReturnTo(session.data.returnTo));
        } catch {
            setFormError(passwordAuthErrorMessage(0));
        } finally {
            submitting.current = false;
            setPending(false);
        }
    }

    return (
        <form
            method="post"
            action={endpoint}
            onSubmit={handleSubmit}
            noValidate
            aria-busy={pending}
            className="mt-6"
        >
            <input type="hidden" name="returnTo" value={sanitizeReturnTo(returnTo)} />
            <fieldset disabled={disabled || pending} className="space-y-4">
                {isSignup && (
                    <div className="space-y-2">
                        <Label htmlFor={`${id}-name`}>Họ và tên</Label>
                        <Input
                            id={`${id}-name`}
                            name="display_name"
                            autoComplete="name"
                            maxLength={255}
                            required
                            aria-invalid={invalidField === "display_name"}
                            aria-describedby={
                                invalidField === "display_name" ? `${id}-error` : undefined
                            }
                        />
                    </div>
                )}
                <div className="space-y-2">
                    <Label htmlFor={`${id}-email`}>Email</Label>
                    <Input
                        id={`${id}-email`}
                        name="email"
                        type="email"
                        autoComplete="username"
                        maxLength={255}
                        required
                        autoCapitalize="none"
                        spellCheck={false}
                        aria-invalid={invalidField === "email"}
                        aria-describedby={invalidField === "email" ? `${id}-error` : undefined}
                    />
                </div>
                <div className="space-y-2">
                    <Label htmlFor={`${id}-password`}>Mật khẩu</Label>
                    <Input
                        id={`${id}-password`}
                        name="password"
                        type="password"
                        autoComplete={isSignup ? "new-password" : "current-password"}
                        maxLength={MAX_PASSWORD_CHARACTERS * 2}
                        required
                        aria-invalid={invalidField === "password"}
                        aria-describedby={
                            invalidField === "password"
                                ? `${id}-error`
                                : isSignup
                                  ? `${id}-password-hint`
                                  : undefined
                        }
                    />
                    {isSignup && (
                        <p
                            id={`${id}-password-hint`}
                            className="text-xs leading-5 text-text-tertiary"
                        >
                            Chọn mật khẩu hoặc cụm mật khẩu riêng biệt có ít nhất 12 ký tự.
                        </p>
                    )}
                </div>
                {isSignup && (
                    <div className="space-y-2">
                        <Label htmlFor={`${id}-confirm`}>Xác nhận mật khẩu</Label>
                        <Input
                            id={`${id}-confirm`}
                            name="confirmPassword"
                            type="password"
                            autoComplete="new-password"
                            maxLength={MAX_PASSWORD_CHARACTERS * 2}
                            required
                            aria-invalid={invalidField === "confirmPassword"}
                            aria-describedby={
                                invalidField === "confirmPassword" ? `${id}-error` : undefined
                            }
                        />
                    </div>
                )}
                {formError && (
                    <p
                        id={`${id}-error`}
                        role="alert"
                        className="text-sm leading-6 text-destructive"
                    >
                        {formError}
                    </p>
                )}
                <Button type="submit" size="lg" className="w-full" disabled={disabled || pending}>
                    {pending && (
                        <LoaderCircle
                            className="h-4 w-4 animate-spin motion-reduce:animate-none"
                            aria-hidden
                        />
                    )}
                    {pending
                        ? isSignup
                            ? "Đang tạo tài khoản…"
                            : "Đang đăng nhập…"
                        : isSignup
                          ? "Tạo tài khoản"
                          : "Đăng nhập"}
                </Button>
            </fieldset>
        </form>
    );
}

function Brand() {
    return (
        <Link
            to="/"
            className="relative inline-flex w-fit items-center gap-3"
            aria-label="Trang chủ Viraldy"
        >
            <BrandLogo className="h-11 w-[164px]" />
            <span>
                <span className="block text-xs text-text-tertiary">Sáng tạo thông minh</span>
            </span>
        </Link>
    );
}
