# Viraldy Creative Domain Intelligence Audit

Date: 2026-07-29
Branch: `hardening/keyless-product-hardening`

## Current Status

The creative-domain hardening pass is implemented and verified locally across fixture mode and mock-provider HTTP mode.

This audit is the handoff file to give ChatGPT or another planner for the next planning pass. The original execution contract is `VIRALDY_CREATIVE_DOMAIN_INTELLIGENCE_HARDENING_GOAL.md`.

## Implemented

- Added versioned schema constants for product context, media observation, evidence, Creative DNA, TikTok score, adaptation, Campaign Pack brief, preflight, and recommendations.
- Added `ProductContextV1` with identity, personas, benefits, features, commercial context, creative context, and governance.
- Added migration `0004_creative_domain_contracts` for typed JSONB schema/version columns and product/run snapshots.
- Backfilled seeded products into valid `product_context_v1` without putting unknown facts into old metadata only.
- Added `MediaObservationBundleV1` covering hook, product visibility, demo, proof, CTA, offer, creator, editing, claims, platform, and uncertainties.
- Added discriminated `evidence_v1` payloads and evidence validation before persistence.
- Replaced shared fixed evidence rows with typed rows derived from fixture/provider observations.
- Added `CreativeDnaV1` builder from typed evidence, with field-level status/confidence/evidence IDs.
- Replaced fixed TikTok scoring with `TikTokScoreResultV2`, signal-driven dimensions, blockers, fixes, strengths, rubric/rule versions, and deterministic final action.
- Added `AdaptationOutputV2`, product snapshots, evidence-backed guidance, exactly-three-concepts validation, and concept-diversity checks.
- Replaced arbitrary Campaign Pack `brief_json` request flow with `CampaignPackBriefV1` validation and immutable product/requirements snapshots.
- Added preflight compiled requirements and `ugc_preflight_v2` requirement-by-requirement evaluation.
- Updated recommendation payload writes to `recommendation_v2`.
- Updated frontend MVP flow route to render typed DNA, score dimensions/signals, adaptation concepts, campaign brief sections, and preflight requirement coverage.
- Updated local seed data and mock provider to cover home organization, beauty tool, POD personalized gift, pet accessory, fashion accessory, and edge scenarios.

## Important Fix Found During Audit

The first mock-provider category sweep exposed an OCR leak: non-home mock video rows still received `Counter clutter fix` as on-screen text because OCR extraction did not receive product context and the mock provider defaulted to the home scenario.

Fix applied:

- `LiveAnalysisProvider.extract_ocr_with_response` now accepts optional product context in the OCR prompt with an explicit "do not invent OCR text" rule.
- The mock provider now reads category from that context and returns category-specific OCR.
- Mock provider edge timestamps are bounded to actual media duration, so `late_product_reveal` cannot produce out-of-range observation timestamps.

Final DB check after rerun:

```text
hardcode_leak_count 0
products_missing_context 0
new_evidence_not_v1 0
creative_dna_not_v1 0
tiktok_scores_not_v2 0
adaptations_not_v2 0
campaign_versions_not_v1 0
preflight_not_v2 0
recommendations_not_v2 0
```

## Verified Flows

Clean DB migration and seed:

```text
alembic upgrade head
0001_initial_foundation -> 0002_creative_intelligence_mvp -> 0003_keyless_product_hardening -> 0004_creative_domain_contracts
scripts/seed_local.py
workspace_id 181a2e7f-1afd-47ba-8ad5-54895bd6d76f
```

Fixture HTTP mode:

```text
home/default: status ok, quick_score_run_id e7d3d9fa-81ed-44c1-a04a-c771b87300a4
beauty:       status ok, quick_score_run_id 79b65103-d793-453e-8caf-d979b698053f
POD gift:     status ok, quick_score_run_id c170760c-c1d0-421c-99b7-d06d8e14908a
pet:          status ok, quick_score_run_id dcd70f98-68d1-49c4-8903-53cb109c5dcd
fashion:      status ok, quick_score_run_id ac20f238-dd5d-49ac-9f65-d0cc77a08ec9
```

Mock-provider HTTP mode:

