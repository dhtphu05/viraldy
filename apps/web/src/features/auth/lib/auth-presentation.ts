import type { AuthIntent } from "./auth-flow";

type AuthMode = "local_test" | "oidc" | "password" | "unavailable";

export type AuthPagePresentation = {
    eyebrow: string;
    title: string;
    description: string;
    ctaLabel: string;
    showDevAccount: boolean;
};

export function authPagePresentation(mode: AuthMode, intent: AuthIntent): AuthPagePresentation {
    if (mode === "password") {
        return intent === "signup"
            ? {
                  eyebrow: "Get started",
                  title: "Create your Viraldy account",
                  description: "Create your account to start working with your team.",
                  ctaLabel: "Create account",
                  showDevAccount: false,
              }
            : {
                  eyebrow: "Welcome back",
                  title: "Sign in to Viraldy",
                  description: "Use your email and password to return to your workspace.",
                  ctaLabel: "Sign in",
                  showDevAccount: false,
              };
    }

    if (mode === "unavailable") {
        return intent === "signup"
            ? {
                  eyebrow: "Access unavailable",
                  title: "Account creation is temporarily unavailable",
                  description:
                      "The authentication service is not ready. Please try again in a moment.",
                  ctaLabel: "Account creation unavailable",
                  showDevAccount: false,
              }
            : {
                  eyebrow: "Access unavailable",
                  title: "Sign in is temporarily unavailable",
                  description:
                      "The authentication service is not ready. Please try again in a moment.",
                  ctaLabel: "Sign in unavailable",
                  showDevAccount: false,
              };
    }

    if (mode === "local_test") {
        return intent === "signup"
            ? {
                  eyebrow: "Development setup",
                  title: "Create your dev account",
                  description:
                      "Start with a ready-to-use local profile containing your required email, name, and phone number.",
                  ctaLabel: "Create dev account & continue",
                  showDevAccount: true,
              }
            : {
                  eyebrow: "Development access",
                  title: "Sign in to Viraldy",
                  description:
                      "Use the local development account below to enter your workspace in one click.",
                  ctaLabel: "Sign in with dev account",
                  showDevAccount: true,
              };
    }

    return intent === "signup"
        ? {
              eyebrow: "Get started",
              title: "Create your Viraldy account",
              description: "Create an account with your identity provider to enter your workspace.",
              ctaLabel: "Create account securely",
              showDevAccount: false,
          }
        : {
              eyebrow: "Welcome back",
              title: "Welcome back",
              description:
                  "Continue with your verified identity. We'll return you to the page you requested.",
              ctaLabel: "Continue to secure sign in",
              showDevAccount: false,
          };
}

export function passwordAuthErrorMessage(status: number): string {
    switch (status) {
        case 0:
            return "We couldn't connect. Check your connection and try again.";
        case 400:
        case 422:
            return "Please check your details and try again.";
        case 401:
            return "The email or password is incorrect. Please try again.";
        case 403:
            return "This account can't sign in right now. Please contact your workspace administrator.";
        case 409:
            return "An account with this email already exists. Sign in instead.";
        case 429:
            return "Too many attempts. Please wait a moment and try again.";
        default:
            return "We couldn't complete sign-in right now. Please try again in a moment.";
    }
}
