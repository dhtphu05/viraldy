import { LandingNav } from "./components/landing-nav";
import { LandingFooter } from "./components/landing-footer";
import { HeroSection } from "./components/hero-section";
import { ScaleProofBand } from "./components/scale-proof-band";
import { CoreWorkflow } from "./components/core-workflow";
import { ProblemSection } from "./components/problem-section";
import { StoryIntro } from "./components/story-intro";
import { ReferenceInput } from "./components/reference-input";
import { PatternBreakdown } from "./components/pattern-breakdown";
import { ReusableStructure } from "./components/reusable-structure";
import { KeepChangeAvoid } from "./components/keep-change-avoid";
import { PatternApplicability } from "./components/pattern-applicability";
import { CreativeDirections } from "./components/creative-directions";
import { CreatorPlan } from "./components/creator-plan";
import { ReviewBeforeYouSpend } from "./components/review-before-you-spend";
import { RevisionCompare } from "./components/revision-compare";
import { SellerDecisions } from "./components/seller-decisions";
import { PerformanceLearning } from "./components/performance-learning";
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

                {/* 02 Data Proof / Scale Band */}
                <ScaleProofBand />

                {/* 03 Core Workflow (Viraldy in 30 Seconds) */}
                <CoreWorkflow />

                {/* 04 The Problem (Before vs With Viraldy) */}
                <ProblemSection />

                {/* 05 Story Intro & Product Context Card */}
                <StoryIntro />

                {/* 06 Reference Input */}
                <ReferenceInput />

                {/* 07 Winning Pattern Breakdown */}
                <PatternBreakdown />

                {/* 08 Reusable Pattern Beats Sequence */}
                <ReusableStructure />

                {/* 09 Keep, Change, Avoid */}
                <KeepChangeAvoid />

                {/* 10 Suitability / Applicability */}
                <PatternApplicability />

                {/* 11 3 Creative Directions & Concept Matrix */}
                <CreativeDirections />

                {/* 12 Creator Plan & Storyboard */}
                <CreatorPlan />

                {/* 13 Quality Control: Draft 1 Score & Fix */}
                <ReviewBeforeYouSpend />

                {/* 14 Quality Control: V2 Revision Compare */}
                <RevisionCompare />

                {/* 15 Commerce Decisions beyond the core loop */}
                <SellerDecisions />

                {/* 16 Performance Learning & Next Test Recommender */}
                <PerformanceLearning />

                {/* 17 Interactive Use Case Tabs */}
                <UseCases />

                {/* 18 Nuanced Why Viraldy Matrix */}
                <WhyViraldy />

                {/* 19 Trust & Grounding Methodology */}
                <TrustSection />

                {/* 20 FAQ */}
                <FaqSection />

                {/* 21 Final CTA */}
                <EarlyAccessCta />
            </main>
            <LandingFooter />
        </div>
    );
}
