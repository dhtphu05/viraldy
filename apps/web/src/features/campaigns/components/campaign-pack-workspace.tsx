import type { ReactNode } from "react";
import { EvidencePanel } from "@/features/campaigns/components/evidence-panel";
import { StepNav } from "@/features/campaigns/components/step-nav";
import type { CampaignPack, StepId } from "@/features/campaigns/types/campaign";

export function CampaignPackWorkspace({
    pack,
    step,
    onStep,
    children,
}: {
    pack: CampaignPack;
    step: StepId;
    onStep: (step: StepId) => void;
    children: ReactNode;
}) {
    return (
        <div className="flex flex-col gap-4">
            <div className="grid gap-4 xl:grid-cols-[220px_minmax(0,1fr)] xl:gap-5">
                <aside className="min-w-0 xl:sticky xl:top-4 xl:self-start">
                    <div className="min-w-0 max-w-full xl:hidden">
                        <StepNav pack={pack} current={step} onSelect={onStep} compact />
                    </div>
                    <div className="hidden xl:block">
                        <StepNav pack={pack} current={step} onSelect={onStep} />
                    </div>
                </aside>

                <section className="min-w-0 rounded-md bg-surface px-4 py-5 sm:px-6 sm:py-6">
                    {children}
                </section>

                <aside className="min-w-0 xl:col-start-2">
                    <EvidencePanel pack={pack} layout="summary" />
                </aside>
            </div>
        </div>
    );
}
