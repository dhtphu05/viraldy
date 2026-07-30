import { ArrowRight, CheckCircle2, CircleAlert, Sparkles } from "lucide-react";
import type { ComponentProps } from "react";
import { sparkBlockers } from "@/features/ugc-review/lib/mockUgcAnalysis";
import type { UgcRights } from "@/features/ugc-review/types/ugc";
import { cn } from "@/shared/lib/utils";
import { Button } from "@/shared/ui/button";
import { Input } from "@/shared/ui/input";
import { Label } from "@/shared/ui/label";
import { RightDrawer } from "@/shared/ui/right-drawer";
import { StatusChip } from "@/shared/ui/status-chip";
import { Switch } from "@/shared/ui/switch";

const EMPTY_RIGHTS: UgcRights = {
    organic: false,
    sparkAllowed: false,
    metaAllowed: false,
    websiteAllowed: false,
    rawFootage: false,
    editingAllowed: false,
    creatorConfirmed: false,
};

const rightsChecklist = [
    {
        key: "organic",
        label: "Organic",
        detail: "Organic publishing permission is recorded.",
        targetId: "rights-organic",
        isComplete: (rights: UgcRights) => rights.organic,
    },
    {
        key: "spark-authorization",
        label: "Spark allowed",
        detail: "Creator has authorized paid use through Spark Ads.",
        targetId: "rights-spark-allowed",
        isComplete: (rights: UgcRights) => rights.sparkAllowed,
    },
    {
        key: "meta",
        label: "Meta allowed",
        detail: "Permission for Meta paid distribution is recorded.",
        targetId: "rights-meta",
        isComplete: (rights: UgcRights) => rights.metaAllowed,
    },
    {
        key: "website",
        label: "Website allowed",
        detail: "Permission for owned website use is recorded.",
        targetId: "rights-website",
        isComplete: (rights: UgcRights) => rights.websiteAllowed,
    },
    {
        key: "raw-footage",
        label: "Raw footage",
        detail: "Raw footage is included in the creator handoff.",
        targetId: "rights-raw-footage",
        isComplete: (rights: UgcRights) => rights.rawFootage,
    },
    {
        key: "editing-permission",
        label: "Editing allowed",
        detail: "The team may create paid variants from this asset.",
        targetId: "rights-editing-allowed",
        isComplete: (rights: UgcRights) => rights.editingAllowed,
    },
    {
        key: "creator-confirmed",
        label: "Creator confirmed",
        detail: "The creator has confirmed the recorded usage permissions.",
        targetId: "rights-creator-confirmed",
        isComplete: (rights: UgcRights) => rights.creatorConfirmed,
    },
    {
        key: "spark-expiry",
        label: "Expiry",
        detail: "The authorization expiry date is available to the media buyer.",
        targetId: "rights-spark-expiry",
        isComplete: (rights: UgcRights) => Boolean(rights.sparkExpiry),
    },
] as const;

