# Local Development

## Fresh clone

Install Git, `make`, Docker with Compose v2, Python 3.12, `uv`, Node.js 22.12+ (or 24+), and pnpm 10. Run these commands from the cloned repository root:

```sh
make setup-env
make backend-install
make web-install
make infra-up
docker compose ps
make migrate
```

`backend-install` uses `uv sync --frozen --all-extras --dev`; `web-install` uses `pnpm install --frozen-lockfile`. Both use the committed lockfiles. Wait for PostgreSQL, Redis, and MinIO to be healthy and `minio-init` to finish before migrating. Do not run `docker compose down -v` to troubleshoot a teammate's database; it deletes local data.

In separate terminals at the repository root, start `make api`, `make worker` (background jobs), and `make web-dev`. The web target pins port 5173 with `--strictPort`, so an occupied port causes an error instead of silently changing the cookie origin. Open [Create account](http://localhost:5173/register) and register with a name, email, and password of at least 12 characters. Registration creates your own workspace; `make seed` is optional test data for the separate `local_test` workspace and does not create a password login. When explicitly using `AUTH_MODE=local_test` for isolated local tests, auth uses `Authorization: Bearer local-test`.

### Safe env setup

`make setup-env` runs the small native Node script `scripts/setup-local.mjs`, with no dependency installation required. It creates missing `apps/backend/.env` from `.env.example` and missing `apps/web/.env.local` from the template's frontend allowlist. Fresh files use permissions `0600`, `AUTH_MODE=password`, `AUTH_DISABLED=false`, and fixture AI. The script generates two independent 32-byte random secrets: the JWT signing secret stays on the backend, and the proxy secret is shared with the frontend server. Backend credentials and provider keys are not copied into the web env.

Existing files are never overwritten or patched. If just one exists, its nonempty single-line `AUTH_PROXY_SECRET` is reused in the missing file. If that value is missing/blank, fill it manually before retrying; no mismatched peer file will be created. If both files already exist, setup leaves them byte-for-byte intact without validating or reconciling them. For older setups, manually check auth mode, JWT/proxy secrets, API URL, canonical origin, and CORS. Keep existing market feature flags unless intentionally changing them. Keep secret values stable across restarts and out of Git; never prefix a secret with `VITE_`.

The new-clone defaults are:

| Setting | Value |
| --- | --- |
| Backend / frontend `VITE_API_BASE_URL` | `http://localhost:8000/api/v1` |
| Frontend server `AUTH_PUBLIC_ORIGIN` | `http://localhost:5173` |
| Backend `BACKEND_CORS_ORIGINS` | `http://localhost:5173` |
| Frontend server `AUTH_TRUST_PROXY_HEADERS` | `false` |

To keep an existing `http://127.0.0.1:8081` setup, retain that canonical origin and matching backend CORS, and run `pnpm --dir apps/web dev --host 127.0.0.1 --port 8081 --strictPort`. Setup does not change existing env files or running processes. Avoid alternating `localhost` and `127.0.0.1`: cookies are host-specific. Restart the API/worker/frontend after manually changing their env files.

The setup tests copy the script and template to isolated temporary clone fixtures, exercise the CLI there, and remove those fixtures afterward. They do not run setup against this checkout's env files:

```sh
node --test tests/setup-local.test.mjs
```

## Optional AI and render providers

Leave `AI_MODE=fixture` for onboarding without external API keys. Smart Remake fixture compile returns deterministic sample analysis; fixture render does not call a video provider or produce a real video URL. Timeline compile still reads real media, extracts source frames/thumbnails and saves a draft with private source/product assets: PostgreSQL, private S3-compatible storage and FFmpeg/FFprobe must therefore be available even in fixture mode. KIE render/repair is blocked in fixture mode. For live Smart Remake, edit private `apps/backend/.env` and restart the API:

```dotenv
AI_MODE=live
SMART_REMAKE_ENABLED=true
GEMINI_API_KEY=<your private Gemini key>
```

`SMART_REMAKE_GEMINI_MODEL` selects the analysis/compiler model. For KIE Veo 3.1, add the following to private `apps/backend/.env`:

```dotenv
KIE_API_KEY=<your private KIE key>
KIE_POLL_INTERVAL_SECONDS=5
KIE_POLL_TIMEOUT_SECONDS=900
```

Start or restart `make api`, `make worker`, and `make beat` in separate terminals. These targets load `.env` into the process environment, which the render clients require. If starting processes directly, use `uv run --env-file .env ...` from `apps/backend`, or supply the same environment through the deployment secret manager. Do not put provider keys in frontend `VITE_*` variables. `AI_MODE=fixture` blocks KIE render/repair generation even when a key is present.

The live frontend selects KIE when its key is configured. New submissions explicitly select Veo 3.1 Lite, native 9:16, raw eight-second clips. The current app analyzes the entire uploaded source video, retains each analyzed logical scene and its canonical prompt, and retimes the scene sequence into the selected 8/16-second output at 24 fps (192/384 frames). There is no application four-scene cap. Initial video generation uses fixed eight-second provider windows: **8 seconds = one KIE `createTask`; 16 seconds = two**. A logical scene crossing the output eight-second boundary has two execution fragments; this does not create another logical scene. For example, output scenes of 5+5+6 seconds use two calls, with the middle scene split at the provider boundary. Source actions, beats and transitions remain part of the scene plan. Manual group breaks cannot add calls to a new fixed-window plan. Old plans remain viewable, and already-submitted tasks reconcile their existing receipts; update an old script before new initial generation.

Prompt validation follows the provider contract. The [current KIE Veo 3.1 schema](https://docs.kie.ai/veo3-api/generate-veo-3-video) inspected on 26 November 2026 publishes no prompt `maxLength`; the app therefore has no arbitrary 20,000-character KIE prompt cap. A provider rejection is surfaced without silently truncating prompts, dropping scenes or creating extra video tasks. Provider reference-image and eight-second clip constraints still apply.

The current app does not ask the seller to authorize a USD cap, attempt count or execution window. New intake defaults to the mode-only policy `{"mode":"unlimited"}`; the app explicitly upgrades an old finite policy before a newly requested AI action. Existing finite API policies remain compatible. The ledger still records request identity, usage, known charges and unresolved receipts. Missing server price bounds do not block the unlimited flow, and an unknown charge/estimate remains unknown rather than displaying as zero. Media rights and processing disclosure are confirmed when needed; valid confirmation is reused until the relevant inputs or rights change. Revision, technical-validity, stop-use, QA and export checks remain enforced.

New grouped plans also require `OPENAI_API_KEY` on the API and worker. Images are edited directly at `https://api.openai.com/v1/images/edits` using **`gpt-image-2.6-sunburst`**, `n=1`, PNG `720x1280`, **`quality=max` and `complexity=high`**. The Images API calls its image planning effort `complexity`; do not send `reasoning_effort` to this endpoint. Both settings are at the highest supported level for this model. `SMART_REMAKE_OPENAI_IMAGE_QUALITY` defaults to `max`; `low`, `medium`, `high` and `xhigh` remain explicit lower-quality overrides. If the process environment still has an older low-quality override, update it and restart the API and worker before compiling a new plan. The direct image client does not use `OPENAI_BASE_URL` or a KIE image proxy. Model, quality and complexity are frozen in the saved plan; older Flare plans/tasks retain their saved configuration, so recompile to select the new profile. Product and composition images are sent as references. Each group uses the real product plus generated first/last scene references, respecting KIE's three-reference limit. Retained images are reused by input/prompt/model/quality/complexity hash within the owned workspace, so a new Sunburst plan cannot silently reuse a lower-quality Flare image. Legacy Flare cache identities remain compatible. Usage token counts are stored, without assuming a fixed dollar price per image. An uncertain paid image/video submission requires reconciliation and is never automatically repeated.

The quality profile follows [OpenAI GPT Image 2.6 Sunburst](https://developers.openai.com/api/docs/models/gpt-image-2.6-sunburst), the [image complexity guide](https://developers.openai.com/api/docs/guides/image-generation), and the [Images edit API](https://developers.openai.com/api/reference/resources/images/methods/edit). Higher settings are a generation policy, not proof of product fidelity; validate actual outputs separately.

KIE render and repair return a persisted project immediately and run in the `default` Celery queue. PostgreSQL, Redis/broker, private S3-compatible storage (local MinIO is supported), and the worker must be available. Restart API and worker after changing configuration. New jobs freeze a finite technical worker window from the server-owned workload: actual video windows, conditioning references, optional repair analysis and polling configuration. Dispatch and recovery use that same metadata; this is separate from a seller execution-time grant and is not a promised latency. Legacy jobs without this metadata keep their existing 7,200-second hard limit. The beat process recovers stale processing jobs. Install `ffmpeg` and `ffprobe` on both the API host (source compile) and worker host (technical checks and assembly); set `SMART_REMAKE_FFMPEG_PATH` and `SMART_REMAKE_FFPROBE_PATH` if they are not on `PATH`.

Apply migrations through `0024_smart_remake_p0_budget` before using Smart Remake. Revision `0023_smart_remake_scene_repair` creates the project and operation tables; `0024` adds the paid-attempt ledger. Compile persists the authoritative source/render plan and original media in the existing JSONB project data. Keep source storage available when recompiling after a page reload; an older project without retained source requires a new source upload. The Creative Library's browser-local collections remain separate from these server-owned project assets.

KIE completion retains raw clips and proposes unreviewed trim ranges; it does not publish Timeline v2 automatically. Confirm one fixed-length range per scene, save with the current revision, then publish. The `smart_remake_compose` job uses Redis/Celery and FFmpeg to assemble a frozen version/hash snapshot without KIE generation. A compose failure keeps the draft and previously published output; retry assembly with the operation's idempotency semantics instead of creating new AI clips. `GET /projects/{id}` returns draft and published timelines separately.

Outputs are copied into private storage so project history does not depend on the provider URL lifetime. Retry with the same render request key after transport/queue failures. When a submission outcome is unknown and no task ID was confirmed, the operation stays blocked for manual provider-history reconciliation; refreshing does not submit a replacement paid task. A known task can be retrieved again. The current integration uses polling and does not require a public webhook endpoint.

Existing renderers remain available: `UNIFICALLY_API_KEY` for Unifically, or a reachable FlowKit service at `FLOWKIT_URL` (default `http://127.0.0.1:8100`); Docker Compose does not start FlowKit. A failed KIE generation does not automatically fall back to either provider. These credentials are independent of native email/password auth. Live operations can incur provider charges. No live KIE generation was run as part of the implementation checks.

## Optional local demo media

`apps/web/public/product_ads/` and `apps/web/public/smart-remake/` are private local demo directories excluded from Git, along with backend outputs, local caches, and root QA screenshots. Pulling application code does not supply the prerecorded videos/images from another developer's machine. Use your own uploads, or obtain the optional demo bundle separately through the team's existing sharing channel.

If you have that bundle, copy only its demo directories, preserving filenames referenced by the UI. From the repository root, replacing `/path/to/private-demo-bundle` with your actual source:

```sh
mkdir -p apps/web/public/product_ads apps/web/public/smart-remake
cp -Rn /path/to/private-demo-bundle/product_ads/. apps/web/public/product_ads/
cp -Rn /path/to/private-demo-bundle/smart-remake/. apps/web/public/smart-remake/
```

`-n` avoids overwriting existing local media. Missing demo files use the frontend's fallback preview state; they are not required for account creation or normal API startup. Do not commit the demo media, generated outputs, screenshots, or env files. `AI_MODE=fixture` does not install media files.

## Native email/password authentication

Use `AUTH_MODE=password` to register and sign in with accounts owned by Viraldy. Accounts, credentials, and sessions persist in PostgreSQL; Redis provides shared rate limiting. Registration creates a user and a private workspace owned by that user. No seeded user is required for this flow.

### Backend environment and migration

For a fresh clone, `make setup-env` generates these secrets. For an existing setup that needs manual configuration, generate two independent secrets once: one for JWT signing and one for signed client-IP forwarding between the BFF and backend.

```sh
openssl rand -hex 32 # AUTH_JWT_SECRET: backend only
openssl rand -hex 32 # AUTH_PROXY_SECRET: same value on backend and frontend server
```

Store the generated values in private environment files or a secret manager. Keep them stable across instances and restarts; never commit them or send them to the browser. Set these backend values in `apps/backend/.env`, which backend commands load from their working directory, or export them into the shell running those commands:

```dotenv
AUTH_MODE=password
AUTH_DISABLED=false
AUTH_JWT_SECRET=<the generated JWT secret>
AUTH_PROXY_SECRET=<the generated shared proxy secret>
AUTH_JWT_ISSUER=viraldy
AUTH_JWT_AUDIENCE=viraldy-api
AUTH_ACCESS_TOKEN_SECONDS=900
AUTH_REFRESH_TOKEN_DAYS=30
REDIS_URL=redis://127.0.0.1:6379/0
```

Also configure `DATABASE_URL` and `DATABASE_SYNC_URL` for the same application database using the asyncpg and psycopg drivers respectively. A root `.env` used by Docker Compose is not automatically the backend `.env`; keep the relevant settings consistent. Use a dedicated Redis instance or database for the target environment.

Install dependencies, start the normal application infrastructure, and migrate before starting the API:

```sh
make backend-install
make infra-up
make migrate
cd apps/backend
uv run alembic current
uv run alembic heads
```

The current head is `0024_smart_remake_p0_budget`, following `0023_smart_remake_scene_repair` and `0022_merge_auth_market`, the merge joining `0020_creative_family_candidates` and `0021_password_auth`. The published native-auth migration `0021_password_auth` retains its original parent `0017_domain_ugc_review`; it does not depend on `0020`. `make migrate` upgrades both branches through the merge, creates the Smart Remake project/operation tables in `0023`, and adds the paid-attempt ledger in `0024`. The auth branch creates `password_credentials`, `password_sessions`, and `password_refresh_tokens` without seeding accounts or altering the `users` table. The merge revision itself has no DDL. Confirm `alembic current` matches the single head reported by `alembic heads`. From a separate shell at the repository root, start `make api`; start `make worker` if testing background jobs.

### Frontend runtime and first account

Set the frontend server's `AUTH_PROXY_SECRET` to the exact same value as the backend. For local Vite development, put the following in private `apps/web/.env.local`, or export the equivalent process variables:

```dotenv
AUTH_PUBLIC_ORIGIN=http://localhost:5173
VITE_API_BASE_URL=http://localhost:8000/api/v1
AUTH_PROXY_SECRET=<the same proxy secret configured on the backend>
AUTH_TRUST_PROXY_HEADERS=false
```

From the repository root:

```sh
make web-dev
```

`AUTH_PUBLIC_ORIGIN`, `AUTH_PROXY_SECRET`, and `AUTH_TRUST_PROXY_HEADERS` are frontend **server runtime** settings. The Vite config explicitly loads an allowlist of four AUTH variables (`AUTH_PUBLIC_ORIGIN`, `AUTH_PROXY_SECRET`, `AUTH_TRUST_PROXY_HEADERS`, and `AUTH_CLIENT_SECRET`) from its environment files into the server process when they are not already set. This supports private local `.env`/`.env.local` files; these AUTH values are not exposed as `VITE_` browser variables. On deployment, set the required values in the frontend server's actual runtime environment rather than relying on the build-time loader.

Use one canonical origin, including the correct port. For the new-clone defaults, set `AUTH_PUBLIC_ORIGIN=http://localhost:5173` and open `http://localhost:5173/register`, enter a name, email, and password of at least 12 characters, then confirm the account can sign out and sign in again. Switching between `localhost` and `127.0.0.1` changes the browser's cookie host.

The browser talks to the frontend BFF for authentication. The BFF stores tokens in HttpOnly, SameSite=Lax cookies and uses Secure, `__Host-` cookies when the canonical origin is HTTPS. The backend returns tokens to the BFF; the browser-facing sign-in response does not expose them. Keep `AUTH_JWT_SECRET` on the backend only.

For a built frontend, configure `VITE_API_BASE_URL` before building. Configure `AUTH_PUBLIC_ORIGIN`, `AUTH_PROXY_SECRET`, and `AUTH_TRUST_PROXY_HEADERS` separately in the deployed frontend server's runtime environment. Keep `AUTH_PROXY_SECRET` separate from `AUTH_JWT_SECRET`; it authenticates forwarding metadata, not user JWTs.

### Token and session lifecycle

| Item              | Current behavior                                                                                                                                                                         |
| ----------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Password storage  | Salted Argon2id hash in `password_credentials.password_hash`; unique lowercase login email.                                                                                              |
| Access token      | HS256 JWT, default lifetime 900 seconds; issuer, audience, subject, session ID, token ID, issue time, expiry, and `type=access` are checked.                                             |
| Session           | `password_sessions.id` links to `user_id`; `expires_at` is an absolute deadline, default 30 days from login/registration. Refresh does not extend it.                                    |
| Revocation        | `password_sessions.revoked_at` is nullable. Protected requests require it to be null, `expires_at` to be in the future, and the linked user's `status` to be `active`.                   |
| Refresh storage   | Only the SHA-256 `token_hash` is persisted in `password_refresh_tokens`, linked by `session_id`, with `created_at` and nullable `consumed_at`.                                           |
| Rotation          | A successful refresh sets the old token's `consumed_at` and issues a fresh token under a locked session row. Consumed hashes remain available for replay detection.                      |
| Duplicate refresh | Reusing a consumed token within five seconds returns HTTP 409 with `REFRESH_ALREADY_USED`, without revoking the session or returning another token.                                      |
| Replay            | Reusing that token at or after five seconds revokes its session and returns HTTP 401 with `SESSION_REVOKED`. Existing access tokens for the same session then fail the DB session check. |
| Logout            | Marks the presented refresh token's session revoked; returns HTTP 204 idempotently. Other independently created sessions remain active.                                                  |

Do not delete consumed refresh-token records while their session remains valid: they are needed to recognize replay. The five-second duplicate window is not an extension of refresh-token validity. The BFF must retain cookies on a temporary 409 and use the winning refresh response; coordination across frontend processes is needed if parallel requests can outlive that window.

### Rate limiting and operational checks

The limiter uses Redis transactions to increment counters and set a 60-second expiry. Current limits are 30 requests per client IP per minute for each of login/register, eight per email per minute for each of login/register, and 300 per client IP per minute for each of refresh/logout. The IP is the verified signed client address when available, otherwise the actual connection peer. Keys hash the IP/email bucket value.

Redis failures are fail-closed: registration, login, refresh, and logout return HTTP 503 `AUTH_UNAVAILABLE` when their limiter cannot reach Redis. HTTP 429 `RATE_LIMITED` means the request exceeded a configured bucket. Keep Redis reachable before testing account flows; there is no fallback that bypasses the limiter.

The BFF's `authPeerHeaders` obtains the address with framework `getRequestIP`. By default, `AUTH_TRUST_PROXY_HEADERS=false` means transport-only address extraction: arbitrary `X-Forwarded-For` headers are not accepted as the client identity. It signs `timestamp:IP` with HMAC-SHA256 using the shared `AUTH_PROXY_SECRET`, and sends `x-viraldy-client-ip`, `x-viraldy-client-time`, and `x-viraldy-client-signature` to the backend on native-auth calls.

The backend's `auth_client_ip` validates IP syntax, requires the timestamp to be within 60 seconds of its clock, and verifies the HMAC before using the normalized address. Missing, invalid, stale, or incorrectly signed assertions fall back to `request.client.host`; arbitrary `X-Forwarded-For` headers are ignored by this verifier. Keep the two servers' proxy secrets identical and their clocks synchronized so valid clients are not grouped under the BFF peer fallback.

Set `AUTH_TRUST_PROXY_HEADERS=true` **only** when the frontend actually runs behind a trusted edge that overwrites forwarding headers, and direct requests cannot bypass that edge with attacker-controlled values. In that deployment the BFF signs the client address supplied by the trusted edge. HMAC authenticates what the BFF forwards; it does not make an untrusted incoming forwarding header trustworthy. Keep the default false for direct local access. If deployed behind an edge with this option false, all users may still share the edge's transport IP; verify separate clients receive separate quotas through the real deployment path.

Check these behaviors against the running environment:

1. `GET /api/v1/auth/config` reports `auth_mode=password` and `enabled=true`.
2. Registration persists a lowercase email and Argon2id hash, creates a private workspace, and allows a later login. Another account cannot access that workspace.
3. Invalid credentials return the same HTTP 401 message for unknown email and wrong password; duplicate registration returns HTTP 409.
4. Refresh rotates the token, an immediate duplicate returns 409, and a replay after the five-second window revokes the session. Test truly simultaneous refreshes and refresh/logout requests as well.
5. Logout makes the same session's access and refresh tokens unusable. Requests with an expired or revoked session return 401.
6. A rate-limit breach returns 429. A separate isolated Redis-outage check returns 503; do not stop shared infrastructure to perform this check.
7. Distinct clients with valid signed forwarding assertions have separate IP quotas even through one BFF. Invalid signatures, timestamps older than 60 seconds, and arbitrary forwarding headers cannot select another client's quota.

### Production configuration and current boundaries

Use `APP_ENV=production`, `AUTH_MODE=password`, and `AUTH_DISABLED=false`. Supply a unique random `AUTH_JWT_SECRET` from your secret manager and the same issuer/audience settings to every API instance. Production/staging password settings also require `AUTH_PROXY_SECRET` of at least 32 bytes; generate it independently and supply the same value to all backend and frontend server instances at runtime. Restrict database/Redis network access and use the deployment's authenticated, encrypted connections. Apply migrations as a controlled release step before routing traffic to the new application version.

Set the frontend server runtime `AUTH_PUBLIC_ORIGIN` to the exact public HTTPS origin, such as `https://app.example.com`, and set the backend address used by `VITE_API_BASE_URL` at build time. Set runtime `AUTH_TRUST_PROXY_HEADERS` according to the actual trusted-edge arrangement above. Verify HTTPS cookie flags, same-origin mutation checks, signed client-IP forwarding, and rate limits through the real deployment proxy.

Email verification and password reset/recovery are **not implemented** in native password mode. Registration signs the user in immediately; the email is a login identifier, not evidence of verified ownership. Do not claim verified-email onboarding or offer an operational password-reset flow until those features exist.
