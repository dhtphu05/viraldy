# VIRALDY — GOLDEN OUTPUT REFERENCE & ACCEPTANCE EXAMPLES

## Purpose

This document defines the quality bar for Viraldy intelligence outputs.

It is a companion to:

- `VIRALDY_PRIVATE_BETA_BACKEND_AUTH_PATTERNKIT_VIRALKIT_COMPLETION_GOAL.md`

Codex must not invent generic outputs. The examples below are the target product behavior for:

- Product Context
- Creative DNA
- PatternKit
- ViralKit
- Creative Campaign Pack
- TikTok Structural Scorer
- UGC Preflight
- Recommendation
- Revision comparison
- Seller feedback and learning capture

These are not marketing mockups. They are golden fixtures and acceptance references for private-beta implementation.

---

# 1. Viraldy output philosophy

Every meaningful Viraldy output must satisfy four grounding layers.

## 1.1 Product-grounded

The response must use the actual product context:

- product mechanism;
- buyer persona;
- buyer pain;
- desired outcome;
- price and offer;
- market;
- shipping and fulfillment;
- claims allowed;
- claims prohibited;
- required disclosures;
- product assets;
- seller constraints.

When a value is unavailable, return `unknown`, `null`, or a typed missing state.

Never fill gaps with a plausible-sounding product claim.

## 1.2 Evidence-grounded

Every observation about a video must identify:

- what was observed;
- evidence source;
- timestamp or time range when available;
- evidence ID;
- confidence;
- uncertainty.

A seller must be able to click a finding and inspect the corresponding moment.

## 1.3 Decision-grounded

Every score or diagnosis must lead to a practical action:

- approve;
- revise;
- reject;
- reshoot;
- organic-only;
- small paid test;
- Spark-ready pending rights;
- create Campaign Pack;
- select concept;
- stop using a pattern;
- collect more evidence.

Never end with generic advice such as:

> Make the hook stronger and add a clearer CTA.

## 1.4 Learning-grounded

The system must preserve:

```text
AI output
→ human correction
→ seller decision
→ revision or execution
→ performance outcome
```

The AI output must not be overwritten when the user corrects it.

---

# 2. Quality bar: generic vs Viraldy-grade output

## 2.1 Unacceptable generic output

```text
The hook is weak.
Show the product earlier.
Add social proof.
Use a stronger CTA.
```

Problems:

- no product context;
- no evidence;
- no exact expected timing;
- no reason why the proof is weak;
- no differentiation between blocker and optional improvement;
- no creator-ready revision;
- no action label.

## 2.2 Viraldy-grade output

```text
Action: Revise before paid use
Confidence: Medium

Product: SwiftPress Mini Garment Steamer
Buyer: US college students who need quick clothing care in small spaces
Objective: TikTok Shop affiliate test

Hard blocker
- The Campaign Pack requires the product to appear by 00:02.000.
- The first clear product appearance is at 00:04.200.
- Evidence: product_appearance_17, frames 126–149.

Missing execution
- The brief requires an observable same-fabric before/after result.
- The draft shows steam output but never returns to the original wrinkled section.
- Evidence: demo_action_22 and proof_summary_31.

What is already strong
- The creator delivery feels natural and matches the requested student-review style.
- The product-tag CTA is visible from 00:18.800 to 00:21.100.

Revision request
1. Move the product close-up into the first two seconds.
2. Keep the same shirt section visible before and after steaming.
3. Add the required disclosure: “Results vary by fabric type.”
4. Preserve the current creator delivery and product-tag CTA.
```

---

# 3. Golden end-to-end scenario A — TikTok Shop US home/travel product

## 3.1 Seller context

```text
Seller type: Cross-border TikTok Shop US operator
Team location: Vietnam
Target market: United States
Team size: 4
Creative volume: 20–40 short videos per month
Current workflow: TikTok Favorites + Drive + Sheets + creator chat
Objective: Produce creator UGC for organic affiliate testing and limited Spark testing
```

## 3.2 Product

```text
Product name: SwiftPress Mini Garment Steamer
Category: Home / travel apparel care
Selling price: $29.99
COGS: $8.40
Shipping promise authorized by seller: 4–6 business days
Primary buyer: US college students and frequent travelers
Primary pain: Wrinkled clothing when there is no room or time for a full-size iron
Desired outcome: Presentable clothing with a compact tool
Observable mechanism: Steam is applied directly to wrinkled fabric
Observable proof: Same fabric area before and after use
Offer: 15% launch discount
Objective: TikTok Shop affiliate test
```

## 3.3 Product claim governance

Allowed:

- helps reduce visible wrinkles;
- compact for dorm rooms and travel;
- heats and produces steam according to verified product instructions;
- convenient alternative for quick touch-ups.

Allowed with qualification:

- visible wrinkle reduction, when accompanied by an actual same-fabric demonstration;
- “quick” when not represented as instant and when tied to the observed clip.

Prohibited:

- removes every wrinkle instantly;
- professional dry-cleaning results;
- sanitizes or kills bacteria unless separately verified;
- safe for every fabric;
- guaranteed result.

Required disclosure:

- Results vary by fabric type.

---

# 4. Golden ProductContextV1 output

```json
{
  "schema_version": "product_context_v1",
  "identity": {
    "name": "SwiftPress Mini Garment Steamer",
    "brand": "SwiftPress",
    "category": "home_travel_apparel_care",
    "market": "US",
    "product_type": "portable_garment_steamer"
  },
  "buyer_personas": [
    {
      "id": "college_student",
      "label": "College student in a dorm or shared apartment",
      "pains": [
        "Wrinkled clothes before class or an event",
        "Limited storage space",
        "No full-size ironing setup"
      ],
      "desired_outcomes": [
        "Look presentable quickly",
        "Keep clothing care compact and convenient"
      ],
      "objections": [
        "Will it actually show a visible difference?",
        "Is it safe for my fabric?",
        "Is it worth carrying or storing?"
      ]
    },
    {
      "id": "frequent_traveler",
      "label": "Frequent traveler with carry-on luggage",
      "pains": [
        "Clothes become wrinkled in luggage",
        "Hotel ironing tools may be unavailable"
      ],
      "desired_outcomes": [
        "Refresh clothing without a full ironing board"
      ],
      "objections": [
        "Will it fit in luggage?",
        "How quickly can it be used?"
      ]
    }
  ],
  "benefits": [
    {
      "id": "visible_wrinkle_reduction",
      "statement": "Helps reduce visible wrinkles when used on supported fabrics.",
      "evidence_status": "seller_provided",
      "claim_policy": "allowed_with_qualification"
    },
    {
      "id": "compact_storage",
      "statement": "Compact format for dorm rooms and travel.",
      "evidence_status": "product_spec",
      "claim_policy": "allowed"
    }
  ],
  "commercial": {
    "currency": "USD",
    "selling_price": 29.99,
    "cogs": 8.40,
    "offer": {
      "type": "percentage_discount",
      "value": 15,
      "label": "15% launch discount"
    },
    "shipping": {
      "market": "US",
      "authorized_promise": "4–6 business days",
      "unverified_promises": []
    }
  },
  "creative_context": {
    "visual_demo_potential": "high",
    "recommended_proof": [
      "same_fabric_before_after",
      "close_up_wrinkle_change"
    ],
    "risky_execution": [
      "steam-only shot without visible result",
      "claiming instant results",
      "switching garments between before and after"
    ],
    "platform_cues": [
      "TikTok Shop product tag",
      "vertical 9:16 framing",
      "natural creator delivery"
    ]
  },
  "governance": {
    "allowed_claims": [
      "Helps reduce visible wrinkles",
      "Compact for quick touch-ups"
    ],
    "allowed_with_qualification": [
      {
        "claim": "Quick wrinkle reduction",
        "qualification": "Show the actual result and avoid instant-result language."
      }
    ],
    "prohibited_claims": [
      "Removes every wrinkle instantly",
      "Professional dry-cleaning results",
      "Kills bacteria",
      "Safe for every fabric",
      "Guaranteed result"
    ],
    "required_disclosures": [
      "Results vary by fabric type."
    ]
  },
  "completeness": {
    "status": "usable",
    "missing_fields": [
      "verified_supported_fabric_list"
    ]
  }
}
```

Acceptance requirements:

- Product projections must match `identity.name` and `identity.market`.
- Missing supported-fabric information remains missing.
- Downstream outputs must not claim universal fabric compatibility.

---

# 5. Golden Creative DNA output for a reference video

## 5.1 Reference asset description

```text
Duration: 23.4 seconds
Reference product: competing portable steamer
Creator: student/lifestyle creator
Observed flow:
wrinkled shirt problem → product reveal → steaming demo → same-shirt result → product-tag CTA
```

## 5.2 CreativeDnaV1 target output

