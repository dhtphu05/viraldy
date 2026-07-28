import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/shared/ui/sheet";
import { campaignTemplates } from "@/features/campaigns/mocks/campaignTemplates";
import { StatusChip } from "@/shared/ui/status-chip";
import { useNavigate } from "@tanstack/react-router";
import { useAppStore } from "@/app/store/app-store";
import { ChevronRight } from "lucide-react";

export function CampaignTemplatesSheet({
    open,
    onOpenChange,
}: {
    open: boolean;
    onOpenChange: (v: boolean) => void;
}) {
    const navigate = useNavigate();
    const setDraft = useAppStore((s) => s.setDraft);

    function pick(templateId: string) {
        const t = campaignTemplates.find((x) => x.id === templateId);
        if (!t) return;
        setDraft({
            templateId,
            objective: t.objective,
            platform: t.platform,
            creatorType: t.creatorType,
            creatorTone: t.creatorTone,
            language: "English",
            market: "US",
        });
        onOpenChange(false);
        navigate({ to: "/campaigns/new" });
    }

    return (
        <Sheet open={open} onOpenChange={onOpenChange}>
            <SheetContent side="right" className="w-full sm:max-w-xl">
                <SheetHeader>
                    <SheetTitle>Campaign templates</SheetTitle>
                    <SheetDescription>
                        Prefill the campaign setup with a starting objective, platform, and creator
                        tone.
                    </SheetDescription>
                </SheetHeader>
                <div className="mt-6 flex flex-col gap-3 overflow-y-auto pb-6">
                    {campaignTemplates.map((t) => (
                        <button
                            key={t.id}
                            type="button"
                            onClick={() => pick(t.id)}
                            className="group grid grid-cols-[minmax(0,1fr)_auto] items-center gap-3 rounded-lg border border-hairline/70 bg-surface p-4 text-left transition-colors hover:border-primary/40 hover:bg-primary-soft/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                        >
                            <div className="min-w-0">
                                <div className="flex flex-wrap items-center gap-2">
                                    <p className="truncate text-sm font-semibold text-text-primary">
                                        {t.name}
                                    </p>
                                    <StatusChip tone="info">{t.objective}</StatusChip>
                                </div>
                                <p className="mt-1 text-xs text-text-secondary">{t.description}</p>
                                <p className="mt-1 text-[11px] text-text-tertiary">
                                    {t.platform} · {t.creatorType} · {t.creatorTone} ·{" "}
                                    {t.suggestedDurationSec}s {t.suggestedAspectRatio}
                                </p>
                            </div>
                            <ChevronRight className="h-4 w-4 text-text-tertiary transition-transform group-hover:translate-x-0.5" />
                        </button>
                    ))}
                </div>
            </SheetContent>
        </Sheet>
    );
}
