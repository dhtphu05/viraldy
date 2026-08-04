import { LandingNav } from "./components/landing-nav";
import { LandingFooter } from "./components/landing-footer";
import { HeroSection } from "./components/hero-section";
import { CoreWorkflow } from "./components/core-workflow";
import { ProblemSection } from "./components/problem-section";
import { FeaturePatternBreakdown } from "./components/feature-pattern-breakdown";
import { FeatureCreativeDirections } from "./components/feature-creative-directions";
import { FeatureCreatorPack } from "./components/feature-creator-pack";
import { ReviewBeforeYouSpend } from "./components/review-before-you-spend";
import { SellerDecisions } from "./components/seller-decisions";
import { LearningLoop } from "./components/learning-loop";
import { UseCases } from "./components/use-cases";
import { WhyViraldy } from "./components/why-viraldy";
import { TrustSection } from "./components/trust-section";
import { EarlyAccessCta } from "./components/early-access-cta";
import { FaqSection } from "./components/faq-section";

export function LandingPage() {
    return (
        <div className="flex h-dvh flex-col overflow-y-auto bg-background">
            <LandingNav />
            <main className="flex-1">
                {/* 01 Hero Section */}
                <HeroSection />

                {/* 02 Workflow (Viraldy in 30 Seconds) */}
                <CoreWorkflow />

                {/* 03 The Problem */}
                <ProblemSection />

                {/* 04 Find What to Make (Breakdowns + Creative Directions) */}
                <FeaturePatternBreakdown />
                <FeatureCreativeDirections />

                {/* 05 Make it Filmable (Creator Plans) */}
                <FeatureCreatorPack />

                {/* 06 Review Before You Spend (Scores & Fixes + Draft Reviews + Revision compares) */}
                <ReviewBeforeYouSpend />

                {/* 07 Commerce Decisions beyond the core loop */}
                <SellerDecisions />

                {/* 08 Learn What to Test Next (Roadmap/Beta Performance loops) */}
                <LearningLoop />

                {/* 09 Use Cases (Tabbed display) */}
                <UseCases />

                {/* 10 Why Viraldy (Comparison matrix) */}
                <WhyViraldy />

                {/* 11 Trust Section (Product Proof / Golden Cases explanation) */}
                <TrustSection />

                {/* 12 FAQ Section */}
                <FaqSection />

                {/* 13 Final High-Converting CTA */}
                <EarlyAccessCta />
            </main>
            <LandingFooter />
        </div>
    );
}