```json
{
  "schema_version": "creative_dna_v1",
  "asset_version_id": "ref-steamer-asset-v1",
  "opening": {
    "hook_type": {
      "value": "situational_problem",
      "evidence_ids": ["ev-hook-01", "ev-asr-01"],
      "confidence": 0.93
    },
    "hook_text": {
      "value": "I was already late and this shirt was still wrinkled.",
      "evidence_ids": ["ev-asr-01"],
      "confidence": 0.98
    },
    "opening_visual": {
      "value": "Creator holds a visibly wrinkled shirt close to camera.",
      "evidence_ids": ["ev-frame-01"],
      "confidence": 0.95
    },
    "first_three_second_structure": {
      "value": [
        "show_problem",
        "state_time_pressure",
        "reveal_product"
      ],
      "evidence_ids": ["ev-scene-01", "ev-scene-02"],
      "confidence": 0.91
    }
  },
  "product": {
    "first_appearance_ms": {
      "value": 1300,
      "evidence_ids": ["ev-product-first-01"],
      "confidence": 0.96
    },
    "shot_types": {
      "value": ["handheld_close_up", "in_use"],
      "evidence_ids": ["ev-product-appearance-01", "ev-product-appearance-02"],
      "confidence": 0.89
    },
    "product_match_confidence": {
      "value": null,
      "unknown_reason": "No target Product Context was attached to this reference analysis.",
      "evidence_ids": [],
      "confidence": 0.0
    }
  },
  "narrative": {
    "structure": {
      "value": "problem_solution_transformation",
      "evidence_ids": ["ev-scene-sequence-01"],
      "confidence": 0.92
    },
    "angle": {
      "value": "last_minute_clothing_rescue",
      "evidence_ids": ["ev-asr-01", "ev-scene-sequence-01"],
      "confidence": 0.87
    },
    "buyer_pain": {
      "value": "Wrinkled clothing immediately before leaving.",
      "evidence_ids": ["ev-asr-01", "ev-frame-01"],
      "confidence": 0.94
    },
    "desired_outcome": {
      "value": "Make clothing look presentable with minimal setup.",
      "evidence_ids": ["ev-result-01"],
      "confidence": 0.81
    }
  },
  "demo": {
    "detected": {
      "value": true,
      "evidence_ids": ["ev-demo-01"],
      "confidence": 0.98
    },
    "demo_type": {
      "value": "same_item_in_use_transformation",
      "evidence_ids": ["ev-demo-01", "ev-proof-01"],
      "confidence": 0.94
    },
    "steps": {
      "value": [
        "show_wrinkled_fabric",
        "apply_steam_to_same_area",
        "show_same_area_after_use"
      ],
      "evidence_ids": ["ev-demo-01", "ev-proof-01"],
      "confidence": 0.93
    },
    "mechanism_clarity": {
      "value": "clear",
      "evidence_ids": ["ev-demo-01"],
      "confidence": 0.90
    },
    "result_visibility": {
      "value": "clear",
      "evidence_ids": ["ev-proof-01"],
      "confidence": 0.88
    }
  },
  "proof": {
    "proof_types": {
      "value": ["same_item_before_after", "observable_visual_result"],
      "evidence_ids": ["ev-proof-01"],
      "confidence": 0.91
    },
    "verifiability": {
      "value": "medium_high",
      "evidence_ids": ["ev-proof-01"],
      "confidence": 0.82,
      "uncertainty": "Lighting changes slightly between the before and after views."
    }
  },
  "creator": {
    "persona": {
      "value": "college_lifestyle_creator",
      "evidence_ids": ["ev-creator-01"],
      "confidence": 0.75
    },
    "delivery_style": {
      "value": "casual_first_person_review",
      "evidence_ids": ["ev-asr-full-01"],
      "confidence": 0.90
    },
    "authenticity_cues": {
      "value": [
        "situational context",
        "natural speech",
        "hands-on demonstration"
      ],
      "evidence_ids": ["ev-creator-01", "ev-demo-01"],
      "confidence": 0.86
    }
  },
  "editing": {
    "pacing": {
      "value": "fast_but_readable",
      "evidence_ids": ["ev-editing-01"],
      "confidence": 0.87
    },
    "first_three_second_cut_count": {
      "value": 2,
      "evidence_ids": ["ev-editing-01"],
      "confidence": 0.99
    },
    "pattern_interrupts": {
      "value": [
        "wrinkled-shirt close-up",
        "fast product hand-entry"
      ],
      "evidence_ids": ["ev-editing-02"],
      "confidence": 0.85
    },
    "dead_air_ranges": {
      "value": [],
      "evidence_ids": ["ev-editing-03"],
      "confidence": 0.82
    }
  },
  "offer": {
    "present": {
      "value": false,
      "evidence_ids": [],
      "confidence": 0.66,
      "uncertainty": "No clear price or discount was observed in transcript or OCR evidence."
    }
  },
  "cta": {
    "present": {
      "value": true,
      "evidence_ids": ["ev-cta-01"],
      "confidence": 0.98
    },
    "cta_type": {
      "value": "tiktok_shop_product_tag",
      "evidence_ids": ["ev-cta-01"],
      "confidence": 0.95
    },
    "start_ms": {
      "value": 20100,
      "evidence_ids": ["ev-cta-01"],
      "confidence": 0.98
    },
    "spoken_text": {
      "value": "It is linked right here.",
      "evidence_ids": ["ev-asr-cta-01"],
      "confidence": 0.97
    },
    "overlay_text": {
      "value": "Shop now",
      "evidence_ids": ["ev-ocr-cta-01"],
      "confidence": 0.91
    }
  },
  "claims": {
    "observed_claims": [
      {
        "text": "It fixed the wrinkles so fast.",
        "risk": "medium",
        "reason": "The claim is supported directionally by the visible result but uses broad speed language.",
        "evidence_ids": ["ev-asr-claim-01", "ev-proof-01"],
        "confidence": 0.79
      }
    ]
  },
  "reusable_mechanisms": [
    {
      "mechanism": "situational urgency before product reveal",
      "evidence_ids": ["ev-hook-01", "ev-product-first-01"],
      "confidence": 0.88
    },
    {
      "mechanism": "same-item demonstration followed by visible result",
      "evidence_ids": ["ev-demo-01", "ev-proof-01"],
      "confidence": 0.92
    }
  ],
  "risks": [
    {
      "code": "REFERENCE_SPEED_CLAIM",
      "severity": "medium",
      "message": "Do not copy broad speed language without product-specific evidence.",
      "evidence_ids": ["ev-asr-claim-01"]
    }
  ],
  "overall_confidence": "high",
  "uncertainties": [
    "The creator persona is inferred from content style, not verified profile data.",
    "No performance data is attached, so this analysis does not prove that the structure caused sales."
  ]
}
```

Acceptance requirements:

- Product match remains unknown because no target product was attached.
- The reference is described, not declared a winning ad.
- CTA spoken text and overlay text remain separate.
- Offer is not invented.
- Every positive observation has evidence.

---

# 6. Golden PatternKit output

## 6.1 PatternKit name

```text
Deadline Pressure → Fast Product Reveal → Same-Fabric Proof
```

## 6.2 Intended use

This PatternKit abstracts a reusable structure from two reference videos. It does not copy either script.

## 6.3 PatternKitV1 target output

