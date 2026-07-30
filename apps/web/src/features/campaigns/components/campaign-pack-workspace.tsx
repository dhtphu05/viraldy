import type { ReactNode } from "react";
import { CampaignActionTray } from "@/features/campaigns/components/campaign-action-tray";
import { EvidencePanel } from "@/features/campaigns/components/evidence-panel";
import { StepNav } from "@/features/campaigns/components/step-nav";
import type { CampaignPack, StepId } from "@/features/campaigns/types/campaign";

export function CampaignPackWorkspace({
    pack,
    step,
    onStep,
    onPreview,
    children,
}: {
    pack: CampaignPack;
    step: StepId;
    onStep: (step: StepId) => void;
    onPreview: () => void;
    children: ReactNode;
}) {
    return (
        <div className="flex flex-col gap-4">
            <div className="grid gap-4 xl:grid-cols-[190px_minmax(0,1fr)_300px] xl:gap-6">
                <aside className="min-w-0 xl:sticky xl:top-20 xl:self-start">
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

                <aside className="hidden xl:sticky xl:top-20 xl:block xl:self-start">
                    <EvidencePanel pack={pack} />
                </aside>

                <aside className="min-w-0 xl:hidden">
                    <EvidencePanel pack={pack} />
                </aside>
            </div>

            <CampaignActionTray pack={pack} step={step} onStep={onStep} onPreview={onPreview} />
        </div>
    );
}
