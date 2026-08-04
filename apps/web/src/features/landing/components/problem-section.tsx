import { SectionWrapper } from "./section-wrapper";

export function ProblemSection() {
    const decisions = [
        { q: "What should we make?", desc: "Which reference angle actually matches our product margin, claims, and buyer persona?" },
        { q: "How should the creator film it?", desc: "How do we write a brief that specifies required scenes, variants, and hook timings without crushing creator freedom?" },
        { q: "Is this draft actually good enough?", desc: "Is the video ready to put money behind, or is it missing structural hooks and product proofs?" },
        { q: "What exactly should we fix?", desc: "Can the editor salvage it by re-sequencing the timeline, or must the creator reshoot a demo scene?" },
        { q: "What did we learn from the test?", desc: "Did version 2 perform better? Which creative hook actually drove the ROAS lift?" },
    ];

    return (
        <SectionWrapper id="problem" background="surface" className="py-20 border-b border-hairline">
            <div className="mx-auto max-w-3xl">
                <span className="rounded-full bg-destructive-soft px-3 py-1.5 text-xs font-semibold text-destructive">
                    The Pain
                </span>
                <h2 className="mt-4 text-3xl font-bold tracking-tight text-text-primary sm:text-4xl">
                    Making more content is easy.
                    <br />
                    <span className="text-text-secondary">Knowing what is worth making is harder.</span>
                </h2>

                <p className="mt-6 text-base leading-relaxed text-text-secondary">
                    You can already ask ChatGPT to generate 20 scripts. You can already save hundreds of winning ad references. You can already send sample products to creators. But teams still struggle to answer the critical questions:
                </p>

                {/* List of Seller Decisions */}
                <div className="mt-8 space-y-4">
                    {decisions.map((item, idx) => (
                        <div key={idx} className="flex gap-4 p-4 rounded-xl border border-hairline bg-background/50">
                            <span className="text-sm font-bold text-primary shrink-0 tabular">0{idx + 1}</span>
                            <div>
                                <h4 className="text-sm font-bold text-text-primary">&ldquo;{item.q}&rdquo;</h4>
                                <p className="mt-1 text-xs text-text-secondary leading-relaxed">{item.desc}</p>
                            </div>
                        </div>
                    ))}
                </div>

                <div className="mt-8 p-5 rounded-2xl bg-primary-softer border border-primary/20 text-center">
                    <p className="text-sm font-medium text-text-primary leading-relaxed">
                        Viraldy is the <strong>decision layer</strong> between creative research, production, review, and learning. We eliminate the messy spreadsheets and guess-work.
                    </p>
                </div>
            </div>
        </SectionWrapper>
    );
}