```text
home/default: status ok, quick_score_run_id 29363b7b-9419-43c0-9a12-3592b4646c07
beauty:       status ok, quick_score_run_id 0e64cc7a-2c6e-4e53-8ad7-f44cbb0c5e64
POD gift:     status ok, quick_score_run_id 18e9e485-365c-458a-877a-de6510159eaf
pet:          status ok, quick_score_run_id 11070e1b-7845-4e55-bdc1-60ed0d77c1f0
fashion:      status ok, quick_score_run_id 0494f353-bdbf-4829-8f96-d3f8015d6d66
```

Mock scenario contract check:

```text
scenario_contracts_checked 12
missing_cta: cta_count 0
no_offer: offer_count 0
no_speech: speaking_present false
product_absent: product_appearance_count 0, demo_detected false, proof_count 0
late_product_reveal: timestamps bounded inside duration
```

Quality checks:

```text
backend unit: 38 passed, 1 warning
backend ruff: All checks passed
frontend lint: passed with existing react-refresh warnings only
frontend build: passed with chunk-size warnings only
```

## Implemented Endpoint Surface

Core endpoint families are still the same `/api/v1` paths:

- `GET /system/ai-readiness`
- `GET/POST /workspaces/{workspace_id}/products`
- `GET/POST /workspaces/{workspace_id}/assets`
- `POST /workspaces/{workspace_id}/assets/upload-sessions`
- `POST /workspaces/{workspace_id}/assets/{asset_id}/complete-upload`
- `GET /workspaces/{workspace_id}/assets/{asset_id}/media-analysis`
- `GET/POST /workspaces/{workspace_id}/references`
- `POST /workspaces/{workspace_id}/references/{reference_id}/analyze`
- `POST /workspaces/{workspace_id}/tiktok-scores`
- `GET /workspaces/{workspace_id}/tiktok-scores/{score_run_id}`
- `GET /workspaces/{workspace_id}/creative-dna/{creative_dna_version_id}`
- `POST /workspaces/{workspace_id}/adaptations`
- `POST /workspaces/{workspace_id}/campaign-packs`
- `GET/POST /workspaces/{workspace_id}/campaign-packs/{campaign_pack_id}/versions`
- `POST /workspaces/{workspace_id}/preflight-runs`
- `GET /workspaces/{workspace_id}/preflight-runs/{preflight_run_id}`
- `GET /workspaces/{workspace_id}/recommendations`
- `GET /workspaces/{workspace_id}/jobs/{job_id}`

## Sample Analyze Output For One Video

Source:

```text
GET /api/v1/workspaces/181a2e7f-1afd-47ba-8ad5-54895bd6d76f/assets/f535053c-b6a9-416b-b900-d0f1792bcc96/media-analysis
Product: StyleLoop Belt Bag
Category: fashion_accessory
Mode: mock-provider HTTP
```

Condensed response:

```json
{
  "asset_version_id": "a666978e-234a-41af-9cb3-a03b9f1d8ebb",
  "artifacts_count": 9,
  "artifact_types": [
    "visual_observations",
    "video_metadata",
    "transcript",
    "ocr",
    "sampled_frames",
    "scene_boundaries",
    "artifact_manifest",
    "thumbnail",
    "audio"
  ],
  "evidence_count": 16,
  "evidence_counts_by_type": {
    "claim_signal": 1,
    "creator_signal": 1,
    "cta_signal": 1,
    "demo_step": 1,
    "demo_summary": 1,
    "editing_signal": 1,
    "hook_signal": 1,
    "offer_signal": 1,
    "on_screen_text": 1,
    "platform_signal": 1,
    "product_appearance": 1,
    "product_visibility_summary": 1,
    "proof_signal": 1,
    "transcript_segment": 3
  },
  "evidence_bundle": {
    "pipeline_version": "media_pipeline_v1",
    "confidence": "high",
    "completeness": {
      "visual_observations": true,
      "opening": true,
      "cta": true,
      "transcript": true,
      "ocr": true
    },
    "missing_required": [],
    "timeline": [
      {
        "start_ms": 0,
        "end_ms": 1000,
        "type": "hook_signal",
        "label": "I tried the accessory with two outfits before deciding.",
        "source": "vision",
        "confidence": 0.9
      },
      {
        "start_ms": 0,
        "end_ms": 1000,
        "type": "on_screen_text",
        "label": "Two outfit check",
        "source": "ocr",
        "confidence": 0.92
      },
      {
        "start_ms": 800,
        "end_ms": 1700,
        "type": "product_appearance",
        "label": "product appearance",
        "source": "vision",
        "confidence": 0.88
      },
      {
        "start_ms": 3200,
        "end_ms": 3900,
        "type": "cta_signal",
        "label": "I linked the product in my TikTok Shop.",
        "source": "vision",
        "confidence": 0.86
      }
    ]
  },
  "sample_evidence": [
    {
      "type": "hook_signal",
      "time_ms": [0, 1000],
      "source": "vision",
      "value": {
        "schema_version": "evidence_v1",
        "evidence_type": "hook_signal",
        "hook_type": "testimonial",
        "spoken_text": "I tried the accessory with two outfits before deciding.",
        "overlay_text": "Two outfit check",
        "buyer_pain": "hard to style one accessory with different outfits",
        "frame_storage_keys": ["mock/frame_000.jpg"]
      }
    },
    {
      "type": "product_visibility_summary",
      "source": "derived",
      "value": {
        "schema_version": "evidence_v1",
        "evidence_type": "product_visibility_summary",
        "first_appearance_ms": 800,
        "total_visible_ms": 2500,
        "screen_time_ratio": 0.62,
        "clear_close_up_present": true,
        "usage_present": true
      }
    },
    {
      "type": "demo_step",
      "time_ms": [1100, 2900],
      "source": "vision",
      "value": {
        "schema_version": "evidence_v1",
        "evidence_type": "demo_step",
        "action": "show the accessory worn with two outfit contexts",
        "product_visible": true,
        "mechanism_visible": true,
        "result_visible": true
      }
    },
    {
      "type": "cta_signal",
      "time_ms": [3200, 3900],
      "source": "vision",
      "value": {
        "schema_version": "evidence_v1",
        "evidence_type": "cta_signal",
        "cta_type": "link_in_shop",
        "text": "I linked the product in my TikTok Shop.",
        "product_tag_visible": true
      }
    }
  ]
}
```

Full local JSON for this sample was generated at `/tmp/viraldy_media_analysis_sample_post_ocr_fix.json` during verification.

## Frontend Integration

The MVP route now sends a typed `brief` object when creating Campaign Pack versions and renders:

- Product context and schema versions.
- Creative DNA sections for opening, product, demo, proof, creator, editing, offer, CTA, risks, mechanisms, uncertainties, and completeness.
- TikTok score v2 dimensions, signals, missing signals, blockers, fixes, strengths, and disclaimer.
- Adaptation v2 guidance and three differentiated concepts.
- Campaign Pack brief sections and compiled requirements.
- Preflight v2 coverage statuses, expected/observed payloads, reasons, evidence IDs, blockers, fixes, and pending-rights action wording.

## Intelligence Layer

The system now has these intelligence pieces:

- Evidence-grounded extraction: provider responses must validate as `MediaObservationBundleV1`.
- Schema-bound persistence: new evidence rows validate as `evidence_v1`.
- Deterministic scoring: final TikTok score/action comes from signal formulas and blockers, not model-provided score.
- Deterministic preflight: compiled brief requirements are evaluated one by one; list length no longer creates an artificial must-show score.
- Product-aware adaptation: adaptation uses immutable product snapshots and Creative DNA evidence.
- Claim safety: high-risk/critical claims can create blockers and lower confidence/action.
- No-fabrication guards: absent CTA/offer/product/demo/proof scenarios do not emit those observations.

## Remaining Risks For Next Planning Pass

- Live provider qualification still needs real MP4 samples across categories. Fixture/mock pass does not prove live model extraction quality.
- The mock provider is OpenAI-compatible but still deterministic test infrastructure; it is not a semantic eval benchmark.
- No production rights workflow was implemented. `spark_ready_pending_rights` correctly keeps rights wording pending.
- Frontend typing is local route-level TypeScript, not generated OpenAPI client types.
- Existing frontend lint warnings are pre-existing Fast Refresh warnings.
- Large frontend chunk-size warnings remain.
- Performance analytics, GMV prediction, PatternKit, ViralKit, creator marketplace, and rights workflow are intentionally out of scope.