```json
{
  "schema_version": "pattern_kit_v1",
  "id": "pk-deadline-fast-reveal-proof",
  "version": 1,
  "name": "Deadline Pressure → Fast Product Reveal → Same-Fabric Proof",
  "summary": "A situation-led structure that creates urgency, reveals the product early, demonstrates use on the same item, and closes with observable proof and a commerce CTA.",
  "kind": "multi_asset_cluster",
  "scope": "workspace_private",
  "status": "candidate",
  "source": {
    "creative_dna_version_ids": [
      "dna-steamer-reference-v1",
      "dna-lint-remover-reference-v1"
    ],
    "source_asset_count": 2,
    "source_category_count": 2,
    "extraction_mode": "ai_assisted"
  },
  "sequence": [
    {
      "beat_id": "beat_1_problem_hook",
      "order": 1,
      "beat_type": "hook",
      "purpose": "Make the buyer recognize a time-sensitive or socially uncomfortable problem.",
      "recommended_start_ms_min": 0,
      "recommended_start_ms_max": 300,
      "recommended_duration_ms_min": 900,
      "recommended_duration_ms_max": 1800,
      "requiredness": "required",
      "evidence_refs": ["pattern-ev-hook-a", "pattern-ev-hook-b"],
      "confidence": 0.90
    },
    {
      "beat_id": "beat_2_product_reveal",
      "order": 2,
      "beat_type": "product_reveal",
      "purpose": "Connect the product directly to the problem before attention decays.",
      "recommended_start_ms_min": 900,
      "recommended_start_ms_max": 2200,
      "recommended_duration_ms_min": 800,
      "recommended_duration_ms_max": 1800,
      "requiredness": "required",
      "evidence_refs": ["pattern-ev-product-a", "pattern-ev-product-b"],
      "confidence": 0.92
    },
    {
      "beat_id": "beat_3_in_use_demo",
      "order": 3,
      "beat_type": "demo",
      "purpose": "Show the mechanism on the actual problem object.",
      "recommended_start_ms_min": 2000,
      "recommended_start_ms_max": 4500,
      "recommended_duration_ms_min": 3500,
      "recommended_duration_ms_max": 7000,
      "requiredness": "required",
      "evidence_refs": ["pattern-ev-demo-a", "pattern-ev-demo-b"],
      "confidence": 0.91
    },
    {
      "beat_id": "beat_4_observable_proof",
      "order": 4,
      "beat_type": "proof",
      "purpose": "Return to the same item or area and show an observable result.",
      "recommended_start_ms_min": 7000,
      "recommended_start_ms_max": 13000,
      "recommended_duration_ms_min": 1800,
      "recommended_duration_ms_max": 4000,
      "requiredness": "required",
      "evidence_refs": ["pattern-ev-proof-a", "pattern-ev-proof-b"],
      "confidence": 0.89
    },
    {
      "beat_id": "beat_5_commerce_cta",
      "order": 5,
      "beat_type": "cta",
      "purpose": "Make the next commerce action explicit without replacing proof with sales language.",
      "recommended_start_ms_min": 15000,
      "recommended_start_ms_max": 22000,
      "recommended_duration_ms_min": 1500,
      "recommended_duration_ms_max": 3500,
      "requiredness": "recommended",
      "evidence_refs": ["pattern-ev-cta-a"],
      "confidence": 0.72
    }
  ],
  "opening": {
    "primary_hook_types": [
      "situational_problem",
      "time_pressure"
    ],
    "hook_mechanism": "Show a recognizable problem and state why it matters now.",
    "opening_visual_pattern": "Problem object fills the frame before or while the first line is spoken.",
    "first_three_second_structure": [
      "problem_visual",
      "situational_context",
      "product_reveal"
    ],
    "face_presence_preference": "optional",
    "product_presence_preference": "before_2200ms",
    "pattern_interrupt_strategy": [
      "macro problem close-up",
      "fast hand-entry with product"
    ],
    "evidence_refs": ["pattern-ev-hook-a", "pattern-ev-hook-b"],
    "confidence": 0.90,
    "uncertainties": []
  },
  "product_reveal": {
    "first_appearance_window_ms": {
      "min": 900,
      "max": 2200
    },
    "preferred_shot_types": [
      "handheld_close_up",
      "in_use"
    ],
    "close_up_expectation": "required",
    "usage_visibility_expectation": "required",
    "screen_time_guidance": "The product should remain identifiable through the core demo.",
    "reveal_role": "solution_connection",
    "product_match_requirement": "Target product identity must be verified when Product Context is attached.",
    "evidence_refs": ["pattern-ev-product-a", "pattern-ev-product-b"],
    "confidence": 0.92,
    "uncertainties": []
  },
  "narrative": {
    "structures": [
      "problem_solution_transformation"
    ],
    "angle_family": "urgent_practical_rescue",
    "buyer_pain_pattern": "A visible problem appears immediately before a socially or practically important moment.",
    "desired_outcome_pattern": "Resolve the visible problem with minimal setup.",
    "emotional_drivers": [
      "relief",
      "preparedness",
      "convenience"
    ],
    "awareness_stage": "problem_aware",
    "narrative_progression": [
      "recognize problem",
      "introduce product",
      "demonstrate mechanism",
      "show result",
      "invite next action"
    ],
    "evidence_refs": ["pattern-ev-narrative-a", "pattern-ev-narrative-b"],
    "confidence": 0.88,
    "uncertainties": []
  },
  "demo": {
    "demo_types": [
      "same_item_in_use_transformation"
    ],
    "mechanism_pattern": "Use the product on the original problem object while preserving visual continuity.",
    "required_steps": [
      "show initial state",
      "show product contacting or affecting the same object",
      "show result on the same object or area"
    ],
    "before_state_expectation": "Clearly visible and retained long enough for comparison.",
    "after_state_expectation": "Same item, same area, or an unmistakably equivalent comparison.",
    "result_visibility_expectation": "Observable without relying only on spoken claims.",
    "continuity_expectation": "medium_high",
    "demo_failure_modes": [
      "showing the tool without showing its effect",
      "changing objects between before and after",
      "cutting before the result becomes visible",
      "using text claims as a substitute for proof"
    ],
    "evidence_refs": ["pattern-ev-demo-a", "pattern-ev-demo-b"],
    "confidence": 0.91,
    "uncertainties": []
  },
  "proof": {
    "proof_types": [
      "same_item_before_after",
      "observable_visual_result"
    ],
    "proof_mechanism": "Return to the original problem area and show a visible change.",
    "verifiability_requirement": "The viewer should be able to compare before and after without trusting narration alone.",
    "proof_timing_guidance": "Immediately after the main demo and before the final CTA.",
    "proof_strength_conditions": [
      "same object or area",
      "similar framing",
      "similar lighting",
      "no hidden product substitution"
    ],
    "unsupported_proof_risks": [
      "universal result claims",
      "instant-result language",
      "edited comparison that hides continuity"
    ],
    "evidence_refs": ["pattern-ev-proof-a", "pattern-ev-proof-b"],
    "confidence": 0.89,
    "uncertainties": []
  },
  "creator": {
    "creator_personas": [
      "student_lifestyle_creator",
      "practical_home_creator",
      "travel_lifestyle_creator"
    ],
    "delivery_styles": [
      "casual_first_person_review",
      "situational_demonstration"
    ],
    "face_presence_preference": "optional",
    "speaking_preference": "recommended",
    "emotion_range": [
      "mild frustration",
      "relief",
      "practical satisfaction"
    ],
    "pacing_preference": "conversational_fast",
    "authenticity_cues": [
      "specific situation",
      "natural wording",
      "hands-on use",
      "observable proof"
    ],
    "sales_language_intensity": "low_to_medium",
    "creator_constraints": [
      "Do not perform exaggerated surprise.",
      "Do not claim universal results."
    ],
    "evidence_refs": ["pattern-ev-creator-a", "pattern-ev-creator-b"],
    "confidence": 0.79,
    "uncertainties": [
      "Creator persona fit has not been validated by performance data."
    ]
  },
  "editing": {
    "pacing": "fast_but_readable",
    "cut_density": "medium_high",
    "first_three_second_cut_guidance": "One or two purposeful cuts; do not hide the product reveal.",
    "caption_density": "medium",
    "transition_types": [
      "direct_cut",
      "match_cut_to_result"
    ],
    "pattern_interrupt_guidance": [
      "macro problem close-up",
      "quick product hand-entry"
    ],
    "dead_air_tolerance": "low",
    "visual_safe_zone_guidance": [
      "Keep product-tag and key overlay clear of TikTok UI zones."
    ],
    "evidence_refs": ["pattern-ev-editing-a", "pattern-ev-editing-b"],
    "confidence": 0.82,
    "uncertainties": []
  },
  "offer": {
    "offer_required": false,
    "offer_types": [
      "optional_launch_discount",
      "value_without_discount"
    ],
    "offer_positioning_pattern": "Proof must appear before offer language.",
    "offer_timing_guidance": "After observable proof and before CTA.",
    "urgency_policy": "Use only seller-authorized urgency.",
    "price_display_policy": "Display only verified price or discount.",
    "commerce_constraints": [
      "Do not invent stock scarcity.",
      "Do not invent shipping speed."
    ],
    "evidence_refs": [],
    "confidence": 0.43,
    "uncertainties": [
      "The source cluster does not contain consistent offer evidence."
    ]
  },
  "cta": {
    "cta_required": true,
    "cta_types": [
      "tiktok_shop_product_tag",
      "low_pressure_shop_prompt"
    ],
    "modalities": [
      "spoken",
      "platform_product_tag"
    ],
    "product_tag_expectation": "required_for_tiktok_shop_objective",
    "cta_timing_guidance": "After proof, before the final two seconds when possible.",
    "cta_language_pattern": "Reference the product tag naturally; avoid unrelated urgency.",
    "cta_failure_modes": [
      "generic 'check it out' without product-tag cue",
      "CTA before the result is visible",
      "unsupported discount claim"
    ],
    "evidence_refs": ["pattern-ev-cta-a"],
    "confidence": 0.72,
    "uncertainties": [
      "CTA evidence comes from one of two source assets."
    ]
  },
  "applicability": {
    "suitable_categories": [
      "portable_garment_care",
      "lint_removal",
      "home_organization",
      "cleaning_tools",
      "visual_transformation_gadgets"
    ],
    "unsuitable_categories": [
      "products_without_observable_use",
      "services",
      "products_requiring_long_term_outcomes"
    ],
    "required_product_traits": [
      "visible problem",
      "safe in-use demonstration",
      "observable short-form result"
    ],
    "preferred_product_traits": [
      "compact form factor",
      "low setup time",
      "clear product handling"
    ],
    "buyer_contexts": [
      "time pressure",
      "small space",
      "travel",
      "practical convenience"
    ],
    "markets": ["US"],
    "platforms": ["tiktok_shop"],
    "objectives": [
      "organic_test",
      "affiliate_test",
      "small_paid_test"
    ],
    "fulfillment_constraints": [
      "Use only seller-authorized shipping language."
    ],
    "compliance_sensitivities": [
      "speed claims",
      "universal result claims",
      "safety claims"
    ],
    "pod_context": null,
    "dropshipping_context": {
      "visual_demo_required": true,
      "trust_mechanisms": [
        "same-item proof",
        "creator hands-on use"
      ],
      "shipping_promise_constraints": [
        "Do not imply immediate delivery."
      ],
      "quality_proof_requirements": [
        "Show actual product operation."
      ],
      "margin_or_offer_constraints": [
        "Use only verified price and seller-authorized discount."
      ],
      "claim_risks": [
        "instant result",
        "universal compatibility"
      ]
    }
  },
  "adaptation_instructions": [
    {
      "element_path": "narrative.progression",
      "instruction_type": "keep",
      "instruction": "Keep the problem → early reveal → in-use demo → observable result sequence.",
      "rationale": "This is the reusable structural mechanism supported by both source assets.",
      "severity": "high"
    },
    {
      "element_path": "opening.hook_text",
      "instruction_type": "change",
      "instruction": "Write a new product- and buyer-specific opening line.",
      "rationale": "Exact wording belongs to the source creative and is not the reusable mechanism.",
      "severity": "hard"
    },
    {
      "element_path": "proof.execution",
      "instruction_type": "keep",
      "instruction": "Preserve same-item continuity and visible comparison.",
      "rationale": "The pattern depends on observable proof rather than narration alone.",
      "severity": "hard"
    },
    {
      "element_path": "claims.speed",
      "instruction_type": "avoid",
      "instruction": "Avoid instant-result or universal-result language.",
      "rationale": "The source evidence does not support universal timing claims.",
      "severity": "hard"
    }
  ],
  "performance_summary": {
    "evidence_status": "none",
    "asset_count": 0,
    "campaign_count": 0,
    "metrics": [],
    "caveats": [
      "No seller performance data is linked.",
      "This PatternKit represents a reusable structural hypothesis, not a winning pattern."
    ],
    "confidence": "low"
  },
  "overall_confidence": "medium",
  "uncertainties": [
    "Offer strategy is weakly supported by the source cluster.",
    "Creator persona performance is not validated."
  ]
}
```

