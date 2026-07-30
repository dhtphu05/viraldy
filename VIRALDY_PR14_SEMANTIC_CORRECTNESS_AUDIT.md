# Viraldy PR14 Semantic Correctness Audit

Date: 2026-07-30 00:05 +07
Branch: `hardening/keyless-product-hardening`
Base head before this pass: `2878bf2075ee22d268c91adf94cfbbdb92f04390`
Goal source: `VIRALDY_PR14_SEMANTIC_CORRECTNESS_COMPLETION_GOAL.md`

## Status

PR14 semantic correctness work is implemented and verified locally across unit,
integration, fixture HTTP smoke, mock-provider HTTP smoke, and no-audio mock HTTP
smoke.

Merge recommendation: semantically merge-ready for live-provider qualification
and private-beta preparation. This is not a production/live-provider claim.

## Defects Closed

### P0: Claim and disclosure semantics

Implemented separate compiled matcher semantics:

- `prohibited_claim_absence`: prohibited claim must not appear.
- `required_disclosure_presence`: required disclosure must appear.
- `allowed_claim_qualification`: allowed claim requires its qualification.

Required disclosures are no longer compiled into prohibited claim checks.

Verification:

- Prohibited claim absent -> satisfied.
- Prohibited claim present -> violated.
- Required disclosure in transcript -> satisfied.
- Required disclosure in OCR -> satisfied.
- Similar but different text -> missing.
- Qualified claim without qualification -> violated.

### P0: Exact requirement matching

Preflight no longer approves requirements from broad TikTok dimension scores.
Campaign Pack requirements compile to `CompiledRequirementV2` and evaluate through
requirement-specific matchers that return:

- `expected`
- `observed`
- `status`
- `confidence`
- `reason`
- `evidence_ids`

Unknown and missing hard requirements are blockers and cannot be silently treated
as satisfied.

### P0: CTA and product timing

Implemented exact matchers for:

- CTA presence.
- CTA type.
- product tag presence.
- CTA timing against `required_before_ms`.
- spoken/overlay CTA text.
- product first appearance against `before_ms`.

### P0: Buyer persona and creator persona

Adaptation and Campaign Pack mapping now keep buyer and creator separate:

- Buyer: `buyer_persona_id`, `buyer_persona_label`, audience pain/outcome.
- Creator: `creator_persona`, `delivery_style`, creator direction.

Regression case verifies `busy college student` buyer does not become
`beauty reviewer` creator.

### P0/P1: No-audio media

Live media pipeline now uses `audio_stream_count` from ffprobe.

When audio stream count is zero:

- audio extraction is skipped.
- audio upload is skipped.
- ASR is skipped.
- transcript is empty.
- OCR, vision, scoring, adaptation, campaign pack, and preflight continue.
- no fake live `audio.wav` artifact is created.

Verified with both unit no-audio MP4 and HTTP mock smoke using a generated
`-an` MP4.

### P1: Typed API contracts

New API rows expose typed contract payloads for:

- `CreativeDnaV1`
- `TikTokScoreResultV2`
- `CampaignPackBriefV1`
- `CompiledRequirementsSnapshotV2`
- `BriefAlignmentResultV2`

Persistence remains JSONB. Pending Preflight rows with legacy `{}` alignment are
adapted to a typed empty alignment response so enqueue responses do not 500.

### P1: Field-level typing

Critical Creative DNA fields now use typed observed wrappers:

- `ObservedStringV1`
- `ObservedBoolV1`
- `ObservedIntV1`
- `ObservedFloatV1`
- `ObservedStringListV1`
- `ObservedObjectListV1`

Invalid examples such as `first_appearance_ms = "early"` now fail validation.

### P1: Product projection consistency

`ProductContextV1.identity` is authoritative for product name and market.

Create/update behavior now prevents drift:

