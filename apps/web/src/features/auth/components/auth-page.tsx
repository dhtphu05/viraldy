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
    auth_unavailable: "Sign-in is temporarily unavailable. Please try again in a moment.",
    callback_failed: "We couldn't complete sign-in. Please restart the secure sign-in flow.",
    invalid_credentials: "The email or password is incorrect. Please try again.",
    signup_failed: "We couldn't create your account. Please check your details and try again.",
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
                "We couldn't complete this request. Please restart the sign-in flow.")) ||
        (reason === "session_expired"
            ? "Your session expired. Sign in again to continue where you left off."
            : reason === "auth_unavailable" || unavailable
              ? errorMessages.auth_unavailable
              : String(loggedOut) === "1"
                ? "You're signed out."
                : null);
    const noticeIsAlert =
        Boolean(error) ||
        reason === "session_expired" ||
        reason === "auth_unavailable" ||
        unavailable;
    const hero = isLocalTest
        ? {
              eyebrow: "Local development workspace",
              title: "Everything you need to explore Viraldy, already set up.",
              description:
                  "A reusable development identity and seeded workspace let you test the complete product without configuring an external provider.",
              benefits: [
                  "One-click sign in with no password to remember",
                  "Profile includes email, full name, and phone number",
                  "Seeded owner access to a ready-to-use workspace",
              ],
              footer: "Local-only access. Keep local_test disabled in production.",
          }
        : isPassword
          ? {
                eyebrow: "Creative intelligence, securely yours",
                title: "Your next great creative starts here.",
                description:
                    "Sign in with your email and password to access your workspace and creative tools.",
                benefits: [
                    "Your password is protected with secure hashing",
                    "Workspace access protected by role and membership",
                    "Private session stored in an HttpOnly cookie",
                ],
                footer: "Your account and workspace, protected by Viraldy.",
            }
          : {
                eyebrow: "Creative intelligence, securely yours",
                title: "Make every creative decision from one trusted workspace.",
                description:
                    "Your identity provider verifies your email and shares your profile. Viraldy never stores your password.",
                benefits: [
                    "Secure Authorization Code + PKCE sign-in",
                    "Workspace access protected by role and membership",
                    "Private session stored in an HttpOnly cookie",
                ],
                footer: "Protected by your organization's identity provider.",
            };

    return (
        <main className="grid min-h-screen bg-background lg:grid-cols-[minmax(0,1.05fr)_minmax(440px,0.95fr)]">
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
                                    Viraldy development account
                                </p>
                                <dl className="mt-3 space-y-2 text-sm text-text-secondary">
                                    <div className="flex items-start justify-between gap-3">
                                        <dt className="text-text-tertiary">Name</dt>
                                        <dd className="text-right text-text-primary">
                                            Local Viraldy User
                                        </dd>
                                    </div>
                                    <div className="flex items-start justify-between gap-3">
                                        <dt className="text-text-tertiary">Email</dt>
                                        <dd className="min-w-0 break-all text-right text-text-primary">
                                            local@viraldy.example.com
                                        </dd>
                                    </div>
                                    <div className="flex items-start justify-between gap-3">
                                        <dt className="text-text-tertiary">Phone</dt>
                                        <dd className="text-right text-text-primary">
                                            +84901234567
                                        </dd>
                                    </div>
                                </dl>
                                <p className="mt-3 text-xs leading-5 text-text-tertiary">
                                    One click only. No password. Local environment only.
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
                                    ? "This account is available only in local development. Its access token stays in a secure HttpOnly session."
                                    : isPassword
                                      ? "Your password is protected with secure hashing. Your session stays in a private HttpOnly cookie."
                                      : "Viraldy receives only your verified profile and access token. Your password stays with the identity provider."}
                            </span>
                        </div>

                        <p className="mt-6 text-center text-sm text-text-secondary">
                            {isSignup ? "Already have an account?" : "New to Viraldy?"}{" "}
                            <Link
                                to={isSignup ? "/login" : "/register"}
                                search={{ returnTo: safeReturnTo }}
                                className="font-semibold text-primary-active underline-offset-4 hover:underline"
                            >
                                {isSignup ? "Sign in" : "Create account"}
                            </Link>
                        </p>
                    </div>
                    <p className="mt-5 text-center text-xs text-text-tertiary">
                        By continuing, you agree to follow your workspace's access policies.
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
                        <Label htmlFor={`${id}-name`}>Full name</Label>
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
                    <Label htmlFor={`${id}-password`}>Password</Label>
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
                            Choose a long, unique password or passphrase.
                        </p>
                    )}
                </div>
                {isSignup && (
                    <div className="space-y-2">
                        <Label htmlFor={`${id}-confirm`}>Confirm password</Label>
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
                            ? "Creating your account…"
                            : "Signing in…"
                        : isSignup
                          ? "Create account"
                          : "Sign in"}
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
            aria-label="Viraldy home"
        >
            <BrandLogo className="h-11 w-[164px]" />
            <span>
                <span className="block text-xs text-text-tertiary">Creative Intelligence</span>
            </span>
        </Link>
    );
}