## 6.4 Required visual presentation

PatternKit UI should show:

```text
SOURCE EVIDENCE
2 reference assets · 11 evidence moments · no linked performance data

REUSABLE STRUCTURE
Problem → Reveal → Demo → Proof → CTA

KEEP
✓ situational problem
✓ product before 2.2s
✓ same-item proof

CHANGE
↻ buyer situation
↻ exact hook wording
↻ creator persona
↻ offer framing

AVOID
✕ competitor script
✕ instant-result claim
✕ unrelated shipping urgency

APPLICABILITY
Best fit: compact products with visible short-form transformation
Not suitable: products with no observable demo
```

---

# 7. Golden ViralKit output

## 7.1 ViralKit objective

```text
Product: SwiftPress Mini Garment Steamer
Platform: TikTok Shop US
Objective: Affiliate test
Primary buyer groups: college student, frequent traveler
Pattern source: Deadline Pressure → Fast Product Reveal → Same-Fabric Proof
```

## 7.2 Pattern match result

```json
{
  "pattern_kit_version_id": "pk-deadline-fast-reveal-proof-v1",
  "match_score": 0.88,
  "applicability_status": "applicable_with_constraints",
  "matched_product_traits": [
    "visible problem",
    "short-form in-use demo",
    "observable result",
    "compact product"
  ],
  "conflicts": [],
  "constraints": [
    "Avoid universal fabric compatibility.",
    "Include seller-required fabric disclosure.",
    "Use authorized 4–6 business day shipping language only if shipping is mentioned."
  ],
  "selection_reason": "The product supports the core same-item transformation mechanism and an early reveal without requiring long-term proof."
}
```

## 7.3 Adaptation plan

### Keep

- visible problem in the opening;
- product reveal before two seconds;
- same-shirt demo and result continuity;
- proof before CTA;
- low-pressure product-tag CTA.

### Change

- reference creator context → US college student/traveler context;
- reference script → new product-specific language;
- reference product → SwiftPress product assets and verified mechanism;
- offer → verified 15% launch discount;
- disclosure → “Results vary by fabric type.”

### Avoid

- copying the competitor sentence;
- “instantly removes every wrinkle”;
- fake countdown or stock scarcity;
- using a different shirt for the after shot;
- claiming sanitation benefits.

## 7.4 Exactly three strategically different concepts

### Concept A — Late for Class Rescue

```json
{
  "id": "late_for_class",
  "name": "Late for Class Rescue",
  "strategic_axis": "time_pressure_for_college_student",
  "diversity_axes": [
    "buyer_persona",
    "hook_mechanism",
    "creator_persona",
    "narrative_structure"
  ],
  "buyer_persona_id": "college_student",
  "buyer_persona_label": "College student in a dorm",
  "buyer_pain": "A wrinkled shirt immediately before class or an event",
  "desired_outcome": "Look presentable without setting up an ironing board",
  "awareness_stage": "problem_aware",
  "creative_angle": "A compact last-minute clothing rescue for dorm life",
  "hook": {
    "hook_type": "situational_problem",
    "spoken_text": "I had ten minutes before class and this shirt looked like it came straight out of my backpack.",
    "overlay_text": null,
    "opening_visual": "Macro close-up of the wrinkled shirt while a phone clock is visible in the background.",
    "target_time_ms": 0,
    "product_present": false,
    "buyer_pain": "last-minute wrinkled clothing"
  },
  "opening_visual": "Wrinkled shirt close-up, then product enters frame before 1.8 seconds.",
  "narrative_structure": "situational_problem_solution_proof",
  "creator_persona": "US college lifestyle creator",
  "delivery_style": "casual first-person demonstration",
  "demo_mechanism": "Steam the same shirt section while keeping the camera close enough to see the fabric.",
  "proof_mechanism": "Return to the same shirt section using similar framing and lighting.",
  "offer_framing": "Mention the verified 15% launch discount only after the result is shown.",
  "cta_strategy": "Natural TikTok Shop product-tag CTA after proof.",
  "claims_to_avoid": [
    "instant result",
    "safe for every fabric",
    "professional dry-cleaning result"
  ],
  "required_disclosures": [
    "Results vary by fabric type."
  ],
  "test_hypothesis": "A time-pressure student scenario will increase relevance and product clicks among college-age viewers without requiring high-pressure sales language.",
  "expected_learning": "Whether urgency from a real dorm situation creates stronger intent than travel or comparison positioning.",
  "feasibility": "high",
  "confidence": "medium"
}
```

### Concept B — Carry-On Clothing Rescue

```json
{
  "id": "carry_on_rescue",
  "name": "Carry-On Clothing Rescue",
  "strategic_axis": "travel_convenience",
  "diversity_axes": [
    "buyer_persona",
    "hook_mechanism",
    "creator_persona",
    "demo_mechanism",
    "narrative_structure"
  ],
  "buyer_persona_id": "frequent_traveler",
  "buyer_persona_label": "Frequent traveler using carry-on luggage",
  "buyer_pain": "Clothing becomes wrinkled inside packed luggage",
  "desired_outcome": "Refresh an outfit in a hotel room with a compact tool",
  "awareness_stage": "solution_aware",
  "creative_angle": "A carry-on-friendly clothing-care backup",
  "hook": {
    "hook_type": "reveal_from_context",
    "spoken_text": "This is why I stopped trusting hotel irons.",
    "overlay_text": "Carry-on clothing rescue",
    "opening_visual": "Open a suitcase and pull out a visibly wrinkled outfit.",
    "target_time_ms": 0,
    "product_present": false,
    "buyer_pain": "wrinkled travel outfit"
  },
  "opening_visual": "Suitcase reveal followed by the product placed beside travel items.",
  "narrative_structure": "travel_problem_tool_demo_result",
  "creator_persona": "US travel creator",
  "delivery_style": "practical travel tip",
  "demo_mechanism": "Use the steamer on one half of a packed shirt in a hotel-room setting.",
  "proof_mechanism": "Show treated and untreated halves in the same frame.",
  "offer_framing": "Optional; value and portability are primary.",
  "cta_strategy": "Product-tag CTA framed as a travel packing recommendation.",
  "claims_to_avoid": [
    "works on every fabric",
    "hotel-safe guarantee",
    "instant result"
  ],
  "required_disclosures": [
    "Results vary by fabric type."
  ],
  "test_hypothesis": "Travel context and side-by-side proof will create stronger saves and comments among frequent travelers than a general convenience demo.",
  "expected_learning": "Whether portability is a stronger purchase driver than time pressure.",
  "feasibility": "medium",
  "confidence": "medium"
}
```

### Concept C — Small-Space Iron Alternative

