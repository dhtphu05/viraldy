# TikTok Market Intelligence Workflow

This milestone connects official TikTok Commercial Content metadata to the existing
workspace Creative Library without introducing billing or paid-plan enforcement.

## Data flow

TikTok search results are stored as server-only `ExternalSourceRecord` rows and mapped
to one globally deduplicated `AssetModel` with `library_scope=MARKET`. A user save creates
a workspace `ReferenceModel` pointing to that asset. The reference is the authorization
boundary: another workspace cannot read a market asset until it saves its own reference.

Approved media persistence uses the existing S3/Celery import path. Metadata-only and
image-only assets remain explicit states. Media analysis is on-demand and feeds the
existing evidence, CreativeDNA, scorer and adaptation pipeline.

Market evidence is labelled as public market signal and cannot be treated as seller
performance, GMV, ROAS, experiment-supported, workspace-proven or high-confidence proof.
Pattern Evidence stores sample size, comparability, market, category, dates, recency and
limitations. Adaptation output is persisted as exactly three `CreativeDirection` rows
with product, evidence and source provenance.

Batch Review stores each asset decision and a separate `DecisionLog`: `TEST`, `FIX`,
`RESHOOT`, `SKIP`, or `INSUFFICIENT_EVIDENCE`, with seller response values
`accepted`, `rejected`, `modified`, or `ignored`.

Published `/insights/{slug}` snapshots pass a server-side privacy gate and contain only
market-safe summaries. Workspace assets, Product Context, seller notes, UGC, rights,
performance data, credentials, transcripts and media URLs are rejected.

## Rollout controls

The feature flags `TIKTOK_MARKET_INTELLIGENCE`, `CREATIVE_FAMILY`,
`MARKET_PATTERN_EVIDENCE`, `BATCH_CREATIVE_REVIEW`, and `SHARE_MARKET_SNAPSHOT` default
to false. Search, analysis, score, adaptation and batch limits are operational cost
controls only. They are not entitlements and do not trigger checkout or upgrade flows.

## Migration and verification

Migration `0019_market_intelligence_workflow.py` follows `0018_tiktok_commercial_content`.
The Alembic revision is `0019_market_intel_workflow` to fit the existing 32-character
Alembic version column.

Useful checks:

```bash
cd apps/backend
uv run alembic heads
uv run pytest -q --no-cov
uv run ruff check src/viraldy

cd ../web
pnpm test
pnpm typecheck
pnpm lint
pnpm build
```

Billing, payment checkout, subscriptions, invoices, trials and paid-plan enforcement
are intentionally deferred to a later milestone.
