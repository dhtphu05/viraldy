# Viraldy Live Product Run Rerun Status - 2026-08-06 04:55 UTC

## Scope

- Mode: `AI_MODE=live`, `AI_PROVIDER=openai`
- Backend: local FastAPI on `127.0.0.1:8002`
- Infra: local Docker Postgres, Redis, MinIO
- Media file: `/Users/mac/Desktop/Viraldy/apps/web/public/demo-media/download (95) copy.mp4`
- Smoke command: `apps/backend/scripts/smoke_mvp_flow.py --expect-mode live --isolated-lifecycle --verify-db`

## Latest Live Run

- Run id: `product-run-live-upload-viral-cap-20260806T044050Z`
- Result artifact: `/Users/mac/Desktop/Viraldy/artifacts/live-product-run/product-run-live-upload-viral-cap-20260806T044050Z.json`
- Final smoke status: `error`
- Failure stage: `presentation_draft_1`
- Workspace deletion: succeeded

## Passed In Live Product Run Core

- Upload sessions: passed
- Asset complete upload: passed
- Quick Score: passed
  - Structural score: `84`
  - Action: `structurally_ready`
  - Mode: `live`
- Creative DNA reference 1: passed
  - Evidence count: `34`
  - Mode: `live`
- Creative DNA reference 2: passed
  - Evidence count: `35`
  - Mode: `live`
- Adaptation: passed
  - API response: `201 Created`
- PatternKit: passed
  - API response: `201 Created`
  - Review/validate actions: passed
- ViralKit: passed after fix
  - API response: `201 Created`
  - Concept action: `201 Created`
- Campaign Pack: passed
  - API response: `201 Created`
  - Export: `200 OK`
- Preflight: completed
  - Preflight score: `66`
  - Action: `reject`
  - Mode: `live`

## Remaining Live Qualification Gap

- Presentation draft still failed the live smoke check because the creator revision message fell back to deterministic output.
- Backend log evidence:
  - `revision_message_generate` first attempt returned invalid JSON: EOF while parsing a string.
  - repair attempt also returned invalid JSON: EOF while parsing a string.
- This is not an upload failure and not a Product Run core failure. It is a presentation-generation output budget issue.

## Fixes Implemented In This Pass

- `apps/backend/src/viraldy/modules/viral_kits/provider.py`
  - Added deterministic normalization for ViralKit system-owned fields, governance guardrails, required disclosures, product tag requirement, provenance, and source PatternKit IDs.
- `apps/backend/src/viraldy/modules/ai_gateway/prompt_packages.py`
  - Changed ViralKit from `reasoning_effort=high`, `max_output_tokens=10000` to `reasoning_effort=medium`, `max_output_tokens=16000`.
  - Increased revision message `max_output_tokens` from `2000` to `6000`.
- `apps/backend/src/viraldy/modules/presentations/service.py`
  - Added normalization for seller summary and creator revision message so required product name, objective, blocker codes, required exact text, and resubmission guidance are preserved before validation.
- `apps/backend/src/viraldy/modules/adaptations/provider.py`
  - Preserves product name and required guardrails in normalized adaptation output.
- `apps/backend/src/viraldy/modules/pattern_kits/provider.py`
  - Normalizes PatternKit identity/provenance/status/source fields before validation.
- `apps/backend/scripts/smoke_mvp_flow.py`
  - Uses created quick-score detail shape.
  - Adds explicit PatternKit applicability override reason for MVP downstream validation.
- `apps/web/src/features/mvp-flow/routes/mvp-route.tsx`
  - Sends explicit PatternKit applicability override reason in Product Run ViralKit creation.

## Verification

- `uv run python -m py_compile src/viraldy/modules/ai_gateway/prompt_packages.py src/viraldy/modules/presentations/service.py`
- `uv run python -m py_compile src/viraldy/modules/viral_kits/provider.py`
- `uv run pytest tests/unit/test_viral_kits.py -q --no-cov`
- `uv run pytest tests/unit/test_presentations.py tests/unit/test_viral_kits.py -q --no-cov`
- Prior targeted suite after earlier fixes: `48 passed`

## Next Step

Run one narrow live validation focused on presentation after restarting API with the new revision-message token cap. Avoid rerunning the whole Product Run unless presentation requires a fresh preflight run.