```json
{
  "id": "small_space_alternative",
  "name": "Small-Space Iron Alternative",
  "strategic_axis": "comparison_and_space_saving",
  "diversity_axes": [
    "hook_mechanism",
    "narrative_structure",
    "demo_mechanism",
    "proof_mechanism",
    "offer_framing"
  ],
  "buyer_persona_id": "small_space_renter",
  "buyer_persona_label": "Apartment renter with limited storage",
  "buyer_pain": "A full-size iron and board take up too much space",
  "desired_outcome": "Keep a compact clothing-care option in a drawer",
  "awareness_stage": "solution_aware",
  "creative_angle": "A compact alternative for quick touch-ups in small spaces",
  "hook": {
    "hook_type": "comparison",
    "spoken_text": "I do not have space for an ironing board, so this lives in my desk drawer.",
    "overlay_text": "No ironing board setup",
    "opening_visual": "Show a crowded closet, then open a drawer containing the compact steamer.",
    "target_time_ms": 0,
    "product_present": true,
    "buyer_pain": "limited storage"
  },
  "opening_visual": "Product is visible immediately inside the drawer.",
  "narrative_structure": "comparison_space_problem_demo_proof",
  "creator_persona": "small-apartment lifestyle creator",
  "delivery_style": "practical comparison review",
  "demo_mechanism": "Show setup time and steam a shirt while the ironing board remains folded away.",
  "proof_mechanism": "Close-up of the treated area plus visual comparison of storage footprint.",
  "offer_framing": "15% launch discount as a secondary value cue.",
  "cta_strategy": "Product-tag CTA after the compact-storage proof.",
  "claims_to_avoid": [
    "replaces professional ironing for every use",
    "instant result",
    "safe for every fabric"
  ],
  "required_disclosures": [
    "Results vary by fabric type."
  ],
  "test_hypothesis": "Immediate product visibility and space-saving comparison will improve product clicks among apartment renters even without a time-pressure story.",
  "expected_learning": "Whether product visibility and storage benefit outperform situational urgency.",
  "feasibility": "high",
  "confidence": "medium"
}
```

## 7.5 Concept comparison visual

```text
                         A: Late for Class   B: Carry-On Rescue   C: Small-Space Alternative
Buyer                    College student     Traveler             Apartment renter
Primary pain             Time pressure       Packed wrinkles      Storage/setup
Hook                     Situational problem Travel reveal        Comparison
Product first seen       <1.8s               <2.2s                0s
Creator                   Student             Travel creator       Home/lifestyle
Demo                      Same-shirt section  Half-shirt compare   Setup + in-use
Proof                     Same-area result    Treated vs untreated Result + footprint
Main metric hypothesis   Product clicks      Saves/comments       Product clicks
```

Acceptance requirements:

- The concepts differ across meaningful axes.
- Buyer persona and creator persona are not merged.
- The same PatternKit mechanism is adapted, not copied.
- Claims and disclosure requirements remain consistent.
- No concept claims predicted GMV or virality.

---

# 8. Golden ViralKit test matrix

```json
{
  "primary_hypothesis": "The same early-reveal and same-item proof pattern will perform differently depending on buyer situation and hook mechanism.",
  "controlled_variables": [
    "product",
    "selling_price",
    "15% launch discount",
    "video length target 18–24 seconds",
    "product-tag CTA",
    "required fabric disclosure"
  ],
  "intentionally_changed_variables": [
    "buyer persona",
    "hook mechanism",
    "creator persona",
    "demo framing",
    "proof framing"
  ],
  "recommended_test_order": [
    "late_for_class",
    "small_space_alternative",
    "carry_on_rescue"
  ],
  "concepts": [
    {
      "concept_id": "late_for_class",
      "hypothesis": "Time pressure creates the strongest immediate purchase intent.",
      "changed_axes": [
        "buyer_persona",
        "hook_mechanism",
        "creator_persona"
      ],
      "held_constant": [
        "product",
        "offer",
        "same-item proof requirement",
        "product tag"
      ],
      "minimum_execution_requirements": [
        "product before 2000ms",
        "same-shirt before and after",
        "required disclosure",
        "product-tag CTA"
      ],
      "metrics_to_observe": [
        "3-second hold rate",
        "product clicks",
        "orders",
        "comments mentioning time or dorm use"
      ]
    },
    {
      "concept_id": "carry_on_rescue",
      "hypothesis": "Travel context creates stronger saves and high-intent comments.",
      "changed_axes": [
        "buyer_persona",
        "hook_mechanism",
        "demo_mechanism"
      ],
      "held_constant": [
        "product",
        "offer",
        "same-item proof requirement",
        "product tag"
      ],
      "minimum_execution_requirements": [
        "suitcase context visible",
        "product before 2300ms",
        "treated vs untreated proof",
        "required disclosure"
      ],
      "metrics_to_observe": [
        "saves",
        "product clicks",
        "comments mentioning travel",
        "orders"
      ]
    },
    {
      "concept_id": "small_space_alternative",
      "hypothesis": "Immediate product visibility and comparison positioning create the strongest click intent.",
      "changed_axes": [
        "hook_mechanism",
        "narrative_structure",
        "proof_mechanism"
      ],
      "held_constant": [
        "product",
        "offer",
        "product tag",
        "required disclosure"
      ],
      "minimum_execution_requirements": [
        "product visible at opening",
        "storage comparison",
        "in-use result",
        "required disclosure"
      ],
      "metrics_to_observe": [
        "product clicks",
        "CTR when paid-tested",
        "orders",
        "comments mentioning storage"
      ]
    }
  ],
  "decision_criteria": [
    {
      "criterion": "Do not compare commercial outcomes unless each concept satisfies its minimum execution requirements.",
      "signal_type": "structural",
      "comparison": "Campaign Pack and Preflight compliance",
      "caveat": "A weak execution cannot fairly test the strategic concept."
    },
    {
      "criterion": "Use product clicks and orders as stronger commerce signals than views alone.",
      "signal_type": "commercial",
      "comparison": "Concept-level rate normalized by exposure and test window",
      "caveat": "Private beta reporting is directional and not a causal claim."
    }
  ]
}
```

---

# 9. Golden Creative Campaign Pack

The selected concept is `late_for_class`.

## 9.1 Human-readable creator view

```text
CREATIVE CAMPAIGN PACK
Product: SwiftPress Mini Garment Steamer
Concept: Late for Class Rescue
Objective: TikTok Shop affiliate test
Target duration: 18–24 seconds

WHO THIS IS FOR
US college students living in dorms or shared apartments who want a compact way to handle wrinkled clothing before class or an event.

CORE ANGLE
A last-minute dorm-room clothing rescue with clear same-shirt proof.

CREATOR STYLE
Casual student lifestyle creator.
Natural first-person delivery.
Do not sound like a commercial voice-over.

MANDATORY OPENING
Start on a visibly wrinkled shirt.
The product must be clearly visible by 00:02.000.

HOOK OPTIONS
1. Spoken: “I had ten minutes before class and this shirt looked like it came straight out of my backpack.”
   Opening visual: wrinkled shirt close-up with a phone clock in the background.
   Mandatory: yes

2. Spoken: “Dorm-room problem: no ironing board and a shirt I cannot wear like this.”
   Opening visual: show the small dorm space before revealing the product.
   Mandatory: no

3. Overlay: “Last-minute outfit rescue”
   Opening visual: shirt first, product enters frame quickly.
   Mandatory: no

Important: A spoken hook does not need to appear as an overlay unless the selected hook explicitly includes overlay text.

REQUIRED STORY
1. Show the wrinkled shirt problem.
2. Reveal the product before two seconds.
3. Steam one clearly visible section of the same shirt.
4. Return to that same section and show the result.
5. Mention or display: “Results vary by fabric type.”
6. End with a natural TikTok Shop product-tag CTA.

MUST SHOW
- Clear product close-up.
- Product operating on the shirt.
- Same-shirt before and after.
- TikTok Shop product tag.
- Required disclosure.

DO
- Keep the same shirt and similar lighting for proof.
- Speak naturally from personal experience.
- Keep the product visible during the main demo.
- Show the result before mentioning the discount.

DO NOT
- Say it removes every wrinkle instantly.
- Say it is safe for every fabric.
- Claim sanitation or bacteria removal.
- Use a different shirt in the result shot.
- Invent stock scarcity or faster shipping.

OFFER
Verified 15% launch discount.
Mention only after the result is visible.

CTA
Spoken direction: “I linked the one I use in the product tag.”
Product tag: required.
Target CTA window: 00:16.000–00:22.000.

RIGHTS REQUEST
Please confirm permission for TikTok organic use, Spark Ads testing, and editing of the submitted cut. Raw footage is preferred but not required for this test.

REVISION CHECKLIST
- Product appears by two seconds.
- Same-shirt proof is visible.
- Disclosure is present.
- Product tag is present.
- No prohibited claim is used.
```

## 9.2 Typed brief highlights

```json
{
  "objective": "tiktok_shop_affiliate_test",
  "audience": {
    "buyer_persona_id": "college_student",
    "persona_label": "US college student in a dorm or shared apartment",
    "pain_points": [
      "last-minute wrinkled clothing",
      "limited space for ironing equipment"
    ],
    "desired_outcomes": [
      "look presentable quickly",
      "use a compact clothing-care tool"
    ]
  },
  "creator_direction": {
    "persona": "US college lifestyle creator",
    "delivery_style": "casual first-person demonstration",
    "tone": ["natural", "specific", "practical"],
    "avoid_tones": ["overhyped", "commercial announcer", "guaranteed result"]
  },
  "cta": {
    "spoken": "I linked the one I use in the product tag.",
    "overlay": null,
    "cta_type": "product_tag",
    "product_tag_required": true,
    "required_before_ms": 22000
  },
  "claim_guardrails": {
    "allowed": [
      "Helps reduce visible wrinkles",
      "Compact for quick touch-ups"
    ],
    "allowed_with_qualification": [
      {
        "claim": "Quick wrinkle reduction",
        "qualification": "Show actual same-shirt proof and avoid instant wording."
      }
    ],
    "prohibited": [
      "Removes every wrinkle instantly",
      "Safe for every fabric",
      "Kills bacteria",
      "Professional dry-cleaning results"
    ],
    "required_disclosures": [
      "Results vary by fabric type."
    ]
  }
}
```

