export type PatternInstruction = {
    element_path: string;
    instruction_type: "keep" | "change" | "avoid";
    instruction: string;
    rationale: string;
    severity: "hard" | "high" | "medium" | "low";
};

export type PatternKitView = {
    name: string;
    summary: string;
    sequence: Array<{
        beat_id: string;
        order: number;
        beat_type: string;
        purpose: string;
        recommended_start_ms_min: number | null;
        recommended_start_ms_max: number | null;
        requiredness: string;
    }>;
    applicability: {
        suitable_categories: string[];
        unsuitable_categories: string[];
        required_product_traits: string[];
        buyer_contexts: string[];
        markets: string[];
        platforms: string[];
        objectives: string[];
    };
    adaptation_instructions: PatternInstruction[];
    performance_summary: {
        evidence_status: "none" | "directional" | "supported";
        asset_count: number;
        caveats: string[];
        confidence: "low" | "medium" | "high";
    };
    source: {
        source_asset_count: number;
        source_category_count: number;
    };
    overall_confidence: "low" | "medium" | "high";
    uncertainties: string[];
};

export type PatternKitDetail = {
    kit: {
        id: string;
        name: string;
        latest_version: number;
        status: string;
    };
    latest_version: {
        id: string;
        version: number;
        pattern: PatternKitView;
        model_run_id: string | null;
    };
};

export type ViralConcept = {
    id: string;
    name: string;
    strategic_axis: string;
    diversity_axes: string[];
    buyer_persona_label: string;
    buyer_pain: string;
    desired_outcome: string;
    creative_angle: string;
    hook: {
        hook_type: string;
        spoken_text: string | null;
        overlay_text: string | null;
        opening_visual: string;
        target_time_ms: number;
        product_present: boolean;
    };
    opening_visual: string;
    narrative_structure: string;
    creator_persona: string;
    delivery_style: string;
    demo_mechanism: string;
    proof_mechanism: string;
    offer_framing: string | null;
    cta_strategy: string;
    must_show: Array<{
        id: string;
        instruction: string;
        severity: string;
        expected_before_ms: number | null;
    }>;
    claims_to_avoid: string[];
    required_disclosures: string[];
    test_hypothesis: string;
    expected_learning: string;
    risks: Array<{ code: string; severity: string; message: string }>;
    confidence: string;
};

export type ViralKitView = {
    name: string;
    objective: string;
    platform: string;
    target_market: string;
    product: {
        snapshot_json: {
            identity?: { name?: string; category?: string; market?: string };
        };
    };
    concepts: ViralConcept[];
    test_matrix: {
        primary_hypothesis: string;
        controlled_variables: string[];
        intentionally_changed_variables: string[];
        recommended_test_order: string[];
        concepts: Array<{
            concept_id: string;
            hypothesis: string;
            changed_axes: string[];
            held_constant: string[];
            minimum_execution_requirements: string[];
            metrics_to_observe: string[];
        }>;
    };
    selected_concept_id: string | null;
    risks: Array<{ code: string; severity: string; message: string }>;
    overall_confidence: string;
    uncertainties: string[];
};

export type ViralKitDetail = {
    kit: {
        id: string;
        name: string;
        latest_version: number;
        status: string;
        selected_concept_id: string | null;
    };
    latest_version: {
        id: string;
        version: number;
        viral_kit: ViralKitView;
        model_run_id: string | null;
    };
};

export type SellerDecisionSummary = {
    headline: string;
    one_sentence_decision: string;
    why_this_matters: string;
    strengths_to_keep: string[];
    blockers_to_fix: string[];
    next_actions: string[];
    confidence_explanation: string;
    commercial_guardrail: string;
    locale: "en-US" | "vi-VN";
};

export type CreatorRevisionMessage = {
    message: string;
    strengths_to_preserve: string[];
    required_changes: Array<{
        code: string;
        instruction: string;
        required_text: string | null;
        target_start_ms: number | null;
        target_end_ms: number | null;
    }>;
    referenced_blocker_codes: string[];
    resubmission_request: string;
    locale: "en-US";
};

export type PreflightPresentation = {
    preflight_run_id: string;
    seller_summary: SellerDecisionSummary;
    creator_revision: CreatorRevisionMessage | null;
    sources: Record<string, "openai" | "deterministic" | "deterministic_fallback">;
    model_run_ids: string[];
};
