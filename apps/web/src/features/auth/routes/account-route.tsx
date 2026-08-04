import { createFileRoute } from "@tanstack/react-router";
import { CheckCircle2, KeyRound, Mail, Phone, UserRound } from "lucide-react";

import { AppShell } from "@/widgets/app-shell/app-shell";
import { PageHeader } from "@/shared/ui/page-header";
import { SurfaceCard } from "@/shared/ui/surface-card";
import { Button } from "@/shared/ui/button";
import { profileInitials } from "../lib/auth-contract";

export const Route = createFileRoute("/account")({
    head: () => ({ meta: [{ title: "Account — Viraldy" }] }),
    component: AccountPage,
});

function AccountPage() {
    const { auth } = Route.useRouteContext();
    if (!auth.user) return null;
    const user = auth.user;

    return (
        <AppShell>
            <div className="flex max-w-3xl flex-col gap-6">
                <PageHeader
                    title="Account"
                    description="Your verified identity and Viraldy session."
                />

                <SurfaceCard className="overflow-hidden p-0">
                    <div className="flex flex-col gap-4 border-b border-divider p-5 sm:flex-row sm:items-center">
                        <div className="grid h-14 w-14 shrink-0 place-items-center rounded-2xl bg-primary-soft text-base font-semibold text-primary-active">
                            {profileInitials(user)}
                        </div>
                        <div className="min-w-0">
                            <h2 className="truncate text-lg font-semibold text-text-primary">
                                {user.display_name}
                            </h2>
                            <p className="mt-1 flex items-center gap-1.5 text-sm text-text-secondary">
                                <CheckCircle2 className="h-4 w-4 text-success" aria-hidden />
                                Verified account
                            </p>
                        </div>
                    </div>

                    <dl className="divide-y divide-divider">
                        <IdentityRow icon={UserRound} label="Full name" value={user.display_name} />
                        <IdentityRow icon={Mail} label="Email" value={user.email} />
                        <IdentityRow icon={Phone} label="Phone number" value={user.phone_number} />
                        <IdentityRow
                            icon={KeyRound}
                            label="Sign-in method"
                            value={
                                auth.mode === "local_test" ? "Local development" : "OIDC provider"
                            }
                        />
                    </dl>
                </SurfaceCard>

                <SurfaceCard className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                    <div>
                        <h2 className="text-sm font-semibold text-text-primary">Session</h2>
                        <p className="mt-1 text-sm text-text-secondary">
                            Signing out clears Viraldy's private session cookies on this device.
                        </p>
                    </div>
                    <form action="/api/auth/logout" method="post">
                        <Button type="submit" variant="outline">
                            Sign out
                        </Button>
                    </form>
                </SurfaceCard>
            </div>
        </AppShell>
    );
}

function IdentityRow({
    icon: Icon,
    label,
    value,
}: {
    icon: typeof UserRound;
    label: string;
    value: string;
}) {
    return (
        <div className="grid gap-2 px-5 py-4 sm:grid-cols-[180px_minmax(0,1fr)] sm:items-center">
            <dt className="flex items-center gap-2 text-sm text-text-tertiary">
                <Icon className="h-4 w-4" aria-hidden />
                {label}
            </dt>
            <dd className="break-words text-sm font-medium text-text-primary">{value}</dd>
        </div>
    );
}