export function RightsReadinessDrawer({
    open,
    onOpenChange,
    rights = EMPTY_RIGHTS,
    onUpdate,
    onMarkReady,
    onCloseAutoFocus,
}: {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    rights?: UgcRights;
    onUpdate: (patch: Partial<UgcRights>) => void;
    onMarkReady: () => boolean;
    onCloseAutoFocus?: ComponentProps<typeof RightDrawer>["onCloseAutoFocus"];
}) {
    const blockers = sparkBlockers(rights);
    const completed = rightsChecklist.filter((item) => item.isComplete(rights)).length;
    const completion = Math.round((completed / rightsChecklist.length) * 100);
    const coverageComplete = completed === rightsChecklist.length;
    const statusId = "rights-readiness-status";
    const status =
        blockers.length === 0
            ? "READY FOR SPARK"
            : rights.organic && !rights.sparkAllowed
              ? "ORGANIC ONLY"
              : `${blockers.length} PAID-USE BLOCKER${blockers.length === 1 ? "" : "S"}`;

    const focusRequirement = (targetId: string) => {
        document.getElementById(targetId)?.focus();
    };

    const markReady = () => {
        if (onMarkReady()) onOpenChange(false);
    };

    return (
        <RightDrawer
            open={open}
            onOpenChange={onOpenChange}
            title="Rights readiness"
            description="Record usage methods and resolve paid launch blockers."
            size="md"
            onCloseAutoFocus={onCloseAutoFocus}
            footer={
                <div className="flex flex-col items-stretch gap-3 sm:flex-row sm:items-center sm:justify-between">
                    <Button variant="ghost" onClick={() => onOpenChange(false)}>
                        Done for now
                    </Button>
                    <div className="sm:ml-auto sm:text-right">
                        <Button
                            onClick={markReady}
                            disabled={blockers.length > 0}
                            aria-describedby={statusId}
                            className="w-full sm:w-auto"
                        >
                            <Sparkles className="h-4 w-4" />
                            Mark Spark-ready
                        </Button>
                        <p
                            id={statusId}
                            role="status"
                            aria-live="polite"
                            className={cn(
                                "mt-1 text-[11px]",
                                blockers.length > 0 ? "text-warn" : "text-ok",
                            )}
                        >
                            {blockers.length > 0
                                ? `${blockers.length} blocker${blockers.length === 1 ? "" : "s"} remaining`
                                : "All Spark requirements complete"}
                        </p>
                    </div>
                </div>
            }
        >
            <div className="space-y-7">
                <section
                    aria-labelledby="rights-primary-status"
                    className="border-b border-hairline pb-5"
                >
                    <p className="text-[11px] font-semibold uppercase text-text-tertiary">
                        Current status
                    </p>
                    <h3
                        id="rights-primary-status"
                        className={cn(
                            "mt-1 text-xl font-semibold",
                            blockers.length === 0
                                ? "text-ok"
                                : rights.organic
                                  ? "text-info"
                                  : "text-warn",
                        )}
                    >
                        {status}
                    </h3>
                    <p className="mt-1 text-sm text-text-secondary">
                        {blockers.length === 0
                            ? "All existing paid-use requirements are complete."
                            : `${completed} of ${rightsChecklist.length} rights checks are recorded.`}
                    </p>
                    {blockers.length > 0 && (
                        <ul className="mt-3 space-y-1 text-xs text-text-secondary">
                            {blockers.map((blocker) => (
                                <li key={blocker} className="flex items-start gap-2">
                                    <CircleAlert
                                        className="mt-0.5 h-3.5 w-3.5 shrink-0 text-warn"
                                        aria-hidden
                                    />
                                    {blocker}
                                </li>
                            ))}
                        </ul>
                    )}
                </section>

                <section aria-labelledby="rights-progress-title">
                    <div className="flex items-start justify-between gap-3">
                        <div>
                            <h3
                                id="rights-progress-title"
                                className="text-sm font-semibold text-text-primary"
                            >
                                Rights coverage
                            </h3>
                            <p className="mt-0.5 text-xs text-text-tertiary">
                                Select an item to jump to its permission field.
                            </p>
                        </div>
                        <StatusChip tone={coverageComplete ? "ok" : "warn"}>
                            {completed}/{rightsChecklist.length} complete
                        </StatusChip>
                    </div>
                    <div
                        className="mt-3 h-1.5 overflow-hidden rounded-full bg-surface-soft"
                        role="progressbar"
                        aria-label="Rights checklist completion"
                        aria-valuemin={0}
                        aria-valuemax={100}
                        aria-valuenow={completion}
                    >
                        <div
                            className={cn(
                                "h-full origin-left rounded-full transition-[width,background-color] duration-200",
                                coverageComplete ? "bg-ok" : "bg-warn",
                            )}
                            style={{ width: `${completion}%` }}
                        />
                    </div>

                    <div className="mt-4 space-y-1.5">
                        {rightsChecklist.map((item) => {
                            const complete = item.isComplete(rights);
                            return (
                                <button
                                    key={item.key}
                                    type="button"
                                    onClick={() => focusRequirement(item.targetId)}
                                    className={cn(
                                        "group flex w-full items-start gap-3 rounded-md px-3 py-2.5 text-left transition-colors duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                                        complete
                                            ? "bg-ok-soft/55 hover:bg-ok-soft"
                                            : "bg-warn-soft/55 hover:bg-warn-soft",
                                    )}
                                    aria-label={`${item.label}: ${complete ? "complete" : "missing"}. Go to field.`}
                                >
                                    {complete ? (
                                        <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-ok" />
                                    ) : (
                                        <CircleAlert className="mt-0.5 h-4 w-4 shrink-0 text-warn" />
                                    )}
                                    <span className="min-w-0 flex-1">
                                        <span className="block text-sm font-medium text-text-primary">
                                            {item.label}
                                        </span>
                                        <span className="mt-0.5 block text-xs text-text-secondary">
                                            {item.detail}
                                        </span>
                                    </span>
                                    <ArrowRight className="mt-1 h-3.5 w-3.5 shrink-0 text-text-tertiary transition-transform duration-200 group-hover:translate-x-0.5" />
                                </button>
                            );
                        })}
                    </div>
                </section>

                <section aria-labelledby="spark-fields-title">
                    <h3 id="spark-fields-title" className="text-sm font-semibold text-text-primary">
                        Required for Spark
                    </h3>
                    <div className="mt-3 space-y-4">
                        <ToggleField
                            id="rights-spark-allowed"
                            label="Spark Ads allowed"
                            description="Paid authorization is documented for this creator asset."
                            value={rights.sparkAllowed}
                            onChange={(sparkAllowed) => onUpdate({ sparkAllowed })}
                        />
                        <ToggleField
                            id="rights-editing-allowed"
                            label="Editing allowed"
                            description="Variants, crops, captions, and cutdowns are permitted."
                            value={rights.editingAllowed}
                            onChange={(editingAllowed) => onUpdate({ editingAllowed })}
                        />
                        <Field
                            id="rights-spark-code"
                            label="Spark authorization code"
                            value={rights.sparkCode ?? ""}
                            placeholder="Enter creator authorization code"
                            invalid={!rights.sparkCode}
                            onChange={(value) => onUpdate({ sparkCode: value || undefined })}
                        />
                        <Field
                            id="rights-spark-expiry"
                            label="Spark code expiry"
                            type="date"
                            value={rights.sparkExpiry?.slice(0, 10) ?? ""}
                            invalid={!rights.sparkExpiry}
                            onChange={(value) => onUpdate({ sparkExpiry: value || undefined })}
                        />
                        <Field
                            id="rights-duration-days"
                            label="Paid usage duration"
                            type="number"
                            min={1}
                            suffix="days"
                            value={rights.durationDays ? String(rights.durationDays) : ""}
                            invalid={!rights.durationDays}
                            onChange={(value) =>
                                onUpdate({
                                    durationDays: value
                                        ? Math.max(1, Math.round(Number(value)))
                                        : undefined,
                                })
                            }
                        />
                    </div>
                </section>

                <section aria-labelledby="optional-rights-title">
                    <h3
                        id="optional-rights-title"
                        className="text-sm font-semibold text-text-primary"
                    >
                        Additional usage
                    </h3>
                    <p className="mt-0.5 text-xs text-text-tertiary">
                        Record supporting permissions for distribution and handoff.
                    </p>
                    <div className="mt-3 divide-y divide-hairline rounded-md border border-hairline px-3">
                        <ToggleField
                            id="rights-organic"
                            label="Organic usage allowed"
                            value={rights.organic}
                            onChange={(organic) => onUpdate({ organic })}
                            compact
                        />
                        <ToggleField
                            id="rights-meta"
                            label="Meta Ads allowed"
                            value={rights.metaAllowed}
                            onChange={(metaAllowed) => onUpdate({ metaAllowed })}
                            compact
                        />
                        <ToggleField
                            id="rights-website"
                            label="Website use allowed"
                            value={rights.websiteAllowed}
                            onChange={(websiteAllowed) => onUpdate({ websiteAllowed })}
                            compact
                        />
                        <ToggleField
                            id="rights-raw-footage"
                            label="Raw footage included"
                            value={rights.rawFootage}
                            onChange={(rawFootage) => onUpdate({ rawFootage })}
                            compact
                        />
                        <ToggleField
                            id="rights-creator-confirmed"
                            label="Creator has confirmed"
                            value={rights.creatorConfirmed}
                            onChange={(creatorConfirmed) => onUpdate({ creatorConfirmed })}
                            compact
                        />
                    </div>
                </section>
            </div>
        </RightDrawer>
    );
}