---

# 10. Golden compiled Preflight requirements

```json
[
  {
    "id": "product_visible_by_2s",
    "requirement_type": "product",
    "source_path": "storyboard[1].product_visibility_required",
    "description": "The target product must be clearly visible by 00:02.000.",
    "severity": "hard",
    "matcher_type": "product_visibility_timing",
    "matcher_config": {
      "before_ms": 2000
    },
    "expected_semantics": "timing"
  },
  {
    "id": "target_product_match",
    "requirement_type": "product",
    "source_path": "product_snapshot.identity",
    "description": "The UGC must show the SwiftPress Mini Garment Steamer, not a different steamer.",
    "severity": "hard",
    "matcher_type": "product_match",
    "matcher_config": {
      "minimum_confidence": 0.70
    },
    "expected_semantics": "type_match"
  },
  {
    "id": "same_shirt_demo",
    "requirement_type": "demo",
    "source_path": "storyboard[2]",
    "description": "The creator must steam the same shirt section shown in the problem opening.",
    "severity": "high",
    "matcher_type": "demo_mechanism_match",
    "matcher_config": {
      "text": "same-shirt section steamed in use"
    },
    "expected_semantics": "semantic_match"
  },
  {
    "id": "same_shirt_proof",
    "requirement_type": "proof",
    "source_path": "proof_direction[0]",
    "description": "The same shirt section must be shown after use with an observable visible result.",
    "severity": "high",
    "matcher_type": "proof_type_match",
    "matcher_config": {
      "proof_type": "same_item_before_after"
    },
    "expected_semantics": "type_match"
  },
  {
    "id": "fabric_disclosure",
    "requirement_type": "claim_governance",
    "source_path": "claim_guardrails.required_disclosures[0]",
    "description": "The disclosure 'Results vary by fabric type.' must appear in spoken or on-screen text.",
    "severity": "hard",
    "matcher_type": "required_disclosure_presence",
    "matcher_config": {
      "text": "Results vary by fabric type."
    },
    "expected_semantics": "presence"
  },
  {
    "id": "no_instant_claim",
    "requirement_type": "claim_governance",
    "source_path": "claim_guardrails.prohibited[0]",
    "description": "The UGC must not claim that every wrinkle is removed instantly.",
    "severity": "hard",
    "matcher_type": "prohibited_claim_absence",
    "matcher_config": {
      "text": "removes every wrinkle instantly"
    },
    "expected_semantics": "absence"
  },
  {
    "id": "product_tag_required",
    "requirement_type": "cta",
    "source_path": "cta.product_tag_required",
    "description": "A TikTok Shop product tag must be present.",
    "severity": "hard",
    "matcher_type": "product_tag_presence",
    "matcher_config": {},
    "expected_semantics": "presence"
  },
  {
    "id": "cta_by_22s",
    "requirement_type": "cta",
    "source_path": "cta.required_before_ms",
    "description": "The CTA must begin no later than 00:22.000.",
    "severity": "high",
    "matcher_type": "cta_timing",
    "matcher_config": {
      "before_ms": 22000
    },
    "expected_semantics": "timing"
  }
]
```

---

# 11. Golden UGC Preflight — first draft

## 11.1 Observed draft

```text
Duration: 22.7 seconds
Product first clearly appears: 4.2 seconds
Creator delivery: natural
Demo: product is used, but the original shirt area is not shown again
Proof: steam is visible; wrinkle result is unclear
CTA: product tag appears at 18.8 seconds
Disclosure: missing
Claims: no prohibited instant claim detected
```

## 11.2 Structural score

```json
{
  "overall_score": 74,
  "band": "revise",
  "dimensions": [
    {
      "name": "hook_clarity",
      "score": 82,
      "reason": "The creator states a specific last-minute clothing problem immediately.",
      "confidence": "high",
      "evidence_ids": ["draft-hook-01"]
    },
    {
      "name": "product_visibility",
      "score": 55,
      "reason": "The product is clearly shown, but its first appearance at 4.2 seconds is late for this brief.",
      "confidence": "high",
      "evidence_ids": ["draft-product-01"]
    },
    {
      "name": "demo_clarity",
      "score": 76,
      "reason": "The product is shown in use on the shirt, but continuity with the opening problem area is incomplete.",
      "confidence": "medium",
      "evidence_ids": ["draft-demo-01"]
    },
    {
      "name": "proof_strength",
      "score": 42,
      "reason": "Steam is visible, but the draft does not show an observable same-shirt result.",
      "confidence": "high",
      "evidence_ids": ["draft-proof-summary-01"]
    },
    {
      "name": "creator_authenticity",
      "score": 88,
      "reason": "The delivery is natural, specific, and consistent with the requested student persona.",
      "confidence": "medium",
      "evidence_ids": ["draft-creator-01"]
    },
    {
      "name": "offer_clarity",
      "score": 68,
      "reason": "The 15% discount is stated after the demonstration, but the result is not yet strong enough to support the offer sequence.",
      "confidence": "medium",
      "evidence_ids": ["draft-offer-01"]
    },
    {
      "name": "cta_readiness",
      "score": 92,
      "reason": "The product-tag CTA is present at 18.8 seconds and clearly tied to the product.",
      "confidence": "high",
      "evidence_ids": ["draft-cta-01"]
    },
    {
      "name": "tiktok_native_fit",
      "score": 84,
      "reason": "Vertical framing, creator-led delivery, and pacing fit the platform context.",
      "confidence": "medium",
      "evidence_ids": ["draft-platform-01"]
    },
    {
      "name": "claim_safety",
      "score": 72,
      "reason": "No prohibited instant-result claim was observed, but required disclosure coverage is missing.",
      "confidence": "medium",
      "evidence_ids": ["draft-text-coverage-01"]
    }
  ]
}
```

## 11.3 Exact alignment evaluations

```json
[
  {
    "requirement_id": "product_visible_by_2s",
    "status": "missing",
    "score": 0,
    "confidence": "high",
    "reason": "The first clear product appearance occurs after the required deadline.",
    "expected": {
      "before_ms": 2000
    },
    "observed": {
      "first_appearance_ms": 4200
    },
    "evidence_ids": ["draft-product-01"]
  },
  {
    "requirement_id": "target_product_match",
    "status": "satisfied",
    "score": 100,
    "confidence": "high",
    "reason": "The observed product matches the attached SwiftPress product assets.",
    "expected": {
      "minimum_confidence": 0.70
    },
    "observed": {
      "product_match_confidence": 0.93
    },
    "evidence_ids": ["draft-product-match-01"]
  },
  {
    "requirement_id": "same_shirt_demo",
    "status": "partial",
    "score": 65,
    "confidence": "medium",
    "reason": "The product is used on the shirt, but the system cannot verify that the exact opening section is preserved through the demo.",
    "expected": {
      "mechanism": "same-shirt section steamed in use"
    },
    "observed": {
      "product_in_use": true,
      "same_section_continuity": "uncertain"
    },
    "evidence_ids": ["draft-demo-01"]
  },
  {
    "requirement_id": "same_shirt_proof",
    "status": "missing",
    "score": 0,
    "confidence": "high",
    "reason": "No same-item before/after proof is observed after the demonstration.",
    "expected": {
      "proof_type": "same_item_before_after"
    },
    "observed": {
      "proof_types": ["steam_visibility_only"]
    },
    "evidence_ids": ["draft-proof-summary-01"]
  },
  {
    "requirement_id": "fabric_disclosure",
    "status": "missing",
    "score": 0,
    "confidence": "high",
    "reason": "The required disclosure was not found in transcript or OCR evidence.",
    "expected": {
      "text": "Results vary by fabric type."
    },
    "observed": {
      "eligible_text_sources": 9,
      "matched": false
    },
    "evidence_ids": []
  },
  {
    "requirement_id": "no_instant_claim",
    "status": "satisfied",
    "score": 100,
    "confidence": "medium",
    "reason": "The prohibited instant-result claim was not observed in available transcript and OCR evidence.",
    "expected": {
      "semantics": "absence",
      "text": "removes every wrinkle instantly"
    },
    "observed": {
      "available_text_sources": 9,
      "coverage": "medium"
    },
    "evidence_ids": []
  },
  {
    "requirement_id": "product_tag_required",
    "status": "satisfied",
    "score": 100,
    "confidence": "high",
    "reason": "A product tag is visible during the CTA window.",
    "expected": {
      "product_tag_required": true
    },
    "observed": {
      "product_tag_present": true,
      "start_ms": 18800
    },
    "evidence_ids": ["draft-cta-01"]
  },
  {
    "requirement_id": "cta_by_22s",
    "status": "satisfied",
    "score": 100,
    "confidence": "high",
    "reason": "The CTA begins before the 22-second deadline.",
    "expected": {
      "before_ms": 22000
    },
    "observed": {
      "cta_start_ms": 18800
    },
    "evidence_ids": ["draft-cta-01"]
  }
]
```

