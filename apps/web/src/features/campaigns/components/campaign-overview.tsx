import { EvidencePanel } from "@/features/campaigns/components/evidence-panel";
import { CampaignReadinessHero } from "@/features/campaigns/components/campaign-readiness-hero";
import { STEPS, stepIsComplete } from "@/features/campaigns/lib/campaignSteps";
import type { ReadinessState } from "@/features/campaigns/lib/campaignSteps";
import type { CampaignPack, StepId } from "@/features/campaigns/types/campaign";

export function CampaignOverview({
    pack,
    readinessState,
    reasons,
    activity,
    onContinue,
    onPreview,
}: {
    pack: CampaignPack;
    readinessState: ReadinessState;
    reasons: string[];
    activity: { id: string; detail: string; at: string }[];
    onContinue: (step: StepId) => void;
    onPreview: () => void;
}) {
    const primaryAngle = pack.angleOptions.find((angle) => angle.id === pack.primaryAngleId);
    const nextIncomplete = STEPS.find((step) => !stepIsComplete(pack, step.id));
    const currentBottleneck = readinessState === "Blocked" ? nextIncomplete : undefined;

    return (
        <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_320px]">
            <div className="flex min-w-0 flex-col gap-6">
                <CampaignReadinessHero
                    pack={pack}
                    state={readinessState}
                    reasons={reasons}
                    onContinue={onContinue}
                    onPreview={onPreview}
                />

                <section aria-labelledby="campaign-summary-heading">
                    <div className="flex flex-wrap items-baseline justify-between gap-2">
                        <h2
                            id="campaign-summary-heading"
                            className="text-base font-semibold text-text-primary"
                        >
                            Campaign summary
                        </h2>
                        <p className="text-xs text-text-tertiary">
                            Updated {new Date(pack.updatedAt).toLocaleString()}
                        </p>
                    </div>
                    <dl className="mt-3 grid grid-cols-2 divide-x divide-y divide-divider border-y border-divider bg-surface sm:grid-cols-4 sm:divide-y-0">
                        <SummaryItem
                            label="Primary angle"
                            value={primaryAngle?.name ?? "Not set"}
                        />
                        <SummaryItem
                            label="Selected hooks"
                            value={String(pack.selectedHookIds.length)}
                        />
                        <SummaryItem
                            label="Deliverables"
                            value={`${pack.deliverables.numberOfVideos} × ${pack.deliverables.targetDurationSec}s`}
                        />
                        <SummaryItem
                            label="Usage rights"
                            value={`${pack.rights.usageDurationDays} days`}
                        />
                    </dl>
                </section>

                <section
                    aria-labelledby="campaign-bottleneck-heading"
                    className="border-l-2 border-primary px-4 py-1"
                >
                    <p
                        id="campaign-bottleneck-heading"
                        className="text-xs font-semibold uppercase text-primary-active"
                    >
                        Current bottleneck
                    </p>
                    <p className="mt-1 text-sm font-medium text-text-primary">
                        {currentBottleneck
                            ? currentBottleneck.label
                            : readinessState === "Needs review"
                              ? "Claim review"
                              : "No blocking work"}
                    </p>
                    <p className="mt-1 text-sm text-text-secondary">
                        {reasons[0]?.replace(/^Missing:\s*/, "") ??
                            "The Campaign Pack is ready for creator preview."}
                    </p>
                </section>

                <section aria-labelledby="campaign-activity-heading">
                    <h2
                        id="campaign-activity-heading"
                        className="text-base font-semibold text-text-primary"
                    >
                        Recent activity
                    </h2>
                    {activity.length === 0 ? (
                        <p className="mt-3 border-y border-divider py-4 text-sm text-text-tertiary">
                            No activity yet.
                        </p>
                    ) : (
                        <ul className="mt-3 divide-y divide-divider border-y border-divider bg-surface">
                            {activity.slice(0, 5).map((event) => (
                                <li
                                    key={event.id}
                                    className="flex items-start justify-between gap-3 px-3 py-3 text-sm"
                                >
                                    <span className="min-w-0 text-text-primary">
                                        {event.detail}
                                    </span>
                                    <span className="shrink-0 tabular text-xs text-text-tertiary">
                                        {new Date(event.at).toLocaleTimeString()}
                                    </span>
                                </li>
                            ))}
                        </ul>
                    )}
                </section>
            </div>

            <aside className="min-w-0 xl:sticky xl:top-20 xl:self-start">
                <EvidencePanel pack={pack} />
            </aside>
        </div>
    );
}

function SummaryItem({ label, value }: { label: string; value: string }) {
    return (
        <div className="min-w-0 p-3 sm:p-4">
            <dt className="text-[11px] font-medium uppercase text-text-tertiary">{label}</dt>
            <dd className="mt-1 break-words text-sm font-medium leading-5 text-text-primary">
                {value}
            </dd>
        </div>
    );
}