function ToggleField({
    id,
    label,
    description,
    value,
    onChange,
    compact = false,
}: {
    id: string;
    label: string;
    description?: string;
    value: boolean;
    onChange: (value: boolean) => void;
    compact?: boolean;
}) {
    const descriptionId = description ? `${id}-description` : undefined;

    return (
        <div
            className={cn(
                "flex items-start justify-between gap-4",
                compact ? "py-3" : "rounded-md border border-hairline px-3 py-3",
            )}
        >
            <div className="min-w-0">
                <Label htmlFor={id} className="text-sm font-medium text-text-primary">
                    {label}
                </Label>
                {description && (
                    <p id={descriptionId} className="mt-0.5 text-xs text-text-tertiary">
                        {description}
                    </p>
                )}
            </div>
            <Switch
                id={id}
                checked={value}
                onCheckedChange={onChange}
                aria-describedby={descriptionId}
            />
        </div>
    );
}

function Field({
    id,
    label,
    value,
    onChange,
    type = "text",
    placeholder,
    min,
    suffix,
    invalid,
}: {
    id: string;
    label: string;
    value: string;
    onChange: (value: string) => void;
    type?: "text" | "number" | "date";
    placeholder?: string;
    min?: number;
    suffix?: string;
    invalid?: boolean;
}) {
    const hintId = `${id}-hint`;

    return (
        <div>
            <Label htmlFor={id}>{label}</Label>
            <div className="relative mt-1.5">
                <Input
                    id={id}
                    type={type}
                    min={min}
                    value={value}
                    placeholder={placeholder}
                    onChange={(event) => onChange(event.target.value)}
                    aria-invalid={invalid}
                    aria-describedby={hintId}
                    className={cn(suffix && "pr-14")}
                />
                {suffix && (
                    <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-xs text-text-tertiary">
                        {suffix}
                    </span>
                )}
            </div>
            <p id={hintId} className={cn("mt-1 text-xs", invalid ? "text-warn" : "text-ok")}>
                {invalid ? "Required before marking Spark-ready." : "Requirement complete."}
            </p>
        </div>
    );
}