## 11.4 Final Preflight output

```json
{
  "structural_score": 74,
  "brief_alignment_score": 57,
  "final_score": 71,
  "action": "revise",
  "confidence": "high",
  "hard_blockers": [
    {
      "code": "PRODUCT_REVEAL_LATE",
      "message": "Product appears at 4.2 seconds; the Campaign Pack requires visibility by 2.0 seconds.",
      "evidence_ids": ["draft-product-01"]
    },
    {
      "code": "REQUIRED_DISCLOSURE_MISSING",
      "message": "The required fabric-result disclosure is missing.",
      "evidence_ids": []
    }
  ],
  "high_priority_fixes": [
    {
      "code": "SAME_ITEM_PROOF_MISSING",
      "instruction": "Return to the exact shirt section shown in the opening and hold the result long enough for comparison.",
      "evidence_ids": ["draft-proof-summary-01"]
    }
  ],
  "strengths": [
    "Natural student-creator delivery",
    "Clear product-tag CTA",
    "Platform-native pacing"
  ],
  "creator_revision_message": "The student setup and delivery feel natural, and the product-tag ending works well. Please move the product close-up into the first two seconds, return to the exact shirt section after steaming so the result is visible, and add the on-screen or spoken disclosure: ‘Results vary by fabric type.’ Keep the current tone and CTA.",
  "next_action": "Upload a revised version and rerun Preflight before paid use."
}
```

---

# 12. Golden revision comparison

## 12.1 Revised observations

```text
Draft 1 product reveal: 4.2s
Draft 2 product reveal: 1.4s

Draft 1 proof: steam only
Draft 2 proof: same-shirt result held for 2.6s

Draft 1 disclosure: missing
Draft 2 disclosure: OCR text from 15.2s to 18.0s

CTA: preserved in both versions
Creator style: preserved
```

## 12.2 Revision diff output

```json
{
  "from_asset_version_id": "ugc-draft-v1",
  "to_asset_version_id": "ugc-draft-v2",
  "resolved": [
    {
      "issue": "PRODUCT_REVEAL_LATE",
      "before": {
        "first_appearance_ms": 4200
      },
      "after": {
        "first_appearance_ms": 1400
      }
    },
    {
      "issue": "SAME_ITEM_PROOF_MISSING",
      "before": {
        "proof_type": "steam_visibility_only"
      },
      "after": {
        "proof_type": "same_item_before_after",
        "proof_duration_ms": 2600
      }
    },
    {
      "issue": "REQUIRED_DISCLOSURE_MISSING",
      "before": {
        "present": false
      },
      "after": {
        "present": true,
        "text": "Results vary by fabric type.",
        "start_ms": 15200,
        "end_ms": 18000
      }
    }
  ],
  "preserved_strengths": [
    "creator authenticity",
    "product-tag CTA",
    "platform-native pacing"
  ],
  "new_issues": [],
  "summary": "All mandatory revision blockers were resolved without removing the strongest creator and CTA signals."
}
```

## 12.3 Revised Preflight

```json
{
  "structural_score": 86,
  "brief_alignment_score": 93,
  "final_score": 87,
  "action": "small_paid_test",
  "confidence": "high",
  "hard_blockers": [],
  "strengths": [
    "Product appears at 1.4 seconds",
    "Same-shirt proof is observable",
    "Required disclosure is present",
    "Product-tag CTA is clear",
    "Creator delivery remains natural"
  ],
  "remaining_caveats": [
    "Structural readiness does not guarantee sales performance.",
    "Confirm Spark and editing rights before paid amplification."
  ],
  "next_action": "Approve for organic posting and a limited paid test after rights confirmation."
}
```

---

# 13. Golden recommendation output

```json
{
  "schema_version": "recommendation_v2",
  "action": "small_paid_test",
  "title": "Approve structure; confirm rights before Spark testing",
  "reason": "The revised video satisfies all hard Campaign Pack requirements and resolves the original product-timing, proof, and disclosure blockers.",
  "confidence": "high",
  "evidence": [
    {
      "statement": "Product appears at 1.4 seconds.",
      "evidence_ids": ["v2-product-first-01"]
    },
    {
      "statement": "Same-shirt before/after proof is visible.",
      "evidence_ids": ["v2-proof-01"]
    },
    {
      "statement": "Required disclosure is present.",
      "evidence_ids": ["v2-disclosure-01"]
    },
    {
      "statement": "Product-tag CTA begins before the deadline.",
      "evidence_ids": ["v2-cta-01"]
    }
  ],
  "blockers": [],
  "conditions": [
    "Confirm TikTok organic usage rights.",
    "Confirm Spark Ads authorization.",
    "Confirm editing permission for the approved cut."
  ],
  "next_steps": [
    "Publish organically or through the planned affiliate workflow.",
    "Run a limited paid test only after rights are complete.",
    "Attach views, product clicks, orders, GMV, and test dates to this asset after the test."
  ],
  "disclaimer": "This recommendation evaluates structural and brief readiness. It is not a guarantee of virality, GMV, ROAS, or sales."
}
```

---

# 14. Seller action and feedback capture

## 14.1 Seller action

```json
{
  "recommendation_id": "rec-steamer-v2",
  "action": "accepted",
  "reason": "The team agrees the required revisions are complete and will use the video for organic affiliate posting first.",
  "created_by": "seller-user-id",
  "created_at": "2026-08-12T09:00:00Z"
}
```

## 14.2 Field-level correction example

```json
{
  "subject_type": "creative_dna",
  "subject_id": "dna-ugc-v2",
  "field_path": "creator.persona",
  "feedback_type": "partial",
  "ai_value_json": {
    "value": "college_lifestyle_creator"
  },
  "user_value_json": {
    "value": "general_lifestyle_creator_with_student_setting"
  },
  "comment": "The setting is student-focused, but the creator's channel is not primarily college content.",
  "model_run_id": "model-run-v2",
  "created_by": "seller-user-id"
}
```

Learning rule:

- preserve the original inference;
- store the correction separately;
- use the corrected label in evaluation and future workspace-private learning only when appropriate.

---

# 15. Golden performance-learning response after testing

Assume the seller later imports directional performance data.

```text
Concept A — Late for Class
Views: 31,400
Product clicks: 1,180
Orders: 42
GMV: $1,259.58

Concept C — Small-Space Alternative
Views: 28,900
Product clicks: 1,460
Orders: 37
GMV: $1,109.63
```

Viraldy-grade response:

```json
{
  "analysis_status": "directional",
  "summary": "Late for Class generated more orders, while Small-Space Alternative generated more product clicks relative to views. The available sample is not sufficient to declare a universally winning pattern.",
  "observations": [
    {
      "finding": "Late for Class produced the higher observed order count and GMV in this test window.",
      "evidence": {
        "concept_id": "late_for_class",
        "orders": 42,
        "gmv": 1259.58
      },
      "confidence": "medium"
    },
    {
      "finding": "Small-Space Alternative produced the higher observed product-click rate.",
      "evidence": {
        "concept_id": "small_space_alternative",
        "product_clicks": 1460,
        "views": 28900
      },
      "confidence": "medium"
    }
  ],
  "diagnosis": [
    "Time-pressure positioning may be stronger for immediate order intent in this sample.",
    "Space-saving comparison may create strong curiosity and product exploration but needs offer or page validation before concluding it is weaker commercially."
  ],
  "recommended_actions": [
    {
      "action": "create_variant",
      "instruction": "Create a second Late for Class variant with a different student creator while preserving the same proof mechanism.",
      "reason": "Test whether the observed order signal is tied to the angle rather than one creator execution."
    },
    {
      "action": "fix_and_retest",
      "instruction": "Retest Small-Space Alternative with clearer price-value framing after the proof.",
      "reason": "The concept generated strong product-click behavior but fewer observed orders."
    }
  ],
  "pattern_update": {
    "pattern_kit_version_id": "pk-deadline-fast-reveal-proof-v1",
    "performance_evidence_status": "directional",
    "do_not_promote_to_supported": true,
    "reason": "The sample contains too few independent campaign executions."
  },
  "caveats": [
    "The test is observational and may be affected by creator, posting time, distribution, product page, and audience differences.",
    "Do not interpret the result as causal proof."
  ]
}
```

---

# 16. Golden scenario B — POD personalization

## 16.1 Product

```text
Product: Personalized Dog Mom Crewneck
Market: US
Buyer: Dog owner buying for herself or as a gift
Personalization: Pet name and breed illustration
Primary value: Identity, emotional connection, giftability
Main risks: Misspelled name, wrong breed, misleading mockup, delivery-date promise
```

## 16.2 POD-specific PatternKit

```text
Identity Hook → Personalization Reveal → Emotional Payoff → Ordering Clarity
```

Reusable structure:

1. Show the identity or recipient context immediately.
2. Reveal the personalized detail clearly.
3. Show an emotional reaction or identity payoff.
4. Explain ordering/personalization simply.
5. Use an accurate delivery statement and product-tag CTA.

Keep:

- identity-led hook;
- close-up personalization reveal;
- recipient or self-purchase payoff;
- ordering clarity.

Change:

- recipient;
- occasion;
- pet name/breed;
- creator relationship;
- exact emotional line.

Avoid:

- copying customer names from references;
- showing a mockup that differs from the delivered item;
- promising an arrival date without authorized fulfillment data;
- using a generic “perfect gift for everyone” claim.

## 16.3 POD ViralKit concepts

### Concept A — Dog Mom Identity

- Buyer: self-purchase dog owner.
- Creator: dog-owner lifestyle creator.
- Hook: “Tell me you are a dog mom without telling me.”
- Reveal: pet name and breed illustration close-up.
- Proof: creator wears the delivered product next to the pet.
- Hypothesis: identity recognition drives saves and product clicks.

### Concept B — Gift Reaction

- Buyer: friend or partner buying a birthday/Mother’s Day gift.
- Creator: gifting/lifestyle creator.
- Hook: recipient reaction before full product explanation.
- Reveal: personalized detail after the reaction setup.
- Proof: recipient verifies pet name and illustration.
- Hypothesis: emotional payoff drives shares and order intent.

### Concept C — How Personalization Works

- Buyer: product-aware shopper uncertain about ordering.
- Creator: practical tutorial creator.
- Hook: “Here is exactly what you submit to make yours.”
- Reveal: input → preview → delivered product.
- Proof: submitted pet details match the delivered item.
- Hypothesis: ordering clarity reduces hesitation and increases product clicks.

## 16.4 POD Preflight requirements

- personalized name matches Product Context/order data;
- breed or illustration matches approved asset;
- delivered product, not only digital mockup, is shown when required;
- personalization detail is readable;
- ordering steps are not misleading;
- delivery promise matches authorized fulfillment information;
- product tag is present;
- creator does not expose private customer information without consent.

Golden output example:

```text
Action: Revise

Hard blocker
- The Campaign Pack requires the personalized name “Milo”.
- OCR detects “Miles” on the visible product detail.
- Expected: Milo
- Observed: Miles
- Evidence: personalization_ocr_12 at 00:07.200–00:09.600

High-priority fix
- Replace the incorrect product sample or reshoot the personalization close-up with the approved “Milo” version.

Do not approve this asset even though the hook and creator reaction are strong.
```

---

# 17. Golden scenario C — Dropshipping visual-demo product

## 17.1 Product

```text
Product: Rechargeable Mini Bag Sealer
Market: US
Buyer: students, families, and snack buyers
Primary problem: opened snack bags become stale or spill
Observable mechanism: device applies heat to reseal supported plastic packaging
Shipping promise: seller-authorized 7–10 business days
Main risks: unsupported airtight guarantee, food-safety guarantee, universal plastic compatibility, fast-shipping promise
```

## 17.2 Dropshipping-specific PatternKit

```text
Mess Interruption → One-Handed Demo → Leak/Seal Proof → Trust Cue
```

Required product traits:

- visible physical mechanism;
- safe short-form demonstration;
- observable seal result;
- trust cue that does not overclaim food preservation.

Keep:

- visible bag problem;
- product in hand early;
- one-use demo;
- observable seal test.

Change:

- snack type;
- user context;
- creator persona;
- exact proof setup;
- offer framing.

Avoid:

- “keeps food fresh forever”;
- “completely airtight” unless verified;
- implying suitability for every packaging material;
- claiming immediate delivery.

## 17.3 Dropshipping ViralKit concepts

### Concept A — Dorm Snack Fix

- buyer: college student;
- hook: spilled chips in a backpack;
- demo: seal the bag before putting it back;
- proof: turn bag upside down briefly under safe conditions;
- CTA: product tag.

### Concept B — Family Pantry Routine

- buyer: parent organizing opened snack bags;
- hook: pantry full of clips and rolled bags;
- demo: seal three common bag types that are verified as supported;
- proof: close-up seal line;
- CTA: value and convenience.

### Concept C — Travel Packing

- buyer: traveler packing snacks;
- hook: avoid clips opening inside a carry-on;
- demo: compact product and one-handed use;
- proof: bag remains closed during packing demonstration;
- CTA: travel utility.

## 17.4 Dropshipping Preflight response example

```text
Action: Revise before posting

Hard blocker
- Spoken line at 00:08.900 says: “This makes every bag completely airtight.”
- Product governance prohibits universal airtight claims.
- Evidence: asr_claim_19.

Observed strength
- The one-handed demo is clear.
- Product appears at 1.1 seconds.
- The seal line is visible in close-up.

Required revision
Replace the claim with:
“I use it to reseal supported snack bags after opening.”

Shipping note
No shipping claim is present. Do not add faster shipping language than the authorized 7–10 business day promise.
```

---

# 18. UI output hierarchy

Viraldy should not display one giant AI paragraph.

## 18.1 Top decision card

```text
REVISE BEFORE PAID USE
Final score: 71
Confidence: High
2 hard blockers · 1 high-priority fix
```

## 18.2 Evidence timeline

```text
0s        2s        5s        10s       15s       20s
| Hook | late product | demo | no proof | offer | CTA |
```

Clicking a segment opens:

- video frame;
- transcript/OCR;
- observed value;
- expected value;
- evidence confidence.

## 18.3 Expected vs observed

```text
Requirement             Expected             Observed             Status
Product reveal          ≤2.0s                4.2s                 Missing
Same-item proof         Required             Not observed         Missing
Disclosure              Required             Not found            Missing
Product tag              Required             18.8s                Satisfied
```

## 18.4 Revision priority

```text
MUST FIX
1. Product timing
2. Required disclosure

SHOULD FIX
3. Same-shirt proof

KEEP
- Creator delivery
- Product-tag CTA
- Pacing
```

## 18.5 PatternKit visual

- source assets;
- evidence-backed sequence;
- keep/change/avoid;
- applicability;
- performance evidence state;
- confidence and uncertainty.

## 18.6 ViralKit visual

- three concept cards;
- differences highlighted by strategic axis;
- controlled vs changed variables;
- concept selection action;
- Campaign Pack status;
- Preflight requirement readiness.

---

# 19. Codex fixture and automated acceptance requirements

Codex must create deterministic fixture data that produces outputs equivalent in meaning to the golden examples.

Required fixture scenarios:

```text
home_travel_steamer
pod_dog_mom_crewneck
dropshipping_bag_sealer
```

Required test assets:

```text
reference_good_structure
ugc_missing_product_timing
ugc_missing_proof
ugc_missing_disclosure
ugc_prohibited_claim
ugc_revision_resolves_all
no_audio_video
```

Required assertions:

## Product Context

- missing facts remain unknown;
- projection fields stay synchronized;
- claim guardrails survive snapshots.

## Creative DNA

- no product-match result without attached Product Context;
- no offer is invented;
- spoken and overlay CTA remain separate;
- every observed field has evidence;
- category-specific observations do not leak across fixtures.

## PatternKit

- at least one source DNA version is required;
- multi-asset cluster requires at least two sources;
- sequence is contiguous;
- exact competitor wording is not emitted as a keep instruction;
- no `winning` label without performance evidence;
- POD and dropshipping applicability fields remain distinct;
- version and provenance are immutable.

## ViralKit

- exactly three concepts;
- each concept differs from every other concept across at least two axes;
- buyer and creator personas remain separate;
- all claims and disclosures are preserved;
- concepts violating product constraints are rejected;
- selected concept action is stored separately;
- Campaign Pack is produced through the Campaign Pack public service.

## Campaign Pack

- spoken hook does not automatically become overlay;
- product timing compiles to exact matcher;
- required disclosure compiles to presence matcher;
- prohibited claim compiles to absence matcher;
- product-tag and CTA timing compile separately;
- buyer audience and creator direction are not mixed.

## Scorer

- no LLM-generated scores;
- timing points only apply when timing is satisfied;
- claim absence confidence reflects evidence coverage;
- hard blockers override score bands.

## Preflight

- product at 4.2s fails a 2.0s requirement;
- generic demo score cannot satisfy an exact same-item proof requirement;
- missing disclosure is a hard blocker;
- prohibited claim detection returns violated;
- unknown hard requirement cannot approve;
- revision resolves exact blockers and preserves strengths.

## Recommendation

- action, reason, evidence, confidence, conditions, and next steps are present;
- seller action is stored separately;
- structural readiness disclaimer is present.

---

# 20. Final product quality statement

The desired Viraldy experience is:

```text
The system understands the seller's actual product,
shows exactly what it observed,
explains the mismatch between brief and execution,
produces a creator-ready action,
and stores what the seller decided and what happened next.
```

Viraldy is not successful because the response sounds intelligent.

Viraldy is successful when:

- a seller can use the Campaign Pack without rewriting it;
- a creator can execute the revision without another clarification call;
- a reviewer agrees with the main blockers;
- the seller changes or confirms a real decision;
- the next test is informed by stored evidence and outcomes.

