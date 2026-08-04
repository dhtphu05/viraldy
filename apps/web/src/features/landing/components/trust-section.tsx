import { ShieldCheck, Info } from "lucide-react";
import { SectionWrapper } from "./section-wrapper";

export function TrustSection() {
    return (
        <SectionWrapper id="trust" background="default" className="py-20 border-b border-hairline">
            <div className="mx-auto max-w-4xl text-center mb-12">
                <span className="rounded-full bg-primary-soft px-3 py-1.5 text-xs font-semibold text-primary">
                    Useful Intelligence, Not Fake Certainty
                </span>
                <h2 className="mt-4 text-3xl font-bold tracking-tight text-text-primary sm:text-4xl">
                    Know why Viraldy recommended it.
                </h2>
                <p className="mt-4 text-lg text-text-secondary leading-relaxed">
                    Important findings should not be mysterious black-box scores. Viraldy keeps the observation, evidence, expectation and next action connected.
                </p>
            </div>

            {/* Four Visual Blocks */}
            <div className="mx-auto max-w-4xl grid gap-4 sm:grid-cols-2 lg:grid-cols-4 text-xs leading-relaxed mb-8">
                {/* Observed */}
                <div className="p-5 rounded-2xl border border-divider bg-surface shadow-sm">
                    <span className="font-bold text-primary uppercase tracking-wider block mb-2 text-[10px]">1. Observed</span>
                    <p className="text-text-secondary mb-3">What actually appeared in the creator video.</p>
                    <ul className="space-y-1.5 font-mono text-[10px] text-text-primary bg-surface-soft p-2.5 rounded-lg border border-divider">
                        <li>• Product @ 4.2s</li>
                        <li>• CTA @ 18.8s</li>
                        <li>• "Miles" @ 7.2–9.6s</li>
                        <li>• Claim @ 8.9s</li>
                    </ul>
                </div>

                {/* Evidence */}
                <div className="p-5 rounded-2xl border border-divider bg-surface shadow-sm">
                    <span className="font-bold text-info uppercase tracking-wider block mb-2 text-[10px]">2. Evidence</span>
                    <p className="text-text-secondary mb-3">Where the observation came from.</p>
                    <ul className="space-y-1.5 text-text-primary font-semibold">
                        <li>• Frame Analysis</li>
                        <li>• ASR Audio Transcript</li>
                        <li>• OCR On-Screen Text</li>
                        <li>• Product Context Card</li>
                        <li>• Creator Plan Brief</li>
                    </ul>
                </div>

                {/* Expected */}
                <div className="p-5 rounded-2xl border border-divider bg-surface shadow-sm">
                    <span className="font-bold text-warn uppercase tracking-wider block mb-2 text-[10px]">3. Expected</span>
                    <p className="text-text-secondary mb-3">What should have happened according to rules.</p>
                    <ul className="space-y-1.5 text-text-secondary list-disc pl-4">
                        <li>Product reveal &le; 2.0s</li>
                        <li>Personalization = Milo</li>
                        <li>Same-item proof shown</li>
                        <li>Disclosure present</li>
                    </ul>
                </div>

                {/* Action */}
                <div className="p-5 rounded-2xl border border-divider bg-surface shadow-sm">
                    <span className="font-bold text-ok uppercase tracking-wider block mb-2 text-[10px]">4. Action</span>
                    <p className="text-text-secondary mb-3">What should happen next to fix the video.</p>
                    <div className="flex flex-wrap gap-1">
                        <span className="px-2 py-0.5 rounded bg-surface-muted text-text-primary font-bold text-[9px] uppercase">Keep</span>
                        <span className="px-2 py-0.5 rounded bg-surface-muted text-text-primary font-bold text-[9px] uppercase">Edit</span>
                        <span className="px-2 py-0.5 rounded bg-surface-muted text-text-primary font-bold text-[9px] uppercase">Reshoot</span>
                        <span className="px-2 py-0.5 rounded bg-surface-muted text-text-primary font-bold text-[9px] uppercase">Confirm</span>
                        <span className="px-2 py-0.5 rounded bg-surface-muted text-text-primary font-bold text-[9px] uppercase">Approve</span>
                        <span className="px-2 py-0.5 rounded bg-surface-muted text-text-primary font-bold text-[9px] uppercase">Small Test</span>
                    </div>
                </div>
            </div>

            {/* Score Statement */}
            <div className="text-center text-xs font-bold text-text-tertiary mb-12 uppercase tracking-wide">
                A structural score is not a promise of virality, ROAS or GMV.
            </div>

            {/* Golden Fixture Methodology Panel */}
            <div className="mx-auto max-w-3xl p-5 rounded-2xl bg-surface border border-hairline flex gap-3 items-start shadow-sm">
                <Info className="h-5 w-5 text-primary shrink-0 mt-0.5" />
                <div>
                    <h3 className="text-sm font-bold text-text-primary">
                        Golden Fixture Methodology
                    </h3>
                    <p className="mt-1 text-xs text-text-secondary leading-relaxed">
                        The SwiftPress Garment Steamer, Dog Mom Crewneck, and Bag Sealer examples shown on this page are <strong>actual product test fixtures</strong> built directly into the Viraldy domain codebase. They demonstrate the exact logic, OCR checks, and rule verification the system runs in production.
                    </p>
                </div>
            </div>
        </SectionWrapper>
    );
}
