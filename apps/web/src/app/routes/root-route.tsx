import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
    Outlet,
    Link,
    createRootRouteWithContext,
    useRouter,
    HeadContent,
    Scripts,
} from "@tanstack/react-router";
import { useEffect, type ReactNode } from "react";

import appCss from "../styles.css?url";
import { reportClientError } from "@/shared/lib/error-reporting";
import { Toaster } from "@/shared/ui/sonner";
import { AnalysisJobsRunner } from "@/features/creative-library/components/analysis-jobs-runner";

function NotFoundComponent() {
    return (
        <div className="flex min-h-screen items-center justify-center bg-background px-4">
            <div className="max-w-md text-center">
                <h1 className="text-7xl font-bold text-text-primary">404</h1>
                <h2 className="mt-4 text-xl font-semibold text-text-primary">Page not found</h2>
                <p className="mt-2 text-sm text-text-secondary">
                    The page you're looking for doesn't exist or has been moved.
                </p>
                <div className="mt-6">
                    <Link
                        to="/dashboard"
                        className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary-hover"
                    >
                        Go to dashboard
                    </Link>
                </div>
            </div>
        </div>
    );
}

function ErrorComponent({ error, reset }: { error: Error; reset: () => void }) {
    console.error(error);
    const router = useRouter();
    useEffect(() => {
        reportClientError(error, { boundary: "tanstack_root_error_component" });
    }, [error]);

    return (
        <div className="flex min-h-screen items-center justify-center bg-background px-4">
            <div className="max-w-md text-center">
                <h1 className="text-xl font-semibold text-text-primary">This page didn't load</h1>
                <p className="mt-2 text-sm text-text-secondary">
                    Something went wrong. Try refreshing or head back to the dashboard.
                </p>
                <div className="mt-6 flex flex-wrap justify-center gap-2">
                    <button
                        onClick={() => {
                            router.invalidate();
                            reset();
                        }}
                        className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary-hover"
                    >
                        Try again
                    </button>
                    <a
                        href="/dashboard"
                        className="inline-flex items-center justify-center rounded-md border border-hairline bg-surface px-4 py-2 text-sm font-medium text-text-primary transition-colors hover:bg-surface-soft"
                    >
                        Go to dashboard
                    </a>
                </div>
            </div>
        </div>
    );
}

export const Route = createRootRouteWithContext<{ queryClient: QueryClient }>()({
    head: () => ({
        meta: [
            { charSet: "utf-8" },
            { name: "viewport", content: "width=device-width, initial-scale=1" },
            { title: "Viraldy — Creative Intelligence for TikTok Shop" },
            {
                name: "description",
                content:
                    "Viraldy is a Creative Intelligence and Creative Operations workspace for TikTok Shop US, POD, dropshipping, and cross-border ecommerce sellers.",
            },
            { name: "author", content: "Viraldy" },
            { property: "og:title", content: "Viraldy — Creative Intelligence for TikTok Shop" },
            {
                property: "og:description",
                content:
                    "Organize creative references, analyze Creative DNA, review UGC, and make Scale / Fix / Kill / Rehire decisions.",
            },
            { property: "og:type", content: "website" },
            { name: "twitter:card", content: "summary_large_image" },
        ],
        links: [
            {
                rel: "stylesheet",
                href: "https://rsms.me/inter/inter.css",
            },
            {
                rel: "stylesheet",
                href: appCss,
            },
            { rel: "icon", href: "/favicon.ico", type: "image/x-icon" },
        ],
    }),
    shellComponent: RootShell,
    component: RootComponent,
    notFoundComponent: NotFoundComponent,
    errorComponent: ErrorComponent,
});

function RootShell({ children }: { children: ReactNode }) {
    return (
        <html lang="en">
            <head>
                <HeadContent />
            </head>
            <body>
                {children}
                <Scripts />
            </body>
        </html>
    );
}

function RootComponent() {
    const { queryClient } = Route.useRouteContext();

    return (
        <QueryClientProvider client={queryClient}>
            <AnalysisJobsRunner />
            <Outlet />
            <Toaster />
        </QueryClientProvider>
    );
}
