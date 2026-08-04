import { LandingNav } from "./components/landing-nav";
import { LandingFooter } from "./components/landing-footer";
import { HeroSection } from "./components/hero-section";
import { ValueStrip } from "./components/value-strip";
import { BuiltFor } from "./components/built-for";
import { ProblemSection } from "./components/problem-section";
import { FeaturePatternBreakdown } from "./components/feature-pattern-breakdown";
import { FeatureCreativeDirections } from "./components/feature-creative-directions";
import { FeatureCreatorPack } from "./components/feature-creator-pack";
import { FeatureTikTokScore } from "./components/feature-tiktok-score";
import { FeatureCreatorDraftReview } from "./components/feature-creator-draft-review";
import { FeatureRevisionCompare } from "./components/feature-revision-compare";
import { CoreWorkflow } from "./components/core-workflow";
import { WhyViraldy } from "./components/why-viraldy";
import { UseCaseTikTokShop } from "./components/use-case-tiktok-shop";
import { UseCasePod } from "./components/use-case-pod";
import { UseCaseDropshipping } from "./components/use-case-dropshipping";
import { AgencySection } from "./components/agency-section";
import { DifferenceSection } from "./components/difference-section";
import { OutputSection } from "./components/output-section";
import { PhilosophySection } from "./components/philosophy-section";
import { AiCreatorRoadmap } from "./components/ai-creator-roadmap";
import { LearningLoop } from "./components/learning-loop";
import { ComparisonTable } from "./components/comparison-table";
import { TrustSection } from "./components/trust-section";
import { EarlyAccessCta } from "./components/early-access-cta";
import { FaqSection } from "./components/faq-section";

export function LandingPage() {
    return (
        <div className="flex h-dvh flex-col overflow-y-auto bg-background">
            <LandingNav />
            <main>
                <HeroSection />
                <ValueStrip />
                <BuiltFor />
                <ProblemSection />
                <FeaturePatternBreakdown />
                <FeatureCreativeDirections />
                <FeatureCreatorPack />
                <FeatureTikTokScore />
                <FeatureCreatorDraftReview />
                <FeatureRevisionCompare />
                <CoreWorkflow />
                <WhyViraldy />
                <UseCaseTikTokShop />
                <UseCasePod />
                <UseCaseDropshipping />
                <AgencySection />
                <DifferenceSection />
                <OutputSection />
                <PhilosophySection />
                <AiCreatorRoadmap />
                <LearningLoop />
                <ComparisonTable />
                <TrustSection />
                <EarlyAccessCta />
                <FaqSection />
            </main>
            <LandingFooter />
        </div>
    );
}
