# TikTok Commercial Content integration

## Architecture

Viraldy now keeps TikTok-specific transport and provider quirks inside
`modules/tiktok_commercial_content`. The flow is:

`TikTok API → external source record → saved workspace asset/reference → media import → existing evidence/media analysis → CreativeDNA → PatternKit/adaptation`.

Public provider records are globally deduplicated by provider/entity identity.
Workspace assets and references are created only by an explicit save action, so
workspace authorization continues to protect canonical creative data.

## Configuration

The integration reads these server-only settings:

- `TIKTOK_COMMERCIAL_CLIENT_KEY`
- `TIKTOK_COMMERCIAL_CLIENT_SECRET`
- `TIKTOK_COMMERCIAL_API_ENABLED`
- `TIKTOK_COMMERCIAL_MEDIA_PERSISTENCE_ALLOWED`
- `TIKTOK_COMMERCIAL_DIRECT_STREAM_ALLOWED`
- `TIKTOK_COMMERCIAL_REQUEST_TIMEOUT_SECONDS`
- `TIKTOK_COMMERCIAL_MAX_RETRIES`
- `TIKTOK_COMMERCIAL_CACHE_TTL_SECONDS`
- `TIKTOK_MARKET_INTELLIGENCE`
- `CREATIVE_FAMILY`
- `MARKET_PATTERN_EVIDENCE`
- `BATCH_CREATIVE_REVIEW`
- `SHARE_MARKET_SNAPSHOT`

Credentials are `SecretStr` values and are not returned to the browser or
stored in PostgreSQL. Local credentials belong in the ignored `.env` file.
Media persistence defaults to disabled; when disabled, saving still creates an
explicit `metadata_only` reference state and does not fabricate playback or
analysis.

For approved local/demo environments, direct stream can be enabled with
`TIKTOK_COMMERCIAL_DIRECT_STREAM_ALLOWED=true`. Viraldy fetches the short-lived
TikTok CDN URL server-side and streams it to the authenticated browser without
persisting the media or exposing the signed provider URL. This does not make the
media eligible for analysis; analysis still requires approved persistence and
the normal asset pipeline.

## API boundary

The Creative Library facade is mounted below `/api/v1`:

- `POST /workspaces/{workspace_id}/creative-library/search`
- `POST /workspaces/{workspace_id}/creative-library/advertisers/search`
- `POST /workspaces/{workspace_id}/creative-library/commercial-content/search`
- `POST /workspaces/{workspace_id}/creative-library/reports/ads`
- `GET /workspaces/{workspace_id}/creative-library/sources/{source_id}`
- `GET /workspaces/{workspace_id}/creative-library/sources/{source_id}/media`
- `POST /workspaces/{workspace_id}/creative-library/sources/{source_id}/save-reference`
- `POST /workspaces/{workspace_id}/creative-library/assets/{asset_id}/analyze`
- `GET /workspaces/{workspace_id}/creative-library/assets/{asset_id}/intelligence`
- `POST /workspaces/{workspace_id}/creative-library/assets/{asset_id}/attach-product`
- `POST /workspaces/{workspace_id}/creative-library/assets/{asset_id}/generate-directions`
- `GET|POST /workspaces/{workspace_id}/creative-library/families...`
- `GET /workspaces/{workspace_id}/creative-library/patterns/summary`
- `GET|POST /workspaces/{workspace_id}/creative-library/batch-reviews...`
- `GET|POST /workspaces/{workspace_id}/creative-library/snapshots...`
- `POST /workspaces/{workspace_id}/creative-library/analytics/events`

All responses use the existing envelope and workspace permissions. Raw TikTok
payloads, bearer tokens, and client secrets do not cross this boundary.

## Persistence and provenance

Migration `0018_tiktok_commercial_content` adds the provider source boundary.
Migration `0019_market_intelligence_workflow` adds globally deduplicated market
assets, provenance, PatternKit/adaptation lineage, batch review, snapshots, and
analytics fields. Migration `0020_creative_family_candidates` adds reviewable
family candidates and the expanded workflow event types.

TikTok metadata is persisted as `PLATFORM_METADATA` evidence. Existing media
analysis remains the source for model observations and deterministic extraction.
PatternKit versions derived from TikTok metadata receive a bounded
`MARKET_OBSERVED` state with provider, sample size, timestamps, market,
comparability, recency, strength, and limitations. This state cannot promote
public data to seller-verified, experiment-supported, or performance-supported
evidence.

## Media import

Approved video or image URLs are downloaded server-side by the durable
`tiktok_media_import` worker with timeout, MIME, size, and checksum validation,
then stored under the existing asset storage key. Video assets can enter the
existing media-analysis and CreativeDNA flow. Image-only and metadata-only
references remain explicit and are not sent through video analysis.

TikTok currently supports EU/EEA, GB, and CH country filters for this API. The
backend validates that limitation before making a provider request; unsupported
codes such as `US` return a clear validation error instead of a provider
`invalid_params` response.

## Verification

- Official TikTok client-credentials request: passed locally; token value was
  not printed.
- Backend test suite: 592 passed, 1 skipped; coverage 75.34%.
- Frontend Vitest: 138 passed; TypeScript and production build passed.
- Live 2026 provider smoke: 10 real results returned for `2026-01-01` through
  `2026-08-10`; no token or secret was printed.
- Backend compile, Ruff, and Alembic head checks: passed.
- Frontend TypeScript and targeted ESLint checks: passed.
- OpenAPI was regenerated locally at `docs/api/openapi.json` (ignored by the
  repository, per the existing OpenAPI workflow).

## Compliance assumptions and follow-up

TikTok reach, dates, duration, advertiser history, and prevalence are public
market signals only. This integration does not implement TikTok Shop GMV,
seller Ads performance, ROAS, conversion, creator quality, fatigue, or winner
prediction. Before enabling media persistence in production, obtain owner and
compliance approval. The next recommended extension is the planned
`Performance Import → Workspace Creative Memory → What Worked/What Didn’t →
Next-Test Engine` flow, keeping seller performance evidence separate from
public provider metadata.
