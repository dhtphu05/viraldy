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

Leave `AI_MODE=fixture` for onboarding without external API keys. Smart Remake fixture compile returns deterministic sample analysis; fixture render validates the payload and does not call a video provider or produce a real video URL. For live Smart Remake, edit private `apps/backend/.env` and restart the API:

```dotenv
AI_MODE=live
SMART_REMAKE_ENABLED=true
GEMINI_API_KEY=<your private Gemini key>
```

`SMART_REMAKE_GEMINI_MODEL` selects the model. Real video generation also requires one configured renderer: `UNIFICALLY_API_KEY` for Unifically, or a reachable FlowKit service at `FLOWKIT_URL` (default `http://127.0.0.1:8100`). Choose the corresponding provider in the UI. Docker Compose does not start FlowKit. Install `ffmpeg` and `ffprobe` on the backend host for media processing/render assembly; set `SMART_REMAKE_FFMPEG_PATH` and `SMART_REMAKE_FFPROBE_PATH` if they are not on `PATH`. Optional R2 keys are only needed for R2 output storage; local output uses `apps/backend/outputs/` and `PUBLIC_BASE_URL` instead. These credentials are independent of native email/password auth. Live operations can incur provider charges.

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

The current head is `0022_merge_auth_market`, a merge joining `0020_creative_family_candidates` and `0021_password_auth`. The published native-auth migration `0021_password_auth` retains its original parent `0017_domain_ugc_review`; it does not depend on `0020`. `make migrate` upgrades both branches to the merge head; the auth branch creates `password_credentials`, `password_sessions`, and `password_refresh_tokens` without seeding accounts or altering the `users` table. The merge revision itself has no DDL. Confirm `alembic current` matches the single head reported by `alembic heads`. From a separate shell at the repository root, start `make api`; start `make worker` if testing background jobs.

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
