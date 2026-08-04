import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/shared/ui/accordion";
import { SectionWrapper } from "./section-wrapper";

const faqs = [
    {
        q: "Is Viraldy an AI video generator?",
        a: "Viraldy is a creative intelligence and workflow product first. Its core job is to help you decide what to make, turn that direction into something executable, and check the result. AI video generation is an execution path that can sit underneath the same creative plan.",
    },
    {
        q: "Can I use Viraldy without a reference video?",
        a: "Yes. You can start from a product and generate creative directions. References make the reasoning richer when you already have examples you want to learn from.",
    },
    {
        q: "Does Viraldy predict whether my TikTok will go viral?",
        a: "No. Viraldy evaluates creative structure, product fit, execution requirements and observable blockers. Virality and commercial performance depend on many variables outside the creative itself.",
    },
    {
        q: "How is this different from asking ChatGPT for scripts?",
        a: "ChatGPT can generate excellent scripts when you provide the right context and prompt. Viraldy keeps product context, references, creative directions, production requirements, video evidence and revisions connected in one workflow. The output is not only a script. It is a creative decision and execution process.",
    },
    {
        q: "What types of sellers is Viraldy designed for?",
        a: "Viraldy is initially designed around TikTok Shop sellers, POD and personalization sellers, dropshipping operators, cross-border ecommerce teams, and agencies managing creator-led ecommerce creative.",
    },
    {
        q: "Can I send the output directly to a creator?",
        a: "Yes. The Creator Plan is designed to turn the selected creative direction into a clear production brief with hooks, talking points, shots, required product details, CTA, do/don't guidance and revision requirements.",
    },
    {
        q: "What happens when my creator sends the video?",
        a: "Upload it to Viraldy. The system can review the draft, surface blockers, separate edit fixes from reshoots and create a creator-friendly revision plan.",
    },
    {
        q: "Does Viraldy replace testing?",
        a: "No. The purpose is to make testing more deliberate. Viraldy helps identify structural issues and clarify what is being tested before you commit more time or budget.",
    },
];

export function FaqSection() {
    return (
        <SectionWrapper id="faq" background="surface">
            <div className="mx-auto max-w-2xl">
                <h2 className="text-center text-2xl font-bold text-text-primary sm:text-3xl">
                    FAQ
                </h2>

                <Accordion type="single" collapsible className="mt-8">
                    {faqs.map((faq) => (
                        <AccordionItem key={faq.q} value={faq.q}>
                            <AccordionTrigger className="text-left text-sm font-medium text-text-primary hover:no-underline">
                                {faq.q}
                            </AccordionTrigger>
                            <AccordionContent className="text-sm leading-relaxed text-text-secondary">
                                {faq.a}
                            </AccordionContent>
                        </AccordionItem>
                    ))}
                </Accordion>
            </div>
        </SectionWrapper>
    );
}