- create with context projects `identity.name` and `identity.market`.
- conflicting top-level name/market is rejected.
- context-only update syncs relational projections.
- top-level name/market update syncs context identity.

### P1: Observation preservation

The pipeline now preserves and uses:

- `editing.pattern_interrupts`
- `editing.dead_air_ranges`
- CTA spoken text
- CTA overlay text
- offer discount text
- offer urgency
- offer timing

Creative DNA no longer sets narrative angle equal to hook type; unknown remains
unknown.

### P1: Scorer correctness

TikTok scorer now:

- compares offer timing against CTA timing.
- compares CTA timing against media duration.
- lowers no-claim safety confidence when transcript/OCR/vision coverage is incomplete.
- only evaluates product mismatch when product context is present.

### P1: Module ownership

Requirement compiler ownership moved to Campaign Pack:

- `modules/campaign_packs/requirements.py`
- public exports through `modules/campaign_packs/public.py`
- `modules/preflight/requirements.py` is now a compatibility re-export.

Architecture test verifies Campaign Pack does not depend on Preflight internals
for the compiler.

## Additional Smoke-Found Fixes

Two API-level issues were found only during HTTP smoke:

1. Pending `PreflightRunResponse` failed typed validation because
   `brief_alignment_json` was `{}` on queued rows. Fixed with a schema adapter
   that coerces `{}` into a typed empty `BriefAlignmentResultV2`.
2. Mock provider adaptation payload was missing the newly required
   `buyer_persona_label`. Fixed mock provider and added unit coverage.

## Verification Commands

Backend unit:

```text
PYTHONPATH=apps/backend/.backend_deps:apps/backend/src \
/Users/mac/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 \
-m pytest apps/backend/tests/unit -q --no-cov
```

Result:

```text
58 passed, 1 warning
```

Backend full tests:

```text
cd apps/backend
PYTHONPATH=.backend_deps:src \
/Users/mac/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 \
-m pytest -q --no-cov
```

Result:

```text
67 passed, 1 warning
```

Backend ruff:

```text
PYTHONPATH=apps/backend/.backend_deps:apps/backend/src \
/Users/mac/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 \
-m ruff check apps/backend/src apps/backend/tests
```

Result:

```text
All checks passed!
```

Whitespace:

```text
git diff --check
```

Result: no output.

Clean migration on local Postgres service:

```text
DATABASE_URL=postgresql+asyncpg://viraldy:viraldy@localhost:55432/viraldy
DATABASE_SYNC_URL=postgresql+psycopg://viraldy:viraldy@localhost:55432/viraldy
python -m alembic upgrade head
```

Result:

```text
PostgresqlImpl, transactional DDL, upgrade head completed
```

Seed:

```text
python scripts/seed_local.py
```

Result:

```text
workspace_id 181a2e7f-1afd-47ba-8ad5-54895bd6d76f
product_id c12f4e66-708d-41e4-9ecd-9dd985b5079b
```

Fixture HTTP smoke:

```text
python scripts/smoke_mvp_flow.py \
  --base-url http://127.0.0.1:8000/api/v1 \
  --expect-mode fixture \
  --timeout-seconds 120 \
  --verify-db
```

Result:

```text
status ok
mode fixture
quick_score_run_id 38cb9378-e8c3-4997-adf2-716482cefbf2
creative_dna_version_id fdb9c3e9-1f3a-4af3-8ce4-e9eb08c1f201
completed_job_ids 3
```

Mock-provider HTTP smoke:

```text
python scripts/mock_openai_provider.py
AI_MODE=mock AI_BASE_URL=http://127.0.0.1:8787/v1 ...
python scripts/smoke_mvp_flow.py \
  --base-url http://127.0.0.1:8000/api/v1 \
  --expect-mode mock \
  --timeout-seconds 120 \
  --verify-db
```

Result:

