# Local Development

Use `make backend-install`, `make infra-up`, `make migrate`, `make seed`, `make api`, and `make worker`. When explicitly using `AUTH_MODE=local_test` for isolated local tests, auth uses `Authorization: Bearer local-test`.

## Native email/password authentication

Use `AUTH_MODE=password` to register and sign in with accounts owned by Viraldy. Accounts, credentials, and sessions persist in PostgreSQL; Redis provides shared rate limiting. Registration creates a user and a private workspace owned by that user. No seeded user is required for this flow.

### Backend environment and migration

Generate two independent secrets once: one for JWT signing and one for signed client-IP forwarding between the BFF and backend.

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

The native-auth migration is `0021_password_auth`, following the committed baseline `0017_domain_ugc_review`. `make migrate` upgrades to the current head and creates `password_credentials`, `password_sessions`, and `password_refresh_tokens`; it does not seed accounts or alter the `users` table. Confirm the database revision matches the reported head. From a separate shell at the repository root, start `make api`; start `make worker` if testing background jobs.

### Frontend runtime and first account

Set the frontend server's `AUTH_PROXY_SECRET` to the exact same value as the backend. For local Vite development, put the following in private `apps/web/.env.local`, or export the equivalent process variables:

```dotenv
AUTH_PUBLIC_ORIGIN=http://127.0.0.1:8081
AUTH_PROXY_SECRET=<the same proxy secret configured on the backend>
AUTH_TRUST_PROXY_HEADERS=false
```

From the repository root:

```sh
pnpm --dir apps/web install
AUTH_PUBLIC_ORIGIN=http://127.0.0.1:8081 \
AUTH_TRUST_PROXY_HEADERS=false \
VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1 \
pnpm --dir apps/web dev --host 127.0.0.1 --port 8081 --strictPort
```

`AUTH_PUBLIC_ORIGIN`, `AUTH_PROXY_SECRET`, and `AUTH_TRUST_PROXY_HEADERS` are frontend **server runtime** settings. The Vite config explicitly loads an allowlist of four AUTH variables (`AUTH_PUBLIC_ORIGIN`, `AUTH_PROXY_SECRET`, `AUTH_TRUST_PROXY_HEADERS`, and `AUTH_CLIENT_SECRET`) from its environment files into the server process when they are not already set. This supports private local `.env`/`.env.local` files; these AUTH values are not exposed as `VITE_` browser variables. On deployment, set the required values in the frontend server's actual runtime environment rather than relying on the build-time loader.

Use one canonical origin, including the correct port. Open `http://127.0.0.1:8081/register`, enter a name, email, and password of at least 12 characters, then confirm the account can sign out and sign in again. Switching between `localhost` and `127.0.0.1` changes the browser's cookie host.

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
