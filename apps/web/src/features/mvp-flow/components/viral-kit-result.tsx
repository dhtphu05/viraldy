import type { KeyboardEvent } from "react";
import { FlaskConical, ShieldAlert, Target } from "lucide-react";

import type { ViralConcept, ViralKitDetail } from "@/features/mvp-flow/intelligence-types";
import { humanizeLabel, humanizeSystemText } from "@/shared/lib/display";
import { cn } from "@/shared/lib/utils";
import { StatusChip } from "@/shared/ui/status-chip";

export function ViralKitResult({
    detail,
    selectedId,
    confirmedId,
    onSelect,
}: {
    detail: ViralKitDetail;
    selectedId?: string;
    confirmedId?: string;
    onSelect: (conceptId: string) => void;
}) {
    const viralKit = detail.latest_version.viral_kit;
    const productName = viralKit.product.snapshot_json.identity?.name ?? "Selected product";

    function handleKeyDown(event: KeyboardEvent<HTMLButtonElement>, index: number) {
        const previous = event.key === "ArrowLeft" || event.key === "ArrowUp";
        const next = event.key === "ArrowRight" || event.key === "ArrowDown";
        if (!previous && !next && event.key !== "Home" && event.key !== "End") return;

        event.preventDefault();
        const nextIndex =
            event.key === "Home"
                ? 0
                : event.key === "End"
                  ? viralKit.concepts.length - 1
                  : previous
                    ? (index - 1 + viralKit.concepts.length) % viralKit.concepts.length
                    : (index + 1) % viralKit.concepts.length;
        onSelect(viralKit.concepts[nextIndex].id);
        event.currentTarget.parentElement
            ?.querySelectorAll<HTMLButtonElement>('[role="radio"]')
            [nextIndex]?.focus();
    }

    return (
        <div className="flex flex-col gap-5">
            <div className="rounded-md bg-primary-soft/45 p-4 sm:p-5">
                <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                        <p className="text-xs font-semibold uppercase text-primary">
                            {humanizeLabel(viralKit.objective)}
                        </p>
                        <h3 className="mt-1 text-lg font-semibold text-text-primary">
                            {productName}
                        </h3>
                        <p className="mt-1 text-sm text-text-secondary">
                            Three product-specific hypotheses for {humanizeLabel(viralKit.platform)}{" "}
                            in {viralKit.target_market}.
                        </p>
                    </div>
                    <StatusChip tone="info">
                        {humanizeLabel(viralKit.overall_confidence)} confidence
                    </StatusChip>
                </div>
            </div>

            <div
                className="grid gap-3 xl:grid-cols-3"
                role="radiogroup"
                aria-label="Product-specific concepts"
            >
                {viralKit.concepts.map((concept, index) => (
                    <ConceptCard
                        key={concept.id}
                        concept={concept}
                        selected={concept.id === selectedId}
                        confirmed={concept.id === confirmedId}
                        tabbable={concept.id === selectedId || (!selectedId && index === 0)}
                        onSelect={() => onSelect(concept.id)}
                        onKeyDown={(event) => handleKeyDown(event, index)}
                    />
                ))}
            </div>

            <section className="rounded-md border border-hairline bg-surface-soft p-4">
                <div className="flex items-center gap-2">
                    <FlaskConical className="h-4 w-4 text-primary" />
                    <h4 className="text-sm font-semibold text-text-primary">Test matrix</h4>
                </div>
                <p className="mt-2 text-sm text-text-secondary">
                    {humanizeSystemText(viralKit.test_matrix.primary_hypothesis)}
                </p>
                <div className="mt-4 overflow-x-auto">
                    <table className="w-full min-w-[680px] border-collapse text-left text-sm">
                        <thead>
                            <tr className="border-b border-divider text-xs text-text-tertiary">
                                <th className="pb-2 pr-4 font-medium">Concept</th>
                                <th className="pb-2 pr-4 font-medium">What changes</th>
                                <th className="pb-2 pr-4 font-medium">Held constant</th>
                                <th className="pb-2 font-medium">Decision signal</th>
                            </tr>
                        </thead>
                        <tbody>
                            {viralKit.test_matrix.concepts.map((cell) => (
                                <tr key={cell.concept_id} className="border-b border-divider">
                                    <td className="py-3 pr-4 font-medium text-text-primary">
                                        {conceptName(viralKit.concepts, cell.concept_id)}
                                    </td>
                                    <td className="py-3 pr-4 text-text-secondary">
                                        {cell.changed_axes
                                            .map((axis) => humanizeLabel(axis))
                                            .join(", ")}
                                    </td>
                                    <td className="py-3 pr-4 text-text-secondary">
                                        {cell.held_constant
                                            .map((item) => humanizeSystemText(item))
                                            .join(", ") || "Product and offer"}
                                    </td>
                                    <td className="py-3 text-text-secondary">
                                        {humanizeSystemText(
                                            cell.metrics_to_observe.join(", ") || cell.hypothesis,
                                        )}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </section>

            {(viralKit.risks.length > 0 || viralKit.uncertainties.length > 0) && (
                <section className="rounded-md border border-hairline bg-warn-soft p-4">
                    <div className="flex items-center gap-2">
                        <ShieldAlert className="h-4 w-4 text-warn" />
                        <h4 className="text-sm font-semibold text-text-primary">Risk summary</h4>
                    </div>
                    <ul className="mt-3 space-y-2 text-sm text-text-secondary">
                        {viralKit.risks.map((risk) => (
                            <li key={risk.code}>
                                <span className="font-medium text-text-primary">
                                    {humanizeLabel(risk.code)}:
                                </span>{" "}
                                {humanizeSystemText(risk.message)}
                            </li>
                        ))}
                        {viralKit.uncertainties.map((uncertainty) => (
                            <li key={uncertainty}>{humanizeSystemText(uncertainty)}</li>
                        ))}
                    </ul>
                </section>
            )}
        </div>
    );
}

function ConceptCard({
    concept,
    selected,
    confirmed,
    tabbable,
    onSelect,
    onKeyDown,
}: {
    concept: ViralConcept;
    selected: boolean;
    confirmed: boolean;
    tabbable: boolean;
    onSelect: () => void;
    onKeyDown: (event: KeyboardEvent<HTMLButtonElement>) => void;
}) {
    return (
        <button
            type="button"
            role="radio"
            aria-checked={selected}
            tabIndex={tabbable ? 0 : -1}
            onClick={onSelect}
            onKeyDown={onKeyDown}
            className={cn(
                "min-w-0 rounded-md border bg-surface p-4 text-left transition-[border-color,background-color,box-shadow] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                selected
                    ? "border-primary bg-primary-soft/35 shadow-sm"
                    : "border-hairline hover:border-primary/50",
            )}
        >
            <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                    <p className="text-xs font-semibold uppercase text-primary">
                        {humanizeLabel(concept.strategic_axis)}
                    </p>
                    <h4 className="mt-1 text-base font-semibold text-text-primary">
                        {concept.name}
                    </h4>
                </div>
                {confirmed ? (
                    <StatusChip tone="ok">Confirmed</StatusChip>
                ) : selected ? (
                    <StatusChip tone="info">Selected</StatusChip>
                ) : null}
            </div>

            <dl className="mt-4 space-y-3 text-sm">
                <ConceptField label="Who it is for" value={concept.buyer_persona_label} />
                <ConceptField
                    label="The opening"
                    value={concept.hook.spoken_text ?? concept.hook.opening_visual}
                />
                <ConceptField label="Why it fits" value={concept.creative_angle} />
                <ConceptField label="Must demonstrate" value={concept.demo_mechanism} />
                <ConceptField label="What counts as proof" value={concept.proof_mechanism} />
                <ConceptField
                    label="What not to say"
                    value={concept.claims_to_avoid.join("; ") || "No additional claim supplied"}
                />
            </dl>

            <div className="mt-4 flex items-start gap-2 border-t border-divider pt-3">
                <Target className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
                <p className="text-xs leading-5 text-text-secondary">
                    {humanizeSystemText(concept.test_hypothesis)}
                </p>
            </div>
        </button>
    );
}

function ConceptField({ label, value }: { label: string; value: string }) {
    return (
        <div>
            <dt className="text-xs font-medium text-text-tertiary">{label}</dt>
            <dd className="mt-0.5 break-words leading-5 text-text-primary">{value}</dd>
        </div>
    );
}

function conceptName(concepts: ViralConcept[], conceptId: string) {
    return concepts.find((concept) => concept.id === conceptId)?.name ?? conceptId;
}