```text
status ok
mode mock
quick_score_run_id 81e16df4-17a9-477f-99f7-bdaa5535362e
creative_dna_version_id 79b92600-6e9b-45cc-85b9-d35acf0320da
completed_job_ids 3
```

No-audio mock HTTP smoke:

```text
ffmpeg -f lavfi -i testsrc=size=360x640:rate=24 -t 4 -an \
  -pix_fmt yuv420p -y /tmp/viraldy-pr14-no-audio.mp4
ffprobe -select_streams a ... /tmp/viraldy-pr14-no-audio.mp4
python scripts/smoke_mvp_flow.py \
  --base-url http://127.0.0.1:8000/api/v1 \
  --expect-mode mock \
  --media-file /tmp/viraldy-pr14-no-audio.mp4 \
  --timeout-seconds 120 \
  --verify-db
```

Result:

```text
ffprobe audio stream output empty
status ok
mode mock
quick_score_run_id ed078bcb-db2a-4a99-8d36-9361bca96ba3
creative_dna_version_id e7519f97-f6b0-4757-8cfd-41fda17b6809
completed_job_ids 3
```

Frontend lint:

```text
pnpm --dir apps/web lint
```

Result:

```text
0 errors, 11 existing react-refresh warnings
```

Frontend build:

```text
pnpm --dir apps/web build
```

Result:

```text
build completed, chunk-size/code-splitting warnings only
```

## Semantic Matrix Coverage

Unit semantic matrix covers strong fixture paths for:

- home organization
- beauty tool
- POD personalized gift
- pet accessory
- fashion accessory

Assertions include:

- schema version
- exact requirement status
- exact observed product first appearance
- evidence IDs present
- product tag status

Additional focused unit cases cover edge scenarios:

- prohibited claim present/absent
- disclosure present/missing
- similar text false positive guard
- missing qualification
- optional hook one-of
- buyer/creator persona separation
- product projection drift
- no-audio artifact behavior
- offer after CTA
- CTA too late
- incomplete evidence claim confidence
- context-gated product mismatch

## Endpoint Surface

The endpoint families remain stable:

- `POST /workspaces/{workspace_id}/references/{reference_id}/analyze`
- `GET /workspaces/{workspace_id}/assets/{asset_id}/media-analysis`
- `GET /workspaces/{workspace_id}/creative-dna/{creative_dna_version_id}`
- `POST /workspaces/{workspace_id}/tiktok-scores`
- `GET /workspaces/{workspace_id}/tiktok-scores/{score_run_id}`
- `POST /workspaces/{workspace_id}/adaptations`
- `POST /workspaces/{workspace_id}/campaign-packs`
- `GET/POST /workspaces/{workspace_id}/campaign-packs/{campaign_pack_id}/versions`
- `POST /workspaces/{workspace_id}/preflight-runs`
- `GET /workspaces/{workspace_id}/preflight-runs/{preflight_run_id}`
- `GET /workspaces/{workspace_id}/jobs/{job_id}`

There is still no single aggregate endpoint that returns every output for one
video in one response. Current one-video output is composed from job result,
media analysis, Creative DNA, score, and preflight records.

## Known Risks

- Live-provider qualification is still required. Mock and fixture modes prove
  contract shape and workflow semantics, not provider reliability.
- The semantic matrix is strong for happy-path categories and focused P0/P1
  edge cases, but not every scenario listed in the goal has a dedicated
  end-to-end HTTP fixture.
- Frontend worktree has additional modified mock/UI files outside this backend
  semantic commit scope. They were lint/build checked but should be reviewed
  separately before staging.
- PR description/checklist still needs remote GitHub update if it cannot be
  updated from the local environment.

## Files To Hand To Planning

Use this file for planning continuation:

```text
VIRALDY_PR14_SEMANTIC_CORRECTNESS_AUDIT.md
```

Use this file only as the original execution contract:

```text
VIRALDY_PR14_SEMANTIC_CORRECTNESS_COMPLETION_GOAL.md
```
