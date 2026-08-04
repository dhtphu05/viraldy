import { Link } from "@tanstack/react-router";
import { ArrowRight, FileVideo, PackageOpen, Sparkles } from "lucide-react";
import { Button } from "@/shared/ui/button";
import { StatusChip } from "@/shared/ui/status-chip";
import { SectionWrapper } from "./section-wrapper";

export function HeroSection() {
    return (
        <SectionWrapper id="hero" className="relative overflow-hidden pt-24 sm:pt-32 lg:pt-40">
            <div
                aria-hidden
                className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_80%_50%_at_50%_-20%,var(--primary-soft),transparent)]"
            />
            <div
                aria-hidden
                className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_60%_40%_at_80%_80%,var(--info-soft),transparent)]"
            />

            <div className="relative mx-auto max-w-3xl text-center">
                <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary-softer px-4 py-1.5">
                    <Sparkles className="h-3.5 w-3.5 text-primary" />
                    <span className="text-xs font-medium text-primary">
                        Creative Intelligence for TikTok Shop &amp; Ecommerce
                    </span>
                </div>

                <h1 className="text-4xl font-bold leading-tight tracking-tight text-text-primary sm:text-5xl lg:text-6xl">
                    Know what TikTok
                    <br />
                    <span className="bg-gradient-to-r from-primary to-warn bg-clip-text text-transparent">
                        to make next.
                    </span>
                </h1>

                <h2 className="mt-6 text-lg leading-relaxed text-text-secondary sm:text-xl">
                    Turn winning creative patterns into product-specific ideas, creator-ready
                    briefs, and exact video fixes &mdash; before you spend.
                </h2>

                <div className="mt-8 flex flex-col items-center gap-3 sm:flex-row sm:justify-center">
                    <Button asChild size="lg" className="shadow-lg shadow-primary/20">
                        <Link to="/login">
                            <PackageOpen className="h-4 w-4" />
                            Start with a Product
                            <ArrowRight className="ml-1 h-4 w-4" />
                        </Link>
                    </Button>
                    <Button asChild variant="outline" size="lg">
                        <Link to="/login">
                            <FileVideo className="h-4 w-4" />
                            Review a Video
                            <ArrowRight className="ml-1 h-4 w-4" />
                        </Link>
                    </Button>
                </div>

                <div className="mt-10 flex flex-wrap items-center justify-center gap-x-8 gap-y-2 text-xs text-text-tertiary">
                    <span>No generic scripts</span>
                    <span aria-hidden>&middot;</span>
                    <span>No &ldquo;make the hook stronger&rdquo;</span>
                    <span aria-hidden>&middot;</span>
                    <span>No guessing what to tell your creator</span>
                </div>

                <div className="mt-10 flex flex-wrap items-center justify-center gap-3">
                    <StatusChip tone="ok" dot>Pattern Breakdown</StatusChip>
                    <StatusChip tone="info" dot>Creative Directions</StatusChip>
                    <StatusChip tone="warn" dot>Creator Pack</StatusChip>
                    <StatusChip tone="neutral" dot>TikTok Score &amp; Fix</StatusChip>
                </div>
            </div>
        </SectionWrapper>
    );
}
