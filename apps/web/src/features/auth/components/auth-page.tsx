import { Link } from "@tanstack/react-router";
import { Check, LockKeyhole, ShieldCheck } from "lucide-react";

import { BrandLogo } from "@/shared/ui/brand-logo";
import type { AuthSnapshot } from "../auth-session";
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
};

export function AuthPage({ auth, intent, returnTo, error, reason, loggedOut }: AuthPageProps) {
    const isSignup = intent === "signup";
    const safeReturnTo = sanitizeReturnTo(returnTo);
    const action = new URLSearchParams({ intent, returnTo: safeReturnTo });
    const unavailable = !auth.enabled || auth.mode === "unavailable";
    const notice =
        (error && errorMessages[error]) ||
        (reason === "session_expired"
            ? "Your session expired. Sign in again to continue where you left off."
            : String(loggedOut) === "1"
              ? "You're signed out."
              : null);

    return (
        <main className="grid min-h-screen bg-background lg:grid-cols-[minmax(0,1.05fr)_minmax(440px,0.95fr)]">
            <section className="relative hidden overflow-hidden border-r border-divider bg-surface px-12 py-12 lg:flex lg:flex-col lg:justify-between">
                <div className="pointer-events-none absolute -left-40 top-1/3 h-96 w-96 rounded-full bg-primary/10 blur-3xl" />
                <Brand />
                <div className="relative max-w-xl">
                    <p className="text-xs font-semibold uppercase tracking-[0.18em] text-primary">
                        Creative intelligence, securely yours
                    </p>
                    <h1 className="mt-4 text-4xl font-semibold leading-tight text-text-primary">
                        Make every creative decision from one trusted workspace.
                    </h1>
                    <p className="mt-5 max-w-lg text-base leading-7 text-text-secondary">
                        Your identity provider verifies your email, name, and phone number. Viraldy
                        never stores your password.
                    </p>
                    <ul className="mt-8 grid gap-4 text-sm text-text-secondary">
                        {[
                            "Secure Authorization Code + PKCE sign-in",
                            "Workspace access protected by role and membership",
                            "Private session stored in an HttpOnly cookie",
                        ].map((item) => (
                            <li key={item} className="flex items-center gap-3">
                                <span className="grid h-6 w-6 place-items-center rounded-full bg-primary-soft text-primary-active">
                                    <Check className="h-3.5 w-3.5" aria-hidden />
                                </span>
                                {item}
                            </li>
                        ))}
                    </ul>
                </div>
                <p className="relative text-xs text-text-tertiary">
                    Protected by your organization's identity provider.
                </p>
            </section>

            <section className="flex min-h-screen items-center justify-center px-5 py-10 sm:px-10">
                <div className="w-full max-w-md">
                    <div className="mb-10 lg:hidden">
                        <Brand />
                    </div>
                    <div className="rounded-2xl border border-hairline bg-surface p-6 shadow-sm sm:p-8">
                        <div className="grid h-11 w-11 place-items-center rounded-xl bg-primary-soft text-primary-active">
                            {isSignup ? (
                                <ShieldCheck className="h-5 w-5" aria-hidden />
                            ) : (
                                <LockKeyhole className="h-5 w-5" aria-hidden />
                            )}
                        </div>
                        <h2 className="mt-6 text-2xl font-semibold text-text-primary">
                            {isSignup ? "Create your Viraldy account" : "Welcome back"}
                        </h2>
                        <p className="mt-2 text-sm leading-6 text-text-secondary">
                            {isSignup
                                ? "Create a verified identity with email, full name, and phone number to enter your workspace."
                                : "Continue with your verified identity. We'll return you to the page you requested."}
                        </p>

                        {notice && (
                            <div
                                role="status"
                                aria-live="polite"
                                className="mt-5 rounded-lg border border-hairline bg-surface-soft px-3 py-2.5 text-sm text-text-secondary"
                            >
                                {notice}
                            </div>
                        )}

                        <a
                            href={`/api/auth/login?${action.toString()}`}
                            aria-disabled={unavailable}
                            className={`mt-6 inline-flex min-h-11 w-full items-center justify-center rounded-lg px-4 text-sm font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 ${
                                unavailable
                                    ? "pointer-events-none bg-surface-muted text-text-tertiary"
                                    : "bg-primary text-primary-foreground hover:bg-primary-hover"
                            }`}
                        >
                            {auth.mode === "local_test"
                                ? "Continue with local demo account"
                                : isSignup
                                  ? "Create account securely"
                                  : "Continue to secure sign in"}
                        </a>

                        <div className="mt-5 flex items-start gap-2 rounded-lg bg-surface-soft px-3 py-3 text-xs leading-5 text-text-tertiary">
                            <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
                            <span>
                                Viraldy receives only your verified profile and access token. Your
                                password stays with the identity provider.
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
